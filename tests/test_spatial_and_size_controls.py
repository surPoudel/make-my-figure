"""Controls that were offered but did nothing.

All three were reported from the running app, and all three were real: the global
Palette had no effect on the enrichment matrix, the six spatial plot types offered
no options at all, and nothing in the "Figure size" panel redrew the preview.
"""

from __future__ import annotations

import pytest

pytest.importorskip("matplotlib")

SPATIAL_PLOTS = ["spatial_categorical_map", "spatial_feature_map",
                 "spatial_transcript_map", "spatial_roi_map",
                 "spatial_composition_map", "neighborhood_enrichment_matrix"]


def _render(plot_type, *, mapping=None, style=None, layout=None):
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry

    table, aux, spec = examples.load_example(plot_type)
    spec = dict(spec)
    if mapping:
        spec["mapping"] = {**(spec.get("mapping") or {}), **mapping}
    if style:
        spec["style"] = {**(spec.get("style") or {}), **style}
    if layout:
        spec["layout"] = {**(spec.get("layout") or {}), **layout}
    return registry.render(spec, table.dataframe,
                           aux={k: v.dataframe for k, v in (aux or {}).items()})


def _pixels(result):
    import numpy as np

    figure = result.figure
    figure.canvas.draw()
    return np.asarray(figure.canvas.buffer_rgba(), dtype=np.float32)


def _differs(a, b):
    import numpy as np
    import matplotlib.pyplot as plt

    pa, pb = _pixels(a), _pixels(b)
    plt.close(a.figure); plt.close(b.figure)
    if pa.shape != pb.shape:
        return True
    return float(np.abs(pa - pb).mean()) > 1e-4


# --------------------------------------------------------------------------
# Every spatial plot type offers controls
# --------------------------------------------------------------------------

@pytest.mark.parametrize("plot_type", SPATIAL_PLOTS)
def test_every_spatial_plot_type_offers_some_controls(plot_type):
    """All six shipped with an empty option list, so the panel was blank."""
    from make_my_figure_core import ui_hints

    assert ui_hints.options(plot_type), \
        f"{plot_type} offers the user no options at all"


@pytest.mark.parametrize("plot_type", SPATIAL_PLOTS)
def test_spatial_options_reach_the_renderer(plot_type):
    """Declaring an option is not enough; the renderer has to receive it.

    These land in ``mapping`` and are overlaid onto the spatial block, because a
    value the user just chose should outrank whatever the saved spec carried.
    """
    from make_my_figure_core import ui_hints
    from make_my_figure_core.plots._spatial_shared import GUI_SETTABLE_SPATIAL_KEYS

    keys = {o.key for o in ui_hints.options(plot_type)}
    routed = keys & set(GUI_SETTABLE_SPATIAL_KEYS)
    assert routed, (
        f"{plot_type} declares {sorted(keys)} but none is overlaid onto the "
        f"spatial block, so none of them can take effect")


def test_a_gui_value_outranks_the_saved_spatial_block():
    """The bug behind the report: the bundled example pinned a colormap, so
    nothing the user picked could ever win."""
    base = _render("neighborhood_enrichment_matrix")
    changed = _render("neighborhood_enrichment_matrix", mapping={"cmap": "Greys"})
    assert _differs(base, changed)


# --------------------------------------------------------------------------
# The global palette
# --------------------------------------------------------------------------

@pytest.mark.parametrize("palette", ["grayscale", "high_contrast", "colorblind_safe"])
def test_the_palette_reaches_the_enrichment_matrix(palette):
    """It did not: the renderer fell back to a hard-coded "RdBu_r" and the
    example pinned the same value, so the control was doubly dead."""
    base = _render("neighborhood_enrichment_matrix")
    changed = _render("neighborhood_enrichment_matrix",
                      style={"palette_name": palette})
    assert _differs(base, changed), f"palette {palette} changed nothing"


