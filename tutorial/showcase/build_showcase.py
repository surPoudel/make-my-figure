"""Render the same-data / different-presentation showcases with the application's own renderer.

Every figure here is produced by make_my_figure_core (the code the desktop application calls),
from the tutorial datasets, through real PlotSpecs. Presets are loaded from their files and applied
with presets.apply_preset - nothing is hand-styled and then called a preset result. Two copies of
each figure are written: the manuscript copy (the preset's own typography) and a presentation copy
(larger fonts, markers and lines via the style override block of the PlotSpec; identical data).

    python tutorial/showcase/build_showcase.py

Outputs: tutorial/showcase/<showcase>/<name>.{png,svg} (+ *_pres.png/svg), presets_used.md,
tutorial/audit/showcase_data_integrity.csv.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TUT = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(TUT, ".."))
sys.path.insert(0, ROOT)

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from make_my_figure_core import experimental_presets as xp  # noqa: E402
from make_my_figure_core import presets as presets_mod  # noqa: E402
from make_my_figure_core.io.loaders import load_table  # noqa: E402
from make_my_figure_core.plots import registry  # noqa: E402
from make_my_figure_core.plots.registry import export_figure  # noqa: E402

DATA = os.path.join(TUT, "datasets")

# Presentation typography: same data, larger text and marks for a projected slide.
PRESENTATION_STYLE = {
    "axis_font_pt": 20, "tick_label_pt": 17, "legend_pt": 16, "legend_title_pt": 17,
    "title_font_pt": 20, "annotation_pt": 15, "base_font_pt": 17,
    "spine_width_pt": 1.6, "tick_width": 1.4, "tick_length": 6, "line_width_pt": 2.6,
    "marker_size": 90, "marker_edge_width": 0.9, "regression_line_width": 3.0,
    "errorbar_line_width": 1.8, "errorbar_capsize": 5,
}
PRES_STATS_FONT = 15.0
PRES_WIDTH_MM, PRES_HEIGHT_MM = 170.0, 150.0   # presentation copies: larger physical figure, same data

STATS_ALL_PAIRS = {
    "enabled": True, "test": "welch_t", "comparison_mode": "selected_pairs", "correction": "holm",
    "selected_pairs": [["Control", "Treatment B"], ["Treatment A", "Treatment B"], ["Control", "Treatment C"]],
    "group_column": "group", "annotate": True,
    "annotation": {"content": "p", "digits": 3, "font_size": 9.5, "placement": "bracket"},
}

integrity_rows = []
presets_used = {}


def _hash_df(df: pd.DataFrame, cols) -> str:
    sub = df[list(cols)].copy()
    return hashlib.sha256(pd.util.hash_pandas_object(sub, index=False).values.tobytes()).hexdigest()[:16]


class _Loaded:
    def __init__(self, name):
        self.info = load_table(os.path.join(DATA, name))
        self.table_name = name
        self.dataframe = self.info.dataframe


def load(name: str):
    info = _Loaded(name)
    return info, info.dataframe


def spec_for(pt, table, mapping, *, statistics=None, style=None, layout=None):
    spec = registry.make_spec(pt, table, "publication", mapping=mapping, statistics=statistics, layout=layout)
    if style:
        spec["style"] = dict(style)
    return spec


def with_preset(spec, preset_id, columns):
    """Apply an experimental preset file to a spec exactly as the application does."""
    entry = next(e for e in xp.list_experimental_presets() if e.preset_id == preset_id)
    preset = xp.load_experimental_preset(entry.path)
    res = presets_mod.apply_preset(preset, spec, columns=list(columns))
    presets_used[preset_id] = {
        "file": os.path.relpath(entry.path, ROOT), "name": preset.get("name"), "mode": preset.get("mode"),
        "plot_type": preset.get("plot_type"), "universal": preset.get("universal"),
        "style": preset.get("style"), "options": preset.get("options"), "layout": preset.get("layout"),
        "applied": len(res.applied), "skipped": len(res.skipped),
        "evidence_note": (preset.get("experimental") or {}).get("limitations")
        or (preset.get("description") or "")[:300],
    }
    return res.spec


def render_pair(showcase, name, spec, df, *, pres_style=None, aux=None, stats_font=None, note=""):
    """Render the manuscript copy and the presentation copy; record integrity facts."""
    out = os.path.join(HERE, showcase)
    os.makedirs(out, exist_ok=True)
    results = {}
    for tag, style_extra in (("", None), ("_pres", pres_style or PRESENTATION_STYLE)):
        s = json.loads(json.dumps(spec))
        if style_extra:
            s.setdefault("style", {})
            s["style"].update(style_extra)
            s.setdefault("layout", {})
            s["layout"].update({"width_mm": PRES_WIDTH_MM, "height_mm": PRES_HEIGHT_MM})
            if s.get("statistics", {}).get("enabled") and stats_font:
                s["statistics"].setdefault("annotation", {})["font_size"] = stats_font
        result = registry.render(s, df, aux=aux)
        base = os.path.join(out, name + tag)
        export_figure(result.figure, base, ["png", "svg"], dpi=220 if tag else 200)
        results[tag] = result
        plt.close(result.figure)
    md = results[""].metadata

    def _stats(res):
        rep = getattr(res, "stats_report", None)
        if rep is None:
            return []
        return [{"comparison": f"{r.group_a} vs {r.group_b}" if r.group_b else (r.group_a or r.test_name),
                 "test": r.test_name, "p": r.p_value, "adj_p": r.adjusted_p_value,
                 "n": r.n_total or sum((r.n_by_group or {}).values())} for r in rep.results]

    st, st_pres = _stats(results[""]), _stats(results["_pres"])
    integrity_rows.append({
        "showcase": showcase, "figure": name, "plot_type": spec["plot_type"],
        "n_rows": int(len(df)), "data_hash": _hash_df(df, df.columns),
        "group_n": json.dumps(md.get("group_n") or md.get("n") or md.get("counts") or {}),
        "statistics": json.dumps(st),
        "statistics_presentation_copy_identical": str(st == st_pres),
        "note": note,
    })
    print(f"  {showcase}/{name}: rendered (manuscript + presentation)")
    return results[""]


# ------------------------------------------------------------------ showcase 1: group comparison
def showcase_group():
    info, df = load("showcase_group_comparison.csv")
    cols = df.columns
    mapping = {"x": "group", "y": "cytokine_pg_ml"}
    layout = {"y_label": "Cytokine (pg/ml)", "x_label": ""}
    pt = "boxplot_or_violin_with_points"

    # A. default rendering (what the app draws after choosing the plot type)
    render_pair("1_group_comparison", "A_default_box", spec_for(pt, info.table_name, mapping, layout=layout), df,
                note="application defaults, no preset, no statistics")
    # B..D. publication presets + statistics, same observations
    base_stats = spec_for(pt, info.table_name, mapping, statistics=STATS_ALL_PAIRS, layout=layout)
    render_pair("1_group_comparison", "B_box_points_outline_preset", with_preset(base_stats, "gc_box_points_outline", cols), df,
                stats_font=PRES_STATS_FONT, note="preset gc_box_points_outline + Welch all pairs Holm")
    render_pair("1_group_comparison", "C_violin_points_preset", with_preset(base_stats, "gc_violin_points", cols), df,
                stats_font=PRES_STATS_FONT, note="preset gc_violin_points + statistics")
    bar_spec = spec_for("barplot_with_error_bar", info.table_name, {"x": "group", "y": "cytokine_pg_ml"},
                        statistics=STATS_ALL_PAIRS, layout=layout)
    render_pair("1_group_comparison", "D_bar_points_jittered_preset", with_preset(bar_spec, "gc_bar_points_jittered", cols), df,
                stats_font=PRES_STATS_FONT, note="preset gc_bar_points_jittered (mean + SEM + observations) + statistics")
    render_pair("1_group_comparison", "E_box_points_light_preset", with_preset(base_stats, "gc_box_points_light", cols), df,
                stats_font=PRES_STATS_FONT, note="preset gc_box_points_light (alternate)")
    render_pair("1_group_comparison", "F_single_column_89mm_N_preset", with_preset(base_stats, "single_89mm_N", cols), df,
                stats_font=PRES_STATS_FONT, note="universal width preset Single column 89 mm (N)")

    # Observation controls: six renderings of the same observations
    variants = {
        "J1_small_narrow_jitter": {"point_size": 12, "point_jitter_width": 0.12, "point_fill": "filled", "point_edge": "none"},
        "J2_large_moderate_jitter": {"point_size": 60, "point_jitter_width": 0.35, "point_fill": "filled", "point_edge": "dark"},
        "J3_open_circles": {"point_size": 55, "point_jitter_width": 0.3, "point_fill": "open", "point_edge": "same", "point_edge_width": 1.2},
        "J4_black_edged_filled": {"point_size": 55, "point_jitter_width": 0.3, "point_fill": "filled", "point_edge": "dark", "point_edge_width": 1.0},
        "J5_beeswarm": {"point_size": 45, "point_arrangement": "beeswarm", "point_fill": "filled", "point_edge": "dark"},
        "J6_centered_no_jitter": {"point_size": 45, "point_arrangement": "centered", "point_jitter_width": 0.0, "point_fill": "filled", "point_edge": "dark", "point_alpha": 0.55},
    }
    for name, opts in variants.items():
        m = dict(mapping, points=True, kind="box", box_fill="outline", **opts)
        render_pair("1_group_comparison", name, spec_for(pt, info.table_name, m, layout=layout), df,
                    note="observation controls: " + ", ".join(f"{k}={v}" for k, v in opts.items()))


# ------------------------------------------------------------------ showcase 2: volcano
def showcase_volcano():
    info, df = load("rnaseq_results.csv")
    pt = "volcano_plot"
    basic = spec_for(pt, info.table_name, {"x": "log2FoldChange", "p": "pvalue", "label": "gene_symbol", "id_col": "gene_id"})
    render_pair("2_volcano", "A_default", basic, df, note="detected roles, all option defaults")
    refined_map = {"x": "log2FoldChange", "p": "padj", "label": "gene_symbol", "id_col": "gene_id",
                   "use_fdr": True, "lfc_cutoff": 1.0, "p_cutoff": 0.05, "label_mode": "top_up_down",
                   "top_n_up": 4, "top_n_down": 4, "color_up": "#B2182B", "color_down": "#2166AC",
                   "color_ns": "#B8B8B8", "show_arrows": True, "label_box": True, "show_legend": True}
    refined = spec_for(pt, info.table_name, refined_map, layout={"x_label": "log2 fold change", "y_label": "-log10 adjusted P"},
                       style={"marker_size": 70, "marker_edge_width": 0.5, "annotation_pt": 11})
    render_pair("2_volcano", "B_refined", refined, df,
                pres_style=dict(PRESENTATION_STYLE, marker_size=110, annotation_pt=16),
                note="adjusted P, FDR axis, 6+6 labels with boxes, larger markers, neutral n.s.")


# ------------------------------------------------------------------ showcase 3: heatmap
def showcase_heatmap():
    info, df = load("feature_sample_matrix.csv")
    values = [c for c in df.columns if c.startswith("S")]
    # same 30 most variable features in both renderings (a data choice, stated)
    var = df[values].var(axis=1)
    sub = df.loc[var.sort_values(ascending=False).index[:30]].reset_index(drop=True)
    pt = "heatmap_clustered_matrix"
    basic = spec_for(pt, info.table_name, {"row_id": "gene_symbol", "value_columns": values})
    render_pair("3_heatmap", "A_basic", basic, sub, note="30 most variable features, defaults (no scaling, auto colormap)")
    refined = spec_for(pt, info.table_name, {"row_id": "gene_symbol", "value_columns": values, "scale": "row_zscore",
                                             "colormap": "RdBu_r", "cluster_columns": False, "cell_border_color": "none",
                                             "cell_border_width": 0.0, "row_label_fontsize": 9, "col_label_fontsize": 10,
                                             "colorbar_shrink": 0.6},
                       layout={"x_label": "Sample", "y_label": ""})
    render_pair("3_heatmap", "B_refined", refined, sub,
                pres_style=dict(PRESENTATION_STYLE),
                note="row z-score, RdBu_r, columns in file order, no cell grid, explicit label sizes, short colorbar")
    # combined plot type that draws the tree
    tree = spec_for("hierarchical_clustering", info.table_name, {"row_id": "gene_symbol", "value_columns": values,
                                                                 "scale": "row_zscore", "colormap": "RdBu_r"})
    try:
        render_pair("3_heatmap", "C_heatmap_with_dendrogram", tree, sub, note="Hierarchical clustering (heatmap + clusters) plot type")
    except Exception as exc:  # noqa: BLE001
        print("  hierarchical_clustering render skipped:", exc)


# ------------------------------------------------------------------ showcase 4: scatter
def showcase_scatter():
    info, df = load("relationship_data.csv")
    pt = "scatterplot_with_regression"
    basic = spec_for(pt, info.table_name, {"x": "expression_a", "y": "expression_b"})
    render_pair("4_scatter", "A_basic", basic, df, note="two roles, defaults")
    refined = spec_for(pt, info.table_name, {"x": "expression_a", "y": "expression_b", "color": "cell_line",
                                             "show_r": True, "show_n": True, "show_p": True, "show_r2": True,
                                             "show_slope": False, "fit_stats_loc": "upper left"},
                       layout={"x_label": "Expression A (log2)", "y_label": "Expression B (log2)"},
                       style={"marker_size": 70, "marker_edge_width": 0.8, "regression_line_width": 2.4})
    render_pair("4_scatter", "B_refined", refined, df,
                pres_style=dict(PRESENTATION_STYLE, marker_size=130, marker_edge_width=1.2),
                note="colour by cell line, per-group fit, r/R2/P/n box, larger edged markers")


# ------------------------------------------------------------------ showcase 5: survival
def showcase_survival():
    info, df = load("survival.csv")
    pt = "kaplan_meier_survival_curve"
    basic = spec_for(pt, info.table_name, {"time": "time_months", "event": "event", "group": "arm"})
    render_pair("5_survival", "A_default", basic, df, note="defaults")
    stats = {"enabled": True, "test": "logrank", "group_column": "arm", "annotate": True,
             "annotation": {"content": "p", "digits": 3, "font_size": 9.5}}
    refined = spec_for(pt, info.table_name, {"time": "time_months", "event": "event", "group": "arm",
                                             "y_scale": "percent", "reference_line": 50, "y_ticks": "ends_and_midpoint",
                                             "x_max": 48},
                       statistics=stats, layout={"x_label": "Time (months)", "y_label": "Survival (%)"},
                       style={"line_width_pt": 2.4})
    render_pair("5_survival", "B_refined", refined, df, stats_font=PRES_STATS_FONT,
                pres_style=dict(PRESENTATION_STYLE, line_width_pt=3.4),
                note="percent scale, 50 % reference, x to 48 months, log-rank P, thicker curves")


def main() -> int:
    showcase_group(); showcase_volcano(); showcase_heatmap(); showcase_scatter(); showcase_survival()
    with open(os.path.join(TUT, "audit", "showcase_data_integrity.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(integrity_rows[0]))
        w.writeheader(); w.writerows(integrity_rows)
    lines = ["# Presets used in the showcases", "",
             "Each preset was loaded from its file and applied with `presets.apply_preset`, exactly as the "
             "application's Preview & apply does. All are EXPERIMENTAL evidence-derived presets; the letters "
             "(S), (C), (N) name the evidence set, not an approval.", ""]
    for pid, p in presets_used.items():
        lines += [f"## `{pid}` - {p['name']}", "", f"File: `{p['file']}`; mode {p['mode']}; plot type {p['plot_type']}; "
                  f"universal {p['universal']}; applied {p['applied']} setting(s), skipped {p['skipped']}.", "",
                  "```json", json.dumps({"style": p["style"], "options": p["options"], "layout": p["layout"]}, indent=1)[:2500], "```", ""]
    with open(os.path.join(HERE, "presets_used.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"integrity rows: {len(integrity_rows)}; presets: {list(presets_used)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
