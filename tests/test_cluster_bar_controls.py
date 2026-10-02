"""The row and column cluster bars are tunable, like the colourbar is.

Before this, the only thing an author could change about the cluster bars was how
many clusters to cut; their colours, thickness, padding, label and key were all
fixed in the renderer. These tests pin the controls that replaced that, and the two
bugs found while adding them: the bar label ignored ``cluster_prefix``, and row and
column bars were drawn from the same palette so the same colour meant two different
things in one figure.
"""

from __future__ import annotations

import pytest

pytest.importorskip("matplotlib")

PLOT_TYPE = "heatmap_clustered_matrix"
NEW_OPTIONS = ("cluster_palette", "cluster_strip_width", "cluster_strip_pad",
               "cluster_strip_labels", "cluster_legend", "cluster_legend_location")


def _render(**mapping):
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry

    table, aux, spec = examples.load_example(PLOT_TYPE)
    base = {"cluster_k_rows": 3, "cluster_k_columns": 3}
    spec = {**spec, "mapping": {**(spec.get("mapping") or {}), **base, **mapping}}
    return registry.render(spec, table.dataframe,
                           aux={k: v.dataframe for k, v in (aux or {}).items()})


def _legends(fig):
    return [c for c in fig.axes[0].get_children()
            if c.__class__.__name__ == "Legend"]


def _strip_axes(fig):
    """The cluster bar axes only.

    The bars are tagged ``_colorbar`` so the QA pass skips them, and the real
    colourbar carries the same tag - it is told apart by its ``<colorbar>`` label.
    """
    return [a for a in fig.axes[1:]
            if getattr(a, "_colorbar", False) and a.get_label() != "<colorbar>"]


def _close(fig):
    import matplotlib.pyplot as plt
    plt.close(fig)


# --------------------------------------------------------------------------
# The controls exist and reach the user
# --------------------------------------------------------------------------

@pytest.mark.parametrize("key", NEW_OPTIONS)
def test_each_cluster_bar_control_is_offered_in_the_ui(key):
    """A control the renderer honours but the UI never shows is not a control."""
    from make_my_figure_core import ui_hints

    keys = {o.key for o in ui_hints.OPTIONS[PLOT_TYPE]}
    assert key in keys, f"{key} is honoured by the renderer but absent from the UI"


@pytest.mark.parametrize("key", NEW_OPTIONS)
def test_the_cluster_bar_controls_are_styling_not_analysis(key):
    """These change appearance only; none may sit in the analysis scope."""
    from make_my_figure_core import ui_hints

    option = next(o for o in ui_hints.OPTIONS[PLOT_TYPE] if o.key == key)
    assert option.scope == "style", f"{key} is appearance, not analysis"


def test_every_offered_legend_location_is_one_the_renderer_knows():
    from make_my_figure_core import ui_hints
    from make_my_figure_core.plots.heatmap import _CLUSTER_LEGEND_ANCHORS

    option = next(o for o in ui_hints.OPTIONS[PLOT_TYPE]
                  if o.key == "cluster_legend_location")
    assert set(option.choices) <= set(_CLUSTER_LEGEND_ANCHORS), \
        "the UI offers a cluster legend position the renderer cannot place"


# --------------------------------------------------------------------------
# Colour
# --------------------------------------------------------------------------

def _strip_colors(fig, which):
    """The colours actually drawn in a cluster bar, in order."""
    axes = _strip_axes(fig)
    for ax in axes:
        images = ax.get_images()
        if not images:
            continue
        data = images[0].get_array()
        tall = data.shape[0] > data.shape[1]
        if (which == "rows") == tall:
            cmap = images[0].get_cmap()
            return [cmap(i) for i in range(cmap.N)]
    return []


def test_the_cluster_bar_palette_is_selectable():
    a = _render(cluster_palette="auto")
    b = _render(cluster_palette="grayscale")
    rows_a, rows_b = _strip_colors(a.figure, "rows"), _strip_colors(b.figure, "rows")
    assert rows_a and rows_b
    assert rows_a != rows_b, "cluster_palette did not change the bar colours"
    _close(a.figure); _close(b.figure)


