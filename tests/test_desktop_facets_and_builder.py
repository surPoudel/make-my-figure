"""Facet grids in the desktop window, the Figure Builder and presets."""
import os
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication

    from apps.desktop_app.main import MainWindow
except Exception as exc:  # noqa: BLE001
    pytest.skip(f"PySide6/Qt unavailable: {exc}", allow_module_level=True)

from apps.desktop_app.controller import DesktopController  # noqa: E402
from make_my_figure_core.panels import FigureLayout, MultiPanelFigure, Panel, build_figure  # noqa: E402
from make_my_figure_core.panels.builder import _render_panel_figure, panel_frames  # noqa: E402
from make_my_figure_core.plots.facets import facet_axes  # noqa: E402
from make_my_figure_core.presets import apply_preset, extract_preset  # noqa: E402

CSV = Path(__file__).parent / "fixtures" / "plant_growth_facets.csv"
DF = pd.read_csv(CSV)
C = DesktopController()


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _option_visible(win, key):
    w = win._option_widgets[key]
    try:
        return win.options_form.isRowVisible(w)
    except AttributeError:  # pragma: no cover
        return w.isVisible()


@pytest.mark.parametrize("pt,group_field", [("boxplot_or_violin_with_points", "hue"),
                                            ("lineplot_timecourse_with_error_band", "color")])
def test_window_offers_facets_and_shows_their_options_only_when_used(app, pt, group_field):
    win = MainWindow()
    win.show()
    win.load_path(str(CSV))
    win.plot_combo.setCurrentIndex(win.plot_combo.findData(pt))
    QApplication.processEvents()
    for f, col in (("x", "Month"), ("y", "Growth_cm"), (group_field, "Nitrogen_Concentration")):
        win._mapping_widgets[f].setCurrentText(col)
    assert {"facet_row", "facet_col"} <= set(win._mapping_widgets)
    spec = win._build_spec()
    assert "facet_labels" not in spec["mapping"] and "facet_share_y" not in spec["mapping"]
    assert not _option_visible(win, "facet_labels")

    win._mapping_widgets["facet_row"].setCurrentText("Age")
    win._mapping_widgets["facet_col"].setCurrentText("Species")
    win._option_widgets["facet_labels"].setCurrentText("value")
    win.render_preview()
    assert _option_visible(win, "facet_labels") and _option_visible(win, "facet_share_y")
    spec = win._build_spec()
    assert spec["mapping"]["facet_labels"] == "value" and spec["mapping"]["facet_row"] == "Age"
    panels = facet_axes(win._canvas.figure)
    assert len(panels) == 4
    win.close()


def test_builder_panel_reproduces_the_grid():
    s = C.build_spec("lineplot_timecourse_with_error_band", "publication", "plants.csv",
                     {"x": "Month", "y": "Growth_cm", "color": "Nitrogen_Concentration", "facet_row": "Age",
                      "facet_col": "Species", "error_display": "bars"}, width="default")
    alone = C.render(s, C.loaded_from_dataframe(DF, "plants.csv"))
    mpf = MultiPanelFigure(name="F", layout=FigureLayout(ncols=1, fig_width_mm=180.0, panel_dpi=72))
    mpf.add_panel(Panel(plot_spec=s, table=DF, label="A", width_in=6.0))
    fig = build_figure(mpf)
    assert [f["label"] for f in panel_frames(fig)] == ["A"]
    pfig = _render_panel_figure(mpf.panels[0], size_in=(6.0, None))
    p_axes, a_axes = facet_axes(pfig), facet_axes(alone.figure)
    assert len(p_axes) == len(a_axes) == 4
    levels = ("Low N", "Medium N", "High N")
    for pa, aa in zip(p_axes, a_axes):
        lp = {ln.get_label(): ln for ln in pa.get_lines() if ln.get_label() in levels}
        la = {ln.get_label(): ln for ln in aa.get_lines() if ln.get_label() in levels}
        assert set(lp) == set(la) == set(levels)
        for lev in levels:
            np.testing.assert_allclose(np.asarray(lp[lev].get_ydata(), float),
                                       np.asarray(la[lev].get_ydata(), float), rtol=1e-12)


