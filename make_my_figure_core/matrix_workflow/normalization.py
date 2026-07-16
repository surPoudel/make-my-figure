"""Python-only normalization methods for a feature matrix.

Each function operates on the confirmed value columns of a DataFrame, returns a
NEW DataFrame (feature id + annotation columns preserved, value columns
normalized) plus a ``(params, warnings)`` record, and never mutates its input.
No R, no rpy2. Methods are not universally appropriate — callers surface the
suitability/risk text from the recommender.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from make_my_figure_core.matrix_workflow.matrix_spec import MatrixSpec

Result = Tuple[pd.DataFrame, Dict[str, Any], List[str]]


def _cols(df: pd.DataFrame, spec: MatrixSpec) -> List[str]:
    return [c for c in spec.value_columns if c in df.columns]


def _block(df: pd.DataFrame, cols: List[str]) -> np.ndarray:
    return df[cols].apply(lambda s: pd.to_numeric(s, errors="coerce")).to_numpy(dtype=float)


def _apply(df: pd.DataFrame, cols: List[str], new: np.ndarray) -> pd.DataFrame:
    out = df.copy()
    out[cols] = new
    return out


# --- library-size / scaling normalizations ---------------------------------
def total_sum(df: pd.DataFrame, spec: MatrixSpec, *, scale_factor: float = 1e6) -> Result:
    cols = _cols(df, spec)
    m = _block(df, cols)
    warns: List[str] = []
    if np.nanmin(m) < 0:
        warns.append("Negative values present — total-sum normalization assumes non-negative signal.")
    totals = np.nansum(m, axis=0)
    totals[totals == 0] = np.nan
    new = m / totals * float(scale_factor)
    return _apply(df, cols, new), {"scale_factor": float(scale_factor)}, warns


def median_scale(df: pd.DataFrame, spec: MatrixSpec) -> Result:
    cols = _cols(df, spec)
    m = _block(df, cols)
    med = np.nanmedian(np.where(np.isfinite(m), m, np.nan), axis=0)
    grand = np.nanmedian(med) or 1.0
    factors = np.where(med == 0, np.nan, med / grand)
    new = m / factors
    return _apply(df, cols, new), {"target": "grand_median"}, []


def upper_quartile(df: pd.DataFrame, spec: MatrixSpec) -> Result:
    cols = _cols(df, spec)
    m = _block(df, cols)
    warns = ["Negative values present — upper-quartile assumes non-negative signal."] if np.nanmin(m) < 0 else []
    uq = np.nanpercentile(np.where(np.isfinite(m), m, np.nan), 75, axis=0)
    grand = np.nanmedian(uq) or 1.0
    factors = np.where(uq == 0, np.nan, uq / grand)
    new = m / factors
    return _apply(df, cols, new), {"quantile": 0.75}, warns


def quantile_normalize(df: pd.DataFrame, spec: MatrixSpec) -> Result:
    """Force every sample to share the same value distribution (rank-based)."""
    cols = _cols(df, spec)
    m = _block(df, cols)
    # mean of sorted values across samples = the common reference distribution
    order = np.argsort(m, axis=0)
    ranks = np.argsort(order, axis=0)
    sorted_vals = np.sort(m, axis=0)
    ref = np.nanmean(sorted_vals, axis=1)
    new = np.empty_like(m)
    for j in range(m.shape[1]):
        new[:, j] = ref[ranks[:, j]]
    warns = ["Quantile normalization forces all samples to the same distribution — "
             "inappropriate when global distribution shifts are biologically real."]
    return _apply(df, cols, new), {}, warns


# --- z-score / standardization ----------------------------------------------
def zscore(df: pd.DataFrame, spec: MatrixSpec, *, axis: str = "row", ddof: int = 0) -> Result:
    cols = _cols(df, spec)
    m = _block(df, cols)
    if axis == "column":
        mu = np.nanmean(m, axis=0, keepdims=True); sd = np.nanstd(m, axis=0, ddof=ddof, keepdims=True)
    elif axis == "global":
        mu = np.nanmean(m); sd = np.nanstd(m, ddof=ddof)
    else:
        axis = "row"
        mu = np.nanmean(m, axis=1, keepdims=True); sd = np.nanstd(m, axis=1, ddof=ddof, keepdims=True)
    sd_safe = np.where((sd == 0) | ~np.isfinite(sd), 1.0, sd)
    new = (m - mu) / sd_safe
    return _apply(df, cols, new), {"axis": axis, "ddof": ddof}, []


def robust_scale(df: pd.DataFrame, spec: MatrixSpec) -> Result:
    """Per-column median/IQR scaling (robust to outliers)."""
    cols = _cols(df, spec)
    m = _block(df, cols)
    med = np.nanmedian(np.where(np.isfinite(m), m, np.nan), axis=0, keepdims=True)
    q1 = np.nanpercentile(np.where(np.isfinite(m), m, np.nan), 25, axis=0, keepdims=True)
    q3 = np.nanpercentile(np.where(np.isfinite(m), m, np.nan), 75, axis=0, keepdims=True)
    iqr = np.where((q3 - q1) == 0, 1.0, q3 - q1)
    new = (m - med) / iqr
    return _apply(df, cols, new), {"scaler": "robust", "units": "changed"}, \
        ["Robust scaling changes units (median-centred / IQR-scaled per sample)."]


def standard_scale(df: pd.DataFrame, spec: MatrixSpec, *, ddof: int = 0) -> Result:
    """Per-column mean 0 / unit variance (StandardScaler-equivalent)."""
    return zscore(df, spec, axis="column", ddof=ddof)


def center(df: pd.DataFrame, spec: MatrixSpec, *, mode: str = "sample_median") -> Result:
    cols = _cols(df, spec)
    m = _block(df, cols)
    if mode == "feature_mean":
        new = m - np.nanmean(m, axis=1, keepdims=True)
    elif mode == "feature_median":
        new = m - np.nanmedian(np.where(np.isfinite(m), m, np.nan), axis=1, keepdims=True)
    elif mode == "grand_median":
        new = m - np.nanmedian(m)
    else:
        mode = "sample_median"
        new = m - np.nanmedian(np.where(np.isfinite(m), m, np.nan), axis=0, keepdims=True)
    return _apply(df, cols, new), {"mode": mode}, []


# --- internal-standard / control-feature / reference normalizations ---------
def _row_mask(df: pd.DataFrame, spec: MatrixSpec, feature_ids: List[str]) -> np.ndarray:
    fid = spec.feature_id_column
    ids = {str(x) for x in (feature_ids or [])}
    if fid and fid in df.columns:
        return df[fid].astype(str).isin(ids).to_numpy()
    return np.zeros(len(df), dtype=bool)


def _normalize_by_factor(df, cols, m, factor, operation, warns):
    factor = np.where((factor == 0) | ~np.isfinite(factor), np.nan, factor)
    if operation == "subtract":
        new = m - factor
    else:                                   # divide / ratio
        new = m / factor
    return _apply(df, cols, new), warns


def internal_standard_features(df: pd.DataFrame, spec: MatrixSpec, *, feature_ids: List[str],
                               how: str = "median", operation: str = "divide") -> Result:
    """Normalize each sample by the signal of user-identified internal-standard
    feature rows (per-sample mean/median of those rows). Reports IS stability."""
    cols = _cols(df, spec)
    m = _block(df, cols)
    mask = _row_mask(df, spec, feature_ids)
    warns: List[str] = []
    if not mask.any():
        raise ValueError("No internal-standard features matched the selected feature ids.")
    is_block = m[mask, :]
    factor = (np.nanmedian(is_block, axis=0) if how == "median" else np.nanmean(is_block, axis=0))
    # stability: coefficient of variation of the per-sample IS factor
    cv = float(np.nanstd(factor) / (np.nanmean(factor) or np.nan)) if np.isfinite(factor).any() else np.nan
    if np.isfinite(cv) and cv > 0.5:
        warns.append(f"Internal-standard signal is unstable across samples (CV={cv:.0%}).")
    out, warns = _normalize_by_factor(df, cols, m, factor, operation, warns)
    return out, {"feature_ids": list(feature_ids), "how": how, "operation": operation,
                 "is_stability_cv": cv}, warns


def control_features(df: pd.DataFrame, spec: MatrixSpec, *, feature_ids: List[str],
                     how: str = "median", operation: str = "divide") -> Result:
    """Normalize by control/housekeeping features (same mechanism as IS features)."""
    out, params, warns = internal_standard_features(df, spec, feature_ids=feature_ids,
                                                    how=how, operation=operation)
    params["role"] = "control_features"
    return out, params, warns


def internal_standard_columns(df: pd.DataFrame, spec: MatrixSpec, *, is_columns: List[str],
                              how: str = "median", operation: str = "divide") -> Result:
    """Normalize value columns by mapped internal-standard measurement column(s):
    a per-feature IS reference (row-wise mean/median across the IS columns) divides
    (or subtracts, if log-scale) each value cell."""
    cols = _cols(df, spec)
    is_cols = [c for c in (is_columns or []) if c in df.columns]
    if not is_cols:
        raise ValueError("No internal-standard columns matched the selection.")
    m = _block(df, cols)
    isb = df[is_cols].apply(lambda s: pd.to_numeric(s, errors="coerce")).to_numpy(dtype=float)
    ref = (np.nanmedian(isb, axis=1) if how == "median" else np.nanmean(isb, axis=1))
    ref = ref.reshape(-1, 1)
    ref = np.where((ref == 0) | ~np.isfinite(ref), np.nan, ref)
    new = (m - ref) if operation == "subtract" else (m / ref)
    return _apply(df, cols, new), {"is_columns": is_cols, "how": how, "operation": operation}, []


def reference_sample(df: pd.DataFrame, spec: MatrixSpec, *, reference: str,
                     metadata=None, operation: str = "divide") -> Result:
    """Express each sample relative to a reference sample (or group mean)."""
    cols = _cols(df, spec)
    m = _block(df, cols)
    if reference in cols:
        ref = m[:, cols.index(reference)].reshape(-1, 1)
        label = f"sample '{reference}'"
    elif metadata is not None and reference in metadata.groups():
        grp_cols = [c for c in metadata.samples_in_group(reference) if c in cols]
        ref = np.nanmean(m[:, [cols.index(c) for c in grp_cols]], axis=1).reshape(-1, 1)
        label = f"group '{reference}'"
    else:
        raise ValueError(f"Reference '{reference}' is not a value column or a group.")
    ref = np.where((ref == 0) | ~np.isfinite(ref), np.nan, ref)
    new = (m - ref) if operation == "subtract" else (m / ref)
    return _apply(df, cols, new), {"reference": label, "operation": operation}, []
