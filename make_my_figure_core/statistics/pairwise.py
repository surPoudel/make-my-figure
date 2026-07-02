"""Two-group tests and correlation/regression.

Every function returns a fully-populated :class:`StatResult`. Test statistics
and p-values come straight from scipy; effect sizes and confidence intervals are
computed here with standard formulas. NaN/non-finite values are dropped
(listwise) before testing.
"""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np
from scipy import stats

from make_my_figure_core.statistics import effect_sizes as es
from make_my_figure_core.statistics._versions import software_versions
from make_my_figure_core.statistics.models import StatResult


def _finite(a) -> np.ndarray:
    a = np.asarray(a, dtype=float)
    return a[np.isfinite(a)]


def _base(test_id: str, test_name: str, value_col, group_col, ga, gb, a, b,
          alternative: str, paired: bool) -> StatResult:
    return StatResult(
        test_id=test_id, test_name=test_name, comparison_type="two_group",
        grouping_columns=[group_col] if group_col else [], value_column=value_col,
        group_a=None if ga is None else str(ga), group_b=None if gb is None else str(gb),
        n_total=int(len(a) + len(b)),
        n_by_group={str(ga): int(len(a)), str(gb): int(len(b))} if group_col else {},
        alternative=alternative, paired=paired,
        software_versions=software_versions(),
    )


# --- independent-samples t tests -------------------------------------------

def students_t(a, b, *, value_col=None, group_col=None, group_a=None, group_b=None,
               alternative: str = "two-sided", alpha: float = 0.05) -> StatResult:
    """Student's two-sample t-test (equal variance assumed)."""
    a, b = _finite(a), _finite(b)
    res = stats.ttest_ind(a, b, equal_var=True, alternative=alternative)
    n1, n2 = a.size, b.size
    df = n1 + n2 - 2
    r = _base("students_t", "Student's t-test", value_col, group_col, group_a, group_b,
              a, b, alternative, paired=False)
    r.statistic = float(res.statistic); r.statistic_name = "t"; r.df = float(df)
    r.p_value = float(res.pvalue)
    name, d = es.cohens_d_independent(a, b)
    r.effect_size_name, r.effect_size = name, d
    # CI for the difference in means (pooled).
    diff = float(a.mean() - b.mean())
    sp = math.sqrt(((n1 - 1) * a.var(ddof=1) + (n2 - 1) * b.var(ddof=1)) / df) if df > 0 else float("nan")
    se = sp * math.sqrt(1.0 / n1 + 1.0 / n2) if sp == sp else float("nan")
    _set_diff_ci(r, diff, se, df, alpha, alternative)
    r.assumptions_checked = ["independent observations", "approximate normality",
                             "equal variances (Student's t)"]
    if n1 < 3 or n2 < 3:
        r.warnings.append("Very small sample; normality cannot be assessed reliably.")
    return r


def welch_t(a, b, *, value_col=None, group_col=None, group_a=None, group_b=None,
            alternative: str = "two-sided", alpha: float = 0.05) -> StatResult:
    """Welch's two-sample t-test (does NOT assume equal variance)."""
    a, b = _finite(a), _finite(b)
    res = stats.ttest_ind(a, b, equal_var=False, alternative=alternative)
    n1, n2 = a.size, b.size
    v1, v2 = a.var(ddof=1), b.var(ddof=1)
    # Welch-Satterthwaite df.
    denom = (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)
    df = ((v1 / n1 + v2 / n2) ** 2 / denom) if denom > 0 else float("nan")
    r = _base("welch_t", "Welch's t-test", value_col, group_col, group_a, group_b,
              a, b, alternative, paired=False)
    r.statistic = float(res.statistic); r.statistic_name = "t"
    r.df = float(df) if df == df else None
    r.p_value = float(res.pvalue)
    name, g = es.hedges_g_independent(a, b)
    r.effect_size_name, r.effect_size = name, g
    diff = float(a.mean() - b.mean())
    se = math.sqrt(v1 / n1 + v2 / n2)
    _set_diff_ci(r, diff, se, df, alpha, alternative)
    r.assumptions_checked = ["independent observations", "approximate normality",
                             "unequal variances allowed (Welch)"]
    return r


