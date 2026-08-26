import os
import sys

import matplotlib

matplotlib.use("Agg")  # never try to open a window during tests

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

MOCK_DIR = os.path.join(_REPO_ROOT, "mock_data")

# plot_type -> mock data file used as a golden input.
PLOT_SAMPLES = {
    "barplot_with_error_bar": "barplot_error_raw.csv",
    "grouped_barplot_with_error_bar": "grouped_barplot_error.csv",
    "heatmap_clustered_matrix": "heatmap_expression_matrix.tsv",
    "volcano_plot": "volcano_plot.csv",
    "scatterplot_with_regression": "scatter_regression.csv",
    "boxplot_or_violin_with_points": "box_violin_points.csv",
    "lineplot_timecourse_with_error_band": "line_timecourse.tsv",
    "ridge_or_density_plot": "ridge_density.csv",
    "histogram_distribution": "histogram_distribution.csv",
    "enrichment_dotplot": "enrichment_dotplot.csv",
    "kaplan_meier_survival_curve": "survival_km.csv",
    "stacked_bar_composition": "stacked_composition.csv",
    "waterfall_plot": "waterfall_response.csv",
    "pca_scatter_from_matrix": "pca_expression_matrix.tsv",
    "oncoprint_mutation_heatmap": "oncoprint_long.csv",
    "lollipop_mutation_plot": "lollipop_mutations.csv",
    "roc_curve": "roc_curve_scores.csv",
    "forest_plot": "forest_plot.csv",
}

PCA_METADATA_FILE = "pca_sample_metadata.csv"


@pytest.fixture
def repo_root():
    return _REPO_ROOT


@pytest.fixture
def mock_dir():
    return MOCK_DIR


@pytest.fixture(params=sorted(PLOT_SAMPLES.items()), ids=lambda kv: kv[0])
def plot_case(request):
    plot_type, filename = request.param
    return plot_type, os.path.join(MOCK_DIR, filename), filename
