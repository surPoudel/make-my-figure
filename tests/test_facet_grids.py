"""Facet grids (facet_row / facet_col) for the box/violin and line plots.

Reference design (tests/fixtures/plant_growth_facets.csv, a mock dataset supplied
with the request): 2 species x 2 initial ages x 3 nitrogen levels x 4 months,
n = 5 per cell, 240 rows - drawn as ggplot's facet_grid(Age ~ Species) with
months on x and nitrogen as colour.

Every test asserts numbers, not only that a figure was produced.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from matplotlib.collections import PathCollection

from apps.desktop_app.controller import DesktopController
from make_my_figure_core.plots.axis_scale import plotted_values
from make_my_figure_core.plots.facets import FACET_HOST_LABEL, FACET_STRIP_LABEL, facet_axes, facet_host
from make_my_figure_core.plots.registry import figure_to_bytes
from make_my_figure_core.ui_hints import column_fields, options

C = DesktopController()
DF = pd.read_csv(Path(__file__).parent / "fixtures" / "plant_growth_facets.csv")
DATA = C.loaded_from_dataframe(DF, "plants.csv")
BOX = {"x": "Month", "y": "Growth_cm", "hue": "Nitrogen_Concentration", "facet_row": "Age", "facet_col": "Species"}
LINE = {"x": "Month", "y": "Growth_cm", "color": "Nitrogen_Concentration", "facet_row": "Age",
        "facet_col": "Species", "error_display": "bars"}
BOX_T, LINE_T = "boxplot_or_violin_with_points", "lineplot_timecourse_with_error_band"


def _render(pt, mapping, layout=None, statistics=None, style=None, data=DATA):
    s = C.build_spec(pt, "publication", data.table_name, mapping, width="default", statistics=statistics)
    s.setdefault("layout", {}).update(layout or {})
    if style:
        s["style"] = style
    return s, C.render(s, data)


def _points(ax):
    cols = [c for c in ax.collections if isinstance(c, PathCollection) and len(c.get_offsets())]
    return np.sort(np.concatenate([c.get_offsets()[:, 1] for c in cols])) if cols else np.array([])


def _strips(fig):
    return sorted(t.get_text() for a in fig.axes if a.get_label() == FACET_STRIP_LABEL for t in a.texts)


def test_both_plots_offer_facet_fields_and_hide_facet_options_until_used():
    for pt in (BOX_T, LINE_T):
        assert {"facet_row", "facet_col"} <= set(column_fields(pt))
        req = {o.key: o.requires for o in options(pt)}
        assert req["facet_labels"] == ("facet_row", "facet_col") and req["facet_share_y"]


def test_box_grid_panels_hold_exactly_their_subsets():
    _, r = _render(BOX_T, BOX)
    panels = facet_axes(r.figure)
    assert len(panels) == 4
    meta = r.metadata["facets"]
    assert meta["rows"] == ["Young", "Old"] and meta["cols"] == ["Species_A", "Species_B"]
    assert [p["n"] for p in meta["panels"]] == [60, 60, 60, 60]
    for ax, (age, sp) in zip(panels, [("Young", "Species_A"), ("Young", "Species_B"),
                                      ("Old", "Species_A"), ("Old", "Species_B")]):
        expected = np.sort(DF[(DF.Age == age) & (DF.Species == sp)].Growth_cm.to_numpy(float))
        np.testing.assert_allclose(_points(ax), expected, rtol=0, atol=1e-12)
    assert _strips(r.figure) == ["Age: Old", "Age: Young", "Species: Species_A", "Species: Species_B"]


def test_box_grid_uses_one_category_order_one_colour_per_level_and_one_value_axis():
    _, r = _render(BOX_T, BOX)
    panels = facet_axes(r.figure)
    # same category positions in every panel; the bottom row (which shows them) reads 4, 6, 8, 10
    assert all(list(ax.get_xticks()) == list(panels[0].get_xticks()) for ax in panels)
    assert all([t.get_text() for t in ax.get_xticklabels()] == ["4", "6", "8", "10"] for ax in panels[2:])
    ylims = {tuple(np.round(ax.get_ylim(), 9)) for ax in panels}
    assert len(ylims) == 1
    lo, hi = ylims.pop()
    assert lo <= DF.Growth_cm.min() and hi >= DF.Growth_cm.max()
    host = facet_host(r.figure)
    leg = host.get_legend()
    assert [t.get_text() for t in leg.get_texts()] == ["Low N", "Medium N", "High N"]
    assert sum(1 for a in r.figure.axes if a.get_legend() is not None) == 1
    # each level's points have the same colour in every panel
    for ax in panels:
        colours = [tuple(np.round(c.get_facecolor()[0][:3], 3)) for c in ax.collections
                   if isinstance(c, PathCollection) and len(c.get_offsets())]
        assert len(set(colours)) == 3


def test_line_grid_means_and_standard_errors_match_pandas():
    _, r = _render(LINE_T, LINE)
    panels = facet_axes(r.figure)
    assert len(panels) == 4 and r.metadata["error_display"] == "bars"
    for ax, (age, sp) in zip(panels, [("Young", "Species_A"), ("Young", "Species_B"),
                                      ("Old", "Species_A"), ("Old", "Species_B")]):
        sub = DF[(DF.Age == age) & (DF.Species == sp)]
        g = sub.groupby(["Nitrogen_Concentration", "Month"]).Growth_cm
        for line in [ln for ln in ax.get_lines() if ln.get_label() in ("Low N", "Medium N", "High N")]:
            exp = g.mean().loc[line.get_label()].sort_index()
            np.testing.assert_allclose(line.get_ydata(), exp.to_numpy(), rtol=1e-12)
        # error-bar half-lengths are SD(ddof=1)/sqrt(n)
        se = (g.std(ddof=1) / np.sqrt(g.count())).to_numpy()
        bars = [seg for c in ax.collections if type(c).__name__ == "LineCollection"
                for seg in c.get_segments()]
        halves = sorted(round(abs(s[1][1] - s[0][1]) / 2, 9) for s in bars if len(s) == 2)
        np.testing.assert_allclose(halves, sorted(np.round(se, 9)), rtol=1e-7)


def test_columns_only_and_rows_only_grids():
    _, r = _render(BOX_T, {**BOX, "facet_row": None})
    assert len(facet_axes(r.figure)) == 2 and _strips(r.figure) == ["Species: Species_A", "Species: Species_B"]
    _, r = _render(LINE_T, {**LINE, "facet_col": None})
    assert len(facet_axes(r.figure)) == 2 and _strips(r.figure) == ["Age: Old", "Age: Young"]


def test_strip_labels_can_show_the_value_only():
    _, r = _render(BOX_T, {**BOX, "facet_labels": "value"})
    assert _strips(r.figure) == ["Old", "Species_A", "Species_B", "Young"]


def test_independent_value_axes_on_request():
    _, r = _render(BOX_T, {**BOX, "facet_share_y": False})
    ylims = {tuple(np.round(ax.get_ylim(), 6)) for ax in facet_axes(r.figure)}
    assert len(ylims) == 4


def test_shared_labels_title_and_inner_tick_labels():
    _, r = _render(BOX_T, BOX, layout={"title": "Plant growth", "x_label": "Month", "y_label": "Growth (cm)"})
    host = facet_host(r.figure)
    assert host.get_title() == "Plant growth" and host.get_xlabel() == "Month" and host.get_ylabel() == "Growth (cm)"
    panels = facet_axes(r.figure)
    r.figure.canvas.draw()
    shown = [(any(t.get_visible() and t.get_text() for t in ax.get_xticklabels()),
              any(t.get_visible() and t.get_text() for t in ax.get_yticklabels())) for ax in panels]
    assert shown == [(False, True), (False, False), (True, True), (True, False)]
    assert all(ax.get_xlabel() == "" and ax.get_ylabel() == "" for ax in panels)


def test_layout_controls_reach_the_grid():
    _, r = _render(BOX_T, BOX, layout={"show_x_label": False, "show_y_tick_labels": False, "x_tick_rotation": 45})
    host = facet_host(r.figure)
    assert host.get_xlabel() == ""
    for ax in facet_axes(r.figure):
        assert not any(t.get_visible() and t.get_text() for t in ax.get_yticklabels())
        assert all(t.get_rotation() == 45 for t in ax.get_xticklabels() if t.get_text())


@pytest.mark.parametrize("location", ["outside bottom", "outside top", "outside left", "outside right",
                                      "inside upper left"])
def test_legend_location_acts_on_the_grid_legend(location):
    _, r = _render(LINE_T, LINE, layout={"legend_location": location})
    host = facet_host(r.figure)
    leg = host.get_legend()
    assert leg is not None and sum(1 for a in r.figure.axes if a.get_legend() is not None) == 1
    r.figure.canvas.draw()
    rd = r.figure.canvas.get_renderer()
    lb, hb = leg.get_window_extent(rd), host.get_window_extent(rd)
    if location == "outside bottom":
        assert lb.y1 < hb.y0 and leg._ncols == 3
    elif location == "outside top":
        assert lb.y0 > hb.y1 - 1
    elif location == "outside left":
        assert lb.x1 < hb.x0 + 1
    elif location == "outside right":
        assert lb.x0 > hb.x1 - 1


def test_log_axis_on_a_grid_covers_every_panel():
    _, r = _render(BOX_T, BOX, layout={"y_scale": "log10", "y_tick_format": "plain"})
    for ax in facet_axes(r.figure):
        assert ax.get_yscale() == "log"
        lo, hi = ax.get_ylim()
        assert lo <= DF.Growth_cm.min() and hi >= DF.Growth_cm.max()


def test_statistics_run_within_each_panel():
    st = {"enabled": True, "test": "welch_t", "comparison_mode": "within_x"}
    _, r = _render(BOX_T, BOX, statistics=st)
    rep = r.stats_report
    assert rep is not None and rep.results
    facets = {res.extra.get("facet") for res in rep.results}
    assert facets == {"Age: Young | Species: Species_A", "Age: Young | Species: Species_B",
                      "Age: Old | Species: Species_A", "Age: Old | Species: Species_B"}
    assert "within each panel" in rep.method_paragraph


def test_spec_json_and_figure_package_round_trips_render_identically():
    s, r = _render(BOX_T, BOX, layout={"legend_location": "outside bottom", "title": "Growth"})
    a = figure_to_bytes(r.figure, "png", dpi=100)
    b = figure_to_bytes(C.render(json.loads(json.dumps(s)), DATA).figure, "png", dpi=100)
    assert a == b
    pkg = C.open_package(C.package_bytes(C.package_content(DATA, s, r, name="facets")))
    d2, s2 = C.loaded_from_package(pkg)
    assert figure_to_bytes(C.render(s2, d2).figure, "png", dpi=100) == a


def test_an_empty_panel_is_kept_and_labelled():
    messy = pd.DataFrame({"g": ["a", "a", "b", "b"], "h": ["x", "x", "y", "y"], "t": [1, 2, 1, 2],
                          "v": [1.0, 2.0, 3.0, 4.0]})
    d = C.loaded_from_dataframe(messy, "m.csv")
    _, r = _render(BOX_T, {"x": "t", "y": "v", "facet_row": "g", "facet_col": "h"}, data=d)
    panels = facet_axes(r.figure)
    assert len(panels) == 4
    empties = [ax for ax in panels if any("no observations" in t.get_text() for t in ax.texts)]
    assert len(empties) == 2


def test_facet_options_are_not_written_without_facets_and_defaults_render_as_before():
    s, _ = _render(BOX_T, {"x": "Month", "y": "Growth_cm"})
    assert "facet_row" not in s["mapping"] and "facet_labels" not in s["mapping"]
    from make_my_figure_core.plots.facets import wants_facets

    assert not wants_facets(s)


def test_host_and_strips_are_decorations_for_the_figure_builder():
    from make_my_figure_core.panels.builder import _data_axes

    _, r = _render(BOX_T, BOX)
    data_axes = _data_axes(r.figure)
    assert all(a.get_label() not in (FACET_HOST_LABEL, FACET_STRIP_LABEL) for a in data_axes)
    assert len(data_axes) == 4


def test_long_level_names_are_wrapped_or_shrunk_into_their_strips():
    long = DF.copy()
    long["Species"] = long.Species.map({"Species_A": "Arabidopsis thaliana ecotype Columbia-0 greenhouse line",
                                        "Species_B": "Brassica napus winter cultivar long-day treatment line"})
    _, r = _render(BOX_T, BOX, data=C.loaded_from_dataframe(long, "long.csv"))
    r.figure.canvas.draw()
    rd = r.figure.canvas.get_renderer()
    for a in r.figure.axes:
        if a.get_label() == FACET_STRIP_LABEL and a.texts:
            sb, tb = a.get_window_extent(rd), a.texts[0].get_window_extent(rd)
            assert tb.x0 >= sb.x0 - 1 and tb.x1 <= sb.x1 + 1 and tb.y0 >= sb.y0 - 1 and tb.y1 <= sb.y1 + 1, \
                a.texts[0].get_text()


def test_whole_grid_anova_uses_the_facet_variables_as_factors():
    from make_my_figure_core.statistics.factorial import factorial_anova

    st = {"enabled": True, "test": "factorial_anova", "facet_scope": "figure"}
    _, r = _render(BOX_T, {**BOX, "hue": None}, statistics=st)
    rep = r.stats_report
    grid_rows = [x for x in rep.results if x.extra.get("facet") == "whole grid"]
    panel_rows = [x for x in rep.results if x.extra.get("facet") != "whole grid"]
    assert panel_rows and grid_rows
    # the same model, fitted directly: Growth ~ Month * Age * Species
    direct = factorial_anova(DF, "Growth_cm", ["Month", "Age", "Species"])
    assert len(grid_rows) == len(direct) == 7
    for ours, ref in zip(grid_rows, direct):
        assert ours.group_a.endswith(ref.group_a) and ours.statistic == pytest.approx(ref.statistic, rel=1e-12)
        assert ours.p_value == pytest.approx(ref.p_value, rel=1e-9)
    assert "fitted once across the whole grid" in rep.method_paragraph
    # four factors (x, hue, row, col) is beyond the engine: explained, not computed
    _, r = _render(BOX_T, BOX, statistics=st)
    assert any("exceed the three" in w for w in r.warnings)
    assert not [x for x in r.stats_report.results if x.extra.get("facet") == "whole grid"]


def test_whole_grid_pairwise_pools_the_panels():
    st = {"enabled": True, "test": "welch_t", "comparison_mode": "all_pairs", "facet_scope": "figure"}
    _, r = _render(BOX_T, {**BOX, "hue": None}, statistics=st)
    grid_rows = [x for x in r.stats_report.results if x.extra.get("facet") == "whole grid"]
    assert len(grid_rows) == 6                       # 4 months, all pairs, once
    assert all(x.n_total == 120 for x in grid_rows)  # two months x 60 rows, pooled over panels


def test_brackets_on_a_shared_axis_do_not_compound_across_panels(monkeypatch):
    # Each panel stacks its brackets from the same starting limits and the shared
    # axis takes the largest result. Stacking one panel after another on the
    # already stretched axis reached y = 115 where the tallest panel needs 107.
    import make_my_figure_core.plots.stats_overlay as overlay

    calls = []
    original = overlay.annotate_pairwise

    def spy(ax, *args, **kwargs):
        before = ax.get_ylim()
        out = original(ax, *args, **kwargs)
        calls.append((before, ax.get_ylim()[1]))
        return out

    monkeypatch.setattr(overlay, "annotate_pairwise", spy)
    st = {"enabled": True, "test": "welch_t", "comparison_mode": "all_pairs"}
    _, r = _render(BOX_T, BOX, statistics=st)
    assert len(calls) == 4
    starts = {tuple(np.round(b, 6)) for b, _ in calls}
    assert len(starts) == 1, starts                       # every panel started from the same limits
    tops = {round(a.get_ylim()[1], 6) for a in facet_axes(r.figure)}
    assert tops == {round(max(t for _, t in calls), 6)}  # the union, not a running total


@pytest.mark.parametrize("pt,mapping", [(BOX_T, BOX), (LINE_T, LINE)])
def test_a_range_on_a_shared_axis_is_checked_against_every_panel(pt, mapping):
    # y_max 40 was checked against the first panel (max 33.8) and applied to all
    # four, cutting points above 40 off panels 2 and 4 with no warning.
    _, r = _render(pt, mapping, layout={"y_max": 40.0})
    drawn_max = max(plotted_values(ax, "y").max() for ax in facet_axes(r.figure))   # raw points (box) or means/bands (line)
    assert drawn_max > 40.0
    assert all(ax.get_ylim()[1] >= drawn_max for ax in facet_axes(r.figure))
    assert any("would hide plotted values" in w and f"{drawn_max:.4g}"[:4] in w for w in r.warnings), r.warnings
    _, r = _render(pt, mapping, layout={"y_max": 60.0})
    assert all(ax.get_ylim()[1] == pytest.approx(60.0) for ax in facet_axes(r.figure))


def test_a_level_name_override_recolours_every_panel_and_the_legend():
    from matplotlib.colors import to_rgb

    _, r = _render(LINE_T, LINE, style={"color_overrides": {"Low N": "#ff00ff"}})
    for ax in facet_axes(r.figure):
        low = [ln for ln in ax.get_lines() if ln.get_label() == "Low N"]
        assert low and all(to_rgb(ln.get_color()) == to_rgb("#ff00ff") for ln in low)
    leg = facet_host(r.figure).get_legend()
    swatch = {t.get_text(): to_rgb(h.get_color()) for h, t in zip(leg.legend_handles, leg.get_texts())}
    assert swatch["Low N"] == to_rgb("#ff00ff")
