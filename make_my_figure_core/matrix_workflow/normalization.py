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


def robust_scale(df: pd.DataFrame, spec: MatrixSpec, *, axis: str = "column") -> Result:
    """Median/IQR scaling (robust to outliers) along ``axis``.

    ``axis``: ``row`` (per feature — the usual choice for proteomics/transcriptomics),
    ``column`` (per sample), or ``global`` (whole matrix)."""
    cols = _cols(df, spec)
    m = np.where(np.isfinite(_block(df, cols)), _block(df, cols), np.nan)
    if axis == "row":
        ax, kd = 1, True
        where = "per feature (row)"
    elif axis == "global":
        ax, kd = None, False
        where = "whole matrix"
    else:
        axis, ax, kd = "column", 0, True
        where = "per sample (column)"
    med = np.nanmedian(m, axis=ax, keepdims=kd)
    q1 = np.nanpercentile(m, 25, axis=ax, keepdims=kd)
    q3 = np.nanpercentile(m, 75, axis=ax, keepdims=kd)
    iqr = np.where((q3 - q1) == 0, 1.0, q3 - q1)
    new = (m - med) / iqr
    return _apply(df, cols, new), {"scaler": "robust", "axis": axis, "units": "changed"}, \
        [f"Robust scaling changes units (median-centred / IQR-scaled {where})."]


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


# --- count-style normalizations (CPM / TMM / voom) --------------------------
# Pure-Python implementations of published count-normalization methods (TMM: Robinson
# & Oshlack 2010; voom: Law et al. 2014). These are generic size-factor / logCPM
# transforms for count-like matrices — no R and no rpy2.
def cpm(df: pd.DataFrame, spec: MatrixSpec, *, log: bool = False,
        prior_count: float = 0.5, lib_sizes: Optional[np.ndarray] = None) -> Result:
    """Counts per million. ``log`` gives log2-CPM with a ``prior_count`` offset added
    proportionally to library size (the standard log-CPM stabilization)."""
    cols = _cols(df, spec)
    m = _block(df, cols)
    warns: List[str] = []
    if np.nanmin(m) < 0:
        warns.append("Negative values present — CPM assumes non-negative counts.")
    lib = np.nansum(m, axis=0) if lib_sizes is None else np.asarray(lib_sizes, dtype=float)
    lib = np.where(lib <= 0, np.nan, lib)
    if log:
        adj = float(prior_count)
        # scale the prior by relative library size so all samples get the same offset in CPM
        scaled_prior = adj * lib / np.nanmean(lib)
        new = np.log2((m + scaled_prior) / (lib + 2 * scaled_prior) * 1e6)
    else:
        new = m / lib * 1e6
    return _apply(df, cols, new), {"log": bool(log), "prior_count": float(prior_count),
                                   "used_effective_lib_size": lib_sizes is not None}, warns


def tmm_norm_factors(m: np.ndarray, *, ref_index: Optional[int] = None,
                     logratio_trim: float = 0.3, sum_trim: float = 0.05) -> np.ndarray:
    """TMM (trimmed mean of M-values) normalization factors, one per sample (column).

    Follows Robinson & Oshlack (2010): per non-reference sample, take the weighted
    trimmed mean of log-ratios (M-values) vs a reference library. The returned factors
    are scaled to a geometric mean of 1. Pure numpy."""
    m = np.asarray(m, dtype=float)
    m = np.where(np.isfinite(m), m, 0.0)
    lib = m.sum(axis=0)
    lib_safe = np.where(lib <= 0, np.nan, lib)
    n_samples = m.shape[1]
    if ref_index is None:
        # Standard TMM reference heuristic: the library whose 75th percentile of CPM
        # is closest to the mean 75th percentile.
        cpm_mat = m / np.where(lib_safe > 0, lib_safe, np.nan)
        with np.errstate(invalid="ignore"):
            q75 = np.nanpercentile(np.where(cpm_mat > 0, cpm_mat, np.nan), 75, axis=0)
        ref_index = int(np.nanargmin(np.abs(q75 - np.nanmean(q75)))) if np.isfinite(q75).any() else 0
    f = np.ones(n_samples)
    ref = m[:, ref_index]
    nref = lib[ref_index]
    for k in range(n_samples):
        obs = m[:, k]
        nk = lib[k]
        if nk <= 0 or nref <= 0:
            continue
        mask = (obs > 0) & (ref > 0)
        if mask.sum() < 3:
            continue
        o, r = obs[mask], ref[mask]
        logr = np.log2((o / nk) / (r / nref))                  # M
        abund = 0.5 * np.log2((o / nk) * (r / nref))            # A
        v = (nk - o) / (nk * o) + (nref - r) / (nref * r)       # asymptotic variance
        finite = np.isfinite(logr) & np.isfinite(abund) & np.isfinite(v)
        logr, abund, v = logr[finite], abund[finite], v[finite]
        if logr.size < 3:
            continue
        n = logr.size
        lo_m, hi_m = np.floor(n * logratio_trim), n - np.floor(n * logratio_trim)
        lo_a, hi_a = np.floor(n * sum_trim), n - np.floor(n * sum_trim)
        rank_m = logr.argsort().argsort() + 1
        rank_a = abund.argsort().argsort() + 1
        keep = (rank_m > lo_m) & (rank_m <= hi_m) & (rank_a > lo_a) & (rank_a <= hi_a)
        if keep.sum() == 0:
            continue
        w = 1.0 / v[keep]
        tmm_log = np.sum(w * logr[keep]) / np.sum(w)
        if np.isfinite(tmm_log):
            f[k] = 2.0 ** tmm_log
    f = f / np.exp(np.mean(np.log(np.where(f > 0, f, np.nan))))  # geometric mean -> 1
    return np.where(np.isfinite(f) & (f > 0), f, 1.0)


