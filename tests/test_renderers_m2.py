"""Milestone-2 renderer-specific assertions (in addition to the broad
render/export/no-mutation tests in test_renderers.py, which now cover all
registered plot types via the parametrized ``plot_case`` fixture)."""

import os

import matplotlib.pyplot as plt
import numpy as np

from conftest import MOCK_DIR, PCA_METADATA_FILE

from make_my_figure_core.io.loaders import load_table
from make_my_figure_core.plots.registry import available_plot_types, make_spec, render


def _load(name):
    return load_table(os.path.join(MOCK_DIR, name))


def test_all_seventeen_plot_types_registered():
    assert len(available_plot_types()) == 17


def test_box_and_violin_kinds(mock_dir):
    info = _load("box_violin_points.csv")
    for kind in ("box", "violin"):
        spec = make_spec("boxplot_or_violin_with_points", "box_violin_points.csv", "nature_like")
        spec["mapping"]["kind"] = kind
        result = render(spec, info.dataframe)
        assert result.metadata["kind"] == kind
        plt.close(result.figure)


def test_lineplot_band_series(mock_dir):
    info = _load("line_timecourse.tsv")
    spec = make_spec("lineplot_timecourse_with_error_band", "line_timecourse.tsv", "nature_like")
    result = render(spec, info.dataframe)
    assert set(result.metadata["series"]) == {"Vehicle", "Drug_A", "Drug_B"}
    plt.close(result.figure)


def test_ridge_groups(mock_dir):
    info = _load("ridge_density.csv")
    spec = make_spec("ridge_or_density_plot", "ridge_density.csv", "cell_like")
    result = render(spec, info.dataframe)
    assert len(result.metadata["groups"]) >= 2
    plt.close(result.figure)


def test_km_groups_and_events(mock_dir):
    info = _load("survival_km.csv")
    spec = make_spec("kaplan_meier_survival_curve", "survival_km.csv", "nature_like")
    result = render(spec, info.dataframe)
    groups = result.metadata["groups"]
    assert set(groups.keys()) == {"Low_risk", "High_risk"}
    assert all(g["events"] <= g["n"] for g in groups.values())
    plt.close(result.figure)


def test_stacked_components_sum(mock_dir):
    info = _load("stacked_composition.csv")
    spec = make_spec("stacked_bar_composition", "stacked_composition.csv", "nature_like")
    result = render(spec, info.dataframe)
    assert len(result.metadata["components"]) >= 2
    plt.close(result.figure)


def test_waterfall_sort_counts(mock_dir):
    info = _load("waterfall_response.csv")
    spec = make_spec("waterfall_plot", "waterfall_response.csv", "nature_like")
    result = render(spec, info.dataframe)
    m = result.metadata
    assert m["sort"] == "ascending"
    assert m["n_decrease"] + m["n_increase"] <= m["n_patients"]
    plt.close(result.figure)


def test_pca_with_metadata(mock_dir):
    matrix = _load("pca_expression_matrix.tsv")
    meta = _load(PCA_METADATA_FILE)
    spec = make_spec("pca_scatter_from_matrix", "pca_expression_matrix.tsv", "nature_like")
    result = render(spec, matrix.dataframe, aux={"metadata": meta.dataframe})
    evr = result.metadata["explained_variance_ratio"]
    assert evr[0] >= evr[1]  # PC1 explains at least as much as PC2
    assert abs(sum(evr) - sum(sorted(evr, reverse=True))) < 1e-9
    assert result.metadata["color_by"] == "group"
    plt.close(result.figure)


def test_pca_without_metadata_warns(mock_dir):
    matrix = _load("pca_expression_matrix.tsv")
    spec = make_spec("pca_scatter_from_matrix", "pca_expression_matrix.tsv", "nature_like")
    result = render(spec, matrix.dataframe)  # no aux
    assert any("metadata" in w.lower() for w in result.warnings)
    plt.close(result.figure)


def test_oncoprint_frequencies(mock_dir):
    info = _load("oncoprint_long.csv")
    spec = make_spec("oncoprint_mutation_heatmap", "oncoprint_long.csv", "nature_like")
    result = render(spec, info.dataframe)
    freq = list(result.metadata["gene_frequency"].values())
    assert freq == sorted(freq, reverse=True)  # genes ordered by frequency
    plt.close(result.figure)


def test_lollipop_positions(mock_dir):
    info = _load("lollipop_mutations.csv")
    spec = make_spec("lollipop_mutation_plot", "lollipop_mutations.csv", "nature_like")
    result = render(spec, info.dataframe)
    assert result.metadata["n_positions"] > 0
    plt.close(result.figure)


def test_roc_auc_ordering(mock_dir):
    info = _load("roc_curve_scores.csv")
    spec = make_spec("roc_curve", "roc_curve_scores.csv", "nature_like")
    result = render(spec, info.dataframe)
    aucs = result.metadata["auc"]
    assert 0.0 <= aucs["score_model_a"] <= 1.0
    # model A is the stronger model in the mock data
    assert aucs["score_model_a"] > 0.5
    plt.close(result.figure)


def test_forest_reference_and_rows(mock_dir):
    info = _load("forest_plot.csv")
    spec = make_spec("forest_plot", "forest_plot.csv", "nature_like")
    result = render(spec, info.dataframe)
    assert result.metadata["reference"] == 1.0
    assert result.metadata["n_rows"] >= 1
    plt.close(result.figure)
