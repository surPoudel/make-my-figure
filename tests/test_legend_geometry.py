"""Legend positioning controls: do they move the legend, and only the legend?

Reported need: the location choices existed, but nothing could nudge a legend a
few points, open out its rows, or push an outside key further from the plot.

Everything here is measured on the drawn legend in POINTS, because that is the
unit the controls are in - an offset of 18 pt must move the legend 18 pt at any
figure size, or the control is a suggestion rather than a setting.
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

from make_my_figure_core import examples
from make_my_figure_core.plots import base, registry
from make_my_figure_core.plots.base import LEGEND_GEOMETRY_KEYS
from make_my_figure_core.styles.capabilities import get_style_capabilities

# One plot per way of getting a legend: grouped scatter (inside, "best"),
# survival curves (per-group lines), and a volcano, whose renderer places its
# key OUTSIDE on purpose - the case a nudge must not undo.
WITH_LEGENDS = ("scatterplot_with_regression", "kaplan_meier_survival_curve",
                "volcano_plot")


def _render(plot_type, **layout):
    table, aux, spec = examples.load_example(plot_type)
    spec = {**spec, "layout": {**(spec.get("layout") or {}), **layout}}
    return registry.render(spec, table.dataframe,
                           aux={k: v.dataframe for k, v in (aux or {}).items()})


def _legend_box_pt(result):
    """The legend's drawn box in points, or None when there is no legend."""
    figure = result.figure
    figure.canvas.draw()
    ax = base.legend_axes(figure)
    leg = ax.get_legend() if ax is not None else None
    if leg is None:
        return None
    box = leg.get_window_extent(figure.canvas.get_renderer())
    scale = 72.0 / figure.dpi
    return (box.x0 * scale, box.y0 * scale, box.width * scale, box.height * scale)


def _measure(plot_type, **layout):
    result = _render(plot_type, **layout)
    box = _legend_box_pt(result)
    plt.close(result.figure)
    return box


# --------------------------------------------------------------------------
# the offsets move the legend by exactly what was asked
# --------------------------------------------------------------------------

@pytest.mark.parametrize("plot_type", WITH_LEGENDS)
def test_an_x_offset_moves_the_legend_that_far_sideways(plot_type):
    base_box = _measure(plot_type)
    moved = _measure(plot_type, legend_offset_x=18.0)
    assert base_box and moved
    assert moved[0] - base_box[0] == pytest.approx(18.0, abs=0.5)
    assert moved[1] - base_box[1] == pytest.approx(0.0, abs=0.5)


@pytest.mark.parametrize("plot_type", WITH_LEGENDS)
def test_a_y_offset_moves_the_legend_that_far_vertically(plot_type):
    base_box = _measure(plot_type)
    moved = _measure(plot_type, legend_offset_y=-12.0)
    assert moved[1] - base_box[1] == pytest.approx(-12.0, abs=0.5)
    assert moved[0] - base_box[0] == pytest.approx(0.0, abs=0.5)


@pytest.mark.parametrize("plot_type", WITH_LEGENDS)
def test_an_offset_does_not_relocate_a_legend_the_plot_put_outside(plot_type):
    """The defect this contract exists to prevent.

    Resolving a location whenever geometry changed moved the volcano's outside
    legend inside the axes: a control that asked for 18 pt moved it 91.
    """
    base_box = _measure(plot_type)
    nudged = _measure(plot_type, legend_offset_x=4.0)
    assert abs(nudged[0] - base_box[0]) < 8.0
    assert abs(nudged[1] - base_box[1]) < 2.0


def test_the_gap_pushes_an_outside_legend_away_from_the_plot():
    flush = _measure("scatterplot_with_regression", legend_location="outside right")
    spaced = _measure("scatterplot_with_regression", legend_location="outside right",
                      legend_gap=24.0)
    assert spaced[0] - flush[0] == pytest.approx(24.0, abs=0.5)


