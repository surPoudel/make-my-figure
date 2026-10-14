"""Axis display scaling: a log axis changes how values are drawn, never the values.

Every applicable plot type is rendered linear and log; the plotted data, the
statistics and the input table must be identical. Refusals (zero/negative values,
an already-log column, a non-positive axis limit, an axis without magnitude) must
be reported, never silent.
"""
import copy
import json
import math

import numpy as np
import pandas as pd
import pytest

from apps.desktop_app.controller import DesktopController
from make_my_figure_core.plots.axis_scale import plotted_values
from make_my_figure_core.plots.registry import available_plot_types
from make_my_figure_core.styles.capabilities import AXIS_SCALE_AXES, axis_scale_support

CTRL = DesktopController()
SUPPORTED = sorted(AXIS_SCALE_AXES)
UNSUPPORTED = sorted(set(available_plot_types()) - set(AXIS_SCALE_AXES))


def _render(pt, layout=None, data=None, mapping=None, statistics=None):
    data = data or CTRL.load_example(pt)
    spec = CTRL.build_spec(pt, "publication", data.table_name, mapping or CTRL.default_mapping(pt),
                           statistics=statistics)
    if layout:
        spec.setdefault("layout", {}).update(layout)
    return spec, CTRL.render(spec, data), data


def _labels(ax, axis):
    ax.figure.canvas.draw()
    ticks = ax.get_yticklabels() if axis == "y" else ax.get_xticklabels()
    lo, hi = sorted(ax.get_ylim() if axis == "y" else ax.get_xlim())
    return [t.get_text() for t in ticks if t.get_text() and lo <= t.get_position()[1 if axis == "y" else 0] <= hi]


def test_every_plot_type_has_an_axis_scale_decision():
    for pt in available_plot_types():
        for axis in "xy":
            ok, reason = axis_scale_support(pt, axis)
            assert ok or reason, (pt, axis)


@pytest.mark.parametrize("pt", SUPPORTED)
@pytest.mark.parametrize("fmt", ["auto", "plain", "power"])
def test_log_axis_draws_the_same_values(pt, fmt):
    x_ok, y_ok = AXIS_SCALE_AXES[pt]
    _, lin, data = _render(pt)
    before = data.info.dataframe.copy()
    layout = {"y_scale": "log10", "y_tick_format": fmt}
    _, log, _ = _render(pt, layout, data=data)
    ax0, ax1 = lin.figure.axes[0], log.figure.axes[0]
    assert ax1.get_yscale() == "log"
    np.testing.assert_array_equal(np.sort(plotted_values(ax0, "y")), np.sort(plotted_values(ax1, "y")))
    np.testing.assert_array_equal(np.sort(plotted_values(ax0, "x")), np.sort(plotted_values(ax1, "x")))
    pd.testing.assert_frame_equal(data.info.dataframe, before)
    lo, hi = ax1.get_ylim()
    vals = plotted_values(ax1, "y")
    assert 0 < lo <= vals.min() and hi >= vals.max(), "log limits must contain every plotted value"
    assert len(_labels(ax1, "y")) >= 2, f"{pt}: fewer than two labelled ticks"


@pytest.mark.parametrize("pt", ["barplot_with_error_bar", "boxplot_or_violin_with_points"])
def test_statistics_do_not_change_with_axis_scale(pt):
    st = {"enabled": True, "test": "welch_t", "comparison_mode": "all_pairs"}
    _, lin, data = _render(pt, statistics=st)
    _, log, _ = _render(pt, {"y_scale": "log10"}, data=data, statistics=st)
    a = [r.to_dict() for r in lin.stats_report.results]
    b = [r.to_dict() for r in log.stats_report.results]
    assert len(a) == len(b) > 0
    for ra, rb in zip(a, b):
        for k in ("statistic", "p_value", "adjusted_p_value", "effect_size", "n_total"):
            assert ra.get(k) == rb.get(k) or (ra.get(k) != ra.get(k) and rb.get(k) != rb.get(k)), k


@pytest.mark.parametrize("pt", UNSUPPORTED)
def test_axis_scale_on_a_plot_without_magnitude_is_reported_not_applied(pt):
    _, base, data = _render(pt)
    _, res, _ = _render(pt, {"y_scale": "log10", "x_scale": "log10"}, data=data)
    if not res.figure.axes:
        return
    a0, a1 = base.figure.axes[0], res.figure.axes[0]
    assert (a1.get_xscale(), a1.get_yscale()) == (a0.get_xscale(), a0.get_yscale())
    assert any("not available for this plot" in w for w in res.warnings), res.warnings


