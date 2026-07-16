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


def test_export_passes_dpi_to_all_formats(tmp_path):
    # Regression: the PDF/SVG panels used to embed at matplotlib's default 100 dpi
    # (blurry) because dpi was only passed for png/tiff. Every format must get it.
    mpf = _build_mpf()
    fig = build_figure(mpf)
    seen = {}
    orig = fig.savefig

    def spy(out, **kw):
        fmt = kw.get("format") or str(out).rsplit(".", 1)[-1]
        seen[fmt] = kw.get("dpi")
        return orig(out, **kw)

    fig.savefig = spy  # type: ignore[assignment]
    export_multipanel(fig, str(tmp_path / "fig"), ["png", "svg", "pdf"], dpi=300)
    assert seen.get("pdf") == 300 and seen.get("svg") == 300 and seen.get("png") == 300
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


def test_titles_off_by_default():
    """Per-panel titles must not be drawn by default (they collide with labels)."""
    assert FigureLayout().show_titles is False
    mpf = _build_mpf()
    fig = build_figure(mpf)
    assert all(ax.get_title() == "" for ax in fig.axes)
    # ...but the title stays available for the auto-drafted legend.
    assert "Bars" in draft_legend(mpf)
    plt.close(fig)


def test_per_panel_size_scales_figure():
    """A larger requested panel size yields a proportionally larger figure."""
    specs = _panel_specs()

    def _fig(w, h):
        mpf = MultiPanelFigure(name="F", layout=FigureLayout(ncols=2, panel_dpi=100))
        for spec, df, title in specs:
            mpf.add_panel(Panel(plot_spec=spec, table=df, title=title, width_in=w, height_in=h))
        f = build_figure(mpf)
        size = f.get_size_inches().copy()
        plt.close(f)
        return size

    small = _fig(3.0, 3.0)
    wide = _fig(5.0, 3.0)
    tall = _fig(3.0, 6.0)
    assert wide[0] > small[0] + 1.0      # wider request -> wider figure
    assert tall[1] > small[1] + 1.0      # taller request -> taller figure


def test_auto_height_follows_aspect_no_distortion():
    """With height on auto, each panel cell matches its own aspect (no stretch)."""
    spec, df, _ = _panel_specs()[0]
    mpf = MultiPanelFigure(name="F", layout=FigureLayout(ncols=1, panel_dpi=100))
    mpf.add_panel(Panel(plot_spec=spec, table=df, width_in=4.0))  # height auto
    fig = build_figure(mpf)
    ax = fig.axes[0]
    # imshow keeps square pixels (aspect != "auto"), so the drawn aspect is 'equal'.
    assert ax.get_aspect() in (1.0, "equal")
    plt.close(fig)


def test_font_overrides_reach_panel_render():
    from make_my_figure_core.panels.builder import _render_panel_figure

    spec, df, title = _panel_specs()[0]
    panel = Panel(plot_spec=spec, table=df, title=title)
    fig = _render_panel_figure(panel, {"axis_font_pt": 22.0})
    # The x/y axis label should pick up the override.
    label_sizes = [fig.axes[0].xaxis.label.get_size(), fig.axes[0].yaxis.label.get_size()]
    assert max(label_sizes) >= 20.0
    plt.close(fig)


def test_layout_font_overrides_dict():
    lay = FigureLayout(axis_font_pt=14.0, legend_pt=9.0)
    ov = lay.font_overrides()
    assert ov == {"axis_font_pt": 14.0, "legend_pt": 9.0}
    assert FigureLayout().font_overrides() == {}


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
