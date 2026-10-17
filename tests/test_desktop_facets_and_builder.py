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
