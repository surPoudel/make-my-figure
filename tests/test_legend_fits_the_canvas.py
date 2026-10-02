"""An outside legend has to end up inside the figure.

Eleven of the 45 plot types used to clip one in their default output - no unusual
request involved, just opening the example. The legend is placed relative to the
axes, so a long label ("Non_responder", "CD68+CD163+ macrophages") hung off the
edge. Exporting with a tight bounding box hid it, which is why it lasted: the
saved file looked right, and the preview and any fixed-size export did not.
"""

from __future__ import annotations

import pytest

pytest.importorskip("matplotlib")

# These genuinely cannot fit at 4 x 2 in: an eight-entry key beside a two-inch
# plot leaves no room, and the fitting pass will not shrink the plot below 55% of
# the canvas to buy some. They are reported, not cropped in silence.
NO_ROOM_AT_4X2 = {"scatterplot_with_regression", "spatial_categorical_map",
                  "spatial_composition_map", "neighborhood_enrichment_matrix"}


def _all_plot_types():
    from make_my_figure_core import examples

    return sorted(examples.plot_types_with_examples())


def _render(plot_type, layout=None):
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry

    table, aux, spec = examples.load_example(plot_type)
    if layout:
        spec = {**spec, "layout": {**(spec.get("layout") or {}), **layout}}
    return registry.render(spec, table.dataframe,
                           aux={k: v.dataframe for k, v in (aux or {}).items()})


def _overflow_px(figure):
    from make_my_figure_core.plots.base import content_overflow_inches

    return max(content_overflow_inches(figure)) * figure.dpi


def _close(figure):
    import matplotlib.pyplot as plt

    plt.close(figure)


@pytest.mark.parametrize("plot_type", _all_plot_types())
def test_nothing_is_clipped_in_the_default_figure(plot_type):
    """The out-of-the-box figure is the one most people will export."""
    result = _render(plot_type)
    over = _overflow_px(result.figure)
    _close(result.figure)
    assert over <= 4.0, f"{plot_type}: {over:.0f}px drawn outside the canvas"


@pytest.mark.parametrize("plot_type", [p for p in _all_plot_types()
                                       if p not in NO_ROOM_AT_4X2])
def test_nothing_is_clipped_at_a_pinned_panel_size(plot_type):
    result = _render(plot_type, {"width_mm": 101.6, "height_mm": 50.8})
    over = _overflow_px(result.figure)
    _close(result.figure)
    assert over <= 4.0, f"{plot_type}: {over:.0f}px clipped at a pinned 4 x 2 in"


@pytest.mark.parametrize("plot_type", _all_plot_types())
def test_a_pinned_size_is_never_overridden_to_fit_a_legend(plot_type):
    """Growing the canvas is the right answer only when nobody asked for a size.

    Four spatial maps used to widen themselves for their key after the pinned
    size had been applied, so asking for 4 inches gave 6.4.
    """
    result = _render(plot_type, {"width_mm": 101.6, "height_mm": 50.8})
    size = tuple(round(float(v), 2) for v in result.figure.get_size_inches())
    _close(result.figure)
    assert size == (4.0, 2.0), f"{plot_type}: asked for 4.0 x 2.0 in, got {size}"


@pytest.mark.parametrize("plot_type", sorted(NO_ROOM_AT_4X2))
def test_a_legend_that_cannot_fit_is_reported_rather_than_cropped(plot_type):
    result = _render(plot_type, {"width_mm": 101.6, "height_mm": 50.8})
    _close(result.figure)
    assert any("falls outside" in w for w in result.warnings), (
        f"{plot_type} cropped its legend without saying so; warnings were "
        f"{result.warnings}")


def test_growing_the_canvas_is_reported():
    """A figure coming back a different size than the renderer chose is worth a
    word, so nobody wonders why their export is 4.75 in and not 4.33."""
    result = _render("volcano_plot")
    _close(result.figure)
    assert any("widened" in w for w in result.warnings)


def test_growing_keeps_the_plot_area_rather_than_shrinking_it():
    """The point of growing is not to pay for the key out of the data area."""
    from make_my_figure_core.plots.base import fit_content_to_canvas
    import matplotlib.pyplot as plt

    figure, ax = plt.subplots(figsize=(4.0, 3.0))
    ax.plot([0, 1], [0, 1], label="a label long enough to hang off the edge")
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0))
    figure.canvas.draw()
    before = ax.get_window_extent().width / figure.dpi
    fit_content_to_canvas(figure)
    figure.canvas.draw()
    after = ax.get_window_extent().width / figure.dpi
    assert after >= before - 0.05, (
        f"the plot area shrank from {before:.2f} to {after:.2f} in while growing")
    assert figure.get_size_inches()[0] > 4.0
    plt.close(figure)


def test_a_figure_with_nothing_outside_the_canvas_is_left_alone():
    from make_my_figure_core.plots.base import fit_content_to_canvas
    import matplotlib.pyplot as plt

    figure, ax = plt.subplots(figsize=(5.0, 4.0))
    ax.plot([0, 1], [0, 1])
    figure.canvas.draw()
    assert fit_content_to_canvas(figure) == []
    assert tuple(figure.get_size_inches()) == (5.0, 4.0)
    plt.close(figure)


def test_the_canvas_is_not_grown_without_limit():
    from make_my_figure_core.plots.base import MAX_FIT_GROWTH_IN, fit_content_to_canvas
    import matplotlib.pyplot as plt

    figure, ax = plt.subplots(figsize=(3.0, 2.0))
    ax.plot([0, 1], [0, 1], label="x" * 400)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0))
    fit_content_to_canvas(figure)
    assert figure.get_size_inches()[0] <= 3.0 + MAX_FIT_GROWTH_IN + 0.01
    plt.close(figure)
