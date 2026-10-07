"""Measured geometry of the multi-panel grid: what the per-panel size controls do.

Every assertion here is in inches on the composite, taken after a draw, because
the bug these tests lock down was invisible to "does it render?" checks: setting
a panel's height moved the grid row and left the panel the same size, floating in
a taller cell. The measurements are:

* ``cell``   - the grid cell the panel was given (``gridspec`` position)
* ``box``    - the panel's drawn image box (axes position after ``apply_aspect``)
* ``frame``  - where the PLOT inside that image landed (``panel_frames``)

The frame is the measurement that matters for alignment: a panel is a picture of
a plot surrounded by its own axis labels, so lining the pictures up leaves the
plots crooked. The compositor therefore places each panel by its frame, which
means a panel's image box is its cell less however far it had to be shifted in
to meet the column's shared left edge - several of the assertions below are
about exactly that difference.
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.panels import FigureLayout, MultiPanelFigure, Panel, build_figure
from make_my_figure_core.panels.builder import (
    panel_frames, panel_from_dict, panel_warnings)

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

def test_default_panel_uses_its_whole_cell_less_the_alignment_shift():
    """Each panel occupies its cell from the column's shared frame edge to the
    cell's far side, and is as tall as its own proportions make it.

    The shift is the only thing between the panel and the full cell width, and it
    is there on purpose: it is how far this panel's plotting frame had to move in
    to line up with its neighbour's.
    """
    mpf = _mpf()
    aspects = _image_aspects(mpf)
    fig = build_figure(mpf)
    m = _measure(fig)
    for i, d in enumerate(m):
        assert d["box_w"] + d["gap_left"] == pytest.approx(d["cell_w"], rel=0.02)
        assert d["box_h"] == pytest.approx(d["box_w"] * aspects[i], rel=0.02)
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
    """All the leftover height goes BELOW the short panel, so the PLOTS line up.

    The plots, not the pictures: the top edge each panel is aligned on is the top
    of its plotting frame, so a panel whose picture carries a title still has its
    axes level with the panel beside it.
    """
    fig = build_figure(_mpf())
    tops = [f["y1"] for f in panel_frames(fig)[:2]]
    assert tops[0] == pytest.approx(tops[1], abs=0.005)
    assert _measure(fig)[1]["gap_below"] > 0.5    # the dead space the user reported
    plt.close(fig)


def test_panels_in_a_column_share_one_plot_left_edge():
    """The alignment contract, and it replaces centring each picture in its cell.

    Centring is what produced the reported defect: panel A's y-axis label is a
    different width from panel C's, so centring their pictures left their plots
    0.41 in out of line, and widening C moved A.
    """
    mpf = _mpf()
    mpf.layout.height_ratios = [2, 1]        # squeezes the rows, so panels narrow
    frames = panel_frames(build_figure(mpf))
    for col in (0, 1):
        xs = [f["x0"] for f in frames if f["col"] == col]
        assert max(xs) - min(xs) == pytest.approx(0.0, abs=0.005)
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
    """A panel asked for more height than anything else in its row gets the whole
    cell, less whatever the row's shared plot-top edge needed."""
    m = _measure(build_figure(_mpf(height_in=12.0)))[1]
    assert m["box_h"] + m["gap_above"] == pytest.approx(m["cell_h"], rel=0.05)
    assert m["gap_below"] == pytest.approx(0.0, abs=0.05)
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
    # What is left is the alignment shift, not dead space: the panel reaches the
    # bottom of its cell and the full width from the column's shared frame edge.
    assert after["gap_below"] == pytest.approx(0.0, abs=0.12)
    assert after["empty"] < before["empty"] / 3.0
    assert after["box_w"] + after["gap_left"] == pytest.approx(after["cell_w"], rel=0.02)
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


# --------------------------------------------------------------------------
# One font setting, one size on the page
# --------------------------------------------------------------------------

MIXED_PANELS = ["volcano_plot", "barplot_with_error_bar",
                "heatmap_clustered_matrix", "lineplot_timecourse_with_error_band"]


