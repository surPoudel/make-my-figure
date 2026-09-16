"""Scientific acceptance: a style preset changes pixels, never numbers.

Renders group-comparison figures with statistics enabled on the synthetic unequal-n datasets,
applies a demanding style preset through the guarded path, renders again, and asserts that the raw
values, group assignment, n per group, summary statistic, error-bar calculation, test, P values and
adjusted P values in the statistics report and the render metadata are identical. Only the drawn
appearance may differ.
"""

from __future__ import annotations

import copy
import json
import os
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import pytest

from make_my_figure_core import preset_preview as pv
from make_my_figure_core import presets
from make_my_figure_core.plots import registry
from make_my_figure_core.plots.registry import make_spec

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "examples" / "group_comparison_test_data"


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _demanding_preset(plot_type):
    return {"format": presets.PRESET_FORMAT, "format_version": 1, "name": "demanding", "mode": "style",
            "plot_type": plot_type, "journal_style": "publication",
            "style": {"tick_label_pt": 6.0, "axis_font_pt": 7.0, "annotation_pt": 6.0, "legend_pt": 6.0,
                      "spine_width_pt": 0.5, "line_width_pt": 0.8, "marker_size": 14.0,
                      "marker_edge_width": 0.5, "errorbar_capsize": 2.0, "palette_name": "grayscale"},
            "layout": {"column_width": "57mm", "aspect": 1.1},
            "options": {}, "output": {"width_mm": 57.0, "dpi": 300},
            "statistics_display": {"annotation": {"font_size": 6.0, "line_width": 0.6}},
            "universal": True}


def _stats_signature(result):
    rep = result.stats_report
    sig = []
    for r in (getattr(rep, "results", None) or []):
        sig.append({k: getattr(r, k, None) for k in
                    ("test_id", "test_name", "comparison_type", "group_a", "group_b", "n_total",
                     "n_by_group", "statistic", "df", "p_value", "adjusted_p_value", "correction_method",
                     "reject_null", "effect_size", "estimate", "confidence_interval_low",
                     "confidence_interval_high")})
    return json.dumps(sig, sort_keys=True, default=str)


def _metadata_numbers(result):
    """Everything numeric-looking in the render metadata except geometry/appearance blocks."""
    md = copy.deepcopy(result.metadata or {})
    for k in ("style", "layout", "output", "figure_size_in", "render_time", "warnings",
              "app_version", "created", "timestamp", "rc", "spec", "export_dimensions",
              "layout_qc", "publication_check", "disclaimer", "style_profile"):
        md.pop(k, None)   # appearance / export geometry: allowed to change
    if isinstance(md.get("statistics"), dict):
        md["statistics"].pop("annotation", None)   # annotation geometry/typography is appearance
    rep = md.get("statistics_report")
    if isinstance(rep, dict):
        cfg = rep.get("config")
        if isinstance(cfg, dict):
            # bracket geometry and annotation typography are appearance, not results
            cfg.pop("_annotation_info", None)
            cfg.pop("annotation", None)
    return json.dumps(md, sort_keys=True, default=str)


CASES = [
    ("boxplot_or_violin_with_points", "three_groups_unequal.csv", {"x": "group", "y": "value"}, "all_pairs"),
    ("boxplot_or_violin_with_points", "unequal_6_vs_17.csv", {"x": "group", "y": "value"}, "auto"),
    ("barplot_with_error_bar", "unequal_4_9_13.csv", {"x": "group", "y": "value"}, "all_pairs"),
    ("barplot_with_error_bar", "two_groups_n30.csv", {"x": "group", "y": "value"}, "auto"),
    ("dot_strip_plot", "unequal_5_vs_8.csv", {"x": "group", "y": "value"}, "auto"),
]


@pytest.mark.parametrize("plot_type,csv_name,mapping,mode", CASES,
                         ids=[f"{c[0]}-{c[1]}" for c in CASES])
def test_numbers_identical_before_and_after_preset(plot_type, csv_name, mapping, mode):
    df = pd.read_csv(DATA / csv_name)
    spec = make_spec(plot_type, csv_name, "publication", mapping=dict(mapping),
                     statistics={"enabled": True, "test": "auto", "comparison_mode": mode,
                                 "posthoc": mode == "all_pairs",
                                 "correction": "benjamini_hochberg", "alpha": 0.05,
                                 "value_column": mapping["y"], "group_column": mapping["x"]})
    before = registry.render(spec, df)
    n_before = df.groupby(mapping["x"])[mapping["y"]].size().to_dict()
    sig_before = _stats_signature(before)
    md_before = _metadata_numbers(before)

    res = pv.apply_with_guard(_demanding_preset(plot_type), spec, columns=list(df.columns))
    assert pv.assert_style_safe(spec, res.spec) == []
    after = registry.render(res.spec, df)

    # the data frame is untouched and the groups/n come from the data, not the preset
    assert df.groupby(mapping["x"])[mapping["y"]].size().to_dict() == n_before
    assert _stats_signature(after) == sig_before, "statistics changed under a style preset"
    assert _metadata_numbers(after) == md_before, "render metadata numbers changed under a style preset"
    # the statistics block itself is unchanged
    assert {k: v for k, v in res.spec["statistics"].items() if k != "annotation"} == \
           {k: v for k, v in spec["statistics"].items() if k != "annotation"}
    # but the drawing did change (width, fonts)
    assert abs(after.figure.get_size_inches()[0] * 25.4 - 57.0) < 0.5
    assert before.figure.get_size_inches()[0] != after.figure.get_size_inches()[0]


def test_stats_report_has_results_for_the_unequal_design():
    """Guard against a vacuous identity test: the report must actually contain comparisons."""
    df = pd.read_csv(DATA / "three_groups_unequal.csv")
    spec = make_spec("boxplot_or_violin_with_points", "x.csv", "publication",
                     mapping={"x": "group", "y": "value"},
                     statistics={"enabled": True, "test": "auto", "comparison_mode": "all_pairs",
                                 "posthoc": True, "value_column": "value", "group_column": "group"})
    out = registry.render(spec, df)
    results = getattr(out.stats_report, "results", None) or []
    assert len([r for r in results if r.comparison_type == "two_group"]) >= 3
    ns = {}
    for r in results:
        ns.update(r.n_by_group or {})
    assert ns == {"Control": 5, "Low dose": 8, "High dose": 11}
