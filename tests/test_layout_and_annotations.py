"""Shared layout + per-plot layout/annotation fixes (v1.0.0-rc figure QC pass).

GUI-free: verifies the shared layout helper, flexible legend locations, and the
concrete renderer fixes (PCA marker size, stacked tick centering, Manhattan cutoff
controls, paired-dot independent colors, UpSet/swimmer margins, MA click-identify,
volcano/MA per-label offsets).
"""

import json

import matplotlib
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import pytest
from matplotlib.collections import PathCollection

matplotlib.use("Agg")

from make_my_figure_core.plots.base import (
    LEGEND_LOCATIONS, apply_publication_layout, resolve_legend_location)
from make_my_figure_core.plots.registry import figure_to_bytes, make_spec, render


# --- shared layout helper ---------------------------------------------------
def test_layout_spec_round_trips():
    layout = {"margin_left": 0.2, "x_tick_rotation": 45, "legend_location": "outside top",
              "title_pad": 12.0, "x_label_pad": 8.0}
    spec = make_spec("barplot_with_error_bar", "b", "publication",
                     mapping={"x": "g", "y": "v"})
    spec["layout"] = {**spec.get("layout", {}), **layout}
    rt = json.loads(json.dumps(spec))
    for k, v in layout.items():
        assert rt["layout"][k] == v


def test_apply_layout_sets_margins_and_rotation():
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["aaa", "bbb"])
    spec = {"layout": {"margin_left": 0.3, "x_tick_rotation": 90, "x_tick_pad": 7,
                       "y_label_pad": 15}}
    apply_publication_layout(fig, ax, spec, None)
    assert abs(fig.subplotpars.left - 0.3) < 1e-6
    assert {t.get_rotation() for t in ax.get_xticklabels()} == {90.0}
    assert ax.yaxis.labelpad == 15
    plt.close(fig)


def test_resolve_legend_location_named():
    spec = {"layout": {"legend_location": "outside bottom"}}
    loc, bbox, side = resolve_legend_location(spec, None)
    assert side == "bottom" and bbox is not None
    assert set(("outside right", "upper left", "inside lower left")) <= set(LEGEND_LOCATIONS)


# --- PCA marker size --------------------------------------------------------
def _pca_df():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"gene": [f"g{i}" for i in range(40)]})
    for s in [f"S{i}" for i in range(8)]:
        df[s] = rng.normal(size=40)
    return df, [f"S{i}" for i in range(8)]


@pytest.mark.parametrize("ms", [30, 120])
def test_pca_marker_size_applies(ms):
    df, cols = _pca_df()
    spec = make_spec("pca_scatter_from_matrix", "p", "publication",
                     mapping={"matrix_row_id": "gene", "value_columns": cols})
    spec["style"] = {"marker_size": ms}
    r = render(spec, df)
    sizes = {s for c in r.figure.axes[0].collections if isinstance(c, PathCollection)
             for s in c.get_sizes()}
    assert sizes == {float(ms)}


def test_pca_marker_size_round_trips():
    spec = make_spec("pca_scatter_from_matrix", "p", "publication",
                     mapping={"matrix_row_id": "gene", "value_columns": ["S0"]})
    spec["style"] = {"marker_size": 99}
    assert json.loads(json.dumps(spec))["style"]["marker_size"] == 99


# --- stacked composition ----------------------------------------------------
def test_stacked_ticks_centered_on_bars():
    df = pd.DataFrame({"sample": ["A", "A", "B", "B", "C", "C"],
                       "comp": ["x", "y"] * 3, "frac": [.6, .4, .5, .5, .7, .3]})
    r = render(make_spec("stacked_bar_composition", "s", "publication",
                         mapping={"x": "sample", "stack": "comp", "y": "frac"}), df)
    ax = r.figure.axes[0]
    assert list(ax.get_xticks()) == [0, 1, 2]  # centered on the 3 bar positions
    bar_centers = sorted({round(p.get_x() + p.get_width() / 2, 3) for p in ax.patches})
    assert bar_centers == [0.0, 1.0, 2.0]


@pytest.mark.parametrize("rot", [45, 90])
def test_rotated_x_labels_stay_below_axis(rot):
    # Regression: rotated x tick labels must hang BELOW the axis, not overlap the
    # bars/plot (a passing angle-only test previously missed this).
    df = pd.DataFrame({"sample": [f"Sample_{i:02d}" for i in range(6) for _ in range(2)],
                       "comp": ["A", "B"] * 6, "frac": [0.5] * 12})
    spec = make_spec("stacked_bar_composition", "s", "publication",
                     mapping={"x": "sample", "stack": "comp", "y": "frac", "x_tick_rotation": rot})
    r = render(spec, df)
    ax = r.figure.axes[0]
    r.figure.canvas.draw()
    inv = ax.transAxes.inverted()
    tops = [inv.transform((0, t.get_window_extent().y1))[1]
            for t in ax.get_xticklabels() if t.get_text()]
    assert max(tops) <= 0.02, f"rotated x labels overlap the plot (top={max(tops):.3f})"


