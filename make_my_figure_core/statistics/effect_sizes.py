"""Effect-size estimators used across the statistics engine.

Each returns a ``(name, value)`` tuple (value may be NaN when undefined) so a
StatResult can record both the effect-size *name* and its magnitude. Formulas
follow standard references; tests pin them against hand-computed examples.
"""

from __future__ import annotations

import math
from typing import Tuple

import numpy as np


def _clean(a) -> np.ndarray:
    a = np.asarray(a, dtype=float)
    return a[np.isfinite(a)]


def cohens_d_independent(a, b) -> Tuple[str, float]:
    """Cohen's d for two independent samples using the pooled SD."""
    a, b = _clean(a), _clean(b)
    n1, n2 = a.size, b.size
    if n1 < 2 or n2 < 2:
        return ("Cohen's d", float("nan"))
    s1, s2 = a.var(ddof=1), b.var(ddof=1)
    sp = math.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2))
    if sp == 0:
        return ("Cohen's d", float("nan"))
    return ("Cohen's d", float((a.mean() - b.mean()) / sp))


def hedges_g_independent(a, b) -> Tuple[str, float]:
    """Hedges' g = Cohen's d with the small-sample bias correction J."""
    _, d = cohens_d_independent(a, b)
    a, b = _clean(a), _clean(b)
    n = a.size + b.size
    if n <= 2 or math.isnan(d):
        return ("Hedges' g", float("nan"))
    J = 1.0 - 3.0 / (4.0 * n - 9.0)
    return ("Hedges' g", float(d * J))


def cohens_dz_paired(diff) -> Tuple[str, float]:
    """Cohen's dz for paired differences = mean(diff) / sd(diff)."""
    d = _clean(diff)
    if d.size < 2 or d.std(ddof=1) == 0:
        return ("Cohen's dz", float("nan"))
    return ("Cohen's dz", float(d.mean() / d.std(ddof=1)))


def cliffs_delta(a, b) -> Tuple[str, float]:
    """Cliff's delta = P(a>b) - P(a<b); equals the rank-biserial correlation
    for the Mann-Whitney U test. Range [-1, 1]."""
    a, b = _clean(a), _clean(b)
    if a.size == 0 or b.size == 0:
        return ("Cliff's delta", float("nan"))
    # O(n log n) via sorting b.
    b_sorted = np.sort(b)
    greater = np.searchsorted(b_sorted, a, side="left").sum()      # # b < a
    less_or_eq = np.searchsorted(b_sorted, a, side="right").sum()  # # b <= a
    ties = less_or_eq - greater
    less = a.size * b.size - less_or_eq                            # # b > a
    delta = (greater - less) / (a.size * b.size)
    return ("Cliff's delta (rank-biserial)", float(delta))


def rank_biserial_from_u(u_stat: float, n1: int, n2: int) -> Tuple[str, float]:
    """Rank-biserial correlation from a Mann-Whitney U statistic.

    ``u_stat`` must be the U for group 1 (as returned by scipy with the two
    samples passed in the same order). r = 2U/(n1 n2) - 1.
    """
    if n1 <= 0 or n2 <= 0:
        return ("rank-biserial", float("nan"))
    return ("rank-biserial", float(2.0 * u_stat / (n1 * n2) - 1.0))


def wilcoxon_rank_biserial(diff) -> Tuple[str, float]:
    """Matched-pairs rank-biserial correlation for the Wilcoxon signed-rank test.

    r = (W+ - W-) / (W+ + W-), where W+/W- are the sums of positive/negative
    signed ranks (zero differences are dropped, matching scipy's default).
    """
    d = _clean(diff)
    d = d[d != 0]
    if d.size == 0:
        return ("rank-biserial", float("nan"))
    ranks = _average_ranks(np.abs(d))
    w_pos = ranks[d > 0].sum()
    w_neg = ranks[d < 0].sum()
    total = w_pos + w_neg
    if total == 0:
        return ("rank-biserial", float("nan"))
    return ("rank-biserial", float((w_pos - w_neg) / total))


def _average_ranks(x: np.ndarray) -> np.ndarray:
    """Ranks with ties averaged (like scipy.stats.rankdata 'average')."""
    from scipy.stats import rankdata

    return rankdata(x, method="average")


def eta_squared_anova(groups) -> Tuple[str, float]:
    """eta-squared for one-way ANOVA = SS_between / SS_total."""
    groups = [_clean(g) for g in groups]
    groups = [g for g in groups if g.size > 0]
    all_vals = np.concatenate(groups) if groups else np.array([])
    if all_vals.size < 2:
        return ("eta-squared", float("nan"))
    grand = all_vals.mean()
    ss_between = sum(g.size * (g.mean() - grand) ** 2 for g in groups)
    ss_total = ((all_vals - grand) ** 2).sum()
    if ss_total == 0:
        return ("eta-squared", float("nan"))
    return ("eta-squared", float(ss_between / ss_total))


def omega_squared_anova(groups) -> Tuple[str, float]:
    """omega-squared for one-way ANOVA (less biased than eta-squared)."""
    groups = [_clean(g) for g in groups]
    groups = [g for g in groups if g.size > 0]
    k = len(groups)
    all_vals = np.concatenate(groups) if groups else np.array([])
    n = all_vals.size
    if k < 2 or n - k < 1:
        return ("omega-squared", float("nan"))
    grand = all_vals.mean()
    ss_between = sum(g.size * (g.mean() - grand) ** 2 for g in groups)
    ss_within = sum(((g - g.mean()) ** 2).sum() for g in groups)
    df_between = k - 1
    df_within = n - k
    ms_within = ss_within / df_within
    ss_total = ss_between + ss_within
    denom = ss_total + ms_within
    if denom == 0:
        return ("omega-squared", float("nan"))
    return ("omega-squared", float((ss_between - df_between * ms_within) / denom))


def epsilon_squared_kruskal(h: float, n: int, k: int) -> Tuple[str, float]:
    """epsilon-squared effect size for Kruskal-Wallis: (H - k + 1)/(n - k)."""
    if n - k <= 0:
        return ("epsilon-squared", float("nan"))
    return ("epsilon-squared", float((h - k + 1) / (n - k)))


def cramers_v(chi2: float, n: int, r: int, c: int) -> Tuple[str, float]:
    """Cramer's V for a chi-square contingency test."""
    denom = n * (min(r, c) - 1)
    if denom <= 0:
        return ("Cramer's V", float("nan"))
    return ("Cramer's V", float(math.sqrt(chi2 / denom)))
