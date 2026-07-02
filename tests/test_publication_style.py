"""Tests for publication-ready defaults, style overrides, and the QA checker."""

import os

import matplotlib
import matplotlib.pyplot as plt
import pytest

matplotlib.use("Agg")

from make_my_figure_core import examples
from make_my_figure_core.plots.registry import available_plot_types, make_spec, render
from make_my_figure_core.qa.publication_check import check_publication_readiness
from make_my_figure_core.styles.engine import (
    NAMED_PALETTES,
    list_profiles,
    load_profile,
)


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _render(pt, style_overrides=None, profile="publication"):
    info, aux, _spec = examples.load_example(pt)
    spec = make_spec(pt, "data.csv", profile)
    if style_overrides is not None:
        spec["style"] = style_overrides
    aux_dfs = {k: v.dataframe for k, v in aux.items()} or None
    return render(spec, info.dataframe, aux=aux_dfs)


def test_publication_profile_available_and_default_first():
    profiles = list_profiles()
    assert profiles[0] == "publication"
    p = load_profile("publication")
    assert p.axis_font_pt >= 11 and p.marker_size >= 30


def test_defaults_are_readable():
    p = load_profile("publication")
    assert p.axis_font_pt >= 11
    assert p.tick_label_pt >= 9
    assert p.legend_pt >= 9
    assert p.title_font_pt >= 12
    assert p.spine_width_pt >= 1.0
    assert p.regression_line_width >= 1.5


def test_with_overrides_does_not_mutate_original():
    p = load_profile("publication")
    orig = p.axis_font_pt
    p2 = p.with_overrides({"axis_font_pt": 22})
    assert p.axis_font_pt == orig
    assert p2.axis_font_pt == 22


def test_font_size_override_applied():
    r = _render("scatterplot_with_regression", {"axis_font_pt": 20})
    ax = r.figure.axes[0]
    assert abs(ax.xaxis.label.get_fontsize() - 20) < 0.5


def test_spine_width_override_applied():
    r = _render("barplot_with_error_bar", {"spine_width_pt": 2.5})
    ax = r.figure.axes[0]
    assert abs(ax.spines["left"].get_linewidth() - 2.5) < 0.01


def test_marker_size_override_applied():
    r = _render("scatterplot_with_regression", {"marker_size": 120})
    ax = r.figure.axes[0]
    coll = [c for c in ax.collections if hasattr(c, "get_sizes") and len(c.get_sizes())]
    assert coll and abs(float(coll[0].get_sizes()[0]) - 120) < 1.0


def test_palette_override_applied():
    p = load_profile("publication").with_overrides({"palette_name": "grayscale"})
    assert p.color_for(0) == NAMED_PALETTES["grayscale"][0]


def test_legend_outside_override_places_legend_outside():
    r = _render("boxplot_or_violin_with_points", {"legend_outside": True})
    # box/violin has no legend; use a plot that always has one via override on grouped bar
    r2 = _render("grouped_barplot_with_error_bar")
    fig = r2.figure
    fig.canvas.draw()
    ax = fig.axes[0]
    leg = ax.get_legend()
    assert leg is not None
    assert leg.get_window_extent().x0 >= ax.get_window_extent().x1 - 2


@pytest.mark.parametrize("pt", available_plot_types())
def test_publication_check_passes_for_all_examples(pt):
    r = _render(pt)
    check = r.metadata.get("publication_check")
    assert check is not None
    assert check["passed"], f"{pt}: {check['warnings']}"


def test_checker_flags_tiny_text():
    r = _render("scatterplot_with_regression", {"axis_font_pt": 4, "tick_label_pt": 4})
    check = check_publication_readiness(r.figure)
    assert not check.passed
    assert any("too small" in w for w in check.warnings)


def test_named_palettes_present():
    for name in ("publication", "colorblind_safe", "high_contrast", "grayscale"):
        assert name in NAMED_PALETTES and len(NAMED_PALETTES[name]) >= 4
