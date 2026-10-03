"""Bracket geometry of the statistical-annotation engine and its wiring into the point plots.

Covers the bracket engine (``plots/stats_overlay.annotate_pairwise``): a bracket starts above the
highest drawn element of every group it spans, stacked brackets do not collide, the value axis
grows so the top label fits without cropping any observation, geometry keys change geometry only,
and specs written before the point-based geometry still render. Also covers the point-based
renderers (dot strip, beeswarm, raincloud, paired slopegraph) producing a StatsReport and brackets
when statistics are enabled - and nothing when they are not.

Data: the synthetic group-comparison files in ``examples/group_comparison_test_data`` (CC0) and a
small synthetic paired design built here.
"""

from __future__ import annotations

import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.plots import stats_overlay
from make_my_figure_core.plots.registry import make_spec, render
from make_my_figure_core.statistics.annotations import AnnotationItem
from make_my_figure_core.statistics.models import StatsReport
from make_my_figure_core.styles.engine import load_profile

DATA = pathlib.Path(__file__).resolve().parent.parent / "examples" / "group_comparison_test_data"
POINT_TYPES = ["dot_strip_plot", "beeswarm_plot", "raincloud_plot"]


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


def _two_groups() -> pd.DataFrame:
    return pd.read_csv(DATA / "two_groups_n6.csv")


def _three_groups() -> pd.DataFrame:
    # Control (n=5), Low dose (n=8), High dose (n=11): the middle group is the tallest
    return pd.read_csv(DATA / "three_groups_unequal.csv")