def test_grayscale_cluster_bars_really_are_grey():
    result = _render(cluster_palette="grayscale")
    for r, g, b, _a in _strip_colors(result.figure, "rows"):
        assert abs(r - g) < 0.02 and abs(g - b) < 0.02, \
            "a 'grayscale' cluster bar drew a coloured patch"
    _close(result.figure)


def test_row_and_column_bars_do_not_use_the_same_colours():
    """The bug this fixes: one colour meaning two different things in one figure.

    With both axes clustered, "Cluster 1" of the rows and "Cluster 1" of the
    columns were drawn in the same colour, so the bars could not be told apart.
    """
    result = _render()
    rows = _strip_colors(result.figure, "rows")
    cols = _strip_colors(result.figure, "columns")
    assert rows and cols
    assert rows[0] != cols[0], \
        "row and column cluster bars start from the same colour"
    _close(result.figure)


def test_clustering_one_axis_only_still_uses_the_default_colours():
    """The shift exists to disambiguate two bars; with one bar there is nothing
    to disambiguate, so the familiar colours are kept."""
    from make_my_figure_core.clustering import CLUSTER_PALETTE
    from matplotlib.colors import to_rgba

    result = _render(cluster_k_columns=0)
    rows = _strip_colors(result.figure, "rows")
    assert rows[0] == to_rgba(CLUSTER_PALETTE[0])
    _close(result.figure)


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------

def test_the_cluster_bars_can_be_made_thicker():
    thin = _render(cluster_strip_width=4.0)
    thick = _render(cluster_strip_width=12.0)

    def row_bar_width(fig):
        for ax in _strip_axes(fig):
            images = ax.get_images()
            if images and images[0].get_array().shape[0] > images[0].get_array().shape[1]:
                return ax.get_window_extent().width
        return 0.0

    assert row_bar_width(thick.figure) > row_bar_width(thin.figure) * 1.5
    _close(thin.figure); _close(thick.figure)


def test_the_cluster_bar_pad_moves_the_bar_away_from_the_heatmap():
    near = _render(cluster_strip_pad=0.02)
    far = _render(cluster_strip_pad=0.4)

    def gap(fig):
        main = fig.axes[0].get_window_extent()
        for ax in _strip_axes(fig):
            images = ax.get_images()
            if images and images[0].get_array().shape[0] > images[0].get_array().shape[1]:
                return main.x0 - ax.get_window_extent().x1
        return 0.0

    assert gap(far.figure) > gap(near.figure)
    _close(near.figure); _close(far.figure)


# --------------------------------------------------------------------------
# Labels and key
# --------------------------------------------------------------------------

def test_the_bar_label_follows_the_cluster_prefix():
    """It used to be the literal string "Cluster" regardless of the prefix set."""
    # Labels are off by default now - the key already names the axis - so turn
    # them on to test what this is about: that the label follows the prefix.
    result = _render(cluster_prefix="Module", cluster_strip_labels=True)
    labels = {ax.get_xlabel() for ax in _strip_axes(result.figure)}
    labels |= {ax.get_ylabel() for ax in _strip_axes(result.figure)}
    assert "Module" in labels, f"bar label ignored cluster_prefix; got {labels}"
    assert "Cluster" not in labels
    _close(result.figure)


def test_the_bar_labels_can_be_turned_off():
    result = _render(cluster_strip_labels=False)
    for ax in _strip_axes(result.figure):
        assert not ax.get_xlabel().strip()
        assert not ax.get_ylabel().strip()
    _close(result.figure)


@pytest.mark.parametrize("mode,expected", [("off", 0), ("rows", 1), ("columns", 1),
                                           ("both", 2)])
def test_the_cluster_key_can_be_asked_for_explicitly(mode, expected):
    result = _render(cluster_legend=mode)
    assert len(_legends(result.figure)) == expected
    _close(result.figure)


def test_one_key_is_drawn_by_default_and_the_reason_is_given():
    """Two keys on the right need more width than the figure has, so only one is
    drawn - but the user is told, rather than left wondering."""
    result = _render()
    assert len(_legends(result.figure)) == 1
    assert any("only the row cluster key is shown" in w for w in result.warnings), \
        f"no explanation given; warnings were {result.warnings}"
    _close(result.figure)


def test_the_key_names_the_axis_it_explains_when_both_are_clustered():
    result = _render(cluster_legend="both")
    titles = {lg.get_title().get_text() for lg in _legends(result.figure)}
    assert titles == {"Rows", "Columns"}, titles
    _close(result.figure)


