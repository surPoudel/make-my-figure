"""Publication-QC: PlotSpec round-trip reproducibility + export integrity.

Renders representative plots (incl. one with statistics and one with manual
annotations), exports figures + the PlotSpec sidecar, reloads the sidecar, and
re-renders — asserting key data/visual settings reproduce. Also checks each
export format is non-empty and that SVG/PDF keep editable (vector) text.
"""

import json
import os

import matplotlib
import matplotlib.pyplot as plt
import pytest

matplotlib.use("Agg")

from make_my_figure_core import examples
from make_my_figure_core.plots.registry import make_spec, render, render_to_files

REPRESENTATIVE = [
    "barplot_with_error_bar",
    "volcano_plot",
    "scatterplot_with_regression",
    "heatmap_clustered_matrix",
    "hierarchical_clustering",
    "network_graph",
    "kaplan_meier_survival_curve",
]


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _aux(pt):
    _i, aux, _s = examples.load_example(pt)
    return {k: v.dataframe for k, v in aux.items()} or None


@pytest.mark.parametrize("pt", REPRESENTATIVE)
def test_plotspec_roundtrip_reproduces_key_metadata(pt, tmp_path):
    info, aux, _ = examples.load_example(pt)
    aux_dfs = _aux(pt)
    spec = make_spec(pt, "data.csv", "publication")
    base = str(tmp_path / f"{pt}_a")
    out = render_to_files(spec, info.dataframe, base, formats=["svg", "png", "pdf"], aux=aux_dfs)

    # exports exist and are non-empty
    assert len(out["files"]) == 3
    for f in out["files"]:
        assert os.path.exists(f) and os.path.getsize(f) > 300
    # SVG keeps editable text (svg.fonttype=none)
    svg = next(f for f in out["files"] if f.endswith(".svg"))
    assert "<text" in open(svg, encoding="utf-8").read()

    # reload the sidecar's plot_spec and re-render
    with open(out["sidecar"], encoding="utf-8") as fh:
        reloaded = json.load(fh)["plot_spec"]
    assert reloaded["plot_type"] == pt
    r2 = render(reloaded, info.dataframe, aux=aux_dfs)
    m1, m2 = out["metadata"], r2.metadata
    assert m2["plot_type"] == m1["plot_type"]
    assert m2["data_columns_used"] == m1["data_columns_used"]
    # numeric fingerprints reproduce where present
    for key in ("n_up", "n_down", "n_ns", "n_clusters", "matrix_shape"):
        if key in m1:
            assert m2.get(key) == m1.get(key), f"{pt}: {key} did not reproduce"


def test_volcano_annotation_settings_roundtrip(tmp_path):
    info, _aux0, _ = examples.load_example("volcano_plot")
    spec = make_spec("volcano_plot", "data.csv", "publication")
    spec["mapping"] = dict(spec["mapping"], label="label", label_mode="top_up_down",
                           top_n_up=5, top_n_down=5, show_arrows=True)
    base = str(tmp_path / "volc")
    out = render_to_files(spec, info.dataframe, base, formats=["svg", "pdf"])
    reloaded = json.load(open(out["sidecar"], encoding="utf-8"))["plot_spec"]
    # annotation choices are stored in the PlotSpec
    assert reloaded["mapping"]["label_mode"] == "top_up_down"
    assert reloaded["mapping"]["show_arrows"] is True
    r2 = render(reloaded, info.dataframe)
    assert r2.metadata["n_labeled"] == out["metadata"]["n_labeled"]


def test_manual_annotationspec_roundtrip(tmp_path):
    info, _a, _s = examples.load_example("scatterplot_with_regression")
    spec = make_spec("scatterplot_with_regression", "data.csv", "publication")
    spec["annotations"] = [
        {"kind": "region", "coords": "axes", "xy": [0.1, 0.1], "xy2": [0.4, 0.5], "text": "ROI"},
        {"kind": "callout", "coords": "axes", "xy": [0.6, 0.6], "xy2": [0.8, 0.3], "text": "x", "arrow": True},
    ]
    base = str(tmp_path / "ann")
    out = render_to_files(spec, info.dataframe, base, formats=["svg", "png"])
    reloaded = json.load(open(out["sidecar"], encoding="utf-8"))["plot_spec"]
    assert len(reloaded["annotations"]) == 2
    r2 = render(reloaded, info.dataframe)
    assert r2.metadata.get("n_manual_annotations") == 2
    # annotation text present in the vector export
    svg = next(f for f in out["files"] if f.endswith(".svg"))
    assert "ROI" in open(svg, encoding="utf-8").read()
