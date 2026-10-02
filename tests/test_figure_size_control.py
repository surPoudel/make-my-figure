"""Explicit figure dimensions must be honoured by every plot type.

A width preset multiplied by a renderer's fixed aspect cannot describe every
figure: a 9x28 dot matrix is wide and short, and no preset says that. Several
renderers also size themselves from their data - a heatmap grows with its rows -
which is the right default but used to leave the user unable to fit a figure to
a column. These tests assert that an explicit request always wins.
"""

from __future__ import annotations

import json
import warnings

import pandas as pd
import pytest

from make_my_figure_core import examples
from make_my_figure_core.plots import registry

MM_PER_INCH = 25.4
SIZES = [(120.0, 60.0), (250.0, 90.0), (80.0, 140.0), (180.0, 180.0)]
TOLERANCE_IN = 0.02

PLOT_TYPES = [p for p in registry.available_plot_types() if examples.entry(p)]


def _render(plot_type, layout_extra):
    entry = examples.entry(plot_type)
    df = pd.read_csv(entry["files"]["csv"])
    spec = json.loads(json.dumps(json.load(open(entry["files"]["plotspec"]))))
    spec.setdefault("layout", {}).update(layout_extra)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return registry.render(spec, df)


@pytest.mark.parametrize("plot_type", PLOT_TYPES)
@pytest.mark.parametrize("width_mm,height_mm", SIZES, ids=[f"{w:.0f}x{h:.0f}mm" for w, h in SIZES])
def test_explicit_size_is_honoured(plot_type, width_mm, height_mm):
    res = _render(plot_type, {"width_mm": width_mm, "height_mm": height_mm})
    got_w, got_h = (float(v) for v in res.figure.get_size_inches())
    want_w, want_h = width_mm / MM_PER_INCH, height_mm / MM_PER_INCH
    assert abs(got_h - want_h) <= TOLERANCE_IN, \
        f"{plot_type}: height {got_h:.2f}in, asked {want_h:.2f}in"
    # A renderer may add width for an outside legend, but must never be narrower.
    assert got_w >= want_w - TOLERANCE_IN, \
        f"{plot_type}: width {got_w:.2f}in, asked at least {want_w:.2f}in"


@pytest.mark.parametrize("plot_type", PLOT_TYPES[:12])
def test_width_alone_keeps_the_renderer_aspect(plot_type):
    """Width without height should not collapse or fix the height."""
    a = _render(plot_type, {"width_mm": 150.0})
    b = _render(plot_type, {"width_mm": 300.0})
    ha, hb = a.figure.get_size_inches()[1], b.figure.get_size_inches()[1]
    assert ha > 0 and hb > 0
    assert hb >= ha, f"{plot_type}: doubling the width shrank the height"


@pytest.mark.parametrize("bad", [0, -5, "wide", None])
def test_a_bad_size_is_ignored_rather_than_producing_a_zero_figure(bad):
    res = _render("scatterplot_with_regression", {"width_mm": bad, "height_mm": bad})
    w, h = res.figure.get_size_inches()
    assert w > 1.0 and h > 1.0, f"bad size {bad!r} produced a {w}x{h} figure"


def test_presets_still_work_when_no_explicit_size_is_given():
    narrow = _render("scatterplot_with_regression", {"column_width": "single"})
    wide = _render("scatterplot_with_regression", {"column_width": "double"})
    assert wide.figure.get_size_inches()[0] > narrow.figure.get_size_inches()[0]


# --- absurd sizes must never produce an unusable figure -----------------------

from make_my_figure_core.plots.base import MIN_FIGURE_MM  # noqa: E402


@pytest.mark.parametrize("plot_type", PLOT_TYPES)
def test_a_sub_millimetre_request_is_raised_to_a_usable_size(plot_type):
    """0.5 mm is never what anyone meant, and matplotlib cannot lay it out."""
    res = _render(plot_type, {"width_mm": 0.5, "height_mm": 0.2})
    w_mm, h_mm = (v * MM_PER_INCH for v in res.figure.get_size_inches())
    assert w_mm >= MIN_FIGURE_MM - 0.5, f"{plot_type}: width came back {w_mm:.2f} mm"
    assert h_mm >= MIN_FIGURE_MM - 0.5, f"{plot_type}: height came back {h_mm:.2f} mm"


def test_the_correction_is_reported_not_silent():
    """A figure must never come back a different size without saying so."""
    res = _render("scatterplot_with_regression", {"width_mm": 0.5, "height_mm": 0.2})
    notes = [w for w in res.warnings if "too small" in w]
    assert len(notes) == 2, res.warnings
    assert all("Set 0 for automatic sizing" in n for n in notes)


def test_a_non_numeric_size_is_reported_and_ignored():
    res = _render("scatterplot_with_regression", {"width_mm": "wide"})
    assert any("not a number" in w for w in res.warnings), res.warnings
    assert res.figure.get_size_inches()[0] > 1.0


def test_zero_is_auto_and_is_not_reported_as_a_problem():
    """0 is the documented way to say 'automatic', not a mistake."""
    res = _render("scatterplot_with_regression", {"width_mm": 0, "height_mm": 0})
    assert not any("too small" in w for w in res.warnings), res.warnings
    assert res.figure.get_size_inches()[0] > 1.0


