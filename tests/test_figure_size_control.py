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
