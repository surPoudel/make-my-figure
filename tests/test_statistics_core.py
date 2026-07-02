"""Correctness tests for the statistics engine.

Each test is pinned against scipy/statsmodels or a hand-computed value so a
regression in a formula is caught immediately.
"""

import math

import numpy as np
import pytest
from scipy import stats

from make_my_figure_core.statistics import (
    adjust_pvalues,
    effect_sizes as es,
)
from make_my_figure_core.statistics import anova, categorical, nonparametric, pairwise, survival
from make_my_figure_core.statistics.models import StatsError
from make_my_figure_core.statistics import validators as val
import pandas as pd

RNG = np.random.default_rng(12345)
A = RNG.normal(0.0, 1.0, 25)
B = RNG.normal(0.7, 1.3, 22)
PX = RNG.normal(0.0, 1.0, 18)
PY = PX + RNG.normal(0.4, 0.5, 18)


# --- two-group tests vs scipy ----------------------------------------------

def test_students_t_matches_scipy():
    r = pairwise.students_t(A, B)
    t, p = stats.ttest_ind(A, B, equal_var=True)
    assert r.statistic == pytest.approx(t)
    assert r.p_value == pytest.approx(p)
    assert r.df == len(A) + len(B) - 2
    assert r.effect_size_name == "Cohen's d"


def test_welch_t_matches_scipy():
    r = pairwise.welch_t(A, B)
    t, p = stats.ttest_ind(A, B, equal_var=False)
    assert r.statistic == pytest.approx(t)
    assert r.p_value == pytest.approx(p)
    # Welch df between the smaller n-1 and n1+n2-2.
    assert 1 < r.df < len(A) + len(B)


def test_mann_whitney_matches_scipy():
    r = pairwise.mann_whitney(A, B)
    u, p = stats.mannwhitneyu(A, B, alternative="two-sided")
    assert r.statistic == pytest.approx(u)
    assert r.p_value == pytest.approx(p)


def test_paired_t_matches_scipy():
    r = pairwise.paired_t(PX, PY)
    t, p = stats.ttest_rel(PX, PY)
    assert r.statistic == pytest.approx(t)
    assert r.p_value == pytest.approx(p)
    assert r.paired is True


def test_wilcoxon_matches_scipy():
    r = pairwise.wilcoxon_signed_rank(PX, PY)
    w, p = stats.wilcoxon(PX, PY)
    assert r.statistic == pytest.approx(w)
    assert r.p_value == pytest.approx(p)


def test_pearson_matches_scipy_with_ci():
    r = pairwise.pearson(PX, PY)
    res = stats.pearsonr(PX, PY)
    assert r.statistic == pytest.approx(res.statistic)
    assert r.p_value == pytest.approx(res.pvalue)
    # CI present and brackets the estimate.
    assert r.confidence_interval_low < r.statistic < r.confidence_interval_high


def test_spearman_and_regression_match_scipy():
    r = pairwise.spearman(PX, PY)
    res = stats.spearmanr(PX, PY)
    assert r.statistic == pytest.approx(res.statistic)
    lr = pairwise.linear_regression(PX, PY)
    ref = stats.linregress(PX, PY)
    assert lr.statistic == pytest.approx(ref.slope)
    assert lr.p_value == pytest.approx(ref.pvalue)
    assert lr.effect_size == pytest.approx(ref.rvalue ** 2)


# --- ANOVA / Kruskal --------------------------------------------------------

def test_one_way_anova_matches_scipy():
    g = [RNG.normal(m, 1.0, 14) for m in (0.0, 0.5, 1.1)]
    r = anova.one_way_anova(["A", "B", "C"], g)
    F, p = stats.f_oneway(*g)
    assert r.statistic == pytest.approx(F)
    assert r.p_value == pytest.approx(p)
    assert r.df == 2 and r.df2 == sum(len(x) for x in g) - 3


def test_kruskal_matches_scipy():
    g = [RNG.normal(m, 1.0, 14) for m in (0.0, 0.5, 1.1)]
    r = nonparametric.kruskal_wallis(["A", "B", "C"], g)
    H, p = stats.kruskal(*g)
    assert r.statistic == pytest.approx(H)
    assert r.p_value == pytest.approx(p)


