"""Frontend-agnostic UI hints: which mapping keys are columns, and what extra
options each plot type exposes. Both the Streamlit and desktop frontends read
this so plot configuration is never hard-coded inside a GUI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Mapping keys that should be presented as *column choosers* per plot type.
COLUMN_FIELDS: Dict[str, List[str]] = {
    "barplot_with_error_bar": ["x", "y", "color"],
    "grouped_barplot_with_error_bar": ["x", "group", "y"],
    "heatmap_clustered_matrix": ["row_id"],
    "volcano_plot": ["x", "p", "label"],
    "scatterplot_with_regression": ["x", "y", "color", "label"],
    "boxplot_or_violin_with_points": ["x", "y"],
    "lineplot_timecourse_with_error_band": ["x", "y", "color"],
    "ridge_or_density_plot": ["x", "group"],
    "enrichment_dotplot": ["y", "x", "size", "color"],
    "kaplan_meier_survival_curve": ["time", "event", "group"],
    "stacked_bar_composition": ["x", "stack", "y", "facet_or_sort_by"],
    "waterfall_plot": ["x", "y", "color"],
    "pca_scatter_from_matrix": ["matrix_row_id"],   # color/shape come from metadata
    "oncoprint_mutation_heatmap": ["sample", "row", "fill"],
    "lollipop_mutation_plot": ["x", "y", "color", "label"],
    "roc_curve": ["label", "score", "score2"],
    "forest_plot": ["label", "estimate", "lower", "upper"],
}

# Mapping keys that are columns of the PCA *metadata* table, not the matrix.
PCA_METADATA_FIELDS: List[str] = ["color", "shape"]


@dataclass
class Option:
    key: str
    label: str
    kind: str                       # "choice" | "bool" | "number"
    default: Any = None
    choices: Optional[List[Any]] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    step: Optional[float] = None
    decimals: int = 3


_ERROR_CHOICES = ["sem", "sd", "ci95", "none"]

# Extra (non-column) options per plot type.
OPTIONS: Dict[str, List[Option]] = {
    "barplot_with_error_bar": [Option("error", "Error bar", "choice", "sem", _ERROR_CHOICES)],
    "grouped_barplot_with_error_bar": [Option("error", "Error bar", "choice", "sem", _ERROR_CHOICES)],
    "heatmap_clustered_matrix": [
        Option("cluster_rows", "Cluster rows", "bool", True),
        Option("cluster_columns", "Cluster columns", "bool", True),
        Option("color_scale", "Color scale", "choice", "diverging", ["diverging", "sequential"]),
    ],
    "volcano_plot": [
        Option("lfc_cutoff", "log2FC cutoff", "number", 1.0, minimum=0.0, maximum=20.0, step=0.5, decimals=2),
        Option("p_cutoff", "p-value cutoff", "number", 0.05, minimum=0.0, maximum=1.0, step=0.01, decimals=4),
    ],
    "scatterplot_with_regression": [Option("fit_line", "Fit regression line", "bool", True)],
    "boxplot_or_violin_with_points": [
        Option("kind", "Kind", "choice", "box", ["box", "violin"]),
        Option("points", "Overlay points", "bool", True),
    ],
    "lineplot_timecourse_with_error_band": [Option("error", "Error band", "choice", "sem", _ERROR_CHOICES)],
    "ridge_or_density_plot": [
        Option("overlap", "Ridge overlap", "number", 0.7, minimum=0.0, maximum=0.95, step=0.05, decimals=2),
    ],
    "enrichment_dotplot": [
        Option("top_n", "Top N terms", "number", 20, minimum=5, maximum=40, step=1, decimals=0),
    ],
    "kaplan_meier_survival_curve": [],
    "stacked_bar_composition": [],
    "waterfall_plot": [Option("sort", "Sort", "choice", "ascending", ["ascending", "descending"])],
    "pca_scatter_from_matrix": [],
    "oncoprint_mutation_heatmap": [],
    "lollipop_mutation_plot": [
        Option("show_labels", "Show mutation labels", "bool", True),
        Option("label_top_n", "Label top N mutations", "number", 6, minimum=0, maximum=40, step=1, decimals=0),
        Option("legend_loc", "Legend position", "choice", "right", ["right", "bottom"]),
        Option("marker_scale", "Marker scale", "number", 16.0, minimum=4.0, maximum=60.0, step=2.0, decimals=1),
        Option("y_margin", "Top y-margin", "number", 0.28, minimum=0.05, maximum=0.6, step=0.05, decimals=2),
    ],
    "roc_curve": [],
    "forest_plot": [
        Option("reference", "Reference line", "number", 1.0, minimum=0.0, maximum=100.0, step=0.5, decimals=2),
        Option("log_scale", "Log x-axis", "bool", True),
    ],
}


def column_fields(plot_type: str) -> List[str]:
    return list(COLUMN_FIELDS.get(plot_type, []))


def options(plot_type: str) -> List[Option]:
    return list(OPTIONS.get(plot_type, []))
