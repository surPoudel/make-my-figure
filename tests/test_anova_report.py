"""R-style statistics report: print(summary(aov(...))) and print(TukeyHSD(...)), line for line.

Request (2026-10-17): the same report as R's console - the ANOVA table and Tukey HSD -
from the app. Reference text: base R 4.5.3 console output
(``quality_audit/assumption_checks/validate_anova_report.R``), compared character for
character after removing trailing spaces and blank lines and writing R's curly quotes
in the significance legend as straight quotes.
"""
from pathlib import Path

import pandas as pd
import pytest

from make_my_figure_core.statistics.anova_report import (
    anova_report,
    format_aov,
    format_pval,
    format_real,
    format_tukey,
    report_for_plot,
)

FX = Path(__file__).parent / "fixtures"
REF = FX / "anova_report_r"
PLANTS = pd.read_csv(FX / "plant_growth_facets.csv")
UNBAL = pd.read_csv(FX / "factorial" / "unbalanced.csv")

CASES = {
    "young_two_way": (PLANTS[PLANTS.Age == "Young"], "Growth_cm", ["Month", "Nitrogen_Concentration"], "young"),
    "plants_one_way": (PLANTS, "Growth_cm", ["Nitrogen_Concentration"], "plants"),
    "plants_three_way": (PLANTS, "Growth_cm", ["Month", "Nitrogen_Concentration", "Age"], "plants"),
    "unbalanced_two_way": (UNBAL, "quantity", ["treatment", "time"], "u"),
    "unbalanced_reversed": (UNBAL, "quantity", ["time", "treatment"], "u"),
}


def _clean(text: str):
    text = text.replace("‘", "'").replace("’", "'")
    return [ln.rstrip() for ln in text.splitlines() if ln.strip()]


@pytest.mark.parametrize("case", sorted(CASES))
def test_report_reads_exactly_as_r_prints_it(case):
    df, y, factors, name = CASES[case]
    rep = anova_report(df, y, factors, data_name=name)
    ours = _clean(format_aov(rep.rows) + "\n" + format_tukey(rep))
    theirs = _clean((REF / f"{case}.txt").read_text(encoding="utf-8"))
    assert ours == theirs


def test_type_one_order_matters_when_unbalanced_and_the_report_says_so():
    a = anova_report(UNBAL, "quantity", ["treatment", "time"])
    b = anova_report(UNBAL, "quantity", ["time", "treatment"])
    ss = lambda rep, term: next(r.sum_sq for r in rep.rows if r.term == term)
    assert ss(a, "treatment") == pytest.approx(112.515767695661, rel=1e-9)     # R anova(lm), case F2
    assert ss(b, "treatment") == pytest.approx(113.16059137291, rel=1e-9)      # case F3
    assert not a.balanced and any("depend on the order" in n for n in a.notes)
    assert anova_report(PLANTS, "Growth_cm", ["Month", "Nitrogen_Concentration"]).balanced


def test_r_number_formatting_rules():
    assert format_real([279.9667, 162.6881, 48.4383, 2.8498], 4) == ["279.97", "162.69", " 48.44", "  2.85"]
    assert format_real([1e-7], 7) == ["1e-07"]                     # scientific when narrower
    assert format_pval([1e-20, 5.14e-10, 1.88e-6], 3) == ["< 2e-16", "5.14e-10", "1.88e-06"]
    assert format_pval([1e-20], 3) == ["<2e-16"]


def test_report_for_a_faceted_plot_panel_matches_the_figure_statistics():
    spec = {"plot_type": "boxplot_or_violin_with_points", "input_table": "plant growth.csv",
            "mapping": {"x": "Month", "y": "Growth_cm", "hue": "Nitrogen_Concentration", "facet_col": "Age"},
            "statistics": {"enabled": True, "test": "factorial_anova"}}
    rep = report_for_plot(PLANTS, spec, panel="Age = Young")
    assert rep.title == "Age = Young" and rep.n == 120 and rep.data_name == "plant_growth"
    from make_my_figure_core.statistics.factorial import factorial_anova

    direct = {r.group_a.replace(" × ", ":"): r for r in
              factorial_anova(PLANTS[PLANTS.Age == "Young"], "Growth_cm", ["Month", "Nitrogen_Concentration"])}
    for row in rep.rows[:-1]:                     # balanced: Type I equals the figure's Type II
        assert row.f == pytest.approx(direct[row.term].statistic, rel=1e-12)
    text = rep.text()
    assert "Shapiro-Wilk" in text and "Levene" in text and "Software:" in text
    with pytest.raises(Exception):
        report_for_plot(PLANTS, {**spec, "statistics": {"test": "pearson"}})


def test_studentized_range_port_matches_r():
    import numpy as np

    from make_my_figure_core.statistics._tukey_dist import ptukey, qtukey

    q = np.array([0.5, 1, 2.5, 3.7, 5, 8, 12])
    for line in (REF / "ptukey_qtukey.txt").read_text().splitlines():
        v = [float(x) for x in line.split()]
        k, df, rq, rp = v[0], v[1], v[2], np.array(v[3:])
        assert qtukey(0.95, k, df) == pytest.approx(rq, rel=1e-12), (k, df)
        np.testing.assert_allclose(ptukey(q, k, df, lower_tail=False), rp, rtol=0, atol=1e-13)
