"""Tests for v0.5 features: network graph, universal annotations, hierarchical
clustering + k assignment, and the volcano annotation overhaul."""

import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")

from make_my_figure_core import examples
from make_my_figure_core.annotations import Annotation, apply_annotations, parse_annotations
from make_my_figure_core.plots.base import RenderError
from make_my_figure_core.plots.registry import make_spec, render, render_to_files
from make_my_figure_core.styles.engine import load_profile


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _edges():
    return pd.DataFrame({
        "source": ["A", "A", "B", "C", "C", "D", "E"],
        "target": ["B", "C", "C", "D", "E", "E", "A"],
        "weight": [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.95],
        "interaction_type": ["a", "b", "a", "b", "a", "b", "a"],
    })


def _nodes():
    return pd.DataFrame({"node": ["A", "B", "C", "D", "E"],
                         "group": ["g1", "g1", "g2", "g2", "g1"],
                         "value": [1.0, -1.0, 0.5, 2.0, -0.5]})


# --- network graph ----------------------------------------------------------
def test_network_registered_and_example_renders():
    info, aux, _ = examples.load_example("network_graph")
    aux_dfs = {k: v.dataframe for k, v in aux.items()} or None
    r = render(make_spec("network_graph", "data.csv", "publication"), info.dataframe, aux=aux_dfs)
    assert r.metadata["publication_check"]["passed"]
    assert r.metadata["network_summary"]["n_nodes"] > 0
    assert r.metadata["network_summary"]["n_edges"] > 0


def test_network_edge_list_missing_column_raises():
    spec = make_spec("network_graph", "d.csv", "nature_like")
    spec["mapping"] = {"source": "source", "target": "__nope__"}
    with pytest.raises(RenderError):
        render(spec, _edges(), aux={"nodes": _nodes()})


def test_network_layout_seed_recorded_and_metrics_present():
    spec = make_spec("network_graph", "d.csv", "publication")
    spec["mapping"] = {"source": "source", "target": "target", "weight": "weight",
                       "layout": "spring", "seed": 7, "color_by": "group"}
    r = render(spec, _edges(), aux={"nodes": _nodes()})
    assert r.metadata.get("seed") == 7 or r.metadata["network_summary"].get("seed") == 7
    s = r.metadata["network_summary"]
    assert s["n_nodes"] == 5 and s["n_edges"] == 7
    assert "density" in s and "n_connected_components" in s


def test_network_min_weight_filter_reduces_edges():
    base = make_spec("network_graph", "d.csv", "publication")
    base["mapping"] = {"source": "source", "target": "target", "weight": "weight", "layout": "circular"}
    r_all = render(base, _edges(), aux={"nodes": _nodes()})
    filt = make_spec("network_graph", "d.csv", "publication")
    filt["mapping"] = dict(base["mapping"], min_weight=0.75)
    r_filt = render(filt, _edges(), aux={"nodes": _nodes()})
    assert r_filt.metadata["network_summary"]["n_edges"] < r_all.metadata["network_summary"]["n_edges"]


def test_network_exports(tmp_path):
    spec = make_spec("network_graph", "d.csv", "science_like")
    spec["mapping"] = {"source": "source", "target": "target", "weight": "weight", "layout": "circular"}
    out = render_to_files(spec, _edges(), str(tmp_path / "net"), formats=["svg", "png", "pdf"],
                          aux={"nodes": _nodes()})
    assert len(out["files"]) == 3
    for f in out["files"]:
        assert os.path.exists(f) and os.path.getsize(f) > 200


# --- universal annotations --------------------------------------------------
def test_annotation_roundtrip():
    a = Annotation(kind="callout", text="hi", xy=(1.0, 2.0), xy2=(3.0, 4.0), arrow=True, box=True)
    d = a.to_dict()
    b = Annotation.from_dict(d)
    assert b.kind == "callout" and b.xy == (1.0, 2.0) and b.xy2 == (3.0, 4.0) and b.arrow


def test_parse_annotations_skips_garbage():
    anns = parse_annotations([{"kind": "text", "xy": [1, 2], "text": "x"}, 123, None])
    assert len(anns) == 1 and anns[0].kind == "text"


def test_annotations_apply_across_plot_types():
    for pt in ("scatterplot_with_regression", "barplot_with_error_bar", "volcano_plot"):
        info, aux, _ = examples.load_example(pt)
        aux_dfs = {k: v.dataframe for k, v in aux.items()} or None
        spec = make_spec(pt, "data.csv", "publication")
        spec["annotations"] = [
            {"kind": "text", "coords": "axes", "xy": [0.05, 0.9], "text": "note", "box": True},
            {"kind": "region", "coords": "axes", "xy": [0.1, 0.1], "xy2": [0.4, 0.4]},
        ]
        r = render(spec, info.dataframe, aux=aux_dfs)
        assert r.metadata.get("n_manual_annotations") == 2


