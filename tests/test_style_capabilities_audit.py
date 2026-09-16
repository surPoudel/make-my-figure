"""Every declared style capability must match what the renderer's source actually reads.

A control that is shown, moved, and changes nothing is a defect: the user cannot tell a no-op from
a subtle effect. ``styles/capabilities.py`` declares which controls apply per plot type so the GUIs
can grey out the rest with a reason - but a declaration only stays true if something compares it
with the code. The audit script does that comparison; this test runs it on every registered
renderer so the table cannot drift again.
"""

from __future__ import annotations

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import audit_style_capabilities as audit  # noqa: E402

from make_my_figure_core import examples as ex  # noqa: E402
from make_my_figure_core.plots.registry import available_plot_types, render  # noqa: E402
from make_my_figure_core.styles.capabilities import get_style_capabilities  # noqa: E402


def test_capabilities_agree_with_renderer_source_for_every_plot_type():
    rows = [audit.scan_renderer(pt) for pt in available_plot_types()]
    assert audit.drift(rows) == []


def test_every_registered_renderer_is_scanned():
    rows = [audit.scan_renderer(pt) for pt in available_plot_types()]
    assert {r["plot_type"] for r in rows} == set(available_plot_types())


def test_volcano_declares_the_palette_inapplicable_with_a_reason():
    caps = get_style_capabilities("volcano_plot")
    assert caps.supports_palette is False
    assert "significance" in caps.unsupported_controls_reason


def test_volcano_colour_options_reach_the_points():
    """The three class colours are real controls, not a palette that does nothing."""
    info, aux, spec = ex.load_example("volcano_plot")
    spec["mapping"].update({"color_up": "#1B7837", "color_down": "#762A83", "color_ns": "#333333"})
    res = render(spec, info.dataframe)
    try:
        drawn = set()
        for coll in res.figure.axes[0].collections:
            fc = coll.get_facecolor()
            if len(fc):
                r, g, b = (int(round(v * 255)) for v in fc[0][:3])
                drawn.add(f"#{r:02X}{g:02X}{b:02X}")
        assert {"#1B7837", "#762A83", "#333333"} <= drawn, drawn
    finally:
        plt.close(res.figure)


def test_volcano_default_colours_are_unchanged():
    info, aux, spec = ex.load_example("volcano_plot")
    res = render(spec, info.dataframe)
    try:
        drawn = set()
        for coll in res.figure.axes[0].collections:
            fc = coll.get_facecolor()
            if len(fc):
                r, g, b = (int(round(v * 255)) for v in fc[0][:3])
                drawn.add(f"#{r:02X}{g:02X}{b:02X}")
        assert {"#B2182B", "#2166AC", "#BBBBBB"} <= drawn
    finally:
        plt.close(res.figure)


def test_ma_plot_not_significant_colour_is_a_control():
    info, aux, spec = ex.load_example("ma_plot")
    spec["mapping"]["color_ns"] = "#1B7837"
    res = render(spec, info.dataframe)
    try:
        drawn = set()
        for coll in res.figure.axes[0].collections:
            fc = coll.get_facecolor()
            if len(fc):
                r, g, b = (int(round(v * 255)) for v in fc[0][:3])
                drawn.add(f"#{r:02X}{g:02X}{b:02X}")
        assert "#1B7837" in drawn
    finally:
        plt.close(res.figure)


def test_embedding_scatter_declares_its_colorbar():
    caps = get_style_capabilities("embedding_scatter")
    assert caps.supports_continuous_colormap and caps.supports_colorbar


@pytest.mark.parametrize("pt", ["stacked_bar_composition", "kaplan_meier_survival_curve", "forest_plot"])
def test_plots_without_markers_say_so(pt):
    assert get_style_capabilities(pt).supports_marker_size is False


def test_box_violin_marker_size_seeds_the_observation_markers():
    """The box/violin plot draws its observations through the shared helper, which scales the
    adaptive marker from ``style.marker_size`` - so the control applies and is declared to."""
    assert get_style_capabilities("boxplot_or_violin_with_points").supports_marker_size is True
    assert get_style_capabilities("boxplot_or_violin_with_points").supports_legend is True


def test_audit_csv_is_written(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "OUT_DIR", tmp_path)
    monkeypatch.setattr(audit, "CSV_PATH", tmp_path / "audit.csv")
    monkeypatch.setattr(sys, "argv", ["audit"])
    assert audit.main() == 0
    text = (tmp_path / "audit.csv").read_text(encoding="utf-8")
    assert "volcano_plot" in text and "color_model" in text
    assert text.count("\n") == len(available_plot_types()) + 1