def test_a_size_at_the_floor_is_accepted_without_complaint():
    res = _render("scatterplot_with_regression",
                  {"width_mm": MIN_FIGURE_MM, "height_mm": MIN_FIGURE_MM})
    assert not any("too small" in w for w in res.warnings), res.warnings


# --- data-driven plot types: ONE pinned dimension is still a pinned dimension --

# These size themselves from their data rather than from a width preset. They
# used to honour a pinned size only when BOTH dimensions were given, so pinning
# just a width - the usual way to fit a figure to a journal column - was silently
# thrown away and the figure came back whatever size the data made it.
DATA_DRIVEN_PLOT_TYPES = [
    "confusion_matrix",
    "heatmap_clustered_matrix",
    "hierarchical_clustering",
    "sankey_plot",
    "swimmer_plot",
    "upset_plot",
    "neighborhood_enrichment_matrix",
]


@pytest.mark.parametrize("plot_type", DATA_DRIVEN_PLOT_TYPES)
def test_a_pinned_width_alone_is_honoured_and_leaves_the_data_driven_height(plot_type):
    auto_w, auto_h = (float(v) for v in _render(plot_type, {}).figure.get_size_inches())
    got_w, got_h = (float(v) for v in
                    _render(plot_type, {"width_mm": 101.6}).figure.get_size_inches())
    assert abs(got_w - 101.6 / MM_PER_INCH) <= TOLERANCE_IN, \
        f"{plot_type}: pinned width 101.6 mm came back {got_w * MM_PER_INCH:.1f} mm"
    # The dimension that was NOT pinned must keep the size the data asked for,
    # rather than being stretched to preserve an aspect ratio.
    assert abs(got_h - auto_h) <= TOLERANCE_IN, \
        f"{plot_type}: pinning a width changed the data-driven height {auto_h:.2f} -> {got_h:.2f}"
    assert auto_w > 0


@pytest.mark.parametrize("plot_type", DATA_DRIVEN_PLOT_TYPES)
def test_a_pinned_height_alone_is_honoured_and_leaves_the_data_driven_width(plot_type):
    auto_w, auto_h = (float(v) for v in _render(plot_type, {}).figure.get_size_inches())
    got_w, got_h = (float(v) for v in
                    _render(plot_type, {"height_mm": 50.8}).figure.get_size_inches())
    assert abs(got_h - 50.8 / MM_PER_INCH) <= TOLERANCE_IN, \
        f"{plot_type}: pinned height 50.8 mm came back {got_h * MM_PER_INCH:.1f} mm"
    assert abs(got_w - auto_w) <= TOLERANCE_IN, \
        f"{plot_type}: pinning a height changed the data-driven width {auto_w:.2f} -> {got_w:.2f}"
    assert auto_h > 0


@pytest.mark.parametrize("plot_type", DATA_DRIVEN_PLOT_TYPES)
def test_both_dimensions_pinned_give_exactly_that_figure(plot_type):
    """The pinned size is exact - not a minimum, and not an aspect-corrected one."""
    res = _render(plot_type, {"width_mm": 101.6, "height_mm": 50.8})
    got_w, got_h = (float(v) for v in res.figure.get_size_inches())
    assert abs(got_w - 101.6 / MM_PER_INCH) <= TOLERANCE_IN
    assert abs(got_h - 50.8 / MM_PER_INCH) <= TOLERANCE_IN


@pytest.mark.parametrize("plot_type", DATA_DRIVEN_PLOT_TYPES)
def test_nothing_pinned_still_gets_the_data_driven_size(plot_type):
    """With no request, the renderer's own sizing applies - not the pinned one."""
    auto = _render(plot_type, {}).figure.get_size_inches()
    pinned = _render(plot_type, {"width_mm": 101.6, "height_mm": 50.8}).figure.get_size_inches()
    assert tuple(round(float(v), 3) for v in auto) != tuple(round(float(v), 3) for v in pinned), \
        f"{plot_type}: the automatic size is indistinguishable from a pinned one"


def test_more_rows_make_a_taller_heatmap_unless_the_height_is_pinned():
    """The data-driven default is really driven by the data, and a pin overrides it."""
    entry = examples.entry("heatmap_clustered_matrix")
    small = pd.read_csv(entry["files"]["csv"])
    big = pd.concat([small, small.assign(gene=small["gene"].astype(str) + "_b")],
                    ignore_index=True)
    spec = json.loads(json.dumps(json.load(open(entry["files"]["plotspec"]))))

    def _height(df, layout_extra):
        s = json.loads(json.dumps(spec))
        s.setdefault("layout", {}).update(layout_extra)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return float(registry.render(s, df).figure.get_size_inches()[1])

    assert _height(big, {}) > _height(small, {}), \
        "doubling the rows did not grow the automatically-sized heatmap"
    assert abs(_height(big, {"height_mm": 50.8}) - _height(small, {"height_mm": 50.8})) <= TOLERANCE_IN, \
        "a pinned height still grew with the row count"