def test_apply_annotations_direct():
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    n = apply_annotations(fig, ax, parse_annotations([
        {"kind": "arrow", "xy": [0.2, 0.2], "xy2": [0.8, 0.8]},
        {"kind": "bracket", "xy": [0.1, 0.9], "xy2": [0.9, 0.9], "text": "span"},
        {"kind": "hline", "xy": [0, 0.5]},
    ]), load_profile("publication"))
    assert n == 3


# --- hierarchical clustering ------------------------------------------------
def test_hierarchical_clustering_k_assignment():
    info, aux, _ = examples.load_example("hierarchical_clustering")
    spec = make_spec("hierarchical_clustering", "data.csv", "publication")
    spec["mapping"] = dict(spec["mapping"], k=3)
    r = render(spec, info.dataframe)
    assign = r.metadata.get("cluster_assignment")
    assert assign is not None and len(assign) == info.n_rows
    n_clusters = len({row["cluster"] for row in assign})
    assert n_clusters == 3


def test_hierarchical_clustering_invalid_k_raises():
    info, aux, _ = examples.load_example("hierarchical_clustering")
    spec = make_spec("hierarchical_clustering", "data.csv", "nature_like")
    spec["mapping"] = dict(spec["mapping"], k=1)
    with pytest.raises(RenderError):
        render(spec, info.dataframe)


def test_hierarchical_clustering_ward_correlation_raises():
    info, aux, _ = examples.load_example("hierarchical_clustering")
    spec = make_spec("hierarchical_clustering", "data.csv", "nature_like")
    spec["mapping"] = dict(spec["mapping"], linkage_method="ward", distance_metric="correlation")
    with pytest.raises(RenderError):
        render(spec, info.dataframe)


def test_heatmap_cluster_k_rows_color_strip_and_assignment():
    info, aux, _ = examples.load_example("heatmap_clustered_matrix")
    spec = make_spec("heatmap_clustered_matrix", "data.csv", "publication")
    spec["mapping"] = dict(spec["mapping"], cluster_k_rows=3)
    r = render(spec, info.dataframe)
    assert r.metadata["publication_check"]["passed"]
    assert r.metadata.get("row_assignment") is not None
    n = len({row["cluster"] for row in r.metadata["row_assignment"]})
    assert n == 3


def test_heatmap_default_still_works():
    info, aux, _ = examples.load_example("heatmap_clustered_matrix")
    r = render(make_spec("heatmap_clustered_matrix", "data.csv", "nature_like"), info.dataframe)
    assert r.metadata["plot_type"] == "heatmap_clustered_matrix"
    assert r.metadata["publication_check"]["passed"]


# --- volcano annotation overhaul --------------------------------------------
def _volcano_df():
    rng = np.random.default_rng(3)
    n = 300
    lfc = rng.normal(0, 1.1, n)
    p = rng.uniform(0, 1, n)
    up = rng.choice(n, 15, replace=False)
    lfc[up] += 3
    p[up] = rng.uniform(1e-8, 1e-3, 15)
    return pd.DataFrame({"log2_fold_change": lfc, "p_value": p,
                         "label": [f"G{i}" for i in range(n)]})


def test_volcano_annotate_off_draws_no_labels():
    spec = make_spec("volcano_plot", "d.csv", "publication")
    spec["mapping"] = dict(spec["mapping"], p="p_value", annotate=False)
    r = render(spec, _volcano_df())
    assert r.metadata["n_labeled"] == 0
    assert r.metadata["publication_check"]["passed"]


def test_volcano_top_up_down_labels():
    spec = make_spec("volcano_plot", "d.csv", "publication")
    spec["mapping"] = dict(spec["mapping"], p="p_value", label="label",
                           label_mode="top_up_down", top_n_up=5, top_n_down=5)
    r = render(spec, _volcano_df())
    assert r.metadata["n_labeled"] > 0
    assert r.metadata["publication_check"]["passed"]


def test_volcano_pasted_list_and_no_arrows():
    spec = make_spec("volcano_plot", "d.csv", "publication")
    spec["mapping"] = dict(spec["mapping"], p="p_value", label="label",
                           label_mode="pasted", label_list=["G0", "G1", "G2"], show_arrows=False)
    r = render(spec, _volcano_df())
    assert r.metadata["publication_check"]["passed"]
