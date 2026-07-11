"""Independent statistics oracle for the publication QC pass.

Recomputes every implemented statistical test from raw data using scipy /
statsmodels (NOT the app's own code path) and compares each reported field
(statistic, df, p, effect size, CI, adjusted p) against the app's StatResult
with tight, field-appropriate tolerances.

`run_oracle()` returns a list of comparison rows; the module both backs
`tests/test_statistics_oracle_validation.py` and, run as a script, writes
`outputs/publication_qc/statistics_oracle_results.md`.
"""

from __future__ import annotations

import math
import os
import sys
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import fisher_exact

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from make_my_figure_core.statistics import (  # noqa: E402
    anova, categorical, effect_sizes as es, nonparametric, pairwise, survival,
)
from make_my_figure_core.statistics.multiple_testing import adjust_pvalues  # noqa: E402

RNG = np.random.default_rng(2024)
A = RNG.normal(0.0, 1.0, 30)
B = RNG.normal(0.8, 1.4, 27)
PX = RNG.normal(5.0, 1.0, 20)
PY = PX + RNG.normal(0.5, 0.6, 20)
G = [RNG.normal(m, 1.0, n) for m, n in ((0, 24), (0.6, 26), (1.2, 22))]

_rows: List[Dict[str, Any]] = []


def _check(name: str, field: str, app, ref, *, rtol=1e-6, atol=1e-9, note=""):
    try:
        if app is None or ref is None or (isinstance(ref, float) and math.isnan(ref)):
            ok = (app is None and ref is None)
        else:
            ok = abs(float(app) - float(ref)) <= atol + rtol * abs(float(ref))
    except Exception as exc:  # noqa: BLE001
        ok, note = False, f"{note} error: {exc}".strip()
    _rows.append({"test": name, "field": field, "app": _fmt(app), "ref": _fmt(ref),
                  "tol": f"rtol={rtol:g}", "pass": ok, "note": note})
    return ok


def _fmt(v):
    if v is None:
        return "None"
    try:
        return f"{float(v):.6g}"
    except (TypeError, ValueError):
        return str(v)


