"""The global Publication-style controls, on the six spatial plot types.

A control the panel offers and the renderer ignores is the worst kind of defect:
the author changes it, nothing moves, and they cannot tell whether the setting is
broken or their expectation is. ``quality_audit/option_efficacy.py`` found four
such controls on the spatial maps. Two of them were only dormant - a map hides
its coordinate axes by default, so there are no tick labels to size - and those
are pinned here *with the axes shown*, which is the precondition for the control
to mean anything. The other two were genuinely dead and are guarded below.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

from make_my_figure_core import examples
from make_my_figure_core.plots._spatial_shared import DEFAULT_STYLE_MARKER_SIZE
from make_my_figure_core.plots.registry import render

# Maps that draw point marks sized by the style, and the size their bundled
# example pins in spatial.marker_size.
SIZED_MAPS = {
    "spatial_categorical_map": 7.0,
    "spatial_feature_map": 8.0,
    "spatial_transcript_map": 1.4,
}

# Every map with coordinate axes it can be asked to show.
COORDINATE_MAPS = [
    "spatial_categorical_map", "spatial_composition_map", "spatial_feature_map",
    "spatial_roi_map", "spatial_transcript_map",
]


def _figure(plot_type, style=None, spatial=None):
    table, aux, spec = examples.load_example(plot_type)
    spec = dict(spec)
    if style:
        spec["style"] = {**(spec.get("style") or {}), **style}
    if spatial:
        spec["spatial"] = {**(spec.get("spatial") or {}), **spatial}
    result = render(spec, table.dataframe,
                    aux={k: v.dataframe for k, v in (aux or {}).items()})
    return result.figure


def _mark_sizes(fig):
    sizes = set()
    for ax in fig.axes:
        for coll in ax.collections:
            if hasattr(coll, "get_sizes"):
                sizes.update(round(float(s), 6) for s in coll.get_sizes())
    return sizes


def _data_axes(fig):
    """The first axes that is not a colourbar."""
    for ax in fig.axes:
        if getattr(ax, "_colorbar", None) is None:
            return ax
    return fig.axes[0]


# --- point size: scaled by the global control, not replaced by it -----------

@pytest.mark.parametrize("plot_type,pinned", sorted(SIZED_MAPS.items()))
def test_a_pinned_point_size_survives_the_default_style(plot_type, pinned):
    """The size the spec asked for is what gets drawn - that is the whole point of
    pinning it, and a global control that quietly replaced it would be a worse bug
    than the one being fixed."""
    fig = _figure(plot_type)
    try:
        assert _mark_sizes(fig) == {pinned}
    finally:
        plt.close(fig)


@pytest.mark.parametrize("plot_type,pinned", sorted(SIZED_MAPS.items()))
@pytest.mark.parametrize("global_size", [120.0, 4.0])
def test_the_global_point_size_scales_a_pinned_spatial_marker_size(
        plot_type, pinned, global_size):
    fig = _figure(plot_type, {"marker_size": global_size})
    try:
        expected = round(pinned * global_size / DEFAULT_STYLE_MARKER_SIZE, 6)
        assert _mark_sizes(fig) == {expected}
    finally:
        plt.close(fig)


@pytest.mark.parametrize("plot_type", sorted(SIZED_MAPS))
def test_a_point_size_of_zero_means_auto(plot_type):
    """``0`` is what the GUI's point-size spinner sends when the user has chosen
    nothing. Taken literally it would draw marks of zero area - an empty map."""
    fig = _figure(plot_type, spatial={"marker_size": 0})
    try:
        assert _mark_sizes(fig) and all(s > 0 for s in _mark_sizes(fig))
    finally:
        plt.close(fig)


# --- typography: dormant with the axes hidden, live once they are shown -----

@pytest.mark.parametrize("plot_type", COORDINATE_MAPS)
def test_hidden_axes_carry_no_labels_or_ticks(plot_type):
    """The default. Nothing to size here, which is why the typography controls
    look dead on these maps - correctly so."""
    fig = _figure(plot_type)
    try:
        ax = _data_axes(fig)
        assert ax.get_xlabel() == "" and ax.get_ylabel() == ""
        assert len(ax.get_xticks()) == 0 and len(ax.get_yticks()) == 0
    finally:
        plt.close(fig)


@pytest.mark.parametrize("plot_type", COORDINATE_MAPS)
def test_shown_axes_are_labelled_with_the_coordinate_column_and_unit(plot_type):
    """Visible axes have to say what they measure; the examples are in pixels."""
    fig = _figure(plot_type, spatial={"show_axes": True})
    try:
        ax = _data_axes(fig)
        assert ax.get_xlabel() == "x (px)"
        assert ax.get_ylabel() == "y (px)"
    finally:
        plt.close(fig)


@pytest.mark.parametrize("plot_type", COORDINATE_MAPS)
@pytest.mark.parametrize("points", [6.0, 22.0])
def test_the_axis_label_size_control_reaches_a_shown_spatial_axis(plot_type, points):
    fig = _figure(plot_type, {"axis_font_pt": points}, {"show_axes": True})
    try:
        ax = _data_axes(fig)
        assert ax.xaxis.label.get_fontsize() == pytest.approx(points)
        assert ax.yaxis.label.get_fontsize() == pytest.approx(points)
    finally:
        plt.close(fig)


@pytest.mark.parametrize("plot_type", COORDINATE_MAPS)
@pytest.mark.parametrize("points", [5.0, 20.0])
def test_the_tick_label_size_control_reaches_shown_spatial_ticks(plot_type, points):
    fig = _figure(plot_type, {"tick_label_pt": points}, {"show_axes": True})
    try:
        ax = _data_axes(fig)
        labels = [t for t in ax.get_xticklabels() + ax.get_yticklabels()]
        assert labels
        assert all(t.get_fontsize() == pytest.approx(points) for t in labels)
    finally:
        plt.close(fig)


# --- grid --------------------------------------------------------------------

@pytest.mark.parametrize("plot_type", COORDINATE_MAPS)
@pytest.mark.parametrize("grid", [True, False])
def test_the_grid_control_reaches_a_spatial_map_once_axes_are_shown(plot_type, grid):
    fig = _figure(plot_type, {"grid": grid}, {"show_axes": True})
    try:
        ax = _data_axes(fig)
        drawn = [ln.get_visible() for ln in ax.get_xgridlines() + ax.get_ygridlines()]
        assert drawn and all(v is grid for v in drawn)
    finally:
        plt.close(fig)


@pytest.mark.parametrize("plot_type", COORDINATE_MAPS)
def test_a_spatial_grid_setting_overrides_the_style(plot_type):
    """The per-plot setting is the more specific intent, so it wins."""
    fig = _figure(plot_type, {"grid": True}, {"show_axes": True, "grid": False})
    try:
        ax = _data_axes(fig)
        assert not any(ln.get_visible()
                       for ln in ax.get_xgridlines() + ax.get_ygridlines())
    finally:
        plt.close(fig)


@pytest.mark.parametrize("grid", [True, False])
def test_the_grid_control_reaches_the_neighbourhood_matrix(grid):
    """The Grid control for this plot is its own option, not the global checkbox.

    The faint guide lines are part of how the matrix is read - they carry the eye
    from a dot back to its row and column across 28 columns - so they are on by
    default even though the publication profile turns grids off globally. There
    is no way to tell "the user unticked Grid" from "this profile has grids off",
    so the per-plot option is the control, in the same way the clustered heatmap
    owns its own cell-border settings rather than deferring to the global grid.
    """
    fig = _figure("neighborhood_enrichment_matrix", spatial={"grid": grid})
    try:
        ax = _data_axes(fig)
        drawn = [ln.get_visible() for ln in ax.get_xgridlines() + ax.get_ygridlines()]
        assert drawn and all(v is grid for v in drawn)
    finally:
        plt.close(fig)


def test_the_matrix_keeps_its_guide_lines_under_a_gridless_profile():
    """Deferring to the global setting would silently strip the guide lines from
    every figure of this type, because the publication profile has grid=False."""
    fig = _figure("neighborhood_enrichment_matrix", style={"grid": False})
    try:
        ax = _data_axes(fig)
        assert any(ln.get_visible()
                   for ln in ax.get_xgridlines() + ax.get_ygridlines()), \
            "the dot matrix lost the guide lines it has always drawn"
    finally:
        plt.close(fig)


def test_a_spec_that_pins_the_matrix_grid_still_wins():
    fig = _figure("neighborhood_enrichment_matrix", {"grid": False},
                  spatial={"grid": True})
    try:
        ax = _data_axes(fig)
        assert any(ln.get_visible()
                   for ln in ax.get_xgridlines() + ax.get_ygridlines())
    finally:
        plt.close(fig)
