"""Tests for the v0.4 manuscript plot types.

Per new plot type: a render smoke test, an export smoke test (SVG/PNG/PDF +
sidecar), and a publication-readiness assertion — all driven from the bundled
example data. Plus targeted validator and metadata-correctness checks.
"""

import os

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import pytest

matplotlib.use("Agg")

from make_my_figure_core import examples
from make_my_figure_core.plots.base import RenderError
from make_my_figure_core.plots.registry import (
    available_plot_types,
    make_spec,
    render,
    render_to_files,
)

V04_PLOT_TYPES = [
    "dot_strip_plot", "beeswarm_plot", "paired_slopegraph", "raincloud_plot",
    "hierarchical_dendrogram", "ma_plot", "manhattan_plot", "qq_plot",
    "bland_altman_plot", "precision_recall_curve", "confusion_matrix",
    "calibration_plot", "dose_response_curve", "upset_plot", "swimmer_plot",
    "spider_plot", "sankey_plot", "embedding_scatter",
]


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _render_example(pt, profile="publication"):
    info, aux, _spec = examples.load_example(pt)
    spec = make_spec(pt, "data.csv", profile)
    aux_dfs = {k: v.dataframe for k, v in aux.items()} or None
    return spec, info, render(spec, info.dataframe, aux=aux_dfs)


def test_all_v04_types_registered():
    registered = set(available_plot_types())
    missing = [pt for pt in V04_PLOT_TYPES if pt not in registered]
    assert not missing, f"unregistered v0.4 types: {missing}"
    assert len(V04_PLOT_TYPES) == 18


@pytest.mark.parametrize("pt", V04_PLOT_TYPES)
def test_v04_has_example(pt):
    assert examples.has_example(pt), f"{pt} has no bundled example"


@pytest.mark.parametrize("pt", V04_PLOT_TYPES)
def test_v04_renders_and_passes_publication_check(pt):
    _spec, _info, result = _render_example(pt)
    assert result.figure is not None
    assert result.metadata["plot_type"] == pt
    check = result.metadata.get("publication_check")
    assert check is not None and check["passed"], f"{pt}: {check and check['warnings']}"


@pytest.mark.parametrize("pt", V04_PLOT_TYPES)
def test_v04_does_not_mutate_input(pt):
    info, aux, _ = examples.load_example(pt)
    before = info.dataframe.copy(deep=True)
    _render_example(pt)
    pd.testing.assert_frame_equal(info.dataframe, before)


@pytest.mark.parametrize("pt", V04_PLOT_TYPES)
def test_v04_exports_svg_png_pdf_with_sidecar(pt, tmp_path):
    info, aux, _spec = examples.load_example(pt)
    spec = make_spec(pt, "data.csv", "science_like")
    aux_dfs = {k: v.dataframe for k, v in aux.items()} or None
    base = str(tmp_path / pt)
    out = render_to_files(spec, info.dataframe, base, formats=["svg", "png", "pdf"], aux=aux_dfs)
    assert len(out["files"]) == 3
    for f in out["files"]:
        assert os.path.exists(f) and os.path.getsize(f) > 200
    assert os.path.exists(out["sidecar"])


# --- validator tests: a guaranteed-missing required column raises clearly ----
# (key, bogus_value) forced into the mapping per type.
_MISSING_REQUIRED = {
    "dot_strip_plot": ("y", "__nope__"),
    "beeswarm_plot": ("y", "__nope__"),
    "paired_slopegraph": ("value", "__nope__"),
    "raincloud_plot": ("y", "__nope__"),
    "manhattan_plot": ("p", "__nope__"),
    "qq_plot": ("p", "__nope__"),
    "bland_altman_plot": ("method_a", "__nope__"),
    "precision_recall_curve": ("score", "__nope__"),
    "confusion_matrix": ("predicted", "__nope__"),
    "calibration_plot": ("prob", "__nope__"),
    "dose_response_curve": ("response", "__nope__"),
    "swimmer_plot": ("end", "__nope__"),
    "spider_plot": ("value", "__nope__"),
    "sankey_plot": ("value", "__nope__"),
}


@pytest.mark.parametrize("pt", sorted(_MISSING_REQUIRED))
def test_v04_missing_required_column_raises(pt):
    info, aux, _spec = examples.load_example(pt)
    spec = make_spec(pt, "data.csv", "nature_like")
    key, bogus = _MISSING_REQUIRED[pt]
    spec["mapping"][key] = bogus
    aux_dfs = {k: v.dataframe for k, v in aux.items()} or None
    with pytest.raises(RenderError):
        render(spec, info.dataframe, aux=aux_dfs)


# --- targeted metadata correctness ------------------------------------------
def test_ma_plot_counts_significant():
    _spec, info, result = _render_example("ma_plot")
    m = result.metadata
    assert m["n_up"] > 0 and m["n_down"] > 0
    assert m["n_up"] + m["n_down"] + m["n_ns"] == info.n_rows


def test_manhattan_flags_genome_wide_hits():
    _spec, _info, result = _render_example("manhattan_plot")
    assert result.metadata["n_genome_wide"] >= 1


def test_precision_recall_stronger_model_has_higher_auprc():
    _spec, _info, result = _render_example("precision_recall_curve")
    auprc = result.metadata.get("auprc", {})
    # model A was generated as the stronger classifier.
    a = next((v for k, v in auprc.items() if "a" in k.lower()), None)
    b = next((v for k, v in auprc.items() if "b" in k.lower()), None)
    assert a is not None and b is not None and a > b


def test_confusion_matrix_accuracy_from_labels():
    _spec, _info, result = _render_example("confusion_matrix")
    acc = result.metadata.get("accuracy")
    assert acc is not None and 0.0 <= acc <= 1.0
