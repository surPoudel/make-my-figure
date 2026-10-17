"""ANOVA on the figure: sums-of-squares type, annotation controls, post-hoc, fit.

Defects reported from the faceted plant-growth figure (macOS, 2026-10-17):
the ANOVA text ran 233 px past the "Age: Young" panel; "Annotation shows",
"Show effect size" and "Hide non-significant" did nothing to ANOVA terms;
"Post-hoc pairwise after omnibus" drew nothing after a two-way / factorial
ANOVA; the ANOVA panel sat over bracket labels; there was no Type I option.
Every styling test asserts the numbers alongside the pixels.
"""
from pathlib import Path

import matplotlib
import pandas as pd
import pytest

matplotlib.use("Agg")

from apps.desktop_app.controller import DesktopController  # noqa: E402
from make_my_figure_core.plots.facets import facet_axes  # noqa: E402
from make_my_figure_core.statistics.annotations import stat_text_panel  # noqa: E402
from make_my_figure_core.statistics.factorial import factorial_anova  # noqa: E402
from make_my_figure_core.statistics.method_reporting import render_annotation  # noqa: E402
from make_my_figure_core.statistics.runner import run_statistics  # noqa: E402

HERE = Path(__file__).parent
PLANTS = pd.read_csv(HERE / "fixtures" / "plant_growth_facets.csv")
FX = HERE / "fixtures" / "factorial"
PT = "boxplot_or_violin_with_points"


C = DesktopController()


def _spec(mapping, stats):
    return C.build_spec(PT, "publication", "table.csv", dict(mapping), width="default",
                        statistics={"enabled": True, **stats})


def render_plot(spec, df):
    return C.render(spec, C.loaded_from_dataframe(df, "table.csv"))


GRID = {"x": "Month", "y": "Growth_cm", "hue": "Nitrogen_Concentration", "facet_col": "Age"}


def _corner(ax):
    return [t for t in ax.texts if t.get_zorder() == 8]


# --- sums of squares --------------------------------------------------------------------------

def test_type_one_sums_of_squares_depend_on_factor_order_when_unbalanced():
    df = pd.read_csv(FX / "unbalanced.csv")
    a = {r.group_a: r for r in factorial_anova(df, "quantity", ["treatment", "time"], ss_type=1)}
    b = {r.group_a: r for r in factorial_anova(df, "quantity", ["time", "treatment"], ss_type=1)}
    # R anova(lm): treatment entered first 112.5158, second 113.1606 (validation cases F2 / F3).
    assert a["treatment"].extra["sum_sq"] == pytest.approx(112.515767695661, rel=1e-9)
    assert b["treatment"].extra["sum_sq"] == pytest.approx(113.16059137291, rel=1e-9)
    assert a["treatment"].extra["ss_type"] == "I"


def test_all_three_sums_of_squares_agree_on_a_balanced_design():
    tables = [{r.group_a: r.statistic for r in factorial_anova(
        PLANTS, "Growth_cm", ["Month", "Nitrogen_Concentration", "Age"], ss_type=t)} for t in (1, 2, 3)]
    for term in tables[0]:
        assert tables[1][term] == pytest.approx(tables[0][term], rel=1e-9)
        assert tables[2][term] == pytest.approx(tables[0][term], rel=1e-9)


def test_figure_statistics_honour_the_chosen_sums_of_squares():
    df = pd.read_csv(FX / "unbalanced.csv")
    stats = {"test": "factorial_anova", "group_column": "treatment", "subgroup_column": "time",
             "ss_type": 3}
    res = render_plot(_spec({"x": "treatment", "y": "quantity", "hue": "time"}, stats), df)
    direct = {r.group_a: r for r in factorial_anova(df, "quantity", ["treatment", "time"], ss_type=3)}
    shown = {r.group_a: r for r in res.stats_report.results if r.comparison_type == "omnibus"}
    assert {r.extra["ss_type"] for r in shown.values()} == {"III"}
    for term, r in direct.items():
        assert shown[term].p_value == pytest.approx(r.p_value, rel=1e-12)


