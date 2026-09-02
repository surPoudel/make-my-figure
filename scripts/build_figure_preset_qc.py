"""Figure Preset QC across the live plot registry.

For every registered renderer - enumerated from the registry, never from a list - this script:

1. loads the bundled synthetic example and renders it with defaults;
2. changes at least three meaningful user-facing settings (typography, colour, layout, legend,
   export, and a plot-specific visual option where the type has one);
3. saves a Figure *style* preset and a *full* configuration preset;
4. loads a different dataset of the same plot type (the mock sample when one exists, otherwise the
   example with its numeric values perturbed) into a fresh spec;
5. applies the presets and renders again;
6. verifies each changed setting came back, that the new data stayed the new data, that no value
   from the original table travelled inside the preset, that PNG/PDF/SVG export, and that both the
   PlotSpec and the preset survive a JSON round-trip byte-for-byte.

It writes ``reports/figure_preset_qc/all_plot_preset_matrix.csv`` with one row per plot type and a
PASS / FAIL / N/A per check, plus a README summarising the run. A check is N/A only with a stated
reason (a plot that draws no legend has no legend to round-trip), never silently.

Usage::

    python scripts/build_figure_preset_qc.py            # write the matrix, exit 1 on any FAIL
    python -c "from scripts.build_figure_preset_qc import check_plot; print(check_plot('volcano_plot'))"
"""

from __future__ import annotations

import copy
import csv
import datetime as _dt
import json
import os
import pathlib
import sys
import tempfile
import warnings
from typing import Any, Dict, List, Optional, Tuple

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from make_my_figure_core import data as mock_data  # noqa: E402
from make_my_figure_core import examples as ex  # noqa: E402
from make_my_figure_core import presets as P  # noqa: E402
from make_my_figure_core import ui_hints  # noqa: E402
from make_my_figure_core.io.loaders import load_table  # noqa: E402
from make_my_figure_core.plots.registry import (available_plot_types, export_figure,  # noqa: E402
                                                make_spec, render)
from make_my_figure_core.styles.capabilities import get_style_capabilities  # noqa: E402

OUT_DIR = ROOT / "reports" / "figure_preset_qc"
CSV_PATH = OUT_DIR / "all_plot_preset_matrix.csv"
README_PATH = OUT_DIR / "README.md"

COLUMNS = ["plot_type", "preset_save", "preset_load", "style_roundtrip", "full_config_roundtrip",
           "color_roundtrip", "typography_roundtrip", "layout_roundtrip", "legend_roundtrip",
           "annotation_roundtrip", "plot_specific_roundtrip", "new_data_safe", "png_export",
           "pdf_export", "svg_export", "status", "notes"]

# The universal perturbations. Every value differs from the Publication default.
STYLE_CHANGES = {"title_font_pt": 17.0, "axis_font_pt": 11.0, "annotation_pt": 8.5,
                 "line_width_pt": 2.6, "marker_size": 70.0, "legend_pt": 8.0}
LAYOUT_CHANGES = {"x_tick_rotation": 45, "margin_left": 0.15, "column_width": "double",
                  "legend_location": "outside right"}
OUTPUT_CHANGES = {"dpi": 450}


class _Fail(Exception):
    pass


def _quiet_render(spec, df, aux=None):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return render(spec, df, aux=aux)


def _aux_frames(aux) -> Optional[Dict[str, pd.DataFrame]]:
    return {k: v.dataframe for k, v in aux.items()} if aux else None


def _perturb(df: pd.DataFrame, seed: int = 11) -> pd.DataFrame:
    """A different dataset with the same columns: numeric values scaled and jittered, rows shuffled.

    Used only when the plot type has no separate mock sample. Integer id-like columns are left
    alone so identifiers stay valid; p-value-like columns stay inside (0, 1].
    """
    rng = np.random.default_rng(seed)
    out = df.copy()
    for col in out.columns:
        s = out[col]
        if pd.api.types.is_float_dtype(s):
            vals = s.to_numpy(dtype=float)
            finite = np.isfinite(vals)
            if not finite.any():
                continue
            lo, hi = np.nanmin(vals), np.nanmax(vals)
            if 0.0 <= lo and hi <= 1.0:                      # probability-like: keep in range
                vals[finite] = np.clip(vals[finite] * rng.uniform(0.85, 1.0, finite.sum()),
                                       1e-12, 1.0)
            else:
                vals[finite] = vals[finite] * 1.07 + rng.normal(0, 1e-3 * (abs(hi - lo) or 1.0),
                                                              finite.sum())
            out[col] = vals
    return out.sample(frac=1.0, random_state=seed).reset_index(drop=True)


