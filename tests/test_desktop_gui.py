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

# Importing the top-level package is not enough: PySide6 installs cleanly while its Qt
# libraries stay unloadable (no libxkbcommon on a bare WSL/container image). That surfaces as
# a plain ImportError from the dynamic loader, which importorskip does not treat as "missing"
# - it only skips ModuleNotFoundError - so collection aborted the entire run and the
# documented "-k not gui" escape could not help, because -k filters after collection.
try:
    import PySide6.QtWidgets  # noqa: F401
except ImportError as exc:  # pragma: no cover - environment-dependent
    pytest.skip(f"PySide6/Qt unavailable: {exc}", allow_module_level=True)

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


# --- editable data table -> live figure update (Part: simplify) ------------

def test_editable_table_updates_dataframe_and_rerenders(app):
    import pandas as pd
    win = MainWindow()
    win.load_example("barplot_with_error_bar")
    df = win.data.info.dataframe
    ycol = next(c for c in df.columns if c in win.data.info.numeric_columns)
    cidx = list(df.columns).index(ycol)
    before = win._current_result
    # simulate a user editing a cell in the preview table
    win.table_widget.item(0, cidx).setText("123.5")
    assert float(win.data.info.dataframe.iat[0, cidx]) == 123.5   # written back
    assert win._current_result is not None
    assert win._current_result is not before                       # re-rendered
    win.close()


def test_editable_table_nonnumeric_becomes_nan(app):
    import pandas as pd
    win = MainWindow()
    win.load_example("boxplot_or_violin_with_points")
    df = win.data.info.dataframe
    ycol = next(c for c in df.columns if c in win.data.info.numeric_columns)
    cidx = list(df.columns).index(ycol)
    win.table_widget.item(0, cidx).setText("not_a_number")
    assert pd.isna(win.data.info.dataframe.iat[0, cidx])           # coerced to NaN
    win.close()


def test_volcano_column_prefill_edger_and_deseq2(app):
    import pandas as pd
    from apps.desktop_app.controller import LoadedData

    def _loaded(df, numeric, cat):
        class _I:
            dataframe = df
            numeric_columns = numeric
            categorical_columns = cat
            warnings = []
            n_rows = len(df)
            @property
            def columns(self_):
                return list(df.columns)
        return LoadedData(info=_I(), table_name="de")

    win = MainWindow()
    # edgeR-style headers
    edger = pd.DataFrame({"geneSymbol": ["A", "B"], "logFC": [2.0, -1.0], "AveExpr": [5, 6],
                          "t": [3, -2], "P.Value": [1e-4, 2e-3], "adj.P.Val": [1e-3, 1e-2]})
    win.data = _loaded(edger, ["logFC", "AveExpr", "t", "P.Value", "adj.P.Val"], ["geneSymbol"])
    win._suppress_change = True
    win.plot_combo.setCurrentIndex(win.plot_combo.findData("volcano_plot"))
    win._suppress_change = False
    win._rebuild_mapping_and_options()
    sel = {k: v.currentText() for k, v in win._mapping_widgets.items()}
    assert sel["x"] == "logFC" and sel["p"] == "P.Value" and sel["label"] == "geneSymbol"

    # DESeq2-style headers
    deseq = pd.DataFrame({"gene_name": ["A", "B"], "log2FoldChange": [2.0, -1.0],
                          "baseMean": [100, 200], "stat": [4, -3], "pvalue": [1e-5, 1e-2],
                          "padj": [1e-4, 1e-1]})
    win.data = _loaded(deseq, ["log2FoldChange", "baseMean", "stat", "pvalue", "padj"], ["gene_name"])
    win._rebuild_mapping_and_options()
    sel = {k: v.currentText() for k, v in win._mapping_widgets.items()}
    assert sel["x"] == "log2FoldChange" and sel["p"] == "pvalue" and sel["label"] == "gene_name"
    win.close()


