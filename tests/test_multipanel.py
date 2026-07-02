"""Tests for the multi-panel figure builder."""

import json
import os

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.plots.registry import make_spec
from make_my_figure_core.panels import (
    FigureLayout,
    MultiPanelFigure,
    Panel,
    build_figure,
    draft_legend,
    export_multipanel,
    multipanel_sidecar,
)

RNG = np.random.default_rng(5)


def _panel_specs():
    bar = pd.DataFrame([{"c": c, "m": float(RNG.normal(v, 0.2))}
                        for c, v in [("x", 1), ("y", 2)] for _ in range(8)])
    sa = make_spec("barplot_with_error_bar", "a", "publication")
    sa["mapping"] = {"x": "c", "y": "m", "error": "sem"}
    sc = pd.DataFrame({"x": RNG.uniform(0, 10, 30)})
    sc["y"] = 1.2 * sc["x"] + RNG.normal(0, 2, 30)
    sb = make_spec("scatterplot_with_regression", "b", "publication")
    sb["mapping"] = {"x": "x", "y": "y", "fit_line": True}
    return [(sa, bar, "Bars"), (sb, sc, "Scatter")]


def _build_mpf(ncols=2):
    mpf = MultiPanelFigure(name="Figure 1", layout=FigureLayout(ncols=ncols, panel_dpi=100))
    for spec, df, title in _panel_specs():
        mpf.add_panel(Panel(plot_spec=spec, table=df, title=title))
    return mpf


def test_autolabel_sequences():
    mpf = _build_mpf()
    assert [p.label for p in mpf.panels] == ["A", "B"]


def test_build_and_export(tmp_path):
    mpf = _build_mpf()
    fig = build_figure(mpf)
    assert fig is not None
    files = export_multipanel(fig, str(tmp_path / "figure1"), ["png", "svg", "pdf"], dpi=120)
    assert len(files) == 3
    for f in files:
        assert os.path.exists(f) and os.path.getsize(f) > 200
    plt.close(fig)


def test_sidecar_has_panel_specs(tmp_path):
    mpf = _build_mpf()
    side = multipanel_sidecar(mpf, str(tmp_path / "figure1"))
    payload = json.load(open(side))
    assert payload["figure"]["name"] == "Figure 1"
    assert len(payload["figure"]["panels"]) == 2
    assert payload["figure"]["panels"][0]["plot_spec"] is not None
    assert "draft_legend" in payload


def test_panel_management():
    mpf = _build_mpf()
    mpf.duplicate_panel(0)
    assert len(mpf.panels) == 3
    assert [p.label for p in mpf.panels] == ["A", "B", "C"]
    mpf.move_panel(0, 2)
    mpf.remove_panel(0)
    assert len(mpf.panels) == 2


def test_draft_legend_marks_draft():
    mpf = _build_mpf()
    text = draft_legend(mpf)
    assert "DRAFT" in text
    assert "(A)" in text and "(B)" in text


def test_prerendered_figure_panel(tmp_path):
    from make_my_figure_core.plots.registry import render

    spec, df, _ = _panel_specs()[0]
    res = render(spec, df)
    mpf = MultiPanelFigure(name="Figure 2", layout=FigureLayout(ncols=1, panel_dpi=100))
    mpf.add_panel(Panel(figure=res.figure, title="Prerendered"))
    fig = build_figure(mpf)
    files = export_multipanel(fig, str(tmp_path / "f2"), ["png"], dpi=100)
    assert os.path.exists(files[0])
    plt.close(fig)
