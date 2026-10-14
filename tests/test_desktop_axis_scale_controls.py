"""Desktop: the axis scale / range controls act, persist, hide, and reset.

Drives the real MainWindow (offscreen). A control is visible only where the plot
can honour it, writes nothing when left alone, reaches the figure when set, comes
back from a saved spec, and is cleared when the plot type changes.
"""
import os

import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from apps.desktop_app.main import MainWindow
except Exception as exc:  # noqa: BLE001
    pytest.skip(f"PySide6/Qt unavailable: {exc}", allow_module_level=True)

from make_my_figure_core.plots.axis_scale import plotted_values  # noqa: E402
from make_my_figure_core.plots.registry import available_plot_types  # noqa: E402
from make_my_figure_core.styles.capabilities import axis_scale_support  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _win(pt):
    win = MainWindow()
    win.show()
    win.load_example(pt)
    win.plot_combo.setCurrentIndex(win.plot_combo.findData(pt))
    win.render_preview()
    QApplication.processEvents()
    return win


def _row_visible(win, widget):
    form = win._axis_scale_form
    try:
        return form.isRowVisible(widget) and win._axis_scale_group.isVisible()
    except AttributeError:  # pragma: no cover
        return widget.isVisible()


@pytest.mark.parametrize("pt", available_plot_types())
def test_controls_are_shown_exactly_where_the_plot_can_honour_them(app, pt):
    win = _win(pt)
    win._style_box.setChecked(True)
    QApplication.processEvents()
    for axis in "xy":
        ok = axis_scale_support(pt, axis)[0]
        assert _row_visible(win, win._axis_scale_widgets[axis]["scale"]) == ok, (pt, axis)
    win.close()


def test_untouched_controls_write_nothing(app):
    win = _win("boxplot_or_violin_with_points")
    win._style_box.setChecked(True)
    spec = win._build_spec()
    assert not {k for k in (spec.get("layout") or {}) if k.startswith(("y_scale", "y_tick_format", "y_min",
                                                                         "y_max", "y_minor"))}
    win.close()


def test_log10_axis_from_the_panel_changes_display_not_data(app):
    win = _win("boxplot_or_violin_with_points")
    before = np.sort(plotted_values(win._canvas.figure.axes[0], "y"))
    win._style_box.setChecked(True)
    w = win._axis_scale_widgets["y"]
    w["scale"].setCurrentIndex(w["scale"].findData("log10"))
    w["fmt"].setCurrentIndex(w["fmt"].findData("plain"))
    win.render_preview()
    ax = win._canvas.figure.axes[0]
    assert ax.get_yscale() == "log"
    np.testing.assert_array_equal(before, np.sort(plotted_values(ax, "y")))
    spec = win._build_spec()
    assert spec["layout"]["y_scale"] == "log10" and spec["layout"]["y_tick_format"] == "plain"

    # back to linear restores the original axis
    w["scale"].setCurrentIndex(0)
    w["fmt"].setCurrentIndex(0)
    win.render_preview()
    assert win._canvas.figure.axes[0].get_yscale() == "linear"
    assert "y_scale" not in (win._build_spec().get("layout") or {})
    win.close()


def test_axis_range_from_the_panel_and_its_refusal(app):
    win = _win("dot_strip_plot")
    vals = plotted_values(win._canvas.figure.axes[0], "y")
    win._style_box.setChecked(True)
    w = win._axis_scale_widgets["y"]
    w["lo"].setText(f"{vals.min() / 2:g}")
    w["hi"].setText(f"{vals.max() * 2:g}")
    win.render_preview()
    lo, hi = win._canvas.figure.axes[0].get_ylim()
    assert lo == pytest.approx(float(f"{vals.min() / 2:g}")) and hi == pytest.approx(float(f"{vals.max() * 2:g}"))
    w["lo"].setText(f"{vals.min() * 1.5:g}")
    win.render_preview()
    assert "would hide plotted values" in win.warn_label.text() or any(
        "would hide plotted values" in m for m in (getattr(win._current_result, "warnings", None) or []))
    win.close()


def test_saved_spec_restores_controls_hidden_settings_do_not_leak_and_new_plot_resets(app):
    win = _win("scatterplot_with_regression")
    win._style_box.setChecked(True)
    for axis in "xy":
        w = win._axis_scale_widgets[axis]
        w["scale"].setCurrentIndex(w["scale"].findData("log2"))
        w["minor"].setCurrentIndex(w["minor"].findData(False))
    win.render_preview()
    spec = win._build_spec()
    assert spec["layout"]["x_scale"] == "log2" and spec["layout"]["y_minor_ticks"] is False

    win2 = _win("scatterplot_with_regression")
    win2._apply_spec_to_controls(spec)
    QApplication.processEvents()
    for axis in "xy":
        assert win2._axis_scale_widgets[axis]["scale"].currentData() == "log2"
        assert win2._axis_scale_widgets[axis]["minor"].currentData() is False

    # a plot that cannot use a log axis neither shows nor receives the setting
    win2.plot_combo.setCurrentIndex(win2.plot_combo.findData("volcano_plot"))
    QTest.qWait(50)
    layout = win2._build_spec().get("layout") or {}
    assert not any(k in layout for k in ("x_scale", "y_scale", "x_minor_ticks", "y_minor_ticks"))
    assert not win2._axis_scale_group.isVisible()

    # a new plot starts clean (reset_plot_styling, as for every plot-local control)
    win2.reset_plot_styling()
    for axis in "xy":
        assert win2._axis_scale_widgets[axis]["scale"].currentIndex() == 0
        assert win2._axis_scale_widgets[axis]["minor"].currentIndex() == 0
        assert win2._axis_scale_widgets[axis]["lo"].text() == ""
    win.close()
    win2.close()


def test_a_spec_without_a_style_block_reopens_with_its_log_axis(app):
    # A browser-made spec or a package carries layout y_scale with no style block;
    # the desktop reopened it linear.
    win = _win("dot_strip_plot")
    spec = win._build_spec()
    spec["style"] = {}
    spec["layout"] = {"y_scale": "log10", "y_tick_format": "plain", "y_min": 1.0}
    win._apply_spec_to_controls(spec)
    QApplication.processEvents()
    assert win._axis_scale_widgets["y"]["scale"].currentData() == "log10"
    assert win._build_spec()["layout"]["y_scale"] == "log10"
    win.close()


def test_axis_limits_use_a_point_for_decimals_on_any_system_locale(app):
    from PySide6.QtGui import QValidator

    win = _win("dot_strip_plot")
    ed = win._axis_scale_widgets["y"]["lo"]
    v = ed.validator()
    assert v.validate("1.5", 0)[0] == QValidator.Acceptable
    assert v.validate("1,5", 0)[0] != QValidator.Acceptable     # was read as 15 under de_DE
    win._style_box.setChecked(True)
    ed.setText("1,5")
    assert "y_min" not in (win._build_spec().get("layout") or {})
    win.close()