def test_define_groups_matrix_to_long(app):
    import pandas as pd
    from apps.desktop_app.grouping_panel import GroupingDialog

    import numpy as np
    win = MainWindow()
    # A realistic small intensity matrix: with only three rows every column has <= 3 distinct
    # values and is (correctly) classified as a categorical annotation column rather than a
    # sample, so no groups are guessed and Accept shows a modal warning instead of grouping.
    rng = np.random.default_rng(7)
    matrix = pd.DataFrame({"gene": [f"G{i}" for i in range(12)]})
    for col in ("Ctrl_1", "Ctrl_2", "Trt_1", "Trt_2"):
        matrix[col] = np.round(rng.lognormal(3.0, 0.5, 12), 2)
    win.data = win.controller.loaded_from_dataframe(matrix, "matrix.csv")
    dlg = GroupingDialog(win.controller, win.data)
    # feature id auto-defaults to the text column; the group column starts blank and is
    # filled by the "Guess groups" button (sample-name tokens), never silently.
    assert dlg.feature_combo.currentText() == "gene"
    assert dlg.sample_table.rowCount() == 4
    assert all(dlg.sample_table.item(r, 1).text() == "" for r in range(4))
    dlg._auto_guess_groups()
    groups = {dlg.sample_table.item(r, 0).text(): dlg.sample_table.item(r, 1).text()
              for r in range(4)}
    assert all(groups.values()), groups   # every sample was assigned a guessed group
    assert groups["Ctrl_1"] == groups["Ctrl_2"] and groups["Trt_1"] == groups["Trt_2"]
    assert groups["Ctrl_1"] != groups["Trt_1"]

    captured = {}
    dlg.grouped.connect(lambda loaded: captured.setdefault("loaded", loaded))
    dlg._on_accept()
    loaded = captured["loaded"]
    assert set(loaded.info.dataframe.columns) == {"feature", "sample", "group", "value"}
    # the main window adopts it and re-renders
    win._adopt_grouped_data(loaded)
    assert win.data is loaded
    win.close()


def test_define_groups_by_column_values(app):
    import pandas as pd
    from apps.desktop_app.grouping_panel import GroupingDialog

    win = MainWindow()
    df = pd.DataFrame({"sample": ["s1", "s2", "s3"], "cond": ["wt", "wt", "ko"], "v": [1.0, 2, 3]})
    win.data = win.controller.loaded_from_dataframe(df, "obs.csv")
    dlg = GroupingDialog(win.controller, win.data)
    dlg.tabs.setCurrentIndex(1)
    dlg.source_combo.setCurrentText("cond")
    dlg._refresh_column_tab()
    # relabel the two unique values
    for r in range(dlg.value_table.rowCount()):
        val = dlg.value_table.item(r, 0).text()
        dlg.value_table.item(r, 1).setText("Control" if val == "wt" else "Knockout")
    captured = {}
    dlg.grouped.connect(lambda loaded: captured.setdefault("loaded", loaded))
    dlg._on_accept()
    out = captured["loaded"].info.dataframe
    assert list(out["group"]) == ["Control", "Control", "Knockout"]
    win.close()


def test_recommendations_panel_populates_and_generates(app):
    win = MainWindow()
    win.load_example("volcano_plot")
    # recommendations computed on load
    assert hasattr(win, "recommend_panel")
    rec_spec = win.controller.recommend_for_loaded(win.data)
    assert rec_spec.recommendations, "expected at least one recommendation"
    top = rec_spec.recommendations[0]
    assert top.plot_type in {win.plot_combo.itemData(i) for i in range(win.plot_combo.count())}
    # generating applies the plot type + renders
    before = win._current_result
    win._on_generate_recommendation(top)
    assert win.plot_combo.currentData() == top.plot_type
    assert win._current_result is not None and win._current_result is not before
    win.close()


