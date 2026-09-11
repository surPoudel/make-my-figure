"""Open, verify and reconstruct a portable figure package.

Order of operations in :func:`open_figure_package` (all before any data are used):

1. container scan (path traversal, links, size and ratio limits);
2. ``manifest.json`` present, parseable, valid against the JSON Schema;
3. package format + version supported by this reader;
4. every file listed in the manifest exists, has the recorded byte size and
   SHA-256, and no unlisted file is present;
5. tables decoded from their lossless mmftable documents, specs parsed, assets
   copied into a fresh managed directory under sanitised names.

Any failure raises a :class:`PackageError` subclass with a message meant for
the user; no traceback needs to reach the GUI.
"""
from __future__ import annotations

import io
import json
import os
import tempfile
import zipfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from make_my_figure_core.package import manifest as M
from make_my_figure_core.package.security import (
    MAX_MANIFEST_BYTES,
    PackageSecurityError,
    read_member,
    safe_basename,
    scan_zip,
)
from make_my_figure_core.package.tabledata import TableEncodingError, table_from_json_bytes


class PackageError(Exception):
    """Base class: the package cannot be opened. ``str(exc)`` is user-facing."""


class PackageFormatError(PackageError):
    """Not a figure package, corrupt container, invalid manifest or missing part."""


class PackageIntegrityError(PackageError):
    """Contents differ from what the manifest recorded (checksum/size mismatch)."""


class PackageVersionError(PackageError):
    """Package format version not supported by this software."""


@dataclass
class PackageTable:
    table_id: str
    role: str
    dataframe: pd.DataFrame
    meta: Dict[str, Any]

    @property
    def display_name(self) -> str:
        return self.meta.get("display_name") or self.table_id


