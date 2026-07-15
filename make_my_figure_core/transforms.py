"""Reproducible, structure-changing data transforms for the recommendation engine.

Some figures need the data reshaped first (a wide matrix melted to long, a
correlation matrix computed, a categorical column counted). These transforms are
**pure pandas** and return a new frame; the recommendation engine attaches a
transform spec (``{name, params}``) to a recommendation, and the app applies it
via :func:`apply_transform` when the user chooses to generate the plot — saving
the transformed table so the result is reproducible.

None of these compute statistics, p-values, or fold changes. Plots that need
those (volcano/MA) require a *precomputed* differential/statistical results
table — the recommendation engine surfaces that as guidance, not a transform.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import pandas as pd


def wide_to_long(df: pd.DataFrame, *, value_cols: List[str], id_col: Optional[str] = None,
                 var_name: str = "column", value_name: str = "value") -> pd.DataFrame:
    """Melt wide numeric columns to long ``[<id_col?>, var_name, value_name]``.

    Turns a features x samples (or any wide numeric) table into a long, tidy frame
    so each melted column becomes a group — enabling ridge/box/violin/bar across
    columns. Non-numeric melted values become NaN and are dropped.
    """
    value_cols = [c for c in value_cols if c in df.columns]
    if not value_cols:
        raise ValueError("wide_to_long: no valid value columns to melt.")
    id_vars = [id_col] if id_col and id_col in df.columns else []
    long = df.melt(id_vars=id_vars, value_vars=value_cols,
                   var_name=var_name, value_name=value_name)
    long[value_name] = pd.to_numeric(long[value_name], errors="coerce")
    return long.dropna(subset=[value_name]).reset_index(drop=True)


def correlation_matrix(df: pd.DataFrame, *, columns: List[str], method: str = "pearson",
                       index_name: str = "feature") -> pd.DataFrame:
    """Compute a square correlation matrix over ``columns`` (features x features).

    Returns a frame with ``index_name`` as the first column then one column per
    variable, ready for the clustered-heatmap renderer (row_id=``index_name``).
    """
    columns = [c for c in columns if c in df.columns]
    if len(columns) < 2:
        raise ValueError("correlation_matrix: need >= 2 numeric columns.")
    num = df[columns].apply(pd.to_numeric, errors="coerce")
    corr = num.corr(method=method)
    corr.index.name = index_name
    return corr.reset_index()


def value_counts(df: pd.DataFrame, *, column: str, category_name: Optional[str] = None,
                 count_name: str = "count") -> pd.DataFrame:
    """Frequency of each category in ``column`` → ``[category_name, count_name]``."""
    if column not in df.columns:
        raise ValueError(f"value_counts: column '{column}' not found.")
    cat = category_name or column
    out = df[column].astype(str).value_counts().reset_index()
    out.columns = [cat, count_name]
    return out


_TRANSFORMS: Dict[str, Callable[..., pd.DataFrame]] = {
    "wide_to_long": wide_to_long,
    "correlation_matrix": correlation_matrix,
    "value_counts": value_counts,
}


def apply_transform(df: pd.DataFrame, name: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """Apply a named transform to ``df`` and return the reshaped frame."""
    if name not in _TRANSFORMS:
        raise ValueError(f"Unknown transform '{name}'. Known: {sorted(_TRANSFORMS)}")
    return _TRANSFORMS[name](df, **(params or {}))