def test_the_enrichment_example_no_longer_pins_a_colormap():
    """Pinning it defeated the Palette control for everyone who opened the
    example. The publication style's diverging default is the same colormap, so
    removing the pin left the default figure untouched."""
    from make_my_figure_core import examples

    _table, _aux, spec = examples.load_example("neighborhood_enrichment_matrix")
    assert "cmap" not in (spec.get("spatial") or {}), \
        "the example pins a colormap again, which silently disables the Palette"


def test_the_default_enrichment_figure_is_unchanged_by_that_removal():
    """The point of removing the pin was to restore a control, not to restyle."""
    base = _render("neighborhood_enrichment_matrix")
    explicit = _render("neighborhood_enrichment_matrix", mapping={"cmap": "RdBu_r"})
    assert not _differs(base, explicit), \
        "the default enrichment figure no longer matches the colormap it shipped with"


# --------------------------------------------------------------------------
# Figure width presets
# --------------------------------------------------------------------------

def test_each_width_preset_exports_at_its_own_width():
    """default / single / onehalf / double used to collapse onto two values,
    so three of the four choices produced the same file."""
    from apps.desktop_app.controller import DesktopController

    controller = DesktopController()
    widths = {}
    for preset in ("default", "single", "onehalf", "double"):
        spec = controller.build_spec("volcano_plot", "publication", "t", {},
                                     width=preset, dpi=300)
        widths[preset] = spec["output"]["width_mm"]
    assert len(set(widths.values())) == 4, f"presets share a width: {widths}"
    assert widths["single"] < widths["default"] < widths["onehalf"] < widths["double"]


def test_the_width_preset_changes_the_rendered_figure():
    assert _differs(_render("volcano_plot", layout={"column_width": "single"}),
                    _render("volcano_plot", layout={"column_width": "double"}))


# --------------------------------------------------------------------------
# The size panel redraws the preview
# --------------------------------------------------------------------------

def test_every_figure_size_control_redraws_the_preview():
    """The whole panel was inert: the values were only read the next time
    something else happened to trigger a render.

    Checked by reading the source rather than by building a MainWindow. A second
    Qt window inside one pytest process aborts the interpreter when several GUI
    test files run together, and a test that takes the suite down with it is not
    worth the slightly stronger assertion.
    """
    import inspect
    import re
    from pathlib import Path

    source = Path(__file__).resolve().parents[1] / "apps" / "desktop_app" / "main.py"
    text = source.read_text(encoding="utf-8")
    for name, signal in (("width_combo", "currentTextChanged"),
                         ("fig_w_mm", "valueChanged"),
                         ("fig_h_mm", "valueChanged"),
                         ("dpi_spin", "valueChanged")):
        pattern = rf"self\.{name}\.{signal}\.connect\(self\.render_preview\)"
        assert re.search(pattern, text), \
            f"{name} does not redraw the preview when it changes"

    # The connections above are only as good as the method they name.
    pyside = pytest.importorskip("PySide6", reason="needs PySide6 to import the app")
    assert pyside
    from apps.desktop_app.main import MainWindow

    assert callable(getattr(MainWindow, "render_preview", None)), \
        "the size controls are wired to a render_preview that does not exist"
    assert inspect.isfunction(MainWindow.render_preview)


# --------------------------------------------------------------------------
# percentile_clip from a single-value control
# --------------------------------------------------------------------------

def test_a_single_percentile_clip_means_a_symmetric_trim():
    """The GUI control is one spinner; the renderer wants [low, high].

    Declaring the option without reconciling those crashed the renderer with
    "object of type 'float' has no len()" - found by the option audit, which
    tries every control at the end of its range.
    """
    pair = _render("spatial_feature_map", mapping={"percentile_clip": [2, 98]})
    single = _render("spatial_feature_map", mapping={"percentile_clip": 2})
    assert not _differs(pair, single)


def test_a_percentile_clip_of_zero_clips_nothing():
    base = _render("spatial_feature_map")
    off = _render("spatial_feature_map", mapping={"percentile_clip": 0})
    assert not _differs(base, off)


def test_a_percentile_clip_that_would_invert_the_range_is_refused():
    """Trimming 60% from each tail is not a figure; say so rather than draw it."""
    from make_my_figure_core.plots.base import RenderError

    with pytest.raises(RenderError, match="below 50"):
        _render("spatial_feature_map", mapping={"percentile_clip": 60})


