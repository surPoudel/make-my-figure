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
    # "x"/"group" is the long form; "value_columns" is the wide form (one column per group).
    "histogram_distribution": ["x", "group", "value_columns"],
    "enrichment_dotplot": ["y", "x", "size", "color"],
    # "event"/"group" drive the subject-level form; "survival_columns" is the
    # precomputed-curve form (one column of S(t) per group).
    "kaplan_meier_survival_curve": ["time", "event", "group", "survival_columns"],
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
    "ma_plot": ["x", "y", "p", "label", "id_col"],
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
    "network_graph": ["source", "target", "weight", "interaction_type"],
}

# Mapping keys that are columns of the PCA *metadata* table, not the matrix.
PCA_METADATA_FIELDS: List[str] = ["color", "shape"]


# What a Figure Preset may carry an option in. "style" options are visual - how the figure looks
# (colours, line styles, arrangements, what text is shown) - and belong in a portable style
# preset that a lab applies to every figure of this type. "config" options are analytical or
# data-dependent - thresholds, bin widths, clustering methods, axis limits, which columns - and
# travel only in a full figure configuration. The default is "config": an option has to be
# declared visual to end up in a style preset, so a new threshold cannot leak into a lab style
# by omission.
OPTION_SCOPES = ("style", "config")


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
    scope: str = "config"           # "style" | "config" - see OPTION_SCOPES

    def __post_init__(self) -> None:
        if self.scope not in OPTION_SCOPES:
            raise ValueError(f"Option {self.key!r}: scope must be one of {OPTION_SCOPES}, "
                             f"got {self.scope!r}")


_ERROR_CHOICES = ["sem", "sd", "ci95", "none"]
# Line plot bands add median-centred order statistics for replicate measurements.
_BAND_CHOICES = ["sem", "sd", "ci95", "iqr", "range", "none"]
# Common publication-safe colors for network node/edge controls ("(palette)" =
# use the active Publication palette rather than a fixed color).
_NET_NODE_COLORS = ["(palette)", "#2166AC", "#B2182B", "#1B7837", "#762A83",
                    "#E08214", "#333333", "#888888", "black", "white"]
_NET_EDGE_COLORS = ["#888888", "#BBBBBB", "#333333", "black", "#2166AC", "#B2182B"]
# Significance-class colours (volcano / MA). Colour-blind-aware pairs first; the defaults are the
# classic blue / grey / red so an untouched figure looks as it always did.
_SIG_COLORS = ["#B2182B", "#2166AC", "#BBBBBB", "#B8B8B8", "#D6604D", "#4393C3", "#E08214",
               "#8073AC", "#1B7837", "#762A83", "#333333", "#888888", "black"]

# Shared control: how to angle categorical x-axis labels. "auto" (default) keeps
# long/numerous labels (e.g. sample names) readable without user intervention.
_X_TICK_ROTATION = Option("x_tick_rotation", "X-axis label angle", "choice", "auto",
                          ["auto", "horizontal", "45", "vertical"], scope="style")

# Curated publication-grade colormaps for heatmaps/clustering. "auto" follows the
# palette + scale (diverging RdBu_r for z-scores, viridis for unscaled). All are
# colourblind-aware except the classic reds/greens which are intentionally omitted.
_HEATMAP_COLORMAP = Option(
    "colormap", "Colormap", "choice", "auto",
    ["auto", "RdBu_r", "coolwarm", "seismic", "RdYlBu_r", "PuOr", "BrBG",
     "viridis", "magma", "cividis", "Blues", "YlOrRd", "Greys"], scope="style")

# Y-axis label orientation (vertical is the default; horizontal reads more easily
# for short labels).
_Y_LABEL_ROTATION = Option("y_label_rotation", "Y-label angle", "choice", "vertical",
                           ["vertical", "horizontal"], scope="style")

