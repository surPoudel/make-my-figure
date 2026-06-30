"""Mock / template dataset helpers.

Centralizes the mapping from plot type to its bundled example dataset so every
frontend (Streamlit, desktop) shares one source of truth. Resource paths are
resolved via :mod:`make_my_figure_core.resources` so this works both in a dev
checkout and inside a packaged app.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from make_my_figure_core.io.loaders import TableInfo, load_table
from make_my_figure_core.resources import resource_path

# plot_type -> bundled example file (relative to the mock_data dir).
SAMPLE_FILES: Dict[str, str] = {
    "barplot_with_error_bar": "barplot_error_raw.csv",
    "grouped_barplot_with_error_bar": "grouped_barplot_error.csv",
    "heatmap_clustered_matrix": "heatmap_expression_matrix.tsv",
    "volcano_plot": "volcano_plot.csv",
    "scatterplot_with_regression": "scatter_regression.csv",
    "boxplot_or_violin_with_points": "box_violin_points.csv",
    "lineplot_timecourse_with_error_band": "line_timecourse.tsv",
    "ridge_or_density_plot": "ridge_density.csv",
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

# PCA needs a second (sample-metadata) table whose sample_id matches the
# matrix's sample column names.
PCA_METADATA_FILE = "pca_sample_metadata.csv"
PCA_PLOT_TYPE = "pca_scatter_from_matrix"

MANIFEST_FILE = "plot_schema_manifest.json"


def mock_dir() -> str:
    return resource_path("mock_data")


def sample_filename(plot_type: str) -> Optional[str]:
    return SAMPLE_FILES.get(plot_type)


def sample_path(plot_type: str) -> Optional[str]:
    fn = SAMPLE_FILES.get(plot_type)
    return os.path.join(mock_dir(), fn) if fn else None


def list_samples() -> List[Tuple[str, str]]:
    """Return ``(plot_type, filename)`` pairs for every bundled example."""
    return list(SAMPLE_FILES.items())


def load_manifest() -> Dict[str, Any]:
    path = os.path.join(mock_dir(), MANIFEST_FILE)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_sample(plot_type: str) -> Tuple[TableInfo, Dict[str, TableInfo]]:
    """Load the example table for ``plot_type`` plus any auxiliary tables.

    Returns ``(table_info, aux)`` where ``aux`` maps auxiliary-table names to
    their loaded :class:`TableInfo` (currently only PCA sample metadata).
    """
    path = sample_path(plot_type)
    if not path:
        raise KeyError(f"No bundled sample for plot type '{plot_type}'.")
    info = load_table(path)
    aux: Dict[str, TableInfo] = {}
    if plot_type == PCA_PLOT_TYPE:
        meta_path = os.path.join(mock_dir(), PCA_METADATA_FILE)
        if os.path.exists(meta_path):
            aux["metadata"] = load_table(meta_path)
    return info, aux
