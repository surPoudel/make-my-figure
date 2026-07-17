"""Network color acceptance tests (GUI-free) — the canonical spec both frontends
target, using the exact synthetic edge list from the bug report.

    source,target,interaction_type,weight
    A,B,activation,1.0
    B,C,inhibition,0.8
    C,D,binding,0.5
    D,A,activation,0.7
"""

import json

import matplotlib
import matplotlib.colors as mcolors
import pandas as pd
import pytest
from matplotlib.collections import LineCollection

matplotlib.use("Agg")

from make_my_figure_core.plots.registry import figure_to_bytes, make_spec, render

_EDGES = pd.DataFrame({
    "source": ["A", "B", "C", "D"],
    "target": ["B", "C", "D", "A"],
    "interaction_type": ["activation", "inhibition", "binding", "activation"],
    "weight": [1.0, 0.8, 0.5, 0.7]})


def _render(mapping, style=None):
    spec = make_spec("network_graph", "n", "publication", mapping=mapping)
    if style:
        spec["style"] = style
    return spec, render(spec, _EDGES)


def _edge_colors(result):
    lcs = [c for c in result.figure.axes[0].collections if isinstance(c, LineCollection)]
    return [mcolors.to_hex(c) for c in lcs[0].get_colors()]


# canonical mapping the Streamlit + desktop builders both produce
_BY_CATEGORY = {"source": "source", "target": "target", "weight": "weight",
                "interaction_type": "interaction_type", "edge_color_by": "interaction_type",
                "color_by": "none"}


def test_edge_color_by_category_three_colors():
    _spec, r = _render(_BY_CATEGORY)
    assert len({c for c in _edge_colors(r)}) >= 3


def test_legend_contains_all_categories():
    _spec, r = _render(_BY_CATEGORY)
    lg = r.figure.axes[0].get_legend()
    assert lg is not None
    labels = {t.get_text() for t in lg.get_texts()}
    assert {"activation", "inhibition", "binding"} <= labels


def test_plotspec_round_trip_preserves_edge_color_mapping():
    spec = make_spec("network_graph", "n", "publication", mapping=_BY_CATEGORY)
    rt = json.loads(json.dumps(spec))
    assert rt["mapping"]["interaction_type"] == "interaction_type"
    assert rt["mapping"]["edge_color_by"] == "interaction_type"


def test_spec_changes_when_edge_color_mode_changes():
    # A cache keyed on the spec must invalidate when the edge color choice changes.
    s_cat = make_spec("network_graph", "n", "publication", mapping=_BY_CATEGORY)
    s_single = make_spec("network_graph", "n", "publication",
                         mapping={**_BY_CATEGORY, "edge_color_by": "none",
                                  "edge_color": "#777777"})
    assert json.dumps(s_cat, sort_keys=True) != json.dumps(s_single, sort_keys=True)
    # and the rendered colors differ (no stale reuse at render level)
    assert set(_edge_colors(render(s_cat, _EDGES))) != set(_edge_colors(render(s_single, _EDGES)))


def test_single_color_mode_is_one_color():
    _spec, r = _render({**_BY_CATEGORY, "edge_color_by": "none", "edge_color": "#777777"})
    assert set(_edge_colors(r)) == {"#777777"}


@pytest.mark.parametrize("fmt", ["png", "pdf", "svg"])
def test_exports_non_empty(fmt):
    _spec, r = _render(_BY_CATEGORY)
    data = figure_to_bytes(r.figure, fmt, dpi=300)
    assert data and len(data) > 500


def test_no_forbidden_style_in_metadata():
    _spec, r = _render(_BY_CATEGORY)
    blob = json.dumps(r.metadata, default=str).lower()
    for tok in ("nature_like", "science_like", "cell_like", "journal-like"):
        assert tok not in blob


def test_canonical_fields_consumed_by_renderer():
    # Every canonical network field the frontends set must be understood by the core
    # renderer (no field silently unused / no separate renderer path).
    mapping = {**_BY_CATEGORY, "node_color": "#123456", "edge_color": "#abcdef",
               "layout": "circular", "seed": 7, "node_labels": True, "show_legend": True,
               "node_color_map": json.dumps({"x": "#000000"})}
    _spec, r = _render(mapping)
    assert r.figure is not None and not any(
        "unknown" in w.lower() for w in (r.warnings or []))
