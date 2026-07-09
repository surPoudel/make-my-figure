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

from PySide6.QtCore import Qt, QPoint  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QSplitter  # noqa: E402

from apps.desktop_app.main import MainWindow, debug_info  # noqa: E402
from make_my_figure_core.plots.registry import available_plot_types  # noqa: E402


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    yield a


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    import matplotlib.pyplot as plt
    plt.close("all")


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


def test_debug_info_fields():
    di = debug_info()
    for key in ("app_version", "git_commit", "desktop_app_file", "core_package_path",
                "current_working_dir", "python_executable", "cloud_synced_folder"):
        assert key in di
    assert di["desktop_app_file"].endswith("main.py")


def test_diagnose_reports_wired_canvas(app):
    win = MainWindow()
    win.load_example("barplot_with_error_bar")
    d = win.diagnose()
    assert all(d.values()), f"diagnostic failed: {d}"
    assert d["toolbar_bound_to_current_canvas"]
    assert d["canvas_has_result_figure"]
    win.close()


def test_object_names_present(app):
    win = MainWindow()
    win.load_example("scatterplot_with_regression")
    tree = win.widget_tree()
    for name in ("mainSplitter", "rightSplitter", "figurePanel",
                 "figureCanvas", "figureToolbar", "messagePanel"):
        assert name in tree, f"missing object name in widget tree: {name}"
    win.close()


def test_toolbar_zoom_with_real_mouse_events(app):
    """Definitive interactivity check: real Qt mouse drag must box-zoom the axes."""
    win = MainWindow()
    win.resize(1000, 720)
    win.show()
    QApplication.processEvents()
    win.load_example("barplot_with_error_bar")
    QApplication.processEvents()
    canvas = win._canvas
    ax = canvas.figure.axes[0]
    x0 = ax.get_xlim()
    win._toolbar.zoom()
    cw, ch = canvas.width(), canvas.height()
    QTest.mousePress(canvas, Qt.LeftButton, Qt.NoModifier, QPoint(int(cw * 0.35), int(ch * 0.55)))
    QApplication.processEvents()
    QTest.mouseMove(canvas, QPoint(int(cw * 0.65), int(ch * 0.25)))
    QApplication.processEvents()
    QTest.mouseRelease(canvas, Qt.LeftButton, Qt.NoModifier, QPoint(int(cw * 0.65), int(ch * 0.25)))
    QApplication.processEvents()
    x1 = ax.get_xlim()
    assert (abs(x1[0] - x0[0]) > 1e-6) or (abs(x1[1] - x0[1]) > 1e-6), \
        "toolbar zoom did not change the axes view via real mouse events"
    win.close()


def test_view_menu_layout_actions(app):
    win = MainWindow()
    win.load_example("volcano_plot")
    # Maximize figure panel shrinks the top tabs pane.
    win.action_maximize_figure()
    assert win.right_splitter.sizes()[0] <= win.right_tabs.minimumHeight() + 1
    # Toggle data preview hides/shows the top tabs.
    win.a_show_data.setChecked(False)
    assert not win.right_tabs.isVisibleTo(win.right_splitter) or win.right_tabs.isHidden()
    win.a_show_data.setChecked(True)
    # Reset layout restores two visible panes.
    win.action_reset_layout()
    assert win.right_splitter.sizes()[0] > 0 and win.right_splitter.sizes()[1] > 0
    win.close()


def test_splitters_non_collapsible_and_grabbable(app):
    win = MainWindow()
    assert win.main_splitter.handleWidth() >= 8
    assert win.right_splitter.handleWidth() >= 8
    assert win.right_splitter.childrenCollapsible() is False
    win.close()


def test_toolbar_selftest_passes(app):
    """The in-app live self-test must confirm Home/Pan/Zoom/Save are functional."""
    win = MainWindow()
    win.load_example("lollipop_mutation_plot")
    res = win.run_toolbar_selftest()
    assert res.get("home_resets_view") is True or res.get("home_resets_view") == True  # noqa: E712
    assert res.get("pan_mode_wired") is True
    assert res.get("zoom_mode_wired") is True
    assert res.get("save_writes_file") is True
    win.close()


