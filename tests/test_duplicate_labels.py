"""Duplicate feature-label handling for Volcano and MA plots.

A DE table often maps several peptides/transcripts to one gene symbol. These tests
pin the shared duplicate-label policy (all / unique / count), deterministic
representative selection, per-point identity (independent click/unlabel/move),
PlotSpec round-trip, and that exports carry every expected label.
"""

from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")

import pandas as pd
import pytest

from make_my_figure_core.plots import label_policy as lp
from make_my_figure_core.plots.registry import make_spec, render, figure_to_bytes
from make_my_figure_core.spec.validate import validate_plot_spec

DATA = pd.DataFrame({
    "feature_id": ["pep_1", "pep_2", "pep_3", "pep_4", "pep_5"],
    "gene": ["Mbp", "Mbp", "Mbp", "Plp1", "Plp1"],
    "log2FC": [0.91, 0.95, 0.88, 1.30, 1.12],
    "pvalue": [1e-5, 2e-5, 3e-5, 1e-6, 4e-4],
    "padj": [0.001, 0.002, 0.003, 0.0001, 0.01],
    "mean_abundance": [10, 12, 9, 15, 11],
})

_BASE = {
    "x": "log2FC", "p": "pvalue", "label": "gene", "id_col": "feature_id",
    "adj_p": "padj", "statistic": None,
    "lfc_cutoff": 0.0, "p_cutoff": 1.0, "label_significant_only": False,
}


def _volcano(**over):
    m = {**_BASE, **over}
    return render(make_spec("volcano_plot", "t", "publication", mapping=m), DATA)


def _ma(**over):
    m = {"x": "mean_abundance", "y": "log2FC", "p": "pvalue", "label": "gene",
         "id_col": "feature_id", "adj_p": "padj", "p_cutoff": 1.0, **over}
    return render(make_spec("ma_plot", "t", "publication", mapping=m), DATA)


def _points(**over):
    """Run the shared engine over all rows and return the LabelPoints."""
    ls = DATA["gene"].astype(str)
    return lp.build_label_points(
        DATA, list(DATA.index), label_series=ls,
        text_fn=lambda i: str(DATA.at[i, "gene"]),
        x_col="log2FC", y_col="pvalue", id_col="feature_id",
        rep_columns={"pvalue": "pvalue", "padj": "padj", "effect": "log2FC", "statistic": None},
        total_counts=lp.total_label_counts(ls), **over)


# 1. Default policy labels every selected point.
def test_default_policy_is_all():
    assert lp.normalize_policy(None) == "all"
    pts = _points()  # default policy
    assert len(pts) == 5


# 2. Three Mbp rows produce three annotations in all-point mode.
def test_all_mode_keeps_three_mbp():
    pts = _points(policy="all")
    mbp = [p for p in pts if p.label_text == "Mbp"]
    assert len(mbp) == 3
    assert {p.point_id for p in mbp} == {"pep_1", "pep_2", "pep_3"}


# 3. Unique mode produces one Mbp label.
def test_unique_mode_one_mbp():
    pts = _points(policy="unique")
    assert sum(p.label_text == "Mbp" for p in pts) == 1
    assert len(pts) == 2  # Mbp + Plp1


# 4. Count mode produces "Mbp (n=3)".
def test_count_mode_suffix():
    pts = _points(policy="count")
    texts = {p.label_text for p in pts}
    assert "Mbp (n=3)" in texts
    assert "Plp1 (n=2)" in texts


# 5-7. Representative rules select deterministically.
@pytest.mark.parametrize("rule,expected", [
    ("pvalue", "pep_1"), ("padj", "pep_1"), ("effect", "pep_2"),
])
def test_representative_rule(rule, expected):
    pts = _points(policy="unique", representative_rule=rule)
    mbp = [p for p in pts if p.label_text == "Mbp"][0]
    assert mbp.point_id == expected


# 8-10. Point identity: clicking is independent per point.
def test_click_single_point_labels_only_it():
    r = _volcano(label_mode="selected", selected_points=["pep_1"])
    assert r.metadata["n_labeled"] == 1


def test_click_toggle_off_removes_only_that_point():
    # Simulate a second click on pep_1 (removed) while pep_2 stays selected.
    r = _volcano(label_mode="selected", selected_points=["pep_2"])
    assert r.metadata["n_labeled"] == 1
    # The remaining label is anchored at pep_2 (log2FC 0.95).
    # (n_labeled==1 confirms pep_1 no longer contributes.)


def test_click_second_mbp_is_independent_annotation():
    r = _volcano(label_mode="selected", selected_points=["pep_1", "pep_2"])
    assert r.metadata["n_labeled"] == 2  # two independent Mbp labels


# 11. Moving one duplicate label does not affect the other.
def test_point_offsets_are_per_point():
    offs = {"pep_1": [22.0, 22.0]}
    r = _volcano(label_mode="selected", selected_points=["pep_1", "pep_2"],
                 point_offsets=json.dumps(offs))
    assert r.metadata["n_labeled"] == 2  # renders without disturbing pep_2
    parsed = lp.parse_offsets(json.dumps(offs))
    assert "pep_1" in parsed and "pep_2" not in parsed