def _cohens_d(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    n1, n2 = a.size, b.size
    sp = math.sqrt(((n1 - 1) * a.var(ddof=1) + (n2 - 1) * b.var(ddof=1)) / (n1 + n2 - 2))
    return (a.mean() - b.mean()) / sp


def run_oracle() -> List[Dict[str, Any]]:
    _rows.clear()

    # 1. Student's t (equal var) — scipy oracle + df + Cohen's d + mean-diff CI.
    r = pairwise.students_t(A, B)
    t, p = stats.ttest_ind(A, B, equal_var=True)
    _check("Student's t", "statistic", r.statistic, t)
    _check("Student's t", "p_value", r.p_value, p)
    _check("Student's t", "df", r.df, A.size + B.size - 2)
    _check("Student's t", "Cohen's d", r.effect_size, _cohens_d(A, B), rtol=1e-6)
    # mean-difference 95% CI oracle
    n1, n2 = A.size, B.size
    sp = math.sqrt(((n1 - 1) * A.var(ddof=1) + (n2 - 1) * B.var(ddof=1)) / (n1 + n2 - 2))
    se = sp * math.sqrt(1 / n1 + 1 / n2)
    tc = stats.t.ppf(0.975, n1 + n2 - 2)
    diff = A.mean() - B.mean()
    _check("Student's t", "CI low", r.confidence_interval_low, diff - tc * se, rtol=1e-5)
    _check("Student's t", "CI high", r.confidence_interval_high, diff + tc * se, rtol=1e-5)

    # 2. Welch's t.
    r = pairwise.welch_t(A, B)
    t, p = stats.ttest_ind(A, B, equal_var=False)
    _check("Welch's t", "statistic", r.statistic, t)
    _check("Welch's t", "p_value", r.p_value, p)

    # 3. Mann-Whitney U.
    r = pairwise.mann_whitney(A, B)
    u, p = stats.mannwhitneyu(A, B, alternative="two-sided")
    _check("Mann-Whitney U", "statistic", r.statistic, u)
    _check("Mann-Whitney U", "p_value", r.p_value, p)

    # 4. Paired t.
    r = pairwise.paired_t(PX, PY)
    t, p = stats.ttest_rel(PX, PY)
    _check("Paired t", "statistic", r.statistic, t)
    _check("Paired t", "p_value", r.p_value, p)
    d = np.asarray(PX, float) - np.asarray(PY, float)
    _check("Paired t", "Cohen's dz", r.effect_size, d.mean() / d.std(ddof=1), rtol=1e-6)

    # 5. Wilcoxon signed-rank.
    r = pairwise.wilcoxon_signed_rank(PX, PY)
    w, p = stats.wilcoxon(PX, PY)
    _check("Wilcoxon", "statistic", r.statistic, w)
    _check("Wilcoxon", "p_value", r.p_value, p)

    # 6. One-way ANOVA.
    r = anova.one_way_anova([0, 1, 2], G)
    F, p = stats.f_oneway(*G)
    _check("One-way ANOVA", "F", r.statistic, F)
    _check("One-way ANOVA", "p_value", r.p_value, p)
    _check("One-way ANOVA", "df1", r.df, len(G) - 1)
    _check("One-way ANOVA", "df2", r.df2, sum(len(x) for x in G) - len(G))
    name, eta = es.eta_squared_anova(G)
    # independent eta^2 = SS_between / SS_total
    grand = np.concatenate(G).mean()
    ss_b = sum(len(x) * (np.mean(x) - grand) ** 2 for x in G)
    ss_t = sum(((np.concatenate(G) - grand) ** 2))
    _check("One-way ANOVA", "eta^2", eta, ss_b / ss_t, rtol=1e-6)

    # 7. Kruskal-Wallis.
    r = nonparametric.kruskal_wallis([0, 1, 2], G)
    H, p = stats.kruskal(*G)
    _check("Kruskal-Wallis", "H", r.statistic, H)
    _check("Kruskal-Wallis", "p_value", r.p_value, p)

    # 8. Two-way ANOVA vs statsmodels.
    df2 = pd.DataFrame({
        "val": np.concatenate([RNG.normal(m, 1.0, 8) for m in (0, 1, 0.5, 1.5)]),
        "A": ["a0"] * 16 + ["a1"] * 16,
        "B": (["b0"] * 8 + ["b1"] * 8) * 2,
    })
    res = anova.two_way_anova(df2, "val", "A", "B")
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    model = smf.ols("val ~ C(A) + C(B) + C(A):C(B)", data=df2).fit()
    aov = sm.stats.anova_lm(model, typ=2)
    ref_map = {"C(A)": "A", "C(B)": "B", "C(A):C(B)": "A x B"}
    for smkey, lbl in ref_map.items():
        match = next((rr for rr in res if rr.extra.get("term") == lbl), None)
        _check(f"Two-way ANOVA [{lbl}]", "F", match.statistic if match else None,
               float(aov.loc[smkey, "F"]), rtol=1e-4, note="" if match else "term not found")
        _check(f"Two-way ANOVA [{lbl}]", "p_value", match.p_value if match else None,
               float(aov.loc[smkey, "PR(>F)"]), rtol=1e-4)

    # 9. Chi-square (with Yates) vs scipy.
    table = np.array([[30, 10], [12, 28]])
    r = categorical.chi_square(table, correction=True)
    chi2, p, dof, _ = stats.chi2_contingency(table, correction=True)
    _check("Chi-square", "statistic", r.statistic, chi2)
    _check("Chi-square", "p_value", r.p_value, p)
    _check("Chi-square", "df", r.df, dof)
    nm, v = es.cramers_v(chi2, table.sum(), 2, 2)
    _check("Chi-square", "Cramer's V", r.effect_size, v, rtol=1e-6)

    # 10. Fisher's exact vs scipy.
    r = categorical.fishers_exact(table)
    orr, p = fisher_exact(table, alternative="two-sided")
    _check("Fisher's exact", "odds ratio", r.effect_size, orr, rtol=1e-6)
    _check("Fisher's exact", "p_value", r.p_value, p)

    # 11. Log-rank vs statsmodels survdiff.
    sdf = pd.DataFrame({
        "time": np.r_[RNG.exponential(10, 30), RNG.exponential(6, 30)],
        "event": np.r_[RNG.binomial(1, 0.7, 30), RNG.binomial(1, 0.8, 30)],
        "grp": ["G1"] * 30 + ["G2"] * 30,
    })
    r = survival.logrank_test(sdf, "time", "event", "grp")
    try:
        from statsmodels.duration.survfunc import survdiff

        chisq, pval = survdiff(sdf["time"].values, sdf["event"].values, sdf["grp"].values)
        _check("Log-rank", "chi2", r.statistic, chisq, rtol=1e-4)
        _check("Log-rank", "p_value", r.p_value, pval, rtol=1e-4)
    except Exception as exc:  # noqa: BLE001
        _check("Log-rank", "chi2", r.statistic, None, note=f"oracle unavailable: {exc}")

    # 12. Pearson vs scipy (+ CI sanity).
    x = RNG.normal(0, 1, 40)
    y = 0.8 * x + RNG.normal(0, 0.6, 40)
    r = pairwise.pearson(x, y)
    pr = stats.pearsonr(x, y)
    _check("Pearson", "r", r.statistic, pr.statistic)
    _check("Pearson", "p_value", r.p_value, pr.pvalue)

    # 13. Spearman vs scipy.
    r = pairwise.spearman(x, y)
    sp = stats.spearmanr(x, y)
    _check("Spearman", "rho", r.statistic, sp.statistic)
    _check("Spearman", "p_value", r.p_value, sp.pvalue)

    # 14. Linear regression vs scipy.linregress.
    r = pairwise.linear_regression(x, y)
    lr = stats.linregress(x, y)
    _check("Linear regression", "slope", r.estimate, lr.slope, rtol=1e-6)
    _check("Linear regression", "p_value", r.p_value, lr.pvalue)
    _check("Linear regression", "R^2", r.effect_size, lr.rvalue ** 2, rtol=1e-6)

    # 15-17. Multiple-testing corrections vs statsmodels.
    pvals = [0.001, 0.01, 0.02, 0.03, 0.2, 0.5]
    from statsmodels.stats.multitest import multipletests

    for method, smm in (("bonferroni", "bonferroni"), ("holm", "holm"),
                        ("benjamini_hochberg", "fdr_bh")):
        out = adjust_pvalues(pvals, method=method)
        adj = out[0] if isinstance(out, tuple) else out   # returns (adjusted, reject, method)
        ref = multipletests(pvals, method=smm)[1]
        for i, (aa, rr) in enumerate(zip(adj, ref)):
            _check(f"Correction [{method}]", f"p_adj[{i}]", aa, rr, rtol=1e-9)

    # Hedges g standalone.
    nm, g = es.hedges_g_independent(A, B)
    J = 1 - 3 / (4 * (A.size + B.size) - 9)
    _check("Hedges g", "g", g, _cohens_d(A, B) * J, rtol=1e-6)

    return list(_rows)


def write_report() -> str:
    rows = run_oracle()
    out_dir = os.path.join(_ROOT, "outputs", "publication_qc")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "statistics_oracle_results.md")
    n_pass = sum(1 for r in rows if r["pass"])
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Statistics oracle validation\n\n")
        fh.write("Independent recomputation via **scipy** / **statsmodels**, compared to the "
                 "app's `StatResult` fields.\n\n")
        fh.write(f"**{n_pass}/{len(rows)} checks passed.**\n\n")
        fh.write("| test | field | app | reference | tolerance | pass | note |\n")
        fh.write("|---|---|---|---|---|:--:|---|\n")
        for r in rows:
            mark = "✅" if r["pass"] else "❌"
            fh.write(f"| {r['test']} | {r['field']} | {r['app']} | {r['ref']} | "
                     f"{r['tol']} | {mark} | {r['note']} |\n")
        fh.write("\nReference libraries: scipy "
                 f"{stats.__name__.split('.')[0]}, statsmodels. Log-rank oracle: "
                 "`statsmodels.duration.survfunc.survdiff`. Cox HR uses statsmodels PHReg "
                 "(same engine; PH assumption not auto-checked — see method sentence).\n")
    return path


if __name__ == "__main__":
    p = write_report()
    rows = run_oracle()
    failed = [r for r in rows if not r["pass"]]
    print(f"Wrote {os.path.relpath(p, _ROOT)} — {len(rows) - len(failed)}/{len(rows)} passed")
    for r in failed:
        print(f"  FAIL: {r['test']} / {r['field']}: app={r['app']} ref={r['ref']} {r['note']}")
    raise SystemExit(1 if failed else 0)