def _paired(n: int = 8, seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for s in range(n):
        base = rng.normal(10, 2)
        for cond, shift in [("Before", 0.0), ("After", 2.5), ("Late", 1.0)]:
            rows.append({"id": f"S{s}", "cond": cond, "val": base + shift + rng.normal(0, 0.8)})
    return pd.DataFrame(rows)


def _stats(**overrides):
    base = {"enabled": True, "test": "welch_t", "comparison_mode": "all_pairs",
            "correction": "benjamini_hochberg", "annotation": {"content": "p"}}
    base.update(overrides)
    return base


def _spec(plot_type, statistics=None, mapping=None):
    return make_spec(plot_type, "synthetic", "publication",
                     mapping=mapping or {"x": "group", "y": "value"}, statistics=statistics)


def _brackets(ax):
    """Bracket lines: four vertices shaped [c, c, c', c'] along x (vertical layout)."""
    out = []
    for line in ax.lines:
        xs = np.asarray(line.get_xdata(), dtype=float)
        ys = np.asarray(line.get_ydata(), dtype=float)
        if len(xs) == 4 and xs[0] == xs[1] and xs[2] == xs[3] and xs[0] != xs[2]:
            out.append({"x1": min(xs[0], xs[2]), "x2": max(xs[0], xs[2]), "base": float(ys[0]),
                        "tick": float(ys[1])})
    return out


def _label_texts(ax):
    return [t for t in ax.texts if t.get_text().strip()]


def _info(res):
    return res.stats_report.config["_annotation_info"]


# --------------------------------------------------------------------------------------------
# (a) a two-group bracket clears both groups and every point
# --------------------------------------------------------------------------------------------

def test_two_group_bracket_sits_above_both_tops_and_every_point():
    df = _two_groups()
    res = render(_spec("dot_strip_plot", _stats()), df)
    ax = res.figure.axes[0]
    brackets = _brackets(ax)
    assert len(brackets) == 1
    (b,) = brackets
    info = _info(res)
    assert info["n_brackets"] == 1 and info["brackets"][0]["level"] == 0
    highest_point = float(df["value"].max())
    per_group_max = df.groupby("group")["value"].max()
    assert b["base"] > highest_point
    assert b["base"] > per_group_max.max()
    # the bracket starts from the taller of the two groups (the summary error bar may add to it)
    assert info["brackets"][0]["start"] >= per_group_max.max() - 1e-12
    # every drawn point is below the bracket base
    for coll in ax.collections:
        offsets = coll.get_offsets()
        if len(offsets):
            assert float(np.max(offsets[:, 1])) < b["base"]


# --------------------------------------------------------------------------------------------
# (b) three groups, all pairs from an omnibus + post hoc: no overlap, the outer bracket clears B
# --------------------------------------------------------------------------------------------

def _display_boxes(ax):
    fig = ax.figure
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    return [t.get_window_extent(renderer=r) for t in _label_texts(ax)]


def _overlapping_pairs(boxes):
    n = 0
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            if a.x0 < b.x1 - 1 and a.x1 > b.x0 + 1 and a.y0 < b.y1 - 1 and a.y1 > b.y0 + 1:
                n += 1
    return n


def test_three_group_posthoc_brackets_do_not_overlap_and_outer_clears_middle_group():
    df = _three_groups()
    stats = _stats(test="one_way_anova", posthoc=True, posthoc_test="welch_t")
    res = render(_spec("dot_strip_plot", stats), df)
    ax = res.figure.axes[0]
    report = res.stats_report
    assert [r.comparison_type for r in report.results].count("two_group") == 3
    info = _info(res)
    assert info["n_brackets"] == 3

    # the outer bracket (Control - High dose) spans Low dose, the tallest group
    groups = res.metadata["groups"]
    assert groups == ["Control", "Low dose", "High dose"]
    middle_top = float(df.loc[df["group"] == "Low dose", "value"].max())
    outer = [b for b in info["brackets"] if set(b["groups"]) == {"Control", "High dose"}]
    assert len(outer) == 1
    assert outer[0]["start"] >= middle_top - 1e-12, "the spanned middle group was not checked"
    assert outer[0]["base"] > middle_top
    assert outer[0]["base"] > float(df["value"].max())

    # a bracket never runs through another bracket's line or label where their spans overlap
    for i, a in enumerate(info["brackets"]):
        for b in info["brackets"][i + 1:]:
            spans_overlap = a["span"][0] < b["span"][1] and b["span"][0] < a["span"][1]
            if spans_overlap:
                lo, hi = sorted((a, b), key=lambda s: s["base"])
                assert lo["label_top"] < hi["base"], f"{lo['groups']} collides with {hi['groups']}"
    # and the drawn labels do not overlap on screen
    assert _overlapping_pairs(_display_boxes(ax)) == 0
    # inner brackets sit below the outer one
    assert max(b["base"] for b in info["brackets"] if b is not outer[0]) < outer[0]["base"]


# --------------------------------------------------------------------------------------------
# (c) the value axis includes the top label; no observation is cropped
# --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("plot_type", POINT_TYPES)
def test_ylim_includes_top_label_and_keeps_observations(plot_type):
    df = _three_groups()
    plain = render(_spec(plot_type), df)
    y0_plain = plain.figure.axes[0].get_ylim()[0]

    res = render(_spec(plot_type, _stats()), df)
    ax = res.figure.axes[0]
    fig = ax.figure
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    ax_box = ax.get_window_extent(renderer=r)
    labels = _label_texts(ax)
    assert labels, "no bracket labels drawn"
    for t in labels:
        bb = t.get_window_extent(renderer=r)
        assert bb.y1 <= ax_box.y1 + 0.5, f"label {t.get_text()!r} pokes above the axes"
        assert bb.y0 >= ax_box.y0
    # the data are still fully inside the axes: bottom limit unchanged, all points inside
    assert ax.get_ylim()[0] == pytest.approx(y0_plain)
    assert ax.get_ylim()[0] < float(df["value"].min())
    assert ax.get_ylim()[1] > _info(res)["top"] - 1e-9
    # the report says the same top the axes shows
    assert _info(res)["top"] == pytest.approx(ax.get_ylim()[1])


# --------------------------------------------------------------------------------------------
# (d) geometry keys change only geometry
# --------------------------------------------------------------------------------------------

def test_geometry_keys_change_geometry_but_not_the_p_text():
    df = _three_groups()
    base_ann = {"content": "p"}
    big_ann = {"content": "p", "font_size": 14.0, "line_width": 2.5, "bracket_height_pt": 9.0,
               "gap_pt": 14.0}
    frac_ann = {"content": "p", "bracket_height_frac": 0.08, "gap_frac": 0.12, "top_margin_frac": 0.2}
    results = {}
    for name, ann in [("base", base_ann), ("big", big_ann), ("frac", frac_ann)]:
        res = render(_spec("beeswarm_plot", _stats(annotation=ann)), df)
        ax = res.figure.axes[0]
        results[name] = {
            "texts": sorted(t.get_text() for t in _label_texts(ax)),
            "ticks": sorted(round(b["tick"] - b["base"], 9) for b in _brackets(ax)),
            "top": ax.get_ylim()[1],
            "p": [r.p_value for r in res.stats_report.results],
            "fontsizes": {t.get_fontsize() for t in _label_texts(ax)},
        }
    assert results["base"]["texts"] == results["big"]["texts"] == results["frac"]["texts"]
    assert results["base"]["p"] == results["big"]["p"] == results["frac"]["p"]
    assert "p" in results["base"]["texts"][0]
    # geometry did move
    assert results["big"]["ticks"] != results["base"]["ticks"]
    assert max(results["big"]["ticks"]) > max(results["base"]["ticks"])
    assert results["big"]["top"] > results["base"]["top"]
    assert results["big"]["fontsizes"] == {14.0}
    assert results["frac"]["ticks"] != results["base"]["ticks"]


def test_point_based_geometry_is_stable_across_value_scales():
    """A bracket tick is a number of points, so scaling the data by 1000 leaves its screen size alone."""
    df = _two_groups()
    small = render(_spec("dot_strip_plot", _stats()), df)
    scaled = df.assign(value=df["value"] * 1000.0)
    big = render(_spec("dot_strip_plot", _stats()), scaled)

    def tick_px(res):
        ax = res.figure.axes[0]
        res.figure.canvas.draw()
        (b,) = _brackets(ax)
        y = ax.transData.transform([[0.0, b["base"]], [0.0, b["tick"]]])[:, 1]
        return float(abs(y[1] - y[0]))

    assert tick_px(small) == pytest.approx(tick_px(big), rel=0.05)
    assert _info(small)["geometry"]["point_based"] is True


# --------------------------------------------------------------------------------------------
# (e) statistics on the point renderers
# --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("plot_type", POINT_TYPES)
def test_point_renderers_produce_a_report_and_brackets(plot_type):
    df = _three_groups()
    res = render(_spec(plot_type, _stats()), df)
    assert isinstance(res.stats_report, StatsReport)
    two_group = [r for r in res.stats_report.results if r.comparison_type == "two_group"]
    assert len(two_group) == 3
    assert all(r.p_value is not None for r in two_group)
    assert res.metadata["statistics_report"]["results"]
    assert len(_brackets(res.figure.axes[0])) == 3
    assert len(_label_texts(res.figure.axes[0])) == 3
    assert _info(res)["n_brackets"] == 3


@pytest.mark.parametrize("plot_type", POINT_TYPES)
def test_point_renderers_run_nothing_unless_enabled(plot_type):
    df = _three_groups()
    res = render(_spec(plot_type), df)
    assert res.stats_report is None
    assert "statistics_report" not in res.metadata
    assert _brackets(res.figure.axes[0]) == []
    disabled = render(_spec(plot_type, {"enabled": False, "test": "welch_t"}), df)
    assert disabled.stats_report is None


def test_paired_slopegraph_runs_paired_tests_and_draws_brackets():
    df = _paired()
    spec = make_spec("paired_slopegraph", "synthetic", "publication",
                     mapping={"subject": "id", "condition": "cond", "value": "val"},
                     statistics={"enabled": True, "annotation": {"content": "p"}})
    res = render(spec, df)
    report = res.stats_report
    assert isinstance(report, StatsReport)
    two_group = [r for r in report.results if r.comparison_type == "two_group"]
    assert len(two_group) == 3
    # auto resolves to the paired test with the subject column as the pair id
    assert {r.test_id for r in two_group} == {"paired_t"}
    assert all(r.paired for r in two_group)
    assert all(r.paired_id_column == "id" for r in two_group)
    assert all(r.n_by_group and set(r.n_by_group.values()) == {8} for r in two_group)
    ax = res.figure.axes[0]
    brackets = _brackets(ax)
    assert len(brackets) == 3
    # brackets clear every drawn point (the line markers)
    highest = max(float(np.max(line.get_ydata())) for line in ax.lines if len(line.get_xdata()) != 4)
    assert min(b["base"] for b in brackets) > highest
    # positions are keyed by the condition labels in drawn order
    assert {tuple(b["groups"]) for b in _info(res)["brackets"]} == {
        ("Before", "After"), ("Before", "Late"), ("After", "Late")}
    assert res.metadata["statistics_report"]["results"][0]["test_id"] == "paired_t"


def test_paired_slopegraph_honours_an_explicit_wilcoxon():
    df = _paired()
    spec = make_spec("paired_slopegraph", "synthetic", "publication",
                     mapping={"subject": "id", "condition": "cond", "value": "val"},
                     statistics={"enabled": True, "test": "wilcoxon",
                                 "selected_pairs": [["Before", "After"]],
                                 "comparison_mode": "selected_pairs"})
    res = render(spec, df)
    two_group = [r for r in res.stats_report.results if r.comparison_type == "two_group"]
    assert len(two_group) == 1 and two_group[0].test_id == "wilcoxon"
    assert len(_brackets(res.figure.axes[0])) == 1


def test_paired_slopegraph_without_statistics_is_unchanged():
    df = _paired()
    spec = make_spec("paired_slopegraph", "synthetic", "publication",
                     mapping={"subject": "id", "condition": "cond", "value": "val"})
    res = render(spec, df)
    assert res.stats_report is None
    assert _brackets(res.figure.axes[0]) == []
    assert res.metadata["n_subjects"] == 8


# --------------------------------------------------------------------------------------------
# (f) old specs still render
# --------------------------------------------------------------------------------------------

def test_old_spec_without_geometry_keys_renders():
    df = _three_groups()
    legacy = {"enabled": True, "test": "welch_t", "comparison_mode": "all_pairs",
              "annotation": {"mode": "stars"}}
    res = render(_spec("dot_strip_plot", legacy), df)
    assert len(_brackets(res.figure.axes[0])) == 3
    assert _info(res)["geometry"]["point_based"] is True


def test_old_spec_with_explicit_fractions_uses_them():
    """A spec that pinned the legacy fractions keeps fraction-of-range geometry."""
    df = _three_groups()
    legacy = {"enabled": True, "test": "welch_t", "comparison_mode": "all_pairs",
              "annotation": {"mode": "stars", "bracket_height_frac": 0.03, "gap_frac": 0.06,
                             "top_margin_frac": 0.10}}
    res = render(_spec("dot_strip_plot", legacy), df)
    ax = res.figure.axes[0]
    info = _info(res)
    assert info["n_brackets"] == 3
    assert info["geometry"]["point_based"] is False
    plain_ylim = render(_spec("dot_strip_plot"), df).figure.axes[0].get_ylim()
    yr = plain_ylim[1] - plain_ylim[0]
    ticks = {round(b["tick"] - b["base"], 6) for b in _brackets(ax)}
    assert ticks == {round(0.03 * yr, 6)}


def test_engine_signature_accepts_orientation_and_group_maps():
    """Direct engine call: horizontal brackets run along x, categories on y, xlim grows."""
    style = load_profile("publication")
    fig, ax = plt.subplots(figsize=(4, 3))
    cats = ["A", "B", "C"]
    values = [3.0, 5.0, 2.0]
    ax.barh(range(3), values, height=0.6)
    ax.set_yticks(range(3))
    ax.set_yticklabels(cats)
    positions = {c: float(i) for i, c in enumerate(cats)}
    tops = {c: v for c, v in zip(cats, values)}
    items = [AnnotationItem("A", "C", "p = 0.01", 0.01, 0.01, True),
             AnnotationItem("A", "B", "p = 0.20", 0.20, 0.20, False)]
    x1_before = ax.get_xlim()[1]

    def lookup(item):
        return positions[item.group_a], positions[item.group_b]

    info = stats_overlay.annotate_pairwise(ax, items, lookup, style=style, cfg={"content": "p"},
                                           positions=positions, tops=tops, orientation="horizontal")
    assert info["orientation"] == "horizontal" and info["n_brackets"] == 2
    assert ax.get_xlim()[1] > x1_before
    # A-C spans B, the largest bar: the bracket base clears it
    outer = [b for b in info["brackets"] if b["groups"] == ["A", "C"]][0]
    assert outer["start"] == 5.0 and outer["base"] > 5.0
    # bracket lines: four vertices shaped [v, v', v', v] along x with y pairs [c, c, c', c']
    horiz = [ln for ln in ax.lines
             if len(ln.get_ydata()) == 4 and ln.get_ydata()[0] == ln.get_ydata()[1]
             and ln.get_ydata()[2] == ln.get_ydata()[3] and ln.get_xdata()[0] == ln.get_xdata()[3]]
    assert len(horiz) == 2
    # labels sit to the right of their bracket tick
    for t in ax.texts:
        assert t.get_ha() == "left"
    for b in info["brackets"]:
        assert ax.get_xlim()[1] >= b["label_top"]


def test_vertical_engine_checks_every_spanned_group():
    """The middle group is taller than both compared groups: the bracket still clears it."""
    style = load_profile("publication")
    fig, ax = plt.subplots(figsize=(4, 3))
    positions = {"A": 0.0, "B": 1.0, "C": 2.0}
    tops = {"A": 1.0, "B": 9.0, "C": 1.5}
    ax.bar(list(positions.values()), list(tops.values()))
    items = [AnnotationItem("A", "C", "*", 0.01, 0.01, True)]
    info = stats_overlay.annotate_pairwise(
        ax, items, lambda it: (positions[it.group_a], positions[it.group_b]), style=style, cfg={},
        top_lookup=lambda it: max(tops[it.group_a], tops[it.group_b]), positions=positions, tops=tops)
    assert info["brackets"][0]["start"] == 9.0
    assert info["brackets"][0]["base"] > 9.0
    assert ax.get_ylim()[1] > info["brackets"][0]["label_top"]
