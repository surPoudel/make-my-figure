"""Measured alignment of a multi-panel composite - the v1.2.1 Figure Builder report.

The report was four unmodified example plots (bar, clustered heatmap, scatter
with regression, volcano) added as panels A-D of a 2x2 figure, and then panel C
widened. Everything asserted here was wrong in that figure:

* widening C moved A's plot 0.41 in sideways, so A and C no longer lined up;
* a panel asked for 3.2 in was drawn 2.68 in;
* "measurement (mean +/- SEM)" was cropped to "measurement (mean +/- SE";
* the volcano's count line wrapped onto three lines, the last one reading "1)";
* the regression statistics covered the whole width of the scatter they
  annotated, and its legend took 38% of the panel;
* panels of different sizes carried different type sizes, 12 pt axis labels in
  one and 10.2 pt in the one beside it.

The measurements come from ``panel_frames``, which reports where each panel's
plotting frame - not its picture - landed on the page.
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

from make_my_figure_core import examples
from make_my_figure_core.panels import FigureLayout, MultiPanelFigure, Panel, build_figure
from make_my_figure_core.panels.builder import panel_frames, panel_typography

# The reported figure, in order: A bar, B heatmap, C scatter, D volcano.
REPORTED_PANELS = ("barplot_with_error_bar", "heatmap_clustered_matrix",
                   "scatterplot_with_regression", "volcano_plot")


def _composite(*, widths=None, pad_mm=None, **layout_kw):
    layout = FigureLayout(ncols=2, fig_width_mm=180.0, panel_dpi=72,
                          panel_pad_mm=pad_mm, **layout_kw)
    mpf = MultiPanelFigure(name="Figure 1", layout=layout)
    for i, plot_type in enumerate(REPORTED_PANELS):
        table, aux, spec = examples.load_example(plot_type)
        mpf.add_panel(Panel(plot_spec=spec, table=table.dataframe,
                            aux={k: v.dataframe for k, v in (aux or {}).items()},
                            width_in=(widths or {}).get(i, 3.2)))
    return mpf


@pytest.fixture(scope="module")
def frames_by_width():
    """``{C's width: {label: frame}}`` for the three widths in the report."""
    out = {}
    for width in (3.2, 4.2, 5.0):
        fig = build_figure(_composite(widths={2: width}))
        out[width] = {f["label"]: f for f in panel_frames(fig)}
        plt.close(fig)
    return out


# --------------------------------------------------------------------------
# alignment
# --------------------------------------------------------------------------

@pytest.mark.parametrize("width", [3.2, 4.2, 5.0])
def test_panels_in_a_column_share_one_plot_left_edge(frames_by_width, width):
    """"The alignment should be fixed - that is the beauty of alignment."

    A over C and B over D, to the thousandth of an inch, at every width C was
    given. Measured at 0.408 in out at C = 4.2 in before the fix.
    """
    f = frames_by_width[width]
    assert f["A"]["x0"] == pytest.approx(f["C"]["x0"], abs=0.002)
    assert f["B"]["x0"] == pytest.approx(f["D"]["x0"], abs=0.002)


@pytest.mark.parametrize("width", [3.2, 4.2, 5.0])
def test_panels_in_a_row_share_one_plot_top_edge(frames_by_width, width):
    """A beside B and C beside D: the plots start at the same height, whatever
    is printed above them. D's two-line count line must not lift C's plot."""
    f = frames_by_width[width]
    assert f["A"]["y1"] == pytest.approx(f["B"]["y1"], abs=0.002)
    assert f["C"]["y1"] == pytest.approx(f["D"]["y1"], abs=0.002)


def test_widening_one_panel_leaves_its_neighbours_alone(frames_by_width):
    """"As I try to increase width of C ... that should never happen."

    Widening C by 1.8 in is a change to C. A is in the same column, so its plot
    may give up the width the shared left edge needs - but it may not move, and
    B and D are not in that column at all and may not change at all.
    """
    base = frames_by_width[3.2]
    for width in (4.2, 5.0):
        f = frames_by_width[width]
        assert f["A"]["x0"] == pytest.approx(base["A"]["x0"], abs=0.03)
        assert f["A"]["x1"] - f["A"]["x0"] == pytest.approx(
            base["A"]["x1"] - base["A"]["x0"], rel=0.05)
        for label in ("B", "D"):
            assert f[label]["x1"] - f[label]["x0"] == pytest.approx(
                base[label]["x1"] - base[label]["x0"], rel=0.02)


def test_widening_a_panel_widens_that_panel(frames_by_width):
    """The control still does what it says: C's plot grows with C's width."""
    got = [frames_by_width[w]["C"]["x1"] - frames_by_width[w]["C"]["x0"]
           for w in (3.2, 4.2, 5.0)]
    assert got[1] > got[0] + 0.5 and got[2] > got[1] + 0.3


def test_panel_letters_in_a_row_sit_at_one_height():
    """The letters are placed on the grid cell, not hung off each picture: the
    pictures in a row start at different heights, so hanging the letters off
    them put A and B at different heights on the page."""
    fig = build_figure(_composite())
    heights = {}
    for text in fig.texts:
        if text.get_text() in ("A", "B", "C", "D"):
            heights[text.get_text()] = round(text.get_position()[1], 6)
    plt.close(fig)
    assert heights["A"] == heights["B"]
    assert heights["C"] == heights["D"]


# --------------------------------------------------------------------------
# size means size
# --------------------------------------------------------------------------

def test_a_panel_is_as_wide_as_it_was_asked_to_be():
    """"The panel comes out around 0.85x the number here" was the help text's
    own apology for the grid sitting inside matplotlib's default margins."""
    fig = build_figure(_composite())
    gs = fig.axes[0].get_gridspec()
    fig_w = float(fig.get_size_inches()[0])
    for col in (0, 1):
        cell = gs[0, col].get_position(fig)
        assert cell.width * fig_w == pytest.approx(3.2, rel=0.02)
    plt.close(fig)


def test_panel_padding_is_a_live_control():
    """The white space around a panel's content is the user's to spend."""
    tight = build_figure(_composite(pad_mm=0.0))
    loose = build_figure(_composite(pad_mm=4.0))
    tight_frame = panel_frames(tight)[0]
    loose_frame = panel_frames(loose)[0]
    plt.close(tight); plt.close(loose)
    tight_w = tight_frame["x1"] - tight_frame["x0"]
    loose_w = loose_frame["x1"] - loose_frame["x0"]
    assert loose_w < tight_w - 0.1


# --------------------------------------------------------------------------
# one figure, one type hierarchy
# --------------------------------------------------------------------------

def test_every_panel_carries_the_same_axis_label_size():
    """One style, one hierarchy. Scaling each panel to its own canvas gave this
    figure 12 pt axis labels in one panel and 10.2 pt in the panel beside it."""
    fig = build_figure(_composite(widths={2: 4.2}))
    measured = panel_typography(fig)
    plt.close(fig)
    sizes = {round(d["axis_font_pt"], 2) for d in measured if d.get("axis_font_pt")}
    assert len(sizes) == 1, f"panels disagree on the axis label size: {sizes}"


def test_shrinking_the_panels_shrinks_the_type():
    """"Should be able to diminish heatmap and the fonts should also decrease
    accordingly." The factor comes from the median panel, so it does."""
    big = build_figure(_composite(widths={i: 4.5 for i in range(4)}))
    small = build_figure(_composite(widths={i: 1.8 for i in range(4)}))
    big_pt = panel_typography(big)[0]["axis_font_pt"]
    small_pt = panel_typography(small)[0]["axis_font_pt"]
    plt.close(big); plt.close(small)
    assert small_pt < big_pt * 0.75


# --------------------------------------------------------------------------
# text that fits the plot it belongs to
# --------------------------------------------------------------------------

def _render(plot_type, size_in, **layout):
    from make_my_figure_core.plots import registry

    table, aux, spec = examples.load_example(plot_type)
    spec = {**spec, "layout": {**(spec.get("layout") or {}),
                               "width_mm": size_in[0] * 25.4,
                               "height_mm": size_in[1] * 25.4, **layout}}
    return registry.render(spec, table.dataframe,
                           aux={k: v.dataframe for k, v in (aux or {}).items()})


def test_a_long_y_axis_label_is_not_cropped():
    """"measurement (mean +/- SEM)" came back as "measurement (mean +/- SE".

    An axis label is centred on its AXES, and matplotlib deliberately leaves its
    along-axis extent out of every tight bounding box it computes - so the label
    ran off the top of the panel and no layout pass could see it. The fix wraps
    or shrinks it; what is asserted here is only that it is on the canvas.
    """
    result = _render("barplot_with_error_bar", (3.2, 2.56))
    figure = result.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    height_px = float(figure.get_size_inches()[1]) * figure.dpi
    label = figure.axes[0].yaxis.label
    box = label.get_window_extent(renderer)
    plt.close(figure)
    assert "mean" in label.get_text() and "SEM" in label.get_text()
    assert box.y0 >= -2.0 and box.y1 <= height_px + 2.0, (
        f"the y axis label runs from {box.y0:.0f} to {box.y1:.0f} px on a "
        f"{height_px:.0f} px canvas, so part of it is cropped")


def test_the_volcano_count_line_wraps_onto_at_most_two_balanced_lines():
    """It came out on three, the last reading "1)".

    Two causes: a hard 9 pt floor under the count line that the canvas-scaled
    hierarchy could not get below, and a wrap width guessed from the character
    count rather than measured - which is half as wide as the overflow asked for,
    and leaves a dangling tail.
    """
    result = _render("volcano_plot", (2.9, 2.0))
    title = result.figure.axes[0].title
    lines = [ln for ln in title.get_text().split("\n") if ln.strip()]
    plt.close(result.figure)
    assert len(lines) <= 2, f"the count line is on {len(lines)} lines: {lines}"
    if len(lines) == 2:
        assert len(lines[1]) > len(lines[0]) / 3, f"dangling last line: {lines}"


def test_the_regression_stats_box_takes_only_a_share_of_the_plot():
    """"The text kill the scatterplot C."

    Six lines of statistics for a two-group fit measured 209 px against a 210 px
    axes - which passed the old "narrower than the axes" test while covering the
    plot it was annotating.
    """
    from make_my_figure_core.plots.scatter import (
        MAX_STATS_AREA_FRACTION, MAX_STATS_WIDTH_FRACTION)

    result = _render("scatterplot_with_regression", (4.1, 3.0))
    figure = result.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    ax = figure.axes[0]
    axes_box = ax.get_window_extent(renderer)
    boxes = [t.get_window_extent(renderer) for t in ax.texts
             if "slope" in t.get_text()]
    plt.close(figure)
    assert boxes, "the regression stats box was not drawn"
    box = boxes[0]
    assert box.width / axes_box.width <= MAX_STATS_WIDTH_FRACTION + 0.02
    area = (box.width * box.height) / (axes_box.width * axes_box.height)
    assert area <= MAX_STATS_AREA_FRACTION + 0.02


def test_an_outside_legend_too_expensive_for_the_panel_moves_inside():
    """A legend took 38% of the scatter panel's width, leaving the plot 1.9 in of
    a 4.1 in panel. It costs nothing inside, where that plot has an empty corner.
    """
    result = _render("scatterplot_with_regression", (4.1, 3.0))
    figure = result.figure
    figure.canvas.draw()
    ax = figure.axes[0]
    legend = ax.get_legend()
    renderer = figure.canvas.get_renderer()
    inside = legend.get_window_extent(renderer).x1 <= ax.get_window_extent(renderer).x1 + 2
    plt.close(figure)
    assert inside


def test_a_plot_that_labels_its_points_keeps_its_legend_outside():
    """The other half of the same decision. A volcano's corners look empty when
    the legend is placed and hold GENE0165 by the time the figure is drawn,
    because the point labels are still being repelled apart - so a plot that
    writes on itself in data coordinates pays for the outside legend.
    """
    result = _render("volcano_plot", (2.9, 2.6))
    figure = result.figure
    figure.canvas.draw()
    ax = figure.axes[0]
    legend = ax.get_legend()
    renderer = figure.canvas.get_renderer()
    outside = legend.get_window_extent(renderer).x0 > ax.get_window_extent(renderer).x1 - 2
    plt.close(figure)
    assert outside


def test_a_shrunken_heatmap_thins_its_row_labels_rather_than_smearing_them():
    """"Should be able to diminish heatmap" - and still read it.

    Thirty gene names in a panel 2.2 in tall have about 4 pt of row each, so at
    any readable size they overlap. Shrinking stops at the publication check's
    own minimum; past that the only honest move is to show fewer labels, and to
    say which.
    """
    from make_my_figure_core.panels.builder import panel_warnings

    mpf = _composite()
    mpf.panels[1].height_in = 2.2          # the clustered heatmap
    fig = build_figure(mpf)
    notes = panel_warnings(fig)
    plt.close(fig)
    assert any("1 in every" in n and "Row labels" in n for n in notes), notes


def test_a_heatmap_with_room_keeps_every_label():
    """The thinning must not fire on a heatmap that was already readable."""
    from make_my_figure_core.panels.builder import panel_warnings

    mpf = _composite(widths={i: 4.0 for i in range(4)})
    fig = build_figure(mpf)
    notes = panel_warnings(fig)
    plt.close(fig)
    assert not any("1 in every" in n and "Row labels" in n for n in notes), notes


def test_matching_plot_heights_lines_the_frames_up_along_the_bottom():
    """"The plot height should be aligned at any cost, or the top part."

    Panels in a row are drawn the same height already; what differs is how much
    of it goes below the axes - a bar chart's rotated category labels take more
    room than a heatmap's sample names - so the plots end at different places.
    """
    loose = build_figure(_composite(widths={2: 4.2}))
    tight = build_figure(_composite(widths={2: 4.2}, match_plot_heights=True))
    a, b = (f for f in panel_frames(loose) if f["label"] in ("A", "B"))
    a2, b2 = (f for f in panel_frames(tight) if f["label"] in ("A", "B"))
    plt.close(loose); plt.close(tight)
    assert abs(a["y0"] - b["y0"]) > 0.5           # the reported mismatch
    assert a2["y0"] == pytest.approx(b2["y0"], abs=0.005)
    assert a2["y1"] == pytest.approx(b2["y1"], abs=0.005)


# --------------------------------------------------------------------------
# the outside edge of the panel, not just the plot inside it
# --------------------------------------------------------------------------

@pytest.mark.parametrize("width", [3.2, 4.2])
def test_panels_in_a_column_share_one_block_left_edge(frames_by_width, width):
    """"The ylabel, or whichever is the leftmost part, should align."

    Aligning the plotting frames alone leaves the panels ragged on the OUTSIDE:
    a heatmap's row labels are wider than a bar chart's tick numbers, so the
    heatmap's block hung 3 mm past the panel above it in the same column. Both
    edges are true at once now, because a y-axis label is positioned by a pad
    rather than by the data and can be pushed out to match its neighbour.
    """
    f = frames_by_width[width]
    for col in (0, 1):
        edges = [v["block_x0"] for v in f.values() if v["col"] == col]
        assert max(edges) - min(edges) == pytest.approx(0.0, abs=0.01), (
            f"column {col} panel blocks start at {edges}")


def test_the_block_edge_does_not_cost_the_plot_its_alignment():
    """Flushing the blocks must not break the frames - both, or it is no good."""
    fig = build_figure(_composite(widths={2: 4.2}))
    frames = {f["label"]: f for f in panel_frames(fig)}
    plt.close(fig)
    assert frames["A"]["x0"] == pytest.approx(frames["C"]["x0"], abs=0.002)
    assert frames["B"]["x0"] == pytest.approx(frames["D"]["x0"], abs=0.002)


def test_the_panel_letter_sits_just_outside_the_block_corner():
    """"A should have little gap and the plot should be aligned just below A,
    so A looks little more left than plot."

    The letter is the leftmost thing in its panel, by a hair, and the block
    starts just below it. Hung off the column rather than off each panel's own
    plot width, or A ends up 0.03 in further out than C in the same column.
    """
    fig = build_figure(_composite())
    frames = {f["label"]: f for f in panel_frames(fig)}
    width_in, height_in = (float(v) for v in fig.get_size_inches())
    letters = {t.get_text(): (t.get_position()[0] * width_in,
                              t.get_position()[1] * height_in)
               for t in fig.texts if t.get_text() in ("A", "B", "C", "D")}
    plt.close(fig)
    assert set(letters) == {"A", "B", "C", "D"}
    for label, (lx, ly) in letters.items():
        block = frames[label]["block_x0"]
        assert lx < block, f"{label}: the letter is not left of its block"
        assert block - lx < 0.25, f"{label}: the letter is {block - lx:.2f} in adrift"
        assert ly > frames[label]["y1"], f"{label}: the letter is not above the plot"
    assert letters["A"][0] == pytest.approx(letters["C"][0], abs=0.002)
    assert letters["B"][0] == pytest.approx(letters["D"][0], abs=0.002)