def _new_dataset(plot_type: str, example_info) -> Tuple[pd.DataFrame, str, str]:
    """(dataframe, table_name, provenance) for the 'new data' step."""
    path = None
    try:
        path = mock_data.sample_path(plot_type)
    except Exception:  # noqa: BLE001
        path = None
    if path and os.path.exists(path):
        info = load_table(path)
        cols_ok = set(map(str, example_info.columns)) <= set(map(str, info.columns))
        if cols_ok:
            return info.dataframe, os.path.basename(path), "mock sample"
    return _perturb(example_info.dataframe), "perturbed_example.csv", "example with values perturbed"


def _first_style_option(plot_type: str) -> Optional[Tuple[str, Any, Any]]:
    """(key, default, changed_value) for the first visual option we can flip meaningfully."""
    for opt in ui_hints.options(plot_type):
        if opt.scope != "style":
            continue
        if opt.kind == "choice" and opt.choices:
            others = [c for c in opt.choices if c != opt.default]
            if others:
                return opt.key, opt.default, others[0]
        elif opt.kind == "bool":
            return opt.key, bool(opt.default), (not bool(opt.default))
        elif opt.kind == "number":
            if opt.default is not None:
                lo = opt.minimum if opt.minimum is not None else 0.0
                hi = opt.maximum if opt.maximum is not None else float(opt.default) * 2 + 1
                cand = (float(lo) + float(hi)) / 2.0
                if cand == opt.default:
                    cand = float(hi)
                if opt.decimals == 0:
                    cand = int(round(cand))
                return opt.key, opt.default, cand
    return None


def _color_option(plot_type: str) -> Optional[Tuple[str, Any]]:
    """A plot-specific colour control, when the type has one (colormap / node colour / class)."""
    for opt in ui_hints.options(plot_type):
        if opt.scope == "style" and opt.kind == "choice" and opt.choices and any(
                t in opt.key for t in ("color", "cmap", "colormap")):
            others = [c for c in opt.choices if c != opt.default and c not in ("auto", "(palette)")]
            if others:
                return opt.key, others[0]
    return None


def _drawn_title_size(fig) -> Optional[float]:
    for ax in fig.axes:
        if ax.get_title():
            return float(ax.title.get_fontsize())
    if fig._suptitle is not None:
        return float(fig._suptitle.get_fontsize())
    return None


