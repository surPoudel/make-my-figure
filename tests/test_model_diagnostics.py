"""Model diagnostics: R's four plot(lm) panels for the model behind the statistics.

Defect it prevents: there were no residual plots. Homogeneity of variance and
influential observations could be judged only from a single Levene P value, and
the standard workflow - look at Residuals vs Fitted, Normal Q-Q, Scale-Location
and Residuals vs Leverage before and after the test - could not be followed.

Reference: base R 4.5.3 (``quality_audit/assumption_checks/validate_diagnostics.R``).
Tolerances fixed in advance: relative 1e-9 for fitted values, residuals,
standardized residuals, leverage and Cook's distance; absolute 1e-8 for lowess.
"""
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")

from make_my_figure_core.statistics.diagnostics import (  # noqa: E402
    WHOLE_GRID,
    diagnostic_figure,
    diagnostics_for_plot,
    fit_diagnostics,
    lowess,
    panel_choices,
    ppoints,
    summary_text,
)

FX = Path(__file__).parent / "fixtures"
REF = FX / "diagnostics_r_reference"
PLANTS = pd.read_csv(FX / "plant_growth_facets.csv")
UNBAL = pd.read_csv(FX / "factorial" / "unbalanced.csv")


def _rel(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(np.max(np.abs(a - b) / np.maximum(np.abs(b), 1e-12)))


def test_balanced_anova_diagnostics_match_r_point_by_point():
    young = PLANTS[PLANTS.Age == "Young"]
    d = fit_diagnostics(young, "Growth_cm", ["Month", "Nitrogen_Concentration"])
    r = pd.read_csv(REF / "young_balanced.csv")
    assert (d.rows == r.row.to_numpy()).all()              # full-table row numbers, as R's row names
    for ours, theirs in ((d.fitted, r.fitted), (d.residuals, r.resid), (d.standardized, r.rstd),
                         (d.leverage, r.hat), (d.cooks, r.cook)):
        assert _rel(ours, theirs) < 1e-9
    assert d.constant_leverage and d.n_parameters == 12
    lw = pd.read_csv(REF / "young_lowess.csv")
    _, y1 = lowess(d.fitted, d.residuals)
    _, y3 = lowess(d.fitted, np.sqrt(np.abs(d.standardized)))
    assert np.max(np.abs(y1 - lw.resid_y)) < 1e-8 and np.max(np.abs(y3 - lw.scale_y)) < 1e-8
    # R's qqnorm positions: ppoints(n) through the normal quantile function, in the residuals' order
    from scipy import stats

    theo = np.empty(d.n)
    theo[np.argsort(d.standardized, kind="stable")] = stats.norm.ppf(ppoints(d.n))
    # Residuals equal in exact arithmetic (a balanced design) differ by ~1e-13 between R and
    # Python, so tied points may swap positions; the set of positions is identical, and every
    # untied residual has exactly R's position.
    assert np.max(np.abs(np.sort(theo) - np.sort(r.qq_x))) < 1e-12
    rs = d.standardized
    untied = np.array([np.sum(np.abs(rs - v) < 1e-9) == 1 for v in rs])
    assert untied.sum() > 100 and np.max(np.abs(theo[untied] - r.qq_x[untied])) < 1e-12


def test_unbalanced_ancova_diagnostics_and_leverage_smoother_match_r():
    d = fit_diagnostics(UNBAL, "quantity", ["treatment", "time"], ["body_size_mm"])
    r = pd.read_csv(REF / "unbalanced_ancova.csv")
    for ours, theirs in ((d.fitted, r.fitted), (d.standardized, r.rstd), (d.leverage, r.hat), (d.cooks, r.cook)):
        assert _rel(ours, theirs) < 1e-9
    assert not d.constant_leverage
    lw = pd.read_csv(REF / "unbalanced_leverage_lowess.csv")
    _, y = lowess(d.leverage, d.standardized)
    assert np.max(np.abs(y - lw.y)) < 1e-8


def test_figure_has_r_panels_labels_and_the_constant_leverage_variant():
    young = PLANTS[PLANTS.Age == "Young"]
    d = fit_diagnostics(young, "Growth_cm", ["Month", "Nitrogen_Concentration"])
    fig = diagnostic_figure(d)
    titles = [ax.get_title() for ax in fig.axes]
    assert titles == ["Residuals vs Fitted", "Normal Q-Q", "Scale-Location",
                      "Constant Leverage:\nResiduals vs Factor Levels"]
    labels = [t.get_text() for t in fig.axes[0].texts]
    top3 = d.rows[np.argsort(-np.abs(d.residuals), kind="stable")[:3]]
    assert labels == [str(x) for x in top3]                 # R's id.n = 3, by |residual|
    fig = diagnostic_figure(fit_diagnostics(UNBAL, "quantity", ["treatment", "time"], ["body_size_mm"]))
    assert fig.axes[3].get_title() == "Residuals vs Leverage"
    assert any(ln.get_linestyle() == "--" for ln in fig.axes[3].get_lines())   # Cook's distance contours


def test_scale_location_shows_the_unequal_variance_and_a_log_response_evens_it():
    """The Levene test fails within each age (P = 9.5e-5); the Scale-Location smoother rises with it."""
    young = PLANTS[PLANTS.Age == "Young"].copy()
    young["log10(Growth_cm)"] = np.log10(young["Growth_cm"])

    def rise(col):
        d = fit_diagnostics(young, col, ["Month", "Nitrogen_Concentration"])
        _, y = lowess(d.fitted, np.sqrt(np.abs(d.standardized)))
        return float(y[-1] - y[0]), d

    raw, d_raw = rise("Growth_cm")
    logged, d_log = rise("log10(Growth_cm)")
    assert raw > 0.4 and abs(logged) < raw / 4, (raw, logged)          # measured: 0.63 vs -0.02
    lev = {c["assumption"]: c for c in fit_diagnostics.__globals__["model_for_statistics"](
        young, {"test": "factorial_anova"}, mapping={"x": "Month", "y": "Growth_cm",
                                                       "hue": "Nitrogen_Concentration"},
        plot_type="boxplot_or_violin_with_points").checks}
    assert lev["equal variances"]["passed"] is False


def test_facet_grid_offers_each_panel_and_the_whole_grid_model():
    spec = {"plot_type": "boxplot_or_violin_with_points",
            "mapping": {"x": "Month", "y": "Growth_cm", "hue": "Nitrogen_Concentration", "facet_col": "Age"},
            "statistics": {"enabled": True, "test": "factorial_anova"}}
    choices = panel_choices(PLANTS, spec)
    assert choices == ["Age = Young", "Age = Old", WHOLE_GRID]
    young = diagnostics_for_plot(PLANTS, spec, panel="Age = Young")
    assert young.n == 120 and young.formula == "Growth_cm ~ Month * Nitrogen_Concentration"
    assert young.rows.min() >= 1 and young.rows.max() <= 240
    grid = diagnostics_for_plot(PLANTS, spec, panel=WHOLE_GRID)
    assert grid.n == 240 and grid.factors == ["Month", "Nitrogen_Concentration", "Age"]
    text = summary_text(grid)
    assert "Shapiro-Wilk" in text and "Levene" in text and "Cook's distance" in text


def test_plain_plot_and_regression_models():
    spec = {"plot_type": "boxplot_or_violin_with_points", "mapping": {"x": "Nitrogen_Concentration",
                                                                     "y": "Growth_cm"}}
    assert panel_choices(PLANTS, spec) == ["whole table"]
    d = diagnostics_for_plot(PLANTS, spec)
    assert d.formula == "Growth_cm ~ Nitrogen_Concentration" and d.n_parameters == 3
    spec = {"plot_type": "scatterplot_with_regression", "mapping": {"x": "Month", "y": "Growth_cm"},
            "statistics": {"test": "linear_regression"}}
    d = diagnostics_for_plot(PLANTS, spec)
    assert d.formula == "Growth_cm ~ Month" and d.n_parameters == 2


def test_missing_values_are_left_out_and_counted():
    df = PLANTS.copy()
    df.loc[[0, 5], "Growth_cm"] = np.nan
    d = fit_diagnostics(df, "Growth_cm", ["Nitrogen_Concentration"])
    assert d.n == 238 and 1 not in d.rows and 6 not in d.rows
    assert any("2 row(s)" in n for n in d.notes)
