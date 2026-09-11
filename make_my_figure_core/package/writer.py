"""Assemble and write a portable figure package (.mmfpackage).

Frontend-independent. A frontend describes *what was on screen* with a
:class:`PackageContent` (specs, the exact tables the renderer received, the
matrix-workflow records, imported assets, the rendered figure) and this module
freezes it into one ZIP container with a manifest and SHA-256 for every file.

Nothing here mutates any user file: source files are read and copied only.
"""
from __future__ import annotations

import io
import os
import re
import zipfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from make_my_figure_core.package import manifest as M
from make_my_figure_core.package.tabledata import table_summary, table_to_json_bytes

# Above this the original source file is still copied but the package reports it as large.
LARGE_PACKAGE_WARN_BYTES = 200 * 1024 ** 2
# Original source files above this size are not copied (the frozen canonical table is what
# reproduces the figure; the file is recorded by name and SHA-256 instead).
MAX_ORIGINAL_COPY_BYTES = 512 * 1024 ** 2
# Human-readable CSV copies are added for tables up to this many cells.
CSV_COPY_MAX_CELLS = 2_000_000


class PackageWriteError(ValueError):
    pass


@dataclass
class TableSource:
    """One table to freeze into the package."""

    table_id: str
    dataframe: pd.DataFrame
    role: str = "source_table"                 # source_table | derived_table | aux_table | metadata_table
    display_name: Optional[str] = None         # the PlotSpec's input_table label
    original_path: Optional[str] = None        # file the table was read from (copied for provenance)
    sheet_name: Optional[str] = None
    header_row: Optional[int] = None
    provenance: Dict[str, Any] = field(default_factory=dict)
    derived_from: Optional[str] = None         # table_id of the table this one was computed from
    include_original_file: bool = True
    # In-memory original (browser uploads have no path): included as the original source file.
    original_bytes: Optional[bytes] = None
    original_filename: Optional[str] = None


@dataclass
class AssetSource:
    asset_id: str
    path: str                                  # file on disk to copy
    component_id: Optional[str] = None
    original_filename: Optional[str] = None
    media_type: Optional[str] = None


@dataclass
class PlotComponent:
    """A rendered plot: the whole figure (single) or one panel (composite)."""

    component_id: str
    plot_spec: Optional[Dict[str, Any]] = None
    table_id: Optional[str] = None             # table the renderer receives
    aux_tables: Dict[str, str] = field(default_factory=dict)   # aux name -> table_id
    stats_payload: Optional[Dict[str, Any]] = None   # stats_sidecar_payload(...) when statistics ran
    render_metadata: Dict[str, Any] = field(default_factory=dict)
    kind: str = "plot"                         # plot | make_my_figure_panel | external_figure_panel
    label: str = ""
    title: str = ""
    asset_id: Optional[str] = None             # for imported panels
    panel_record: Optional[Dict[str, Any]] = None   # Panel.to_dict() for composites
    width_in: Optional[float] = None
    height_in: Optional[float] = None


@dataclass
class PackageContent:
    kind: str                                  # single_plot | composite
    name: str
    components: List[PlotComponent]
    tables: List[TableSource]
    assets: List[AssetSource] = field(default_factory=list)
    matrix_spec: Optional[Dict[str, Any]] = None
    sample_metadata_spec: Optional[Dict[str, Any]] = None
    preprocessing_spec: Optional[Dict[str, Any]] = None
    figure_spec: Optional[Dict[str, Any]] = None      # {"figure": MultiPanelFigure.to_dict(), ...}
    preview_figure: Any = None                 # matplotlib Figure to render previews from
    preview_formats: Tuple[str, ...] = ("png", "svg", "pdf")
    preview_dpi: int = 300
    warnings: List[str] = field(default_factory=list)
    record_original_paths: bool = False        # privacy: full paths are NOT recorded unless asked


@dataclass
class WriteReport:
    path: Optional[str]
    n_bytes: int
    manifest: Dict[str, Any]
    warnings: List[str]


_SAFE = re.compile(r"[^A-Za-z0-9._\-]+")


def _safe_component(name: str) -> str:
    s = _SAFE.sub("_", (name or "").strip()).strip("._") or "item"
    return s[:80]


def _media_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".tif": "image/tiff",
            ".tiff": "image/tiff", ".svg": "image/svg+xml", ".pdf": "application/pdf", ".webp": "image/webp",
            ".bmp": "image/bmp", ".csv": "text/csv", ".tsv": "text/tab-separated-values",
            ".txt": "text/plain", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel", ".json": "application/json"}.get(ext, "application/octet-stream")


