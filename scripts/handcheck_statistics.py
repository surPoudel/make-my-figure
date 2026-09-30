"""Independent hand-check validation of MakeMyFigure statistics.

These fixtures do NOT call SciPy/statsmodels on the reference side. Expected values are
computed from closed-form arithmetic written out explicitly here, so they test the
mathematics rather than the wiring. This is a different and stronger class of evidence
than the oracle comparison in validate_statistics_for_manuscript.py.

Run: PYTHONPATH=. python scripts/handcheck_statistics.py
Writes manuscript/final_editorial_revision/handcheck_validation.csv
"""
from __future__ import annotations

import csv
import math
import os

import numpy as np
import pandas as pd

from make_my_figure_core.statistics.runner import run_statistics
from make_my_figure_core.statistics import categorical
from make_my_figure_core.statistics.multiple_testing import adjust_pvalues

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "manuscript", "final_editorial_revision")
os.makedirs(OUT, exist_ok=True)
ROWS = []


def rec(name, expected, observed, tol, how):
    diff = abs(float(observed) - float(expected))
    ROWS.append({"check": name, "expected_hand_computed": f"{expected:.10g}",
                 "observed_from_app": f"{observed:.10g}", "abs_difference": f"{diff:.3e}",
                 "tolerance": f"{tol:.1e}",
                 "status": "PASS" if diff <= tol else "FAIL",
                 "how_expected_was_derived": how})
    print(f"{'PASS' if diff <= tol else 'FAIL':5} {name:34} |Δ|={diff:.2e}")


def main() -> int:
    # ---- 1. Student's t on a tiny hand-computable fixture -------------------
    # a = [1,2,3,4,5]  mean 3, var 2.5 ; b = [6,7,8,9,10] mean 8, var 2.5
    # pooled sd = sqrt(2.5) ; se = sqrt(2.5*(1/5+1/5)) = 1 ; t = (3-8)/1 = -5, df=8
    a = [1, 2, 3, 4, 5]
    b = [6, 7, 8, 9, 10]
    df = pd.DataFrame({"value": a + b, "group": ["A"] * 5 + ["B"] * 5})
    spec = {"enabled": True, "test": "students_t", "comparison_mode": "all_pairs",
            "correction": "none", "value_column": "value", "group_column": "group"}
    r = run_statistics(df, spec, plot_type="boxplot_or_violin_with_points",
                       mapping={"x": "group", "y": "value"}).results[0]
    rec("students_t statistic (t=-5, df=8)", -5.0, r.statistic, 1e-12,
        "pooled sd = sqrt(2.5); se = sqrt(2.5*(1/5+1/5)) = 1; t = (3-8)/1 = -5")
    rec("students_t degrees of freedom", 8.0, float(r.df), 1e-12, "n1+n2-2 = 8")

    # ---- 2. Effect size by hand ---------------------------------------------
    # NOTE (audit finding): for students_t the engine reports Cohen's d, not Hedges' g.
    # An earlier draft of this fixture asserted the bias-corrected value against the
    # reported field and failed; the software was right and the fixture was wrong.
    # Both quantities are therefore checked explicitly and separately below.
    d_hand = -5.0 / math.sqrt(2.5)               # = -3.16227766...
    assert r.effect_size_name == "Cohen's d", f"unexpected effect name {r.effect_size_name}"
    rec("Cohen's d as reported (students_t)", d_hand, r.effect_size, 1e-12,
        "d = (mean_a - mean_b)/pooled_sd = -5/sqrt(2.5)")
    from make_my_figure_core.statistics.effect_sizes import hedges_g_independent
    _name, g_app = hedges_g_independent(a, b)
    J = 1 - 3 / (4 * (len(a) + len(b) - 2) - 1)  # J with df = n1+n2-2 = 8
    rec("Hedges' g via effect_sizes API", d_hand * J, g_app, 1e-9,
        "g = d * J, J = 1 - 3/(4*df-1), df = 8")

    # ---- 3. Pearson r on an exactly-linear fixture --------------------------
    # y = 2x exactly -> r = 1
    dl = pd.DataFrame({"x": [1.0, 2, 3, 4, 5], "y": [2.0, 4, 6, 8, 10]})
    rp = run_statistics(dl, {"enabled": True, "test": "pearson", "correction": "none",
                             "x_column": "x", "y_column": "y"},
                        plot_type="scatterplot_with_regression",
                        mapping={"x": "x", "y": "y"}).results[0]
    rec("pearson r on exact line y=2x", 1.0, rp.estimate if rp.estimate is not None
        else rp.statistic, 1e-12, "perfectly collinear data => r = 1 by definition")

    # ---- 4. Chi-square on a hand-computable 2x2 -----------------------------
    # [[10,10],[10,10]] -> all expected = 10 -> chi2 = 0
    r0 = categorical.chi_square(np.array([[10, 10], [10, 10]]), correction=False)
    rec("chi-square, perfectly balanced 2x2", 0.0, r0.statistic, 1e-12,
        "all expected counts equal observed => sum((O-E)^2/E) = 0")
    # [[20,10],[10,20]] : E = 15 each; chi2 = 4*(25/15) = 6.6666667
    r1 = categorical.chi_square(np.array([[20, 10], [10, 20]]), correction=False)
    rec("chi-square [[20,10],[10,20]]", 4 * (25 / 15), r1.statistic, 1e-10,
        "E=15 in all cells; chi2 = 4 * (5^2/15) = 6.666...")

    # ---- 5. Benjamini-Hochberg by hand --------------------------------------
    # p = [0.01, 0.02, 0.03, 0.04]; m=4
    # raw p*m/i = [0.04, 0.04, 0.04, 0.04] -> all adjusted = 0.04 after monotonicity
    p = [0.01, 0.02, 0.03, 0.04]
    adj, _rej, _m = adjust_pvalues(list(p), "benjamini_hochberg")
    for i, val in enumerate(adj):
        rec(f"BH adjusted p[{i}] (all = 0.04)", 0.04, float(val), 1e-12,
            "p_(i)*m/i = 0.04 for every i; monotone step-up leaves all at 0.04")

    # ---- 6. Bonferroni by hand ----------------------------------------------
    adjb, _r, _m = adjust_pvalues([0.01, 0.02], "bonferroni")
    rec("Bonferroni adjusted p[0] (0.01*2)", 0.02, float(adjb[0]), 1e-12,
        "p * m = 0.01 * 2 = 0.02")

    path = os.path.join(OUT, "handcheck_validation.csv")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ROWS[0].keys()))
        w.writeheader(); w.writerows(ROWS)
    npass = sum(1 for r_ in ROWS if r_["status"] == "PASS")
    print(f"\n{npass}/{len(ROWS)} hand-checks PASS -> {os.path.relpath(path, ROOT)}")
    return 0 if npass == len(ROWS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