def _mixed_composite(**layout_kw):
    from make_my_figure_core import examples
    from make_my_figure_core.panels import FigureLayout, MultiPanelFigure, Panel

    layout = FigureLayout(ncols=2, fig_width_mm=180.0, base_font_pt=7.0,
                          axis_font_pt=7.5, tick_label_pt=6.5, legend_pt=6.5,
                          **layout_kw)
    mpf = MultiPanelFigure(name="F", layout=layout)
    for plot_type in MIXED_PANELS:
        table, aux, spec = examples.load_example(plot_type)
        mpf.add_panel(Panel(plot_spec=spec, table=table.dataframe,
                            aux={k: v.dataframe for k, v in (aux or {}).items()},
                            width_in=3.2))
    return mpf


def _image_scales(figure):
    """Source pixels per drawn inch, per panel, over the render dpi.

    1.0 means the panel is drawn at the size it was rendered, so a point of type
    in it is a point on the page.
    """
    figure.canvas.draw()
    width_in = float(figure.get_size_inches()[0])
    scales = []
    for ax in figure.axes:
        images = ax.get_images()
        if not images:
            continue
        source_w = images[0].get_array().shape[1]
        drawn_w = ax.get_position().width * width_in
        scales.append((source_w / max(drawn_w, 1e-6)) / 150.0)
    return scales


def test_every_panel_is_drawn_at_the_size_it_was_rendered():
    """Panels used to be rendered once and then scaled to their cell by a
    DIFFERENT factor each, so the one font setting the user chose for the whole
    figure arrived on the page at a different size in every panel - measured
    1.18x spread untouched and 1.90x once a panel was resized.
    """
    from make_my_figure_core.panels.builder import build_figure
    import matplotlib.pyplot as plt

    figure = build_figure(_mixed_composite())
    scales = _image_scales(figure)
    plt.close(figure)
    assert scales, "no panel images found"
    spread = max(scales) / min(scales)
    assert spread < 1.05, (
        f"panels are drawn at {spread:.2f}x different scales, so one font size "
        f"lands on the page at {spread:.2f}x different sizes: {scales}")


def test_one_font_setting_gives_one_tick_size_in_every_panel():
    """The composite's point sizes must be literal, not scaled per panel.

    Each panel is a different size, so the canvas-responsive type scaling - right
    for a standalone figure - scaled each panel's type by a different factor
    (measured 69% / 71% / 98% / 66%), which is the same defect by another route.
    """
    from make_my_figure_core import examples
    from make_my_figure_core.panels import Panel
    from make_my_figure_core.panels.builder import _render_panel_figure
    import matplotlib.pyplot as plt

    overrides = {"base_font_pt": 7.0, "axis_font_pt": 7.5,
                 "tick_label_pt": 6.5, "legend_pt": 6.5}
    seen = {}
    for plot_type in MIXED_PANELS[:3]:
        table, aux, spec = examples.load_example(plot_type)
        panel = Panel(plot_spec=spec, table=table.dataframe,
                      aux={k: v.dataframe for k, v in (aux or {}).items()},
                      width_in=3.2)
        figure = _render_panel_figure(panel, overrides, size_in=(2.68, 1.86))
        seen[plot_type] = round(figure.axes[0].yaxis.label.get_fontsize(), 2)
        plt.close(figure)
    assert len(set(seen.values())) == 1, (
        f"one axis-label setting produced different sizes per panel: {seen}")
    assert set(seen.values()) == {7.5}, (
        f"the composite's point sizes are not literal: {seen}")


def test_a_standalone_figure_still_scales_its_type_to_its_canvas():
    """Opting out is for composites only. A single figure on a small canvas must
    still shrink its type, which is what keeps a 2 x 1 in panel readable."""
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry
    import matplotlib.pyplot as plt

    table, aux, spec = examples.load_example("barplot_with_error_bar")
    spec = {**spec, "layout": {**(spec.get("layout") or {}),
                               "width_mm": 50.8, "height_mm": 25.4}}
    result = registry.render(spec, table.dataframe,
                             aux={k: v.dataframe for k, v in (aux or {}).items()})
    scaled = any("Text sizes were scaled" in w for w in result.warnings)
    plt.close(result.figure)
    assert scaled, "a standalone small figure no longer scales its type"