def test_publication_qc_runs_and_scores(app):
    win = MainWindow()
    win.load_example("barplot_with_error_bar")
    assert win._current_result is not None
    score = win.controller.publication_qc(win._current_result, win._current_spec)
    assert score.level in {"pass", "warn", "fail"}
    assert 0 <= score.score <= 100
    # auto-fix path returns a valid, different spec dict without raising
    fixes = win.controller.qc_suggested_fixes(score, win._current_spec)
    new_spec = win.controller.apply_qc_fixes(win._current_spec, [f["id"] for f in fixes])
    assert isinstance(new_spec, dict)
    win.close()


def test_add_recommendation_to_figure_builder(app):
    win = MainWindow()
    win.load_example("scatterplot_with_regression")
    rec_spec = win.controller.recommend_for_loaded(win.data)
    gen = [r for r in rec_spec.recommendations if r.plot_spec_draft]
    assert gen, "expected a generatable recommendation"
    n_before = len(win._saved_panels)
    win._on_add_recommendation_to_builder(gen[0])
    assert len(win._saved_panels) == n_before + 1
    win.close()


def test_open_plotspec_reproduces_benchmark_panel(app):
    """Open PlotSpec: load a saved plotspec.json + resolve its data + render exactly."""
    import os
    win = MainWindow()
    base = os.path.join(_REPO_ROOT, "benchmarks", "ten_publication_recreation",
                        "publications", "gorman2014_penguins", "recreated_panels", "panel_A")
    spec_path = os.path.join(base, "plotspec.json")
    if not os.path.exists(spec_path):
        import pytest
        pytest.skip("benchmark panel not present")
    spec, data_path = win.controller.load_plotspec(spec_path)
    # The panel's plot type is whatever the benchmark recorded (it was re-verified against the
    # paper in the benchmark history); the test checks the round trip, not a fixed plot type.
    assert spec["plot_type"] in [t for t, _ in win.controller.plot_types()]
    assert data_path and data_path.endswith("processed_data.csv")   # auto-resolved
    win.data = win.controller.load_file(data_path)
    win.stack.setCurrentIndex(1)
    win._populate_table()
    win._apply_plotspec_to_ui(spec)
    # controls reflect the spec
    assert win.plot_combo.currentData() == spec["plot_type"]
    for role, column in spec["mapping"].items():
        if role in win._mapping_widgets and isinstance(column, str):
            assert win._mapping_widgets[role].currentText() == column, role
    # and it renders exactly from the loaded spec
    result = win.controller.render(spec, win.data)
    assert result.figure is not None
    win.close()


def test_open_plotspec_restores_statistics(app):
    """Opening a PlotSpec that carries statistics repopulates the Stats panel so
    the annotations survive a later control edit."""
    win = MainWindow()
    win.load_example("boxplot_or_violin_with_points")
    # enable statistics and build a spec that includes them
    win.stats_panel.setChecked(True)
    win.stats_panel.enable_cb.setChecked(True)
    i = win.stats_panel.test_combo.findData("welch_t")
    if i >= 0:
        win.stats_panel.test_combo.setCurrentIndex(i)
    spec = win._build_spec()
    assert spec.get("statistics", {}).get("enabled") is True
    saved_test = spec["statistics"]["test"]
    # simulate a fresh open: clear the panel, then apply the saved spec
    win.stats_panel.setChecked(False)
    win.stats_panel.enable_cb.setChecked(False)
    win._apply_plotspec_to_ui(spec)
    assert win.stats_panel.is_enabled()                       # re-enabled
    assert win.stats_panel.stats_spec()["test"] == saved_test  # test restored
    # re-rendering from the (restored) widgets still produces a stats report
    result = win.controller.render(win._build_spec(), win.data)
    assert getattr(result, "stats_report", None) is not None
    win.close()