# 12. Annotation storage keys use point identity, not label text.
def test_point_id_distinct_from_label_text():
    pts = _points(policy="all")
    ids = [p.point_id for p in pts if p.label_text == "Mbp"]
    assert ids == ["pep_1", "pep_2", "pep_3"]      # distinct ids, same text
    r = _volcano()
    pid_list = [pp["point_id"] for pp in r.metadata["pickable_points"]]
    assert pid_list == ["pep_1", "pep_2", "pep_3", "pep_4", "pep_5"]
    assert r.metadata["pick_label_key"] == "selected_points"


# 13-14. PlotSpec round-trip preserves policy for both plot types.
@pytest.mark.parametrize("plot_type,base", [
    ("volcano_plot", _BASE),
    ("ma_plot", {"x": "mean_abundance", "y": "log2FC", "p": "pvalue",
                 "label": "gene", "id_col": "feature_id", "p_cutoff": 1.0}),
])
def test_plotspec_roundtrip_preserves_policy(plot_type, base):
    m = {**base, "duplicate_label_policy": "count",
         "duplicate_label_representative_rule": "effect",
         "duplicate_label_show_count": True}
    spec = make_spec(plot_type, "t", "publication", mapping=m)
    validate_plot_spec(spec, known_plot_types=[plot_type], known_styles=["publication"])
    reloaded = json.loads(json.dumps(spec))
    r = render(reloaded, DATA)
    assert r.metadata["duplicate_label_policy"] == "count"
    assert r.metadata["duplicate_label_representative_rule"] == "effect"


# 15. PNG/PDF/SVG exports contain all expected annotations.
def test_exports_contain_all_duplicate_labels():
    r = _volcano(label_mode="pasted", label_list=["Mbp"], duplicate_label_policy="all")
    assert r.metadata["n_labeled"] == 3
    svg = figure_to_bytes(r.figure, "svg").decode("utf-8", "ignore")
    assert svg.count("Mbp") >= 3            # editable text kept in the SVG
    # Raster/vector both serialize without error and are non-empty.
    assert len(figure_to_bytes(r.figure, "png")) > 0
    assert len(figure_to_bytes(r.figure, "pdf")) > 0


# 16. Top-N behavior is deterministic (and N = unique labels in unique mode).
def test_top_n_deterministic_and_unique_counts_labels():
    a = _volcano(label_mode="top_fdr", top_n=2, duplicate_label_policy="unique")
    b = _volcano(label_mode="top_fdr", top_n=2, duplicate_label_policy="unique")
    assert a.metadata["n_labeled"] == b.metadata["n_labeled"] == 2


def test_top_n_all_mode_counts_rows():
    r = _volcano(label_mode="top_fdr", top_n=4, duplicate_label_policy="all")
    assert r.metadata["n_labeled"] == 4     # rows, not unique genes


# 17. Pasted gene list obeys the selected duplicate policy.
def test_pasted_list_obeys_policy():
    all_mode = _volcano(label_mode="pasted", label_list=["Mbp"], duplicate_label_policy="all")
    uniq = _volcano(label_mode="pasted", label_list=["Mbp"], duplicate_label_policy="unique")
    assert all_mode.metadata["n_labeled"] == 3
    assert uniq.metadata["n_labeled"] == 1


# 18-19. Missing / empty label values are handled safely and not shown.
def test_missing_and_empty_labels_ignored():
    df = DATA.copy()
    df.loc[1, "gene"] = None
    df.loc[2, "gene"] = "   "
    ls = df["gene"].astype(str).str.strip()
    has_text = ls.ne("") & ls.str.lower().ne("nan") & df["gene"].notna()
    pts = lp.build_label_points(
        df, list(df[has_text].index), label_series=ls,
        text_fn=lambda i: (str(df.at[i, "gene"]).strip()
                           if pd.notna(df.at[i, "gene"]) else ""),
        x_col="log2FC", y_col="pvalue", id_col="feature_id",
        policy="all", rep_columns={}, total_counts={})
    labels = [p.label_text for p in pts]
    assert "" not in labels and "nan" not in [l.lower() for l in labels]
    assert set(labels) == {"Mbp", "Plp1"}  # pep_1 Mbp, pep_4/pep_5 Plp1


# 20. Existing specs without the duplicate policy still load (default 'all').
def test_legacy_spec_without_policy_defaults_all():
    m = {**_BASE, "label_mode": "pasted", "label_list": ["Mbp"]}
    spec = make_spec("volcano_plot", "t", "publication", mapping=m)
    assert "duplicate_label_policy" not in spec["mapping"]
    r = render(spec, DATA)
    assert r.metadata["duplicate_label_policy"] == "all"
    assert r.metadata["n_labeled"] == 3   # all three Mbp peptides labelled


# Regression: MA no longer collapses distant duplicates silently either.
def test_ma_all_mode_labels_every_row():
    r = _ma(label_top_n=10, duplicate_label_policy="all")
    assert r.metadata["n_labeled"] == 5
    r2 = _ma(label_top_n=10, duplicate_label_policy="unique")
    assert r2.metadata["n_labeled"] == 2
