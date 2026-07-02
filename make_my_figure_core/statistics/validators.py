"""Design validation for statistical tests.

These helpers fail *loudly and early* with :class:`StatsError` so the app never
returns a questionable p-value from an invalid design (e.g. a paired test with
mismatched IDs). Every helper returns cleaned numeric data + metadata that the
test functions consume directly.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from make_my_figure_core.statistics.models import StatsError


def require_columns(df: pd.DataFrame, columns: List[str], *, context: str) -> None:
    missing = [c for c in columns if c and c not in df.columns]
    if missing:
        raise StatsError(
            f"{context}: missing column(s) {missing}. Available: {list(df.columns)}"
        )


def numeric_series(df: pd.DataFrame, column: str, *, context: str) -> pd.Series:
    s = pd.to_numeric(df[column], errors="coerce")
    if s.notna().sum() == 0:
        raise StatsError(f"{context}: column '{column}' has no numeric values.")
    return s


def group_levels(df: pd.DataFrame, column: str) -> List[Any]:
    """First-seen order of the levels of a grouping column (NaN dropped)."""
    seen: List[Any] = []
    for v in df[column].tolist():
        if pd.isna(v):
            continue
        if v not in seen:
            seen.append(v)
    return seen


def two_group_arrays(
    df: pd.DataFrame,
    value_col: str,
    group_col: str,
    group_a: Any,
    group_b: Any,
    *,
    context: str,
    min_n: int = 2,
) -> Tuple[np.ndarray, np.ndarray]:
    require_columns(df, [value_col, group_col], context=context)
    vals = numeric_series(df, value_col, context=context)
    a = vals[df[group_col] == group_a].dropna().to_numpy(float)
    b = vals[df[group_col] == group_b].dropna().to_numpy(float)
    if a.size < min_n or b.size < min_n:
        raise StatsError(
            f"{context}: each group needs >= {min_n} finite values "
            f"(got {a.size} for '{group_a}', {b.size} for '{group_b}')."
        )
    return a, b


def paired_arrays(
    df: pd.DataFrame,
    value_col: str,
    group_col: str,
    group_a: Any,
    group_b: Any,
    id_col: str,
    *,
    context: str,
    min_n: int = 2,
) -> Tuple[np.ndarray, np.ndarray, List[Any]]:
    """Aligned paired arrays for two conditions, matched on ``id_col``.

    Raises if IDs do not match up, if there are duplicate IDs within a
    condition, or if fewer than ``min_n`` complete pairs remain.
    """
    require_columns(df, [value_col, group_col, id_col], context=context)
    vals = numeric_series(df, value_col, context=context)
    work = pd.DataFrame({id_col: df[id_col], group_col: df[group_col], value_col: vals})
    for g in (group_a, group_b):
        sub = work[work[group_col] == g]
        if sub[id_col].duplicated().any():
            raise StatsError(
                f"{context}: duplicate '{id_col}' within group '{g}'. Paired tests "
                "require exactly one measurement per subject per condition."
            )
    a_map = work[work[group_col] == group_a].set_index(id_col)[value_col]
    b_map = work[work[group_col] == group_b].set_index(id_col)[value_col]
    common = [i for i in a_map.index if i in b_map.index]
    a = a_map.loc[common].to_numpy(float)
    b = b_map.loc[common].to_numpy(float)
    mask = np.isfinite(a) & np.isfinite(b)
    a, b = a[mask], b[mask]
    kept_ids = [common[i] for i in range(len(common)) if mask[i]]
    if a.size < min_n:
        raise StatsError(
            f"{context}: need >= {min_n} complete pairs matched on '{id_col}' "
            f"(got {a.size})."
        )
    return a, b, kept_ids


def multi_group_arrays(
    df: pd.DataFrame,
    value_col: str,
    group_col: str,
    *,
    context: str,
    min_groups: int = 3,
    min_n: int = 2,
) -> Tuple[List[Any], List[np.ndarray]]:
    require_columns(df, [value_col, group_col], context=context)
    vals = numeric_series(df, value_col, context=context)
    levels = group_levels(df, group_col)
    arrays = [vals[df[group_col] == lv].dropna().to_numpy(float) for lv in levels]
    keep = [(lv, arr) for lv, arr in zip(levels, arrays) if arr.size >= min_n]
    if len(keep) < min_groups:
        raise StatsError(
            f"{context}: need >= {min_groups} groups with >= {min_n} values each "
            f"(got {len(keep)} usable of {len(levels)})."
        )
    levels = [lv for lv, _ in keep]
    arrays = [arr for _, arr in keep]
    return levels, arrays