def test_home_view_seeded_after_render(app):
    win = MainWindow()
    win.load_example("barplot_with_error_bar")
    state = win.diagnose_toolbar_state()
    assert state["nav_history_len"] and state["nav_history_len"] >= 1
    assert state["toolbar_canvas_matches"] is True
    assert all(a["enabled"] in (True, False) for a in state["actions"])
    # Home / Pan / Zoom / Save actions all present.
    names = {a["name"] for a in state["actions"]}
    assert {"Home", "Pan", "Zoom", "Save"} <= names
    win.close()


def test_toolbar_stays_connected_across_plot_switches(app):
    win = MainWindow()
    for pt in ["lollipop_mutation_plot", "scatterplot_with_regression",
               "volcano_plot", "heatmap_clustered_matrix", "barplot_with_error_bar",
               "lollipop_mutation_plot"]:
        win.load_example(pt)
        assert win._toolbar.canvas is win._canvas, f"toolbar detached for {pt}"
        assert win._canvas.figure is win._current_result.figure
        assert win.run_toolbar_selftest().get("save_writes_file") is True
    win.close()


def test_validation_failure_clears_figure_toolbar_recovers(app):
    win = MainWindow()
    win.load_example("scatterplot_with_regression")
    win.data.is_example = False           # treat as user upload
    _select_plot_type(win, "volcano_plot")  # incompatible -> clears figure
    assert win._canvas is None and win._current_result is None
    # Recover by loading the matching example; toolbar reconnects and works.
    win._load_example_for_current_type()
    assert win._toolbar.canvas is win._canvas
    assert win.run_toolbar_selftest().get("home_resets_view") is True
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


# --- app navigation / upload reset (Part 1) --------------------------------

def test_home_upload_returns_to_welcome_and_clears(app):
    win = MainWindow()
    win.load_example("barplot_with_error_bar")
    assert win.stack.currentIndex() == 1 and win.data is not None
    win.reset_to_upload()
    assert win.stack.currentIndex() == 0          # back on welcome/upload
    assert win.data is None                        # dataset cleared
    assert win._current_spec is None               # plot spec cleared
    assert win._current_result is None             # figure preview cleared
    win.close()


def test_swap_dataset_in_one_session(app):
    win = MainWindow()
    win.load_example("barplot_with_error_bar")
    first_cols = set(win.data.info.columns)
    # return to upload, then load a structurally different dataset
    win.reset_to_upload()
    win.load_example("kaplan_meier_survival_curve")
    second_cols = set(win.data.info.columns)
    assert second_cols != first_cols               # new data replaced old
    assert win.stack.currentIndex() == 1
    assert win._current_result is not None          # fresh figure rendered
    win.close()


def test_reset_clears_statistics(app):
    win = MainWindow()
    win.load_example("boxplot_or_violin_with_points")
    win.stats_panel.setChecked(True)
    win.stats_panel.enable_cb.setChecked(True)
    idx = [i for i in range(win.stats_panel.test_combo.count())
           if win.stats_panel.test_combo.itemData(i) == "welch_t"][0]
    win.stats_panel.test_combo.setCurrentIndex(idx)
    win.render_preview()
    assert win.stats_panel.table.rowCount() >= 1
    win.reset_to_upload()
    assert win.stats_panel.table.rowCount() == 0   # stats results cleared
    assert not win.stats_panel.enable_cb.isChecked()
    win.close()


def test_matplotlib_toolbar_home_still_present(app):
    # The app-level Home button is separate from the Matplotlib toolbar 'home'
    # (which resets zoom/pan). Both must exist independently.
    win = MainWindow()
    win.load_example("scatterplot_with_regression")
    assert hasattr(win, "home_btn")                # app-level upload button
    assert win._toolbar is not None                # matplotlib nav toolbar
    assert hasattr(win._toolbar, "home")           # toolbar's axes-home action
    win._toolbar.home()                            # should not raise
    win.close()


