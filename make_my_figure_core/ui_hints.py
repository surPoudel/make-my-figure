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
    "volcano_plot": ["x", "p", "label", "id_col"],
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
    # --- v0.4 manuscript plot types ---
    "dot_strip_plot": ["x", "y", "color"],
    "beeswarm_plot": ["x", "y", "color"],
    "paired_slopegraph": ["subject", "condition", "value", "color"],
    "raincloud_plot": ["x", "y"],
    "hierarchical_dendrogram": ["row_id"],
    "ma_plot": ["x", "y", "p", "label"],
    "manhattan_plot": ["chrom", "pos", "p", "snp"],
    "qq_plot": ["p"],
    "bland_altman_plot": ["method_a", "method_b", "label"],
    "precision_recall_curve": ["label", "score", "score2"],
    "confusion_matrix": ["true", "predicted"],
    "calibration_plot": ["label", "prob"],
    "dose_response_curve": ["dose", "response", "group"],
    "upset_plot": [],                 # membership is a list of set columns (mapping['sets'])
    "swimmer_plot": ["subject", "start", "end", "duration", "event", "group"],
    "spider_plot": ["subject", "time", "value", "group"],
    "sankey_plot": ["source", "target", "value"],
    "embedding_scatter": ["x", "y", "color", "shape", "label"],
    # --- v0.5 ---
    "hierarchical_clustering": ["row_id"],
    "network_graph": ["source", "target", "weight"],
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
        # v0.5 clustering + highlighting
        Option("scale", "Scale", "choice", "none",
               ["none", "row_zscore", "column_zscore", "center_rows", "log", "log_zscore"]),
        Option("distance_metric", "Distance", "choice", "euclidean",
               ["euclidean", "correlation", "cosine", "cityblock"]),
        Option("linkage_method", "Linkage", "choice", "average",
               ["average", "complete", "single", "ward"]),
        Option("cluster_k_rows", "Row clusters (k, 0=off)", "number", 0, minimum=0, maximum=20, step=1, decimals=0),
        Option("cluster_k_columns", "Column clusters (k, 0=off)", "number", 0, minimum=0, maximum=20, step=1, decimals=0),
        Option("sort_by_cluster", "Sort by cluster", "bool", False),
        Option("max_features", "Max features (rows) for clustering", "number", 2000, minimum=50, maximum=50000, step=100, decimals=0),
    ],
    "volcano_plot": [
        Option("lfc_cutoff", "log2FC cutoff", "number", 1.0, minimum=0.0, maximum=20.0, step=0.5, decimals=2),
        Option("p_cutoff", "p-value / FDR cutoff", "number", 0.05, minimum=0.0, maximum=1.0, step=0.01, decimals=4),
        Option("use_fdr", "P column is FDR/adjusted (y-axis = −log10 FDR)", "bool", False),
        # v0.5 annotation controls
        Option("annotate", "Show labels", "bool", True),
        Option("label_mode", "Label mode", "choice", "top_fdr",
               ["top_fdr", "top_lfc", "top_up_down", "selected", "pasted", "significant_all"]),
        Option("top_n", "Top N labels", "number", 10, minimum=0, maximum=60, step=1, decimals=0),
        Option("top_n_up", "Top N up", "number", 8, minimum=0, maximum=40, step=1, decimals=0),
        Option("top_n_down", "Top N down", "number", 8, minimum=0, maximum=40, step=1, decimals=0),
        Option("label_by", "Label by", "choice", "symbol", ["symbol", "id", "both"]),
        Option("show_arrows", "Arrows to points", "bool", True),
        Option("label_box", "Label background box", "bool", False),
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
    # --- v0.4 manuscript plot types ---
    "dot_strip_plot": [
        Option("summary", "Summary overlay", "choice", "mean", ["none", "mean", "median", "ci", "sd", "sem"]),
        Option("jitter", "Jitter points", "bool", True),
    ],
    "beeswarm_plot": [
        Option("summary", "Summary overlay", "choice", "mean", ["none", "mean", "median", "ci", "sd", "sem"]),
    ],
    "paired_slopegraph": [],
    "raincloud_plot": [],
    "hierarchical_dendrogram": [
        Option("method", "Linkage method", "choice", "average", ["average", "complete", "single", "ward"]),
        Option("cluster", "Cluster", "choice", "rows", ["rows", "columns"]),
        Option("orientation", "Orientation", "choice", "top", ["top", "left"]),
    ],
    "ma_plot": [
        Option("p_cutoff", "Significance cutoff", "number", 0.05, minimum=0.0, maximum=1.0, step=0.01, decimals=4),
        Option("label_top_n", "Label top N hits", "number", 8, minimum=0, maximum=40, step=1, decimals=0),
    ],
    "manhattan_plot": [],
    "qq_plot": [Option("mode", "Mode", "choice", "pvalue", ["pvalue", "quantile"])],
    "bland_altman_plot": [Option("show_ci", "Shade 95% CI of bias", "bool", False)],
    "precision_recall_curve": [],
    "confusion_matrix": [
        Option("normalize", "Normalize", "choice", "none", ["none", "row", "column", "total"]),
    ],
    "calibration_plot": [
        Option("n_bins", "Number of bins", "number", 10, minimum=3, maximum=20, step=1, decimals=0),
    ],
    "dose_response_curve": [Option("fit", "Fit 4PL curve", "bool", True)],
    "upset_plot": [],
    "swimmer_plot": [],
    "spider_plot": [
        Option("reference", "Reference line (y)", "number", 0.0, minimum=-100.0, maximum=100.0, step=5.0, decimals=1),
    ],
    "sankey_plot": [],
    "embedding_scatter": [],
    # --- v0.5 ---
    "hierarchical_clustering": [
        Option("cluster", "Cluster", "choice", "rows", ["rows", "columns"]),
        Option("k", "Number of clusters k", "number", 3, minimum=2, maximum=20, step=1, decimals=0),
        Option("scale", "Scale", "choice", "row_zscore",
               ["none", "row_zscore", "column_zscore", "center_rows", "log", "log_zscore"]),
        Option("distance_metric", "Distance", "choice", "euclidean",
               ["euclidean", "correlation", "cosine", "cityblock"]),
        Option("linkage_method", "Linkage", "choice", "average",
               ["average", "complete", "single", "ward"]),
        Option("max_features", "Max features (rows) for clustering", "number", 2000, minimum=50, maximum=50000, step=100, decimals=0),
    ],
    "network_graph": [
        Option("layout", "Layout", "choice", "spring",
               ["spring", "kamada_kawai", "circular", "shell", "spectral", "multipartite", "fixed", "random"]),
        Option("seed", "Layout seed", "number", 42, minimum=0, maximum=99999, step=1, decimals=0),
        Option("color_by", "Color nodes by", "choice", "group", ["group", "value", "none"]),
        Option("size_by", "Size nodes by", "choice", "degree", ["degree", "value"]),
        Option("min_weight", "Min edge weight", "number", 0.0, minimum=0.0, maximum=100.0, step=0.1, decimals=2),
        Option("corr_cutoff", "|correlation| cutoff", "number", 0.3, minimum=0.0, maximum=1.0, step=0.05, decimals=2),
        Option("top_n_edges", "Top N edges (0=all)", "number", 0, minimum=0, maximum=5000, step=10, decimals=0),
        Option("min_degree", "Min node degree", "number", 0, minimum=0, maximum=100, step=1, decimals=0),
        Option("remove_isolates", "Remove isolated nodes", "bool", True),
        Option("detect_communities", "Detect communities (heuristic)", "bool", False),
        Option("node_labels", "Show node labels", "bool", True),
    ],
}


def column_fields(plot_type: str) -> List[str]:
    return list(COLUMN_FIELDS.get(plot_type, []))


def options(plot_type: str) -> List[Option]:
    return list(OPTIONS.get(plot_type, []))
