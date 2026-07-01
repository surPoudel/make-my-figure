"""GUI smoke tests for the desktop app, run on Qt's offscreen platform.

These build the real MainWindow (no visible window), drive a couple of code
paths (load example, switch plot type, render preview, export), and assert no
exception. Skipped automatically if PySide6 is unavailable.
"""

import os
import sys

import matplotlib
import pytest

matplotlib.use("Agg")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QSplitter  # noqa: E402

from apps.desktop_app.main import MainWindow  # noqa: E402
from make_my_figure_core.plots.registry import available_plot_types  # noqa: E402


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    yield a


def test_window_starts_on_welcome(app):
    win = MainWindow()
    assert win.stack.currentIndex() == 0  # welcome page
    win.close()


def test_load_example_and_render(app):
    win = MainWindow()
    win.load_example("barplot_with_error_bar")
    assert win.stack.currentIndex() == 1       # moved to workbench
    assert win.data is not None
    assert win._current_result is not None      # a figure was rendered
    assert win._canvas is not None
    win.close()


def test_switch_plot_types_renders(app):
    win = MainWindow()
    # load an example then switch through several plot types
    for pt in ["scatterplot_with_regression", "volcano_plot",
               "kaplan_meier_survival_curve", "pca_scatter_from_matrix"]:
        win.load_example(pt)
        assert win._current_result is not None, f"no figure for {pt}"
    win.close()


def _select_plot_type(win, plot_type):
    idx = win.plot_combo.findData(plot_type)
    assert idx >= 0
    win.plot_combo.setCurrentIndex(idx)   # triggers _on_plot_type_changed


def test_switch_scatter_to_volcano_autoloads(app):
    win = MainWindow()
    win.load_example("scatterplot_with_regression")
    assert "x_marker" in win.data.info.columns
    # Switch plot type -> incompatible example data should auto-load volcano example.
    _select_plot_type(win, "volcano_plot")
    assert win.plot_combo.currentData() == "volcano_plot"
    assert "log2_fold_change" in win.data.info.columns   # new dataset loaded
    assert win._current_result is not None
    assert win._current_result.metadata["plot_type"] == "volcano_plot"
    assert win._canvas is not None                        # a fresh figure is shown
    win.close()


def test_stale_figure_cleared_on_incompatible_user_data(app):
    win = MainWindow()
    win.load_example("scatterplot_with_regression")
    assert win._canvas is not None
    # Pretend this is user-uploaded data (not an example): incompatible switch
    # must clear the stale figure and offer the example, not keep the old plot.
    win.data.is_example = False
    _select_plot_type(win, "volcano_plot")
    assert win._canvas is None                 # stale scatter figure cleared
    assert win._current_result is None
    # offered to load example (isHidden reflects the flag without a shown window)
    assert not win.example_prompt_btn.isHidden()
    # And clicking the offer loads the volcano example and renders it.
    win._load_example_for_current_type()
    assert win._current_result is not None
    assert win._current_result.metadata["plot_type"] == "volcano_plot"
    assert win._canvas is not None
    win.close()


def test_column_mappings_reset_on_plot_type_change(app):
    win = MainWindow()
    win.load_example("scatterplot_with_regression")
    assert set(win._mapping_widgets) == set(win.controller.column_fields("scatterplot_with_regression"))
    _select_plot_type(win, "volcano_plot")
    # mapping dropdowns rebuilt for the new plot type
    assert set(win._mapping_widgets) == set(win.controller.column_fields("volcano_plot"))
    win.close()


def test_every_plot_type_loads_and_renders_in_gui(app):
    win = MainWindow()
    for pt in available_plot_types():
        win.load_example(pt)
        assert win._current_result is not None, f"no figure for {pt}"
        assert win._current_result.metadata["plot_type"] == pt
        assert win._canvas is not None
    win.close()


def test_layout_has_resizable_splitters(app):
    win = MainWindow()
    assert isinstance(win.main_splitter, QSplitter)
    assert isinstance(win.right_splitter, QSplitter)
    assert win.main_splitter.orientation() == Qt.Horizontal   # controls | preview
    assert win.right_splitter.orientation() == Qt.Vertical     # data/msgs — figure
    assert win.main_splitter.count() == 2
    assert win.right_splitter.count() == 2
    win.close()


def test_splitter_state_save_and_restore(app):
    win = MainWindow()
    state = win.right_splitter.saveState()
    assert win.right_splitter.restoreState(state) is True
    win._save_splitter_state()
    assert win.settings.value("right_splitter_state") is not None
    assert win.settings.value("main_splitter_state") is not None
    # A fresh window restores persisted layout without error.
    win2 = MainWindow()
    win2._restore_splitter_state()
    win.close()
    win2.close()


def test_toolbar_tracks_active_canvas_and_no_stale_refs(app):
    win = MainWindow()
    win.load_example("barplot_with_error_bar")
    assert win._canvas is not None and win._toolbar is not None
    # Toolbar is a real Qt matplotlib toolbar bound to the CURRENT canvas.
    assert win._toolbar.canvas is win._canvas
    assert win._canvas.figure is win._current_result.figure
    old_canvas = win._canvas
    _select_plot_type(win, "volcano_plot")   # example switch -> new figure
    assert win._canvas is not old_canvas       # stale canvas replaced
    assert win._toolbar.canvas is win._canvas  # toolbar drives the new canvas
    win.close()


def test_toolbar_navigation_actions_callable(app):
    win = MainWindow()
    win.load_example("scatterplot_with_regression")
    tb = win._toolbar
    # The standard NavigationToolbar2QT actions must be present and callable
    # against the live canvas (Home/Back/Forward/Pan/Zoom/Save wiring).
    for name in ("home", "back", "forward", "pan", "zoom"):
        assert hasattr(tb, name)
    tb.home()
    tb.back()
    tb.forward()
    tb.pan()   # enter pan mode
    tb.pan()   # leave pan mode
    tb.zoom()  # enter zoom mode
    tb.zoom()  # leave zoom mode
    assert win._canvas is not None
    win.close()


def test_key_plot_types_render_live_canvas(app):
    win = MainWindow()
    for pt in ["scatterplot_with_regression", "volcano_plot",
               "heatmap_clustered_matrix", "barplot_with_error_bar"]:
        win.load_example(pt)
        assert win._canvas is not None
        assert win._toolbar.canvas is win._canvas          # live, connected canvas
        assert win._current_result.metadata["plot_type"] == pt
    win.close()


def test_export_paths(app, tmp_path, monkeypatch):
    win = MainWindow()
    win.load_example("forest_plot")
    # Export ZIP without a dialog by stubbing the save dialog.
    from PySide6.QtWidgets import QFileDialog

    dest = str(tmp_path / "bundle.zip")
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (dest, "ZIP (*.zip)")))
    win.export_zip()
    assert os.path.exists(dest) and os.path.getsize(dest) > 300
    win.close()
