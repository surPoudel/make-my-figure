"""Recommend preprocessing workflows from QC diagnostics — as suggestions only.

Each recommendation explains when a method is suitable or risky; the app never
applies anything without user confirmation. Pure python (uses the QCMetricSummary).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from make_my_figure_core.matrix_workflow.qc_diagnostics import QCMetricSummary


@dataclass
class NormalizationRecommendation:
    method: str
    reason: str
    required_assumptions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    suitable_for: str = ""
    not_suitable_for: str = ""
    requires_positive_values: bool = False
    requires_internal_standard_column: bool = False
    requires_metadata: bool = False
    output_scale: str = ""
    recommended_yes_no: bool = True
    user_confirmed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PreprocessingWorkflow:
    """A named ordered chain of steps the user can preview / apply / save."""
    name: str
    steps: List[Dict[str, Any]]           # [{'method':..., 'params':{...}}]
    reason: str
    assumptions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    expected_plots: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def recommend_preprocessing(qc: QCMetricSummary) -> List[PreprocessingWorkflow]:
    """Return candidate preprocessing workflows ranked most-relevant first."""
    recs: List[PreprocessingWorkflow] = []
    skew = qc.skewness_summary.get("overall", 0.0)
    has_neg = qc.negative_value_fraction > 0
    tot = qc.sample_total_summary
    totals_differ = tot.get("min", 0) > 0 and tot.get("max", 0) / max(tot["min"], 1e-9) > 3
    many_zeros = qc.zero_fraction > 0.3
    dtype = qc.suspected_data_type

    if dtype in ("log_like_or_normalized", "possibly_log_or_normalized"):
        recs.append(PreprocessingWorkflow(
            "Center/scale only (looks already log/normalized)",
            [{"method": "row_zscore", "params": {}}],
            "Values look already log-transformed or normalized — do NOT log again.",
            assumptions=["Data are already on a comparable scale."],
            expected_plots=["clustered heatmap", "PCA"]))
        return recs + _always(qc)

    if totals_differ and not has_neg:
        recs.append(PreprocessingWorkflow(
            "Total-sum normalize -> log2 -> z-score",
            [{"method": "total_sum", "params": {"scale_factor": 1e6}},
             {"method": "log2", "params": {"pseudocount": 1.0}},
             {"method": "row_zscore", "params": {}}],
            "Sample totals differ substantially and values are non-negative/skewed.",
            assumptions=["Non-negative signal; total signal is comparable across samples."],
            warnings=(["Many zeros — pseudocount choice is sensitive."] if many_zeros else []),
            expected_plots=["clustered heatmap", "PCA", "sample correlation"]))
        recs.append(PreprocessingWorkflow(
            "Median-scale -> log2",
            [{"method": "median_scale", "params": {}}, {"method": "log2", "params": {"pseudocount": 1.0}}],
            "Robust alternative to total-sum when a few features dominate totals.",
            assumptions=["Most features are not differentially abundant."],
            expected_plots=["clustered heatmap", "PCA"]))

    if skew > 1.5 and not has_neg:
        recs.append(PreprocessingWorkflow(
            "log2(x + 1) -> z-score",
            [{"method": "log2", "params": {"pseudocount": 1.0}}, {"method": "row_zscore", "params": {}}],
            "Strong right skew with non-negative values.",
            assumptions=["Non-negative values; a small pseudocount is acceptable."],
            warnings=(["Many zeros — consider filtering sparse features first."] if many_zeros else []),
            expected_plots=["clustered heatmap", "PCA", "selected-feature box/violin"]))
        recs.append(PreprocessingWorkflow(
            "arcsinh (intensity-like) -> z-score",
            [{"method": "arcsinh", "params": {"cofactor": 5.0}}, {"method": "row_zscore", "params": {}}],
            "Intensity-like skewed data; arcsinh handles zeros without a pseudocount.",
            assumptions=["Cofactor chosen for your instrument/scale."],
            expected_plots=["clustered heatmap", "PCA"]))

    if many_zeros:
        recs.append(PreprocessingWorkflow(
            "Filter sparse features -> log2",
            [{"method": "filter", "params": {"max_zero_frac": 0.5, "drop_constant": True}},
             {"method": "log2", "params": {"pseudocount": 1.0}}],
            "High zero fraction — filter sparse/constant features before transforming.",
            assumptions=["Sparse features are not of primary interest."],
            expected_plots=["heatmap", "PCA"]))

    if has_neg:
        recs.append(PreprocessingWorkflow(
            "Z-score for visualization only (negatives present)",
            [{"method": "row_zscore", "params": {}}],
            "Negative values present — do NOT log or use ratio fold-change; "
            "z-score/centering are for visualization only.",
            assumptions=["Downstream stats use mean difference, not ratio fold change."],
            expected_plots=["clustered heatmap", "PCA"]))

    return recs + _always(qc)


def _always(qc: QCMetricSummary) -> List[PreprocessingWorkflow]:
    """Options always offered (with caveats)."""
    return [
        PreprocessingWorkflow(
            "Internal-standard normalization (if you have IS features/columns)",
            [{"method": "internal_standard_features",
              "params": {"feature_ids": [], "how": "median", "operation": "divide"}}],
            "Normalize each sample to spiked internal-standard features (you select them).",
            assumptions=["Internal standards are stable across samples."],
            warnings=["Requires you to identify the internal-standard features/columns."],
            expected_plots=["selected-feature box/violin", "heatmap"]),
        PreprocessingWorkflow(
            "Quantile normalization (forces identical distributions)",
            [{"method": "quantile", "params": {}}],
            "Aggressively removes distribution differences between samples.",
            assumptions=["Global distribution shifts are technical, not biological."],
            warnings=["Inappropriate when distribution shifts are biologically real."],
            expected_plots=["clustered heatmap", "PCA"]),
    ]


def normalization_catalog() -> List[NormalizationRecommendation]:
    """Static catalog describing each normalization method (for the UI / docs)."""
    C = NormalizationRecommendation
    return [
        C("total_sum", "Divide each sample by its total signal, then rescale.",
          ["Non-negative signal", "Comparable total signal per sample"],
          ["Distorted if a few features dominate totals"],
          "count-like data with comparable library sizes", "data with dominant features",
          requires_positive_values=True, output_scale="relative abundance"),
        C("median_scale", "Scale samples so their medians match.",
          ["Most features not differentially abundant"], ["Breaks if >50% features change"],
          "robust size correction", "very small feature sets", output_scale="scaled signal"),
        C("upper_quartile", "Scale by the 75th percentile.",
          ["Non-negative signal"], ["Sensitive to sparsity"],
          "data where a few features dominate totals", "very sparse data",
          requires_positive_values=True, output_scale="scaled signal"),
        C("quantile", "Force all samples to the same distribution.",
          ["Distribution differences are technical"], ["Erases real global shifts"],
          "removing technical distribution differences", "biologically shifted distributions",
          output_scale="ranked/matched"),
        C("row_zscore", "Standardize each feature (mean 0, unit variance).", [],
          ["Loses absolute magnitude"], "heatmap contrast across features",
          "comparing absolute levels", output_scale="z-score"),
        C("internal_standard_features", "Normalize each sample by internal-standard features.",
          ["Internal standards are stable"], ["Unstable IS propagates error"],
          "targeted assays with spike-ins", "data without internal standards",
          requires_metadata=False, output_scale="ratio to internal standard"),
    ]