def test_clipping_actually_narrows_the_colour_range():
    base = _render("spatial_feature_map")
    clipped = _render("spatial_feature_map", mapping={"percentile_clip": 10})
    assert _differs(base, clipped)


# --------------------------------------------------------------------------
# The width preset works on every plot type
# --------------------------------------------------------------------------

def _width_in(plot_type, preset):
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry
    import matplotlib.pyplot as plt

    table, aux, spec = examples.load_example(plot_type)
    spec = {**spec, "layout": {**(spec.get("layout") or {}),
                               "column_width": preset}}
    result = registry.render(spec, table.dataframe,
                             aux={k: v.dataframe for k, v in (aux or {}).items()})
    width = round(float(result.figure.get_size_inches()[0]), 2)
    plt.close(result.figure)
    return width, result.warnings


def _all_plot_types():
    from make_my_figure_core import examples

    return sorted(examples.plot_types_with_examples())


@pytest.mark.parametrize("plot_type", _all_plot_types())
def test_every_plot_type_honours_every_width_preset(plot_type):
    """Three presets, three widths. Three plot types used to clamp the narrow
    ones to a legibility floor, so the control did nothing on them at all."""
    widths = {p: _width_in(plot_type, p)[0]
              for p in ("single", "onehalf", "double")}
    assert len(set(widths.values())) == 3, \
        f"{plot_type}: width presets do not give distinct widths: {widths}"
    assert widths["single"] < widths["onehalf"] < widths["double"]


@pytest.mark.parametrize("plot_type", ["neighborhood_enrichment_matrix",
                                       "sankey_plot", "upset_plot"])
def test_a_width_below_the_legibility_floor_is_honoured_and_reported(plot_type):
    """These three need more width than a single column to keep their labels
    clear. The request is obeyed - refusing it silently is what made the control
    look broken - and the crowding is stated."""
    _width, warnings = _width_in(plot_type, "single")
    assert any("narrower" in w for w in warnings), \
        f"{plot_type} quietly used a width below its legibility floor"


@pytest.mark.parametrize("plot_type", ["neighborhood_enrichment_matrix",
                                       "sankey_plot", "upset_plot"])
def test_the_automatic_width_still_respects_the_legibility_floor(plot_type):
    """The floor is right for the size nobody asked for."""
    auto, warnings = _width_in(plot_type, "default")
    assert auto >= 6.0, f"{plot_type}: automatic width {auto} ignores its floor"
    assert not any("narrower" in w for w in warnings)


@pytest.mark.parametrize("plot_type", ["sankey_plot", "upset_plot",
                                       "neighborhood_enrichment_matrix"])
def test_the_widened_examples_are_not_clipped_at_their_declared_width(plot_type):
    """An example pinning a width its own content cannot fit is a bad example.

    Sankey and UpSet both pinned "single" - harmless while the renderer clamped
    it to a legibility floor, and a clipped figure the moment the control started
    working. Both now declare the width they actually need.

    Scoped to these three rather than every plot type: eleven others clip a
    legend in their default output for an unrelated reason, tracked as
    KNOWN_DEFAULT_OVERFLOW in tests/test_typography_system.py. Re-asserting that
    here would just duplicate a known defect as a second failing test.
    """
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry
    import matplotlib.pyplot as plt

    table, aux, spec = examples.load_example(plot_type)
    result = registry.render(spec, table.dataframe,
                             aux={k: v.dataframe for k, v in (aux or {}).items()})
    figure = result.figure
    figure.canvas.draw()
    dpi = figure.dpi
    width_px, height_px = [v * dpi for v in figure.get_size_inches()]
    box = figure.get_tightbbox(figure.canvas.get_renderer())
    over = (max(0.0, -box.x0 * dpi) + max(0.0, box.x1 * dpi - width_px)
            + max(0.0, -box.y0 * dpi) + max(0.0, box.y1 * dpi - height_px))
    plt.close(figure)
    assert over <= 4.0, (
        f"{plot_type}: {over:.0f}px clipped at the width its example asks for")