# --- annotation controls on ANOVA terms -------------------------------------------------------

def test_default_anova_text_is_unchanged():
    res = render_plot(_spec({"x": "Month", "y": "Growth_cm"}, {"test": "one_way_anova"}), PLANTS)
    assert [t.get_text() for t in _corner(res.figure.axes[0])] == ["One-way ANOVA: F = 77.9, p < 0.001"]


@pytest.mark.parametrize("content,expect,absent", [
    ("p", "Month: p < 0.001", "F("),
    ("p_stat", "Month: F(3, 108) = 242, p < 0.001", None),
    ("effect", "Month: $\\eta_p^2$ = 0.87", "p <"),
])
def test_annotation_shows_acts_on_anova_terms(content, expect, absent):
    young = PLANTS[PLANTS.Age == "Young"]
    rep = run_statistics(young, {"enabled": True, "test": "factorial_anova",
                                 "group_column": "Month", "subgroup_column": "Nitrogen_Concentration"},
                         plot_type=PT, mapping={"x": "Month", "y": "Growth_cm"})
    lines = stat_text_panel(rep.results, cfg={"content": content})
    assert any(ln.strip() == expect for ln in lines), lines
    if absent:
        assert not any(absent in ln for ln in lines[1:]), lines
    direct = factorial_anova(young, "Growth_cm", ["Month", "Nitrogen_Concentration"])
    assert rep.results[0].statistic == pytest.approx(direct[0].statistic, rel=1e-12)   # 241.60


def test_hide_nonsignificant_drops_anova_terms_and_show_effect_adds_partial_eta():
    rep = run_statistics(PLANTS, {"enabled": True, "test": "factorial_anova",
                                  "factors": ["Month", "Nitrogen_Concentration", "Age"]},
                         plot_type=PT, mapping={"x": "Month", "y": "Growth_cm"})
    ns = [r.group_a for r in rep.results if not r.reject_null]
    assert ns == ["Month × Age", "Nitrogen_Concentration × Age", "Month × Nitrogen_Concentration × Age"]
    lines = stat_text_panel(rep.results, cfg={"content": "stars", "hide_nonsignificant": True,
                                              "show_effect": True})
    assert not any(term in ln for ln in lines for term in ns)
    assert len(lines) == 1 + 4 and all("$\\eta_p^2$" in ln for ln in lines[1:])


def test_show_effect_size_acts_on_brackets_with_stars_only():
    a = PLANTS[(PLANTS.Month == 10) & (PLANTS.Nitrogen_Concentration == "Low N")].Growth_cm
    rep = run_statistics(PLANTS[PLANTS.Month == 10], {"enabled": True, "test": "welch_t",
                                                      "comparison_mode": "all_pairs",
                                                      "group_column": "Nitrogen_Concentration"},
                         plot_type=PT, mapping={"x": "Nitrogen_Concentration", "y": "Growth_cm"})
    r = rep.results[0]
    assert render_annotation(r, {"content": "stars"}) == "****"
    assert render_annotation(r, {"content": "stars", "show_effect": True}) == \
        f"****, g = {r.effect_size:.2g}"
    assert len(a) == 20


# --- post-hoc after a two-way / factorial ANOVA ----------------------------------------------

@pytest.mark.parametrize("test", ["two_way_anova", "factorial_anova"])
def test_posthoc_after_two_way_or_factorial_anova_is_run_and_drawn(test):
    young = PLANTS[PLANTS.Age == "Young"]
    spec = _spec({"x": "Month", "y": "Growth_cm", "hue": "Nitrogen_Concentration"},
                 {"test": test, "posthoc": True})
    res = render_plot(spec, young)
    pairs = [r for r in res.stats_report.results if r.comparison_type == "two_group"]
    assert len(pairs) == 4 * 3                       # 3 nitrogen pairs within each of 4 months
    assert all(r.extra.get("within_x") for r in pairs)
    assert {r.correction_method for r in pairs} == {"benjamini_hochberg"}
    assert res.stats_report.config["_annotation_info"]["n_brackets"] >= 1
    off = render_plot(_spec(spec["mapping"], {"test": test, "posthoc": False}), young)
    assert not [r for r in off.stats_report.results if r.comparison_type == "two_group"]
    # the omnibus table itself is unchanged by asking for post-hoc pairs
    om = lambda rep: [(r.group_a, r.statistic) for r in rep.results if r.comparison_type == "omnibus"]
    assert om(res.stats_report) == om(off.stats_report)


