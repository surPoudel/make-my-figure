"""Table loaders for CSV, TSV, and XLSX inputs.

Design goals (from the master prompt, Phase 2):

* infer delimiters for delimited text,
* preserve sample-ID-like columns as strings (never silently coerce to int),
* detect numeric columns,
* report missing values,
* surface clear validation messages instead of failing silently.
"""

from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass, field
from typing import Any, BinaryIO, Dict, List, Optional, Union

import pandas as pd


class LoaderError(Exception):
    """Raised when a table cannot be loaded or is structurally invalid."""


@dataclass
class TableInfo:
    """A loaded table plus the metadata the app needs to validate mappings."""

    dataframe: pd.DataFrame
    source_name: str
    delimiter: Optional[str]
    numeric_columns: List[str] = field(default_factory=list)
    categorical_columns: List[str] = field(default_factory=list)
    missing_value_counts: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    @property
    def columns(self) -> List[str]:
        return list(self.dataframe.columns)

    @property
    def n_rows(self) -> int:
        return int(len(self.dataframe))

    def summary(self) -> Dict[str, Any]:
        return {
            "source_name": self.source_name,
            "delimiter": self.delimiter,
            "n_rows": self.n_rows,
            "n_columns": len(self.columns),
            "columns": self.columns,
            "numeric_columns": self.numeric_columns,
            "categorical_columns": self.categorical_columns,
            "missing_value_counts": self.missing_value_counts,
            "warnings": self.warnings,
        }


# Column names that look like identifiers should stay textual even when their
# values happen to be all digits, so that "001" never becomes 1.
_ID_HINTS = ("id", "sample", "patient", "barcode", "accession", "replicate")

_DELIMITER_CANDIDATES = [",", "\t", ";", "|"]


def _looks_like_id_column(name: str) -> bool:
    lowered = str(name).lower()
    return any(hint in lowered for hint in _ID_HINTS)


def _sniff_delimiter(sample_text: str, ext: str) -> str:
    """Guess the field delimiter from a text sample.

    Falls back to the extension hint (.tsv -> tab) and finally a comma.
    """
    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters="".join(_DELIMITER_CANDIDATES))
        return dialect.delimiter
    except (csv.Error, Exception):  # pragma: no cover - defensive
        pass

    # Heuristic: pick the candidate with the most consistent per-line count.
    lines = [ln for ln in sample_text.splitlines() if ln.strip()][:20]
    best_delim, best_score = None, -1.0
    for cand in _DELIMITER_CANDIDATES:
        counts = [ln.count(cand) for ln in lines]
        if not counts or max(counts) == 0:
            continue
        # reward many columns and penalise inconsistency
        consistency = 1.0 if len(set(counts)) == 1 else 0.5
        score = max(counts) * consistency
        if score > best_score:
            best_delim, best_score = cand, score
    if best_delim is not None:
        return best_delim
    return "\t" if ext == ".tsv" else ","


def _classify_columns(df: pd.DataFrame) -> tuple[List[str], List[str]]:
    numeric, categorical = [], []
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]) and not _looks_like_id_column(col):
            numeric.append(col)
        else:
            categorical.append(col)
    return numeric, categorical


def _post_process(df: pd.DataFrame, source_name: str, delimiter: Optional[str]) -> TableInfo:
    if df.shape[1] == 0:
        raise LoaderError(f"'{source_name}' has no columns; check the delimiter or file content.")
    if df.shape[0] == 0:
        raise LoaderError(f"'{source_name}' has no data rows.")

    warnings: List[str] = []

    # Strip whitespace from string-like column names.
    df.columns = [str(c).strip() for c in df.columns]

    # Detect duplicate column names, which break mapping by name.
    seen, dups = set(), set()
    for c in df.columns:
        if c in seen:
            dups.add(c)
        seen.add(c)
    if dups:
        warnings.append(f"Duplicate column names found: {sorted(dups)}")

    numeric, categorical = _classify_columns(df)

    missing = {c: int(df[c].isna().sum()) for c in df.columns if df[c].isna().any()}
    if missing:
        warnings.append(
            "Missing values detected in: "
            + ", ".join(f"{c} ({n})" for c, n in missing.items())
        )

    return TableInfo(
        dataframe=df,
        source_name=source_name,
        delimiter=delimiter,
        numeric_columns=numeric,
        categorical_columns=categorical,
        missing_value_counts=missing,
        warnings=warnings,
    )


def _id_dtype_overrides(columns: List[str]) -> Dict[str, str]:
    return {c: "string" for c in columns if _looks_like_id_column(c)}