@dataclass
class FigurePackage:
    path: Optional[str]
    manifest: Dict[str, Any]
    tables: Dict[str, PackageTable]
    specs: Dict[str, Any]                     # key -> parsed JSON (plot_spec, stats_spec, matrix_spec, ...)
    panel_specs: Dict[str, Dict[str, Any]]    # component_id -> {"plot_spec":..., "stats_spec":..., "panel":...}
    assets_dir: Optional[str]
    asset_paths: Dict[str, str]               # manifest asset path -> extracted file path
    previews: Dict[str, bytes] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    integrity: str = "verified"

    # convenience -----------------------------------------------------------
    @property
    def kind(self) -> str:
        return self.manifest["figure_kind"]

    @property
    def name(self) -> str:
        return self.manifest.get("name", "figure")

    @property
    def components(self) -> List[Dict[str, Any]]:
        return list(self.manifest.get("components", []))

    @property
    def plot_spec(self) -> Optional[Dict[str, Any]]:
        return self.specs.get("plot_spec")

    @property
    def stats_payload(self) -> Optional[Dict[str, Any]]:
        return self.specs.get("stats_spec")

    @property
    def matrix_spec(self) -> Optional[Dict[str, Any]]:
        return self.specs.get("matrix_spec")

    @property
    def sample_metadata_spec(self) -> Optional[Dict[str, Any]]:
        return self.specs.get("sample_metadata_spec")

    @property
    def preprocessing_spec(self) -> Optional[Dict[str, Any]]:
        return self.specs.get("preprocessing_spec")

    @property
    def figure_spec(self) -> Optional[Dict[str, Any]]:
        return self.specs.get("figure_spec")

    def component(self, component_id: str) -> Dict[str, Any]:
        for c in self.components:
            if c["component_id"] == component_id:
                return c
        raise KeyError(component_id)

    def primary_component(self) -> Dict[str, Any]:
        return self.components[0]

    def table_for(self, component: Dict[str, Any]) -> Optional[PackageTable]:
        tid = component.get("table_id")
        return self.tables.get(tid) if tid else None

    def aux_for(self, component: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        return {name: self.tables[tid].dataframe for name, tid in (component.get("aux_tables") or {}).items()
                if tid in self.tables}

    def source_table(self) -> Optional[PackageTable]:
        """The original (pre-preprocessing) table when the package has one."""
        for t in self.tables.values():
            if t.role == "source_table":
                return t
        return None

    def derived_table(self) -> Optional[PackageTable]:
        for t in self.tables.values():
            if t.role == "derived_table":
                return t
        return None

    def summary_lines(self) -> List[str]:
        m = self.manifest
        out = [f"{m.get('name')} — {m.get('figure_kind').replace('_', ' ')}",
               f"created {m.get('created_at')} with Make My Figure {m['created_with'].get('version')}",
               f"{len(self.tables)} table(s), {len(m.get('assets', []))} asset(s), "
               f"{len(m.get('components', []))} component(s); specs: {', '.join(sorted(m.get('specs', {})))}"]
        return out


def _open_zip(src: Union[str, bytes, io.BytesIO]) -> zipfile.ZipFile:
    try:
        if isinstance(src, (bytes, bytearray)):
            return zipfile.ZipFile(io.BytesIO(src), "r")
        if isinstance(src, io.BytesIO):
            return zipfile.ZipFile(src, "r")
        if not os.path.isfile(src):
            raise PackageFormatError(f"The file does not exist: {src}")
        return zipfile.ZipFile(src, "r")
    except zipfile.BadZipFile as exc:
        raise PackageFormatError("This file is not a Make My Figure package (not a valid ZIP container).") from exc


def _read_manifest(zf: zipfile.ZipFile) -> Dict[str, Any]:
    names = {zi.filename for zi in zf.infolist()}
    if M.MANIFEST_NAME not in names:
        raise PackageFormatError("This file is not a Make My Figure package: manifest.json is missing.")
    try:
        raw = read_member(zf, M.MANIFEST_NAME, limit=MAX_MANIFEST_BYTES)
        manifest = json.loads(raw.decode("utf-8"))
    except PackageSecurityError as exc:
        raise PackageFormatError(str(exc)) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageFormatError(f"The package manifest is not valid JSON ({exc}).") from exc
    if not isinstance(manifest, dict) or manifest.get("package_format") != M.PACKAGE_FORMAT:
        raise PackageFormatError("This file is not a Make My Figure figure package "
                                 f"(package_format={manifest.get('package_format')!r} if isinstance(manifest, dict) else 'n/a').")
    ver = manifest.get("format_version")
    if not isinstance(ver, int):
        raise PackageFormatError("The package manifest has no valid format_version.")
    if ver not in M.SUPPORTED_FORMAT_VERSIONS:
        if ver > max(M.SUPPORTED_FORMAT_VERSIONS):
            raise PackageVersionError(
                f"This package was written in format version {ver}, which is newer than this version of "
                f"Make My Figure understands (up to {max(M.SUPPORTED_FORMAT_VERSIONS)}). Update the application.")
        raise PackageVersionError(f"Package format version {ver} is no longer supported.")
    errors = M.validate_manifest(manifest)
    if errors:
        raise PackageFormatError("The package manifest is invalid: " + "; ".join(errors[:4]))
    return manifest


def inspect_figure_package(src: Union[str, bytes]) -> Dict[str, Any]:
    """Return the validated manifest without loading tables or verifying checksums."""
    try:
        with _open_zip(src) as zf:
            scan_zip(zf)
            return _read_manifest(zf)
    except PackageSecurityError as exc:
        raise PackageFormatError(f"The package was rejected for safety: {exc}") from exc


def open_figure_package(src: Union[str, bytes], *, assets_dir: Optional[str] = None,
                        load_previews: bool = False) -> FigurePackage:
    """Open, verify and load a package. Raises :class:`PackageError` on any problem."""
    path = src if isinstance(src, str) else None
    try:
        with _open_zip(src) as zf:
            members = {zi.filename: zi for zi in scan_zip(zf)}
            manifest = _read_manifest(zf)
            listed = {f["path"]: f for f in manifest["files"]}
            # --- 4. integrity ----------------------------------------------------
            missing = [p for p in listed if p not in members]
            if missing:
                raise PackageFormatError("The package is incomplete; missing: " + ", ".join(missing[:5]))
            unlisted = [n for n in members if n not in listed and n != M.MANIFEST_NAME]
            if unlisted:
                raise PackageIntegrityError(
                    "Package integrity check failed: the container holds files that are not recorded in the "
                    "manifest: " + ", ".join(unlisted[:5]))
            blobs: Dict[str, bytes] = {}
            for p, rec in listed.items():
                data = read_member(zf, p)
                if len(data) != int(rec["bytes"]) or M.sha256_bytes(data) != rec["sha256"]:
                    raise PackageIntegrityError(
                        "Package integrity check failed: data differ from the values recorded when the package "
                        f"was created ({p}). The package was modified after it was saved and cannot be trusted.")
                blobs[p] = data
    except PackageSecurityError as exc:
        raise PackageFormatError(f"The package was rejected for safety: {exc}") from exc

    warnings: List[str] = list(manifest.get("warnings", []))
    # --- 5. tables -----------------------------------------------------------
    tables: Dict[str, PackageTable] = {}
    for t in manifest["tables"]:
        try:
            df = table_from_json_bytes(blobs[t["path"]])
        except (TableEncodingError, KeyError, ValueError) as exc:
            raise PackageFormatError(f"Table {t['table_id']!r} could not be decoded: {exc}") from exc
        if df.shape != (int(t["n_rows"]), int(t["n_columns"])):
            raise PackageIntegrityError(f"Table {t['table_id']!r} has shape {df.shape}, manifest says "
                                        f"({t['n_rows']}, {t['n_columns']}).")
        tables[t["table_id"]] = PackageTable(t["table_id"], t["role"], df, t)
    # --- specs ---------------------------------------------------------------
    specs: Dict[str, Any] = {}
    for key, p in manifest.get("specs", {}).items():
        specs[key] = _json(blobs, p, key)
    panel_specs: Dict[str, Dict[str, Any]] = {}
    for c in manifest["components"]:
        entry: Dict[str, Any] = {}
        if c.get("plot_spec"):
            entry["plot_spec"] = _json(blobs, c["plot_spec"], f"{c['component_id']} plot_spec")
        if c.get("stats_spec"):
            entry["stats_spec"] = _json(blobs, c["stats_spec"], f"{c['component_id']} stats_spec")
        prec = f"panels/{c['component_id']}/panel.json"
        if prec in blobs:
            entry["panel"] = _json(blobs, prec, f"{c['component_id']} panel record")
        panel_specs[c["component_id"]] = entry
    # --- assets -> managed directory ---------------------------------------------
    asset_paths: Dict[str, str] = {}
    if manifest.get("assets"):
        assets_dir = assets_dir or tempfile.mkdtemp(prefix="mmf_package_assets_")
        os.makedirs(assets_dir, exist_ok=True)
        for a in manifest["assets"]:
            fname = safe_basename(os.path.basename(a["path"]))
            dest = os.path.join(assets_dir, fname)
            n = 1
            while os.path.exists(dest):
                stem, ext = os.path.splitext(fname)
                dest = os.path.join(assets_dir, f"{stem}_{n}{ext}")
                n += 1
            with open(dest, "wb") as fh:
                fh.write(blobs[a["path"]])
            asset_paths[a["path"]] = dest
    previews = {}
    if load_previews:
        for pv in manifest.get("previews", []):
            previews[pv["format"]] = blobs[pv["path"]]
    pkg = FigurePackage(path=path, manifest=manifest, tables=tables, specs=specs, panel_specs=panel_specs,
                        assets_dir=assets_dir if asset_paths else None, asset_paths=asset_paths,
                        previews=previews, warnings=warnings, integrity="verified")
    # cross-checks
    for c in manifest["components"]:
        if c.get("table_id") and c["table_id"] not in tables:
            raise PackageFormatError(f"Component {c['component_id']} references table {c['table_id']!r}, "
                                     "which is not in the package.")
        if c.get("asset") and c["asset"] not in asset_paths:
            raise PackageFormatError(f"Component {c['component_id']} references an asset that is not in the package.")
    return pkg


def _json(blobs: Dict[str, bytes], path: str, what: str) -> Any:
    if path not in blobs:
        raise PackageFormatError(f"The package is incomplete: {what} ({path}) is missing.")
    try:
        return json.loads(blobs[path].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageFormatError(f"{what} is not valid JSON ({exc}).") from exc


# --------------------------------------------------------------------------------
# reconstruction helpers
# --------------------------------------------------------------------------------
def single_plot_inputs(pkg: FigurePackage) -> Tuple[Dict[str, Any], pd.DataFrame, Dict[str, pd.DataFrame]]:
    """``(plot_spec, table, aux)`` for a single-plot package."""
    if pkg.kind != "single_plot":
        raise PackageFormatError("This package holds a multi-panel figure, not a single plot.")
    comp = pkg.primary_component()
    spec = pkg.plot_spec or pkg.panel_specs.get(comp["component_id"], {}).get("plot_spec")
    if not spec:
        raise PackageFormatError("The package has no plot specification.")
    tbl = pkg.table_for(comp)
    if tbl is None:
        raise PackageFormatError("The package has no data table for the plot.")
    from make_my_figure_core.styles.engine import normalize_style_name

    spec = json.loads(json.dumps(spec))
    if spec.get("journal_style"):
        spec["journal_style"] = normalize_style_name(spec["journal_style"])
    return spec, tbl.dataframe, pkg.aux_for(comp)


def rebuild_composite(pkg: FigurePackage):
    """Rebuild a :class:`MultiPanelFigure` (tables attached) from a composite package."""
    from make_my_figure_core.panels import FigureLayout, MultiPanelFigure, panel_from_dict

    if pkg.kind != "composite":
        raise PackageFormatError("This package holds a single plot, not a multi-panel figure.")
    fig_d = (pkg.figure_spec or {}).get("figure") or {}
    layout = FigureLayout.from_dict(fig_d.get("layout") or {})
    panels = []
    for c in pkg.components:
        rec = dict(pkg.panel_specs.get(c["component_id"], {}).get("panel") or {})
        if c.get("asset"):
            rec["image_path"] = os.path.basename(pkg.asset_paths[c["asset"]])
            panel = panel_from_dict(rec, assets_dir=os.path.dirname(pkg.asset_paths[c["asset"]]))
        else:
            rec.setdefault("plot_spec", pkg.panel_specs.get(c["component_id"], {}).get("plot_spec"))
            panel = panel_from_dict(rec)
            tbl = pkg.table_for(c)
            if tbl is None:
                raise PackageFormatError(f"Panel {c['component_id']} has no data table in the package.")
            panel.table = tbl.dataframe
            panel.aux = pkg.aux_for(c)
        panel.width_in = c.get("width_in", panel.width_in)
        panel.height_in = c.get("height_in", panel.height_in)
        panel.title = c.get("title") or panel.title
        panels.append(panel)
    mpf = MultiPanelFigure(name=fig_d.get("name") or pkg.name, panels=panels, layout=layout,
                           legend_text=fig_d.get("legend_text", ""))
    mpf.autolabel()
    return mpf


def _close(a: Any, b: Any, rel: float = 1e-9) -> bool:
    import math

    if a is None or b is None:
        return a is None and b is None
    try:
        fa, fb = float(a), float(b)
    except (TypeError, ValueError):
        return a == b
    if math.isnan(fa) and math.isnan(fb):
        return True
    return math.isclose(fa, fb, rel_tol=rel, abs_tol=1e-300)


def verify_statistics(stored_payload: Optional[Dict[str, Any]], report: Any) -> List[str]:
    """Compare a fresh StatsReport with the statistics stored in the package.

    Returns human-readable discrepancies (empty when identical). The frozen data
    make the deterministic tests reproduce exactly; any difference means the
    statistics engine changed between versions and the user must be told.
    """
    if not stored_payload:
        return [] if report is None else ["statistics were computed but the package stored no StatsSpec"]
    if report is None:
        return ["the package stores statistics but none were computed on reopening"]
    stored = stored_payload.get("results") or []
    fresh = [r.to_dict() for r in report.results]
    problems: List[str] = []
    if len(stored) != len(fresh):
        problems.append(f"{len(stored)} stored result(s) vs {len(fresh)} recomputed")
    for s, f in zip(stored, fresh):
        for key in ("test_id", "group_a", "group_b", "n_total", "correction_method", "effect_size_name"):
            if s.get(key) != f.get(key):
                problems.append(f"{key}: stored {s.get(key)!r} vs recomputed {f.get(key)!r}")
        for key in ("statistic", "p_value", "adjusted_p_value", "effect_size", "effect_ci_low", "effect_ci_high"):
            if not _close(s.get(key), f.get(key)):
                problems.append(f"{s.get('group_a')} vs {s.get('group_b')} {key}: stored {s.get(key)} vs recomputed {f.get(key)}")
    return problems


def verify_preprocessing(pkg: FigurePackage, *, max_cells: int = 5_000_000) -> Dict[str, Any]:
    """Re-run the stored PreprocessingSpec on the frozen source table and compare with
    the frozen derived table. Returns ``{"status": ..., "detail": ...}``.

    Status values: ``"identical"``, ``"differs"``, ``"skipped"`` (no records / too large),
    ``"error"``. The frozen derived table is always what the figure is drawn from; this
    check only tells the user whether the recorded chain still reproduces it.
    """
    ps = pkg.preprocessing_spec
    src = pkg.source_table()
    der = pkg.derived_table()
    if not ps or src is None or der is None or not pkg.matrix_spec:
        return {"status": "skipped", "detail": "no preprocessing record to verify"}
    if src.dataframe.size > max_cells:
        return {"status": "skipped", "detail": "source matrix too large for the automatic check"}
    try:
        import numpy as np

        import make_my_figure_core.matrix_workflow as mw

        mspec = mw.MatrixSpec.from_dict(pkg.matrix_spec)
        # the stored MatrixSpec is the *derived* spec when preprocessing ran; take the source columns from the record
        src_spec = mw.MatrixSpec.from_dict({**pkg.matrix_spec,
                                            "value_columns": ps.get("value_columns") or mspec.value_columns,
                                            "feature_id_column": ps.get("feature_id_column") or mspec.feature_id_column})
        meta = mw.SampleMetadataSpec.from_dict(pkg.sample_metadata_spec) if pkg.sample_metadata_spec else None
        steps = [{"method": s.get("method_name"), "params": _replay_params(s)} for s in ps.get("preprocessing_steps", [])]
        final_df, _dspec, _ps = mw.run_preprocessing(src.dataframe, src_spec, steps, metadata=meta,
                                                     output_matrix_id=ps.get("output_matrix_id") or "processed")
        a, b = final_df, der.dataframe
        if list(a.columns) != list(b.columns) or a.shape != b.shape:
            return {"status": "differs", "detail": f"shape/columns differ: {a.shape} vs {b.shape}"}
        num = a.select_dtypes("number").columns
        for c in num:
            x, y = a[c].to_numpy(dtype="float64"), b[c].to_numpy(dtype="float64")
            if not np.array_equal(x, y, equal_nan=True):
                if np.allclose(x, y, rtol=1e-10, atol=1e-12, equal_nan=True):
                    return {"status": "identical", "detail": f"values agree to 1e-10 relative (column {c} differs only in the last bits)"}
                return {"status": "differs", "detail": f"column {c!r} differs (max |Δ| = {np.nanmax(np.abs(x - y)):.3g})"}
        for c in [c for c in a.columns if c not in num]:
            if not a[c].astype(str).equals(b[c].astype(str)):
                return {"status": "differs", "detail": f"column {c!r} differs"}
        return {"status": "identical", "detail": "re-running the recorded preprocessing reproduces the frozen derived matrix"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "detail": f"could not re-run the preprocessing record: {exc}"}


def _replay_params(step: Dict[str, Any]) -> Dict[str, Any]:
    """Parameters to pass when replaying a recorded step.

    Records written by v1.1.1+ carry ``user_parameters`` (exactly what was requested).
    Older records only have ``parameters`` (requested values merged with what the method
    reported back), so keep only the keys the method's signature accepts.
    """
    if "user_parameters" in step and isinstance(step["user_parameters"], dict):
        return dict(step["user_parameters"])
    params = dict(step.get("parameters") or {})
    method = step.get("method_name")
    try:
        import inspect

        from make_my_figure_core.matrix_workflow import preprocessing as _pp

        if method == "zscore" or method in _pp._ZSCORE:
            return {k: v for k, v in params.items() if k in ("axis", "ddof")}
        fn = _pp._REGISTRY[method][0]
        sig = inspect.signature(fn)
        if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
            return params
        return {k: v for k, v in params.items() if k in sig.parameters and k not in ("df", "matrix_spec")}
    except Exception:  # noqa: BLE001
        return params
