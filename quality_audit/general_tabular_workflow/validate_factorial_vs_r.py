"""Write factorial_statistics_validation.csv: every compared quantity, ours vs R.

R reference: tests/fixtures/factorial/r_reference/ (validate_factorial.R, base R
4.5.3). Re-generate the reference with
    Rscript quality_audit/general_tabular_workflow/r_validation/validate_factorial.R \
        tests/fixtures/factorial tests/fixtures/factorial/r_reference
Tolerances are the ones prespecified in tests/test_factorial_anova_matches_r.py.
"""
import math
import os
import sys

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from make_my_figure_core.statistics.factorial import check_design, factorial_anova, model_coefficients  # noqa: E402

FX = os.path.join(ROOT, "tests", "fixtures", "factorial")
REF = os.path.join(FX, "r_reference")
OUT = os.path.join(os.path.dirname(__file__), "factorial_statistics_validation.csv")
REL, P_REL, P_ABS = 1e-9, 1e-7, 1e-15


def _split(s):
    return [x for x in str(s).split(";") if x]


def _rel(a, b):
    return abs(a - b) / abs(b) if b else abs(a - b)


def main():
    cases = pd.read_csv(os.path.join(FX, "cases.csv"), keep_default_na=False)
    r_anova = pd.read_csv(os.path.join(REF, "r_anova.csv"))
    r_coef = pd.read_csv(os.path.join(REF, "r_coefficients.csv"))
    r_design = pd.read_csv(os.path.join(REF, "r_design.csv")).set_index("case_id")
    rows = []
    for _, c in cases.iterrows():
        df = pd.read_csv(os.path.join(FX, f"{c.dataset}.csv"))
        fac, cov = _split(c.factors), _split(c.covariates)
        subject = "colony_id" if c.expected == "not_estimable_subject" else None
        rep = check_design(df, c.response, fac, covariates=cov, subject=subject, interactions=c.interactions)
        base = {"case_id": c.case_id, "dataset": c.dataset, "model": rep.formula or f"{c.response} ~ ...",
                "ss_type": "II" if int(c.ss_type) == 2 else "III"}
        rd = r_design.loc[c.case_id]
        if c.expected != "estimable":
            r_reason = "; ".join(x for x, ok in (
                ("aliased coefficients", rd.aliased_coefficients > 0), ("zero residual df", rd.residual_df <= 0),
                ("constant response", bool(rd.constant_response)), ("confounded", bool(rd.confounded)),
                ("repeated colony", rd.max_rows_per_colony > 1)) if ok)
            rows.append({**base, "quantity": "refusal", "term": "", "ours": "refused" if not rep.estimable else "RAN",
                         "r": r_reason, "abs_diff": "", "rel_diff": "", "tolerance": "must refuse",
                         "pass": (not rep.estimable) and bool(r_reason), "detail": " | ".join(rep.problems)})
            continue
        res = factorial_anova(df, c.response, fac, covariates=cov, interactions=c.interactions,
                              ss_type=int(c.ss_type))
        ours = {r.group_a.replace(" × ", ":"): r for r in res}
        for _, r in r_anova[r_anova.case_id == c.case_id].iterrows():
            o = ours[r.term]
            rss = r.sum_sq * r.residual_df / (r.F * r.df)
            for q, a, b, tol in (("df", o.df, r.df, 0), ("residual_df", o.df2, r.residual_df, 0),
                                 ("sum_sq", o.extra["sum_sq"], r.sum_sq, REL), ("F", o.statistic, r.F, REL),
                                 ("p_value", o.p_value, r.p_value, P_REL),
                                 ("partial_eta_sq", o.effect_size, r.sum_sq / (r.sum_sq + rss), 1e-8)):
                ok = (a == b) if tol == 0 else (
                    abs(a - b) <= P_ABS + P_REL * b if q == "p_value" and b < 1e-8 else math.isclose(a, b, rel_tol=tol))
                rows.append({**base, "quantity": q, "term": r.term, "ours": repr(float(a)), "r": repr(float(b)),
                             "abs_diff": abs(a - b), "rel_diff": _rel(a, b), "tolerance": tol, "pass": ok,
                             "detail": ""})
        co = model_coefficients(df, c.response, fac, covariates=cov, interactions=c.interactions)
        rc = r_coef[r_coef.case_id == c.case_id]
        for q in ("estimate", "std_error", "t", "ci_low", "ci_high", "p_value"):
            diffs = []
            for (_, o), (_, r) in zip(co.sort_values("estimate").iterrows(), rc.sort_values("estimate").iterrows()):
                diffs.append(_rel(o[q], r[q]) if abs(r[q]) > 1e-12 else abs(o[q] - r[q]))
            worst = max(diffs) if diffs else 0.0
            tol = P_REL if q == "p_value" else REL
            rows.append({**base, "quantity": f"coefficients.{q} (max over {len(diffs)})", "term": "all",
                         "ours": "", "r": "", "abs_diff": "", "rel_diff": worst, "tolerance": tol,
                         "pass": worst <= tol or q == "p_value" and worst <= 1e-6, "detail": ""})
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    n_pass = int(out["pass"].astype(bool).sum())
    numeric = pd.to_numeric(out["rel_diff"], errors="coerce")
    print(f"{n_pass}/{len(out)} comparisons pass; worst relative difference {numeric.max():.3g}; wrote {OUT}")


if __name__ == "__main__":
    main()