def test_generate_transform_recommendation_reshapes_saves_and_renders(app, tmp_path):
    """A transform recommendation reshapes the data, saves the new CSV, and plots it."""
    import os
    import numpy as np
    import pandas as pd
    win = MainWindow()
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"gene": [f"g{i}" for i in range(20)]})
    for s in ["S1", "S2", "S3", "S4"]:
        df[s] = rng.normal(5, 2, 20)
    src = tmp_path / "matrix.csv"
    df.to_csv(src, index=False)
    win._set_data(win.controller.load_file(str(src)))
    rs = win.controller.recommend_for_loaded(win.data)
    tf = [r for r in rs.recommendations
          if getattr(r, "transform", None) and r.plot_type == "ridge_or_density_plot"]
    assert tf, "expected a wide->long ridge transform recommendation"
    win._on_generate_recommendation(tf[0])
    # data was reshaped to long, plotted, and the reshaped CSV persisted
    assert set(win.data.info.columns) == {"column", "value"}
    assert win._current_result is not None
    assert any(f.endswith("__long.csv") for f in os.listdir(tmp_path))
    win.close()


def test_differential_screen_via_grouping_dialog(app, tmp_path, monkeypatch):
    """Define groups → Differential screen → results table (log2FC/p/FDR) saved,
    adopted, and volcano/MA become recommended."""
    import os
    import numpy as np
    import pandas as pd
    from apps.desktop_app import grouping_panel
    from apps.desktop_app.grouping_panel import GroupingDialog

    monkeypatch.setattr(grouping_panel.QMessageBox, "information",
                        staticmethod(lambda *a, **k: None))
    win = MainWindow()
    rng = np.random.default_rng(2)
    df = pd.DataFrame({"gene": [f"g{i}" for i in range(25)]})
    for s in ["C1", "C2", "C3"]:
        df[s] = rng.normal(5, 1, 25)
    for s in ["T1", "T2", "T3"]:
        df[s] = rng.normal(6, 1, 25)
    src = tmp_path / "norm.csv"
    df.to_csv(src, index=False)
    win._set_data(win.controller.load_file(str(src)))
    dlg = GroupingDialog(win.controller, win.data)
    dlg.feature_combo.setCurrentText("gene")
    dlg._refresh_matrix_tab()
    for r in range(dlg.sample_table.rowCount()):
        s = dlg.sample_table.item(r, 0).text()
        dlg.sample_table.item(r, 1).setText("Ctrl" if s.startswith("C") else "Treat")
    dlg.mode_diff.setChecked(True)
    captured = {}
    dlg.grouped.connect(lambda ld: captured.setdefault("ld", ld))
    dlg._on_accept()
    ld = captured["ld"]
    assert {"log2FoldChange", "pvalue", "padj", "AveExpr"} <= set(ld.info.columns)
    win._adopt_grouped_data(ld)
    rs = win.controller.recommend_for_loaded(win.data)
    assert any(r.plot_type == "volcano_plot" and r.kind == "direct" for r in rs.recommendations)
    assert any(f.endswith("__diff.csv") for f in os.listdir(tmp_path))
    win.close()


def test_revert_restores_original_data_after_transform(app, tmp_path):
    """After a transform recommendation reshapes the data, Revert restores it."""
    import numpy as np
    import pandas as pd
    win = MainWindow()
    rng = np.random.default_rng(3)
    df = pd.DataFrame({"gene": [f"g{i}" for i in range(20)]})
    for s in ["S1", "S2", "S3", "S4"]:
        df[s] = rng.normal(5, 2, 20)
    src = tmp_path / "m.csv"
    df.to_csv(src, index=False)
    win._set_data(win.controller.load_file(str(src)))
    assert win.revert_btn.isHidden()                 # clean load: nothing to revert
    orig_cols = set(win.data.info.columns)
    rs = win.controller.recommend_for_loaded(win.data)
    tf = [r for r in rs.recommendations
          if getattr(r, "transform", None) and r.plot_type == "ridge_or_density_plot"][0]
    win._on_generate_recommendation(tf)
    assert set(win.data.info.columns) == {"column", "value"}   # reshaped
    assert not win.revert_btn.isHidden()             # revert now offered
    win.action_revert_data()
    assert set(win.data.info.columns) == orig_cols   # back to the original table
    assert win.revert_btn.isHidden()                 # button hidden again
    assert win._current_result is not None or win.data is not None
    win.close()


