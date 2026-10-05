"""Figure margins must apply, and must say so when they cannot.

Margins are matplotlib edge POSITIONS in figure fractions: left/bottom measure
from the left/bottom edge, right/top give the position of the far edge. So
``right=0.70`` leaves 30% of the width blank on the right, which is how a user
shrinks the plotting area while keeping the canvas - and the whitespace for
labels - the same size.

Three things made this hard to use before, and each has a test here:

* ``0`` was documented as "auto" but passed through as a literal 0, producing
  ``left >= right``;
* matplotlib's rejection was swallowed by a bare ``except``, so a single bad
  value silently discarded *every* margin;
* nothing told the user any of that had happened.
"""

from __future__ import annotations

import json
import warnings

import pandas as pd
import pytest

from make_my_figure_core import examples
from make_my_figure_core.plots import registry

MARGINS = {"margin_left": 0.15, "margin_right": 0.70,
           "margin_top": 0.88, "margin_bottom": 0.22}
TOL = 0.02
PLOT_TYPES = [p for p in registry.available_plot_types() if examples.entry(p)]


def _render(plot_type, layout):
    entry = examples.entry(plot_type)
    df = pd.read_csv(entry["files"]["csv"])
    spec = json.loads(json.dumps(json.load(open(entry["files"]["plotspec"]))))
    spec.setdefault("layout", {}).update(layout)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return registry.render(spec, df)


def _is_constrained(fig, ax) -> bool:
    """True when the axes box legitimately cannot match the requested margins.

    An equal-aspect plot must stay square, a colourbar takes reserved space from
    its parent, and a faceted figure subdivides the margined area between
    panels. In all three the margin IS applied - to the figure - and the axes
    then adjusts, which is correct rather than a failure to honour the request.
    """
    if str(ax.get_aspect()) not in ("auto",):
        return True
    if any(getattr(a, "_colorbar", None) is not None for a in fig.axes):
        return True
    return len([a for a in fig.axes if getattr(a, "_colorbar", None) is None]) > 1


@pytest.mark.parametrize("plot_type", PLOT_TYPES)
def test_margins_are_applied(plot_type):
    res = _render(plot_type, {"width_mm": 101.6, "height_mm": 50.8, **MARGINS})
    fig = res.figure
    ax = fig.axes[0]
    box = ax.get_position()
    left, right = MARGINS["margin_left"], MARGINS["margin_right"]
    bottom, top = MARGINS["margin_bottom"], MARGINS["margin_top"]

    if _is_constrained(fig, ax):
        # An equal-aspect axes is CENTRED in the margined box rather than
        # stretched to it, and a colourbar takes space from its parent. The
        # requirement is that the axes stays inside the area the user reserved,
        # not that it fills it - filling it would mean distorting the plot.
        assert box.x0 >= left - TOL and box.x1 <= right + TOL, \
            f"{plot_type}: x {box.x0:.3f}-{box.x1:.3f} outside {left}-{right}"
        assert box.y0 >= bottom - TOL and box.y1 <= top + TOL, \
            f"{plot_type}: y {box.y0:.3f}-{box.y1:.3f} outside {bottom}-{top}"
        assert box.width > 0.05 and box.height > 0.05, f"{plot_type}: axes collapsed"
    else:
        assert abs(box.x0 - left) < TOL, f"{plot_type}: left {box.x0:.3f}"
        assert abs(box.x1 - right) < TOL, f"{plot_type}: right {box.x1:.3f}"
        assert abs(box.y0 - bottom) < TOL, f"{plot_type}: bottom {box.y0:.3f}"
        assert abs(box.y1 - top) < TOL, f"{plot_type}: top {box.y1:.3f}"


def test_zero_means_auto_not_a_literal_zero():
    """The control is labelled "0 = auto"; it has to behave that way."""
    res = _render("scatterplot_with_regression",
                  {"margin_left": 0.24, "margin_right": 0.0,
                   "margin_top": 0.50, "margin_bottom": 0.32})
    box = res.figure.axes[0].get_position()
    assert abs(box.x0 - 0.24) < TOL, "left margin was discarded"
    assert box.x1 > 0.24, "right edge collapsed onto the left"
    assert not any("margin" in w.lower() for w in res.warnings), res.warnings


def test_right_margin_creates_whitespace_on_the_right():
    """The thing a user actually wants: a smaller plot, same canvas."""
    wide = _render("scatterplot_with_regression", {"margin_left": 0.12, "margin_right": 0.95})
    narrow = _render("scatterplot_with_regression", {"margin_left": 0.12, "margin_right": 0.60})
    assert narrow.figure.axes[0].get_position().x1 < wide.figure.axes[0].get_position().x1
    # the canvas itself is unchanged - only the plotting area shrank
    assert wide.figure.get_size_inches()[0] == pytest.approx(
        narrow.figure.get_size_inches()[0])


def test_an_inverted_pair_is_reported_rather_than_silently_dropping_everything():
    res = _render("scatterplot_with_regression",
                  {"margin_left": 0.80, "margin_right": 0.20})
    notes = [w for w in res.warnings if "must be less than" in w]
    assert notes, f"no report of the inverted margins: {res.warnings}"
    assert "positions from the left edge" in notes[0]


def test_an_inverted_vertical_pair_is_reported_too():
    res = _render("scatterplot_with_regression",
                  {"margin_bottom": 0.90, "margin_top": 0.10})
    assert any("must be less than" in w for w in res.warnings), res.warnings