def test_two_way_anova_terms():
    df = pd.DataFrame({
        "y": np.r_[RNG.normal(1, .3, 10), RNG.normal(2, .3, 10),
                   RNG.normal(1, .3, 10), RNG.normal(1.2, .3, 10)],
        "A": ["WT"] * 20 + ["KO"] * 20,
        "B": (["V"] * 10 + ["D"] * 10) * 2,
    })
    results = anova.two_way_anova(df, "y", "A", "B")
    labels = {r.group_a for r in results}
    assert labels == {"A", "B", "A x B"}
    for r in results:
        assert r.p_value is not None


def test_rm_anova_matches_statsmodels():
    from statsmodels.stats.anova import AnovaRM

    rows = []
    for s in range(10):
        base = RNG.normal(0, 1)
        for t, add in [("t0", 0), ("t1", 1.0), ("t2", 2.0)]:
            rows.append({"subj": s, "t": t, "y": base + add + RNG.normal(0, .3)})
    df = pd.DataFrame(rows)
    r = anova.repeated_measures_anova(df, "y", "subj", "t")
    ref = AnovaRM(df, "y", "subj", within=["t"]).fit().anova_table
    assert r.statistic == pytest.approx(ref.loc["t", "F Value"])
    assert r.p_value == pytest.approx(ref.loc["t", "Pr > F"])


def test_rm_anova_rejects_incomplete_design():
    df = pd.DataFrame({"subj": [1, 1, 2], "t": ["a", "b", "a"], "y": [1.0, 2.0, 3.0]})
    with pytest.raises(StatsError):
        anova.repeated_measures_anova(df, "y", "subj", "t")


# --- categorical ------------------------------------------------------------

def test_chi_square_matches_scipy():
    tab = np.array([[12, 20], [28, 15]])
    r = categorical.chi_square(tab, correction=False)
    c, p, dof, _ = stats.chi2_contingency(tab, correction=False)
    assert r.statistic == pytest.approx(c)
    assert r.p_value == pytest.approx(p)
    assert r.df == dof


def test_chi_square_warns_low_expected():
    tab = np.array([[1, 2], [3, 40]])
    r = categorical.chi_square(tab)
    assert any("expected count" in w for w in r.warnings)


def test_fisher_matches_scipy():
    tab = np.array([[8, 2], [1, 9]])
    r = categorical.fishers_exact(tab)
    odds, p = stats.fisher_exact(tab)
    assert r.p_value == pytest.approx(p)
    assert r.estimate == pytest.approx(odds)


def test_fisher_large_table_handled():
    # scipy >= 1.15 supports r x c Fisher; older versions warn. Either way the
    # engine must not crash and must give a p-value OR an explicit warning.
    tab = np.array([[5, 6, 7], [8, 9, 10], [3, 2, 1]])
    r = categorical.fishers_exact(tab)
    assert (r.p_value is not None and r.p_value == r.p_value) or any("2x2" in w for w in r.warnings)


# --- survival ---------------------------------------------------------------

def test_logrank_matches_statsmodels():
    import statsmodels.api as sm

    t = np.r_[RNG.exponential(10, 30), RNG.exponential(18, 32)]
    e = RNG.binomial(1, 0.8, 62)
    g = np.array([0] * 30 + [1] * 32)
    df = pd.DataFrame({"t": t, "e": e, "g": g})
    r = survival.logrank_test(df, "t", "e", "g")
    chi2, p = sm.duration.survdiff(df["t"], df["e"], df["g"])
    assert r.statistic == pytest.approx(chi2, rel=1e-6)
    assert r.p_value == pytest.approx(p, rel=1e-6)