def check_plot(plot_type: str, workdir: Optional[str] = None) -> Dict[str, str]:
    """Run the full preset QC for one plot type; returns a matrix row (all values strings)."""
    row = {c: "" for c in COLUMNS}
    row["plot_type"] = plot_type
    notes: List[str] = []
    tmp = workdir or tempfile.mkdtemp(prefix=f"mmf_preset_qc_{plot_type}_")
    caps = get_style_capabilities(plot_type)

    def mark(col: str, ok: bool, why: str = "") -> None:
        row[col] = "PASS" if ok else "FAIL"
        if not ok and why:
            notes.append(f"{col}: {why}")

    def na(col: str, why: str) -> None:
        row[col] = "N/A"
        notes.append(f"{col}: N/A - {why}")

    try:
        # 1. defaults --------------------------------------------------------------------------
        info, aux, spec = ex.load_example(plot_type)
        spec = copy.deepcopy(spec)
        base = _quiet_render(spec, info.dataframe, _aux_frames(aux))
        plt.close(base.figure)

        # 2. change settings ------------------------------------------------------------------
        spec["style"] = dict(STYLE_CHANGES)
        palette_ok = bool(caps.supports_palette)
        if palette_ok:
            spec["style"]["palette_name"] = "high_contrast"
        spec["layout"] = {**(spec.get("layout") or {}), **LAYOUT_CHANGES, "title": "QC title"}
        spec["output"] = {**spec["output"], **OUTPUT_CHANGES}
        opt = _first_style_option(plot_type)
        if opt:
            spec["mapping"][opt[0]] = opt[2]
        color_opt = _color_option(plot_type)
        if color_opt:
            spec["mapping"][color_opt[0]] = color_opt[1]
        changed = _quiet_render(spec, info.dataframe, _aux_frames(aux))
        plt.close(changed.figure)
        n_changed = len(STYLE_CHANGES) + len(LAYOUT_CHANGES) + len(OUTPUT_CHANGES) \
            + (1 if opt else 0) + (1 if color_opt else 0) + (1 if palette_ok else 0)
        assert n_changed >= 3

        # 3. save both presets ----------------------------------------------------------------
        style_preset = P.extract_preset(spec, mode="style", name=f"{plot_type} QC style")
        full_preset = P.extract_preset(spec, mode="full", name=f"{plot_type} QC full")
        style_path = P.save_preset(style_preset, os.path.join(tmp, "style"))
        full_path = P.save_preset(full_preset, os.path.join(tmp, "full"))
        mark("preset_save", os.path.getsize(style_path) > 0 and os.path.getsize(full_path) > 0)

        loaded_style = P.load_preset(style_path)
        loaded_full = P.load_preset(full_path)
        mark("preset_load", loaded_style == style_preset and loaded_full == full_preset,
             "loaded preset differs from the saved one")

        # 4. new data ----------------------------------------------------------------------
        new_df, new_name, provenance = _new_dataset(plot_type, info)
        notes.append(f"new data: {provenance}")
        fresh = make_spec(plot_type, new_name, "publication",
                          mapping={k: v for k, v in spec["mapping"].items()
                                   if k in P.role_keys(plot_type)})
        # the new figure's own title - a style preset must not overwrite it, and it gives the
        # typography check a drawn title whose size can be measured
        fresh["layout"] = {"title": "New data title"}
        aux_cols = None
        if aux:
            aux_cols = sorted({str(c) for v in aux.values() for c in v.columns})
        # matrix-style plots need their aux tables; UpSet needs its set list
        if "sets" in spec["mapping"]:
            fresh["mapping"]["sets"] = spec["mapping"]["sets"]

        # 5. apply + render --------------------------------------------------------------
        res_style = P.apply_preset(loaded_style, fresh, columns=list(new_df.columns),
                                   aux_columns=aux_cols)
        out_style = _quiet_render(res_style.spec, new_df, _aux_frames(aux))
        res_full = P.apply_preset(loaded_full, fresh, columns=list(new_df.columns),
                                  aux_columns=aux_cols)
        out_full = _quiet_render(res_full.spec, new_df, _aux_frames(aux))

        s2 = res_style.spec
        # 6. verify ------------------------------------------------------------------------
        typo_ok = all(s2["style"].get(k) == v for k, v in STYLE_CHANGES.items())
        drawn = _drawn_title_size(out_style.figure)
        if drawn is not None:
            typo_ok = typo_ok and abs(drawn - STYLE_CHANGES["title_font_pt"]) < 1e-6
        mark("typography_roundtrip", typo_ok,
             f"style tokens {s2.get('style')} / drawn title size {drawn}")

        lay_ok = all(s2["layout"].get(k) == v for k, v in LAYOUT_CHANGES.items()
                     if k != "legend_location")
        lay_ok = lay_ok and s2["output"].get("dpi") == OUTPUT_CHANGES["dpi"]
        lay_ok = lay_ok and s2["layout"].get("title") == "New data title"   # a label is data
        mark("layout_roundtrip", lay_ok, f"layout {s2.get('layout')} output {s2.get('output')}")

        if caps.supports_legend:
            mark("legend_roundtrip",
                 s2["layout"].get("legend_location") == "outside right"
                 and s2["style"].get("legend_pt") == STYLE_CHANGES["legend_pt"])
        else:
            na("legend_roundtrip", "this plot type draws no legend")

        mark("annotation_roundtrip", s2["style"].get("annotation_pt") == STYLE_CHANGES["annotation_pt"])

        color_checks = []
        if palette_ok:
            color_checks.append(s2["style"].get("palette_name") == "high_contrast")
        if color_opt:
            color_checks.append(s2["mapping"].get(color_opt[0]) == color_opt[1])
        if color_checks:
            mark("color_roundtrip", all(color_checks),
                 f"palette={s2['style'].get('palette_name')} option={color_opt}")
        else:
            na("color_roundtrip", "no palette or colour control applies to this plot type")
        if not palette_ok:
            notes.append("palette control declared inapplicable: " + caps.unsupported_controls_reason)

        if opt:
            mark("plot_specific_roundtrip", s2["mapping"].get(opt[0]) == opt[2],
                 f"{opt[0]} expected {opt[2]!r} got {s2['mapping'].get(opt[0])!r}")
        else:
            na("plot_specific_roundtrip",
               "every option of this plot type is analytical (config scope); none belongs in a style preset")

        # style preset must carry no data; full preset must carry roles but not the table
        style_text = json.dumps(loaded_style)
        leaks = P.preset_contains_data(loaded_style) + P.preset_contains_data(loaded_full)
        col_leak = [c for c in map(str, info.columns) if len(c) > 2 and f'"{c}"' in style_text]
        first_vals = [str(v) for c in info.dataframe.columns[:3] for v in info.dataframe[c].head(3)
                      if isinstance(v, str) and len(v) > 4]
        val_leak = [v for v in first_vals if v in style_text or v in json.dumps(loaded_full)]
        # identity: the rendered figure records the NEW table, and neither preset names the old one
        new_is_new = (s2["input_table"] == new_name and res_full.spec["input_table"] == new_name
                      and out_style.metadata["spec"]["input_table"] == new_name
                      and "input_table" not in loaded_style and "input_table" not in loaded_full
                      and f'"{spec["input_table"]}"' not in style_text)
        mark("new_data_safe", not leaks and not col_leak and not val_leak and new_is_new,
             f"leaks={leaks} columns={col_leak} values={val_leak[:2]} new_is_new={new_is_new}")

        # full configuration: roles + analytical options come back exactly
        split = P.split_mapping(plot_type, spec["mapping"])
        roles_back = all(res_full.spec["mapping"].get(k) == v for k, v in split.roles.items()
                         if v not in (None, ""))
        config_back = all(res_full.spec["mapping"].get(k) == v
                          for k, v in split.config_options.items())
        labels_back = res_full.spec["layout"].get("title") == "QC title"   # full restores labels
        mark("full_config_roundtrip", roles_back and config_back and labels_back
             and not res_full.unresolved_roles,
             f"roles={roles_back} config={config_back} labels={labels_back} "
             f"unresolved={res_full.unresolved_roles}")

        # style preset applied to the new data then re-extracted is the same preset
        again = P.extract_preset(s2, mode="style", name=style_preset["name"])
        volatile = {"created", "notes", "description"}
        same = {k: v for k, v in again.items() if k not in volatile} == \
               {k: v for k, v in style_preset.items() if k not in volatile}
        mark("style_roundtrip", same, "re-extracted style preset differs")

        # exports
        base_path = os.path.join(tmp, "qc_figure")
        files = export_figure(out_style.figure, base_path, ["png", "pdf", "svg"],
                              dpi=int(s2["output"]["dpi"]))
        for fmt in ("png", "pdf", "svg"):
            path = f"{base_path}.{fmt}"
            mark(f"{fmt}_export", path in files and os.path.getsize(path) > 0)

        # PlotSpec JSON round-trip renders to the same record
        rt = json.loads(json.dumps(s2))
        out_rt = _quiet_render(rt, new_df, _aux_frames(aux))
        rt_ok = (rt == s2 and out_rt.metadata.get("n_rows") == out_style.metadata.get("n_rows")
                 and out_rt.metadata.get("data_columns_used") == out_style.metadata.get("data_columns_used"))
        plt.close(out_rt.figure)
        if not rt_ok:
            notes.append("plotspec_roundtrip: re-rendered spec differs")
        plt.close(out_style.figure)
        plt.close(out_full.figure)

        fails = [c for c in COLUMNS if row.get(c) == "FAIL"]
        row["status"] = "PASS" if not fails and rt_ok else "FAIL"
    except Exception as exc:  # noqa: BLE001 - one plot type failing must not stop the matrix
        row["status"] = "FAIL"
        notes.append(f"error: {type(exc).__name__}: {exc}")
        for c in COLUMNS[1:-2]:
            row[c] = row[c] or "FAIL"
    finally:
        plt.close("all")
    row["notes"] = " | ".join(notes)
    return row


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = [check_plot(pt) for pt in available_plot_types()]
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    n_pass = sum(r["status"] == "PASS" for r in rows)
    na_cells = sum(1 for r in rows for c in COLUMNS if r[c] == "N/A")
    lines = [
        "# Figure Preset QC — every registered plot type",
        "",
        f"Generated {_dt.datetime.now(_dt.timezone.utc).isoformat(timespec='seconds')} by "
        "`scripts/build_figure_preset_qc.py` against the live plot registry "
        f"({len(rows)} renderers, enumerated from code).",
        "",
        f"**{n_pass} / {len(rows)} plot types PASS.** {na_cells} individual checks are N/A, each "
        "with its reason in the `notes` column (a plot that draws no legend has no legend to "
        "round-trip; a plot whose options are all analytical has no visual option to carry in a "
        "style preset).",
        "",
        "Per plot type the harness renders the bundled example with defaults, changes typography, "
        "colour, layout, legend and export settings plus one visual plot option where one exists, "
        "saves a style preset and a full-configuration preset, loads a *different* dataset of the "
        "same type, applies both, and checks that every setting came back, that the new data stayed "
        "the new data, that nothing from the original table travelled in either preset, that "
        "PNG/PDF/SVG export, and that PlotSpec and preset both survive a JSON round-trip.",
        "",
        "| plot_type | status | N/A checks |",
        "|---|---|---|",
    ]
    for r in rows:
        nas = [c for c in COLUMNS if r[c] == "N/A"]
        lines.append(f"| {r['plot_type']} | {r['status']} | {', '.join(nas) or '—'} |")
    lines += ["", "Columns of `all_plot_preset_matrix.csv`: " + ", ".join(COLUMNS) + ".",
              "", "Companion audit: `color_controls_audit.csv` (which colour model each renderer "
              "uses and which style controls it honours; regenerated by "
              "`scripts/audit_style_capabilities.py`)."]
    README_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {CSV_PATH.relative_to(ROOT)} and README: {n_pass}/{len(rows)} PASS")
    for r in rows:
        if r["status"] != "PASS":
            print(f"  FAIL {r['plot_type']}: {r['notes']}")
    return 0 if n_pass == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