def default_package_filename(stem: str) -> str:
    return f"{_safe_component(stem) or 'figure'}{M.PACKAGE_EXTENSION}"


def estimate_package_size(content: PackageContent) -> int:
    """Rough uncompressed size in bytes (tables as JSON + original files + assets)."""
    total = 0
    for t in content.tables:
        # ~ 20 bytes per numeric cell in JSON, strings by length
        df = t.dataframe
        total += int(df.shape[0] * df.shape[1] * 20) + 4096
        if t.include_original_file and t.original_path and os.path.isfile(t.original_path):
            total += os.path.getsize(t.original_path)
    for a in content.assets:
        if os.path.isfile(a.path):
            total += os.path.getsize(a.path)
    total += 2 * 1024 * 1024 * (1 if content.preview_figure is not None else 0)
    return total


class _Zip:
    """Collects members + integrity records while writing."""

    def __init__(self) -> None:
        self.buf = io.BytesIO()
        self.zf = zipfile.ZipFile(self.buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6)
        self.files: List[Dict[str, Any]] = []
        self.names: set = set()

    def add(self, path: str, data: bytes, role: str) -> Dict[str, Any]:
        if path in self.names:
            raise PackageWriteError(f"duplicate package path {path!r}")
        self.names.add(path)
        self.zf.writestr(zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0)), data,
                         compress_type=zipfile.ZIP_DEFLATED)
        rec = {"path": path, "sha256": M.sha256_bytes(data), "bytes": len(data), "role": role}
        self.files.append(rec)
        return rec

    def finish(self, manifest: Dict[str, Any]) -> bytes:
        self.zf.writestr(zipfile.ZipInfo(M.MANIFEST_NAME, date_time=(1980, 1, 1, 0, 0, 0)),
                         M.json_bytes(manifest), compress_type=zipfile.ZIP_DEFLATED)
        self.zf.close()
        return self.buf.getvalue()


