"""Factorial ANOVA agrees with an independent base-R implementation.

Reference values in ``tests/fixtures/factorial/r_reference/`` were produced by
``quality_audit/general_tabular_workflow/r_validation/validate_factorial.R``
(R 4.5.3, base R only): Type II sums of squares from nested-model comparisons,
Type III from ``drop1`` with sum-to-zero contrasts, coefficients from
``summary(lm)`` / ``confint``. The datasets are SYNTHETIC
(``tests/fixtures/factorial/generate.py``).

Tolerances are fixed in advance and are not to be loosened to make a test
pass: relative 1e-9 for sums of squares, F, estimates, standard errors, t and
confidence limits; P values relative 1e-7 (absolute 1e-15 below 1e-8). Degrees
of freedom must be equal.
"""
import math
from pathlib import Path

import pandas as pd
import pytest

from make_my_figure_core.statistics.factorial import check_design, factorial_anova, model_coefficients
from make_my_figure_core.statistics.models import StatsError

FX = Path(__file__).parent / "fixtures" / "factorial"
REF = FX / "r_reference"
CASES = pd.read_csv(FX / "cases.csv", keep_default_na=False)
R_ANOVA = pd.read_csv(REF / "r_anova.csv")
R_COEF = pd.read_csv(REF / "r_coefficients.csv")
R_DESIGN = pd.read_csv(REF / "r_design.csv").set_index("case_id")
REL = 1e-9
P_REL, P_ABS = 1e-7, 1e-15


def _split(s):
    return [x for x in str(s).split(";") if x]


def _case(case_id):
    row = CASES.set_index("case_id").loc[case_id]
    df = pd.read_csv(FX / f"{row.dataset}.csv")
    return row, df


def _close(a, b, rel):
    return math.isclose(float(a), float(b), rel_tol=rel, abs_tol=0.0)


def _p_close(a, b):
    a, b = float(a), float(b)
    if b < 1e-8:
        return abs(a - b) <= P_ABS + P_REL * b
    return math.isclose(a, b, rel_tol=P_REL)


ESTIMABLE = CASES[CASES.expected == "estimable"].case_id.tolist()
REFUSED = CASES[CASES.expected != "estimable"].case_id.tolist()


@pytest.mark.parametrize("case_id", ESTIMABLE)
def test_anova_table_matches_r(case_id):
    row, df = _case(case_id)
    res = factorial_anova(df, row.response, _split(row.factors), covariates=_split(row.covariates),
                          interactions=row.interactions, ss_type=int(row.ss_type))
    ref = R_ANOVA[R_ANOVA.case_id == case_id]
    ours = {r.group_a.replace(" × ", ":"): r for r in res}
    assert set(ours) == set(ref.term), (sorted(ours), sorted(ref.term))
    for _, r in ref.iterrows():
        o = ours[r.term]
        assert o.df == r.df and o.df2 == r.residual_df, (r.term, o.df, o.df2)
        assert _close(o.extra["sum_sq"], r.sum_sq, REL), (r.term, o.extra["sum_sq"], r.sum_sq)
        assert _close(o.statistic, r.F, REL), (r.term, o.statistic, r.F)
        assert _p_close(o.p_value, r.p_value), (r.term, o.p_value, r.p_value)
        # partial eta-squared from R's own SS: SS / (SS + RSS), RSS = SS * df_res / (F * df)
        rss = r.sum_sq * r.residual_df / (r.F * r.df)
        assert _close(o.effect_size, r.sum_sq / (r.sum_sq + rss), 1e-8)


@pytest.mark.parametrize("case_id", ESTIMABLE)
def test_coefficients_match_r_sum_contrasts(case_id):
    row, df = _case(case_id)
    ours = model_coefficients(df, row.response, _split(row.factors), covariates=_split(row.covariates),
                              interactions=row.interactions)
    ref = R_COEF[R_COEF.case_id == case_id].set_index("r_name")
    assert len(ours) == len(ref)
    factors, covs = _split(row.factors), _split(row.covariates)
    used = df.dropna(subset=[row.response, *factors, *covs])
    levels = {f"_f{i}": sorted(used[f].astype(str).unique()) for i, f in enumerate(factors)}
    names = {**{f"_f{i}": f for i, f in enumerate(factors)}, **{f"_c{i}": c for i, c in enumerate(covs)}}

    def r_name(term):
        # "C(_f0, Sum)[S.control]:C(_f2, Sum)[S.day2]" -> "treatment1:time1" (R's contr.sum naming)
        if term == "Intercept":
            return "(Intercept)"
        out = []
        for piece in term.split(":"):
            if piece.startswith("C("):
                inner = piece[2:].split(",")[0]
                level = piece.split("[S.", 1)[1].rstrip("]")
                out.append(f"{names[inner]}{levels[inner].index(level) + 1}")
            else:
                out.append(names[piece])
        return ":".join(out)

    for _, o in ours.iterrows():
        r = ref.loc[r_name(o.term)]
        for key in ("estimate", "std_error", "t", "ci_low", "ci_high"):
            assert math.isclose(o[key], r[key], rel_tol=REL, abs_tol=1e-12), (case_id, o.term, key, o[key], r[key])
        assert _p_close(o.p_value, r.p_value), (case_id, o.term, o.p_value, r.p_value)


