"""Nonparametric multi-group tests: Kruskal-Wallis and Dunn's post-hoc.

Dunn's test is implemented natively (no scikit-posthocs dependency) using the
standard z-statistic with a shared tie correction, and its p-values are passed
through the multiple-testing engine like any other family.
"""

from __future__ import annotations

from typing import Any, List, Optional

import numpy as np
from scipy import stats

from make_my_figure_core.statistics import effect_sizes as es
from make_my_figure_core.statistics._versions import software_versions
from make_my_figure_core.statistics.models import StatResult


def kruskal_wallis(levels: List[Any], arrays: List[np.ndarray], *,
                   value_col=None, group_col=None, alpha: float = 0.05) -> StatResult:
    """Kruskal-Wallis H test across >= 3 groups."""
    arrays = [np.asarray(a, float) for a in arrays]
    arrays = [a[np.isfinite(a)] for a in arrays]
    k = len(arrays)
    n = int(sum(a.size for a in arrays))
    res = stats.kruskal(*arrays)
    r = StatResult(test_id="kruskal_wallis", test_name="Kruskal-Wallis test",
                   comparison_type="omnibus", value_column=value_col,
                   grouping_columns=[group_col] if group_col else [],
                   n_total=n, n_by_group={str(lv): int(a.size) for lv, a in zip(levels, arrays)},
                   software_versions=software_versions())
    r.statistic = float(res.statistic); r.statistic_name = "H"
    r.df = float(k - 1); r.p_value = float(res.pvalue)
    name, eps = es.epsilon_squared_kruskal(float(res.statistic), n, k)
    r.effect_size_name, r.effect_size = name, eps
    r.extra = {"levels": [str(lv) for lv in levels]}
    r.assumptions_checked = ["independent observations",
                             "similar distribution shapes across groups"]
    return r


def dunn_posthoc(levels: List[Any], arrays: List[np.ndarray], *,
                 value_col=None, group_col=None) -> List[StatResult]:
    """Dunn's test for all pairwise comparisons after Kruskal-Wallis.

    Returns raw (uncorrected) p-values as StatResults; the caller applies the
    chosen multiple-testing correction across the family.
    """
    arrays = [np.asarray(a, float) for a in arrays]
    arrays = [a[np.isfinite(a)] for a in arrays]
    ns = [a.size for a in arrays]
    N = sum(ns)
    all_vals = np.concatenate(arrays)
    ranks = stats.rankdata(all_vals)
    # Mean rank per group.
    mean_ranks = []
    start = 0
    for n in ns:
        mean_ranks.append(ranks[start:start + n].mean())
        start += n
    # Tie correction term.
    _, counts = np.unique(all_vals, return_counts=True)
    ties = float(np.sum(counts ** 3 - counts))
    sigma_common = (N * (N + 1) / 12.0) - ties / (12.0 * (N - 1)) if N > 1 else float("nan")

    results: List[StatResult] = []
    for i in range(len(arrays)):
        for j in range(i + 1, len(arrays)):
            se = np.sqrt(sigma_common * (1.0 / ns[i] + 1.0 / ns[j]))
            if se == 0 or not np.isfinite(se):
                continue
            z = (mean_ranks[i] - mean_ranks[j]) / se
            p = float(2 * stats.norm.sf(abs(z)))
            r = StatResult(test_id="dunn", test_name="Dunn's test (post-hoc)",
                           comparison_type="two_group", value_column=value_col,
                           grouping_columns=[group_col] if group_col else [],
                           group_a=str(levels[i]), group_b=str(levels[j]),
                           n_by_group={str(levels[i]): int(ns[i]), str(levels[j]): int(ns[j])},
                           n_total=int(ns[i] + ns[j]),
                           software_versions=software_versions())
            r.statistic = float(z); r.statistic_name = "z"; r.p_value = p
            r.effect_size_name = "rank-biserial"
            _, rb = es.cliffs_delta(arrays[i], arrays[j])
            r.effect_size = rb
            r.extra = {"posthoc_of": "kruskal_wallis"}
            results.append(r)
    return results
