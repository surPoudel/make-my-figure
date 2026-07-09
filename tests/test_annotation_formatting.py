"""Tests for flexible statistical-annotation display formatting (Part 2)."""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.plots.registry import make_spec, render, render_to_files
from make_my_figure_core.statistics import method_reporting as mr
from make_my_figure_core.statistics.models import StatResult

RNG = np.random.default_rng(3)


def _res(**kw):
    base = dict(test_id="welch_t", test_name="Welch's t-test", comparison_type="two_group",
                group_a="A", group_b="B", statistic=2.43, statistic_name="t", p_value=0.023,
                adjusted_p_value=0.041, effect_size=0.71, effect_size_name="Hedges' g",
                reject_null=True, n_total=40, n_by_group={"A": 20, "B": 20})
    base.update(kw)
    return StatResult(**base)


def test_content_modes():
    r = _res()
    assert mr.render_annotation(r, {"content": "stars"}) == "*"
    assert mr.render_annotation(r, {"content": "p"}) == "p = 0.023"
    assert mr.render_annotation(r, {"content": "p_adj"}) == "q = 0.041"
    assert mr.render_annotation(r, {"content": "p_stars"}) == "p = 0.023 (*)"
    assert mr.render_annotation(r, {"content": "stat", "stat_digits": 3}) == "t = 2.43"
    assert mr.render_annotation(r, {"content": "effect"}) == "g = 0.71"
    assert mr.render_annotation(r, {"content": "p_stat", "stat_digits": 3}) == "t = 2.43, p = 0.023"
    assert mr.render_annotation(r, {"content": "p_effect"}) == "g = 0.71, p = 0.023"
    assert "Welch" in mr.render_annotation(r, {"content": "full"})


def test_custom_template_tokens_are_bare():
    r = _res()
    out = mr.render_annotation(r, {"content": "custom",
                                   "template": "{effect_symbol} = {effect}, p = {p}"})
    assert out == "g = 0.71, p = 0.023"
    # bare tokens: {p} has no 'p =' prefix, {stars} is the star
    assert mr.render_annotation(r, {"content": "custom", "template": "{stars}"}) == "*"
    assert mr.render_annotation(r, {"content": "custom", "template": "{comparison}"}) == "A vs B"
    assert mr.render_annotation(r, {"content": "custom", "template": "n={n}"}) == "n=40"


def test_statistic_symbols():
    chi = _res(test_id="chi_square", test_name="Chi-square", statistic=5.71,
               statistic_name="chi2", effect_size=0.18, effect_size_name="Cramer's V")
    assert r"\chi^2" in mr.render_annotation(chi, {"content": "stat"})
    u = _res(statistic=34, statistic_name="U")
    assert mr.render_annotation(u, {"content": "stat", "stat_digits": 2}).startswith("U = 34")


def test_p_less_than_and_exact():
    r = _res(p_value=0.0001)
    assert mr.render_annotation(r, {"content": "p", "p_less_than_style": True}) == "p < 0.001"
    exact = mr.render_annotation(r, {"content": "p", "p_less_than_style": False, "digits": 4})
    assert exact == "p = 0.0001"


def test_ns_label_and_hide():
    r = _res(group_b="C", statistic=0.4, p_value=0.7, adjusted_p_value=0.7, reject_null=False,
             effect_size=0.05)
    assert mr.render_annotation(r, {"content": "stars", "use_ns": True}) == "n.s."
    assert mr.render_annotation(r, {"content": "stars", "use_ns": False}) == "ns"
    assert mr.render_annotation(r, {"content": "p_stars", "hide_nonsignificant": True}) == ""


def test_flags_mode():
    r = _res()
    out = mr.render_annotation(r, {"content": "flags", "show_stat": True, "show_p": True,
                                   "show_n": True, "stat_digits": 3})
    assert "t = 2.43" in out and "p = 0.023" in out and "n = 40" in out


# --- on-figure rendering with content modes -------------------------------

def _bar_df():
    return pd.DataFrame([{"g": g, "y": float(RNG.normal(m, 0.3))}
                         for g, m in [("A", 1.0), ("B", 2.0), ("C", 1.4)] for _ in range(9)])


def _render_bar(annotation):
    spec = make_spec("barplot_with_error_bar", "t", "publication")
    spec["mapping"] = {"x": "g", "y": "y"}
    spec["statistics"] = {"enabled": True, "test": "welch_t", "comparison_mode": "all_pairs",
                          "correction": "benjamini_hochberg", "annotation": annotation}
    return render(spec, _bar_df())


@pytest.mark.parametrize("content", ["stars", "p", "p_adj", "stat", "effect", "p_stat", "full"])
def test_figure_renders_each_content_mode(content):
    res = _render_bar({"content": content})
    ax = res.figure.axes[0]
    labels = [t.get_text() for t in ax.texts if t.get_text().strip()]
    assert labels, f"no annotation labels drawn for content={content}"
    plt.close(res.figure)


def test_custom_template_on_figure():
    res = _render_bar({"content": "custom", "template": "{effect_symbol}={effect}"})
    ax = res.figure.axes[0]
    assert any("=" in t.get_text() for t in ax.texts)
    plt.close(res.figure)


def test_statsspec_retains_all_values_when_hidden():
    # Figure shows only stars, but the exported StatsSpec keeps p, adj p, effect, stat.
    res = _render_bar({"content": "stars"})
    payload = res.metadata["statistics_report"]
    for r in payload["results"]:
        assert r["p_value"] is not None
        assert r["statistic"] is not None
        assert r["effect_size"] is not None
    plt.close(res.figure)


def test_hidden_nonsignificant_still_in_statsspec(tmp_path):
    res = _render_bar({"content": "p_stars", "hide_nonsignificant": True})
    # Every computed comparison remains in the report even if not drawn.
    assert len(res.stats_report.results) == 3
    out = render_to_files(
        {**make_spec("barplot_with_error_bar", "data.csv", "publication"),
         "mapping": {"x": "g", "y": "y"},
         "statistics": {"enabled": True, "test": "welch_t", "comparison_mode": "all_pairs",
                        "annotation": {"content": "p_stars", "hide_nonsignificant": True}}},
        _bar_df(), str(tmp_path / "fig"))
    assert out["stats_sidecar"]
    plt.close(res.figure)


@pytest.mark.parametrize("fmt", ["svg", "pdf", "png"])
def test_annotations_export_all_formats(fmt, tmp_path):
    import os

    spec = make_spec("barplot_with_error_bar", "data.csv", "publication")
    spec["mapping"] = {"x": "g", "y": "y"}
    spec["statistics"] = {"enabled": True, "test": "welch_t", "comparison_mode": "all_pairs",
                          "annotation": {"content": "p_stat"}}
    out = render_to_files(spec, _bar_df(), str(tmp_path / "fig"), formats=[fmt])
    assert os.path.exists(out["files"][0]) and os.path.getsize(out["files"][0]) > 200