# Extra (non-column) options per plot type.
OPTIONS: Dict[str, List[Option]] = {
    "barplot_with_error_bar": [Option("error", "Error bar", "choice", "sem", _ERROR_CHOICES, scope="style"),
                               _X_TICK_ROTATION],
    "grouped_barplot_with_error_bar": [Option("error", "Error bar", "choice", "sem", _ERROR_CHOICES, scope="style"),
                                       _X_TICK_ROTATION],
    "heatmap_clustered_matrix": [
        Option("cluster_rows", "Cluster rows", "bool", True),
        Option("cluster_columns", "Cluster columns", "bool", True),
        Option("color_scale", "Color scale", "choice", "diverging", ["diverging", "sequential"], scope="style"),
        _HEATMAP_COLORMAP,
        _Y_LABEL_ROTATION,
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
        Option("group_separators", "Group separator lines", "bool", True, scope="style"),
        # Catchy cell grid + group-separator styling (all user-controllable).
        Option("cell_border_color", "Cell grid color", "choice", "white",
               ["white", "black", "#888888", "none"], scope="style"),
        Option("cell_border_width", "Cell grid width (0 = off)", "number", 0.6,
               minimum=0.0, maximum=3.0, step=0.2, decimals=1, scope="style"),
        Option("group_separator_color", "Group separator color", "choice", "#222222",
               ["#222222", "black", "white", "#B2182B"], scope="style"),
        Option("group_separator_width", "Group separator width", "number", 1.6,
               minimum=0.0, maximum=6.0, step=0.5, decimals=1, scope="style"),
        Option("max_features", "Max features (rows) for clustering", "number", 2000, minimum=50, maximum=50000, step=100, decimals=0),
        Option("colorbar_location", "Colorbar location", "choice", "right", ["right", "left", "top", "bottom"], scope="style"),
        Option("colorbar_pad", "Colorbar pad", "number", 0.03, minimum=0.0, maximum=0.4, step=0.01, decimals=2, scope="style"),
        Option("colorbar_shrink", "Colorbar size", "number", 1.0, minimum=0.3, maximum=1.0, step=0.1, decimals=1, scope="style"),
        Option("row_label_fontsize", "Row label font (0=auto)", "number", 0, minimum=0, maximum=20, step=1, decimals=0, scope="style"),
        Option("col_label_fontsize", "Column label font (0=auto)", "number", 0, minimum=0, maximum=20, step=1, decimals=0, scope="style"),
        Option("y_label_pad", "Y-axis label padding", "number", 6.0, minimum=0.0, maximum=40.0, step=1.0, decimals=1, scope="style"),
    ],
    "volcano_plot": [
        Option("color_up", "Up-regulated colour", "choice", "#B2182B", _SIG_COLORS, scope="style"),
        Option("color_down", "Down-regulated colour", "choice", "#2166AC", _SIG_COLORS, scope="style"),
        Option("color_ns", "Not-significant colour", "choice", "#BBBBBB", _SIG_COLORS, scope="style"),
        Option("lfc_cutoff", "log2FC cutoff", "number", 1.0, minimum=0.0, maximum=20.0, step=0.5, decimals=2),
        Option("p_cutoff", "p-value / FDR cutoff", "number", 0.05, minimum=0.0, maximum=1.0, step=0.01, decimals=4),
        Option("use_fdr", "P column is FDR/adjusted (y-axis = −log10 FDR)", "bool", False),
        # v0.5 annotation controls
        Option("annotate", "Show labels", "bool", True, scope="style"),
        Option("label_mode", "Label mode", "choice", "top_fdr",
               ["top_fdr", "top_lfc", "top_up_down", "selected", "pasted", "significant_all"]),
        Option("top_n", "Top N labels", "number", 10, minimum=0, maximum=60, step=1, decimals=0),
        Option("top_n_up", "Top N up", "number", 8, minimum=0, maximum=40, step=1, decimals=0),
        Option("top_n_down", "Top N down", "number", 8, minimum=0, maximum=40, step=1, decimals=0),
        Option("label_by", "Label by", "choice", "symbol", ["symbol", "id", "both"]),
        Option("show_arrows", "Arrows to points", "bool", True, scope="style"),
        Option("label_box", "Label background box", "bool", False, scope="style"),
        # Duplicate-label handling (several rows/features may share a gene symbol).
        Option("duplicate_label_policy", "Duplicate labels", "choice", "all",
               ["all", "unique", "count"], scope="style"),
        Option("duplicate_label_representative_rule", "Representative point", "choice",
               "pvalue", ["pvalue", "padj", "effect", "statistic", "first"], scope="style"),
        Option("duplicate_label_show_count", "Append (n=…) count", "bool", False, scope="style"),
    ],
    "scatterplot_with_regression": [
        Option("fit_line", "Fit regression line", "bool", True),
        Option("show_fit_stats", "Show regression stats box", "bool", True, scope="style"),
        Option("show_slope", "  • slope", "bool", True, scope="style"),
        Option("show_r2", "  • R²", "bool", True, scope="style"),
        Option("show_p", "  • p-value", "bool", True, scope="style"),
        Option("show_r", "  • Pearson r", "bool", False, scope="style"),
        Option("show_intercept", "  • intercept", "bool", False, scope="style"),
        Option("show_n", "  • n", "bool", False, scope="style"),
        Option("show_equation", "  • full equation (y = a·x + b)", "bool", False, scope="style"),
        Option("fit_stats_loc", "Stats box location", "choice", "lower right",
               ["lower right", "lower left", "upper right", "upper left"], scope="style"),
    ],
    "boxplot_or_violin_with_points": [
        Option("kind", "Kind", "choice", "box", ["box", "violin"], scope="style"),
        Option("points", "Overlay points", "bool", True, scope="style"),
        _X_TICK_ROTATION,
    ],
    "lineplot_timecourse_with_error_band": [Option("error", "Error band", "choice", "sem", _BAND_CHOICES, scope="style")],
    "ridge_or_density_plot": [
        Option("density_mode", "Density mode", "choice", "ridge", ["ridge", "overlay"], scope="style"),
        Option("overlap", "Ridge overlap", "number", 0.7, minimum=0.0, maximum=0.95, step=0.05, decimals=2, scope="style"),
    ],
    # A histogram counts; the ridge/density plot above smooths. Both are offered because a kernel
    # density estimate can render two modes as one shoulder, and for a distribution that is not
    # unimodal that is a difference in the result, not the styling.
    "histogram_distribution": [
        # Which shape the table is in - declared rather than guessed, as for the survival curve.
        # "long" is one numeric column plus an optional group column; "wide" is one column per
        # group, which is what a spreadsheet of one column per condition already looks like.
        Option("input_form", "Input form", "choice", "long", ["long", "wide"]),
        Option("panel_mode", "Arrangement", "choice", "panels", ["panels", "overlay"], scope="style"),
        Option("draw_style", "Draw as", "choice", "bars", ["bars", "line", "both"], scope="style"),
        Option("normalize", "Y axis shows", "choice", "count",
               ["count", "frequency", "percent", "density"], scope="style"),
        Option("cumulative", "Cumulative", "bool", False, scope="style"),
        # 'bins' and 'bin_width' are two ways to say the same thing, so both default to unset and
        # the renderer refuses to resolve a conflict rather than picking a silent winner. The
        # minimums sit below any real value so a frontend that cannot show an empty numeric field
        # can use the minimum as its "(auto)" sentinel.
        Option("bins", "Number of bins", "number", None,
               minimum=-1.0, maximum=200.0, step=1, decimals=0),
        Option("bin_width", "Bin width", "number", None,
               minimum=-1.0, maximum=1e6, step=0.5, decimals=4),
        Option("show_mean", "Mark the mean", "bool", False, scope="style"),
        Option("show_median", "Mark the median", "bool", False, scope="style"),
        Option("bar_alpha", "Fill opacity", "number", None,
               minimum=-1.0, maximum=1.0, step=0.05, decimals=2, scope="style"),
        Option("log_y", "Logarithmic Y axis", "bool", False, scope="style"),
        Option("share_axes", "Panels share both axes", "bool", True, scope="style"),
        Option("x_min", "X-axis minimum", "number", None,
               minimum=-1e9, maximum=1e9, step=1.0, decimals=4),
        Option("x_max", "X-axis maximum", "number", None,
               minimum=-1e9, maximum=1e9, step=1.0, decimals=4),
        Option("y_min", "Y-axis minimum", "number", None,
               minimum=-1e9, maximum=1e9, step=1.0, decimals=4),
        Option("y_max", "Y-axis maximum", "number", None,
               minimum=-1e9, maximum=1e9, step=1.0, decimals=4),
        _X_TICK_ROTATION,
    ],
    "enrichment_dotplot": [
        Option("top_n", "Top N terms", "number", 20, minimum=5, maximum=40, step=1, decimals=0),
    ],
    "kaplan_meier_survival_curve": [
        Option("input_form", "Input form", "choice", "subject_level",
               ["subject_level", "precomputed"]),
        Option("y_scale", "Y-axis scale", "choice", "fraction", ["fraction", "percent"], scope="style"),
        # minimum is below the axis range on purpose: a frontend that cannot show an empty
        # numeric field uses the minimum as its "(auto)" sentinel, so keeping it outside 0-100
        # leaves every real value - including 0 - expressible.
        Option("reference_line", "Reference line (y-axis units, blank for none)", "number",
               None, minimum=-1.0, maximum=100.0, step=0.5, decimals=2, scope="style"),
        Option("curve_style", "Curve style (line: precomputed curves only)", "choice", "step",
               ["step", "line"], scope="style"),
        Option("y_ticks", "Y ticks", "choice", "auto", ["auto", "ends_and_midpoint"], scope="style"),
        Option("x_min", "X-axis minimum (blank for auto)", "number", None,
               minimum=-100000.0, maximum=100000.0, step=1.0, decimals=2),
        Option("x_max", "X-axis maximum (blank for auto)", "number", None,
               minimum=-100000.0, maximum=100000.0, step=1.0, decimals=2),
    ],
    "stacked_bar_composition": [_X_TICK_ROTATION],
    "waterfall_plot": [Option("sort", "Sort", "choice", "ascending", ["ascending", "descending"], scope="style")],
    "pca_scatter_from_matrix": [],
    "oncoprint_mutation_heatmap": [],
    "lollipop_mutation_plot": [
        Option("show_labels", "Show mutation labels", "bool", True, scope="style"),
        Option("label_top_n", "Label top N mutations", "number", 6, minimum=0, maximum=40, step=1, decimals=0),
        Option("legend_loc", "Legend position", "choice", "right", ["right", "bottom"], scope="style"),
        Option("marker_scale", "Marker scale", "number", 16.0, minimum=4.0, maximum=60.0, step=2.0, decimals=1, scope="style"),
        Option("y_margin", "Top y-margin", "number", 0.42, minimum=0.05, maximum=0.6, step=0.05, decimals=2, scope="style"),
        Option("label_font_size", "Label font size (0=auto)", "number", 0, minimum=0, maximum=20, step=1, decimals=0, scope="style"),
    ],
    "roc_curve": [],
    "forest_plot": [
        Option("reference", "Reference line", "number", 1.0, minimum=0.0, maximum=100.0, step=0.5, decimals=2, scope="style"),
        Option("log_scale", "Log x-axis", "bool", True, scope="style"),
    ],
    # --- v0.4 manuscript plot types ---
    "dot_strip_plot": [
        Option("summary", "Summary overlay", "choice", "mean", ["none", "mean", "median", "ci", "sd", "sem"], scope="style"),
        Option("jitter", "Jitter points", "bool", True, scope="style"),
        _X_TICK_ROTATION,
    ],
    "beeswarm_plot": [
        Option("summary", "Summary overlay", "choice", "mean", ["none", "mean", "median", "ci", "sd", "sem"], scope="style"),
        _X_TICK_ROTATION,
    ],
    "paired_slopegraph": [],
    "raincloud_plot": [_X_TICK_ROTATION],
    "hierarchical_dendrogram": [
        Option("method", "Linkage method", "choice", "average", ["average", "complete", "single", "ward"]),
        Option("cluster", "Cluster", "choice", "rows", ["rows", "columns"]),
        Option("orientation", "Orientation", "choice", "top", ["top", "left"], scope="style"),
    ],
    "ma_plot": [
        Option("color_ns", "Not-significant colour", "choice", "#B8B8B8", _SIG_COLORS, scope="style"),
        Option("p_cutoff", "Significance cutoff", "number", 0.05, minimum=0.0, maximum=1.0, step=0.01, decimals=4),
        Option("label_top_n", "Label top N hits", "number", 8, minimum=0, maximum=40, step=1, decimals=0),
        # Duplicate-label handling (shared with the volcano plot).
        Option("duplicate_label_policy", "Duplicate labels", "choice", "all",
               ["all", "unique", "count"], scope="style"),
        Option("duplicate_label_representative_rule", "Representative point", "choice",
               "pvalue", ["pvalue", "padj", "effect", "statistic", "first"], scope="style"),
        Option("duplicate_label_show_count", "Append (n=…) count", "bool", False, scope="style"),
    ],
    "manhattan_plot": [],
    "qq_plot": [Option("mode", "Mode", "choice", "pvalue", ["pvalue", "quantile"])],
    "bland_altman_plot": [Option("show_ci", "Shade 95% CI of bias", "bool", False, scope="style")],
    "precision_recall_curve": [],
    "confusion_matrix": [
        Option("normalize", "Normalize", "choice", "none", ["none", "row", "column", "total"], scope="style"),
    ],
    "calibration_plot": [
        Option("n_bins", "Number of bins", "number", 10, minimum=3, maximum=20, step=1, decimals=0),
    ],
    "dose_response_curve": [Option("fit", "Fit 4PL curve", "bool", True)],
    "upset_plot": [],
    "swimmer_plot": [],
    "spider_plot": [
        Option("reference", "Reference line (y)", "number", 0.0, minimum=-100.0, maximum=100.0, step=5.0, decimals=1, scope="style"),
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
        _HEATMAP_COLORMAP,
        _Y_LABEL_ROTATION,
        Option("cluster_legend_title", "Show cluster legend title", "bool", False, scope="style"),
        Option("show_dendrogram", "Show dendrogram tree", "bool", False, scope="style"),
        Option("max_features", "Max features (rows) for clustering", "number", 2000, minimum=50, maximum=50000, step=100, decimals=0),
        Option("colorbar_location", "Colorbar location", "choice", "right", ["right", "left", "top", "bottom"], scope="style"),
        Option("colorbar_pad", "Colorbar pad", "number", 0.03, minimum=0.0, maximum=0.4, step=0.01, decimals=2, scope="style"),
        Option("colorbar_shrink", "Colorbar size", "number", 1.0, minimum=0.3, maximum=1.0, step=0.1, decimals=1, scope="style"),
        Option("row_label_fontsize", "Row label font (0=auto)", "number", 0, minimum=0, maximum=20, step=1, decimals=0, scope="style"),
        Option("col_label_fontsize", "Column label font (0=auto)", "number", 0, minimum=0, maximum=20, step=1, decimals=0, scope="style"),
        Option("y_label_pad", "Y-axis label padding", "number", 6.0, minimum=0.0, maximum=40.0, step=1.0, decimals=1, scope="style"),
    ],
    "network_graph": [
        Option("layout", "Layout", "choice", "spring",
               ["spring", "kamada_kawai", "circular", "shell", "spectral", "multipartite", "fixed", "random"], scope="style"),
        Option("seed", "Layout seed", "number", 42, minimum=0, maximum=99999, step=1, decimals=0),
        # --- node color ---
        Option("color_by", "Color nodes by", "choice", "group", ["group", "value", "none"]),
        Option("node_color", "Node color (when 'none')", "choice", "(palette)", _NET_NODE_COLORS, scope="style"),
        Option("node_cmap", "Node colormap (when 'value')", "choice", "(default)",
               ["(default)", "viridis", "magma", "cividis", "coolwarm", "Greys"], scope="style"),
        # --- node size ---
        Option("size_by", "Size nodes by", "choice", "degree", ["degree", "value", "fixed"]),
        Option("node_size", "Fixed node size (when 'fixed')", "number", 300, minimum=20, maximum=2000, step=20, decimals=0, scope="style"),
        # --- edges ---
        Option("edge_color_by", "Color edges by category", "choice", "(auto)",
               ["(auto)", "none", "interaction_type", "edge_type", "pathway", "sign"]),
        Option("edge_color", "Edge color (single)", "choice", "#888888", _NET_EDGE_COLORS, scope="style"),
        Option("edge_color_positive", "Edge color +corr", "choice", "#B2182B", _NET_EDGE_COLORS + ["#B2182B"], scope="style"),
        Option("edge_color_negative", "Edge color -corr", "choice", "#2166AC", _NET_EDGE_COLORS + ["#2166AC"], scope="style"),
        Option("edge_width_by", "Edge width by", "choice", "weight", ["weight", "fixed"]),
        Option("edge_width", "Fixed edge width (when 'fixed')", "number", 1.5, minimum=0.2, maximum=8.0, step=0.2, decimals=1, scope="style"),
        # --- labels / legend ---
        Option("node_labels", "Show node labels", "bool", True, scope="style"),
        Option("label_color", "Label color", "choice", "#222222", ["#222222", "black", "#555555", "#2166AC", "#B2182B"], scope="style"),
        Option("label_font_size", "Label font size (0=auto)", "number", 0, minimum=0, maximum=24, step=1, decimals=0, scope="style"),
        Option("show_legend", "Show legend (grouped)", "bool", True, scope="style"),
        # --- filtering / structure ---
        Option("min_weight", "Min edge weight", "number", 0.0, minimum=0.0, maximum=100.0, step=0.1, decimals=2),
        Option("corr_cutoff", "|correlation| cutoff", "number", 0.3, minimum=0.0, maximum=1.0, step=0.05, decimals=2),
        Option("top_n_edges", "Top N edges (0=all)", "number", 0, minimum=0, maximum=5000, step=10, decimals=0),
        Option("min_degree", "Min node degree", "number", 0, minimum=0, maximum=100, step=1, decimals=0),
        Option("remove_isolates", "Remove isolated nodes", "bool", True),
        Option("detect_communities", "Detect communities (heuristic)", "bool", False),
    ],
    "manhattan_plot": [
        _X_TICK_ROTATION,
        Option("show_cutoff_line", "Genome-wide cutoff line", "bool", True, scope="style"),
        Option("genome_wide_threshold", "Cutoff threshold (p)", "number", 5e-8,
               minimum=0.0, maximum=1.0, step=1e-8, decimals=9),
        Option("cutoff_line_color", "Cutoff line color", "choice", "#C0392B",
               ["#C0392B", "#333333", "black", "#2166AC", "#1B7837"], scope="style"),
        Option("cutoff_line_style", "Cutoff line style", "choice", "--", ["--", "-", ":", "-."], scope="style"),
        Option("cutoff_line_width", "Cutoff line width", "number", 1.5, minimum=0.4, maximum=6.0, step=0.2, decimals=1, scope="style"),
        Option("show_suggestive_line", "Suggestive line", "bool", True, scope="style"),
    ],
    "paired_slopegraph": [
        Option("point_color", "Point color", "choice", "(group)",
               ["(group)", "#2166AC", "#B2182B", "#1B7837", "#333333", "black"], scope="style"),
        Option("line_color", "Line color", "choice", "(group)",
               ["(group)", "#BBBBBB", "#888888", "#2166AC", "#B2182B", "black"], scope="style"),
        Option("point_size", "Point size", "number", 6.0, minimum=2.0, maximum=20.0, step=1.0, decimals=1, scope="style"),
        Option("line_width", "Line width", "number", 1.5, minimum=0.4, maximum=6.0, step=0.2, decimals=1, scope="style"),
        Option("line_alpha", "Line alpha", "number", 0.7, minimum=0.1, maximum=1.0, step=0.1, decimals=1, scope="style"),
    ],
    "swimmer_plot": [
        Option("right_pad_frac", "Right-side headroom", "number", 0.06, minimum=0.0, maximum=0.4, step=0.02, decimals=2, scope="style"),
    ],
}


# Roles that take SEVERAL columns rather than one. A frontend must offer a multi-select for these;
# rendering them as a single-value picker silently limits the figure - a survival plot given one
# column of a three-group curve set draws one curve and looks finished.
MULTI_COLUMN_FIELDS = frozenset({
    "value_columns",      # matrix plots: the measurement columns
    "survival_columns",   # precomputed survival curves: one column of S(t) per group
})


def is_multi_column(field: str) -> bool:
    """True when a column role expects a list of columns."""
    return field in MULTI_COLUMN_FIELDS


def column_fields(plot_type: str) -> List[str]:
    return list(COLUMN_FIELDS.get(plot_type, []))


def options(plot_type: str) -> List[Option]:
    return list(OPTIONS.get(plot_type, []))
