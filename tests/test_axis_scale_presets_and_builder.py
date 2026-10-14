"""Axis scale / derived data across presets and the Figure Builder.

* A style preset carries how ticks are written, never the axis scale or range
  (those are choices about one dataset); a full preset carries both.
* A Figure Builder panel keeps the log axis and the derived values of the plot
  it was made from.
"""
import numpy as np
import pandas as pd

from apps.desktop_app.controller import DesktopController
from make_my_figure_core.panels import FigureLayout, MultiPanelFigure, Panel, build_figure
from make_my_figure_core.panels.builder import panel_frames
from make_my_figure_core.plots.axis_scale import plotted_values
from make_my_figure_core.presets import apply_preset, extract_preset
from make_my_figure_core.tabular import TableTransform

CTRL = DesktopController()
AXIS = {"y_scale": "log10", "y_tick_format": "plain", "y_minor_ticks": False, "y_min": 1.0, "y_max": 1e8}


def _wide():
    rng = np.random.default_rng(7)
    return pd.DataFrame({"treatment": np.repeat(["control", "low", "high"], 8),
                         "quantity": np.round(np.exp(rng.normal(np.log(1e6), 1.0, 24)))})


def _spec(table="t.csv", layout=None, y="quantity"):
    s = CTRL.build_spec("dot_strip_plot", "publication", table, {"x": "treatment", "y": y})
    s.setdefault("layout", {}).update(layout or {})
    return s


def test_style_preset_carries_tick_notation_but_not_scale_or_range():
    preset = extract_preset(_spec(layout=AXIS), mode="style")
    out = apply_preset(preset, _spec(table="other.csv"), columns=["treatment", "quantity"]).spec
    layout = out.get("layout") or {}
    assert layout.get("y_tick_format") == "plain" and layout.get("y_minor_ticks") is False
    for key in ("y_scale", "y_min", "y_max"):
        assert key not in layout, key


def test_full_preset_carries_scale_and_range():
    preset = extract_preset(_spec(layout=AXIS), mode="full")
    out = apply_preset(preset, _spec(table="other.csv"), columns=["treatment", "quantity"]).spec
    for key, value in AXIS.items():
        assert out["layout"][key] == value, key


def test_builder_panel_keeps_log_axis_and_derived_values():
    raw = CTRL.loaded_from_dataframe(_wide(), "wide.csv")
    derived = CTRL.derive_table(raw, [TableTransform("quantity", "log10")])
    panels = [
        ("A", _spec("wide.csv", {"y_scale": "log10", "y_tick_format": "plain"}), raw.info.dataframe),
        ("B", _spec("wide (derived)", y="log10(quantity)"), derived.info.dataframe),
    ]
    mpf = MultiPanelFigure(name="F", layout=FigureLayout(ncols=2, fig_width_mm=180.0, panel_dpi=72))
    standalone = {}
    for label, spec, df in panels:
        res = CTRL.render(spec, CTRL.loaded_from_dataframe(df, spec["input_table"]))
        standalone[label] = (res.figure.axes[0].get_yscale(), np.sort(plotted_values(res.figure.axes[0], "y")))
        mpf.add_panel(Panel(plot_spec=spec, table=df, label=label, width_in=3.2))
    fig = build_figure(mpf)
    frames = {f["label"]: f for f in panel_frames(fig)}
    assert set(frames) == {"A", "B"}
    # The Builder re-renders each panel from its PlotSpec at the panel size and
    # composes the pictures; check that rendering, as the Builder does it.
    from make_my_figure_core.panels.builder import _render_panel_figure

    for panel in mpf.panels:
        pfig = _render_panel_figure(panel, size_in=(panel.width_in, None))
        ax = pfig.axes[0]
        scale, values = standalone[panel.label]
        assert ax.get_yscale() == scale, panel.label
        np.testing.assert_allclose(np.sort(plotted_values(ax, "y")), values, rtol=1e-12)
    assert standalone["A"][0] == "log" and standalone["B"][0] == "linear"
    # The observations in panel B are log10 of exactly the observations panel A
    # draws on a log axis. The summary marks are NOT: A marks the arithmetic mean
    # of the raw values, B the mean of the logs (= log of the geometric mean).
    # That difference is the reason display scaling and transformation are kept
    # apart, and why the tutorial explains it.
    from matplotlib.collections import PathCollection

    pts = {}
    for label, spec, df in panels:
        res = CTRL.render(spec, CTRL.loaded_from_dataframe(df, spec["input_table"]))
        ax = res.figure.axes[0]
        pts[label] = np.sort(np.concatenate([c.get_offsets()[:, 1] for c in ax.collections
                                             if isinstance(c, PathCollection) and len(c.get_offsets())]))
    np.testing.assert_allclose(np.log10(pts["A"]), pts["B"], rtol=1e-12)
    raw = _wide()["quantity"]
    assert abs(np.log10(raw.mean()) - np.log10(raw).mean()) > 0.05   # arithmetic vs geometric mean
