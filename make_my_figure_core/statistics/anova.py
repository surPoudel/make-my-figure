"""ANOVA family: one-way, two-way, and repeated-measures.

One-way ANOVA uses scipy (F, p) with a native effect-size computation. Two-way
and repeated-measures ANOVA use statsmodels, which is a required dependency for
these designs; if statsmodels is unavailable the functions raise a clear
:class:`StatsError` rather than guessing.
"""

from __future__ import annotations

from typing import Any, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

from make_my_figure_core.statistics import effect_sizes as es
from make_my_figure_core.statistics._versions import software_versions
from make_my_figure_core.statistics.models import StatResult, StatsError


def one_way_anova(levels: List[Any], arrays: List[np.ndarray], *,
                  value_col=None, group_col=None, alpha: float = 0.05) -> StatResult:
    """One-way ANOVA across >= 3 groups."""
    arrays = [np.asarray(a, float) for a in arrays]
    arrays = [a[np.isfinite(a)] for a in arrays]
    k = len(arrays)
    n = int(sum(a.size for a in arrays))
    res = stats.f_oneway(*arrays)
    r = StatResult(test_id="one_way_anova", test_name="One-way ANOVA",
                   comparison_type="omnibus", value_column=value_col,
                   grouping_columns=[group_col] if group_col else [],
                   n_total=n, n_by_group={str(lv): int(a.size) for lv, a in zip(levels, arrays)},
                   software_versions=software_versions())
    r.statistic = float(res.statistic); r.statistic_name = "F"
    r.df = float(k - 1); r.df2 = float(n - k); r.p_value = float(res.pvalue)
    name, eta = es.eta_squared_anova(arrays)
    r.effect_size_name, r.effect_size = name, eta
    _, omega = es.omega_squared_anova(arrays)
    r.extra = {"omega_squared": omega, "levels": [str(lv) for lv in levels]}
    r.assumptions_checked = ["independent observations", "approximate normality",
                             "homogeneity of variances"]
    return r


def two_way_anova(df: pd.DataFrame, value_col: str, factor_a: str, factor_b: str,
                  *, alpha: float = 0.05) -> List[StatResult]:
    """Two-way ANOVA (Type II sums of squares) via statsmodels.

    Returns one :class:`StatResult` per term: factor A, factor B, and their
    interaction.
    """
    try:
        import statsmodels.api as sm
        from statsmodels.formula.api import ols
    except Exception as exc:  # pragma: no cover
        raise StatsError(f"Two-way ANOVA requires statsmodels ({exc}).")

    work = df[[value_col, factor_a, factor_b]].copy()
    work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
    work = work.dropna()
    if work.empty:
        raise StatsError("Two-way ANOVA: no complete rows after dropping missing values.")
    work = work.rename(columns={value_col: "_y", factor_a: "_A", factor_b: "_B"})
    work["_A"] = work["_A"].astype(str)
    work["_B"] = work["_B"].astype(str)
    model = ols("_y ~ C(_A) + C(_B) + C(_A):C(_B)", data=work).fit()
    table = sm.stats.anova_lm(model, typ=2)
    ss_total = float(table["sum_sq"].sum())
    term_map = {"C(_A)": factor_a, "C(_B)": factor_b, "C(_A):C(_B)": f"{factor_a} x {factor_b}"}
    results: List[StatResult] = []
    for term, label in term_map.items():
        if term not in table.index:
            continue
        row = table.loc[term]
        r = StatResult(test_id="two_way_anova", test_name="Two-way ANOVA",
                       comparison_type="omnibus", value_column=value_col,
                       grouping_columns=[factor_a, factor_b],
                       n_total=int(len(work)), software_versions=software_versions())
        r.group_a = label
        r.statistic = float(row["F"]); r.statistic_name = "F"
        r.df = float(row["df"]); r.df2 = float(table.loc["Residual", "df"])
        r.p_value = float(row["PR(>F)"])
        eta = float(row["sum_sq"] / ss_total) if ss_total > 0 else float("nan")
        r.effect_size_name = "partial eta-squared (approx, eta-sq of total SS)"
        r.effect_size = eta
        r.extra = {"term": label, "sum_sq": float(row["sum_sq"])}
        r.assumptions_checked = ["independent observations", "approximate normality",
                                 "homogeneity of variances", "balanced/near-balanced design"]
        results.append(r)
    return results


def repeated_measures_anova(df: pd.DataFrame, value_col: str, subject_col: str,
                            within_col: str, *, alpha: float = 0.05) -> StatResult:
    """One-way repeated-measures ANOVA via statsmodels ``AnovaRM``.

    Requires a subject identifier and a within-subject factor, with exactly one
    observation per subject per level (a balanced complete design). Invalid
    structure raises :class:`StatsError` instead of returning a wrong result.
    """
    try:
        from statsmodels.stats.anova import AnovaRM
    except Exception as exc:  # pragma: no cover
        raise StatsError(f"Repeated-measures ANOVA requires statsmodels ({exc}).")

    work = df[[value_col, subject_col, within_col]].copy()
    work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
    work = work.dropna()
    if work.empty:
        raise StatsError("Repeated-measures ANOVA: no complete rows.")
    # Validate the design: one row per (subject, within-level), and every subject
    # observed at every level (balanced/complete).
    dup = work.duplicated(subset=[subject_col, within_col])
    if dup.any():
        raise StatsError(
            f"Repeated-measures ANOVA: multiple rows per subject per {within_col} level. "
            "Aggregate to one value per subject per condition first."
        )
    counts = work.groupby(subject_col)[within_col].nunique()
    n_levels = work[within_col].nunique()
    incomplete = counts[counts < n_levels]
    if len(incomplete) > 0:
        raise StatsError(
            f"Repeated-measures ANOVA requires a complete design: "
            f"{len(incomplete)} subject(s) are missing at least one {within_col} level."
        )
    if n_levels < 2:
        raise StatsError("Repeated-measures ANOVA needs >= 2 within-subject levels.")

    aov = AnovaRM(work, depvar=value_col, subject=subject_col, within=[within_col]).fit()
    tbl = aov.anova_table
    row = tbl.loc[within_col]
    r = StatResult(test_id="rm_anova", test_name="Repeated-measures ANOVA",
                   comparison_type="omnibus", value_column=value_col,
                   grouping_columns=[within_col], block_column=subject_col,
                   n_total=int(len(work)), software_versions=software_versions())
    r.statistic = float(row["F Value"]); r.statistic_name = "F"
    r.df = float(row["Num DF"]); r.df2 = float(row["Den DF"])
    r.p_value = float(row["Pr > F"])
    r.extra = {"n_subjects": int(work[subject_col].nunique()), "n_levels": int(n_levels)}
    r.assumptions_checked = ["within-subject design", "sphericity (not corrected here)",
                             "approximate normality"]
    r.warnings.append("Sphericity is assumed and not corrected (no Greenhouse-Geisser).")
    return r