def test_a_style_preset_does_not_carry_facet_columns_a_full_preset_does():
    base = {"x": "Month", "y": "Growth_cm", "hue": "Nitrogen_Concentration", "facet_row": "Age",
            "facet_col": "Species", "facet_labels": "value"}
    s = C.build_spec("boxplot_or_violin_with_points", "publication", "plants.csv", base, width="default")
    fresh = C.build_spec("boxplot_or_violin_with_points", "publication", "other.csv",
                         {"x": "Month", "y": "Growth_cm"}, width="default")
    cols = list(DF.columns)
    out = apply_preset(extract_preset(s, mode="style"), fresh, columns=cols).spec
    assert "facet_row" not in out["mapping"] and "facet_col" not in out["mapping"]
    out = apply_preset(extract_preset(s, mode="full"), fresh, columns=cols).spec
    assert out["mapping"]["facet_row"] == "Age" and out["mapping"]["facet_col"] == "Species"


def test_statistics_panel_offers_whole_grid_option_only_on_a_grid(app):
    win = MainWindow()
    win.show()
    win.load_path(str(CSV))
    win.plot_combo.setCurrentIndex(win.plot_combo.findData("boxplot_or_violin_with_points"))
    QApplication.processEvents()
    for f, col in (("x", "Month"), ("y", "Growth_cm")):
        win._mapping_widgets[f].setCurrentText(col)
    win.stats_panel.setChecked(True)
    win.stats_panel.enable_cb.setChecked(True)
    win.stats_panel.facet_scope_cb.setChecked(True)
    spec = win._build_spec()
    assert "facet_scope" not in (spec.get("statistics") or {})      # no facets: inert and hidden
    assert not win.stats_panel._facets_active
    win._mapping_widgets["facet_col"].setCurrentText("Species")
    spec = win._build_spec()
    assert win.stats_panel._facets_active
    assert spec["statistics"].get("facet_scope") == "figure"
    win.close()


def test_sums_of_squares_shown_for_factorial_anova_only_and_placement_only_when_bracketed(app):
    from apps.desktop_app.stats_panel import StatisticsPanel

    p = StatisticsPanel(C)
    p.show()
    form = p._form

    def shown(w):
        return form.isRowVisible(w)

    p.setChecked(True)
    p.enable_cb.setChecked(True)
    assert not shown(p.ss_combo) and shown(p.placement_combo)          # Auto-suggest
    p.test_combo.setCurrentIndex(p.test_combo.findData("factorial_anova"))
    assert shown(p.ss_combo) and not shown(p.placement_combo)          # nothing to bracket
    assert "ss_type" not in p.stats_spec()                              # untouched: writes nothing
    p.posthoc_cb.setChecked(True)
    assert shown(p.placement_combo)                                     # post-hoc pairs are bracketed
    p.ss_combo.setCurrentIndex(p.ss_combo.findData(1))
    spec = p.stats_spec()
    assert spec["ss_type"] == 1
    q = StatisticsPanel(C)
    q.load_spec(spec)
    assert q.ss_combo.currentData() == 1 and q.stats_spec()["ss_type"] == 1
    p.test_combo.setCurrentIndex(p.test_combo.findData("welch_t"))
    assert not shown(p.ss_combo) and "ss_type" not in p.stats_spec()


