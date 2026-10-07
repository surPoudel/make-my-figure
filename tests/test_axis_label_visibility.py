"""Show/hide for tick labels and axis names, on every plot type at once.

Reported need: a heatmap whose 30 row names will not fit, and panels whose axes
are already named by the panel beside them. The controls live in the shared
layout block and are applied centrally, so there is one implementation rather
than forty-five - and the condition for acting is an explicit ``False``, so a
figure that has never touched them renders exactly as it did before.
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

from make_my_figure_core import examples
from make_my_figure_core.plots import registry

# One plot type per shape of axis: a matrix with text on both axes, a
# categorical bar chart, a numeric scatter, and a curve.
COVERED = ("heatmap_clustered_matrix", "barplot_with_error_bar",
           "scatterplot_with_regression", "kaplan_meier_survival_curve")

HIDE_ALL = {"show_x_tick_labels": False, "show_y_tick_labels": False,
            "show_x_label": False, "show_y_label": False}


def _render(plot_type, **layout):
    table, aux, spec = examples.load_example(plot_type)
    spec = {**spec, "layout": {**(spec.get("layout") or {}), **layout}}
    return registry.render(spec, table.dataframe,
                           aux={k: v.dataframe for k, v in (aux or {}).items()})


def _axis_state(figure):
    figure.canvas.draw()
    ax = figure.axes[0]
    return {
        "x_ticks": len([t for t in ax.get_xticklabels()
                        if t.get_visible() and t.get_text().strip()]),
        "y_ticks": len([t for t in ax.get_yticklabels()
                        if t.get_visible() and t.get_text().strip()]),
        "x_label": ax.get_xlabel(),
        "y_label": ax.get_ylabel(),
    }


@pytest.mark.parametrize("plot_type", COVERED)
def test_by_default_every_axis_keeps_everything_it_had(plot_type):
    """The controls are opt-in: absent means the renderer decides, as before."""
    state = _axis_state(_render(plot_type).figure)
    plt.close("all")
    assert state["x_ticks"] > 0 and state["y_ticks"] > 0
    assert state["x_label"] and state["y_label"]


@pytest.mark.parametrize("plot_type", COVERED)
def test_each_part_of_an_axis_can_be_turned_off(plot_type):
    state = _axis_state(_render(plot_type, **HIDE_ALL).figure)
    plt.close("all")
    assert state["x_ticks"] == 0, f"{plot_type}: x tick labels still drawn"
    assert state["y_ticks"] == 0, f"{plot_type}: y tick labels still drawn"
    assert state["x_label"] == "" and state["y_label"] == ""


@pytest.mark.parametrize("key,field", [("show_x_tick_labels", "x_ticks"),
                                       ("show_y_tick_labels", "y_ticks"),
                                       ("show_x_label", "x_label"),
                                       ("show_y_label", "y_label")])
def test_each_control_acts_alone(key, field):
    """Turning one off must not take the other three with it."""
    state = _axis_state(_render("heatmap_clustered_matrix", **{key: False}).figure)
    plt.close("all")
    off = state.pop(field)
    assert off == 0 or off == ""
    for name, value in state.items():
        assert value, f"{key} also removed {name}"


def test_true_is_not_an_override_of_the_renderer():
    """``True`` means "leave it alone", not "put it back".

    A heatmap drops row labels it has no room for, and a control that forced
    them back on would hand back the illegible figure that decision avoids.
    """
    table, aux, spec = examples.load_example("heatmap_clustered_matrix")
    spec = {**spec, "mapping": {**spec["mapping"], "show_row_labels": False},
            "layout": {**(spec.get("layout") or {}), "show_y_tick_labels": True}}
    result = registry.render(spec, table.dataframe,
                             aux={k: v.dataframe for k, v in (aux or {}).items()})
    state = _axis_state(result.figure)
    plt.close("all")
    assert state["y_ticks"] == 0


def test_the_setting_survives_a_plotspec_round_trip():
    import json

    table, aux, spec = examples.load_example("barplot_with_error_bar")
    spec = {**spec, "layout": {**(spec.get("layout") or {}), **HIDE_ALL}}
    reloaded = json.loads(json.dumps(spec))
    registry.validate_plot_spec(reloaded)
    state = _axis_state(registry.render(
        reloaded, table.dataframe,
        aux={k: v.dataframe for k, v in (aux or {}).items()}).figure)
    plt.close("all")
    assert state["x_ticks"] == 0 and state["y_ticks"] == 0
    assert state["x_label"] == "" and state["y_label"] == ""


# --------------------------------------------------------------------------
# the controls in the desktop app
# --------------------------------------------------------------------------

import os  # noqa: E402

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import PySide6.QtWidgets  # noqa: F401,E402
except ImportError as exc:  # pragma: no cover - environment-dependent
    PySide6 = None
    _QT_REASON = str(exc)
else:
    _QT_REASON = ""

qt_only = pytest.mark.skipif(bool(_QT_REASON),
                             reason=f"PySide6/Qt unavailable: {_QT_REASON}")

CHECKBOXES = (("chk_xticklabels", "show_x_tick_labels"),
              ("chk_yticklabels", "show_y_tick_labels"),
              ("chk_xlabel", "show_x_label"),
              ("chk_ylabel", "show_y_label"))


@pytest.fixture(scope="module")
def win():
    from PySide6.QtWidgets import QApplication

    from apps.desktop_app.main import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.load_example("heatmap_clustered_matrix")
    yield window
    window.close()
    del app


@qt_only
def test_the_boxes_start_checked_and_write_nothing(win):
    """A figure that has never touched these must be unchanged, so a checked box
    puts no key in the spec at all."""
    win._style_box.setChecked(True)
    for attr, _key in CHECKBOXES:
        getattr(win, attr).setChecked(True)
    layout, _cb = win._collect_layout_controls()
    assert not any(k.startswith("show_") for k in layout), layout


@qt_only
@pytest.mark.parametrize("attr,key", CHECKBOXES)
def test_unchecking_a_box_reaches_the_spec(win, attr, key):
    win._style_box.setChecked(True)
    for other, _ in CHECKBOXES:
        getattr(win, other).setChecked(True)
    getattr(win, attr).setChecked(False)
    layout, _cb = win._collect_layout_controls()
    assert layout.get(key) is False
    assert sum(1 for k in layout if k.startswith("show_")) == 1
    getattr(win, attr).setChecked(True)


@qt_only
def test_a_new_plot_starts_with_the_axes_shown_again(win):
    """The v1.2.1 defect class: a plot-local setting leaking into the next plot."""
    win._style_box.setChecked(True)
    for attr, _ in CHECKBOXES:
        getattr(win, attr).setChecked(False)
    win.reset_plot_styling()
    for attr, _ in CHECKBOXES:
        assert getattr(win, attr).isChecked(), attr
