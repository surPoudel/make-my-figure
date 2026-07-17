"""Plot-aware style capabilities + network styling.

Covers: capabilities exist for every plot type; unsupported controls are warned
(not silently ignored); the network renderer honors user-selected node/edge colors,
palette, sizes and widths; choices round-trip in the PlotSpec; exports are non-empty.
No GUI, no private data.
"""

import json

import matplotlib
import matplotlib.colors as mcolors
import pandas as pd
import pytest
from matplotlib.collections import LineCollection, PathCollection

matplotlib.use("Agg")

from make_my_figure_core.plots import registry
from make_my_figure_core.plots.registry import figure_to_bytes, make_spec, render
from make_my_figure_core.styles.capabilities import (
    get_style_capabilities,
    validate_style_controls_for_plot,
    warn_ignored_style_controls,
)

_EDGES = pd.DataFrame({"source": ["A", "A", "B", "C", "D", "E"],
                       "target": ["B", "C", "C", "D", "E", "A"],
                       "weight": [1, 2, 3, 1, 2, 1.0]})
_NODES = pd.DataFrame({"node": ["A", "B", "C", "D", "E"],
                       "group": ["g1", "g1", "g2", "g2", "g3"]})


def _net(mapping, style=None, aux=None):
    spec = make_spec("network_graph", "n", "publication", mapping=mapping)
    if style:
        spec["style"] = style
    return render(spec, _EDGES, aux=aux)


def _node_facecolors(result):
    pcs = [c for c in result.figure.axes[0].collections if isinstance(c, PathCollection)]
    return {mcolors.to_hex(c) for c in pcs[0].get_facecolors()}


def _edge_colors(result):
    lcs = [c for c in result.figure.axes[0].collections if isinstance(c, LineCollection)]
    return {mcolors.to_hex(c) for c in lcs[0].get_colors()}


# --- capability registry ----------------------------------------------------
def test_capabilities_exist_for_every_plot_type():
    for pt in registry._RENDERERS:
        caps = get_style_capabilities(pt)
        assert caps.plot_type in (pt, "_default") or caps is not None


def test_network_axis_padding_unsupported():
    caps = get_style_capabilities("network_graph")
    assert caps.supports_axes is False
    assert caps.supports_axis_label_padding is False
    assert caps.supports_marker_size is False
    assert caps.supports_node_colors and caps.supports_edge_colors


def test_unsupported_control_is_warned_not_silent():
    warns = warn_ignored_style_controls("network_graph", {"marker_size": 80})
    assert warns and "marker_size" in warns[0]
    # and it surfaces on the rendered result
    r = _net({"source": "source", "target": "target"}, style={"marker_size": 80})
    assert any("marker_size" in w for w in r.warnings)


def test_common_control_applies_to_ordinary_plot():
    # palette on a barplot is supported -> no capability warning
    assert warn_ignored_style_controls("barplot_with_error_bar", {"palette_name": "grayscale"}) == []
    # marker_size on a scatter is supported -> no warning
    assert warn_ignored_style_controls("scatterplot_with_regression", {"marker_size": 60}) == []


def test_colorbar_label_unsupported_on_barplot():
    checks = dict((k, ok) for k, ok, _ in
                  validate_style_controls_for_plot("barplot_with_error_bar",
                                                   {"colorbar_label": "x"}))
    assert checks["colorbar_label"] is False


# --- network color controls -------------------------------------------------
def test_network_fixed_node_color():
    r = _net({"source": "source", "target": "target", "color_by": "none",
              "node_color": "#123456"})
    assert _node_facecolors(r) == {"#123456"}


def test_network_categorical_group_colors_use_palette():
    # The reported Mac bug: the Publication palette must drive group node colors.
    from make_my_figure_core.styles.engine import NAMED_PALETTES
    r = _net({"source": "source", "target": "target", "color_by": "group"},
             style={"palette_name": "grayscale"}, aux={"nodes": _NODES})
    gray = {c.lower() for c in NAMED_PALETTES["grayscale"]}
    assert {c.lower() for c in _node_facecolors(r)} & gray


def test_network_custom_category_color_map():
    mp = json.dumps({"g1": "#ff0000", "g2": "#00ff00", "g3": "#0000ff"})
    r = _net({"source": "source", "target": "target", "color_by": "group",
              "node_color_map": mp}, aux={"nodes": _NODES})
    assert {"#ff0000", "#00ff00", "#0000ff"} <= _node_facecolors(r)


_ITYPE_EDGES = pd.DataFrame({
    "source": ["A", "A", "B", "C", "D", "E", "F", "G"],
    "target": ["B", "C", "C", "D", "E", "A", "G", "A"],
    "weight": [1, 2, 3, 1, 2, 1, 2, 1.0],
    "itype": ["activation", "inhibition", "activation", "binding", "inhibition",
              "binding", "activation", "binding"]})


def _itype_edge_colors(mapping, style=None):
    spec = make_spec("network_graph", "n", "publication", mapping=mapping)
    if style:
        spec["style"] = style
    r = render(spec, _ITYPE_EDGES)
    lcs = [c for c in r.figure.axes[0].collections if isinstance(c, LineCollection)]
    return [mcolors.to_hex(c) for c in lcs[0].get_colors()], r


