"""RNA-seq analysis workflow for Make My Figure.

Three input modes are supported (see :mod:`detect`):

* **Mode A - precomputed DE result table** (e.g. a limma/edgeR ``topTable``):
  auto-detect logFC / p-value / adj-p / statistic / gene columns and draw a
  publication-grade volcano plot. No statistics are recomputed.
* **Mode B - normalized expression matrix** (e.g. a voom-normalized matrix):
  gene metadata columns + sample columns, used for heatmaps / PCA / sample
  correlation / gene-level plots.
* **Mode C - raw counts + sample metadata (+ optional config)**: validated and
  handed to a reproducible **edgeR + limma-voom (empirical Bayes)** DE pipeline
  run through R. If R or the required Bioconductor packages are missing, the app
  reports exactly what to install and does **not** fall back to a t-test.

Nothing is faked: a p-value shown on a volcano comes from the uploaded DE table
or from the R pipeline, never from an ad-hoc recomputation.
"""

from make_my_figure_core.rnaseq.detect import (
    RNASEQ_COLUMN_ALIASES,
    detect_input_mode,
    detect_de_columns,
    load_rnaseq_table,
    split_expression_matrix,
)
from make_my_figure_core.rnaseq.de_table import (
    DEResult,
    classify_de,
    parse_de_table,
    volcano_spec_from_de,
)
from make_my_figure_core.rnaseq.expression import (
    ExpressionMatrix,
    build_expression_matrix,
    heatmap_spec_from_expression,
    select_genes,
    transform_matrix,
)
from make_my_figure_core.rnaseq.spec import RnaSeqSpec, method_report_markdown
from make_my_figure_core.rnaseq.config import parse_rnaseq_config
from make_my_figure_core.rnaseq.validate import validate_counts, validate_metadata
from make_my_figure_core.rnaseq.runner import (
    RDependencyError,
    check_r_environment,
    run_de_pipeline,
)
from make_my_figure_core.rnaseq.r_setup import (
    app_data_dir,
    install_r_environment,
    managed_rscript_path,
    r_env_prefix,
)

__all__ = [
    "RNASEQ_COLUMN_ALIASES",
    "detect_input_mode",
    "detect_de_columns",
    "load_rnaseq_table",
    "split_expression_matrix",
    "DEResult",
    "classify_de",
    "parse_de_table",
    "volcano_spec_from_de",
    "ExpressionMatrix",
    "build_expression_matrix",
    "heatmap_spec_from_expression",
    "select_genes",
    "transform_matrix",
    "RnaSeqSpec",
    "method_report_markdown",
    "parse_rnaseq_config",
    "validate_counts",
    "validate_metadata",
    "RDependencyError",
    "check_r_environment",
    "run_de_pipeline",
    "app_data_dir",
    "install_r_environment",
    "managed_rscript_path",
    "r_env_prefix",
]
