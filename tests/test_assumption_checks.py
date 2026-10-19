"""Normality and equal-variance checks before a parametric test.

Defect it prevents: no assumption was ever tested. Every result listed
``assumptions_checked`` ("approximately normal residuals", "equal variances
across groups") as text only, and a t-test or ANOVA ran on any data without a
Shapiro-Wilk or Levene result anywhere - the standard ecology workflow tests the
assumptions first.

Reference values: base R 4.5.3 (``quality_audit/assumption_checks/validate_assumptions.R``):
``shapiro.test`` and median-centred Levene from its definition. Tolerances fixed
in advance: relative 1e-9 for W and F, 1e-7 for P (absolute 1e-15 below 1e-8).
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from apps.desktop_app.controller import DesktopController
from make_my_figure_core.statistics.assumptions import levene, shapiro
from make_my_figure_core.statistics.runner import run_statistics

FX = Path(__file__).parent / "fixtures"
PLANTS = pd.read_csv(FX / "plant_growth_facets.csv")
UNBAL = pd.read_csv(FX / "factorial" / "unbalanced.csv")
REF = pd.read_csv(FX / "assumption_checks_r_reference.csv").set_index("case")
PT = "boxplot_or_violin_with_points"
C = DesktopController()


def _close_p(a, b):
    return abs(a - b) <= 1e-15 + 1e-7 * b if b < 1e-8 else math.isclose(a, b, rel_tol=1e-7)


def _agree(check, case):
    r = REF.loc[case]
    assert math.isclose(check.statistic, r.statistic, rel_tol=1e-9), (case, check.statistic, r.statistic)
    assert _close_p(check.p_value, r.p_value), (case, check.p_value, r.p_value)
    if check.df is not None:
        assert (check.df, check.df2) == (r.df1, r.df2)


def _stats(df, mapping, **stats):
    return run_statistics(df, {"enabled": True, **stats}, plot_type=PT, mapping=mapping)


def _checks(rep):
    return {c["assumption"]: c for c in rep.assumptions["checks"]}


def test_factorial_anova_checks_model_residuals_and_cell_variances_like_r():
    young = PLANTS[PLANTS.Age == "Young"]
    rep = _stats(young, {"x": "Month", "y": "Growth_cm", "hue": "Nitrogen_Concentration"}, test="factorial_anova")
    from make_my_figure_core.statistics.assumptions import AssumptionCheck

    ch = {k: AssumptionCheck(**v) for k, v in _checks(rep).items()}
    _agree(ch["normality"], "young_factorial_residuals")
    _agree(ch["equal variances"], "young_factorial_levene")
    assert ch["normality"].n == 120 and "residuals" in ch["normality"].target


def test_three_way_one_way_and_unbalanced_checks_match_r():
    from make_my_figure_core.statistics.assumptions import AssumptionCheck

    rep = _stats(PLANTS, {"x": "Month", "y": "Growth_cm"}, test="factorial_anova",
                 factors=["Month", "Nitrogen_Concentration", "Age"])
    ch = {k: AssumptionCheck(**v) for k, v in _checks(rep).items()}
    _agree(ch["normality"], "all_three_way_residuals")
    _agree(ch["equal variances"], "all_three_way_levene")
    rep = _stats(PLANTS, {"x": "Nitrogen_Concentration", "y": "Growth_cm"}, test="one_way_anova")
    ch = {k: AssumptionCheck(**v) for k, v in _checks(rep).items()}
    _agree(ch["normality"], "oneway_residuals")
    _agree(ch["equal variances"], "oneway_levene")
    rep = run_statistics(UNBAL, {"enabled": True, "test": "factorial_anova", "group_column": "treatment",
                                 "subgroup_column": "time"}, plot_type=PT, mapping={"y": "quantity"})
    ch = {k: AssumptionCheck(**v) for k, v in _checks(rep).items()}
    _agree(ch["normality"], "unbalanced_residuals")
    _agree(ch["equal variances"], "unbalanced_levene")


def test_t_tests_check_each_group_and_only_students_checks_variances():
    m10 = PLANTS[PLANTS.Month == 10]
    rep = _stats(m10, {"x": "Nitrogen_Concentration", "y": "Growth_cm"}, test="welch_t",
                 comparison_mode="all_pairs")
    checks = rep.assumptions["checks"]
    assert [c["target"] for c in checks] == ["group Low N", "group Medium N", "group High N"]
    from make_my_figure_core.statistics.assumptions import AssumptionCheck

    for c in checks:
        _agree(AssumptionCheck(**c), f"m10_group_{c['target'][6:]}")
    rep = _stats(m10, {"x": "Nitrogen_Concentration", "y": "Growth_cm"}, test="students_t",
                 comparison_mode="all_pairs")
    assert [c["assumption"] for c in rep.assumptions["checks"]][-1] == "equal variances"


def test_failed_normality_is_reported_and_the_requested_test_still_runs():
    rng = np.random.default_rng(7)
    df = pd.DataFrame({"g": ["a"] * 40 + ["b"] * 40,
                       "y": np.r_[rng.lognormal(0, 1.2, 40), rng.lognormal(0.6, 1.2, 40)]})
    rep = run_statistics(df, {"enabled": True, "test": "welch_t"}, plot_type=PT, mapping={"x": "g", "y": "y"})
    assert rep.assumptions["normality_failed"] and rep.results[0].test_id == "welch_t"
    assert any("normality was not met" in w and "Mann-Whitney" in w for w in rep.warnings)
    assert "was run as requested" in rep.method_paragraph


def test_switch_uses_the_non_parametric_alternative_and_says_so():
    rng = np.random.default_rng(7)
    df = pd.DataFrame({"g": ["a"] * 40 + ["b"] * 40,
                       "y": np.r_[rng.lognormal(0, 1.2, 40), rng.lognormal(0.6, 1.2, 40)]})
    rep = run_statistics(df, {"enabled": True, "test": "welch_t", "assumption_action": "switch"},
                         plot_type=PT, mapping={"x": "g", "y": "y"})
    assert rep.results[0].test_id == "mann_whitney" and rep.assumptions["used_test"] == "mann_whitney"
    assert "Mann-Whitney U test was used instead of the Welch's t-test" in rep.method_paragraph
    from scipy import stats

    ref = stats.mannwhitneyu(df.y[df.g == "a"], df.y[df.g == "b"], alternative="two-sided")
    assert rep.results[0].p_value == pytest.approx(ref.pvalue, rel=1e-12)
    # an ANOVA with no rank-based equivalent is reported, never replaced
    df["h"] = np.tile(["x", "y"], 40)
    rep = run_statistics(df, {"enabled": True, "test": "factorial_anova", "assumption_action": "switch",
                              "group_column": "g", "subgroup_column": "h"}, plot_type=PT, mapping={"y": "y"})
    assert {r.test_id for r in rep.results} == {"factorial_anova"}
    assert any("log or square-root transformation" in w for w in rep.warnings)


def test_met_assumptions_leave_the_results_unchanged():
    young = PLANTS[PLANTS.Age == "Young"]
    mapping = {"x": "Month", "y": "Growth_cm", "hue": "Nitrogen_Concentration"}
    a = _stats(young, mapping, test="factorial_anova")
    b = _stats(young, mapping, test="factorial_anova", assumption_action="switch")
    assert [(r.group_a, r.statistic, r.p_value) for r in a.results] == \
        [(r.group_a, r.statistic, r.p_value) for r in b.results]


def test_too_few_observations_are_reported_not_tested():
    c = shapiro([1.0, 2.0], "group a", 0.05)
    assert c.passed is None and "at least 3" in c.note
    c = levene({"a": [1.0], "b": [2.0]}, "groups", 0.05)
    assert c.passed is None


def test_grid_reports_checks_per_panel_and_for_the_whole_grid():
    s = C.build_spec(PT, "publication", "t.csv", {"x": "Month", "y": "Growth_cm", "hue": "Nitrogen_Concentration",
                                                  "facet_col": "Age"}, width="default",
                     statistics={"enabled": True, "test": "factorial_anova", "facet_scope": "figure"})
    res = C.render(s, C.loaded_from_dataframe(PLANTS, "t.csv"))
    rep = res.stats_report
    panels = [a["panel"] for a in rep.assumptions]
    assert panels == ["Age: Young", "Age: Old", "whole grid"]
    text = rep.method_paragraph
    assert "Assumptions were checked in each panel" in text and "For the whole-grid model" in text
    assert text.count("Assumptions were checked before the test") == 0      # no panel-1 sentence passed off
    rows = C.stats_table_rows(rep)
    assert sum(r["test"].startswith("Shapiro-Wilk") for r in rows) == 3
    assert sum(r["test"].startswith("Levene") for r in rows) == 3