def test_a_single_key_is_not_drawn_twice():
    """ax.legend() both returns the legend and sets ax.legend_, so holding it with
    add_artist unconditionally draws a lone key twice."""
    result = _render(cluster_legend="rows")
    assert len(_legends(result.figure)) == 1
    _close(result.figure)


# --------------------------------------------------------------------------
# The figure stays usable whatever is chosen
# --------------------------------------------------------------------------

@pytest.mark.parametrize("location", ["right", "right_lower", "inside"])
@pytest.mark.parametrize("mode", ["auto", "both"])
def test_every_offered_combination_produces_a_clean_figure(location, mode):
    """No offered setting may clip the canvas or draw the key over the tick labels
    or the colourbar. An option that makes a bad figure is not worth offering."""
    result = _render(cluster_legend=mode, cluster_legend_location=location)
    figure = result.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    dpi = figure.dpi
    width_px, height_px = [v * dpi for v in figure.get_size_inches()]
    box = figure.get_tightbbox(renderer)
    off = (max(0.0, -box.x0 * dpi) + max(0.0, box.x1 * dpi - width_px)
           + max(0.0, -box.y0 * dpi) + max(0.0, box.y1 * dpi - height_px))
    assert off <= 4.0, f"{location}/{mode}: {off:.0f}px clipped off the canvas"

    ax = figure.axes[0]
    obstacles = [t.get_window_extent(renderer) for t in
                 ax.get_xticklabels() + ax.get_yticklabels() if t.get_text().strip()]
    obstacles += [a.get_window_extent() for a in figure.axes[1:]]
    for legend in _legends(figure):
        lb = legend.get_window_extent(renderer)
        assert not any(lb.overlaps(ob) for ob in obstacles), \
            f"{location}/{mode}: the cluster key is drawn over the plot decorations"
    _close(figure)


def test_the_bars_are_not_labelled_by_default():
    """Reported from the running app: "there are 2 cluster text in plot, remove
    them, that is not necessary".

    The key above already reads "Rows"/"Columns" over "Cluster 1, 2, 3", so
    writing "Cluster" beside each bar as well says it a third time - and it lands
    on top of the axis labels, which is where it was noticed.
    """
    result = _render()
    labels = {ax.get_xlabel() for ax in _strip_axes(result.figure)}
    labels |= {ax.get_ylabel() for ax in _strip_axes(result.figure)}
    assert not any(l.strip() for l in labels), f"the bars are still labelled: {labels}"
    _close(result.figure)


def test_both_cluster_bars_get_the_same_gap_from_the_heatmap():
    """They did not. make_axes_locatable builds a fresh divider per call, and two
    dividers on one axes overwrite each other's space reservation - so with both
    bars the row bar's pad did nothing and it sat hard against the heatmap, while
    the column bar (appended last) worked. Each alone was fine, which is what
    made it look like a row-only bug.
    """
    for pad in (0.02, 0.18, 0.40):
        result = _render(cluster_strip_pad=pad)
        figure = result.figure
        figure.canvas.draw()
        main = figure.axes[0].get_window_extent()
        gaps = {}
        for ax in _strip_axes(figure):
            box = ax.get_window_extent()
            if box.height > box.width:
                gaps["row"] = main.x0 - box.x1
            else:
                gaps["col"] = box.y0 - main.y1
        _close(figure)
        assert set(gaps) == {"row", "col"}, gaps
        assert abs(gaps["row"] - gaps["col"]) < 2.0, (
            f"pad={pad}: row gap {gaps['row']:.1f}px but column gap "
            f"{gaps['col']:.1f}px - the two bars do not share a divider")
        assert gaps["row"] > 0, (
            f"pad={pad}: the row bar overlaps the heatmap ({gaps['row']:.1f}px)")


def test_the_row_bar_does_not_cover_the_row_labels():
    """The divider reserves the margin but knows nothing about the tick labels
    that already live there, so the bar was drawn over the end of every name."""
    result = _render(cluster_strip_pad=0.18)
    figure = result.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    ax = figure.axes[0]
    row_bar = next(a for a in _strip_axes(figure)
                   if a.get_window_extent().height > a.get_window_extent().width)
    bar_x0 = row_bar.get_window_extent().x0
    worst = max((t.get_window_extent(renderer).x1 - bar_x0
                 for t in ax.get_yticklabels() if t.get_text().strip()), default=0.0)
    _close(figure)
    assert worst <= 1.0, f"row labels reach {worst:.1f}px into the cluster bar"