@pytest.mark.parametrize("case_id", ESTIMABLE)
def test_design_counts_match_r(case_id):
    row, df = _case(case_id)
    rep = check_design(df, row.response, _split(row.factors), covariates=_split(row.covariates),
                       interactions=row.interactions)
    ref = R_DESIGN.loc[case_id]
    assert rep.n_used == ref.n_used and rep.residual_df == ref.residual_df


@pytest.mark.parametrize("case_id", REFUSED)
def test_non_estimable_designs_are_refused_where_r_shows_why(case_id):
    row, df = _case(case_id)
    subject = "colony_id" if row.expected == "not_estimable_subject" else None
    rep = check_design(df, row.response, _split(row.factors), covariates=_split(row.covariates),
                       subject=subject, interactions=row.interactions)
    assert not rep.estimable and rep.problems
    ref = R_DESIGN.loc[case_id]
    # R's own evidence that the model is not a valid analysis:
    assert (ref.aliased_coefficients > 0 or ref.residual_df <= 0 or bool(ref.constant_response)
            or bool(ref.confounded) or ref.max_rows_per_colony > 1)
    with pytest.raises(StatsError):
        factorial_anova(df, row.response, _split(row.factors), covariates=_split(row.covariates),
                        subject=subject, interactions=row.interactions)


def test_two_way_anova_effect_size_is_partial_eta_squared_not_share_of_total():
    # Up to v1.3.0 two_way_anova reported SS_term / SS_total under the name
    # "partial eta-squared". On case B3 (unbalanced 2x2, Type II) that gave
    # 0.549 / 0.164 / 0.110 for treatment / time / interaction; the partial
    # eta-squared from R's sums of squares is 0.756 / 0.480 / 0.384.
    from make_my_figure_core.statistics import anova

    row, df = _case("B3")
    res = {r.group_a: r for r in anova.two_way_anova(df, "quantity", "treatment", "time")}
    ref = R_ANOVA[R_ANOVA.case_id == "B3"].set_index("term")
    for ours, term in (("treatment", "treatment"), ("time", "time"), ("treatment x time", "treatment:time")):
        r = ref.loc[term]
        rss = r.sum_sq * r.residual_df / (r.F * r.df)
        assert res[ours].effect_size_name == "partial eta-squared"
        assert _close(res[ours].effect_size, r.sum_sq / (r.sum_sq + rss), 1e-8)
        assert _close(res[ours].statistic, r.F, REL) and _p_close(res[ours].p_value, r.p_value)


def test_two_way_anova_refuses_the_confounded_bee_design():
    from make_my_figure_core.statistics import anova

    bee = pd.read_excel(FX.parent / "bee_demo_workbook.xlsx")
    with pytest.raises(StatsError, match="completely confounded"):
        anova.two_way_anova(bee, "bee body size_mm", "treatment", "time")


@pytest.mark.parametrize("case_id", ESTIMABLE)
def test_readable_coefficient_labels_name_the_same_coefficients_as_r(case_id):
    # "treatment = control" must be R's "treatment1" (level 1 of contr.sum), and so on.
    row, df = _case(case_id)
    factors, covs = _split(row.factors), _split(row.covariates)
    ours = model_coefficients(df, row.response, factors, covariates=covs, interactions=row.interactions)
    used = df.dropna(subset=[row.response, *factors, *covs])
    levels = {f: sorted(used[f].astype(str).unique()) for f in factors}
    ref = R_COEF[R_COEF.case_id == case_id].set_index("r_name")

    def to_r(label):
        if label == "Intercept":
            return "(Intercept)"
        out = []
        for part in label.replace(" (slope)", "").split(" × "):
            if " = " in part:
                f, lev = part.split(" = ", 1)
                out.append(f"{f}{levels[f].index(lev) + 1}")
            else:
                out.append(part)
        return ":".join(out)

    for _, o in ours.iterrows():
        r = ref.loc[to_r(o.label)]
        assert math.isclose(o.estimate, r.estimate, rel_tol=REL, abs_tol=1e-12), (o.label, o.estimate, r.estimate)
        assert o.residual_df == R_DESIGN.loc[case_id].residual_df
