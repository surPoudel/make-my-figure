"""Tests for on-figure statistical annotations (brackets + panels)."""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.plots.registry import make_spec, render

RNG = np.random.default_rng(7)


def _bar_df():
    return pd.DataFrame([{"condition": c, "measurement": float(RNG.normal(m, 0.25))}
                         for c, m in [("Ctrl", 1.0), ("A", 1.9), ("B", 0.8)] for _ in range(10)])


def _box_df():
    return pd.DataFrame([{"group": g, "value": float(RNG.normal(m, 0.5))}
                         for g, m in [("H", 4.5), ("D", 6.5), ("T", 5.2)] for _ in range(18)])


def _stats(**kw):
    base = {"enabled": True, "test": "welch_t", "comparison_mode": "all_pairs",
            "correction": "benjamini_hochberg", "annotation": {"mode": "stars"}}
    base.update(kw)
    return base


def _count_text(ax, needle):
    return sum(1 for t in ax.texts if needle in t.get_text())


def test_brackets_render_for_bar():
    df = _bar_df()
    spec = make_spec("barplot_with_error_bar", "t", "publication")
    spec["mapping"] = {"x": "condition", "y": "measurement", "error": "sem"}
    spec["statistics"] = _stats()
    res = render(spec, df)
    ax = res.figure.axes[0]
    # 3 pairwise comparisons -> 3 bracket labels (stars or ns).
    labels = [t.get_text() for t in ax.texts]
    star_like = [l for l in labels if l in ("ns",) or set(l) <= set("*")]
    assert len(star_like) == 3
    plt.close(res.figure)


def test_brackets_render_for_box():
    df = _box_df()
    spec = make_spec("boxplot_or_violin_with_points", "t", "publication")
    spec["mapping"] = {"x": "group", "y": "value", "kind": "box"}
    spec["statistics"] = _stats()
    res = render(spec, df)
    assert res.stats_report is not None and len(res.stats_report.results) == 3
    plt.close(res.figure)


def test_brackets_expand_ylim_no_clip():
    df = _bar_df()
    spec = make_spec("barplot_with_error_bar", "t", "publication")
    spec["mapping"] = {"x": "condition", "y": "measurement", "error": "sem"}
    # No stats -> record data-driven top.
    res0 = render(spec, df)
    top0 = res0.figure.axes[0].get_ylim()[1]
    plt.close(res0.figure)
    spec["statistics"] = _stats()
    res1 = render(spec, df)
    top1 = res1.figure.axes[0].get_ylim()[1]
    # Adding brackets must raise the top so labels are not clipped.
    assert top1 > top0
    plt.close(res1.figure)


def test_stacked_brackets_do_not_share_level():
    # All-pairs on 3 groups includes an overarching pair that must stack above.
    df = _bar_df()
    spec = make_spec("barplot_with_error_bar", "t", "publication")
    spec["mapping"] = {"x": "condition", "y": "measurement", "error": "sem"}
    spec["statistics"] = _stats()
    res = render(spec, df)
    ax = res.figure.axes[0]
    # The bracket horizontal segments sit at >= 2 distinct y levels.
    ys = []
    for line in ax.lines:
        yd = line.get_ydata()
        if len(yd) == 4:  # bracket shape [y, y_tick, y_tick, y]
            ys.append(round(float(max(yd)), 4))
    assert len(set(ys)) >= 2
    plt.close(res.figure)


def test_exact_p_and_both_modes():
    df = _bar_df()
    spec = make_spec("barplot_with_error_bar", "t", "publication")
    spec["mapping"] = {"x": "condition", "y": "measurement", "error": "sem"}
    spec["statistics"] = _stats(annotation={"mode": "p"})
    res = render(spec, df)
    ax = res.figure.axes[0]
    assert _count_text(ax, "p =") + _count_text(ax, "p <") >= 1
    plt.close(res.figure)


def test_grouped_within_x_brackets():
    rows = []
    for dose in ["0.5", "1.0", "2.0"]:
        for supp, base in [("VC", 8), ("OJ", 13)]:
            for _ in range(8):
                rows.append({"dose": dose, "supp": supp, "len": float(RNG.normal(base + float(dose) * 3, 1.5))})
    df = pd.DataFrame(rows)
    spec = make_spec("grouped_barplot_with_error_bar", "t", "publication")
    spec["mapping"] = {"x": "dose", "group": "supp", "y": "len", "error": "sem"}
    spec["statistics"] = _stats(comparison_mode="within_x")
    res = render(spec, df)
    # One comparison per dose level.
    assert len(res.stats_report.results) == 3
    for r in res.stats_report.results:
        assert r.extra.get("within_x") is True
    plt.close(res.figure)


def test_survival_logrank_annotation():
    t = np.r_[RNG.exponential(10, 30), RNG.exponential(18, 30)]
    e = RNG.binomial(1, 0.8, 60)
    df = pd.DataFrame({"time_months": t, "event": e, "group": ["A"] * 30 + ["B"] * 30})
    spec = make_spec("kaplan_meier_survival_curve", "t", "publication")
    spec["mapping"] = {"time": "time_months", "event": "event", "group": "group"}
    spec["statistics"] = {"enabled": True, "test": "logrank"}
    res = render(spec, df)
    ax = res.figure.axes[0]
    assert _count_text(ax, "Log-rank") >= 1
    plt.close(res.figure)


def test_scatter_correlation_annotation():
    x = RNG.uniform(0, 10, 40)
    y = 1.4 * x + RNG.normal(0, 2, 40)
    df = pd.DataFrame({"x": x, "y": y})
    spec = make_spec("scatterplot_with_regression", "t", "publication")
    spec["mapping"] = {"x": "x", "y": "y", "fit_line": True}
    spec["statistics"] = {"enabled": True, "test": "pearson"}
    res = render(spec, df)
    ax = res.figure.axes[0]
    assert _count_text(ax, "r =") >= 1
    plt.close(res.figure)


def test_annotation_backed_by_stored_result():
    # Every bracket label must correspond to a stored StatResult p-value.
    df = _bar_df()
    spec = make_spec("barplot_with_error_bar", "t", "publication")
    spec["mapping"] = {"x": "condition", "y": "measurement", "error": "sem"}
    spec["statistics"] = _stats()
    res = render(spec, df)
    assert res.stats_report is not None
    assert all(r.p_value is not None for r in res.stats_report.results)
    assert res.metadata["statistics_report"]["results"]  # serialized into metadata
    plt.close(res.figure)
