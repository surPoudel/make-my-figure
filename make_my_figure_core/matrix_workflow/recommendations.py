"""Plot recommendations for a confirmed feature matrix (+ optional metadata).

Given a confirmed MatrixSpec and (optionally) a confirmed SampleMetadataSpec and
whether a differential summary exists, return a ranked list of RecommendedPlot
entries with a readiness status and the transformations each needs. Nothing is
auto-generated — the UI shows these and the user picks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from make_my_figure_core.matrix_workflow.matrix_spec import MatrixSpec
from make_my_figure_core.matrix_workflow.metadata_spec import SampleMetadataSpec

# readiness_status values
READY = "ready"
NEEDS_FEATURE = "needs_feature_selection"
NEEDS_GROUP = "needs_group_selection"
NEEDS_TRANSFORM = "needs_transformation"
UNAVAILABLE = "unavailable"


@dataclass
class RecommendedPlot:
    plot_type: str
    label: str
    reason: str
    required_data_shape: str = "matrix"
    required_transformations: List[str] = field(default_factory=list)
    required_user_inputs: List[str] = field(default_factory=list)
    readiness_status: str = READY
    scientific_warnings: List[str] = field(default_factory=list)
    visual_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def recommend_plots(matrix_spec: MatrixSpec,
                    metadata: Optional[SampleMetadataSpec] = None,
                    *, has_differential_summary: bool = False,
                    n_features: Optional[int] = None) -> List[RecommendedPlot]:
    """Return recommended plots ordered ready-first. See module docstring."""
    recs: List[RecommendedPlot] = []
    confirmed = bool(matrix_spec.confirmed_by_user and matrix_spec.value_columns)
    n_val = len(matrix_spec.value_columns)
    has_groups = bool(metadata and metadata.confirmed_by_user
                      and len([g for g, n in metadata.group_sizes().items() if n >= 1]) >= 2)
    big = bool(n_features and n_features > 200)

    def add(plot_type, label, reason, *, transforms=None, inputs=None,
            status=READY, sci=None, vis=None, shape="matrix"):
        recs.append(RecommendedPlot(plot_type, label, reason,
                    required_data_shape=shape,
                    required_transformations=transforms or [],
                    required_user_inputs=inputs or [], readiness_status=status,
                    scientific_warnings=sci or [], visual_warnings=vis or []))

    matrix_status = READY if confirmed else NEEDS_FEATURE

    # --- always possible after matrix confirmation ---
    add("heatmap_clustered_matrix", "Heatmap", "Visualize the whole value matrix.",
        status=matrix_status,
        vis=(["Large matrix — defaults to top-variable features for legibility."] if big else []))
    add("heatmap_clustered_matrix", "Clustered heatmap (row z-score)",
        "Cluster features/samples on standardized values.",
        transforms=["row_zscore"], status=matrix_status)
    add("hierarchical_clustering", "Hierarchical clustering", "Cluster and reorder the matrix.",
        status=matrix_status)
    add("hierarchical_dendrogram", "Dendrogram", "Sample/feature clustering tree.",
        status=matrix_status)
    add("heatmap_clustered_matrix", "Sample correlation heatmap",
        "Sample-by-sample correlation structure / QC.",
        transforms=["sample_correlation"], status=matrix_status)
    add("pca_scatter_from_matrix", "PCA scatter", "Sample structure in low dimensions.",
        transforms=["pca"], status=matrix_status,
        sci=(["Need >= 3 samples for a meaningful PCA."] if n_val and n_val < 3 else []))
    if not big:
        add("heatmap_clustered_matrix", "Feature correlation heatmap",
            "Feature-feature correlation (manageable feature count).",
            transforms=["feature_correlation"], status=matrix_status)
    add("hierarchical_clustering", "Top variable-feature heatmap",
        "Most variable features only — good for large matrices.",
        transforms=["top_variable_features", "row_zscore"], status=matrix_status)

    # --- group-based (need confirmed groups) ---
    group_status = READY if has_groups else NEEDS_GROUP
    for pt, label in (("boxplot_or_violin_with_points", "Selected-feature box/violin by group"),
                      ("dot_strip_plot", "Selected-feature dot/strip by group"),
                      ("raincloud_plot", "Selected-feature raincloud by group"),
                      ("barplot_with_error_bar", "Selected-feature bar (mean +/- error) by group")):
        add(pt, label, "Compare chosen features across groups.",
            transforms=["wide_to_long"], inputs=["select feature(s)"],
            status=group_status, shape="long")
    add("pca_scatter_from_matrix", "PCA colored by group", "Sample structure colored by condition.",
        transforms=["pca"], status=group_status)

    # --- differential-summary plots ---
    diff_status = READY if has_differential_summary else (
        NEEDS_TRANSFORM if has_groups else NEEDS_GROUP)
    for pt, label, reason in (
        ("volcano_plot", "Volcano", "Effect vs significance from a differential summary."),
        ("ma_plot", "MA plot", "Effect vs mean abundance from a differential summary."),
        ("lollipop_mutation_plot", "Ranked effect (lollipop)", "Top features by effect size."),
    ):
        add(pt, label, reason,
            transforms=[] if has_differential_summary else ["feature_differential_summary"],
            inputs=(["group A", "group B", "confirm value scale"] if not has_differential_summary else []),
            status=diff_status, shape="differential_table")

    # rank ready-first, keep insertion order within a status
    order = {READY: 0, NEEDS_FEATURE: 1, NEEDS_GROUP: 2, NEEDS_TRANSFORM: 3, UNAVAILABLE: 4}
    recs.sort(key=lambda r: order.get(r.readiness_status, 9))
    return recs


def recommend_from_differential_table(has_average_abundance: bool = False,
                                      has_matrix: bool = False) -> List[RecommendedPlot]:
    """Recommendations when the user supplied a PRECOMPUTED differential table."""
    recs: List[RecommendedPlot] = []
    recs.append(RecommendedPlot("volcano_plot", "Volcano",
                "Effect vs significance from your precomputed table.",
                required_data_shape="differential_table"))
    if has_average_abundance:
        recs.append(RecommendedPlot("ma_plot", "MA plot",
                    "Effect vs average abundance.", required_data_shape="differential_table"))
    recs.append(RecommendedPlot("lollipop_mutation_plot", "Ranked effect (lollipop)",
                "Top features by effect.", required_data_shape="differential_table"))
    if has_matrix:
        recs.append(RecommendedPlot("heatmap_clustered_matrix", "Top-feature heatmap",
                    "Heatmap of the top differential features from the matrix.",
                    required_data_shape="matrix", required_transformations=["top_variable_features"]))
    return recs