def build_package_bytes(content: PackageContent) -> Tuple[bytes, Dict[str, Any], List[str]]:
    """Serialise ``content`` to package bytes. Returns ``(bytes, manifest, warnings)``."""
    if content.kind not in ("single_plot", "composite"):
        raise PackageWriteError(f"unknown package kind {content.kind!r}")
    if not content.components:
        raise PackageWriteError("a package needs at least one component")
    warnings: List[str] = list(content.warnings)
    z = _Zip()
    manifest: Dict[str, Any] = {
        "package_format": M.PACKAGE_FORMAT,
        "format_version": M.PACKAGE_FORMAT_VERSION,
        "created_with": {"application": "Make My Figure", "version": M.__version__,
                         "commit": M.build_info().get("commit")},
        "created_at": M.utc_now_iso(),
        "figure_kind": content.kind,
        "name": content.name or "figure",
        "privacy_notice": M.PRIVACY_NOTICE,
        "specs": {},
        "components": [],
        "tables": [],
        "assets": [],
        "previews": [],
        "files": [],
        "relationships": [],
        "environment": M.ENVIRONMENT_PATH,
        "warnings": warnings,
        "compatibility": {"min_reader_format_version": M.PACKAGE_FORMAT_VERSION,
                          "reader_must_verify_checksums": True,
                          "features": []},
    }
    features = set()

    # ---- tables -------------------------------------------------------------
    table_ids = set()
    for t in content.tables:
        if t.table_id in table_ids:
            raise PackageWriteError(f"duplicate table_id {t.table_id!r}")
        table_ids.add(t.table_id)
        tid = _safe_component(t.table_id)
        blob, tw = table_to_json_bytes(t.dataframe)
        warnings.extend(f"table {t.table_id}: {w}" for w in tw)
        rec = z.add(f"data/{tid}.mmftable.json", blob, f"table:{t.role}")
        entry: Dict[str, Any] = {
            "table_id": t.table_id, "role": t.role, "path": rec["path"], "encoding": "mmftable/1",
            "sha256": rec["sha256"], "bytes": rec["bytes"], "content_digest": rec["sha256"],
            "display_name": t.display_name, "derived_from": t.derived_from,
            "provenance": {k: v for k, v in (t.provenance or {}).items() if v is not None},
        }
        entry.update(table_summary(t.dataframe))
        # convenience copy for humans (never used for reconstruction)
        if t.dataframe.shape[0] * max(t.dataframe.shape[1], 1) <= CSV_COPY_MAX_CELLS:
            csv = t.dataframe.to_csv(index=False, float_format="%.17g").encode("utf-8")
            entry["csv_copy"] = z.add(f"data/{tid}.csv", csv, "table_csv_copy")["path"]
        else:
            entry["csv_copy"] = None
        # original source file for provenance
        orig: Optional[Dict[str, Any]] = None
        if t.original_bytes is not None and not t.original_path:
            fname = t.original_filename or f"{tid}_original"
            orig = {"filename": fname, "sheet_name": t.sheet_name, "header_row": t.header_row, "path": None,
                    "sha256": M.sha256_bytes(t.original_bytes), "bytes": len(t.original_bytes), "included": False, "note": None}
            if t.include_original_file and len(t.original_bytes) <= MAX_ORIGINAL_COPY_BYTES:
                rec2 = z.add(f"data/original/{tid}/{M.safe_basename_for_zip(fname)}", t.original_bytes, "original_source_file")
                orig["path"] = rec2["path"]
                orig["included"] = True
                features.add("original_source_file")
        elif t.original_path:
            fname = os.path.basename(t.original_path)
            orig = {"filename": fname, "sheet_name": t.sheet_name, "header_row": t.header_row,
                    "path": None, "sha256": None, "bytes": None, "included": False, "note": None}
            if content.record_original_paths:
                orig["original_location"] = os.path.abspath(t.original_path)
            if os.path.isfile(t.original_path):
                size = os.path.getsize(t.original_path)
                orig["bytes"] = size
                orig["sha256"] = M.sha256_file(t.original_path)
                if t.include_original_file and size <= MAX_ORIGINAL_COPY_BYTES:
                    with open(t.original_path, "rb") as fh:
                        data = fh.read()
                    rec2 = z.add(f"data/original/{tid}/{M.safe_basename_for_zip(fname)}", data, "original_source_file")
                    orig["path"] = rec2["path"]
                    orig["included"] = True
                    features.add("original_source_file")
                elif t.include_original_file:
                    orig["note"] = "original file not copied (larger than the copy limit); recorded by name and SHA-256"
                    warnings.append(f"original file {fname} was not copied (>{MAX_ORIGINAL_COPY_BYTES // 1024 ** 2} MB)")
            else:
                orig["note"] = "original file was not accessible when the package was written"
        entry["original_file"] = orig
        manifest["tables"].append(entry)
        if t.derived_from:
            manifest["relationships"].append({"type": "derived_from", "from": t.table_id, "to": t.derived_from,
                                              "via": "preprocessing_spec.json" if content.preprocessing_spec else None})

    # ---- specs ----------------------------------------------------------------
    if content.kind == "single_plot":
        c0 = content.components[0]
        if not c0.plot_spec:
            raise PackageWriteError("single-plot package needs a plot_spec")
        manifest["specs"]["plot_spec"] = z.add("plot_spec.json", M.json_bytes(c0.plot_spec), "spec:plot_spec")["path"]
        if c0.stats_payload:
            manifest["specs"]["stats_spec"] = z.add("stats_spec.json", M.json_bytes(c0.stats_payload), "spec:stats_spec")["path"]
            features.add("statistics")
        if c0.render_metadata:
            z.add("render_metadata.json", M.json_bytes(c0.render_metadata), "render_metadata")
    else:
        if not content.figure_spec:
            raise PackageWriteError("composite package needs a figure_spec")
        manifest["specs"]["figure_spec"] = z.add("figure_spec.json", M.json_bytes(content.figure_spec), "spec:figure_spec")["path"]
        features.add("composite")
    for key, obj in (("matrix_spec", content.matrix_spec), ("sample_metadata_spec", content.sample_metadata_spec),
                     ("preprocessing_spec", content.preprocessing_spec)):
        if obj:
            manifest["specs"][key] = z.add(f"{key}.json", M.json_bytes(obj), f"spec:{key}")["path"]
            features.add("matrix_workflow")

    # ---- assets ---------------------------------------------------------------
    asset_paths: Dict[str, str] = {}
    for a in content.assets:
        if not os.path.isfile(a.path):
            raise PackageWriteError(f"imported asset is missing: {a.path}")
        with open(a.path, "rb") as fh:
            data = fh.read()
        aname = M.safe_basename_for_zip(os.path.basename(a.path))
        rec = z.add(f"assets/{_safe_component(a.asset_id)}/{aname}", data, "asset")
        asset_paths[a.asset_id] = rec["path"]
        manifest["assets"].append({"asset_id": a.asset_id, "path": rec["path"], "sha256": rec["sha256"],
                                   "bytes": rec["bytes"], "original_filename": a.original_filename or os.path.basename(a.path),
                                   "media_type": a.media_type or _media_type(a.path), "component_id": a.component_id})
        features.add("imported_assets")

    # ---- components -----------------------------------------------------------
    for c in content.components:
        entry = {"component_id": c.component_id, "kind": c.kind if content.kind == "composite" else "plot",
                 "label": c.label or None, "title": c.title or None,
                 "plot_type": (c.plot_spec or {}).get("plot_type"), "plot_spec": None, "stats_spec": None,
                 "table_id": c.table_id, "aux_tables": dict(c.aux_tables), "asset": asset_paths.get(c.asset_id) if c.asset_id else None,
                 "width_in": c.width_in, "height_in": c.height_in}
        if c.table_id and c.table_id not in table_ids:
            raise PackageWriteError(f"component {c.component_id} references unknown table {c.table_id!r}")
        for tid in c.aux_tables.values():
            if tid not in table_ids:
                raise PackageWriteError(f"component {c.component_id} references unknown aux table {tid!r}")
        if content.kind == "single_plot":
            entry["plot_spec"] = manifest["specs"]["plot_spec"]
            entry["stats_spec"] = manifest["specs"].get("stats_spec")
        else:
            cid = _safe_component(c.component_id)
            if c.plot_spec:
                entry["plot_spec"] = z.add(f"panels/{cid}/plot_spec.json", M.json_bytes(c.plot_spec), "spec:plot_spec")["path"]
            if c.stats_payload:
                entry["stats_spec"] = z.add(f"panels/{cid}/stats_spec.json", M.json_bytes(c.stats_payload), "spec:stats_spec")["path"]
                features.add("statistics")
            if c.panel_record is not None:
                z.add(f"panels/{cid}/panel.json", M.json_bytes(c.panel_record), "panel_record")
        manifest["components"].append(entry)

    # ---- previews -------------------------------------------------------------
    if content.preview_figure is not None:
        from make_my_figure_core.plots.registry import figure_to_bytes

        for fmt in content.preview_formats:
            try:
                data = figure_to_bytes(content.preview_figure, fmt, dpi=content.preview_dpi)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"preview {fmt} could not be rendered: {exc}")
                continue
            rec = z.add(f"preview/figure.{fmt}", data, "preview")
            manifest["previews"].append({"path": rec["path"], "format": fmt,
                                         "dpi": content.preview_dpi if fmt in ("png", "tiff") else None})

    # ---- environment + README -------------------------------------------------
    z.add(M.ENVIRONMENT_PATH, M.json_bytes(M.environment_record()), "environment")
    z.add("README.txt", _readme(content, manifest).encode("utf-8"), "readme")

    manifest["compatibility"]["features"] = sorted(features)
    manifest["files"] = z.files
    errors = M.validate_manifest(manifest)
    if errors:
        raise PackageWriteError("internal error: manifest does not validate: " + "; ".join(errors[:5]))
    total = sum(f["bytes"] for f in z.files)
    if total > LARGE_PACKAGE_WARN_BYTES:
        warnings.append(f"large package: {total / 1024 ** 2:.0f} MB of data before compression")
    data = z.finish(manifest)
    return data, manifest, warnings