def test_anova_terms_as_stars_checkbox_is_opt_in_and_round_trips(app):
    from apps.desktop_app.stats_panel import StatisticsPanel

    p = StatisticsPanel(C)
    p.show()
    p.setChecked(True)
    p.enable_cb.setChecked(True)
    p.test_combo.setCurrentIndex(p.test_combo.findData("factorial_anova"))
    assert p._form.isRowVisible(p.omnibus_stars_cb)                      # Stars only + ANOVA
    assert "omnibus_stars" not in p.stats_spec()["annotation"]           # untouched: writes nothing
    p.omnibus_stars_cb.setChecked(True)
    spec = p.stats_spec()
    assert spec["annotation"]["omnibus_stars"] is True
    q = StatisticsPanel(C)
    q.load_spec(spec)
    assert q.omnibus_stars_cb.isChecked()
    p.annotation_combo.setCurrentIndex(p.annotation_combo.findData("p"))
    assert not p._form.isRowVisible(p.omnibus_stars_cb)                  # acts only under Stars only
    assert "omnibus_stars" not in p.stats_spec()["annotation"]
    p.annotation_combo.setCurrentIndex(p.annotation_combo.findData("stars"))
    p.test_combo.setCurrentIndex(p.test_combo.findData("welch_t"))
    assert not p._form.isRowVisible(p.omnibus_stars_cb)                  # no ANOVA terms


def test_wide_table_is_reshaped_in_the_window_saved_beside_and_revertible(app, tmp_path, monkeypatch):
    import hashlib

    from PySide6.QtWidgets import QDialog

    from apps.desktop_app import reshape_dialog

    wide = tmp_path / "plants_wide.csv"
    wide.write_bytes((Path(__file__).parent / "fixtures" / "plant_growth_wide.csv").read_bytes())
    digest = hashlib.sha256(wide.read_bytes()).hexdigest()
    win = MainWindow()
    win.load_path(str(wide))
    QApplication.processEvents()
    assert win.reshape_btn.text().endswith("(suggested)")

    def drive(dlg):
        # the suggestion is pre-filled: Month_4 ... Month_10 into Month; name the values
        assert dlg.btn_apply.isEnabled() and "60 rows → 240 rows" in dlg.status.text()
        dlg.values_to.setText("Growth_cm")
        dlg._accept()
        return QDialog.Accepted

    monkeypatch.setattr(reshape_dialog.ReshapeDialog, "exec", drive)
    win.action_reshape_wide()
    df = win.data.info.dataframe
    assert df.shape == (240, 6) and list(df.columns)[-2:] == ["Month", "Growth_cm"]
    assert (tmp_path / "plants_wide_long.csv").exists()
    assert (tmp_path / "plants_wide_long.transformations.json").exists()
    assert hashlib.sha256(wide.read_bytes()).hexdigest() == digest
    assert win.revert_btn.isVisibleTo(win) and not win.reshape_btn.text().endswith("(suggested)")
    win.plot_combo.setCurrentIndex(win.plot_combo.findData("boxplot_or_violin_with_points"))
    QApplication.processEvents()
    for f, col in (("x", "Month"), ("y", "Growth_cm"), ("hue", "Nitrogen_Concentration"),
                   ("facet_row", "Age"), ("facet_col", "Species")):
        win._mapping_widgets[f].setCurrentText(col)
    win.render_preview()
    assert len(facet_axes(win._canvas.figure)) == 4
    win.action_revert_data()
    assert win.data.info.dataframe.shape == (60, 8)
    win.close()