# --- flexible annotation panel + RNA-seq dialog (Parts 2 & 4) --------------

def test_statistics_panel_annotation_content_modes(app):
    from apps.desktop_app.stats_panel import StatisticsPanel
    from apps.desktop_app.controller import DesktopController
    sp = StatisticsPanel(DesktopController())
    sp.setChecked(True); sp.enable_cb.setChecked(True)
    # pick "custom template" -> template field becomes visible
    idx = [i for i in range(sp.annotation_combo.count())
           if sp.annotation_combo.itemData(i) == "custom"][0]
    sp.annotation_combo.setCurrentIndex(idx)
    # isHidden() reflects explicit visibility intent (offscreen widgets report
    # isVisible()==False without a shown ancestor).
    assert not sp.template_edit.isHidden()
    sp.template_edit.setText("{effect_symbol} = {effect}, p = {p}")
    spec = sp.stats_spec()
    assert spec["annotation"]["content"] == "custom"
    assert spec["annotation"]["template"] == "{effect_symbol} = {effect}, p = {p}"


def test_rnaseq_dialog_de_volcano(app, tmp_path):
    import os
    from apps.desktop_app.rnaseq_panel import RnaSeqDialog
    from apps.desktop_app.controller import DesktopController
    de_file = os.path.join(os.path.dirname(__file__), "..", "test_matrix",
                           "Ctrl_vs_Treatment_DE.txt")
    if not os.path.exists(de_file):
        import pytest
        pytest.skip("DE example missing")
    dlg = RnaSeqDialog(DesktopController())
    dlg.info = __import__("make_my_figure_core.rnaseq", fromlist=["load_rnaseq_table"]) \
        .load_rnaseq_table(de_file)
    dlg._source_path = de_file
    dlg.detection = __import__("make_my_figure_core.rnaseq", fromlist=["detect_input_mode"]) \
        .detect_input_mode(dlg.info)
    dlg.de_use_adj.setChecked(False)   # raw-p so there are hits
    dlg._generate_volcano()
    assert dlg._result is not None
    assert dlg._de.n_up + dlg._de.n_down >= 1
    assert dlg._rnaseq_spec is not None and dlg._rnaseq_spec.input_mode == "de_result"
    dlg.close()


def test_rnaseq_dialog_heatmap(app):
    import os
    from apps.desktop_app.rnaseq_panel import RnaSeqDialog
    from apps.desktop_app.controller import DesktopController
    import make_my_figure_core.rnaseq as rna
    voom = os.path.join(os.path.dirname(__file__), "..", "test_matrix", "voom_norm_annot.txt")
    if not os.path.exists(voom):
        import pytest
        pytest.skip("voom example missing")
    dlg = RnaSeqDialog(DesktopController())
    dlg.info = rna.load_rnaseq_table(voom)
    dlg._source_path = voom
    idx = dlg.mode_combo.findData("expression_matrix")
    dlg.mode_combo.setCurrentIndex(idx)
    dlg.hm_ngenes.setValue(30)
    dlg._generate_heatmap()
    assert dlg._result is not None
    assert dlg._rnaseq_spec.input_mode == "expression_matrix"
    dlg.close()


def test_rnaseq_dialog_rawcounts_run_disabled_without_r(app):
    from apps.desktop_app.rnaseq_panel import RnaSeqDialog
    from apps.desktop_app.controller import DesktopController
    from make_my_figure_core.rnaseq import check_r_environment
    dlg = RnaSeqDialog(DesktopController())
    idx = dlg.mode_combo.findData("raw_counts")
    dlg.mode_combo.setCurrentIndex(idx)
    # Run DE button reflects R availability
    assert dlg.run_de_btn.isEnabled() == check_r_environment().ready
    dlg.close()
