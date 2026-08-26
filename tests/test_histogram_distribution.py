"""Histogram plot type: binned counts, shared bins across groups, honest handling of unequal n.

Added because there was no way to draw a histogram at all: the nearest plot type was the ridge /
density plot, which smooths. For a distribution that is not unimodal that substitution is not
cosmetic - a kernel density estimate can render two modes as one shoulder - so a request for
"a histogram of each group" had no correct answer.

The properties pinned here are the ones that are invisible once the figure is drawn: that both
groups were binned on the *same* edges, that the counts are the real counts, and that a
misleading arrangement is warned about rather than left to the reader.

All fixtures are synthetic and built in-test.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.plots.base import RenderError
from make_my_figure_core.plots.registry import make_spec, render

PLOT = "histogram_distribution"


def _bimodal(rng, n, w_small, mu1, mu2):
    small = rng.normal(mu1, 3.0, int(n * w_small))
    large = rng.normal(mu2, 6.0, n - int(n * w_small))
    return np.concatenate([small, large])


def _two_groups(n_a=600, n_b=400, seed=3) -> pd.DataFrame:
    """Two bimodal groups of deliberately different size."""
    rng = np.random.default_rng(seed)
    rows = []
    for name, n in (("A", n_a), ("B", n_b)):
        for v in _bimodal(rng, n, 0.4, 14.0, 31.0):
            rows.append({"grp": name, "val": float(v)})
    return pd.DataFrame(rows)


def _render(mapping, df, layout=None):
    spec = make_spec(PLOT, "synthetic", "publication", mapping=mapping, layout=layout or {})
    return render(spec, df)


def _bar_heights(ax):
    """Heights of the step patches on an axes, in draw order."""
    from matplotlib.patches import StepPatch
    out = []
    for patch in ax.patches:
        if isinstance(patch, StepPatch):
            out.append(np.asarray(patch.get_data()[0], dtype=float))
    return out


# --------------------------------------------------------------------------------------
# it is registered everywhere a plot type has to be registered
# --------------------------------------------------------------------------------------

def test_plot_type_is_wired_into_every_surface():
    from make_my_figure_core import ui_hints
    from make_my_figure_core.plots.registry import (
        _DEFAULT_MAPPINGS, _DISPLAY_NAMES, _RENDERERS, available_plot_types, display_name)

    assert PLOT in _RENDERERS
    assert PLOT in _DEFAULT_MAPPINGS
    assert PLOT in _DISPLAY_NAMES
    assert PLOT in available_plot_types()
    assert display_name(PLOT) != PLOT, "needs a human-readable display name"
    # both GUIs build their controls from these two, so a missing entry means no widgets
    assert ui_hints.column_fields(PLOT) == ["x", "group", "value_columns"]
    assert {o.key for o in ui_hints.options(PLOT)} == {
        "input_form", "panel_mode", "draw_style", "normalize", "cumulative", "bins", "bin_width",
        "show_mean", "show_median", "bar_alpha", "log_y", "share_axes",
        "x_min", "x_max", "y_min", "y_max", "x_tick_rotation"}


def test_optional_numeric_options_declare_no_default():
    """A frontend renders "(auto)" from default=None; a 0 default would force a real value."""
    from make_my_figure_core import ui_hints

    options = {o.key: o for o in ui_hints.options(PLOT)}
    for key in ("bins", "bin_width", "bar_alpha", "x_min", "x_max", "y_min", "y_max"):
        assert options[key].default is None, f"{key} must default to unset"
        # the sentinel a spin box uses for "(auto)" has to sit outside the real value range
        assert options[key].minimum < 0


def test_bundled_example_renders():
    from make_my_figure_core import examples as ex

    info, aux, spec = ex.load_example(PLOT)
    res = render(spec, info.dataframe)
    try:
        assert res.metadata["n_bins"] >= 2
    finally:
        plt.close(res.figure)


# --------------------------------------------------------------------------------------
# the counts drawn are the real counts
# --------------------------------------------------------------------------------------

def test_bar_heights_are_the_actual_counts():
    df = pd.DataFrame({"val": [1.0, 1.5, 2.5, 2.6, 2.7, 3.5]})
    res = _render({"x": "val", "bin_width": 1.0}, df)
    try:
        edges = np.arange(1.0, 5.0)          # 1-2, 2-3, 3-4
        expected, _ = np.histogram(df["val"], bins=edges)
        drawn = _bar_heights(res.figure.axes[0])
        assert drawn, "no step patches were drawn"
        assert np.array_equal(drawn[0][:len(expected)], expected.astype(float))
        assert drawn[0].sum() == len(df), "every observation must land in exactly one bin"
    finally:
        plt.close(res.figure)


def test_percent_normalisation_sums_to_100_per_group():
    df = _two_groups()
    res = _render({"x": "val", "group": "grp", "panel_mode": "overlay",
                   "normalize": "percent"}, df)
    try:
        for heights in _bar_heights(res.figure.axes[0]):
            assert heights.sum() == pytest.approx(100.0)
    finally:
        plt.close(res.figure)


def test_density_normalisation_integrates_to_one():
    df = _two_groups()
    res = _render({"x": "val", "group": "grp", "panel_mode": "overlay",
                   "normalize": "density", "bin_width": 2.0}, df)
    try:
        for heights in _bar_heights(res.figure.axes[0]):
            assert (heights * 2.0).sum() == pytest.approx(1.0)
    finally:
        plt.close(res.figure)


def test_bimodality_survives_the_default_binning():
    """The reason this plot type exists: a smoother can erase a second mode, bins cannot."""
    df = _two_groups(n_a=1200, n_b=1200, seed=9)
    res = _render({"x": "val", "bin_width": 2.0}, df)
    try:
        heights = _bar_heights(res.figure.axes[0])[0]
        # a dip strictly between two peaks
        peak = heights.argmax()
        other = heights[:max(peak - 3, 1)].argmax() if peak > 4 else heights[peak + 3:].argmax()
        assert heights.min() < heights.max()
        interior = heights[1:-1]
        rises = np.sum(np.diff(interior) > 0)
        falls = np.sum(np.diff(interior) < 0)
        assert rises >= 2 and falls >= 2, "a bimodal input should rise, fall and rise again"
    finally:
        plt.close(res.figure)


# --------------------------------------------------------------------------------------
# shared bins - the thing that is impossible to check by looking
# --------------------------------------------------------------------------------------

def test_groups_are_binned_on_identical_edges():
    df = _two_groups()
    res = _render({"x": "val", "group": "grp", "panel_mode": "overlay"}, df)
    try:
        from matplotlib.patches import StepPatch
        edge_sets = [tuple(np.round(p.get_data()[1], 9)) for p in res.figure.axes[0].patches
                     if isinstance(p, StepPatch)]
        assert len(edge_sets) >= 2
        assert len(set(edge_sets)) == 1, "each group was binned differently"
        assert res.metadata["shared_bins"] is True
    finally:
        plt.close(res.figure)


def test_panels_share_edges_and_axes_so_they_can_be_compared():
    df = _two_groups()
    res = _render({"x": "val", "group": "grp", "panel_mode": "panels"}, df)
    try:
        axes = [a for a in res.figure.axes if a.get_visible()]
        assert len(axes) == 2
        assert axes[0].get_xlim() == axes[1].get_xlim()
        assert axes[0].get_ylim() == axes[1].get_ylim()
    finally:
        plt.close(res.figure)


def test_panels_can_be_unshared_when_asked():
    df = _two_groups(n_a=900, n_b=120)
    res = _render({"x": "val", "group": "grp", "panel_mode": "panels",
                   "share_axes": False}, df)
    try:
        axes = [a for a in res.figure.axes if a.get_visible()]
        assert axes[0].get_ylim() != axes[1].get_ylim()
        # the bins are still shared - only the axis scaling was released
        assert res.metadata["shared_bins"] is True
    finally:
        plt.close(res.figure)


def test_each_panel_is_labelled_with_its_own_n():
    df = _two_groups(n_a=600, n_b=400)
    res = _render({"x": "val", "group": "grp", "panel_mode": "panels"}, df)
    try:
        titles = " ".join(a.get_title() for a in res.figure.axes if a.get_visible())
        assert "n=600" in titles and "n=400" in titles
        assert res.metadata["n_by_group"] == {"A": 600, "B": 400}
    finally:
        plt.close(res.figure)


# --------------------------------------------------------------------------------------
# unequal n
# --------------------------------------------------------------------------------------

def test_overlaid_raw_counts_with_unequal_n_are_warned_about():
    """The comparison is dominated by the larger group whatever its shape."""
    df = _two_groups(n_a=1800, n_b=1200)
    res = _render({"x": "val", "group": "grp", "panel_mode": "overlay",
                   "normalize": "count"}, df)
    try:
        assert any("Group sizes differ" in w and "percent" in w for w in res.warnings)
    finally:
        plt.close(res.figure)


def test_no_warning_once_normalised_or_in_panels():
    df = _two_groups(n_a=1800, n_b=1200)
    for mapping in ({"panel_mode": "overlay", "normalize": "percent"},
                    {"panel_mode": "panels", "normalize": "count"}):
        res = _render({"x": "val", "group": "grp", **mapping}, df)
        try:
            assert not any("Group sizes differ" in w for w in res.warnings), mapping
        finally:
            plt.close(res.figure)


def test_equal_group_sizes_are_not_warned_about():
    df = _two_groups(n_a=500, n_b=500)
    res = _render({"x": "val", "group": "grp", "panel_mode": "overlay"}, df)
    try:
        assert not any("Group sizes differ" in w for w in res.warnings)
    finally:
        plt.close(res.figure)


# --------------------------------------------------------------------------------------
# bin selection
# --------------------------------------------------------------------------------------

def test_bin_width_is_honoured_and_edges_start_on_a_round_multiple():
    df = pd.DataFrame({"val": [10.37, 22.1, 41.9, 58.6]})
    res = _render({"x": "val", "bin_width": 2.0}, df)
    try:
        assert res.metadata["bin_width"] == pytest.approx(2.0)
        assert res.metadata["bin_range"][0] == pytest.approx(10.0)   # not 10.37
        assert res.metadata["bin_selection"] == "bin_width=2"
    finally:
        plt.close(res.figure)


def test_bin_count_is_honoured():
    df = _two_groups()
    res = _render({"x": "val", "bins": 12}, df)
    try:
        assert res.metadata["n_bins"] == 12
    finally:
        plt.close(res.figure)


def test_setting_both_bins_and_bin_width_is_refused():
    """Two ways of saying the same thing; a silent winner would change every bar."""
    df = _two_groups()
    with pytest.raises(RenderError, match="not both"):
        _render({"x": "val", "bins": 10, "bin_width": 2.0}, df)


@pytest.mark.parametrize("mapping,match", [
    ({"bin_width": 0}, "positive number"),
    ({"bin_width": -2}, "positive number"),
    ({"bin_width": 10_000}, "wider than the data range"),
    ({"bins": 0}, "at least 1"),
    ({"normalize": "log"}, "normalize must be"),
    ({"panel_mode": "grid"}, "panel_mode must be"),
])
def test_invalid_options_are_refused(mapping, match):
    df = _two_groups()
    with pytest.raises(RenderError, match=match):
        _render({"x": "val", "group": "grp", **mapping}, df)


def test_automatic_binning_is_recorded_so_a_figure_can_be_reproduced():
    df = _two_groups()
    res = _render({"x": "val", "group": "grp"}, df)
    try:
        assert "auto" in res.metadata["bin_selection"]
        assert res.metadata["n_bins"] >= 2
        assert res.metadata["bin_width"] > 0
    finally:
        plt.close(res.figure)


# --------------------------------------------------------------------------------------
# axis overrides, degenerate input, and the no-mutation contract
# --------------------------------------------------------------------------------------

def test_x_range_that_would_cut_bars_off_is_refused():
    """Step patches are not lines; the shared guard had to learn to see them."""
    df = _two_groups()
    with pytest.raises(RenderError, match="would hide data"):
        _render({"x": "val", "group": "grp", "x_max": 20}, df)


def test_a_wider_x_range_is_accepted():
    df = _two_groups()
    res = _render({"x": "val", "group": "grp", "x_min": -10, "x_max": 90}, df)
    try:
        assert res.metadata["axis_overrides"]["x_limits"] == [-10.0, 90.0]
    finally:
        plt.close(res.figure)


def test_group_with_no_finite_values_is_reported_not_dropped_silently():
    df = pd.DataFrame({"grp": ["A"] * 5 + ["B"] * 5,
                       "val": [1.0, 2.0, 3.0, 4.0, 5.0] + [np.nan] * 5})
    res = _render({"x": "val", "group": "grp"}, df)
    try:
        assert any("Group 'B'" in w and "left out" in w for w in res.warnings)
        assert res.metadata["groups"] == ["A"]
    finally:
        plt.close(res.figure)


def test_a_single_distinct_value_still_draws():
    df = pd.DataFrame({"val": [7.0] * 20})
    res = _render({"x": "val"}, df)
    try:
        assert res.metadata["n_bins"] == 1
        assert _bar_heights(res.figure.axes[0])[0].sum() == 20
    finally:
        plt.close(res.figure)


def test_no_numeric_values_at_all_is_an_error():
    df = pd.DataFrame({"val": [np.nan, np.nan]})
    with pytest.raises(RenderError):
        _render({"x": "val"}, df)


def test_input_dataframe_is_not_mutated():
    df = _two_groups()
    before = df.copy(deep=True)
    res = _render({"x": "val", "group": "grp"}, df)
    plt.close(res.figure)
    pd.testing.assert_frame_equal(df, before)


# --------------------------------------------------------------------------------------
# y-axis modes
# --------------------------------------------------------------------------------------

def test_frequency_normalisation_sums_to_one_per_group():
    """'frequency' is the relative frequency - the fraction of its own group."""
    df = _two_groups()
    res = _render({"x": "val", "group": "grp", "panel_mode": "overlay",
                   "normalize": "frequency"}, df)
    try:
        for heights in _bar_heights(res.figure.axes[0]):
            assert heights.sum() == pytest.approx(1.0)
    finally:
        plt.close(res.figure)


@pytest.mark.parametrize("normalize,expected_label", [
    ("count", "Count"),
    ("frequency", "Relative frequency"),
    ("percent", "Percentage of group (%)"),
    ("density", "Density"),
])
def test_y_label_names_what_the_axis_shows(normalize, expected_label):
    df = _two_groups()
    res = _render({"x": "val", "normalize": normalize}, df)
    try:
        assert res.figure.axes[0].get_ylabel() == expected_label
    finally:
        plt.close(res.figure)


def test_a_supplied_y_label_is_not_overridden():
    df = _two_groups()
    res = _render({"x": "val", "normalize": "percent"}, df,
                  layout={"y_label": "Number of myofibres"})
    try:
        assert res.figure.axes[0].get_ylabel() == "Number of myofibres"
    finally:
        plt.close(res.figure)


# --------------------------------------------------------------------------------------
# cumulative
# --------------------------------------------------------------------------------------

def test_cumulative_counts_rise_to_n():
    df = _two_groups(n_a=600, n_b=400)
    res = _render({"x": "val", "group": "grp", "panel_mode": "overlay",
                   "cumulative": True, "normalize": "count"}, df)
    try:
        # bars draw a fill and an outline patch per group, so endpoints repeat
        totals = sorted({float(h[-1]) for h in _bar_heights(res.figure.axes[0])})
        assert totals == [400.0, 600.0]
        for heights in _bar_heights(res.figure.axes[0]):
            assert np.all(np.diff(heights) >= 0), "a cumulative curve must never fall"
    finally:
        plt.close(res.figure)


@pytest.mark.parametrize("normalize,top", [("percent", 100.0), ("frequency", 1.0),
                                           ("density", 1.0)])
def test_cumulative_normalised_forms_end_at_their_maximum(normalize, top):
    """A cumulative density is a distribution function: it reaches 1, not 1/bin width."""
    df = _two_groups()
    res = _render({"x": "val", "group": "grp", "panel_mode": "overlay",
                   "cumulative": True, "normalize": normalize, "bin_width": 2.0}, df)
    try:
        for heights in _bar_heights(res.figure.axes[0]):
            assert float(heights[-1]) == pytest.approx(top)
    finally:
        plt.close(res.figure)


def test_cumulative_relabels_the_axis():
    df = _two_groups()
    res = _render({"x": "val", "cumulative": True, "normalize": "count"}, df)
    try:
        assert res.figure.axes[0].get_ylabel() == "Cumulative count"
        assert res.metadata["cumulative"] is True
    finally:
        plt.close(res.figure)


def test_cumulative_bin_width_does_not_change_the_endpoint():
    """The endpoint of a CDF is a property of the data, not of the binning."""
    df = _two_groups()
    ends = []
    for width in (1.0, 5.0):
        res = _render({"x": "val", "cumulative": True, "normalize": "density",
                       "bin_width": width}, df)
        ends.append(float(_bar_heights(res.figure.axes[0])[0][-1]))
        plt.close(res.figure)
    assert ends[0] == pytest.approx(ends[1]) == pytest.approx(1.0)


# --------------------------------------------------------------------------------------
# bars / line / both
# --------------------------------------------------------------------------------------

def _polygon_lines(ax):
    return [ln for ln in ax.lines if len(ln.get_xdata()) > 2]


def test_bars_only_draws_no_polygon():
    df = _two_groups()
    res = _render({"x": "val", "group": "grp", "panel_mode": "overlay",
                   "draw_style": "bars"}, df)
    try:
        assert _bar_heights(res.figure.axes[0])
        assert _polygon_lines(res.figure.axes[0]) == []
        assert res.metadata["draw_style"] == "bars"
    finally:
        plt.close(res.figure)


def test_line_only_draws_no_bars():
    df = _two_groups()
    res = _render({"x": "val", "group": "grp", "panel_mode": "overlay",
                   "draw_style": "line"}, df)
    try:
        assert _bar_heights(res.figure.axes[0]) == []
        assert len(_polygon_lines(res.figure.axes[0])) == 2
    finally:
        plt.close(res.figure)


def test_both_draws_bars_and_a_polygon():
    df = _two_groups()
    res = _render({"x": "val", "group": "grp", "panel_mode": "overlay",
                   "draw_style": "both"}, df)
    try:
        assert len(_bar_heights(res.figure.axes[0])) == 4     # fill + outline per group
        assert len(_polygon_lines(res.figure.axes[0])) == 2
    finally:
        plt.close(res.figure)


def test_the_polygon_passes_through_the_bin_heights():
    """A frequency polygon must be the same numbers as the bars, not a smoothed version."""
    df = pd.DataFrame({"val": [1.2, 1.8, 2.3, 2.4, 2.9, 3.1]})
    res = _render({"x": "val", "bin_width": 1.0, "draw_style": "both"}, df)
    try:
        ax = res.figure.axes[0]
        bars = _bar_heights(ax)[0]
        line = _polygon_lines(ax)[0]
        ys = np.asarray(line.get_ydata(), dtype=float)
        # closed to zero at both ends, with the bar heights in between
        assert ys[0] == 0.0 and ys[-1] == 0.0
        assert np.array_equal(ys[1:-1], bars)
        xs = np.asarray(line.get_xdata(), dtype=float)
        assert np.all(np.diff(xs) > 0), "vertices must run left to right"
    finally:
        plt.close(res.figure)


def test_line_style_works_in_panels_too():
    df = _two_groups()
    res = _render({"x": "val", "group": "grp", "panel_mode": "panels",
                   "draw_style": "line"}, df)
    try:
        axes = [a for a in res.figure.axes if a.get_visible()]
        assert len(axes) == 2
        assert all(len(_polygon_lines(a)) == 1 for a in axes)
        assert all(_bar_heights(a) == [] for a in axes)
    finally:
        plt.close(res.figure)


def test_unknown_draw_style_is_refused():
    df = _two_groups()
    with pytest.raises(RenderError, match="draw_style must be"):
        _render({"x": "val", "draw_style": "smooth"}, df)


def test_x_range_accounts_for_the_polygon_overhang():
    """The polygon closes half a bin past the last bin, so the guard must see that too."""
    df = pd.DataFrame({"val": [10.0, 12.0, 14.0, 16.0, 18.0, 20.0]})
    with pytest.raises(RenderError, match="would hide data"):
        _render({"x": "val", "bin_width": 2.0, "draw_style": "line", "x_max": 20.5}, df)


# --------------------------------------------------------------------------------------
# log axis, mean/median markers, opacity, y range
# --------------------------------------------------------------------------------------

def test_log_y_sets_a_log_scale_and_a_positive_floor():
    df = _two_groups()
    res = _render({"x": "val", "group": "grp", "log_y": True}, df)
    try:
        for a in (a for a in res.figure.axes if a.get_visible()):
            assert a.get_yscale() == "log"
            assert a.get_ylim()[0] > 0
        assert res.metadata["log_y"] is True
    finally:
        plt.close(res.figure)


def test_log_y_warns_that_empty_bins_cannot_be_shown():
    """A count of zero has no position on a log scale; saying so beats a blank gap."""
    df = pd.DataFrame({"val": [1.0, 1.1, 1.2, 9.0, 9.1]})   # a gap in the middle
    res = _render({"x": "val", "bins": 12, "log_y": True}, df)
    try:
        assert any("empty bin" in w and "log" in w for w in res.warnings)
    finally:
        plt.close(res.figure)


def test_mean_and_median_markers_are_drawn_and_recorded():
    df = _two_groups()
    res = _render({"x": "val", "group": "grp", "panel_mode": "overlay",
                   "show_mean": True, "show_median": True}, df)
    try:
        styles = sorted(ln.get_linestyle() for ln in res.figure.axes[0].lines
                        if len(ln.get_xdata()) == 2)
        assert len(styles) == 4, "one mean and one median line per group"
        assert res.metadata["mean_by_group"].keys() == {"A", "B"}
        assert res.metadata["median_by_group"].keys() == {"A", "B"}
        # the recorded values must be the real ones
        for g, sub in df.groupby("grp"):
            assert res.metadata["mean_by_group"][g] == pytest.approx(sub["val"].mean())
            assert res.metadata["median_by_group"][g] == pytest.approx(sub["val"].median())
    finally:
        plt.close(res.figure)


def test_markers_are_absent_unless_asked_for():
    df = _two_groups()
    res = _render({"x": "val", "group": "grp"}, df)
    try:
        assert "mean_by_group" not in res.metadata
        assert "median_by_group" not in res.metadata
    finally:
        plt.close(res.figure)


def test_fill_opacity_is_honoured():
    df = _two_groups()
    res = _render({"x": "val", "group": "grp", "panel_mode": "overlay",
                   "bar_alpha": 0.8}, df)
    try:
        from matplotlib.patches import StepPatch
        alphas = {p.get_alpha() for p in res.figure.axes[0].patches
                  if isinstance(p, StepPatch) and p.get_fill()}
        assert 0.8 in alphas
    finally:
        plt.close(res.figure)


@pytest.mark.parametrize("bad", [0, -0.5, 1.5])
def test_invalid_opacity_is_refused(bad):
    df = _two_groups()
    with pytest.raises(RenderError, match="bar_alpha"):
        _render({"x": "val", "bar_alpha": bad}, df)


def test_y_range_that_would_cut_bars_off_is_refused():
    """A truncated count axis exaggerates differences, so it is refused like the x axis."""
    df = _two_groups()
    with pytest.raises(RenderError, match="would hide data"):
        _render({"x": "val", "y_max": 5}, df)


def test_a_wider_y_range_is_accepted():
    df = _two_groups()
    res = _render({"x": "val", "y_min": 0, "y_max": 5000}, df)
    try:
        assert res.metadata["axis_overrides"]["y_limits"] == [0.0, 5000.0]
    finally:
        plt.close(res.figure)


def test_inverted_y_range_is_refused():
    df = _two_groups()
    with pytest.raises(RenderError, match="must be greater"):
        _render({"x": "val", "y_min": 100, "y_max": 10}, df)


def test_tick_rotation_reaches_every_panel():
    """The registry only styles the first axes, so a multi-panel figure has to do it itself."""
    df = _two_groups()
    res = _render({"x": "val", "group": "grp", "panel_mode": "panels",
                   "x_tick_rotation": "vertical"}, df)
    try:
        for a in (a for a in res.figure.axes if a.get_visible()):
            rotations = {t.get_rotation() for t in a.get_xticklabels() if t.get_text()}
            assert rotations == {90.0}, f"panel not rotated: {rotations}"
    finally:
        plt.close(res.figure)


# --------------------------------------------------------------------------------------
# wide input: one column per group
# --------------------------------------------------------------------------------------

def _wide(n_a=600, n_b=400, seed=3) -> pd.DataFrame:
    """Two columns of different length - what a spreadsheet of one column per group looks like.

    The shorter column is padded with NaN because a DataFrame is rectangular; that padding must not
    be counted as observations.
    """
    rng = np.random.default_rng(seed)
    a = _bimodal(rng, n_a, 0.4, 14.0, 31.0)
    b = _bimodal(rng, n_b, 0.4, 14.0, 31.0)
    return pd.DataFrame({"WT": pd.Series(a),
                         "Mutant": pd.Series(np.concatenate([b, np.full(n_a - n_b, np.nan)]))})


def test_wide_input_makes_one_histogram_per_column():
    df = _wide()
    res = _render({"value_columns": ["WT", "Mutant"], "panel_mode": "panels"}, df)
    try:
        assert res.metadata["input_form"] == "wide"
        assert res.metadata["groups"] == ["WT", "Mutant"]
        axes = [a for a in res.figure.axes if a.get_visible()]
        assert len(axes) == 2
    finally:
        plt.close(res.figure)


def test_wide_input_does_not_count_the_rectangular_padding():
    """The blanks that make the columns the same length are not observations."""
    df = _wide(n_a=600, n_b=400)
    res = _render({"value_columns": ["WT", "Mutant"]}, df)
    try:
        assert res.metadata["n_by_group"] == {"WT": 600, "Mutant": 400}
    finally:
        plt.close(res.figure)


def test_wide_and_long_forms_agree_exactly():
    """The wide form is a reshape, so it must not change a single number."""
    wide = _wide(n_a=600, n_b=400)
    long = pd.concat([
        pd.DataFrame({"grp": "WT", "val": wide["WT"].dropna().to_numpy()}),
        pd.DataFrame({"grp": "Mutant", "val": wide["Mutant"].dropna().to_numpy()})],
        ignore_index=True)

    a = _render({"value_columns": ["WT", "Mutant"], "bin_width": 2.0}, wide)
    b = _render({"x": "val", "group": "grp", "bin_width": 2.0}, long)
    try:
        for key in ("n_bins", "bin_range", "bin_width", "shared_bins"):
            assert a.metadata[key] == b.metadata[key], key
        assert list(a.metadata["n_by_group"].values()) == list(b.metadata["n_by_group"].values())
        for pa, pb in zip(_bar_heights(a.figure.axes[0]), _bar_heights(b.figure.axes[0])):
            assert np.array_equal(pa, pb)
    finally:
        plt.close(a.figure)
        plt.close(b.figure)


def test_wide_input_shares_bins_across_columns():
    df = _wide()
    res = _render({"value_columns": ["WT", "Mutant"], "panel_mode": "overlay"}, df)
    try:
        from matplotlib.patches import StepPatch
        edges = {tuple(np.round(p.get_data()[1], 9)) for p in res.figure.axes[0].patches
                 if isinstance(p, StepPatch)}
        assert len(edges) == 1
    finally:
        plt.close(res.figure)


def test_a_single_wide_column_is_one_histogram():
    df = _wide()
    res = _render({"value_columns": ["WT"]}, df)
    try:
        assert res.metadata["groups"] == ["WT"]
        assert res.metadata["n_by_group"] == {"WT": 600}
    finally:
        plt.close(res.figure)


def test_wide_column_given_as_a_bare_string_is_accepted():
    """A frontend with a single-select control sends a string, not a one-item list."""
    df = _wide()
    res = _render({"value_columns": "WT"}, df)
    try:
        assert res.metadata["groups"] == ["WT"]
    finally:
        plt.close(res.figure)


def test_declared_wide_form_uses_the_listed_columns():
    df = _wide()
    res = _render({"input_form": "wide", "value_columns": ["WT", "Mutant"]}, df)
    try:
        assert res.metadata["input_form"] == "wide"
        assert res.metadata["groups"] == ["WT", "Mutant"]
    finally:
        plt.close(res.figure)


def test_wide_form_without_any_columns_is_refused():
    df = _wide()
    with pytest.raises(RenderError, match="list one column per group"):
        _render({"input_form": "wide"}, df)


def test_long_form_wins_over_stray_columns_and_says_so():
    """A GUI prefills 'x', so both arriving is normal - the declared form has to decide."""
    df = _wide()
    res = _render({"input_form": "long", "x": "WT", "value_columns": ["WT", "Mutant"]}, df)
    try:
        assert res.metadata["input_form"] == "long"
        assert res.metadata["groups"] == ["all"]
        assert any("were ignored" in w and "wide" in w for w in res.warnings)
    finally:
        plt.close(res.figure)


def test_columns_without_an_x_are_read_as_wide_with_a_note():
    """The one safe inference: nothing was chosen for x, so the listed columns are the intent."""
    df = _wide()
    res = _render({"value_columns": ["WT", "Mutant"]}, df)
    try:
        assert res.metadata["input_form"] == "wide"
        assert any("wide form" in w for w in res.warnings)
    finally:
        plt.close(res.figure)


def test_supplying_neither_input_form_is_refused():
    df = _wide()
    with pytest.raises(RenderError, match="choose 'x'"):
        _render({}, df)


def test_unknown_input_form_is_refused():
    df = _wide()
    with pytest.raises(RenderError, match="input_form must be"):
        _render({"input_form": "tall", "x": "WT"}, df)


def test_repeating_a_wide_column_is_refused():
    df = _wide()
    with pytest.raises(RenderError, match="same column twice"):
        _render({"value_columns": ["WT", "WT"]}, df)


def test_missing_wide_column_is_reported_by_name():
    df = _wide()
    with pytest.raises(RenderError, match="Knockout"):
        _render({"value_columns": ["WT", "Knockout"]}, df)


def test_wide_input_is_not_mutated():
    df = _wide()
    before = df.copy(deep=True)
    res = _render({"value_columns": ["WT", "Mutant"]}, df)
    plt.close(res.figure)
    pd.testing.assert_frame_equal(df, before)


def test_value_columns_is_declared_a_multi_select_role():
    """Without this the desktop app would offer one combo box and draw a single histogram."""
    from make_my_figure_core import ui_hints

    assert ui_hints.is_multi_column("value_columns")
    assert "value_columns" in ui_hints.column_fields(PLOT)