# --- fitting on the figure --------------------------------------------------------------------

def test_grid_anova_text_stays_inside_its_panel():
    res = render_plot(_spec(GRID, {"test": "factorial_anova"}), PLANTS)
    fig = res.figure
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    for ax in facet_axes(fig):
        frame = ax.get_window_extent(r)
        (panel,) = _corner(ax)
        box = panel.get_window_extent(r)
        assert box.x1 <= frame.x1 + 0.5 and box.x0 >= frame.x0 - 0.5, (box, frame)  # was +233 px
        assert "F(3, 108)" in panel.get_text()             # never broken inside "F(3, 108)"
    young = PLANTS[PLANTS.Age == "Young"]
    direct = factorial_anova(young, "Growth_cm", ["Month", "Nitrogen_Concentration"])
    shown = [r for r in res.stats_report.results if r.extra.get("facet") == "Age: Young"]
    assert [r.statistic for r in shown] == pytest.approx([r.statistic for r in direct], rel=1e-12)


def test_single_plot_keeps_its_figure_wide_text_fitting():
    res = render_plot(_spec({"x": "Month", "y": "Growth_cm", "hue": "Nitrogen_Concentration"},
                            {"test": "factorial_anova"}), PLANTS)
    (panel,) = _corner(res.figure.axes[0])
    assert "\n    F(" not in panel.get_text()          # the grid's line breaking stays in grids


@pytest.mark.parametrize("facet", [False, True])
def test_anova_panel_clears_every_bracket_label(facet):
    mapping = GRID if facet else {k: v for k, v in GRID.items() if k != "facet_col"}
    res = render_plot(_spec(mapping, {"test": "factorial_anova", "posthoc": True,
                                      "annotation": {"content": "stars", "show_effect": True}}), PLANTS)
    fig = res.figure
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    for ax in (facet_axes(fig) if facet else fig.axes[:1]):
        (panel,) = _corner(ax)
        box = panel.get_bbox_patch().get_window_extent(r)
        for t in ax.texts:
            if t.get_zorder() != 7:
                continue
            b = t.get_window_extent(r)
            if b.x1 < box.x0 or b.x0 > box.x1:
                continue
            assert b.y1 <= box.y0 + 0.5, (t.get_text(), b.y1, box.y0)


def test_crowded_grid_bracket_labels_are_reported():
    crowded = render_plot(_spec(GRID, {"test": "factorial_anova", "posthoc": True,
                                       "annotation": {"content": "stars", "show_effect": True}}), PLANTS)
    assert any("overlap another label" in w for w in crowded.warnings)
    plain = render_plot(_spec(GRID, {"test": "factorial_anova", "posthoc": True,
                                     "annotation": {"content": "stars"}}), PLANTS)
    assert not any("overlap another label" in w for w in plain.warnings)


def test_anova_terms_as_stars_is_opt_in():
    base = {"x": "Month", "y": "Growth_cm"}
    off = render_plot(_spec(base, {"test": "one_way_anova", "annotation": {"content": "stars"}}), PLANTS)
    on = render_plot(_spec(base, {"test": "one_way_anova",
                                  "annotation": {"content": "stars", "omnibus_stars": True}}), PLANTS)
    assert [t.get_text() for t in _corner(off.figure.axes[0])] == ["One-way ANOVA: F = 77.9, p < 0.001"]
    assert [t.get_text() for t in _corner(on.figure.axes[0])] == ["One-way ANOVA: ****"]
    assert on.stats_report.results[0].statistic == off.stats_report.results[0].statistic   # 77.9
    assert on.stats_report.results[0].p_value == off.stats_report.results[0].p_value
