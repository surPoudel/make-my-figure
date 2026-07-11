"""Shared helpers for the v0.4 manuscript plot types.

These are small, dependency-light utilities (numpy/scipy/pandas only — no new
dependencies) used by several of the new renderers so behaviour stays
consistent: matrix parsing, hierarchical linkage, jitter / quasi-beeswarm
layout, summary overlays, flexible column detection, and -log10(p).

Renderers still follow the standard contract in ``plots/base.py`` (never mutate
the input DataFrame, pull styling from tokens, return a ``RenderResult``).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from make_my_figure_core.plots.base import RenderError

# Standard GWAS thresholds (used by Manhattan / Q-Q).
GENOME_WIDE_SIG = 5e-8
SUGGESTIVE_SIG = 1e-5

_LINKAGE_METHODS = ("average", "complete", "single", "ward")


def _norm(name: str) -> str:
    return str(name).lower().replace(" ", "").replace("_", "").replace(".", "").replace("-", "")


def pick_column(df: pd.DataFrame, aliases: Sequence[str], *, default: Optional[str] = None) -> Optional[str]:
    """Return the first DataFrame column matching any alias (case/format-insensitive)."""
    lookup = {_norm(c): c for c in df.columns}
    for alias in aliases:
        hit = lookup.get(_norm(alias))
        if hit is not None:
            return hit
    return default


def numeric_matrix(
    df: pd.DataFrame, id_col: Optional[str] = None, *, context: str
) -> Tuple[List[str], List[str], np.ndarray, List[str]]:
    """Parse a ``features x samples`` matrix.

    The ``id_col`` (or the first column when unset) holds row labels; every
    other column is coerced to numeric. Returns
    ``(row_labels, value_columns, matrix, warnings)`` and never mutates ``df``.
    """
    if df.shape[1] < 2:
        raise RenderError(f"{context}: expected a label column plus at least one numeric column.")
    if id_col is None or id_col == "":
        id_col = df.columns[0]
    if id_col not in df.columns:
        raise RenderError(f"{context}: label column '{id_col}' not found. Columns: {list(df.columns)}")

    row_labels = df[id_col].astype(str).tolist()
    value_cols = [c for c in df.columns if c != id_col]
    numeric = df[value_cols].apply(lambda s: pd.to_numeric(s, errors="coerce"))
    # Drop columns that are entirely non-numeric (e.g. stray text metadata columns).
    keep = [c for c in value_cols if numeric[c].notna().any()]
    if not keep:
        raise RenderError(f"{context}: no numeric value columns besides label '{id_col}'.")
    dropped = [c for c in value_cols if c not in keep]
    warnings: List[str] = []
    if dropped:
        warnings.append(f"Ignored non-numeric column(s): {dropped}.")
    matrix = numeric[keep].to_numpy(dtype=float)
    if np.isnan(matrix).any():
        warnings.append("Matrix has missing/non-numeric entries; treated as 0 for clustering.")
    return row_labels, keep, matrix, warnings


def linkage_matrix(matrix: np.ndarray, *, method: str = "average", metric: str = "euclidean"):
    """SciPy hierarchical linkage with safe defaults.

    ``ward`` requires a Euclidean metric, so the metric is forced to euclidean
    for ward. NaNs are replaced with 0 first so degenerate rows don't error.
    """
    from scipy.cluster.hierarchy import linkage

    method = (method or "average").lower()
    if method not in _LINKAGE_METHODS:
        method = "average"
    if method == "ward":
        metric = "euclidean"
    filled = np.nan_to_num(np.asarray(matrix, dtype=float), nan=0.0)
    return linkage(filled, method=method, metric=metric)


def jitter(n: int, *, width: float = 0.18, seed: int = 0) -> np.ndarray:
    """Deterministic uniform jitter offsets in ``[-width, width]``."""
    rng = np.random.default_rng(seed)
    if n <= 0:
        return np.zeros(0)
    return rng.uniform(-width, width, size=int(n))


def beeswarm_offsets(values: Sequence[float], *, width: float = 0.32, seed: int = 0) -> np.ndarray:
    """Quasi-beeswarm x-offsets with basic collision avoidance.

    Points are binned by value; within each bin they are spread symmetrically so
    same-value points don't overprint. This is a lightweight approximation of a
    true force-directed beeswarm (documented limitation) — no extra dependency.
    """
    vals = np.asarray(values, dtype=float)
    n = vals.size
    offsets = np.zeros(n)
    if n == 0:
        return offsets
    finite = vals[np.isfinite(vals)]
    if finite.size == 0:
        return jitter(n, width=width * 0.3, seed=seed)
    span = float(np.ptp(finite)) or 1.0
    n_bins = max(10, min(60, int(np.sqrt(n) * 4)))
    bin_h = span / n_bins
    order = np.argsort(vals)
    bins: Dict[int, List[int]] = {}
    for idx in order:
        v = vals[idx]
        b = 0 if not np.isfinite(v) else int((v - np.nanmin(finite)) / bin_h)
        bins.setdefault(b, []).append(idx)
    for members in bins.values():
        k = len(members)
        if k == 1:
            offsets[members[0]] = 0.0
            continue
        # Symmetric spread: -width..width across the bin members.
        spread = np.linspace(-width, width, k)
        for slot, idx in zip(spread, members):
            offsets[idx] = slot
    return offsets


def summary_stat(values: Sequence[float], kind: str) -> Tuple[float, float]:
    """Return ``(center, half_error)`` for a summary overlay.

    ``kind`` is one of ``mean``, ``median``, ``ci``/``ci95``, ``sd``, ``sem``.
    Median returns a zero error bar (a line only). NaNs are dropped.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    kind = (kind or "mean").lower()
    if arr.size == 0:
        return (np.nan, 0.0)
    if kind == "median":
        return (float(np.median(arr)), 0.0)
    mean = float(np.mean(arr))
    if arr.size < 2:
        return (mean, 0.0)
    sd = float(np.std(arr, ddof=1))
    if kind in ("sd", "std"):
        return (mean, sd)
    sem = sd / np.sqrt(arr.size)
    if kind in ("ci", "ci95", "ci_95"):
        return (mean, 1.96 * sem)
    return (mean, sem)  # default: SEM


def neg_log10(p: Sequence[float]) -> np.ndarray:
    """``-log10(p)`` with tiny p clipped to avoid infinities."""
    arr = pd.to_numeric(pd.Series(p), errors="coerce").to_numpy(dtype=float)
    tiny = np.nextafter(0, 1)
    arr = np.clip(arr, tiny, 1.0)
    return -np.log10(arr)


def ordered_unique(series: Sequence[Any]) -> List[Any]:
    """Stable unique values (first-seen order), dropping NaN/blank."""
    out: List[Any] = []
    seen = set()
    for v in series:
        if v is None:
            continue
        if isinstance(v, float) and np.isnan(v):
            continue
        s = str(v)
        if s == "" or s.lower() == "nan":
            continue
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out
