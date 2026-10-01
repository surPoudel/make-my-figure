"""One typography system, shared by every renderer.

Two things have to stay true for a figure set to look deliberate rather than
assembled: every renderer must take its text sizes from the style rather than
from a literal of its own, and the hierarchy between those sizes must survive a
change of canvas. These tests pin both, plus the bounds that keep the scaling
from running away in either direction.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from make_my_figure_core.styles.engine import load_profile
from make_my_figure_core.styles.typography import (
    ABSOLUTE_MIN_PT,
    GROW_ABOVE,
    MAX_SCALE,
    MIN_SCALE,
    SHRINK_BELOW,
    TYPE_ATTRS,
    describe,
    scaled_for_canvas,
    typography_scale,
)

PLOTS_DIR = Path(__file__).resolve().parents[1] / "make_my_figure_core" / "plots"

# The hierarchy the publication style defines, as ratios to the axis-label size.
# Recorded here so a change to the visual identity has to be deliberate.
CANONICAL_RATIOS = {
    "title_font_pt": 1.083,
    "axis_font_pt": 1.0,
    "legend_title_pt": 0.917,
    "tick_label_pt": 0.833,
    "legend_pt": 0.833,
    "annotation_pt": 0.792,
}


@pytest.fixture(scope="module")
def style():
    return load_profile("publication")


# --------------------------------------------------------------------------
# The hierarchy itself
# --------------------------------------------------------------------------

def test_the_type_hierarchy_is_the_documented_one(style):
    actual = {k: v["ratio_to_axis_label"] for k, v in describe(style).items()}
    assert actual == pytest.approx(CANONICAL_RATIOS, abs=0.01)


def test_the_hierarchy_is_strictly_ordered(style):
    """Title largest, annotation smallest. A flat hierarchy reads as an accident."""
    assert style.title_font_pt > style.axis_font_pt > style.tick_label_pt
    assert style.legend_title_pt > style.legend_pt
    assert style.annotation_pt <= style.tick_label_pt


def test_every_style_profile_keeps_a_readable_hierarchy():
    """A style is free to choose its sizes, not to invert or flatten the hierarchy."""
    from make_my_figure_core.styles.engine import list_profiles

    for name in list_profiles():
        s = load_profile(name)
        assert s.title_font_pt >= s.axis_font_pt, f"{name}: title smaller than axis label"
        assert s.axis_font_pt >= s.tick_label_pt, f"{name}: axis label smaller than ticks"
        for attr in TYPE_ATTRS:
            assert getattr(s, attr) >= ABSOLUTE_MIN_PT, f"{name}.{attr} is unreadable"


# --------------------------------------------------------------------------
# No renderer may define its own type sizes
# --------------------------------------------------------------------------

def test_no_renderer_hardcodes_a_font_size():
    """A numeric fontsize in a renderer is a figure that ignores the style."""
    offenders = []
    pattern = re.compile(r"\b(?:fontsize|labelsize|size)\s*=\s*\d+(?:\.\d+)?\b")
    for path in sorted(PLOTS_DIR.glob("*.py")):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if pattern.search(line):
                offenders.append(f"{path.name}:{n}: {line.strip()}")
    assert not offenders, "renderers must take text sizes from the style:\n" + "\n".join(offenders)


def test_no_renderer_hardcodes_a_text_colour():
    """Text colour is part of the style, including for annotations."""
    offenders = []
    pattern = re.compile(r"(?:color|c)\s*=\s*[\"'](?:black|k|#000|#000000)[\"']")
    for path in sorted(PLOTS_DIR.glob("*.py")):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if pattern.search(line) and (".text(" in line or ".annotate(" in line
                                         or "text_color" in line):
                offenders.append(f"{path.name}:{n}: {stripped}")
    assert not offenders, "text colour must come from the style:\n" + "\n".join(offenders)


# --------------------------------------------------------------------------
# Scaling with the canvas
# --------------------------------------------------------------------------

def test_a_figure_at_the_reference_size_is_not_restyled(style):
    ref_w, ref_h = style.figure_size_inches()
    scaled, factor = scaled_for_canvas(style, ref_w, ref_h)
    assert factor == 1.0
    assert scaled is style, "the common case must not even copy the style"


def test_a_normal_resize_does_not_restyle_the_figure(style):
    """Between the thresholds, type is left exactly as the style set it."""
    ref_w, ref_h = style.figure_size_inches()
    for area_fraction in (SHRINK_BELOW, 0.8, 1.0, 1.3, GROW_ABOVE):
        k = area_fraction ** 0.5
        _, factor = scaled_for_canvas(style, ref_w * k, ref_h * k)
        assert factor == 1.0, f"area x{area_fraction} should not rescale type"


def test_a_small_panel_shrinks_type_and_a_large_one_grows_it(style):
    ref_w, ref_h = style.figure_size_inches()
    _, small = scaled_for_canvas(style, 2.0, 1.0)
    _, large = scaled_for_canvas(style, ref_w * 3, ref_h * 3)
    assert small < 1.0 < large


@pytest.mark.parametrize("size", [(2.0, 1.0), (4.0, 2.0), (4.0, 4.0), (1.5, 1.5),
                                  (12.0, 9.0), (20.0, 16.0)])
def test_scaling_preserves_the_hierarchy_exactly(style, size):
    """The ratios are the identity; they must not drift as the canvas changes."""
    scaled, _ = scaled_for_canvas(style, *size)
    ratios = {k: v["ratio_to_axis_label"] for k, v in describe(scaled).items()}
    assert ratios == pytest.approx(CANONICAL_RATIOS, abs=0.02)


@pytest.mark.parametrize("size", [(0.4, 0.3), (2.0, 1.0), (60.0, 40.0), (0.01, 0.01)])
def test_type_never_becomes_unreadable_or_runs_away(style, size):
    scaled, factor = scaled_for_canvas(style, *size)
    assert MIN_SCALE <= factor <= MAX_SCALE
    for attr in TYPE_ATTRS:
        assert getattr(scaled, attr) >= ABSOLUTE_MIN_PT, f"{attr} unreadable at {size}"


def test_scaling_is_continuous_across_the_threshold(style):
    """No visible jump the moment a figure crosses out of the dead band."""
    ref_w, ref_h = style.figure_size_inches()
    k = SHRINK_BELOW ** 0.5
    inside = typography_scale(ref_w * k * 1.001, ref_h * k * 1.001, (ref_w, ref_h))
    outside = typography_scale(ref_w * k * 0.999, ref_h * k * 0.999, (ref_w, ref_h))
    assert inside == 1.0
    assert abs(outside - 1.0) < 0.01, f"discontinuity at the shrink threshold: {outside}"


def test_a_degenerate_canvas_is_ignored_rather_than_crashing(style):
    for bad in ((0, 5), (5, 0), (-3, 2)):
        _, factor = scaled_for_canvas(style, *bad)
        assert factor == 1.0


def test_scaling_does_not_mutate_the_profile_it_was_given(style):
    before = {a: getattr(style, a) for a in TYPE_ATTRS}
    scaled_for_canvas(style, 2.0, 1.0)
    assert {a: getattr(style, a) for a in TYPE_ATTRS} == before


# --------------------------------------------------------------------------
# Every renderer inherits it
# --------------------------------------------------------------------------

def _rendered_text_sizes(plot_type, layout):
    """The font sizes actually drawn, in points, for one plot type."""
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry

    table, aux, spec = examples.load_example(plot_type)
    spec = {**spec, "layout": {**(spec.get("layout") or {}), **layout}}
    result = registry.render(
        spec, table.dataframe,
        aux={k: v.dataframe for k, v in (aux or {}).items()})
    figure = result.figure
    sizes = []
    for obj in figure.findobj(match=lambda o: hasattr(o, "get_fontsize")
                              and hasattr(o, "get_text")):
        try:
            if obj.get_text().strip():
                sizes.append(round(float(obj.get_fontsize()), 2))
        except Exception:  # noqa: BLE001
            continue
    import matplotlib.pyplot as plt
    plt.close(figure)
    return sizes


def _example_plot_types():
    from make_my_figure_core import examples

    return sorted(examples.plot_types_with_examples())


@pytest.mark.parametrize("plot_type", _example_plot_types())
def test_every_plot_type_inherits_the_shared_typography(plot_type):
    """A pinned small canvas must shrink the type of *every* plot type.

    This is what makes the system shared rather than a set of per-renderer
    patches: the scaling is applied once, centrally, and a renderer that
    reached for its own font sizes would show up here as text that did not move.
    """
    default = _rendered_text_sizes(plot_type, {})
    small = _rendered_text_sizes(plot_type, {"width_mm": 50.8, "height_mm": 25.4})
    if not default:
        pytest.skip(f"{plot_type} draws no text")
    assert max(small) < max(default), (
        f"{plot_type}: largest text stayed at {max(small)} pt on a 2x1 in canvas, "
        f"so this renderer is not taking its sizes from the shared style")


# Plot types that still draw outside a pinned 4 x 2 in canvas, with the cause.
# These are real defects, not accepted behaviour: an outside legend or a colourbar
# label is placed as though the figure could be widened, which it cannot be once the
# user has pinned the size. Fixing them means changing legend and colourbar
# placement across those renderers, which belongs with the layout work rather than
# here - see quality_audit/typography.md. Recorded so that the list cannot grow
# unnoticed, and so that fixing one shows up as a test to update.
KNOWN_CANVAS_OVERFLOW_AT_4X2 = {
    "dose_response_curve": "outside legend",
    "grouped_barplot_with_error_bar": "outside legend",
    "lollipop_mutation_plot": "outside legend",
    "ma_plot": "colourbar label",
    "neighborhood_enrichment_matrix": "colourbar label",
    "network_graph": "outside legend",
    "sankey_plot": "node label",
    "scatterplot_with_regression": "outside legend",
    "spatial_feature_map": "colourbar label",
    "spider_plot": "outside legend",
    "swimmer_plot": "outside legend",
    "volcano_plot": "outside legend",
}


def _canvas_overflow_px(plot_type, width_mm=101.6, height_mm=50.8, axis="x"):
    """Pixels of drawn content hanging off the edge of the canvas.

    Uses matplotlib's own tight bounding box rather than walking every ``Text``:
    an axis keeps label objects for ticks outside the view limits, parked far off
    the canvas and never drawn, and counting those reports overflow on figures
    that are in fact clean.
    """
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry
    import matplotlib.pyplot as plt

    table, aux, spec = examples.load_example(plot_type)
    spec = {**spec, "layout": {**(spec.get("layout") or {}),
                               "width_mm": width_mm, "height_mm": height_mm}}
    result = registry.render(
        spec, table.dataframe,
        aux={k: v.dataframe for k, v in (aux or {}).items()})
    figure = result.figure
    figure.canvas.draw()
    dpi = figure.dpi
    width_px = figure.get_size_inches()[0] * dpi
    height_px = figure.get_size_inches()[1] * dpi
    box = figure.get_tightbbox(figure.canvas.get_renderer())
    if axis == "x":
        over = max(0.0, -box.x0 * dpi) + max(0.0, box.x1 * dpi - width_px)
    else:
        over = max(0.0, -box.y0 * dpi) + max(0.0, box.y1 * dpi - height_px)
    plt.close(figure)
    return over


# The same defect on the vertical axis, and the larger of the two: at a pinned
# 4 x 2 in these plot types push their x-axis label (or a legend placed under the
# axes) off the bottom of the canvas. ``tight_layout`` gives up when the canvas is
# too small for the decorations and the content is simply clipped, which costs the
# axis label - the one piece of text a figure cannot do without. Same reasoning as
# above: a layout fix, tripwired here.
KNOWN_VERTICAL_OVERFLOW_AT_4X2 = {
    "chord_diagram", "dose_response_curve", "embedding_scatter",
    "grouped_barplot_with_error_bar", "lollipop_mutation_plot", "ma_plot",
    "neighborhood_enrichment_matrix", "scatterplot_with_regression",
    "spatial_categorical_map", "spatial_composition_map", "spider_plot",
    "swimmer_plot", "upset_plot", "volcano_plot",
}


@pytest.mark.parametrize("plot_type", [p for p in _example_plot_types()
                                       if p not in KNOWN_CANVAS_OVERFLOW_AT_4X2])
def test_a_pinned_panel_size_keeps_text_inside_the_canvas(plot_type):
    """4 x 2 in is a normal multi-panel size; drawing past the edge there is a bug."""
    over = _canvas_overflow_px(plot_type)
    assert over <= 1.0, (
        f"{plot_type}: {over:.0f}px of content hangs off a pinned 4 x 2 in canvas")


def test_the_list_of_plots_that_overflow_a_pinned_canvas_has_not_grown():
    """A tripwire on a known defect, so it cannot spread or be quietly forgotten.

    Failing here is the point: if a plot type is fixed, remove it from the list; if
    a new one starts overflowing, it has to be dealt with rather than discovered in
    someone's manuscript.
    """
    still_overflowing = {p for p in KNOWN_CANVAS_OVERFLOW_AT_4X2
                         if _canvas_overflow_px(p) > 1.0}
    fixed = set(KNOWN_CANVAS_OVERFLOW_AT_4X2) - still_overflowing
    assert not fixed, (
        f"these no longer overflow and should be removed from "
        f"KNOWN_CANVAS_OVERFLOW_AT_4X2: {sorted(fixed)}")


# --------------------------------------------------------------------------
# Titles longer than the figure is wide
# --------------------------------------------------------------------------

LONG_TITLE = ("Cell-type enrichment across spatial neighbourhoods in colorectal "
              "carcinoma sections")


def _figure_with_title(title, width_in=4.0, height_in=2.0):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(width_in, height_in))
    ax.set_title(title)
    fig.canvas.draw()
    return fig, ax


def test_a_title_that_fits_is_left_exactly_as_it_was():
    from make_my_figure_core.styles.typography import wrap_overlong_titles
    import matplotlib.pyplot as plt

    fig, ax = _figure_with_title("Tumour", width_in=6.0)
    notes = wrap_overlong_titles(fig)
    assert notes == []
    assert ax.get_title() == "Tumour"
    plt.close(fig)


def test_an_overlong_title_is_wrapped_until_it_fits():
    from make_my_figure_core.styles.typography import (
        TITLE_OVERFLOW_TOLERANCE_PX, _horizontal_overflow, wrap_overlong_titles)
    import matplotlib.pyplot as plt

    fig, ax = _figure_with_title(LONG_TITLE)
    assert _horizontal_overflow(ax.title, fig) > TITLE_OVERFLOW_TOLERANCE_PX, \
        "test is meaningless unless the title starts out too wide"
    notes = wrap_overlong_titles(fig)
    assert notes, "an overflowing title must be reported, not silently left"
    assert "\n" in ax.get_title()
    assert _horizontal_overflow(ax.title, fig) <= TITLE_OVERFLOW_TOLERANCE_PX
    plt.close(fig)


def test_wrapping_keeps_every_word_of_the_title():
    """A title may be re-laid-out; it may never lose content."""
    from make_my_figure_core.styles.typography import wrap_overlong_titles
    import matplotlib.pyplot as plt

    fig, ax = _figure_with_title(LONG_TITLE)
    wrap_overlong_titles(fig)
    assert ax.get_title().split() == LONG_TITLE.split()
    plt.close(fig)


def test_a_title_the_user_already_broke_across_lines_is_not_touched():
    from make_my_figure_core.styles.typography import wrap_overlong_titles
    import matplotlib.pyplot as plt

    deliberate = "Cell-type enrichment\nacross neighbourhoods"
    fig, ax = _figure_with_title(deliberate, width_in=2.0)
    assert wrap_overlong_titles(fig) == []
    assert ax.get_title() == deliberate
    plt.close(fig)


def test_wrapping_is_bounded_rather_than_stacking_lines_forever():
    from make_my_figure_core.styles.typography import (
        MAX_TITLE_LINES, wrap_overlong_titles)
    import matplotlib.pyplot as plt

    fig, ax = _figure_with_title(LONG_TITLE * 3, width_in=1.5)
    wrap_overlong_titles(fig)
    assert ax.get_title().count("\n") + 1 <= MAX_TITLE_LINES
    plt.close(fig)


def test_an_empty_title_is_not_reported_as_overflowing():
    from make_my_figure_core.styles.typography import wrap_overlong_titles
    import matplotlib.pyplot as plt

    fig, _ = _figure_with_title("   ", width_in=1.0)
    assert wrap_overlong_titles(fig) == []
    plt.close(fig)


def test_a_title_that_cannot_fit_at_all_says_so_rather_than_pretending():
    """Wrapping has a limit; past it the user needs to be told, not placated."""
    from make_my_figure_core.styles.typography import wrap_overlong_titles
    import matplotlib.pyplot as plt

    fig, _ = _figure_with_title(LONG_TITLE * 3, width_in=1.5)
    notes = wrap_overlong_titles(fig)
    assert notes and "still does not fit" in notes[0], notes
    plt.close(fig)


def test_wrapping_does_not_push_the_title_off_the_top_of_the_canvas():
    """Fixing horizontal overflow must not simply move it to the vertical axis.

    An axes title is anchored at its bottom edge, so extra lines grow upward and
    straight off the figure unless room is made for them.
    """
    from make_my_figure_core.styles.typography import wrap_overlong_titles
    import matplotlib.pyplot as plt

    fig, ax = _figure_with_title(LONG_TITLE)
    wrap_overlong_titles(fig)
    fig.canvas.draw()
    height_px = fig.get_size_inches()[1] * fig.dpi
    top = ax.title.get_window_extent(fig.canvas.get_renderer()).y1
    assert top <= height_px + 1, (
        f"wrapped title reaches {top:.0f}px on a {height_px:.0f}px canvas")
    plt.close(fig)


def test_making_room_never_squeezes_the_axes_to_nothing():
    """A plot reduced to a sliver under a four-line title is not an improvement."""
    from make_my_figure_core.styles.typography import MIN_AXES_TOP, wrap_overlong_titles
    import matplotlib.pyplot as plt

    fig, _ = _figure_with_title(LONG_TITLE * 3, width_in=1.5)
    wrap_overlong_titles(fig)
    assert fig.subplotpars.top >= MIN_AXES_TOP - 1e-6
    plt.close(fig)


@pytest.mark.parametrize("plot_type", [p for p in _example_plot_types()
                                       if p not in KNOWN_VERTICAL_OVERFLOW_AT_4X2])
def test_a_pinned_panel_size_keeps_the_axis_label_on_the_canvas(plot_type):
    over = _canvas_overflow_px(plot_type, axis="y")
    assert over <= 1.0, (
        f"{plot_type}: {over:.0f}px of content, most likely the axis label, falls "
        f"off a pinned 4 x 2 in canvas")


def test_the_list_of_plots_that_overflow_vertically_has_not_grown():
    still = {p for p in KNOWN_VERTICAL_OVERFLOW_AT_4X2
             if _canvas_overflow_px(p, axis="y") > 1.0}
    fixed = KNOWN_VERTICAL_OVERFLOW_AT_4X2 - still
    assert not fixed, (
        f"these no longer overflow and should be removed from "
        f"KNOWN_VERTICAL_OVERFLOW_AT_4X2: {sorted(fixed)}")


def test_no_plot_type_pushes_a_title_off_the_top_of_a_pinned_canvas():
    """The title fitting above must hold for every plot type, not just the two
    that were found by hand."""
    import matplotlib.pyplot as plt
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry

    offenders = []
    for plot_type in _example_plot_types():
        table, aux, spec = examples.load_example(plot_type)
        spec = {**spec, "layout": {**(spec.get("layout") or {}),
                                   "width_mm": 101.6, "height_mm": 50.8}}
        result = registry.render(
            spec, table.dataframe,
            aux={k: v.dataframe for k, v in (aux or {}).items()})
        figure = result.figure
        figure.canvas.draw()
        dpi = figure.dpi
        height_px = figure.get_size_inches()[1] * dpi
        above = figure.get_tightbbox(figure.canvas.get_renderer()).y1 * dpi - height_px
        if above > 1.0:
            offenders.append(f"{plot_type} (+{above:.0f}px)")
        plt.close(figure)
    assert not offenders, "content pushed off the top of the canvas: " + ", ".join(offenders)


# --------------------------------------------------------------------------
# The same defect without anybody asking for a custom size
# --------------------------------------------------------------------------

# Plot types that draw outside the canvas at the style's own default size, with no
# figure size set by the user at all. Worse than the pinned-canvas lists above
# because it affects every figure of these types out of the box, and the cause is
# the same: an outside legend placed as though the canvas could be widened.
# Measured as pixels of overhang at default size; see quality_audit/typography.md.
KNOWN_DEFAULT_OVERFLOW = {
    "dose_response_curve", "embedding_scatter", "grouped_barplot_with_error_bar",
    "lollipop_mutation_plot", "ma_plot", "scatterplot_with_regression",
    "spatial_composition_map", "spatial_feature_map", "spider_plot",
    "swimmer_plot", "volcano_plot",
}


def _default_overflow_px(plot_type):
    """Overhang past any canvas edge at the style's own default figure size."""
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry
    import matplotlib.pyplot as plt

    table, aux, spec = examples.load_example(plot_type)
    result = registry.render(
        spec, table.dataframe,
        aux={k: v.dataframe for k, v in (aux or {}).items()})
    figure = result.figure
    figure.canvas.draw()
    dpi = figure.dpi
    width_px, height_px = [v * dpi for v in figure.get_size_inches()]
    box = figure.get_tightbbox(figure.canvas.get_renderer())
    over = (max(0.0, -box.x0 * dpi) + max(0.0, box.x1 * dpi - width_px)
            + max(0.0, -box.y0 * dpi) + max(0.0, box.y1 * dpi - height_px))
    plt.close(figure)
    return over


@pytest.mark.parametrize("plot_type", [p for p in _example_plot_types()
                                       if p not in KNOWN_DEFAULT_OVERFLOW])
def test_a_default_sized_figure_draws_entirely_on_its_canvas(plot_type):
    """Nothing should be clipped when the user has not asked for anything unusual."""
    over = _default_overflow_px(plot_type)
    assert over <= 4.0, (
        f"{plot_type}: {over:.0f}px of content is clipped at the default figure size")


def test_the_list_of_plots_clipped_at_default_size_has_not_grown():
    still = {p for p in KNOWN_DEFAULT_OVERFLOW if _default_overflow_px(p) > 4.0}
    fixed = KNOWN_DEFAULT_OVERFLOW - still
    assert not fixed, (
        f"these no longer clip at default size and should be removed from "
        f"KNOWN_DEFAULT_OVERFLOW: {sorted(fixed)}")