def test_turning_the_bars_on_does_not_cramp_the_column_labels():
    """The bars live in the margin, and the margin comes out of the axes - so
    switching them on used to narrow the heatmap until its column labels
    collided. The figure asks for the extra inches instead."""
    import matplotlib.pyplot as plt

    def spacing_vs_need(**mapping):
        result = _render(**mapping)
        figure = result.figure
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        labels = [t for t in figure.axes[0].get_xticklabels() if t.get_text().strip()]
        xs = sorted(t.get_window_extent(renderer).x0 for t in labels)
        step = min((b - a) for a, b in zip(xs, xs[1:])) if len(xs) > 1 else 0.0
        need = labels[0].get_fontsize() * figure.dpi / 72.0 if labels else 0.0
        plt.close(figure)
        return step, need

    step, need = spacing_vs_need(cluster_strip_pad=0.18)
    assert step >= need, (
        f"with cluster bars the columns are {step:.1f}px apart but vertical "
        f"labels need {need:.1f}px - the bars were taken out of the heatmap")


# --------------------------------------------------------------------------
# Picked point labels are placed together, not one at a time
# --------------------------------------------------------------------------

def test_picked_scatter_labels_avoid_each_other():
    """Reported from the app: picking several nearby points piled their names on
    top of each other, while the volcano's labels do not.

    The scatter annotated each point separately at a fixed (3, 3) offset, so two
    close points always collided. The shared repeller in plots.base - the one the
    volcano already used - is now applied here too.
    """
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry
    import matplotlib.pyplot as plt

    table, _aux, spec = examples.load_example("scatterplot_with_regression")
    frame = table.dataframe
    picks = [str(v) for v in frame["sample_id"].head(14)]
    spec = {**spec, "mapping": {**(spec.get("mapping") or {}),
                                "label": "sample_id", "selected_labels": picks}}
    result = registry.render(spec, frame, aux={})
    figure = result.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    labels = [t for t in figure.axes[0].texts
              if t.get_text().strip() in picks]
    boxes = [t.get_window_extent(renderer) for t in labels]
    overlaps = sum(1 for i in range(len(boxes)) for j in range(i + 1, len(boxes))
                   if boxes[i].overlaps(boxes[j]))
    plt.close(figure)
    assert len(labels) == len(picks), f"{len(labels)} of {len(picks)} picks drawn"
    # Not zero: 14 labels among ~60 points in a 4 x 3 in axes cannot always be
    # fully separated, and the solver also avoids the points themselves. Before
    # this it was 6; the guard is that it stays well under the un-repelled count.
    assert overlaps <= 3, (
        f"{overlaps} of the picked labels still overlap each other; the fixed "
        f"offset gave 6, so placement has regressed")


def test_the_label_repeller_is_shared_not_per_renderer():
    """It lived in volcano.py while the scatter had none, which is how one plot
    got overlap avoidance and the other did not."""
    from make_my_figure_core.plots import base

    assert callable(getattr(base, "repel_labels", None)), (
        "the overlap-avoiding label placer is not in plots.base, so each "
        "renderer will solve it again or not at all")


# --------------------------------------------------------------------------
# Which edge the tick labels sit on
# --------------------------------------------------------------------------

@pytest.mark.parametrize("key,choices", [("row_label_side", {"left", "right"}),
                                         ("column_label_side", {"bottom", "top"})])
def test_the_label_side_is_offered(key, choices):
    from make_my_figure_core import ui_hints

    option = next((o for o in ui_hints.options(PLOT_TYPE) if o.key == key), None)
    assert option is not None, f"{key} is not offered"
    assert set(option.choices) == choices


