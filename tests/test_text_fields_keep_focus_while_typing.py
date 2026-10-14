"""Regression: typing a title must not lose keyboard focus to the re-rendered figure.

Reported from v1.3.0 use: "when I try to put a title it deactivates the title box
immediately so I cannot type fully". Each keystroke schedules a live preview
(180 ms debounce), and the re-render took the keyboard away twice over:

1. ``_clear_figure`` detached the old toolbar and figure holder with
   ``setParent(None)``, which makes a visible widget a top-level window for an
   instant; Qt moved window focus to it and the main window lost activation.
2. ``_show_figure`` then called ``canvas.setFocus()`` on the new canvas.

Measured on v1.3.0 code: after the first pause, focus was on
``FigureCanvasQTAgg`` (or nothing) in 3 of 3 text fields.
"""
import os

import matplotlib
import pytest

matplotlib.use("Agg")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from apps.desktop_app.main import MainWindow
except Exception as exc:  # noqa: BLE001
    pytest.skip(f"PySide6/Qt unavailable: {exc}", allow_module_level=True)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _settle(win, ms=400):
    # Let the debounce timer fire and the render finish.
    QTest.qWait(ms)
    QApplication.processEvents()


def _activate(win):
    win.show()
    win.activateWindow()
    assert QTest.qWaitForWindowActive(win, 3000), "test window never became active"


def _focused_window(app, plot_type="barplot_with_error_bar"):
    win = MainWindow()
    _activate(win)
    win.load_example(plot_type)
    win.render_preview()
    _settle(win)
    return win


def test_a_live_re_render_keeps_the_main_window_active(app):
    win = _focused_window(app)
    for _ in range(3):
        win.render_preview()
        _settle(win, 250)
        assert QApplication.activeWindow() is win, f"active window became {QApplication.activeWindow()!r}"
        stray = [w for w in QApplication.topLevelWidgets() if w.isVisible() and w is not win]
        assert not stray, f"re-render left visible top-level widgets: {stray}"
    win.close()


@pytest.mark.parametrize("field", ["title_edit", "xlabel_edit", "ylabel_edit"])
def test_typing_with_pauses_keeps_focus_and_every_character(app, field):
    win = _focused_window(app)
    edit = getattr(win, field)
    edit.setFocus(Qt.OtherFocusReason)
    QApplication.processEvents()
    assert edit.hasFocus()
    renders_before = id(win._canvas)
    text = "Worker bees"
    for word in text.split(" "):
        QTest.keyClicks(edit, word)
        _settle(win)                        # a pause long enough for a live re-render
        assert QApplication.focusWidget() is edit, f"focus moved to {QApplication.focusWidget()!r}"
        if word != text.split(" ")[-1]:
            QTest.keyClicks(edit, " ")
    assert edit.text() == text
    assert id(win._canvas) != renders_before, "the preview did not re-render while typing"
    assert win._canvas.figure.axes[0].get_title() == text or field != "title_edit"
    win.close()


def test_clicking_the_canvas_still_gives_it_focus(app):
    # The canvas takes focus for its key/scroll interactions when the user puts it there.
    win = _focused_window(app)
    win._canvas.setFocus(Qt.MouseFocusReason)
    QApplication.processEvents()
    win.render_preview()
    _settle(win)
    assert QApplication.focusWidget() is win._canvas
    win.close()


from make_my_figure_core.plots.registry import available_plot_types  # noqa: E402

_CASES = [(pt, None) for pt in available_plot_types()] + [("boxplot_or_violin_with_points", "violin")]


@pytest.mark.parametrize("plot_type,kind", _CASES, ids=[f"{p}-{k}" if k else p for p, k in _CASES])
def test_title_typing_keeps_focus_on_every_plot_type(app, plot_type, kind):
    win = MainWindow()
    _activate(win)
    win.load_example(plot_type)
    if kind:
        combo = win._option_widgets["kind"]
        combo.setCurrentIndex(combo.findText(kind) if combo.findText(kind) >= 0 else combo.findData(kind))
    win.render_preview()
    _settle(win, 300)
    edit = win.title_edit
    edit.setFocus(Qt.OtherFocusReason)
    QApplication.processEvents()
    for chunk in ("Colony", " size"):
        QTest.keyClicks(edit, chunk)
        _settle(win, 300)
        assert QApplication.focusWidget() is edit, f"{plot_type}: focus moved to {QApplication.focusWidget()!r}"
    assert edit.text() == "Colony size"
    win.close()