def tmm(df: pd.DataFrame, spec: MatrixSpec, *, log: bool = False,
        prior_count: float = 0.5) -> Result:
    """TMM-CPM: counts per million using TMM-adjusted effective library sizes.
    ``log`` gives log2 TMM-CPM. Assumes non-negative count-like values."""
    cols = _cols(df, spec)
    m = _block(df, cols)
    warns: List[str] = []
    if np.nanmin(m) < 0:
        warns.append("Negative values present — TMM assumes non-negative counts.")
    factors = tmm_norm_factors(m)
    eff_lib = np.nansum(np.where(np.isfinite(m), m, 0.0), axis=0) * factors
    out_df, params, w = cpm(df, spec, log=log, prior_count=prior_count, lib_sizes=eff_lib)
    params.update({"method": "tmm", "norm_factors": [float(x) for x in factors]})
    return out_df, params, warns + w


def voom(df: pd.DataFrame, spec: MatrixSpec, *, prior_count: float = 0.5,
         span: float = 0.5) -> Result:
    """voom-style log2 CPM on TMM-effective library sizes (Law et al. 2014).

    Produces the logCPM value matrix used for linear modeling. Observation-level
    precision weights (from the mean–variance trend) are computed and available via
    :func:`voom_weights` for weighted regression; the transform itself outputs logCPM."""
    cols = _cols(df, spec)
    m = _block(df, cols)
    warns: List[str] = []
    if np.nanmin(m) < 0:
        warns.append("Negative values present — voom assumes non-negative counts.")
    factors = tmm_norm_factors(m)
    eff_lib = np.nansum(np.where(np.isfinite(m), m, 0.0), axis=0) * factors
    out_df, _p, w = cpm(df, spec, log=True, prior_count=prior_count, lib_sizes=eff_lib)
    return out_df, {"method": "voom", "output_scale": "log2_cpm",
                    "norm_factors": [float(x) for x in factors],
                    "weights_available": True}, warns + w


def voom_weights(df: pd.DataFrame, spec: MatrixSpec, *, prior_count: float = 0.5) -> pd.DataFrame:
    """Per-observation voom precision weights (features x samples).

    Fits a lowess mean–variance trend on the logCPM values (sqrt residual SD vs mean
    logCPM) and returns weights ``1/sd^2`` per cell. Falls back to unit weights if the
    trend cannot be fit. Pure numpy + statsmodels lowess."""
    cols = _cols(df, spec)
    logcpm, _p, _w = cpm(df, spec, log=True, prior_count=prior_count,
                         lib_sizes=np.nansum(np.where(np.isfinite(_block(df, cols)), _block(df, cols), 0.0), axis=0)
                         * tmm_norm_factors(_block(df, cols)))
    y = _block(logcpm, cols)
    feat_mean = np.nanmean(y, axis=1)
    feat_sd = np.nanstd(y, axis=1, ddof=1)
    try:
        from statsmodels.nonparametric.smoothers_lowess import lowess
        ok = np.isfinite(feat_mean) & np.isfinite(feat_sd) & (feat_sd > 0)
        sm = lowess(np.sqrt(feat_sd[ok]), feat_mean[ok], frac=0.5, return_sorted=True)
        trend = np.interp(feat_mean, sm[:, 0], sm[:, 1])
        sd_hat = np.where(trend > 0, trend ** 2, np.nan)
        wmat = np.repeat((1.0 / sd_hat).reshape(-1, 1), y.shape[1], axis=1)
        wmat = np.where(np.isfinite(wmat), wmat, 1.0)
    except Exception:  # noqa: BLE001
        wmat = np.ones_like(y)
    return pd.DataFrame(wmat, columns=cols, index=df.index)