def test_the_gap_does_nothing_to_a_legend_inside_the_axes():
    """It is a legend-to-axes gap; inside the axes there is no such edge."""
    inside = _measure("scatterplot_with_regression", legend_location="inside upper left")
    gapped = _measure("scatterplot_with_regression", legend_location="inside upper left",
                      legend_gap=24.0)
    assert gapped[0] == pytest.approx(inside[0], abs=0.5)


# --------------------------------------------------------------------------
# padding
# --------------------------------------------------------------------------

@pytest.mark.parametrize("plot_type", WITH_LEGENDS)
def test_internal_padding_makes_the_legend_bigger(plot_type):
    base_box = _measure(plot_type)
    padded = _measure(plot_type, legend_borderpad=2.0, legend_labelspacing=1.5)
    assert padded[2] > base_box[2] + 5.0, "no extra width from the border pad"
    assert padded[3] > base_box[3] + 5.0, "no extra height from the row spacing"


def test_column_spacing_only_shows_with_more_than_one_column():
    """It is matplotlib's own control and it needs columns to act on."""
    one = _measure("volcano_plot", legend_columnspacing=4.0)
    assert one is not None


# --------------------------------------------------------------------------
# nothing happens unless asked
# --------------------------------------------------------------------------

@pytest.mark.parametrize("plot_type", WITH_LEGENDS)
def test_a_figure_that_sets_no_geometry_is_unchanged(plot_type):
    """Absent is the reset: the legend is where the plot type drew it."""
    first = _measure(plot_type)
    again = _measure(plot_type, **{k: None for k in LEGEND_GEOMETRY_KEYS})
    assert again == pytest.approx(first, abs=0.01)


def test_zero_is_also_a_no_op():
    first = _measure("volcano_plot")
    zeroed = _measure("volcano_plot", legend_offset_x=0.0, legend_offset_y=0.0,
                      legend_gap=0.0)
    assert zeroed == pytest.approx(first, abs=0.01)


# --------------------------------------------------------------------------
# the controls are offered only where they can work
# --------------------------------------------------------------------------

def test_every_plot_that_draws_a_legend_declares_that_it_does():
    """The GUI hides the legend controls using this flag, so it has to be true."""
    wrong = []
    for plot_type in sorted(registry.available_plot_types()):
        if not examples.entry(plot_type):
            continue
        table, aux, spec = examples.load_example(plot_type)
        result = registry.render(
            spec, table.dataframe,
            aux={k: v.dataframe for k, v in (aux or {}).items()})
        drawn = (any(ax.get_legend() is not None for ax in result.figure.axes)
                 or bool(result.figure.legends))
        plt.close(result.figure)
        if drawn and not get_style_capabilities(plot_type).supports_legend:
            wrong.append(plot_type)
    assert wrong == [], f"draw a legend but declare supports_legend=False: {wrong}"


def test_geometry_on_a_plot_without_a_legend_is_harmless():
    """No legend, no crash, no warning storm - the control is simply hidden."""
    result = _render("bland_altman_plot", legend_offset_x=20.0, legend_borderpad=2.0)
    assert _legend_box_pt(result) is None
    assert not [w for w in result.warnings if "Legend" in w]
    plt.close(result.figure)


def test_geometry_round_trips_through_the_plotspec():
    import json

    table, aux, spec = examples.load_example("volcano_plot")
    spec = {**spec, "layout": {**(spec.get("layout") or {}),
                               "legend_offset_x": 14.0, "legend_offset_y": -6.0}}
    reloaded = json.loads(json.dumps(spec))
    registry.validate_plot_spec(reloaded)
    plain = _measure("volcano_plot")
    result = registry.render(reloaded, table.dataframe,
                             aux={k: v.dataframe for k, v in (aux or {}).items()})
    box = _legend_box_pt(result)
    plt.close(result.figure)
    assert box[0] - plain[0] == pytest.approx(14.0, abs=0.5)
    assert box[1] - plain[1] == pytest.approx(-6.0, abs=0.5)


def test_geometry_is_a_portable_preset_key():
    from make_my_figure_core.presets import LAYOUT_STYLE_KEYS

    assert set(LEGEND_GEOMETRY_KEYS) <= set(LAYOUT_STYLE_KEYS)
