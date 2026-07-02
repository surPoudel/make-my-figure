"""Categorical association tests: chi-square and Fisher's exact.

Contingency tables are built from two categorical columns of a DataFrame, or
supplied directly as a 2-D array. Expected-count warnings and effect sizes
(Cramer's V, odds ratio) are reported for transparent interpretation.
"""

from __future__ import annotations

from typing import Any, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

from make_my_figure_core.statistics import effect_sizes as es
from make_my_figure_core.statistics._versions import software_versions
from make_my_figure_core.statistics.models import StatResult, StatsError


def contingency_from_columns(df: pd.DataFrame, row_col: str, col_col: str) -> pd.DataFrame:
    """Build a contingency table (counts) from two categorical columns."""
    for c in (row_col, col_col):
        if c not in df.columns:
            raise StatsError(f"Categorical test: missing column '{c}'.")
    table = pd.crosstab(df[row_col], df[col_col])
    if table.size == 0:
        raise StatsError("Categorical test: contingency table is empty.")
    return table


def chi_square(table, *, row_col=None, col_col=None, correction: bool = True,
               alpha: float = 0.05) -> StatResult:
    """Pearson chi-square test of independence with Cramer's V."""
    arr = np.asarray(table, dtype=float)
    if arr.ndim != 2 or arr.shape[0] < 2 or arr.shape[1] < 2:
        raise StatsError("Chi-square needs a contingency table with >= 2 rows and columns.")
    chi2, p, dof, expected = stats.chi2_contingency(arr, correction=correction)
    n = int(arr.sum())
    r = StatResult(test_id="chi_square", test_name="Chi-square test of independence",
                   comparison_type="categorical",
                   grouping_columns=[c for c in (row_col, col_col) if c],
                   n_total=n, software_versions=software_versions())
    r.statistic = float(chi2); r.statistic_name = "chi2"; r.df = float(dof)
    r.p_value = float(p)
    name, v = es.cramers_v(float(chi2), n, arr.shape[0], arr.shape[1])
    r.effect_size_name, r.effect_size = name, v
    small = int((expected < 5).sum())
    if small > 0:
        frac = small / expected.size
        r.warnings.append(
            f"{small} of {expected.size} cells have expected count < 5 "
            f"({frac:.0%}); chi-square may be unreliable - consider Fisher's exact."
        )
    r.assumptions_checked = ["independent observations", "expected counts >= 5 (checked)"]
    r.extra = {"expected_min": float(expected.min()),
               "table_shape": [int(arr.shape[0]), int(arr.shape[1])]}
    if arr.shape == (2, 2) and correction:
        r.extra["note"] = "Yates' continuity correction applied (2x2)."
    return r


def fishers_exact(table, *, row_col=None, col_col=None, alternative: str = "two-sided",
                  alpha: float = 0.05) -> StatResult:
    """Fisher's exact test. Odds ratio is reported for 2x2 tables."""
    arr = np.asarray(table, dtype=float)
    if arr.ndim != 2 or arr.shape[0] < 2 or arr.shape[1] < 2:
        raise StatsError("Fisher's exact needs a contingency table with >= 2 rows and columns.")
    r = StatResult(test_id="fishers_exact", test_name="Fisher's exact test",
                   comparison_type="categorical",
                   grouping_columns=[c for c in (row_col, col_col) if c],
                   n_total=int(arr.sum()), alternative=alternative,
                   software_versions=software_versions())
    if arr.shape == (2, 2):
        oddsratio, p = stats.fisher_exact(arr, alternative=alternative)
        r.p_value = float(p)
        r.estimate = float(oddsratio); r.estimate_name = "odds ratio"
        r.effect_size_name = "odds ratio"; r.effect_size = float(oddsratio)
        r.statistic_name = "odds ratio"; r.statistic = float(oddsratio)
    else:
        # scipy >= 1.15 supports r x c Fisher's exact; older versions raise for
        # non-2x2, in which case we fall back to a clear warning (no fake p).
        try:
            res = stats.fisher_exact(arr)
            r.p_value = float(res.pvalue if hasattr(res, "pvalue") else res[1])
            r.warnings.append("Odds ratio is only reported for 2x2 tables.")
        except Exception:
            r.p_value = float("nan")
            r.warnings.append(
                "Fisher's exact for tables larger than 2x2 is not supported by the "
                "installed scipy; use the chi-square test instead."
            )
    r.assumptions_checked = ["independent observations", "fixed marginal totals"]
    return r