def test_cox_matches_statsmodels():
    from statsmodels.duration.hazard_regression import PHReg

    t = np.r_[RNG.exponential(10, 30), RNG.exponential(20, 32)]
    e = RNG.binomial(1, 0.8, 62)
    g = np.array([0] * 30 + [1] * 32)
    df = pd.DataFrame({"t": t, "e": e, "g": g})
    res = survival.cox_hazard_ratio(df, "t", "e", "g")
    x = (df["g"] == 1).astype(float).to_numpy().reshape(-1, 1)
    fit = PHReg(df["t"].to_numpy(float), x, status=df["e"].to_numpy(float)).fit()
    assert res[0].estimate == pytest.approx(math.exp(fit.params[0]))
    assert any("proportional-hazards" in w.lower() for w in res[0].warnings)


# --- effect sizes -----------------------------------------------------------

def test_cohens_d_hand_value():
    a = np.array([2.0, 4, 6, 8, 10])
    b = np.array([1.0, 2, 3, 4, 5])
    _, d = es.cohens_d_independent(a, b)
    sp = math.sqrt((4 * a.var(ddof=1) + 4 * b.var(ddof=1)) / 8)
    assert d == pytest.approx((a.mean() - b.mean()) / sp)


def test_hedges_g_smaller_than_d():
    _, d = es.cohens_d_independent(A, B)
    _, g = es.hedges_g_independent(A, B)
    assert abs(g) < abs(d)


def test_cliffs_delta_bounds_and_sign():
    _, delta = es.cliffs_delta([5, 6, 7, 8], [1, 2, 3, 4])
    assert delta == pytest.approx(1.0)
    _, delta2 = es.cliffs_delta([1, 2, 3, 4], [5, 6, 7, 8])
    assert delta2 == pytest.approx(-1.0)


def test_cramers_v_range():
    tab = np.array([[10, 0], [0, 10]])
    chi2, _, _, _ = stats.chi2_contingency(tab, correction=False)
    _, v = es.cramers_v(chi2, 20, 2, 2)
    assert v == pytest.approx(1.0)


# --- multiple testing -------------------------------------------------------

@pytest.mark.parametrize("method,sm_method", [
    ("bonferroni", "bonferroni"), ("holm", "holm"), ("benjamini_hochberg", "fdr_bh")])
def test_correction_matches_statsmodels(method, sm_method):
    from statsmodels.stats.multitest import multipletests

    pv = [0.001, 0.008, 0.02, 0.04, 0.2, 0.5]
    adj, rej, meth = adjust_pvalues(pv, method)
    _, sm_adj, _, _ = multipletests(pv, method=sm_method)
    assert np.allclose(adj, sm_adj)


def test_correction_handles_missing():
    adj, rej, meth = adjust_pvalues([0.01, None, float("nan"), 0.02], "bonferroni")
    assert adj[1] is None and adj[2] is None
    assert adj[0] == pytest.approx(0.02)  # m = 2 valid


def test_bonferroni_hand_value():
    adj, _, _ = adjust_pvalues([0.01, 0.02, 0.03], "bonferroni")
    assert adj == pytest.approx([0.03, 0.06, 0.09])


# --- validators / design errors --------------------------------------------

def test_paired_arrays_requires_matching_ids():
    df = pd.DataFrame({"id": [1, 2, 3, 1, 2], "cond": ["a", "a", "a", "b", "b"],
                       "v": [1.0, 2, 3, 4, 5]})
    a, b, ids = val.paired_arrays(df, "v", "cond", "a", "b", "id", context="test")
    assert list(ids) == [1, 2]  # id 3 has no 'b' partner


def test_paired_arrays_rejects_duplicate_ids():
    df = pd.DataFrame({"id": [1, 1], "cond": ["a", "a"], "v": [1.0, 2.0]})
    with pytest.raises(StatsError):
        val.paired_arrays(df, "v", "cond", "a", "b", "id", context="test")


def test_two_group_requires_min_n():
    df = pd.DataFrame({"g": ["a", "b"], "v": [1.0, 2.0]})
    with pytest.raises(StatsError):
        val.two_group_arrays(df, "v", "g", "a", "b", context="test")


def test_missing_values_dropped_consistently():
    a = np.array([1.0, 2, np.nan, 4])
    b = np.array([2.0, np.nan, 6, 8])
    r = pairwise.students_t(a, b)
    # finite values only: 3 per group after dropping the NaN in each.
    assert r.n_total == 3 + 3
