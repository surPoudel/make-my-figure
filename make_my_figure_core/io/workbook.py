"""Shared multi-sheet Excel workbook layer for the desktop and Streamlit apps.

A workbook (``.xlsx``/``.xls``/``.xlsm``) may contain many worksheets: differential
result tables, matrices, sample metadata, enrichment tables, README/notes sheets,
empty sheets, and so on. This module lets both frontends:

* list **every** worksheet in workbook order (never hiding a sheet because it does
  not look like data),
* preview a sheet cheaply without fully loading it,
* fully load only the selected sheet,
* attach a lightweight **advisory** classification (documentation / matrix /
  differential results / metadata / enrichment / generic / empty / unknown), and
* build cross-platform-safe output slugs from the workbook + sheet names.

Design invariants:

* Classification is advisory only — it never removes a sheet from the list or blocks
  selection.
* The workbook bytes are read once; sheet listing/preview/load work from the cached
  bytes so switching sheets never re-reads the file from disk.
* No new heavy dependencies: sheet listing/hidden-state uses ``openpyxl`` (already a
  dependency); reading uses pandas. Old ``.xls`` is supported only if an ``xlrd``
  engine is installed (degrades with a clear message otherwise).

Pure pandas/openpyxl — no R and no RNA-seq pipeline.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, BinaryIO, Dict, List, Optional, Sequence, Union

import pandas as pd

from make_my_figure_core.io.loaders import LoaderError, TableInfo, load_table

ExcelSource = Union[str, os.PathLike, bytes, BinaryIO]

EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}

# Advisory sheet-type labels (stable strings persisted in provenance).
SHEET_TYPE_DIFFERENTIAL = "differential_results"
SHEET_TYPE_MATRIX = "matrix"
SHEET_TYPE_METADATA = "metadata"
SHEET_TYPE_ENRICHMENT = "enrichment"
SHEET_TYPE_DOCUMENTATION = "documentation"
SHEET_TYPE_GENERIC = "generic"
SHEET_TYPE_EMPTY = "empty"
SHEET_TYPE_UNKNOWN = "unknown"

# Human-readable blurbs the UIs can show under the dropdown.
SHEET_TYPE_MESSAGES = {
    SHEET_TYPE_DIFFERENTIAL: (
        "Detected sheet type: precomputed differential results. Volcano, MA, and "
        "ranked-effect plots may be available after column confirmation."
    ),
    SHEET_TYPE_MATRIX: (
        "Detected sheet type: numeric feature matrix. Heatmap, PCA, and clustering "
        "plots may be available after mapping the value columns."
    ),
    SHEET_TYPE_METADATA: (
        "Detected sheet type: sample metadata. Use it to define groups, or as the "
        "metadata source for a matrix on another worksheet."
    ),
    SHEET_TYPE_ENRICHMENT: (
        "Detected sheet type: enrichment / pathway table. Ranked bar or dot plots "
        "may be available after column confirmation."
    ),
    SHEET_TYPE_DOCUMENTATION: (
        "Detected sheet type: documentation/notes. You may still select and inspect "
        "this worksheet, but no plot is currently recommended."
    ),
    SHEET_TYPE_GENERIC: (
        "Detected sheet type: generic tabular data. Choose a plot type and map the "
        "columns to visualize it."
    ),
    SHEET_TYPE_EMPTY: (
        "This worksheet is empty. It stays selectable, but plotting is disabled."
    ),
    SHEET_TYPE_UNKNOWN: (
        "Sheet type could not be inferred. You may still select and inspect it."
    ),
}


@dataclass
class WorksheetInfo:
    """Lightweight description of one worksheet (from a cheap preview read)."""

    workbook_id: str
    sheet_name: str
    sheet_index: int
    row_count: int
    column_count: int
    inferred_type: str = SHEET_TYPE_UNKNOWN
    header_row: Optional[int] = 0
    headers: List[str] = field(default_factory=list)
    preview: Optional[pd.DataFrame] = None
    warnings: List[str] = field(default_factory=list)
    is_empty: bool = False
    is_hidden: bool = False
    # Every worksheet is always selectable — classification is advisory only.
    selectable: bool = True
    classification_reason: str = ""

    @property
    def type_message(self) -> str:
        return SHEET_TYPE_MESSAGES.get(self.inferred_type, SHEET_TYPE_MESSAGES[SHEET_TYPE_UNKNOWN])

    def summary(self) -> Dict[str, Any]:
        return {
            "workbook_id": self.workbook_id,
            "sheet_name": self.sheet_name,
            "sheet_index": self.sheet_index,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "inferred_type": self.inferred_type,
            "header_row": self.header_row,
            "headers": list(self.headers),
            "warnings": list(self.warnings),
            "is_empty": self.is_empty,
            "is_hidden": self.is_hidden,
            "selectable": self.selectable,
        }


@dataclass
class WorkbookInfo:
    """Description of a workbook: its sheets, order, hidden state, and identity."""

    workbook_id: str
    source_filename: str
    sheet_names: List[str] = field(default_factory=list)
    sheet_order: List[int] = field(default_factory=list)
    hidden_sheets: List[str] = field(default_factory=list)
    active_sheet: Optional[str] = None
    workbook_format: str = "xlsx"
    file_hash: str = ""
    warnings: List[str] = field(default_factory=list)

    @property
    def n_sheets(self) -> int:
        return len(self.sheet_names)

    def is_hidden(self, sheet_name: str) -> bool:
        return sheet_name in self.hidden_sheets

    def summary(self) -> Dict[str, Any]:
        return {
            "workbook_id": self.workbook_id,
            "source_filename": self.source_filename,
            "sheet_names": list(self.sheet_names),
            "hidden_sheets": list(self.hidden_sheets),
            "active_sheet": self.active_sheet,
            "workbook_format": self.workbook_format,
            "file_hash": self.file_hash,
            "warnings": list(self.warnings),
        }


# --------------------------------------------------------------------------- #
# Source normalization + caching
# --------------------------------------------------------------------------- #

# Cache workbook bytes by content hash so switching sheets never re-reads a file,
# and cache preview/full reads by (hash, sheet, header) so repeated widget reruns
# are cheap. Bounded to avoid unbounded growth on large sessions.
_BYTES_CACHE: "Dict[str, bytes]" = {}
_PREVIEW_CACHE: "Dict[tuple, WorksheetInfo]" = {}
_MAX_CACHE_ENTRIES = 64


def _prune(cache: dict) -> None:
    while len(cache) > _MAX_CACHE_ENTRIES:
        cache.pop(next(iter(cache)))


def _read_source_bytes(source: ExcelSource) -> tuple[bytes, str]:
    """Return ``(raw_bytes, source_filename)`` for any accepted source form."""
    if isinstance(source, (str, os.PathLike)):
        path = os.fspath(source)
        with open(path, "rb") as fh:
            data = fh.read()
        return data, os.path.basename(path)
    if isinstance(source, bytes):
        return source, "uploaded_workbook.xlsx"
    # file-like
    name = getattr(source, "name", "") or "uploaded_workbook.xlsx"
    if hasattr(source, "seek"):
        try:
            source.seek(0)
        except Exception:  # pragma: no cover - defensive
            pass
    data = source.read()
    if isinstance(data, str):  # text-mode handle
        data = data.encode("utf-8")
    return data, os.path.basename(name)


def compute_file_hash(data: bytes) -> str:
    """Stable short content hash used for workbook identity + cache keys."""
    return hashlib.sha256(data).hexdigest()[:16]


def is_excel_source(source_name: Optional[str]) -> bool:
    if not source_name:
        return False
    return os.path.splitext(source_name)[1].lower() in EXCEL_EXTENSIONS


# --------------------------------------------------------------------------- #
# Sheet listing / inspection
# --------------------------------------------------------------------------- #

def _openpyxl_sheet_states(data: bytes) -> Optional[Dict[str, str]]:
    """Map sheet name -> state ('visible'/'hidden'/'veryHidden') via openpyxl.

    Returns ``None`` when openpyxl cannot open the workbook (e.g. legacy ``.xls``).
    """
    try:
        import openpyxl  # local import; already a dependency
    except Exception:  # pragma: no cover - openpyxl is a declared dependency
        return None
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, keep_links=False)
    except Exception:
        return None
    try:
        return {ws.title: ws.sheet_state for ws in wb.worksheets}
    finally:
        wb.close()


def list_excel_sheets(source: ExcelSource) -> List[str]:
    """Return every worksheet name in workbook order (no filtering)."""
    return inspect_excel_workbook(source).sheet_names


def inspect_excel_workbook(
    source: ExcelSource, source_name: Optional[str] = None
) -> WorkbookInfo:
    """List all worksheets and identity for a workbook without loading sheet data.

    Raises :class:`LoaderError` with an actionable message for corrupt /
    password-protected / unsupported / empty workbooks.
    """
    data, fname = _read_source_bytes(source)
    if source_name:
        fname = source_name
    if not data:
        raise LoaderError(f"Workbook '{fname}' is empty (no bytes).")

    file_hash = compute_file_hash(data)
    _BYTES_CACHE[file_hash] = data
    _prune(_BYTES_CACHE)

    ext = os.path.splitext(fname)[1].lower() or ".xlsx"
    warnings: List[str] = []
    engine = None
    if ext == ".xls":
        try:
            import xlrd  # noqa: F401
        except Exception:
            raise LoaderError(
                f"'{fname}' is a legacy .xls workbook and the 'xlrd' engine is not "
                "installed. Re-save it as .xlsx, or install xlrd."
            )
        engine = "xlrd"

    try:
        xl = pd.ExcelFile(io.BytesIO(data), engine=engine)
        sheet_names = list(xl.sheet_names)
    except LoaderError:
        raise
    except Exception as exc:
        msg = str(exc).lower()
        if "password" in msg or "encrypt" in msg:
            raise LoaderError(
                f"'{fname}' looks password-protected/encrypted; remove the password "
                "and re-upload."
            ) from exc
        raise LoaderError(
            f"Could not open workbook '{fname}': {exc}. It may be corrupt or an "
            "unsupported format."
        ) from exc

    if not sheet_names:
        raise LoaderError(f"Workbook '{fname}' contains no worksheets.")

    states = _openpyxl_sheet_states(data) if ext != ".xls" else None
    hidden = []
    if states:
        hidden = [name for name in sheet_names if states.get(name, "visible") != "visible"]
    elif ext != ".xls":
        warnings.append("Could not determine hidden-sheet state; all sheets shown.")

    return WorkbookInfo(
        workbook_id=file_hash,
        source_filename=fname,
        sheet_names=sheet_names,
        sheet_order=list(range(len(sheet_names))),
        hidden_sheets=hidden,
        active_sheet=sheet_names[0] if sheet_names else None,
        workbook_format=ext.lstrip("."),
        file_hash=file_hash,
        warnings=warnings,
    )


def _bytes_for(workbook: WorkbookInfo, source: Optional[ExcelSource]) -> bytes:
    """Resolve workbook bytes from the cache, re-reading ``source`` if needed."""
    data = _BYTES_CACHE.get(workbook.file_hash)
    if data is not None:
        return data
    if source is None:
        raise LoaderError(
            "Workbook bytes are no longer cached; re-open the workbook to continue."
        )
    data, _ = _read_source_bytes(source)
    _BYTES_CACHE[workbook.file_hash] = data
    _prune(_BYTES_CACHE)
    return data


# --------------------------------------------------------------------------- #
# Classification (advisory only)
# --------------------------------------------------------------------------- #

_ENRICHMENT_HINTS = ("term", "pathway", "go_", "goterm", "geneset", "gene_set",
                     "nes", "enrichment", "gene_ratio", "generatio", "overlap",
                     "kegg", "reactome", "padj_enrich")
_SAMPLE_HINTS = ("sample", "replicate", "barcode")
_GROUP_HINTS = ("group", "condition", "treatment", "genotype", "cohort", "batch")
_FEATURE_HINTS = ("gene", "feature", "protein", "peptide", "transcript", "id",
                  "symbol", "accession")


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def classify_worksheet(
    df: Optional[pd.DataFrame], *, header_present: bool = True
) -> tuple[str, str]:
    """Advisory classification of a worksheet preview.

    Returns ``(inferred_type, reason)``. Never raises; purely heuristic. The reason
    is a short human-readable justification for the UI.
    """
    if df is None or df.shape[0] == 0 or df.shape[1] == 0:
        return SHEET_TYPE_EMPTY, "No rows or columns."

    # A tiny, mostly-text single/double-column table reads as documentation/notes.
    non_null = df.notna().sum().sum()
    total_cells = df.shape[0] * df.shape[1]
    if total_cells and non_null / total_cells < 0.15:
        return SHEET_TYPE_DOCUMENTATION, "Mostly blank cells (looks like notes)."

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    numeric_frac = len(numeric_cols) / df.shape[1] if df.shape[1] else 0.0
    lowered = {c: _norm(c) for c in df.columns}
    norm_names = list(lowered.values())

    # Differential-result headers via the shared DE alias detector.
    try:
        from make_my_figure_core.de_detect import detect_de_columns

        de = detect_de_columns(df)
    except Exception:  # pragma: no cover - defensive
        de = {}
    has_lfc = bool(de.get("logFC"))
    has_p = bool(de.get("p_value") or de.get("adj_p"))
    if has_lfc and has_p:
        return SHEET_TYPE_DIFFERENTIAL, "Found fold-change and p-value/FDR columns."

    # Enrichment / pathway tables.
    if any(any(h in n for h in _ENRICHMENT_HINTS) for n in norm_names):
        return SHEET_TYPE_ENRICHMENT, "Found enrichment/pathway-style headers."

    # Documentation: 1-2 columns and no numeric columns.
    if df.shape[1] <= 2 and not numeric_cols:
        return SHEET_TYPE_DOCUMENTATION, "Only text columns (looks like notes/legend)."

    # Metadata: small, has a sample-like id and a group-like column.
    has_sample = any(any(h in n for h in _SAMPLE_HINTS) for n in norm_names)
    has_group = any(any(h in n for h in _GROUP_HINTS) for n in norm_names)
    if has_sample and has_group and numeric_frac < 0.5:
        return SHEET_TYPE_METADATA, "Found sample-id and group columns."

    # Matrix: a feature-id-like first column plus many numeric (sample) columns.
    first_is_feature = any(h in lowered[df.columns[0]] for h in _FEATURE_HINTS)
    if numeric_frac >= 0.6 and len(numeric_cols) >= 3:
        if first_is_feature or not first_is_feature:
            return SHEET_TYPE_MATRIX, "Mostly numeric columns (looks like a matrix)."

    if numeric_cols:
        return SHEET_TYPE_GENERIC, "Tabular data with a mix of column types."
    return SHEET_TYPE_UNKNOWN, "Could not infer a specific sheet type."


# --------------------------------------------------------------------------- #
# Preview + full load
# --------------------------------------------------------------------------- #

def preview_excel_sheet(
    workbook: WorkbookInfo,
    sheet_name: str,
    *,
    source: Optional[ExcelSource] = None,
    header: Union[int, Sequence[int], None] = 0,
    nrows: int = 50,
) -> WorksheetInfo:
    """Cheap preview (first ``nrows`` rows) + advisory classification of a sheet.

    Never raises for empty/odd sheets — those come back as selectable
    :class:`WorksheetInfo` with an explanatory warning.
    """
    key = (workbook.file_hash, sheet_name, header, nrows)
    cached = _PREVIEW_CACHE.get(key)
    if cached is not None:
        return cached

    data = _bytes_for(workbook, source)
    try:
        sheet_index = workbook.sheet_names.index(sheet_name)
    except ValueError:
        raise LoaderError(f"Worksheet '{sheet_name}' is not in workbook '{workbook.source_filename}'.")

    engine = "xlrd" if workbook.workbook_format == "xls" else None
    warnings: List[str] = []
    try:
        preview = pd.read_excel(
            io.BytesIO(data),
            sheet_name=sheet_name,
            header=header,
            nrows=nrows,
            engine=engine,
        )
    except Exception as exc:
        # A malformed sheet stays selectable; surface the reason.
        info = WorksheetInfo(
            workbook_id=workbook.file_hash,
            sheet_name=sheet_name,
            sheet_index=sheet_index,
            row_count=0,
            column_count=0,
            inferred_type=SHEET_TYPE_UNKNOWN,
            header_row=header,
            headers=[],
            preview=None,
            warnings=[f"Could not preview this sheet: {exc}"],
            is_empty=True,
            is_hidden=workbook.is_hidden(sheet_name),
            selectable=True,
            classification_reason="Preview failed.",
        )
        _PREVIEW_CACHE[key] = info
        _prune(_PREVIEW_CACHE)
        return info

    if header is None:
        preview.columns = [f"column_{i + 1}" for i in range(preview.shape[1])]

    is_empty = preview.shape[0] == 0 or preview.shape[1] == 0
    headers = [] if header is None else [str(c) for c in preview.columns]

    # Detect unnamed / duplicate columns (advisory).
    if not is_empty:
        unnamed = [c for c in preview.columns if str(c).startswith("Unnamed:")]
        if unnamed:
            warnings.append(
                "Some columns have no header — confirm the header row or choose "
                "'No header'."
            )
        seen, dups = set(), set()
        for c in preview.columns:
            if c in seen:
                dups.add(c)
            seen.add(c)
        if dups:
            warnings.append(f"Duplicate column names: {sorted(str(d) for d in dups)}")

    inferred, reason = classify_worksheet(None if is_empty else preview,
                                          header_present=header is not None)
    if is_empty:
        warnings.append("This worksheet is empty.")

    # Row count without loading the whole sheet unless it fits in the preview.
    row_count = int(preview.shape[0])
    if not is_empty and row_count >= nrows:
        # Full count via a values-only pass (cheap relative to a typed full load).
        try:
            full = pd.read_excel(
                io.BytesIO(data), sheet_name=sheet_name, header=header,
                usecols=[0], engine=engine,
            )
            row_count = int(full.shape[0])
        except Exception:
            warnings.append(f"Showing first {nrows} rows; full row count unknown.")

    info = WorksheetInfo(
        workbook_id=workbook.file_hash,
        sheet_name=sheet_name,
        sheet_index=sheet_index,
        row_count=row_count,
        column_count=int(preview.shape[1]),
        inferred_type=inferred,
        header_row=header,
        headers=headers,
        preview=preview if not is_empty else None,
        warnings=warnings,
        is_empty=is_empty,
        is_hidden=workbook.is_hidden(sheet_name),
        selectable=True,
        classification_reason=reason,
    )
    _PREVIEW_CACHE[key] = info
    _prune(_PREVIEW_CACHE)
    return info


def load_excel_sheet(
    workbook: WorkbookInfo,
    sheet_name: str,
    *,
    source: Optional[ExcelSource] = None,
    header: Union[int, Sequence[int], None] = 0,
    header_fill: str = "merged",
    sheet_type: Optional[str] = None,
) -> TableInfo:
    """Fully load one worksheet into a :class:`TableInfo` with worksheet provenance.

    Raises :class:`LoaderError` for empty sheets (they cannot become a table) — the
    UIs handle that by keeping the sheet selectable and disabling plotting.
    """
    data = _bytes_for(workbook, source)
    try:
        sheet_index = workbook.sheet_names.index(sheet_name)
    except ValueError:
        raise LoaderError(f"Worksheet '{sheet_name}' is not in workbook '{workbook.source_filename}'.")

    display = f"{workbook.source_filename} [{sheet_name}]"
    info = load_table(
        io.BytesIO(data),
        source_name=display,
        file_type=workbook.workbook_format,
        sheet_name=sheet_name,
        header=header,
        header_fill=header_fill,
    )
    # Attach provenance for specs/exports/filenames.
    info.source_workbook_name = workbook.source_filename
    info.source_workbook_hash = workbook.file_hash
    info.source_sheet_name = sheet_name
    info.source_sheet_index = sheet_index
    info.source_header_row = header
    if sheet_type is None:
        try:
            sheet_type, _ = classify_worksheet(info.dataframe, header_present=header is not None)
        except Exception:  # pragma: no cover - defensive
            sheet_type = None
    info.source_sheet_type = sheet_type
    if workbook.is_hidden(sheet_name):
        info.warnings.insert(0, f"'{sheet_name}' is a hidden worksheet.")
    return info


# --------------------------------------------------------------------------- #
# Output naming
# --------------------------------------------------------------------------- #

_INVALID_PATH_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# Windows reserved device names (case-insensitive), which are invalid as files.
_RESERVED_NAMES = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


def sanitize_sheet_name_for_path(name: str, *, fallback: str = "sheet") -> str:
    """Turn a worksheet/workbook name into a cross-platform-safe path component.

    Preserves readability (keeps letters, digits, spaces→underscores, dashes) while
    removing characters that are invalid on Windows/macOS/Linux, collapsing runs,
    trimming trailing dots/spaces, and avoiding reserved device names.
    """
    if name is None:
        return fallback
    # Normalize unicode so accented names stay readable but path-safe.
    text = unicodedata.normalize("NFKC", str(name)).strip()
    text = _INVALID_PATH_CHARS.sub("_", text)
    text = text.replace(os.sep, "_")
    if os.altsep:
        text = text.replace(os.altsep, "_")
    # Collapse whitespace to single underscores; collapse repeated underscores.
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"_+", "_", text)
    # Windows disallows trailing dots/spaces.
    text = text.strip(" ._")
    if not text:
        return fallback
    if text.lower() in _RESERVED_NAMES:
        text = f"{text}_sheet"
    # Keep names reasonable for path length limits.
    return text[:120]


def make_sheet_output_slug(
    workbook_name: Optional[str],
    sheet_name: Optional[str],
    *,
    existing: Optional[set] = None,
) -> str:
    """Build a readable, unique per-sheet filename stem.

    ``existing`` is an optional set of already-used slugs; when a collision occurs
    (e.g. two sheets whose names sanitize identically) a numeric suffix is added so
    outputs from different sheets never overwrite one another.
    """
    slug = sanitize_sheet_name_for_path(sheet_name or workbook_name or "sheet")
    if existing is None:
        return slug
    candidate, i = slug, 2
    while candidate in existing:
        candidate = f"{slug}_{i}"
        i += 1
    existing.add(candidate)
    return candidate


def sheet_output_dir(workbook_name: Optional[str], sheet_name: Optional[str]) -> str:
    """Relative ``<workbook>/<sheet>`` output directory (sanitized components)."""
    wb = sanitize_sheet_name_for_path(
        os.path.splitext(workbook_name or "workbook")[0], fallback="workbook"
    )
    sh = sanitize_sheet_name_for_path(sheet_name or "sheet")
    return os.path.join(wb, sh)


def output_basename(
    workbook_name: Optional[str],
    sheet_name: Optional[str],
    plot_type: Optional[str] = None,
) -> str:
    """Filename stem for exports, e.g. ``Sol_24M_vs_6M_volcano``.

    Falls back to the workbook stem when there is no sheet (CSV/single-table).
    """
    stem = sanitize_sheet_name_for_path(
        sheet_name or os.path.splitext(workbook_name or "figure")[0],
        fallback="figure",
    )
    return f"{stem}_{plot_type}" if plot_type else stem
