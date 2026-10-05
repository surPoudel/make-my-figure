"""A requested figure width is the width you get, on every plot type.

Three separate layers used to overrule it. A renderer's legibility floor - "a
network graph needs 5.2 inches for its labels" - is right for the size nobody
asked for and wrong as an answer to a direct request, so picking single, onehalf
or double all returned 132 mm and the control looked dead. The fitting pass that
keeps an outside legend on the canvas grew the figure instead, handing back 157
mm for a 110 mm column. And the spatial maps widened for their legend before
either ran.

A width is an instruction. When the content genuinely does not fit, the renderer
says so and the plot area gives up the room - it does not quietly return a
different figure, which is the one outcome that makes a journal submission fail
at the typesetter rather than on screen.
"""

from __future__ import annotations

import pytest

pytest.importorskip("matplotlib")

# Two named presets, two measurements. 57 mm is the narrowest column any of the
# shipped journal presets asks for, and is deliberately severe for the plot types
# that size themselves from their data.
REQUESTS = [("single", 110.0), ("double", 180.0), ("57mm", 57.0), ("174mm", 174.0)]


def _all_plot_types():
    from make_my_figure_core import examples

    return sorted(examples.plot_types_with_examples())


def _render(plot_type, column_width):
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry

    table, aux, spec = examples.load_example(plot_type)
    layout = {**(spec.get("layout") or {}), "column_width": column_width}
    # width_mm would answer the question before column_width was consulted.
    layout.pop("width_mm", None)
    return registry.render({**spec, "layout": layout}, table.dataframe,
                           aux={k: v.dataframe for k, v in (aux or {}).items()})


@pytest.mark.parametrize("plot_type", _all_plot_types())
@pytest.mark.parametrize("column_width,expected_mm", REQUESTS)
def test_the_figure_is_the_width_that_was_asked_for(plot_type, column_width, expected_mm):
    import matplotlib.pyplot as plt

    result = _render(plot_type, column_width)
    drawn_mm = result.figure.get_size_inches()[0] * 25.4
    plt.close(result.figure)
    assert abs(drawn_mm - expected_mm) < 0.5, (
        f"{plot_type}: asked for {column_width} ({expected_mm:.0f} mm), "
        f"drew {drawn_mm:.1f} mm")


@pytest.mark.parametrize("plot_type", ["network_graph", "confusion_matrix",
                                       "neighborhood_enrichment_matrix", "upset_plot"])
def test_a_width_below_the_legibility_floor_is_obeyed_and_reported(plot_type):
    """Obeyed *and* reported - silence here is what made the control look broken."""
    import matplotlib.pyplot as plt

    result = _render(plot_type, "57mm")
    plt.close(result.figure)
    assert any("narrower" in w or "tight" in w.lower() for w in result.warnings), (
        f"{plot_type}: squeezed to 57 mm without telling anyone. "
        f"Warnings were: {result.warnings}")


def test_default_leaves_the_renderer_to_choose():
    """"default" is not a request, so a renderer's own sizing still applies."""
    import matplotlib.pyplot as plt

    from make_my_figure_core.plots.base import chosen_column_width, requested_width

    assert chosen_column_width({"layout": {"column_width": "default"}}) is None
    assert requested_width({"layout": {"column_width": "default"}}) is None
    # An unparseable value falls back to automatic rather than erroring.
    assert requested_width({"layout": {"column_width": "nonsense"}}) is None

    result = _render("network_graph", "default")
    drawn_mm = result.figure.get_size_inches()[0] * 25.4
    plt.close(result.figure)
    assert drawn_mm > 110.0, (
        "the automatic size should still apply the renderer's legibility floor, "
        f"but drew {drawn_mm:.1f} mm")
