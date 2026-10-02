"""Measured geometry of the multi-panel grid: what the per-panel size controls do.

Every assertion here is in inches on the composite, taken after a draw, because
the bug these tests lock down was invisible to "does it render?" checks: setting
a panel's height moved the grid row and left the panel the same size, floating in
a taller cell. The measurements are:

* ``cell``  - the grid cell the panel was given (``gridspec`` position)
* ``box``   - the panel's drawn image box (axes position after ``apply_aspect``)
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.panels import FigureLayout, MultiPanelFigure, Panel, build_figure
from make_my_figure_core.panels.builder import panel_from_dict, panel_warnings

# One fixed table for the whole module: these tests compare one build against
# another to the inch, so the panel content must be identical every time (fresh
# random draws change the tick labels, which changes the tight bounding box).
_RNG = np.random.default_rng(11)
_BAR_DF = pd.DataFrame([{"c": c, "m": float(_RNG.normal(v, 0.2))}
                        for c, v in [("x", 1.0), ("y", 2.0)] for _ in range(6)])


# --------------------------------------------------------------------------------------------
# fixtures + measuring
# --------------------------------------------------------------------------------------------

def _bar_spec():
    from make_my_figure_core.plots.registry import make_spec

    spec = make_spec("barplot_with_error_bar", "a", "publication")
    spec["mapping"] = {"x": "c", "y": "m", "error": "sem"}
    return spec, _BAR_DF.copy()


def _prerendered(w, h):
    """A cheap, fixed-shape panel (no PlotSpec, so it can never be re-drawn)."""
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_subplot(111)
    ax.plot([0, 1, 2], [0, 1, 0])
    return fig


def _mpf(*, height_in=None, fill_cell=False, ncols=2):
    """The reported 2x2: a TALL panel A beside a short generated panel B.

    B is the panel that ends up with the band of white space under it, and the
    one whose height control the user reached for. The bottom row is two square
    panels, which keeps the grid's inches-per-cell close to the 2x2 the bug was
    reported on (a one-row grid distributes the figure's margins differently).
    """
    spec, df = _bar_spec()
    mpf = MultiPanelFigure(name="F", layout=FigureLayout(ncols=ncols, panel_dpi=72))
    mpf.add_panel(Panel(figure=_prerendered(2.0, 5.0)))
    mpf.add_panel(Panel(plot_spec=spec, table=df, height_in=height_in, fill_cell=fill_cell))
    mpf.add_panel(Panel(figure=_prerendered(3.0, 3.0)))
    mpf.add_panel(Panel(figure=_prerendered(3.0, 3.0)))
    return mpf


def _measure(fig):
    """[(cell_w, cell_h, box_w, box_h, gap_above, gap_below), ...] in inches, per panel."""
    fig.canvas.draw()
    fig_w, fig_h = (float(v) for v in fig.get_size_inches())
    gs = fig.axes[0].get_gridspec()
    _, ncols = gs.get_geometry()
    out = []
    for i, ax in enumerate(fig.axes):
        r, c = divmod(i, ncols)
        cell, box = gs[r, c].get_position(fig), ax.get_position()
        out.append({
            "cell_w": cell.width * fig_w, "cell_h": cell.height * fig_h,
            "box_w": box.width * fig_w, "box_h": box.height * fig_h,
            "gap_above": (cell.y1 - box.y1) * fig_h, "gap_below": (box.y0 - cell.y0) * fig_h,
            "gap_left": (box.x0 - cell.x0) * fig_w, "gap_right": (cell.x1 - box.x1) * fig_w,
            "empty": 1.0 - (box.width * box.height) / (cell.width * cell.height),
        })
    return out


def _image_aspects(mpf):
    """Aspect (h/w) of each panel's rasterized image, as the builder sees it."""
    fig = build_figure(mpf)
    out = [ax.get_images()[0].get_array().shape[0] / ax.get_images()[0].get_array().shape[1]
           for ax in fig.axes]
    plt.close(fig)
    return out


# --------------------------------------------------------------------------------------------
# the default: proportions preserved, nothing stretched, nothing moved
# --------------------------------------------------------------------------------------------

def test_default_panel_fills_its_cell_width_at_its_own_aspect():
    """The unchanged default: each panel is as wide as its cell and as tall as its
    own proportions make it. This is the geometry every saved layout relies on."""
    mpf = _mpf()
    aspects = _image_aspects(mpf)
    fig = build_figure(mpf)
    m = _measure(fig)
    for i, d in enumerate(m):
        assert d["box_w"] == pytest.approx(d["cell_w"], rel=0.02)
        assert d["box_h"] == pytest.approx(d["cell_w"] * aspects[i], rel=0.02)
    plt.close(fig)


def test_aspect_is_preserved_by_default():
    """The drawn box has the panel image's own aspect - no distortion, ever, by default."""
    mpf = _mpf()
    aspects = _image_aspects(mpf)
    fig = build_figure(mpf)
    for i, (ax, d) in enumerate(zip(fig.axes, _measure(fig))):
        assert ax.get_aspect() in (1.0, "equal")          # square pixels
        assert d["box_h"] / d["box_w"] == pytest.approx(aspects[i], rel=0.02)
    assert not any("stretched" in w for w in panel_warnings(fig))
    plt.close(fig)


def test_short_panel_in_a_tall_row_is_top_aligned():
    """All the leftover height goes BELOW the short panel, so panel tops line up."""
    fig = build_figure(_mpf())
    short = _measure(fig)[1]
    assert short["gap_above"] == pytest.approx(0.0, abs=0.01)
    assert short["gap_below"] > 0.5          # the dead space the user reported
    plt.close(fig)


def test_panels_stay_horizontally_centred_in_their_cell():
    """Horizontal placement is unchanged (matplotlib's 'N' anchor centred it too):
    a figure laid out before per-panel heights were honoured must not shift sideways."""
    mpf = _mpf()
    mpf.layout.height_ratios = [2, 1]        # squeezes the rows, so panels narrow
    for d in _measure(build_figure(mpf)):
        assert d["gap_left"] == pytest.approx(d["gap_right"], abs=0.01)
    plt.close("all")


def test_explicit_height_ratios_still_fit_each_panel_to_its_cell():
    """When the user pins height_ratios THEY decide the proportions: each panel
    fills its cell in one direction, exactly as it did before this change."""
    mpf = _mpf()
    mpf.layout.height_ratios = [2, 1]
    for d in _measure(build_figure(mpf)):
        assert (d["box_w"] == pytest.approx(d["cell_w"], rel=0.02)
                or d["box_h"] == pytest.approx(d["cell_h"], rel=0.02))
    plt.close("all")


# --------------------------------------------------------------------------------------------
# the fix: a requested height changes the drawn height
# --------------------------------------------------------------------------------------------

def test_requested_height_grows_the_drawn_panel():
    """The reported bug: raising a panel's height left its drawn size untouched.

    The panel must get taller by (near enough) the factor asked for - the grid's
    inches are approximate, so the test pins the RATIO, which is exact.
    """
    auto = _measure(build_figure(_mpf()))[1]["box_h"]
    one = _measure(build_figure(_mpf(height_in=2.5)))[1]["box_h"]
    two = _measure(build_figure(_mpf(height_in=5.0)))[1]["box_h"]
    assert two == pytest.approx(2.0 * one, rel=0.08)     # twice the height asked for
    assert two > auto * 1.5                  # and it is a real change, not a rounding wobble
    plt.close("all")


def test_panel_asked_to_be_the_tallest_fills_its_cell():
    """A panel asked for more height than anything else in its row gets the whole cell."""
    m = _measure(build_figure(_mpf(height_in=12.0)))[1]
    assert m["box_h"] == pytest.approx(m["cell_h"], rel=0.05)
    assert m["empty"] < 0.10
    plt.close("all")


def test_requested_height_does_not_distort_the_panel():
    """The panel is RE-DRAWN taller (taller axes), never stretched."""
    mpf = _mpf(height_in=3.2)
    aspects = _image_aspects(mpf)
    fig = build_figure(mpf)
    m = _measure(fig)[1]
    assert fig.axes[1].get_aspect() in (1.0, "equal")
    assert m["box_h"] / m["box_w"] == pytest.approx(aspects[1], rel=0.02)
    assert not any("stretched" in w for w in panel_warnings(fig))
    plt.close(fig)


def test_drawn_box_matches_the_width_by_height_asked_for():
    """width x height means what it says: the drawn panel has that shape.

    Before, the drawn box always came back at the plot's own ratio (0.80 here)
    whatever was typed, which is what made the height control look dead.
    """
    spec, df = _bar_spec()
    for w, h in [(3.0, 1.5), (3.0, 4.5), (4.0, 4.0)]:
        mpf = MultiPanelFigure(name="F", layout=FigureLayout(ncols=1, panel_dpi=72))
        mpf.add_panel(Panel(plot_spec=spec, table=df, width_in=w, height_in=h))
        d = _measure(build_figure(mpf))[0]
        assert d["box_h"] / d["box_w"] == pytest.approx(h / w, rel=0.06)
        plt.close("all")


def test_fill_cell_removes_the_dead_space():
    """'Fill the cell' is the one-click answer to a short panel in a tall row."""
    before = _measure(build_figure(_mpf()))[1]
    after = _measure(build_figure(_mpf(fill_cell=True)))[1]
    assert before["empty"] > 0.40            # the reported white band
    assert after["empty"] < 0.10
    assert after["box_h"] > before["box_h"] * 1.5
    plt.close("all")


def test_fill_cell_keeps_square_pixels_on_a_generated_panel():
    """Filling a cell must not be a stretch: the plot is re-rendered at that size."""
    fig = build_figure(_mpf(fill_cell=True))
    assert fig.axes[1].get_aspect() in (1.0, "equal")
    assert not any("stretched" in w for w in panel_warnings(fig))
    plt.close(fig)


def test_fill_cell_on_a_fixed_shape_panel_stretches_and_says_so():
    """A panel with no PlotSpec cannot be re-drawn, so filling it does distort it -
    which must be reported rather than done silently."""
    mpf = _mpf()
    mpf.panels[0].fill_cell = True           # the pre-rendered (fixed-shape) panel
    fig = build_figure(mpf)
    assert any("stretched" in w for w in panel_warnings(fig))
    plt.close(fig)


def test_unreachable_height_on_a_fixed_shape_panel_adds_no_white_space():
    """A fixed-shape panel asked for an impossible height must not inflate its row.

    Before, the row grew to the requested height and the panel stayed its own size,
    so asking for more height produced more white space. Now the request is capped
    and explained.
    """
    plain = build_figure(_mpf())
    plain_h = float(plain.get_size_inches()[1])
    plt.close(plain)
    mpf = _mpf()
    mpf.panels[0].height_in = 12.0           # fixed-shape panel, 2x5 in => impossible
    fig = build_figure(mpf)
    assert float(fig.get_size_inches()[1]) == pytest.approx(plain_h, rel=0.02)
    assert any("cannot be made" in w for w in panel_warnings(fig))
    plt.close(fig)


def test_shorter_request_shrinks_a_fixed_shape_panel():
    """The height control still does something for a panel that cannot be re-drawn:
    it scales the whole picture down, proportions intact."""
    auto = _measure(build_figure(_mpf()))[0]
    mpf = _mpf()
    mpf.panels[0].height_in = 2.5            # half of its natural 5.0 in
    small = _measure(build_figure(mpf))[0]
    assert small["box_h"] < auto["box_h"] * 0.75
    assert small["box_h"] / small["box_w"] == pytest.approx(auto["box_h"] / auto["box_w"], rel=0.02)
    plt.close("all")


# --------------------------------------------------------------------------------------------
# round-tripping the new field
# --------------------------------------------------------------------------------------------

def test_fill_cell_round_trips_through_panel_dict():
    p = Panel(plot_spec={"plot_type": "barplot_with_error_bar"}, fill_cell=True, height_in=2.5)
    back = panel_from_dict(p.to_dict())
    assert back.fill_cell is True and back.height_in == 2.5


def test_old_panel_dict_without_fill_cell_loads_unchanged():
    """A layout saved before the field existed must load as 'keep proportions'."""
    d = Panel(plot_spec={"plot_type": "barplot_with_error_bar"}, height_in=2.5).to_dict()
    d.pop("fill_cell")
    assert panel_from_dict(d).fill_cell is False


def test_old_layout_preset_without_fill_cell_renders_identically():
    from make_my_figure_core import presets as P

    mpf = _mpf()
    preset = P.extract_layout_preset(mpf, name="old")
    for size in preset["panel_sizes"]:
        size.pop("fill_cell")                # a preset written by an older version
    target = _mpf()
    P.apply_layout_preset(preset, target)
    assert [p.fill_cell for p in target.panels] == [False] * len(target.panels)
    before = _measure(build_figure(_mpf()))
    after = _measure(build_figure(target))
    for b, a in zip(before, after):
        assert a["box_w"] == pytest.approx(b["box_w"], rel=1e-6)
        assert a["box_h"] == pytest.approx(b["box_h"], rel=1e-6)
    plt.close("all")


def test_fill_cell_survives_a_layout_preset():
    from make_my_figure_core import presets as P

    src = _mpf(fill_cell=True, height_in=3.0)
    preset = P.extract_layout_preset(src, name="filled")
    target = _mpf()
    P.apply_layout_preset(preset, target)
    assert target.panels[1].fill_cell is True
    assert target.panels[1].height_in == 3.0
