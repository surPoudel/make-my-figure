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
    result = _render(cluster_prefix="Module")
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
