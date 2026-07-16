"""Matrix workflow: map a feature-by-sample matrix, confirm groups, validate,
recommend plots + transformations, and compute generic feature-level statistics.

Generic feature-matrix layer (expression / protein / metabolite / any numeric
feature-by-sample matrix). NOT an RNA-seq pipeline: no raw-count differential
expression and no R. Precomputed differential tables
and normalized-matrix feature-level statistics are supported. Nothing is plotted
or analysed until the user confirms the column mapping and (for statistics) the
groups — no silent guessing.
"""

from make_my_figure_core.matrix_workflow.matrix_spec import (
    DUPLICATE_FEATURE_POLICIES,
    MISSING_VALUE_POLICIES,
    VALUE_TYPES,
    MatrixSpec,
    looks_log_scale,
    suggest_matrix_spec,
)
from make_my_figure_core.matrix_workflow.metadata_spec import (
    SampleMetadataSpec,
    metadata_from_assignment,
    metadata_sample_match,
    suggest_metadata_from_table,
)
from make_my_figure_core.matrix_workflow.validators import (
    ValidationReport,
    require_for_statistics,
    validate_matrix,
)
from make_my_figure_core.matrix_workflow.recommendations import (
    RecommendedPlot,
    recommend_from_differential_table,
    recommend_plots,
)
from make_my_figure_core.matrix_workflow.differential_summary import (
    CORRECTIONS,
    MULTI_GROUP_TESTS,
    TWO_GROUP_TESTS,
    DifferentialSummary,
    feature_differential_summary,
)
from make_my_figure_core.matrix_workflow.plot_builder import (
    PlotInputs,
    build_plot_inputs,
)
from make_my_figure_core.matrix_workflow.preprocessing_spec import (
    PreprocessingSpec,
    PreprocessingStep,
)
from make_my_figure_core.matrix_workflow.qc_diagnostics import (
    QCMetricSummary,
    diagnose_matrix,
)
from make_my_figure_core.matrix_workflow.transform_recommendations import (
    NormalizationRecommendation,
    PreprocessingWorkflow,
    normalization_catalog,
    recommend_preprocessing,
)
from make_my_figure_core.matrix_workflow.preprocessing import (
    apply_step,
    available_methods,
    run_preprocessing,
)
from make_my_figure_core.matrix_workflow import normalization, preprocessing, transformations

__all__ = [
    "MatrixSpec", "suggest_matrix_spec", "looks_log_scale",
    "VALUE_TYPES", "MISSING_VALUE_POLICIES", "DUPLICATE_FEATURE_POLICIES",
    "SampleMetadataSpec", "metadata_from_assignment", "suggest_metadata_from_table",
    "metadata_sample_match",
    "ValidationReport", "validate_matrix", "require_for_statistics",
    "RecommendedPlot", "recommend_plots", "recommend_from_differential_table",
    "DifferentialSummary", "feature_differential_summary",
    "TWO_GROUP_TESTS", "MULTI_GROUP_TESTS", "CORRECTIONS",
    "PlotInputs", "build_plot_inputs",
    # raw-like preprocessing / QC
    "PreprocessingSpec", "PreprocessingStep", "QCMetricSummary", "diagnose_matrix",
    "NormalizationRecommendation", "PreprocessingWorkflow", "recommend_preprocessing",
    "normalization_catalog", "apply_step", "run_preprocessing", "available_methods",
    "normalization", "preprocessing", "transformations",
]
