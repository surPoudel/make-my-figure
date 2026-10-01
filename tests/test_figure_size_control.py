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