def _set_diff_ci(r: StatResult, diff: float, se: float, df: float, alpha: float,
                 alternative: str) -> None:
    r.estimate = diff
    r.estimate_name = "difference in means (group_a - group_b)"
    r.ci_level = 1 - alpha
    if not (se == se) or not (df and df == df) or df <= 0 or se == 0:
        r.warnings.append("Confidence interval for the mean difference is unavailable.")
        return
    if alternative != "two-sided":
        # One-sided CIs are unbounded on one end; report the two-sided interval
        # for interpretability and note it.
        r.warnings.append("CI shown is two-sided; test alternative is one-sided.")
    tcrit = stats.t.ppf(1 - alpha / 2, df)
    r.confidence_interval_low = float(diff - tcrit * se)
    r.confidence_interval_high = float(diff + tcrit * se)


def mann_whitney(a, b, *, value_col=None, group_col=None, group_a=None, group_b=None,
                 alternative: str = "two-sided", alpha: float = 0.05) -> StatResult:
    """Mann-Whitney U test (independent, nonparametric)."""
    a, b = _finite(a), _finite(b)
    res = stats.mannwhitneyu(a, b, alternative=alternative)
    r = _base("mann_whitney", "Mann-Whitney U test", value_col, group_col, group_a,
              group_b, a, b, alternative, paired=False)
    r.statistic = float(res.statistic); r.statistic_name = "U"
    r.p_value = float(res.pvalue)
    name, val = es.rank_biserial_from_u(float(res.statistic), a.size, b.size)
    r.effect_size_name, r.effect_size = name, val
    r.assumptions_checked = ["independent observations",
                             "similar distribution shapes (for a location interpretation)"]
    r.missing_data_policy = "listwise deletion (drop non-finite values)"
    return r


# --- paired tests -----------------------------------------------------------

def paired_t(a, b, *, value_col=None, group_col=None, group_a=None, group_b=None,
             id_col=None, alternative: str = "two-sided", alpha: float = 0.05) -> StatResult:
    """Paired-samples t-test on aligned arrays ``a`` and ``b``."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    diff = a - b
    res = stats.ttest_rel(a, b, alternative=alternative)
    n = diff.size
    df = n - 1
    r = _base("paired_t", "Paired t-test", value_col, group_col, group_a, group_b,
              a, b, alternative, paired=True)
    r.paired_id_column = id_col
    r.n_total = int(n)
    r.n_by_group = {str(group_a): int(n), str(group_b): int(n)}
    r.statistic = float(res.statistic); r.statistic_name = "t"; r.df = float(df)
    r.p_value = float(res.pvalue)
    name, dz = es.cohens_dz_paired(diff)
    r.effect_size_name, r.effect_size = name, dz
    md = float(diff.mean())
    se = float(diff.std(ddof=1) / math.sqrt(n)) if n > 1 else float("nan")
    r.estimate = md; r.estimate_name = "mean of paired differences (a - b)"
    r.ci_level = 1 - alpha
    if df > 0 and se == se and se > 0:
        tcrit = stats.t.ppf(1 - alpha / 2, df)
        r.confidence_interval_low = float(md - tcrit * se)
        r.confidence_interval_high = float(md + tcrit * se)
    r.assumptions_checked = ["paired/matched observations",
                             "approximate normality of differences"]
    return r


def wilcoxon_signed_rank(a, b, *, value_col=None, group_col=None, group_a=None,
                         group_b=None, id_col=None, alternative: str = "two-sided",
                         alpha: float = 0.05) -> StatResult:
    """Wilcoxon signed-rank test on aligned paired arrays."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    diff = a - b
    nonzero = diff[diff != 0]
    r = _base("wilcoxon", "Wilcoxon signed-rank test", value_col, group_col, group_a,
              group_b, a, b, alternative, paired=True)
    r.paired_id_column = id_col
    r.n_total = int(diff.size)
    r.n_by_group = {str(group_a): int(diff.size), str(group_b): int(diff.size)}
    if nonzero.size == 0:
        r.warnings.append("All paired differences are zero; test is undefined.")
        r.p_value = float("nan")
        return r
    res = stats.wilcoxon(a, b, alternative=alternative, zero_method="wilcox")
    r.statistic = float(res.statistic); r.statistic_name = "W"
    r.p_value = float(res.pvalue)
    name, val = es.wilcoxon_rank_biserial(diff)
    r.effect_size_name, r.effect_size = name, val
    if diff.size - (diff == 0).sum() < 6:
        r.warnings.append("Fewer than ~6 nonzero pairs; p-value may be unreliable.")
    r.assumptions_checked = ["paired/matched observations",
                             "symmetric distribution of differences"]
    return r