def test_assumption_action_is_offered_for_parametric_tests_and_round_trips(app):
    from apps.desktop_app.stats_panel import StatisticsPanel

    p = StatisticsPanel(C)
    p.show()
    p.setChecked(True)
    p.enable_cb.setChecked(True)
    assert p._form.isRowVisible(p.assumption_combo)                      # Auto-suggest may pick one
    assert "assumption_action" not in p.stats_spec()                     # untouched: writes nothing
    p.test_combo.setCurrentIndex(p.test_combo.findData("mann_whitney"))
    assert not p._form.isRowVisible(p.assumption_combo)                  # nothing to check
    p.test_combo.setCurrentIndex(p.test_combo.findData("welch_t"))
    p.assumption_combo.setCurrentIndex(p.assumption_combo.findData("switch"))
    spec = p.stats_spec()
    assert spec["assumption_action"] == "switch"
    q = StatisticsPanel(C)
    q.load_spec(spec)
    assert q.assumption_combo.currentData() == "switch"
    # the results table lists the checks with a verdict
    young = DF[DF.Age == "Young"]
    s = C.build_spec("boxplot_or_violin_with_points", "publication", "t.csv",
                     {"x": "Month", "y": "Growth_cm", "hue": "Nitrogen_Concentration"}, width="default",
                     statistics={"enabled": True, "test": "factorial_anova"})
    p.show_report(C.render(s, C.loaded_from_dataframe(young, "t.csv")).stats_report)
    tests = [p.table.item(i, 1).text() for i in range(p.table.rowCount())]
    notes = [p.table.item(i, 6).text() for i in range(p.table.rowCount())]
    assert "Shapiro-Wilk - normality" in tests and "Levene (median-centred) - equal variances" in tests
    assert notes[tests.index("Shapiro-Wilk - normality")] == "met"
    assert notes[tests.index("Levene (median-centred) - equal variances")] == "NOT met"   # P = 9.5e-5


def test_model_diagnostics_window_shows_the_four_panels_and_saves(app, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    from apps.desktop_app.diagnostics_dialog import DiagnosticsDialog

    win = MainWindow()
    win.load_path(str(CSV))
    win.plot_combo.setCurrentIndex(win.plot_combo.findData("boxplot_or_violin_with_points"))
    QApplication.processEvents()
    for f, col in (("x", "Month"), ("y", "Growth_cm"), ("hue", "Nitrogen_Concentration"), ("facet_col", "Age")):
        win._mapping_widgets[f].setCurrentText(col)
    dlg = DiagnosticsDialog(win.data, win._build_spec(), None, win)
    panels = [dlg.panel_combo.itemData(i) for i in range(dlg.panel_combo.count())]
    assert panels[:2] == ["Age = Young", "Age = Old"] and panels[-1].startswith("whole grid")
    assert [ax.get_title() for ax in dlg.canvas.figure.axes][:3] == ["Residuals vs Fitted", "Normal Q-Q",
                                                                      "Scale-Location"]
    assert "NOT met" in dlg.summary.text()                    # Levene within an age, P = 9.5e-5
    png, csv = tmp_path / "d.png", tmp_path / "d.csv"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(png), ""))
    dlg._save_figure()
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(csv), ""))
    dlg._save_values()
    assert png.stat().st_size > 10_000
    vals = pd.read_csv(csv)
    assert len(vals) == 120 and {"fitted", "standardized_residual", "leverage", "cooks_distance"} <= set(vals.columns)
    dlg.panel_combo.setCurrentIndex(dlg.panel_combo.count() - 1)
    assert dlg.diag.n == 240
    dlg.close()
    win.close()


def test_statistics_report_tab_reads_like_r_and_saves(app, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    from apps.desktop_app.diagnostics_dialog import DiagnosticsDialog

    s = C.build_spec("boxplot_or_violin_with_points", "publication", "plants.csv",
                     {"x": "Month", "y": "Growth_cm", "hue": "Nitrogen_Concentration", "facet_col": "Age"},
                     width="default", statistics={"enabled": True, "test": "factorial_anova"})
    dlg = DiagnosticsDialog(C.loaded_from_dataframe(DF, "plants.csv"), s, None, None,
                            start_tab=DiagnosticsDialog.REPORT_TAB)
    assert dlg.tabs.currentIndex() == 0
    text = dlg.report_text.toPlainText()
    assert "> summary(model)" in text and "Df Sum Sq Mean Sq F value" in text
    assert "$`Month:Nitrogen_Concentration`" in text and "Age = Young" in text
    out = tmp_path / "report.txt"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(out), ""))
    dlg._save_report()
    assert out.read_text(encoding="utf-8").startswith("Statistics report - Age = Young")
    dlg.close()