# --- reproducible figure packages (v1.1.1) -----------------------------------------------

def _stub_dialogs(monkeypatch, save_path=None, open_path=None):
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    if save_path is not None:
        monkeypatch.setattr(QFileDialog, "getSaveFileName",
                            staticmethod(lambda *a, **k: (save_path, "Figure package (*.mmfpackage)")))
    if open_path is not None:
        monkeypatch.setattr(QFileDialog, "getOpenFileName",
                            staticmethod(lambda *a, **k: (open_path, "Figure package (*.mmfpackage)")))
    shown = []
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.Save if len(a) > 3 and (a[3] & QMessageBox.Save) else QMessageBox.Yes))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: shown.append(("info", a[1], a[2]))))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: shown.append(("warning", a[1], a[2]))))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: shown.append(("critical", a[1], a[2]))))
    return shown


def test_landing_page_has_open_figure_package_button(app):
    from PySide6.QtWidgets import QPushButton

    win = MainWindow()
    labels = [b.text() for b in win.findChildren(QPushButton)]
    assert "Open Figure Package" in labels
    assert "Open data file" in labels and "Use example data" in labels and "Recent files" in labels and "Help" in labels
    assert "Save Figure Package (.mmfpackage)" in labels
    win.close()


def test_save_and_reopen_figure_package_with_statistics(app, tmp_path, monkeypatch):
    """Save package → close → new window → Open Figure Package → identical spec + stats."""
    import shutil

    win = MainWindow()
    win.load_example("boxplot_or_violin_with_points")
    win.stats_panel.setChecked(True)
    win.stats_panel.enable_cb.setChecked(True)
    i = win.stats_panel.test_combo.findData("welch_t")
    if i >= 0:
        win.stats_panel.test_combo.setCurrentIndex(i)
    win.render_preview()
    assert win._current_result is not None and win._current_result.stats_report is not None
    spec_a = win._build_spec()
    stats_a = [r.to_dict() for r in win._current_result.stats_report.results]
    dest = str(tmp_path / "boxes.mmfpackage")
    shown = _stub_dialogs(monkeypatch, save_path=dest)
    win.action_save_package()
    assert os.path.exists(dest) and os.path.getsize(dest) > 1000
    assert any(kind == "info" and "Figure package saved" in title for kind, title, _ in shown)
    assert dest in win._recent_files()
    win.close()
    # move it, open in a fresh window
    moved = tmp_path / "elsewhere" / "received.mmfpackage"
    moved.parent.mkdir()
    shutil.move(dest, moved)
    win2 = MainWindow()
    shown2 = _stub_dialogs(monkeypatch, open_path=str(moved))
    win2.action_open_package()
    assert win2.stack.currentIndex() == 1 and win2._current_result is not None
    assert win2._package_context is not None and win2._package_context.integrity == "verified"
    assert win2.plot_combo.currentData() == spec_a["plot_type"]
    spec_b = win2._current_spec
    for k in ("plot_type", "mapping", "layout", "statistics"):
        assert {kk: v for kk, v in spec_b.get(k, {}).items() if kk != "source"} == \
               {kk: v for kk, v in spec_a.get(k, {}).items() if kk != "source"} if isinstance(spec_a.get(k), dict) else spec_b.get(k) == spec_a.get(k)
    stats_b = [r.to_dict() for r in win2._current_result.stats_report.results]
    assert [(r["test_id"], r["p_value"], r["adjusted_p_value"], r["effect_size"]) for r in stats_a] == \
           [(r["test_id"], r["p_value"], r["adjusted_p_value"], r["effect_size"]) for r in stats_b]
    assert not any(kind in ("warning", "critical") for kind, _, _ in shown2), shown2
    assert "integrity verified" in win2.statusBar().currentMessage()
    # normal editing + re-export still work
    win2.title_edit.setText("edited after reopening")
    win2.render_preview()
    assert win2._current_spec["layout"]["title"] == "edited after reopening"
    blob_dest = str(tmp_path / "again.zip")
    monkeypatch.setattr(__import__("PySide6.QtWidgets", fromlist=["QFileDialog"]).QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (blob_dest, "ZIP (*.zip)")))
    win2.export_zip()
    import zipfile

    assert any(n.endswith(".mmfpackage") for n in zipfile.ZipFile(blob_dest).namelist())
    win2.close()