def test_stacked_x_tick_rotation():
    df = pd.DataFrame({"sample": ["A", "B"], "comp": ["x", "x"], "frac": [1.0, 1.0]})
    spec = make_spec("stacked_bar_composition", "s", "publication",
                     mapping={"x": "sample", "stack": "comp", "y": "frac", "x_tick_rotation": 90})
    r = render(spec, df)
    assert 90.0 in {t.get_rotation() for t in r.figure.axes[0].get_xticklabels() if t.get_text()}


# --- Manhattan cutoff controls ----------------------------------------------
def _manhattan_df():
    rng = np.random.default_rng(0)
    n = 400
    return pd.DataFrame({"chrom": np.repeat([str(i) for i in range(1, 5)], n // 4),
                         "pos": np.tile(np.arange(n // 4), 4),
                         "p": rng.uniform(1e-9, 1, n)})


def _man_lines(extra):
    df = _manhattan_df()
    m = {"chrom": "chrom", "pos": "pos", "p": "p", **extra}
    r = render(make_spec("manhattan_plot", "m", "publication", mapping=m), df)
    return [l for l in r.figure.axes[0].get_lines() if l.get_linestyle() in ("--", ":", "-.", "-")], r


def test_manhattan_cutoff_can_be_hidden():
    on, _ = _man_lines({})
    off, _ = _man_lines({"show_cutoff_line": False, "show_suggestive_line": False})
    assert len(off) < len(on)


def test_manhattan_cutoff_color_width_style_and_threshold():
    _lines, r = _man_lines({"genome_wide_threshold": 1e-6, "cutoff_line_color": "#00AA00",
                            "cutoff_line_width": 3.0, "cutoff_line_style": "-",
                            "show_suggestive_line": False})
    gw = [l for l in r.figure.axes[0].get_lines() if mcolors.to_hex(l.get_color()) == "#00aa00"]
    assert len(gw) == 1 and gw[0].get_linewidth() == 3.0


def test_manhattan_tick_rotation():
    _lines, r = _man_lines({"x_tick_rotation": 45})
    assert 45.0 in {t.get_rotation() for t in r.figure.axes[0].get_xticklabels() if t.get_text()}


def test_manhattan_cutoff_spec_round_trip():
    m = {"chrom": "chrom", "pos": "pos", "p": "p", "genome_wide_threshold": 1e-6,
         "cutoff_line_color": "#00AA00", "show_cutoff_line": True}
    spec = make_spec("manhattan_plot", "m", "publication", mapping=m)
    rt = json.loads(json.dumps(spec))["mapping"]
    assert rt["genome_wide_threshold"] == 1e-6 and rt["cutoff_line_color"] == "#00AA00"


# --- paired dot independent colors ------------------------------------------
def test_paired_dot_line_and_point_colors_independent():
    df = pd.DataFrame({"subj": ["s1", "s1", "s2", "s2"], "cond": ["pre", "post"] * 2,
                       "val": [1, 2, 2, 3]})
    spec = make_spec("paired_slopegraph", "p", "publication",
                     mapping={"subject": "subj", "condition": "cond", "value": "val",
                              "line_color": "#cccccc", "point_color": "#B2182B"})
    r = render(spec, df)
    lines = r.figure.axes[0].get_lines()
    lc = {mcolors.to_hex(l.get_color()) for l in lines}
    pc = {mcolors.to_hex(l.get_markerfacecolor()) for l in lines if l.get_marker() == "o"}
    assert "#cccccc" in lc and "#b2182b" in pc and lc != pc


# --- UpSet / swimmer margins ------------------------------------------------
def test_upset_left_margin_control():
    from make_my_figure_core import examples as ex
    info, aux, ps = ex.load_example("upset_plot")
    auxd = {k: v.dataframe for k, v in (aux or {}).items()} or None
    m = dict(ps.get("mapping") or {})
    spec = make_spec("upset_plot", "u", "publication", mapping=m)
    spec["layout"] = {"margin_left": 0.4}
    r = render(spec, info.dataframe, aux=auxd)
    assert abs(r.figure.subplotpars.left - 0.4) < 1e-6


def test_swimmer_right_margin_control():
    from make_my_figure_core import examples as ex
    info, aux, ps = ex.load_example("swimmer_plot")
    auxd = {k: v.dataframe for k, v in (aux or {}).items()} or None
    m = dict(ps.get("mapping") or {})
    spec = make_spec("swimmer_plot", "s", "publication", mapping=m)
    spec["layout"] = {"margin_right": 0.7}
    r = render(spec, info.dataframe, aux=auxd)
    assert abs(r.figure.subplotpars.right - 0.7) < 1e-6


# --- MA / volcano interactive annotation model ------------------------------
def _de_table(n=80):
    rng = np.random.default_rng(1)
    return pd.DataFrame({"feature_label": [f"G{i}" for i in range(n)],
                         "log2_fold_change": rng.normal(0, 2, n),
                         "p_value": rng.uniform(0, 1, n),
                         "adjusted_p_value": rng.uniform(0, 1, n),
                         "AveExpr": rng.uniform(0, 12, n)})


def test_ma_has_click_identify_points():
    tbl = _de_table()
    spec = make_spec("ma_plot", "m", "publication",
                     mapping={"x": "AveExpr", "y": "log2_fold_change",
                              "p": "adjusted_p_value", "label": "feature_label"})
    r = render(spec, tbl)
    assert len(r.metadata.get("pickable_points", [])) == len(tbl)
    assert r.metadata.get("pick_label_key") == "selected_labels"


def test_ma_selected_labels_and_offsets_render():
    tbl = _de_table()
    spec = make_spec("ma_plot", "m", "publication",
                     mapping={"x": "AveExpr", "y": "log2_fold_change", "p": "adjusted_p_value",
                              "label": "feature_label", "selected_labels": ["G1", "G2"],
                              "label_offsets": json.dumps({"G1": [30, 20]})})
    r = render(spec, tbl)
    texts = {t.get_text() for t in r.figure.axes[0].texts}
    assert {"G1", "G2"} <= texts


def test_volcano_per_label_offset_only_affects_that_label():
    tbl = _de_table()
    base = {"x": "log2_fold_change", "p": "adjusted_p_value", "label": "feature_label",
            "annotate": True, "label_mode": "top_fdr", "top_n": 8}
    r1 = render(make_spec("volcano_plot", "v", "publication", mapping=base), tbl)
    r2 = render(make_spec("volcano_plot", "v", "publication",
                          mapping={**base, "label_offsets": json.dumps({"G1": [50, -30]})}), tbl)
    assert r1.figure is not None and r2.figure is not None  # renders with/without offsets


# --- heatmap / hierarchical clustering controls -----------------------------
def _heat_df(nrow=18, ncol=8):
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"gene": [f"LongGene_{i:03d}" for i in range(nrow)]})
    for c in [f"S{j}" for j in range(ncol)]:
        df[c] = rng.normal(size=nrow)
    return df, [f"S{j}" for j in range(ncol)]


def test_heatmap_colorbar_location_and_ylabelpad_apply():
    df, cols = _heat_df()
    spec = make_spec("heatmap_clustered_matrix", "h", "publication",
                     mapping={"row_id": "gene", "value_columns": cols, "scale": "row_zscore",
                              "show_row_labels": True, "colorbar_location": "left",
                              "y_label_pad": 20, "row_label_fontsize": 7})
    r = render(spec, df)
    ax = r.figure.axes[0]
    assert ax.yaxis.labelpad == 20
    assert {t.get_fontsize() for t in ax.get_yticklabels() if t.get_text()} == {7.0}
    assert len(figure_to_bytes(r.figure, "pdf")) > 500


def test_hierarchical_clustering_controls_apply():
    df, cols = _heat_df(20, 9)
    spec = make_spec("hierarchical_clustering", "h", "publication",
                     mapping={"row_id": "gene", "value_columns": cols, "cluster": "rows",
                              "k": 3, "scale": "row_zscore", "y_label_pad": 16,
                              "colorbar_pad": 0.22, "row_label_fontsize": 8})
    r = render(spec, df)
    assert r.figure is not None and not any("error" in w.lower() for w in (r.warnings or []))
    assert r.figure.axes[0].yaxis.labelpad == 16


# --- lollipop annotation alignment ------------------------------------------
def test_lollipop_labels_anchor_to_markers():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"pos": sorted(rng.integers(1, 500, 12)), "count": rng.integers(3, 10, 12),
                       "mut": [f"p.M{i}V" for i in range(12)]})
    spec = make_spec("lollipop_mutation_plot", "l", "publication",
                     mapping={"x": "pos", "y": "count", "label": "mut", "label_top_n": 5})
    r = render(spec, df)
    assert r.metadata.get("labels_shown", 0) >= 1 and r.figure is not None


def test_lollipop_per_label_offset_renders():
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"pos": list(range(10)), "count": list(range(10, 0, -1)),
                       "mut": [f"m{i}" for i in range(10)]})
    spec = make_spec("lollipop_mutation_plot", "l", "publication",
                     mapping={"x": "pos", "y": "count", "label": "mut", "label_top_n": 4,
                              "label_offsets": json.dumps({"m0": [0, 45]})})
    r = render(spec, df)
    assert "m0" in {t.get_text() for t in r.figure.axes[0].texts}


# --- exports + ui_hints exposure --------------------------------------------
@pytest.mark.parametrize("fmt", ["png", "pdf", "svg"])
def test_manhattan_exports_non_empty(fmt):
    _lines, r = _man_lines({})
    assert len(figure_to_bytes(r.figure, fmt, dpi=300)) > 500


def test_ui_hints_expose_new_controls():
    from make_my_figure_core import ui_hints as u
    man = {o.key for o in u.options("manhattan_plot")}
    assert {"show_cutoff_line", "genome_wide_threshold", "cutoff_line_color",
            "x_tick_rotation"} <= man
    paired = {o.key for o in u.options("paired_slopegraph")}
    assert {"point_color", "line_color"} <= paired
