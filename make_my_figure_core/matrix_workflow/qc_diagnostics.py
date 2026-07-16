"""Diagnose the distribution/quality of a mapped feature matrix.

Runs on the confirmed value columns and reports evidence (skew, zeros, negatives,
sample-total differences, suspected data type, outliers). These are *suggestions*
only — the app never classifies with certainty and never transforms silently.
Pure numpy/scipy/pandas.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

from make_my_figure_core.matrix_workflow.matrix_spec import MatrixSpec


@dataclass
class QCMetricSummary:
    n_features: int = 0
    n_samples: int = 0
    missing_values: int = 0
    zero_fraction: float = 0.0
    negative_value_fraction: float = 0.0
    integer_like: bool = False
    min: float = 0.0
    max: float = 0.0
    mean: float = 0.0
    median: float = 0.0
    variance_summary: Dict[str, float] = field(default_factory=dict)
    skewness_summary: Dict[str, float] = field(default_factory=dict)
    library_size_or_column_sum_summary: Dict[str, float] = field(default_factory=dict)
    sample_total_summary: Dict[str, float] = field(default_factory=dict)
    sample_median_summary: Dict[str, float] = field(default_factory=dict)
    outlier_samples: List[str] = field(default_factory=list)
    outlier_features: List[str] = field(default_factory=list)
    suspected_data_type: str = "unknown"
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "QCMetricSummary":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (d or {}).items() if k in known})


def _summ(arr: np.ndarray) -> Dict[str, float]:
    a = arr[np.isfinite(arr)]
    if a.size == 0:
        return {"min": 0.0, "median": 0.0, "max": 0.0}
    return {"min": float(np.min(a)), "median": float(np.median(a)), "max": float(np.max(a))}


def diagnose_matrix(df: pd.DataFrame, matrix_spec: MatrixSpec,
                    *, mad_k: float = 3.5) -> QCMetricSummary:
    """Compute a QC summary for the confirmed value columns of ``df``."""
    frame = matrix_spec.feature_frame(df)           # features x samples (numeric)
    values = frame.to_numpy(dtype=float)
    feats = list(frame.index)
    samples = list(frame.columns)
    finite = values[np.isfinite(values)]
    n_feat, n_samp = values.shape if values.ndim == 2 else (0, 0)

    q = QCMetricSummary(n_features=int(n_feat), n_samples=int(n_samp))
    total = values.size or 1
    q.missing_values = int(np.isnan(values).sum())
    q.zero_fraction = float(np.sum(finite == 0) / total)
    q.negative_value_fraction = float(np.sum(finite < 0) / total)
    if finite.size:
        q.min, q.max = float(finite.min()), float(finite.max())
        q.mean, q.median = float(finite.mean()), float(np.median(finite))
        q.integer_like = bool(np.all(np.equal(np.mod(finite, 1), 0)))

    # per-feature variance + per-sample skew distributions
    with np.errstate(all="ignore"):
        feat_var = np.nanvar(values, axis=1)
        q.variance_summary = _summ(feat_var)
        col_sums = np.nansum(values, axis=0)
        q.library_size_or_column_sum_summary = _summ(col_sums)
        q.sample_total_summary = _summ(col_sums)
        col_med = np.nanmedian(np.where(np.isfinite(values), values, np.nan), axis=0)
        q.sample_median_summary = _summ(col_med)
        # overall + per-sample skew
        per_sample_skew = []
        for j in range(n_samp):
            cj = values[:, j]
            cj = cj[np.isfinite(cj)]
            if cj.size > 2 and np.std(cj) > 0:
                per_sample_skew.append(float(stats.skew(cj)))
        overall_skew = (float(stats.skew(finite)) if finite.size > 2 and np.std(finite) > 0
                        else 0.0)
        q.skewness_summary = {"overall": overall_skew,
                              "median_per_sample": float(np.median(per_sample_skew))
                              if per_sample_skew else overall_skew}

    # outlier samples: column total far from the median (robust MAD rule)
    if n_samp > 3 and np.isfinite(col_sums).any():
        med = np.median(col_sums)
        mad = np.median(np.abs(col_sums - med)) or 1.0
        for j, s in enumerate(samples):
            if abs(col_sums[j] - med) > mad_k * mad:
                q.outlier_samples.append(str(s))
    # outlier features: very high variance (top by robust rule)
    if n_feat > 10 and np.isfinite(feat_var).any():
        med = np.median(feat_var)
        mad = np.median(np.abs(feat_var - med)) or 1.0
        hi = [feats[i] for i in range(n_feat) if feat_var[i] - med > mad_k * mad]
        q.outlier_features = [str(f) for f in hi[:50]]

    q.suspected_data_type = _suspect_type(q)
    q.warnings = _warnings(q)
    return q


def _suspect_type(q: QCMetricSummary) -> str:
    skew = q.skewness_summary.get("overall", 0.0)
    dyn_range = (q.max - q.min)
    has_neg = q.negative_value_fraction > 0
    if has_neg and q.max < 40 and q.min > -40:
        return "log_like_or_normalized"          # centred-ish, includes negatives
    if not has_neg and q.integer_like and skew > 1.5 and q.max >= 100:
        return "count_like"
    if not has_neg and skew > 1.5 and dyn_range > 0:
        return "intensity_like_skewed"
    if not has_neg and abs(skew) < 1.0 and q.max < 40:
        return "possibly_log_or_normalized"
    return "unknown"


def _warnings(q: QCMetricSummary) -> List[str]:
    w: List[str] = []
    skew = q.skewness_summary.get("overall", 0.0)
    if skew > 1.5:
        w.append("Strongly right-skewed values — consider a log/arcsinh transform "
                 "(the choice depends on your data type).")
    if q.negative_value_fraction > 0:
        w.append("Negative values present — log transforms and ratio fold-change are "
                 "not valid without an explicit, justified offset.")
    if q.zero_fraction > 0.3:
        w.append(f"{q.zero_fraction:.0%} of values are zero — log pseudocount choice is "
                 "sensitive; consider filtering sparse features.")
    tot = q.sample_total_summary
    if tot.get("min", 0) > 0 and tot.get("max", 0) / max(tot["min"], 1e-9) > 3:
        w.append("Sample totals differ substantially — consider total-sum or median "
                 "scaling before comparing samples.")
    if q.missing_values:
        w.append(f"{q.missing_values} missing value(s) — choose an imputation or filtering "
                 "policy before some analyses.")
    if q.suspected_data_type == "count_like":
        w.append("Values look count-like (non-negative, integer, right-skewed).")
    elif q.suspected_data_type == "intensity_like_skewed":
        w.append("Values look intensity-like and skewed.")
    elif q.suspected_data_type in ("log_like_or_normalized", "possibly_log_or_normalized"):
        w.append("Values may already be log-transformed/normalized — avoid re-logging; "
                 "consider only centering/scaling.")
    return w
