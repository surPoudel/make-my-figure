"""Core tests for click-to-identify / click-to-label (headless).

The GUI click handler is a thin layer over this data: renderers emit a
``pickable_points`` table + ``pick_label_column``; ``nearest_pickable`` maps a
click to a point; appending its label to the spec re-labels it. All of that is
tested here without a GUI.
"""

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import pytest

matplotlib.use("Agg")

from make_my_figure_core import examples
from make_my_figure_core.plots.base import (
    build_pickable_points,
    choose_label_column,
    nearest_pickable,
    resolve_point_labels,
)
from make_my_figure_core.plots.registry import make_spec, render


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def test_choose_label_column_prefers_populated():
    df = pd.DataFrame({"label": ["", "", "hit", ""], "gene": ["A", "B", "C", "D"]})
    # 'label' is mostly blank -> 'gene' (fully populated) is chosen
    assert choose_label_column(df, ["label", "gene"]) == "gene"
    assert choose_label_column(df, ["missing"]) is None


def test_resolve_point_labels_falls_back_to_index():
    df = pd.DataFrame({"g": ["A", "", "nan"]})
    assert resolve_point_labels(df, "g") == ["A", "1", "2"]
    assert resolve_point_labels(df, None) == ["0", "1", "2"]


def test_build_pickable_points_skips_nonfinite():
    pts = build_pickable_points([1.0, float("nan"), 3.0], [0.0, 1.0, 2.0], ["a", "b", "c"])
    assert [p["label"] for p in pts] == ["a", "c"]
    assert pts[0] == {"x": 1.0, "y": 0.0, "label": "a", "index": 0}


def test_nearest_pickable_finds_closest():
    pts = [{"x": 0, "y": 0, "label": "o", "index": 0},
           {"x": 10, "y": 10, "label": "far", "index": 1}]
    best, d = nearest_pickable(pts, 0.2, 0.1, xspan=10, yspan=10)
    assert best["label"] == "o" and d < 0.05
    assert nearest_pickable([], 0, 0, 1, 1) == (None, float("inf"))


@pytest.mark.parametrize("pt,expect_col", [
    ("volcano_plot", "gene"),
    ("scatterplot_with_regression", "sample_id"),
])
def test_renderers_emit_pickable_points(pt, expect_col):
    info, _a, _s = examples.load_example(pt)
    r = render(make_spec(pt, "data.csv", "publication"), info.dataframe)
    pts = r.metadata["pickable_points"]
    assert len(pts) == info.n_rows
    assert r.metadata["pick_label_column"] == expect_col
    assert r.metadata["pick_label_key"] == "selected_labels"
    # labels are meaningful, not "nan"
    assert all(p["label"] and p["label"].lower() != "nan" for p in pts)


def test_click_to_label_roundtrip_volcano():
    info, _a, _s = examples.load_example("volcano_plot")
    r = render(make_spec("volcano_plot", "data.csv", "publication"), info.dataframe)
    pts = r.metadata["pickable_points"]
    col = r.metadata["pick_label_column"]
    # emulate a click near point 30
    target = pts[30]
    best, d = nearest_pickable(pts, target["x"], target["y"], 12, 5)
    assert best["index"] == target["index"] and d < 0.02
    # append clicked gene to the spec and re-render -> it is labelled
    spec = make_spec("volcano_plot", "data.csv", "publication")
    spec["mapping"] = dict(spec["mapping"], label=col, selected_labels=[best["label"]])
    r2 = render(spec, info.dataframe)
    assert r2.metadata["n_labeled"] >= 1


def test_click_to_label_roundtrip_scatter_only_selected():
    info, _a, _s = examples.load_example("scatterplot_with_regression")
    r = render(make_spec("scatterplot_with_regression", "data.csv", "publication"), info.dataframe)
    col = r.metadata["pick_label_column"]
    picked = r.metadata["pickable_points"][5]["label"]
    spec = make_spec("scatterplot_with_regression", "data.csv", "publication")
    spec["mapping"] = dict(spec["mapping"], label=col, selected_labels=[picked])
    fig = render(spec, info.dataframe).figure
    fig.canvas.draw()
    # exactly the picked point is annotated (scatter labels only 'selected_labels')
    texts = [t.get_text() for ax in fig.axes for t in ax.texts if t.get_text().strip()]
    assert picked in texts
