"""Tests for publication QC scoring + auto-fix (make_my_figure_core.qc)."""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import pytest

from make_my_figure_core.plots.registry import make_spec, render
from make_my_figure_core.qc import (
    apply_fixes,
    score_publication,
    suggest_fixes,
)

MOCK_DIR = os.path.join(os.path.dirname(__file__), "..", "mock_data")


def _load(name):
    from make_my_figure_core.io.loaders import load_table
    return load_table(os.path.join(MOCK_DIR, name))


def _check_ids(score):
    return {c.id for c in score.checks}


def test_flags_missing_axis_labels():
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [1, 3, 2])  # no x/y labels
    score = score_publication(figure=fig)
    assert "missing_axis_labels" in _check_ids(score)
    plt.close(fig)


def test_flags_low_export_dpi():
    info = _load("barplot_error_raw.csv")
    spec = make_spec("barplot_with_error_bar", "barplot_error_raw.csv", "publication")
    spec["output"]["dpi"] = 72
    result = render(spec, info.dataframe)
    score = score_publication(result=result, spec=spec)
    dpi_checks = [c for c in score.checks if c.id == "export_dpi"]
    assert dpi_checks and dpi_checks[0].level == "fail"
    assert score.level == "fail"
    plt.close(result.figure)


def test_flags_dense_heatmap_rows():
    # The heatmap renderer sensibly caps drawn row labels, so exercise the
    # crowding check directly with a figure that actually carries many y ticks.
    fig, ax = plt.subplots()
    ax.imshow([[0, 1], [1, 0]] * 1)
    ax.set_yticks(range(80))
    ax.set_yticklabels([f"gene_{i}" for i in range(80)])
    ax.set_xlabel("x")
    ax.set_ylabel("genes")
    spec = {"plot_type": "heatmap_clustered_matrix"}
    score = score_publication(figure=fig, spec=spec)
    assert "heatmap_row_density" in _check_ids(score)
    plt.close(fig)


def test_good_figure_passes_or_warns_not_fail():
    info = _load("scatter_regression.csv")
    spec = make_spec("scatterplot_with_regression", "scatter_regression.csv", "publication")
    result = render(spec, info.dataframe)
    score = score_publication(result=result, spec=spec)
    assert score.level in ("pass", "warn")   # a clean default render must not FAIL
    assert 0 <= score.score <= 100
    plt.close(result.figure)


def test_autofix_increase_font_raises_tokens():
    spec = {"plot_type": "barplot_with_error_bar", "style": {"base_font_pt": 11, "axis_font_pt": 12}}
    out = apply_fixes(spec, ["increase_font"])
    assert out["style"]["base_font_pt"] > 11
    assert out["style"]["axis_font_pt"] > 12


def test_autofix_increase_dpi():
    spec = {"plot_type": "volcano_plot", "output": {"dpi": 72}}
    out = apply_fixes(spec, ["increase_dpi"])
    assert out["output"]["dpi"] >= 300


def test_apply_fixes_does_not_mutate_input():
    spec = {"plot_type": "barplot_with_error_bar", "style": {"base_font_pt": 11},
            "output": {"dpi": 72}, "layout": {}}
    import copy
    snapshot = copy.deepcopy(spec)
    _ = apply_fixes(spec, ["increase_font", "increase_dpi", "enlarge_figure", "legend_outside"])
    assert spec == snapshot   # input untouched


def test_suggest_fixes_maps_dpi_issue():
    spec = {"plot_type": "volcano_plot", "output": {"dpi": 72}}
    result_spec = make_spec("volcano_plot", "volcano_plot.csv", "publication")
    result_spec["output"]["dpi"] = 72
    info = _load("volcano_plot.csv")
    result = render(result_spec, info.dataframe)
    score = score_publication(result=result, spec=result_spec)
    fixes = suggest_fixes(score, result_spec)
    assert any(f["id"] == "increase_dpi" for f in fixes)
    plt.close(result.figure)
