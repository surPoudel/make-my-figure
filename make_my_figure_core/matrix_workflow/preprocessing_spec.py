"""Reproducible specs for preprocessing a raw-like / unnormalized feature matrix.

Nothing is transformed silently: each step the user confirms is recorded as a
``PreprocessingStep``, and the ordered chain that produced a derived matrix is a
``PreprocessingSpec``. The original matrix is never mutated. Frontend-agnostic,
pure pandas/numpy. Generic feature-matrix language only (no RNA-seq branding, no R).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, List, Optional

from make_my_figure_core.version import __version__


@dataclass
class PreprocessingStep:
    """One confirmed preprocessing operation (transform or normalization)."""

    step_id: str
    step_type: str                      # "transform" | "normalization" | "filter" | "impute"
    method_name: str                    # e.g. "log2", "total_sum", "internal_standard_features"
    parameters: Dict[str, Any] = field(default_factory=dict)
    input_matrix_id: Optional[str] = None
    output_matrix_id: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    qc_before: Optional[Dict[str, Any]] = None
    qc_after: Optional[Dict[str, Any]] = None
    user_confirmed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PreprocessingStep":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (d or {}).items() if k in known})


@dataclass
class PreprocessingSpec:
    """The ordered chain of steps that produced a derived (processed) matrix."""

    source_matrix_id: Optional[str] = None
    output_matrix_id: Optional[str] = None
    input_file: Optional[str] = None
    input_shape: Optional[List[int]] = None
    feature_id_column: Optional[str] = None
    value_columns: List[str] = field(default_factory=list)
    metadata_spec_id: Optional[str] = None
    preprocessing_steps: List[PreprocessingStep] = field(default_factory=list)
    user_confirmed: bool = False
    created_at: Optional[str] = None
    app_version: str = __version__
    warnings: List[str] = field(default_factory=list)
    method_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["preprocessing_steps"] = [s.to_dict() if isinstance(s, PreprocessingStep) else s
                                    for s in self.preprocessing_steps]
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PreprocessingSpec":
        d = dict(d or {})
        steps = [PreprocessingStep.from_dict(s) for s in d.get("preprocessing_steps", [])]
        known = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in d.items() if k in known}
        kwargs["preprocessing_steps"] = steps
        return cls(**kwargs)

    def add_step(self, step: PreprocessingStep) -> None:
        self.preprocessing_steps.append(step)
        self.method_summary = self.method_sentence()
        for w in step.warnings:
            if w not in self.warnings:
                self.warnings.append(w)

    def method_sentence(self) -> str:
        """A human-readable summary of the applied chain (for method reporting)."""
        if not self.preprocessing_steps:
            return "No preprocessing applied (raw matrix used as-is)."
        parts = [_step_phrase(s) for s in self.preprocessing_steps]
        return "Values were " + ", then ".join(parts) + "."


# --- readable phrasing for method sentences ---------------------------------
_METHOD_PHRASES = {
    "log2": "log2(x + {pseudocount}) transformed",
    "log": "ln(x + {pseudocount}) transformed",
    "ln": "ln(x + {pseudocount}) transformed",
    "log10": "log10(x + {pseudocount}) transformed",
    "arcsinh": "arcsinh(x / {cofactor}) transformed",
    "sqrt": "square-root transformed",
    "winsorize": "winsorized to the [{lower}, {upper}] percentile range",
    "total_sum": "total-sum (library-size) normalized to {scale_factor}",
    "median_scale": "median-scaled across samples",
    "upper_quartile": "upper-quartile normalized",
    "quantile": "quantile normalized",
    "row_zscore": "row (feature) z-scored",
    "column_zscore": "column (sample) z-scored",
    "global_zscore": "globally z-scored",
    "robust_scale": "robust-scaled (median/IQR) per column",
    "standard_scale": "standardized (mean 0 / unit variance) per column",
    "center_sample_median": "sample-median centred",
    "center_feature_mean": "feature-mean centred",
    "internal_standard_features": "normalized to the internal-standard features ({how})",
    "internal_standard_columns": "normalized to the mapped internal-standard column(s) ({how})",
    "control_features": "normalized to the control/housekeeping features ({how})",
    "reference_sample": "expressed relative to the reference {reference}",
    "impute": "missing values imputed by {strategy}",
    "filter": "filtered ({summary})",
}


def _step_phrase(step: PreprocessingStep) -> str:
    tmpl = _METHOD_PHRASES.get(step.method_name)
    if not tmpl:
        return step.method_name.replace("_", " ")
    try:
        return tmpl.format(**{**{"pseudocount": 1, "cofactor": 5, "lower": 1, "upper": 99,
                                 "scale_factor": "1e6", "how": "median", "strategy": "median",
                                 "reference": "sample", "summary": ""}, **step.parameters})
    except Exception:  # noqa: BLE001
        return step.method_name.replace("_", " ")