# --- correlation / regression ----------------------------------------------

def pearson(x, y, *, x_col=None, y_col=None, group_label=None,
            alternative: str = "two-sided", alpha: float = 0.05) -> StatResult:
    """Pearson product-moment correlation with a Fisher-z confidence interval."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    res = stats.pearsonr(x, y, alternative=alternative)
    r = StatResult(test_id="pearson", test_name="Pearson correlation",
                   comparison_type="correlation", value_column=y_col,
                   grouping_columns=[x_col] if x_col else [], alternative=alternative,
                   n_total=int(x.size), software_versions=software_versions())
    if group_label is not None:
        r.group_a = str(group_label)
    rho = float(res.statistic)
    r.statistic = rho; r.statistic_name = "r"; r.p_value = float(res.pvalue)
    r.df = float(x.size - 2)
    r.effect_size_name = "R-squared"; r.effect_size = float(rho ** 2)
    r.estimate = rho; r.estimate_name = "Pearson r"; r.ci_level = 1 - alpha
    # Fisher z CI (needs n >= 4).
    if x.size >= 4 and abs(rho) < 1:
        z = math.atanh(rho); se = 1 / math.sqrt(x.size - 3)
        zcrit = stats.norm.ppf(1 - alpha / 2)
        r.confidence_interval_low = float(math.tanh(z - zcrit * se))
        r.confidence_interval_high = float(math.tanh(z + zcrit * se))
    else:
        r.warnings.append("Confidence interval requires n >= 4 and |r| < 1.")
    r.assumptions_checked = ["linear relationship", "bivariate normality"]
    return r


def spearman(x, y, *, x_col=None, y_col=None, group_label=None,
             alternative: str = "two-sided", alpha: float = 0.05) -> StatResult:
    """Spearman rank correlation."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    res = stats.spearmanr(x, y, alternative=alternative)
    r = StatResult(test_id="spearman", test_name="Spearman correlation",
                   comparison_type="correlation", value_column=y_col,
                   grouping_columns=[x_col] if x_col else [], alternative=alternative,
                   n_total=int(x.size), software_versions=software_versions())
    if group_label is not None:
        r.group_a = str(group_label)
    rho = float(res.statistic)
    r.statistic = rho; r.statistic_name = "rho"; r.p_value = float(res.pvalue)
    r.effect_size_name = "Spearman rho"; r.effect_size = rho
    r.estimate = rho; r.estimate_name = "Spearman rho"
    r.assumptions_checked = ["monotonic relationship"]
    return r


def linear_regression(x, y, *, x_col=None, y_col=None, group_label=None,
                      alpha: float = 0.05) -> StatResult:
    """Ordinary least-squares linear regression (slope test)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    res = stats.linregress(x, y)
    r = StatResult(test_id="linear_regression", test_name="Linear regression",
                   comparison_type="regression", value_column=y_col,
                   grouping_columns=[x_col] if x_col else [], alternative="two-sided",
                   n_total=int(x.size), software_versions=software_versions())
    if group_label is not None:
        r.group_a = str(group_label)
    r.statistic = float(res.slope); r.statistic_name = "slope"
    r.p_value = float(res.pvalue); r.df = float(x.size - 2)
    r.effect_size_name = "R-squared"; r.effect_size = float(res.rvalue ** 2)
    r.estimate = float(res.slope); r.estimate_name = "regression slope"
    r.ci_level = 1 - alpha
    if x.size > 2 and res.stderr == res.stderr and res.stderr > 0:
        tcrit = stats.t.ppf(1 - alpha / 2, x.size - 2)
        r.confidence_interval_low = float(res.slope - tcrit * res.stderr)
        r.confidence_interval_high = float(res.slope + tcrit * res.stderr)
    r.extra = {"intercept": float(res.intercept), "pearson_r": float(res.rvalue),
               "stderr": float(res.stderr)}
    r.assumptions_checked = ["linearity", "independent residuals",
                             "homoscedasticity", "normal residuals"]
    return r