def test_network_edge_color_by_interaction_type_auto():
    # The reported WSL bug: coloring by interaction_type must produce multiple hues,
    # not a single color. Auto-detected when the column is mapped.
    cols, r = _itype_edge_colors({"source": "source", "target": "target",
                                  "interaction_type": "itype", "color_by": "none"})
    assert len(set(cols)) == 3
    lg = r.figure.axes[0].get_legend()
    assert lg is not None
    assert {t.get_text() for t in lg.get_texts()} == {"activation", "inhibition", "binding"}


def test_network_interaction_type_not_single_color():
    cols, _ = _itype_edge_colors({"source": "source", "target": "target",
                                  "interaction_type": "itype", "color_by": "none"})
    assert len(set(cols)) > 1, "edges collapsed to a single color despite categories"


def test_network_edge_color_by_explicit_none_is_single():
    cols, _ = _itype_edge_colors({"source": "source", "target": "target",
                                  "interaction_type": "itype", "edge_color_by": "none",
                                  "edge_color": "#777777", "color_by": "none"})
    assert set(cols) == {"#777777"}


def test_network_edge_categories_honor_palette():
    from make_my_figure_core.styles.engine import NAMED_PALETTES
    cols, _ = _itype_edge_colors({"source": "source", "target": "target",
                                  "interaction_type": "itype", "color_by": "none"},
                                 style={"palette_name": "grayscale"})
    gray = {c.lower() for c in NAMED_PALETTES["grayscale"]}
    assert {c.lower() for c in cols} & gray


def test_network_fixed_edge_color():
    r = _net({"source": "source", "target": "target", "edge_color": "#abcdef",
              "color_by": "none"})
    assert "#abcdef" in _edge_colors(r)


def test_network_fixed_edge_width():
    r = _net({"source": "source", "target": "target", "edge_width_by": "fixed",
              "edge_width": 4.0, "color_by": "none"})
    lcs = [c for c in r.figure.axes[0].collections if isinstance(c, LineCollection)]
    widths = set(lcs[0].get_linewidths())
    assert widths == {4.0}


def test_network_fixed_node_size():
    r = _net({"source": "source", "target": "target", "size_by": "fixed",
              "node_size": 500, "color_by": "none"})
    pcs = [c for c in r.figure.axes[0].collections if isinstance(c, PathCollection)]
    assert set(pcs[0].get_sizes()) == {500.0}


def test_network_colors_round_trip_in_spec():
    mp = json.dumps({"g1": "#ff0000"})
    spec = make_spec("network_graph", "n", "publication",
                     mapping={"source": "source", "target": "target",
                              "color_by": "group", "node_color_map": mp,
                              "edge_color": "#abcdef"})
    round_tripped = json.loads(json.dumps(spec))
    assert round_tripped["mapping"]["node_color_map"] == mp
    assert round_tripped["mapping"]["edge_color"] == "#abcdef"


def test_network_no_stale_colors_between_renders():
    # Two renders with different fixed colors must differ (no cached reuse).
    r1 = _net({"source": "source", "target": "target", "color_by": "none",
               "node_color": "#111111"})
    r2 = _net({"source": "source", "target": "target", "color_by": "none",
               "node_color": "#eeeeee"})
    assert _node_facecolors(r1) != _node_facecolors(r2)


def test_network_show_legend_toggle():
    r_on = _net({"source": "source", "target": "target", "color_by": "group",
                 "show_legend": True}, aux={"nodes": _NODES})
    r_off = _net({"source": "source", "target": "target", "color_by": "group",
                  "show_legend": False}, aux={"nodes": _NODES})
    assert r_on.figure.axes[0].get_legend() is not None
    assert r_off.figure.axes[0].get_legend() is None


# --- exports ----------------------------------------------------------------
@pytest.mark.parametrize("fmt", ["png", "pdf", "svg"])
def test_network_export_non_empty(fmt):
    r = _net({"source": "source", "target": "target", "color_by": "none",
              "node_color": "#123456", "edge_color": "#abcdef"})
    data = figure_to_bytes(r.figure, fmt, dpi=300)
    assert data and len(data) > 500


def test_figure_builder_preserves_network_colors():
    from make_my_figure_core.panels.builder import build_figure
    from make_my_figure_core.panels.models import FigureLayout, MultiPanelFigure, Panel
    spec = make_spec("network_graph", "n", "publication",
                     mapping={"source": "source", "target": "target",
                              "color_by": "none", "node_color": "#123456"})
    mpf = MultiPanelFigure(name="F", layout=FigureLayout(ncols=1))
    mpf.add_panel(Panel(plot_spec=spec, table=_EDGES, source_name="net"))
    fig = build_figure(mpf)
    # Composed figure exists and the panel carries the colored spec unchanged.
    assert fig is not None
    assert mpf.panels[0].plot_spec["mapping"]["node_color"] == "#123456"


def test_network_svg_preserves_custom_color():
    r = _net({"source": "source", "target": "target", "color_by": "none",
              "node_color": "#123456"})
    svg = figure_to_bytes(r.figure, "svg").decode("utf-8", errors="ignore").lower()
    # SVG may encode as #123456 or rgb(...); the node fill color must appear.
    assert "#123456" in svg or "18,52,86" in svg or "rgb(18" in svg