def write_figure_package(content: PackageContent, dest_path: str) -> WriteReport:
    """Write ``content`` to ``dest_path`` (adds the extension when missing)."""
    if not dest_path.lower().endswith(M.PACKAGE_EXTENSION):
        dest_path = dest_path + M.PACKAGE_EXTENSION
    data, manifest, warnings = build_package_bytes(content)
    tmp = dest_path + ".part"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, dest_path)
    return WriteReport(path=dest_path, n_bytes=len(data), manifest=manifest, warnings=warnings)


def _readme(content: PackageContent, manifest: Dict[str, Any]) -> str:
    lines = [
        "Make My Figure — reproducible figure package",
        "=" * 46,
        f"Name: {manifest['name']}",
        f"Kind: {manifest['figure_kind']}",
        f"Created: {manifest['created_at']} with Make My Figure {manifest['created_with']['version']}",
        "",
        "Open this file in Make My Figure (Open Figure Package) to reproduce the figure.",
        "Everything needed is inside: the plot specification(s), the exact tables used",
        "(data/*.mmftable.json — lossless; data/*.csv are convenience copies), statistics",
        "and preprocessing records when they apply, imported assets, and preview images.",
        "The manifest lists every file with its SHA-256; the application refuses to open a",
        "package whose contents no longer match.",
        "",
        M.PRIVACY_NOTICE,
        "",
        "A .plot_spec.json alone is only the recipe (it needs the source data);",
        "a .mmfpreset.json carries appearance only; this .mmfpackage carries everything.",
    ]
    return "\n".join(lines) + "\n"