def test_open_invalid_and_tampered_package_shows_error_no_traceback(app, tmp_path, monkeypatch):
    import json
    import zipfile

    win = MainWindow()
    bad = tmp_path / "bad.mmfpackage"
    bad.write_bytes(b"this is not a zip")
    shown = _stub_dialogs(monkeypatch, open_path=str(bad))
    win.action_open_package()
    assert shown and shown[-1][0] == "critical" and "not a valid ZIP" in shown[-1][2]
    assert win.stack.currentIndex() == 0            # still on the landing page
    # tampered: build a good package, edit one value, repack
    win.load_example("scatterplot_with_regression")
    good = str(tmp_path / "good.mmfpackage")
    shown = _stub_dialogs(monkeypatch, save_path=good)
    win.action_save_package()
    zin = zipfile.ZipFile(good)
    tampered = str(tmp_path / "tampered.mmfpackage")
    with zipfile.ZipFile(tampered, "w") as zout:
        for zi in zin.infolist():
            data = zin.read(zi.filename)
            if zi.filename.startswith("data/") and zi.filename.endswith(".mmftable.json"):
                doc = json.loads(data)
                doc["columns"][1]["values"][0] = 424242.0
                data = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
            zout.writestr(zi.filename, data)
    shown = _stub_dialogs(monkeypatch, open_path=tampered)
    win.action_open_package()
    assert shown[-1][0] == "critical" and "integrity check failed" in shown[-1][2]
    win.close()


def test_package_path_routes_through_load_path_and_recent(app, tmp_path, monkeypatch):
    win = MainWindow()
    win.load_example("forest_plot")
    dest = str(tmp_path / "forest.mmfpackage")
    _stub_dialogs(monkeypatch, save_path=dest)
    win.action_save_package()
    win2 = MainWindow()
    _stub_dialogs(monkeypatch)
    win2.load_path(dest)                                   # drag-drop / recent files use this
    assert win2._package_context is not None and win2.plot_combo.currentData() == "forest_plot"
    labels = [a.text() for a in win2.recent_menu.actions()]
    assert any(l.startswith("📦 ") and l.endswith("forest.mmfpackage") for l in labels)
    win.close()
    win2.close()


def test_composite_package_reopens_in_figure_builder(app, tmp_path, monkeypatch):
    from apps.desktop_app.stats_panel import FigureBuilderDialog

    win = MainWindow()
    win.load_example("scatterplot_with_regression")
    win.action_save_panel()
    win.load_example("barplot_with_error_bar")
    win.action_save_panel()
    assert len(win._saved_panels) == 2
    dlg = FigureBuilderDialog(win.controller, win._saved_panels, win)
    dest = str(tmp_path / "Figure_1.mmfpackage")
    _stub_dialogs(monkeypatch, save_path=dest)
    dlg._save_package()
    assert os.path.exists(dest)
    dlg.close()
    win.close()
    # fresh window, no panels: open the composite package (the builder dialog is stubbed to not block)
    win2 = MainWindow()
    monkeypatch.setattr(FigureBuilderDialog, "exec", lambda self: 0)
    shown = _stub_dialogs(monkeypatch, open_path=dest)
    win2.action_open_package()
    assert len(win2._saved_panels) == 2
    assert win2._saved_panels[0]["plot_spec"]["plot_type"] == "scatterplot_with_regression"
    assert win2._saved_panels[0]["table"] is not None and len(win2._saved_panels[0]["table"]) > 0
    assert not any(kind == "critical" for kind, _, _ in shown), shown
    win2.close()