def _read_delimited(buffer: Union[str, bytes], source_name: str, ext: str) -> TableInfo:
    if isinstance(buffer, bytes):
        text = buffer.decode("utf-8-sig")
    else:
        text = buffer
    if not text.strip():
        raise LoaderError(f"'{source_name}' is empty.")

    sample = "\n".join(text.splitlines()[:50])
    delimiter = _sniff_delimiter(sample, ext)

    # Two-pass read: first read headers to know which columns are IDs, then
    # re-read forcing those columns to stay strings.
    header_df = pd.read_csv(io.StringIO(text), sep=delimiter, nrows=0, engine="python")
    dtype = _id_dtype_overrides(list(header_df.columns))

    try:
        df = pd.read_csv(io.StringIO(text), sep=delimiter, dtype=dtype, engine="python")
    except Exception as exc:  # pragma: no cover - defensive
        raise LoaderError(f"Failed to parse '{source_name}' with delimiter {delimiter!r}: {exc}") from exc

    return _post_process(df, source_name, delimiter)


def _read_excel(source: Union[str, BinaryIO], source_name: str, sheet_name: Optional[Union[str, int]]) -> TableInfo:
    try:
        # Read once to discover columns, then re-read forcing ID columns to str.
        probe = pd.read_excel(source, sheet_name=sheet_name if sheet_name is not None else 0, nrows=0)
        if hasattr(source, "seek"):
            source.seek(0)
        dtype = _id_dtype_overrides(list(probe.columns))
        df = pd.read_excel(
            source,
            sheet_name=sheet_name if sheet_name is not None else 0,
            dtype=dtype,
        )
    except Exception as exc:
        raise LoaderError(f"Failed to read Excel file '{source_name}': {exc}") from exc

    if isinstance(df, dict):  # multiple sheets returned
        raise LoaderError(
            f"'{source_name}' returned multiple sheets; pass sheet_name to choose one of {list(df.keys())}."
        )
    return _post_process(df, source_name, delimiter=None)


def load_table(
    source: Union[str, os.PathLike, bytes, BinaryIO],
    *,
    source_name: Optional[str] = None,
    file_type: Optional[str] = None,
    sheet_name: Optional[Union[str, int]] = None,
) -> TableInfo:
    """Load a CSV/TSV/XLSX table into a :class:`TableInfo`.

    Parameters
    ----------
    source:
        A filesystem path, raw bytes, or a binary file-like object (e.g. a
        Streamlit ``UploadedFile``).
    source_name:
        Display name; inferred from a path when not given.
    file_type:
        One of ``csv``/``tsv``/``xlsx``/``xls``. Inferred from the extension
        when not given. Required when passing raw bytes without a name.
    sheet_name:
        Excel sheet selector (defaults to the first sheet).
    """
    # Resolve a name and extension.
    if isinstance(source, (str, os.PathLike)):
        path = os.fspath(source)
        source_name = source_name or os.path.basename(path)
        ext = os.path.splitext(path)[1].lower()
    else:
        name_for_ext = source_name or getattr(source, "name", "") or ""
        source_name = source_name or (name_for_ext if name_for_ext else "uploaded_table")
        ext = os.path.splitext(name_for_ext)[1].lower()

    if file_type:
        ext = "." + file_type.lower().lstrip(".")

    excel_exts = {".xlsx", ".xls", ".xlsm"}
    delimited_exts = {".csv", ".tsv", ".txt", ".tab"}

    if ext in excel_exts:
        if isinstance(source, (str, os.PathLike)):
            return _read_excel(os.fspath(source), source_name, sheet_name)
        if isinstance(source, bytes):
            return _read_excel(io.BytesIO(source), source_name, sheet_name)
        return _read_excel(source, source_name, sheet_name)

    if ext not in delimited_exts and ext not in excel_exts:
        # Unknown extension: attempt delimited parsing but warn.
        if ext:
            note = f"Unrecognised extension '{ext}'; attempting delimited text parsing."
        else:
            note = "No file extension; attempting delimited text parsing."
        if isinstance(source, (str, os.PathLike)):
            with open(source, "rb") as fh:
                info = _read_delimited(fh.read(), source_name, ext or ".csv")
        elif isinstance(source, bytes):
            info = _read_delimited(source, source_name, ext or ".csv")
        else:
            info = _read_delimited(source.read(), source_name, ext or ".csv")
        info.warnings.insert(0, note)
        return info

    # Delimited text path.
    if isinstance(source, (str, os.PathLike)):
        with open(source, "rb") as fh:
            return _read_delimited(fh.read(), source_name, ext)
    if isinstance(source, bytes):
        return _read_delimited(source, source_name, ext)
    return _read_delimited(source.read(), source_name, ext)