def test_row_labels_can_move_to_the_right_of_the_heatmap():
    """Reported from the app: with a row cluster bar the tick marks, the bar and
    the gene names all compete for the left margin, leaving the marks orphaned
    between the bar and the data. Moving the names to the right - the usual
    clustermap arrangement - leaves that margin to the bar alone.
    """
    left = _render(row_label_side="left")
    right = _render(row_label_side="right")
    try:
        for result, side in ((left, "left"), (right, "right")):
            figure = result.figure
            figure.canvas.draw()
            renderer = figure.canvas.get_renderer()
            ax = figure.axes[0]
            main = ax.get_window_extent()
            boxes = [t.get_window_extent(renderer) for t in ax.get_yticklabels()
                     if t.get_text().strip()]
            assert boxes, "no row labels drawn"
            if side == "right":
                assert all(b.x0 > main.x1 for b in boxes), \
                    "row labels asked to sit right are still on the left"
            else:
                assert all(b.x1 < main.x0 + 1 for b in boxes)
    finally:
        _close(left.figure); _close(right.figure)


def test_moving_the_row_labels_right_widens_the_heatmap():
    """The point of the move: the left margin stops holding two things."""
    left = _render(row_label_side="left", cluster_strip_pad=0.16)
    right = _render(row_label_side="right", cluster_strip_pad=0.16)
    try:
        for r in (left, right):
            r.figure.canvas.draw()
        assert (right.figure.axes[0].get_window_extent().width
                > left.figure.axes[0].get_window_extent().width)
    finally:
        _close(left.figure); _close(right.figure)


@pytest.mark.parametrize("side", ["left", "right"])
@pytest.mark.parametrize("col_k", [0, 3])
def test_nothing_collides_whichever_edge_the_labels_are_on(side, col_k):
    """Moving the labels put them under the colourbar and then under the cluster
    key - each fixed in turn, and each a thing that only shows up on the render.
    """
    from make_my_figure_core.plots.base import content_overflow_inches

    result = _render(row_label_side=side, cluster_k_columns=col_k,
                     cluster_strip_pad=0.16)
    figure = result.figure
    try:
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        ax = figure.axes[0]
        obstacles = [t.get_window_extent(renderer) for t in ax.get_yticklabels()
                     if t.get_text().strip()]
        obstacles += [a.get_window_extent() for a in figure.axes
                      if a.get_label() == "<colorbar>"]
        for legend in (c for c in ax.get_children()
                       if c.__class__.__name__ == "Legend"):
            box = legend.get_window_extent(renderer)
            assert not any(box.overlaps(ob) for ob in obstacles), \
                f"side={side} col_k={col_k}: the cluster key sits on the labels"
        label_box = ax.yaxis.label.get_window_extent(renderer)
        assert not any(label_box.overlaps(ob) for ob in obstacles), \
            f"side={side} col_k={col_k}: the axis label sits on the labels"
        assert max(content_overflow_inches(figure)) * figure.dpi <= 4.0
    finally:
        _close(figure)


# --------------------------------------------------------------------------
# The option tables themselves
# --------------------------------------------------------------------------

def test_no_plot_type_is_declared_twice_in_the_option_table():
    """A repeated key silently discards the earlier list.

    OPTIONS had three empty placeholder entries shadowed by the real ones later
    in the same literal. Harmless while they stayed empty - Python keeps the last
    - and a trap the moment anyone adds an option to the first one, which is
    exactly what happened while adding the point-outline control: the option was
    declared, the UI never showed it, and nothing complained.
    """
    import ast
    import collections
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "make_my_figure_core"
              / "ui_hints.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    duplicates = {}
    for node in ast.walk(tree):
        target = getattr(node, "target", None)
        if target is None or getattr(target, "id", "") not in ("OPTIONS",
                                                               "COLUMN_FIELDS"):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        keys = [k.value for k in node.value.keys]
        repeated = {k: n for k, n in collections.Counter(keys).items() if n > 1}
        if repeated:
            duplicates[target.id] = repeated
    assert not duplicates, f"a later entry silently discards an earlier one: {duplicates}"


def test_every_declared_option_is_reachable_through_the_public_accessor():
    """Declaring an option in the table is only half of it; ui_hints.options()
    is what the app reads, and a shadowed entry never gets there."""
    from make_my_figure_core import ui_hints

    for plot_type, declared in ui_hints.OPTIONS.items():
        reachable = {o.key for o in ui_hints.options(plot_type)}
        missing = {o.key for o in declared} - reachable
        assert not missing, f"{plot_type}: declared but unreachable: {sorted(missing)}"