def _frame(values):
    return pd.DataFrame({"g": ["a", "b", "c", "d"] * (len(values) // 4), "v": values})


def _custom(pt, df, layout, y="v"):
    data = CTRL.loaded_from_dataframe(df, "t.csv")
    return _render(pt, layout, data=data, mapping={"x": "g", "y": y})


def test_log_axis_refused_with_zero_or_negative_values():
    for values in ([0.0, 1, 10, 100] * 3, [-5.0, 1, 10, 100] * 3):
        _, res, _ = _custom("dot_strip_plot", _frame(values), {"y_scale": "log10"})
        assert res.figure.axes[0].get_yscale() == "linear"
        assert any("include 0 or negative" in w for w in res.warnings)


def test_log_axis_refused_on_a_column_that_is_already_log():
    df = _frame([0.5, 1.0, 1.5, 2.0] * 3).rename(columns={"v": "log10(count)"})
    _, res, _ = _custom("dot_strip_plot", df, {"y_scale": "log10"}, y="log10(count)")
    assert res.figure.axes[0].get_yscale() == "linear"
    assert any("apply the logarithm twice" in w for w in res.warnings)


def test_non_positive_axis_minimum_is_refused_and_positive_limits_are_kept():
    df = _frame([2.0, 20, 200, 2000] * 3)
    _, res, _ = _custom("dot_strip_plot", df, {"y_scale": "log10", "y_min": 0})
    assert res.figure.axes[0].get_yscale() == "linear"
    assert any("must be greater than 0" in w for w in res.warnings)
    for pt in SUPPORTED:
        if not AXIS_SCALE_AXES[pt][1]:
            continue
        _, lin, data = _render(pt)
        vals = plotted_values(lin.figure.axes[0], "y")
        lo, hi = vals.min() / 2, vals.max() * 2
        _, res, _ = _render(pt, {"y_scale": "log10", "y_min": lo, "y_max": hi}, data=data)
        ax = res.figure.axes[0]
        assert ax.get_yscale() == "log" and ax.get_ylim() == pytest.approx((lo, hi)), pt
        _, res, _ = _render(pt, {"y_min": vals.min() * 1.5}, data=data)
        assert any("would hide plotted values" in w or "would hide data" in w for w in res.warnings) \
            or res.figure is None, pt


def test_wide_range_plain_labels_read_like_ordinary_numbers():
    df = _frame([1e4, 1e5, 1e6, 1e7] * 3)
    _, res, _ = _custom("dot_strip_plot", df, {"y_scale": "log10", "y_tick_format": "plain"})
    labels = _labels(res.figure.axes[0], "y")
    assert {"100,000", "1,000,000", "10,000,000"} <= set(labels), labels


def test_power_labels_label_every_tick_across_a_decade_and_a_half():
    df = _frame([1.2e6, 3e6, 9e6, 3.2e7] * 3)
    _, res, _ = _custom("dot_strip_plot", df, {"y_scale": "log10", "y_tick_format": "power"})
    labels = _labels(res.figure.axes[0], "y")
    assert len(labels) >= 3 and all("10^" in t for t in labels), labels


@pytest.mark.parametrize("scale,base", [("log2", 2.0), ("ln", math.e)])
def test_other_bases_tick_on_powers_of_their_base(scale, base):
    df = _frame([1.0, 8, 64, 4096] * 3)
    _, res, _ = _custom("dot_strip_plot", df, {"y_scale": scale})
    ax = res.figure.axes[0]
    assert ax.get_yscale() == "log" and ax.yaxis.get_transform().base == pytest.approx(base)
    lo, hi = ax.get_ylim()
    ticks = [t for t in ax.get_yticks() if lo <= t <= hi]
    assert ticks and all(abs(math.log(t, base) - round(math.log(t, base))) < 1e-9 for t in ticks)


def test_scientific_notation_on_a_linear_axis_is_not_a_log_scale():
    df = _frame([1e6, 2e6, 4e6, 8e6] * 3)
    _, res, _ = _custom("dot_strip_plot", df, {"y_tick_format": "scientific"})
    ax = res.figure.axes[0]
    ax.figure.canvas.draw()
    assert ax.get_yscale() == "linear"
    assert "10^{6}" in ax.yaxis.get_offset_text().get_text() or "10^6" in ax.yaxis.get_offset_text().get_text()
    _, plain, _ = _custom("dot_strip_plot", df, {})
    np.testing.assert_array_equal(np.sort(plotted_values(ax, "y")), np.sort(plotted_values(plain.figure.axes[0], "y")))


def test_power_labels_on_a_linear_axis_are_reported():
    _, res, _ = _custom("dot_strip_plot", _frame([1.0, 2, 3, 4] * 3), {"y_tick_format": "power"})
    assert any("need a logarithmic axis" in w for w in res.warnings)


def test_bars_on_a_log_axis_carry_the_baseline_caveat():
    _, res, _ = _render("barplot_with_error_bar", {"y_scale": "log10"})
    assert any("compare bar tops" in w for w in res.warnings)


def test_untouched_spec_gets_no_axis_scale_keys_and_no_notes():
    spec, res, _ = _render("dot_strip_plot")
    assert not any(k in (spec.get("layout") or {}) for k in ("y_scale", "y_tick_format", "y_minor_ticks"))
    assert not any("axis not applied" in w or "logarithmic" in w for w in res.warnings)


def test_axis_scale_keys_survive_json_round_trip_and_render_identically():
    from make_my_figure_core.plots.registry import figure_to_bytes

    spec, res, data = _render("dot_strip_plot", {"y_scale": "log10", "y_tick_format": "plain",
                                                 "y_minor_ticks": False})
    spec2 = json.loads(json.dumps(spec))
    res2 = CTRL.render(spec2, data)
    a = figure_to_bytes(res.figure, "png", dpi=100)
    b = figure_to_bytes(res2.figure, "png", dpi=100)
    assert a == b
    assert copy.deepcopy(spec2["layout"])["y_scale"] == "log10"


@pytest.mark.parametrize("layout,max_covered", [({}, 0), ({"x_scale": "log10"}, 0), ({"y_scale": "log10"}, 0),
                                                ({"x_scale": "log10", "y_scale": "log10"}, 1)])
def test_regression_statistics_box_stays_off_the_data_and_the_legend(layout, max_covered):
    # On a log axis the legend ("best") took the one empty corner and the box was
    # pushed onto 11 (log x) and 19 (log y) of 60 points; then, once the box could
    # take that corner, "best" settled the legend on the box. Linear: 0 covered,
    # unchanged.
    _, res, _ = _render("scatterplot_with_regression", layout)
    ax = res.figure.axes[0]
    res.figure.canvas.draw()
    rd = res.figure.canvas.get_renderer()
    box = [t for t in ax.texts if "R²" in t.get_text()][0].get_window_extent(rd)
    pts = np.concatenate([ax.transData.transform(c.get_offsets()) for c in ax.collections if len(c.get_offsets())])
    covered = int(((pts[:, 0] >= box.x0) & (pts[:, 0] <= box.x1) & (pts[:, 1] >= box.y0) & (pts[:, 1] <= box.y1)).sum())
    assert covered <= max_covered, covered
    lb = ax.get_legend().get_window_extent(rd)
    assert lb.x1 < box.x0 or lb.x0 > box.x1 or lb.y1 < box.y0 or lb.y0 > box.y1, "legend overlaps the statistics box"


# --- findings of the independent review ------------------------------------------------

def test_a_truncated_linear_bar_axis_is_still_refused():
    # Moving layout limits to the central step dropped the bar base from the check:
    # y_min = 45 on bars of ~51-59 was drawn, exaggerating differences ~2.6-fold.
    df = pd.DataFrame({"g": list("abc") * 4, "v": [51.0, 55.0, 59.0] * 4})
    data = CTRL.loaded_from_dataframe(df, "t.csv")
    _, res, _ = _render("barplot_with_error_bar", {"y_min": 45}, data=data, mapping={"x": "g", "y": "v"})
    assert res.figure.axes[0].get_ylim()[0] == 0.0
    assert any("truncated value axis" in w for w in res.warnings)


def test_legacy_log_scale_on_other_plot_types_still_draws_log():
    _, res, _ = _render("histogram_distribution", {"y_scale": "log"})
    assert res.figure.axes[0].get_yscale() == "log"
    assert not any("not available" in w for w in res.warnings)


def test_a_range_on_a_plot_with_its_own_range_option_is_not_contradicted():
    _, res, _ = _render("histogram_distribution", {"y_min": 0, "y_max": 100})
    assert not any("not available" in w for w in res.warnings)


@pytest.mark.parametrize("pt", ["barplot_with_error_bar", "boxplot_or_violin_with_points",
                                "grouped_barplot_with_error_bar", "dot_strip_plot"])
def test_significance_labels_stay_inside_a_log_axis(pt):
    st = {"enabled": True, "test": "welch_t", "comparison_mode": "all_pairs"}
    _, res, _ = _render(pt, {"y_scale": "log10"}, statistics=st)
    fig, ax = res.figure, res.figure.axes[0]
    fig.canvas.draw()
    rd = fig.canvas.get_renderer()
    top = ax.get_window_extent(rd).y1
    out = [t.get_text() for t in ax.texts if t.get_text().strip() and t.get_window_extent(rd).y1 > top + 1]
    assert not out, out


@pytest.mark.parametrize("name,expected", [("log10(count)", True), ("-log10 P", True), ("log2FC", True),
                                           ("log fold change", True), ("catalog_id", False),
                                           ("blog_views", False), ("dialog", False), ("biologic", False)])
def test_already_log_names_are_matched_as_whole_words(name, expected):
    from make_my_figure_core.tabular import looks_already_log

    assert looks_already_log(name) is expected
