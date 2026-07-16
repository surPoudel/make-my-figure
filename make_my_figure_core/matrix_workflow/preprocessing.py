"""Transforms + the orchestrator that applies confirmed preprocessing steps.

Transforms (log family, arcsinh, sqrt, winsorize, impute, filter) and the
normalization methods (``normalization.py``) are dispatched by ``apply_step`` /
``run_preprocessing``, which never mutate the input, always return a NEW derived
matrix, and record each operation as a :class:`PreprocessingStep`. Pure
numpy/pandas/scipy. No R, no rpy2.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from make_my_figure_core.matrix_workflow import normalization as _norm
from make_my_figure_core.matrix_workflow.matrix_spec import MatrixSpec
from make_my_figure_core.matrix_workflow.preprocessing_spec import (
    PreprocessingSpec,
    PreprocessingStep,
)

Result = Tuple[pd.DataFrame, Dict[str, Any], List[str]]

# Transforms that put the matrix on a log-like scale (drives value_type + fold change).
_LOG_METHODS = {"log2", "log", "ln", "log10", "arcsinh"}


# --- element-wise transforms -------------------------------------------------
def _log(df, spec, base, pseudocount) -> Result:
    cols = _norm._cols(df, spec)
    m = _norm._block(df, cols)
    warns: List[str] = []
    if np.nanmin(m) < 0:
        warns.append("Negative values present — a log transform needs a justified offset; "
                     "results below zero are undefined.")
    shifted = m + float(pseudocount)
    with np.errstate(all="ignore"):
        if base == 2:
            new = np.log2(shifted)
        elif base == 10:
            new = np.log10(shifted)
        else:
            new = np.log(shifted)
    new[~np.isfinite(new)] = np.nan
    return _norm._apply(df, cols, new), {"pseudocount": float(pseudocount), "base": base}, warns


def log2(df, spec, *, pseudocount: float = 1.0) -> Result:
    return _log(df, spec, 2, pseudocount)


def ln(df, spec, *, pseudocount: float = 1.0) -> Result:
    return _log(df, spec, np.e, pseudocount)


def log10(df, spec, *, pseudocount: float = 1.0) -> Result:
    return _log(df, spec, 10, pseudocount)


def arcsinh(df, spec, *, cofactor: float = 5.0) -> Result:
    cols = _norm._cols(df, spec)
    m = _norm._block(df, cols)
    new = np.arcsinh(m / float(cofactor))
    return _norm._apply(df, cols, new), {"cofactor": float(cofactor)}, []


def sqrt(df, spec) -> Result:
    cols = _norm._cols(df, spec)
    m = _norm._block(df, cols)
    warns = ["Negative values present — square-root transform is only valid for non-negative data."] \
        if np.nanmin(m) < 0 else []
    new = np.sqrt(np.clip(m, 0, None))
    return _norm._apply(df, cols, new), {}, warns


def winsorize(df, spec, *, lower: float = 1.0, upper: float = 99.0) -> Result:
    cols = _norm._cols(df, spec)
    m = _norm._block(df, cols)
    lo = np.nanpercentile(m, lower)
    hi = np.nanpercentile(m, upper)
    capped = int(np.sum((m < lo) | (m > hi)))
    new = np.clip(m, lo, hi)
    return _norm._apply(df, cols, new), {"lower": lower, "upper": upper,
                                         "capped_values": capped}, []


def impute(df, spec, *, strategy: str = "feature_median", constant: float = 0.0) -> Result:
    cols = _norm._cols(df, spec)
    m = _norm._block(df, cols)
    n_missing = int(np.isnan(m).sum())
    if strategy == "none" or n_missing == 0:
        return df.copy(), {"strategy": strategy, "imputed": 0}, []
    if strategy == "sample_median":
        fill = np.nanmedian(np.where(np.isfinite(m), m, np.nan), axis=0, keepdims=True)
        new = np.where(np.isnan(m), fill, m)
    elif strategy == "constant":
        new = np.where(np.isnan(m), float(constant), m)
    else:                                     # feature_median (default)
        strategy = "feature_median"
        fill = np.nanmedian(np.where(np.isfinite(m), m, np.nan), axis=1, keepdims=True)
        new = np.where(np.isnan(m), fill, m)
    return _norm._apply(df, cols, new), {"strategy": strategy, "imputed": n_missing}, []


def filter_features(df, spec, *, max_missing_frac: Optional[float] = None,
                    max_zero_frac: Optional[float] = None, min_variance: Optional[float] = None,
                    min_total: Optional[float] = None, drop_constant: bool = False,
                    top_variable_n: Optional[int] = None) -> Result:
    cols = _norm._cols(df, spec)
    m = _norm._block(df, cols)
    n0 = m.shape[0]
    keep = np.ones(n0, dtype=bool)
    reasons: List[str] = []
    if max_missing_frac is not None:
        frac = np.isnan(m).mean(axis=1)
        keep &= frac <= max_missing_frac; reasons.append(f"missing>{max_missing_frac}")
    if max_zero_frac is not None:
        frac = (np.nan_to_num(m) == 0).mean(axis=1)
        keep &= frac <= max_zero_frac; reasons.append(f"zeros>{max_zero_frac}")
    if drop_constant:
        keep &= np.nanstd(m, axis=1) > 0; reasons.append("constant")
    if min_variance is not None:
        keep &= np.nan_to_num(np.nanvar(m, axis=1)) >= min_variance; reasons.append(f"var<{min_variance}")
    if min_total is not None:
        keep &= np.nan_to_num(np.nansum(m, axis=1)) >= min_total; reasons.append(f"total<{min_total}")
    if top_variable_n is not None and top_variable_n < int(keep.sum()):
        var = np.where(keep, np.nan_to_num(np.nanvar(m, axis=1)), -np.inf)
        order = np.argsort(var)[::-1][:int(top_variable_n)]
        sel = np.zeros(n0, dtype=bool); sel[order] = True
        keep &= sel; reasons.append(f"top{top_variable_n}var")
    out = df.iloc[np.where(keep)[0]].reset_index(drop=True)
    removed = int(n0 - keep.sum())
    summary = f"removed {removed}/{n0} features ({', '.join(reasons) or 'none'})"
    return out, {"removed": removed, "n_in": n0, "criteria": reasons, "summary": summary}, []


# --- dispatch ---------------------------------------------------------------
_REGISTRY = {
    # transforms
    "log2": (log2, "transform"), "log": (ln, "transform"), "ln": (ln, "transform"),
    "log10": (log10, "transform"), "arcsinh": (arcsinh, "transform"), "sqrt": (sqrt, "transform"),
    "winsorize": (winsorize, "transform"),
    "impute": (impute, "impute"), "filter": (filter_features, "filter"),
    # normalizations
    "total_sum": (_norm.total_sum, "normalization"), "median_scale": (_norm.median_scale, "normalization"),
    "upper_quartile": (_norm.upper_quartile, "normalization"),
    "quantile": (_norm.quantile_normalize, "normalization"),
    "robust_scale": (_norm.robust_scale, "normalization"),
    "standard_scale": (_norm.standard_scale, "normalization"),
    "center": (_norm.center, "normalization"),
    "internal_standard_features": (_norm.internal_standard_features, "normalization"),
    "internal_standard_columns": (_norm.internal_standard_columns, "normalization"),
    "control_features": (_norm.control_features, "normalization"),
    "reference_sample": (_norm.reference_sample, "normalization"),
    # count-style normalizations (pure-Python; no R dependency)
    "cpm": (_norm.cpm, "normalization"),
    "tmm": (_norm.tmm, "normalization"),
    "voom": (_norm.voom, "normalization"),
}
# z-score axis variants map to the single zscore(axis=...) function.
_ZSCORE = {"row_zscore": "row", "column_zscore": "column", "global_zscore": "global"}


def available_methods() -> List[str]:
    # "zscore" is the generic axis-parameterized variant (row | column | global).
    return sorted(list(_REGISTRY) + list(_ZSCORE) + ["zscore"])


def apply_step(df: pd.DataFrame, matrix_spec: MatrixSpec, method: str, *,
               params: Optional[Dict[str, Any]] = None, metadata=None,
               with_qc: bool = False) -> Tuple[pd.DataFrame, MatrixSpec, PreprocessingStep]:
    """Apply one preprocessing method; return (derived_df, derived_spec, step)."""
    from make_my_figure_core.matrix_workflow.qc_diagnostics import diagnose_matrix

    params = dict(params or {})
    qc_before = diagnose_matrix(df, matrix_spec).to_dict() if with_qc else None

    if method == "zscore" or method in _ZSCORE:
        # Generic "zscore" reads params['axis'] (row | column | global); the named
        # variants (row_/column_/global_zscore) fix the axis. Default is row-wise —
        # the convention for MS proteomics and bulk transcriptomics (per-feature).
        axis = params.get("axis", "row") if method == "zscore" else _ZSCORE[method]
        if axis not in ("row", "column", "global"):
            axis = "row"
        new_df, p, warns = _norm.zscore(df, matrix_spec, axis=axis,
                                        ddof=int(params.get("ddof", 0)))
        step_type = "normalization"
    else:
        if method not in _REGISTRY:
            raise ValueError(f"Unknown preprocessing method: {method}")
        fn, step_type = _REGISTRY[method]
        kwargs = dict(params)
        if method == "reference_sample":
            kwargs["metadata"] = metadata
        new_df, p, warns = fn(df, matrix_spec, **kwargs)

    # derived spec: same roles; value scale / value_columns updated as needed
    import dataclasses
    derived = dataclasses.replace(matrix_spec)
    _p = p or {}
    if method in _LOG_METHODS or method == "voom" or bool(_p.get("log")) \
            or str(_p.get("output_scale", "")).startswith("log"):
        derived.value_type = "log_normalized"
    step = PreprocessingStep(
        step_id=f"{method}", step_type=step_type, method_name=method,
        parameters={**params, **(p or {})}, input_matrix_id=matrix_spec.source_file,
        output_matrix_id=None, warnings=list(warns), qc_before=qc_before,
        qc_after=(diagnose_matrix(new_df, derived).to_dict() if with_qc else None),
        user_confirmed=True)
    return new_df, derived, step


def run_preprocessing(df: pd.DataFrame, matrix_spec: MatrixSpec,
                      steps: List[Dict[str, Any]], *, metadata=None,
                      output_matrix_id: str = "processed",
                      with_qc: bool = False) -> Tuple[pd.DataFrame, MatrixSpec, PreprocessingSpec]:
    """Apply an ordered list of ``[{'method':..., 'params':{...}}]`` steps.

    Returns ``(final_df, final_matrix_spec, PreprocessingSpec)``. The original ``df``
    is untouched; the spec fully documents the chain for reproducibility."""
    cur_df, cur_spec = df, matrix_spec
    ps = PreprocessingSpec(
        source_matrix_id=matrix_spec.source_file, output_matrix_id=output_matrix_id,
        input_file=matrix_spec.source_file,
        input_shape=[int(df.shape[0]), int(df.shape[1])],
        feature_id_column=matrix_spec.feature_id_column,
        value_columns=list(matrix_spec.value_columns), user_confirmed=True)
    for spec_step in steps:
        method = spec_step["method"]
        cur_df, cur_spec, step = apply_step(cur_df, cur_spec, method,
                                            params=spec_step.get("params"),
                                            metadata=metadata, with_qc=with_qc)
        step.output_matrix_id = output_matrix_id
        ps.add_step(step)
    cur_spec.source_file = output_matrix_id
    return cur_df, cur_spec, ps
