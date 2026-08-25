"""Per-bar significance annotation for comparisons against a reference group.

Regression cover for collaborator concern C3: "it would be [good] if the P-values could be
automatically added on top of each bar as in the graph in Fig. 2F". That paper compares each
condition to one control and puts a single marker over each bar.

MakeMyFigure could already run the comparisons (`comparison_mode: vs_control` with a
`reference_group`) but the overlay engine could only draw pairwise brackets, so eight groups produced
seven stacked brackets that inflated the y-axis to about 2.9x the data range and compressed the bars
into the lower third of the panel.

All fixtures are synthetic.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.plots.registry import make_spec, render
from make_my_figure_core.statistics.models import StatsError

CONTROL = "control"
EFFECTS = {CONTROL: 1.00, "rnai_a": 0.62, "rnai_b": 0.58, "rnai_c": 0.70,
           "rnai_d": 0.75, "rnai_e": 0.80, "rnai_f": 1.45, "rnai_g": 1.60}


def _screen(seed: int = 11, n: int = 8) -> pd.DataFrame:
    """A knockdown screen: one control and seven conditions, n replicates each."""
    rng = np.random.default_rng(seed)
    rows = []
    for group, effect in EFFECTS.items():
        for value in rng.normal(effect * 100, 12, n):
            rows.append({"rnai": group, "area": float(value)})
    return pd.DataFrame(rows)


def _spec(placement="above_bar", content="stars", mode="vs_control",
          reference=CONTROL, test="welch_t"):
    statistics = {"enabled": True, "test": test, "comparison_mode": mode,
                  "correction": "benjamini_hochberg",
                  "annotation": {"content": content, "placement": placement}}
    if reference is not None:
        statistics["reference_group"] = reference
    return make_spec("barplot_with_error_bar", "synthetic", "publication",
                     mapping={"x": "rnai", "y": "area", "error": "sd"},
                     statistics=statistics)


def _bracket_artists(ax):
    """Significance brackets only.

    A bracket is drawn as a four-vertex path shaped [x0, x0, x1, x1] - up, across, down. Matching
    on the vertex count alone also catches the error-bar artists, whose vertex count grows with the
    number of categories, so the shape is checked too.
    """
    found = []
    for line in ax.lines:
        xs = np.asarray(line.get_xdata(), dtype=float)
        if len(xs) == 4 and xs[0] == xs[1] and xs[2] == xs[3] and xs[0] != xs[2]:
            found.append(line)
    return found


def _labels_by_category(ax):
    order = {t.get_text(): i for i, t in enumerate(ax.get_xticklabels())}
    drawn = {}
    for text in ax.texts:
        if text.get_text().strip():
            drawn[round(text.get_position()[0])] = text.get_text()
    return order, drawn


# --------------------------------------------------------------------------------------
# the requested placement
# --------------------------------------------------------------------------------------

def test_above_bar_puts_one_label_over_each_compared_bar():
    df = _screen()
    res = render(_spec(), df)
    try:
        info = res.stats_report.config["_annotation_info"]
        assert info["n_labels"] == len(EFFECTS) - 1
        assert info["reference"] == CONTROL
        assert not info["unplaced"]
        order, drawn = _labels_by_category(res.figure.axes[0])
        # every non-control bar carries a label...
        for group in EFFECTS:
            if group == CONTROL:
                continue
            assert order[group] in drawn, f"{group} has no label"
        # ...and the control bar carries none
        assert order[CONTROL] not in drawn
    finally:
        plt.close(res.figure)


def test_above_bar_draws_no_brackets():
    df = _screen()
    res = render(_spec(), df)
    try:
        assert _bracket_artists(res.figure.axes[0]) == []
    finally:
        plt.close(res.figure)


def test_above_bar_needs_far_less_headroom_than_brackets():
    """The reported problem: stacked brackets squeeze the data into part of the panel."""
    df = _screen()
    data_max = float(df["area"].max())

    bracketed = render(_spec(placement="bracket"), df)
    bracket_ratio = bracketed.figure.axes[0].get_ylim()[1] / data_max
    plt.close(bracketed.figure)

    above = render(_spec(placement="above_bar"), df)
    above_ratio = above.figure.axes[0].get_ylim()[1] / data_max
    plt.close(above.figure)

    assert bracket_ratio > 2.0, "expected the bracket stack to inflate the axis"
    assert above_ratio < 1.35
    assert above_ratio < bracket_ratio / 2


def test_each_label_sits_above_its_own_bar():
    df = _screen()
    res = render(_spec(), df)
    try:
        ax = res.figure.axes[0]
        order, _ = _labels_by_category(ax)
        means = df.groupby("rnai")["area"].mean()
        for text in ax.texts:
            if not text.get_text().strip():
                continue
            x, y = text.get_position()
            group = next(g for g, i in order.items() if i == round(x))
            # above the bar it belongs to, and not parked at the top of the panel
            assert y > means[group]
            assert y < ax.get_ylim()[1]
    finally:
        plt.close(res.figure)


def test_labels_do_not_collide_with_each_other():
    df = _screen()
    res = render(_spec(), df)
    try:
        ax = res.figure.axes[0]
        fig = res.figure
        fig.canvas.draw()
        boxes = [t.get_window_extent(fig.canvas.get_renderer())
                 for t in ax.texts if t.get_text().strip()]
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                assert not a.overlaps(b), "two significance labels overlap"
    finally:
        plt.close(res.figure)


# --------------------------------------------------------------------------------------
# reference handling
# --------------------------------------------------------------------------------------

def test_reference_group_is_inferred_when_not_restated():
    """vs_control comparisons all name the control, so the overlay can recover it."""
    from make_my_figure_core.plots.stats_overlay import infer_reference_group
    from make_my_figure_core.statistics.annotations import AnnotationItem

    items = [AnnotationItem(group_a="ctrl", group_b=g, text="*", p_value=0.01,
                            display_p=0.01, significant=True) for g in ("a", "b", "c")]
    assert infer_reference_group(items) == "ctrl"


def test_all_pairs_comparisons_have_no_single_reference():
    """With no shared group a label above one bar would be ambiguous, so None is returned."""
    from make_my_figure_core.plots.stats_overlay import infer_reference_group
    from make_my_figure_core.statistics.annotations import AnnotationItem

    items = [AnnotationItem(group_a=a, group_b=b, text="*", p_value=0.01,
                            display_p=0.01, significant=True)
             for a, b in (("a", "b"), ("b", "c"), ("a", "c"))]
    assert infer_reference_group(items) is None


def test_comparisons_without_a_reference_fall_back_to_brackets():
    """An all-pairs request must not silently lose its comparisons."""
    df = _screen(n=6)
    res = render(_spec(mode="all_pairs", reference=None), df)
    try:
        info = res.stats_report.config["_annotation_info"]
        # nothing could be placed above a single bar...
        assert info["n_labels"] == 0
        # ...so the bracket engine drew them instead
        assert info.get("bracket_fallback", {}).get("n_brackets", 0) > 0
        assert _bracket_artists(res.figure.axes[0])
    finally:
        plt.close(res.figure)


# --------------------------------------------------------------------------------------
# the drawn value must be the stored value
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("content", ["stars", "p", "p_adj"])
def test_every_label_is_reproducible_from_its_stored_result(content):
    """The invariant: renderers never format a p-value, they draw a stored one."""
    from make_my_figure_core.statistics import method_reporting

    df = _screen()
    res = render(_spec(content=content), df)
    try:
        ax = res.figure.axes[0]
        order, drawn = _labels_by_category(ax)
        assert res.stats_report.results
        for result in res.stats_report.results:
            target = result.group_b if result.group_a == CONTROL else result.group_a
            expected = method_reporting.render_annotation(result, {"content": content})
            assert drawn[order[target]] == expected
    finally:
        plt.close(res.figure)


def test_reported_p_values_match_scipy_and_statsmodels():
    """Independent oracles for the values the figure shows."""
    from scipy import stats as sps
    multitest = pytest.importorskip("statsmodels.stats.multitest")

    df = _screen()
    res = render(_spec(), df)
    try:
        results = list(res.stats_report.results)
    finally:
        plt.close(res.figure)

    control = df[df["rnai"] == CONTROL]["area"].to_numpy()
    raw = []
    for result in results:
        target = result.group_b if result.group_a == CONTROL else result.group_a
        other = df[df["rnai"] == target]["area"].to_numpy()
        raw.append(sps.ttest_ind(control, other, equal_var=False).pvalue)
    _, adjusted, _, _ = multitest.multipletests(raw, method="fdr_bh")

    for result, p_expected, q_expected in zip(results, raw, adjusted):
        assert result.p_value == pytest.approx(p_expected, abs=1e-12)
        assert result.adjusted_p_value == pytest.approx(q_expected, abs=1e-12)


def test_nonsignificant_comparisons_can_be_hidden():
    """A screen with mostly null conditions should not be papered with 'n.s.'."""
    rng = np.random.default_rng(2)
    df = pd.concat([
        pd.DataFrame({"rnai": g, "area": rng.normal(100, 12, 8)})
        for g in (CONTROL, "flat_a", "flat_b")
    ], ignore_index=True)
    spec = make_spec("barplot_with_error_bar", "synthetic", "publication",
                     mapping={"x": "rnai", "y": "area", "error": "sd"},
                     statistics={"enabled": True, "test": "welch_t",
                                 "comparison_mode": "vs_control",
                                 "reference_group": CONTROL,
                                 "annotation": {"content": "stars",
                                                "placement": "above_bar",
                                                "hide_nonsignificant": True}})
    res = render(spec, df)
    try:
        drawn = [t.get_text() for t in res.figure.axes[0].texts if t.get_text().strip()]
        assert drawn == []
    finally:
        plt.close(res.figure)


# --------------------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------------------

def test_bracket_remains_the_default_placement():
    from make_my_figure_core.statistics.schemas import default_annotation

    assert default_annotation()["placement"] == "bracket"

    df = _screen(n=5)
    spec = make_spec("barplot_with_error_bar", "synthetic", "publication",
                     mapping={"x": "rnai", "y": "area", "error": "sd"},
                     statistics={"enabled": True, "test": "welch_t",
                                 "comparison_mode": "vs_control",
                                 "reference_group": CONTROL,
                                 "annotation": {"content": "stars"}})
    res = render(spec, df)
    try:
        assert _bracket_artists(res.figure.axes[0])
    finally:
        plt.close(res.figure)


def test_unknown_placement_is_rejected():
    df = _screen(n=5)
    with pytest.raises(StatsError, match="placement"):
        render(_spec(placement="floating"), df)


def test_above_bar_works_for_box_and_violin_too():
    """The placement belongs to the overlay engine, not to one renderer."""
    df = _screen(n=10)
    spec = make_spec("boxplot_or_violin_with_points", "synthetic", "publication",
                     mapping={"x": "rnai", "y": "area", "kind": "box"},
                     statistics={"enabled": True, "test": "welch_t",
                                 "comparison_mode": "vs_control",
                                 "reference_group": CONTROL,
                                 "annotation": {"content": "stars",
                                                "placement": "above_bar"}})
    res = render(spec, df)
    try:
        info = res.stats_report.config["_annotation_info"]
        assert info["n_labels"] == len(EFFECTS) - 1
        assert _bracket_artists(res.figure.axes[0]) == []
    finally:
        plt.close(res.figure)
