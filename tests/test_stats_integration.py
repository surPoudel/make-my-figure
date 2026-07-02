"""Integration + export tests for statistics on renderers and sidecars."""

import json
import os

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.plots.registry import make_spec, render, render_to_files
from make_my_figure_core.statistics.schemas import normalize_stats_spec, validate_stats_spec

RNG = np.random.default_rng(99)


def _bar():
    df = pd.DataFrame([{"condition": c, "measurement": float(RNG.normal(m, 0.3))}
                       for c, m in [("Ctrl", 1.0), ("A", 1.8), ("B", 0.9)] for _ in range(9)])
    spec = make_spec("barplot_with_error_bar", "data.csv", "publication")
    spec["mapping"] = {"x": "condition", "y": "measurement", "error": "sem"}
    spec["statistics"] = {"enabled": True, "test": "welch_t", "comparison_mode": "all_pairs",
                          "correction": "benjamini_hochberg"}
    return spec, df


def test_render_attaches_stats_report_and_metadata():
    spec, df = _bar()
    res = render(spec, df)
    assert res.stats_report is not None
    assert "statistics_report" in res.metadata
    assert res.metadata["statistics_report"]["correction_method"] == "benjamini_hochberg"


def test_render_without_stats_has_no_report():
    spec, df = _bar()
    spec.pop("statistics")
    res = render(spec, df)
    assert res.stats_report is None
    assert "statistics_report" not in res.metadata
    plt.close(res.figure)


def test_stats_sidecar_written(tmp_path):
    spec, df = _bar()
    out = render_to_files(spec, df, str(tmp_path / "fig"))
    assert out["stats_sidecar"] and os.path.exists(out["stats_sidecar"])
    payload = json.load(open(out["stats_sidecar"]))
    assert payload["results"] and payload["method_paragraph"]
    assert "disclaimer" in payload
    # plotspec sidecar also embeds the statistics config
    plot_payload = json.load(open(out["sidecar"]))
    assert "statistics" in plot_payload["plot_spec"]


def test_disabled_stats_produces_no_annotation():
    spec, df = _bar()
    spec["statistics"]["enabled"] = False
    res = render(spec, df)
    assert res.stats_report is None
    plt.close(res.figure)


def test_normalize_and_validate_spec():
    norm = normalize_stats_spec({"test": "bogus", "alpha": 3})
    assert norm["test"] == "auto"
    assert norm["alpha"] == 0.05
    errs = validate_stats_spec({"test": "welch_t", "comparison_mode": "all_pairs", "alpha": 0.05})
    assert errs == []
    assert validate_stats_spec({"test": "nope", "comparison_mode": "x", "alpha": 5})


def test_volcano_does_not_invent_pvalues():
    # Volcano has no auto test; enabling stats should not fabricate comparisons.
    from make_my_figure_core.statistics import run_statistics

    df = pd.DataFrame({"log2_fold_change": RNG.normal(0, 2, 30),
                       "adjusted_p_value": RNG.uniform(0, 1, 30),
                       "label": [f"g{i}" for i in range(30)]})
    report = run_statistics(df, {"enabled": True, "test": "auto"},
                            plot_type="volcano_plot", mapping={})
    assert report.results == []


def test_auto_test_selection_two_vs_multi_group():
    from make_my_figure_core.statistics import run_statistics

    two = pd.DataFrame([{"g": g, "v": float(RNG.normal(m, 1))}
                        for g, m in [("a", 0), ("b", 1)] for _ in range(12)])
    rep2 = run_statistics(two, {"enabled": True, "test": "auto", "comparison_mode": "all_pairs"},
                          plot_type="boxplot_or_violin_with_points",
                          mapping={"x": "g", "y": "v"})
    assert rep2.results and rep2.results[0].test_id in ("welch_t", "students_t", "mann_whitney")
