"""Optional, opt-in Python-only count-model differential analysis.

This is NOT part of the default install, the default workflow, or the core test
suite. It is offered only for users with genuine **count-like, non-negative,
integer** matrices who want a negative-binomial count model WITHOUT R, via the
optional ``pip install -e ".[count-de]"`` extra (PyDESeq2 — pure Python, no R,
no rpy2). See ``docs/COUNT_MODEL_DE_INVESTIGATION.md`` for the decision, install
burden, and caveats.

If the extra is not installed, everything here degrades gracefully: callers get a
clear message pointing to the precomputed-table mode or the generic feature-level
differential summary. It is deliberately kept separate from — and clearly
distinguished from — the simple feature-level differential summary.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from make_my_figure_core.matrix_workflow.matrix_spec import MatrixSpec
from make_my_figure_core.matrix_workflow.metadata_spec import SampleMetadataSpec


@dataclass
class CountDESpec:
    method: str = "pydeseq2"
    package_version: str = ""
    source_matrix_id: Optional[str] = None
    group_a: str = ""
    group_b: str = ""
    design_factor: str = "condition"
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def count_model_available() -> bool:
    """True only if the optional 'count-de' extra (PyDESeq2) is importable."""
    try:
        import pydeseq2  # noqa: F401
        return True
    except Exception:
        return False


def validate_integer_counts(df: pd.DataFrame, matrix_spec: MatrixSpec) -> List[str]:
    """Return blocking problems if the matrix is not a non-negative integer count matrix."""
    frame = matrix_spec.feature_frame(df)
    m = frame.to_numpy(dtype=float)
    finite = m[np.isfinite(m)]
    problems: List[str] = []
    if finite.size == 0:
        return ["No numeric values in the selected value columns."]
    if finite.min() < 0:
        problems.append("Count models require non-negative values (negatives present).")
    if not np.all(np.equal(np.mod(finite, 1), 0)):
        problems.append("Count models require integer counts (non-integer values present).")
    if np.isnan(m).any():
        problems.append("Missing values present — impute or filter before a count model.")
    return problems


def count_model_differential(df: pd.DataFrame, matrix_spec: MatrixSpec,
                             metadata: SampleMetadataSpec, *, group_a: str,
                             group_b: str) -> "tuple[pd.DataFrame, CountDESpec]":
    """Run an optional PyDESeq2 negative-binomial analysis (opt-in extra).

    Raises ``RuntimeError`` with guidance if the extra is not installed, and
    ``ValueError`` if the matrix is not a valid integer count matrix. Returns a
    result table compatible with the volcano/MA renderers plus a ``CountDESpec``.
    """
    if not count_model_available():
        raise RuntimeError(
            "Optional count-model differential analysis needs the 'count-de' extra "
            "(PyDESeq2, pure Python — no R). Install: pip install -e \".[count-de]\". "
            "Otherwise use a precomputed differential table or the generic "
            "feature-level differential summary.")
    problems = validate_integer_counts(df, matrix_spec)
    if problems:
        raise ValueError("Not a valid count matrix: " + "; ".join(problems))

    import pydeseq2
    from pydeseq2.dds import DeseqDataSet
    from pydeseq2.ds import DeseqStats

    fid = matrix_spec.feature_id_column
    frame = matrix_spec.feature_frame(df)                    # features x samples
    samples = [s for s in metadata.samples_in_group(group_a) + metadata.samples_in_group(group_b)
               if s in frame.columns]
    counts = frame[samples].T.round().astype(int)            # samples x features (PyDESeq2 layout)
    counts.columns = df[fid].astype(str).tolist() if fid in df.columns else counts.columns
    meta = pd.DataFrame({"condition": [metadata.sample_to_group[s] for s in samples]},
                        index=samples)
    dds = DeseqDataSet(counts=counts, metadata=meta, design_factors="condition", quiet=True)
    dds.deseq2()
    stat = DeseqStats(dds, contrast=["condition", group_a, group_b], quiet=True)
    stat.summary()
    res = stat.results_df.reset_index().rename(columns={
        "index": "feature_id", "log2FoldChange": "log2_fold_change",
        "pvalue": "p_value", "padj": "adjusted_p_value", "baseMean": "average_abundance"})
    res["feature_label"] = res["feature_id"]
    res["test_name"] = "pydeseq2_negative_binomial"
    spec = CountDESpec(method="pydeseq2", package_version=getattr(pydeseq2, "__version__", ""),
                       source_matrix_id=matrix_spec.source_file, group_a=group_a, group_b=group_b,
                       warnings=["Optional count-model analysis (PyDESeq2). Distinct from the "
                                 "generic feature-level differential summary."])
    return res, spec
