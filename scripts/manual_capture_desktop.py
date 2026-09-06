"""Capture Desktop-app screenshots for the manuals, offscreen, from bundled example data only.

Runs the real MainWindow on Qt's offscreen platform (QT_QPA_PLATFORM=offscreen), drives it through
the documented states, and grabs each as PNG under docs/manuals/assets/screenshots/. Modal dialogs
are captured by temporarily replacing QDialog.exec with a grab-and-cancel, so nothing blocks.

Only bundled synthetic examples are loaded; the preset library is pointed at a temporary folder.
"""
from __future__ import annotations

import json
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MAKE_MY_FIGURE_PRESETS", "/tmp/doc_presets")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "docs", "manuals", "assets", "screenshots")
os.makedirs(OUT, exist_ok=True)

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QWidget, QScrollArea  # noqa: E402

from apps.desktop_app import main as M  # noqa: E402

app = QApplication.instance() or QApplication(["mmf"])
W, H = 1680, 1000
captured = []


def pump(n=25, dt=0.04):
    for _ in range(n):
        app.processEvents()
        time.sleep(dt)


def grab(widget: QWidget, name: str, note: str = ""):
    pump(8)
    path = os.path.join(OUT, name)
    ok = widget.grab().save(path)
    captured.append({"screenshot": name, "ok": ok, "size": f"{widget.width()}x{widget.height()}", "note": note})
    print(f"  {'ok ' if ok else 'FAIL'} {name}  {widget.width()}x{widget.height()}  {note}")


# capture modal dialogs instead of blocking on them
_pending_dialog_name = {"name": None}
_orig_exec = QDialog.exec


def _grab_exec(self, *a, **k):
    name = _pending_dialog_name["name"] or f"dialog_{self.windowTitle().replace(' ', '_')}.png"
    self.show()
    pump(20)
    grab(self, name, f"dialog: {self.windowTitle()}")
    self.hide()
    return QDialog.Rejected


QDialog.exec = _grab_exec
_about_text = {}
_messages = []
QMessageBox.about = lambda parent, title, text: _about_text.update({"title": title, "text": text})


def _record(kind):
    def _f(parent, title, text, *a, **k):
        _messages.append({"kind": kind, "title": str(title), "text": str(text)[:300]})
        print(f"  [msgbox:{kind}] {title}: {str(text)[:100]}")
        return QMessageBox.Yes if kind == "question" else QMessageBox.Ok
    return _f


# Static message boxes would block forever offscreen; record them and answer "OK"/"Yes" instead.
for _kind in ("information", "warning", "critical", "question"):
    setattr(QMessageBox, _kind, staticmethod(_record(_kind)))

win = M.MainWindow()
win.resize(W, H)
win.show()
pump(20)
# a wider controls column so the recommendation cards and combos are not clipped
try:
    win.main_splitter.setSizes([640, W - 640])
except Exception:
    pass
pump(10)

# 01 home / upload
grab(win, "desktop_01_home_upload.png", "welcome page before any data")

# 02 data loaded + workspace (bar plot example)
win.load_example("barplot_with_error_bar")
pump(40)
grab(win, "desktop_02_data_loaded_workspace.png", "bar plot example rendered; data preview + controls")

# 03 plot selector (Plot types help tab is in Help; the selector is the combo) — capture controls column
ctrl = win.main_splitter.widget(0)
grab(ctrl, "desktop_03_plot_selector_and_mapping.png", "controls column: plot type, recommendations, map columns, options")

# 04 publication controls: enable the style box and scroll it into view
win._style_box.setChecked(True)
pump(10)
scroll = None
for sa in ctrl.findChildren(QScrollArea):
    scroll = sa
if scroll is not None:
    scroll.ensureWidgetVisible(win._style_box)
    pump(10)
grab(win._style_box, "desktop_04_publication_controls.png", "5. Publication style group (typography, axes, legend, colorbar, margins)")

# 05 statistics panel with a two-group example (box/violin)
win.load_example("boxplot_or_violin_with_points")
pump(40)
sp = win.stats_panel
sp.setChecked(True)            # the group box itself is checkable
sp.enable_cb.setChecked(True)
pump(10)
try:
    i = sp.test_combo.findData("welch_t");  sp.test_combo.setCurrentIndex(max(i, 0))
    j = sp.mode_combo.findData("all_pairs"); sp.mode_combo.setCurrentIndex(max(j, 0))
except Exception:
    pass
pump(10)
try:
    sp.run()                   # "Run statistics"
except Exception as exc:
    print("  stats run failed:", exc)
pump(60)
if scroll is not None:
    scroll.ensureWidgetVisible(sp)
grab(sp, "desktop_05_statistics.png", "Statistics panel: test, comparison, correction, annotation, results table")
grab(win, "desktop_05b_statistics_figure.png", "box/violin with brackets after Run statistics")

# 06/07/08 matrix workflow dialog tabs
win.load_example("heatmap_clustered_matrix")
pump(40)
from apps.desktop_app.matrix_wizard import MatrixWizardDialog  # noqa: E402
dlg = MatrixWizardDialog(win.controller, win.data, win._saved_panels, win)
dlg.resize(1400, 860)
dlg.show(); pump(30)
tw = dlg.tabs
grab(dlg, "desktop_06_matrix_workflow_mapping.png", "Matrix workflow tab: ① Map columns (before confirming)")
dlg._confirm_mapping(); pump(30)                       # unlocks the later steps
tw.setCurrentIndex(1); pump(20)
# fill the group table the way a user would type it, using the same name-token guess the
# Define-groups dialog offers (Ctrl_1 -> Ctrl, DrugA_1 -> DrugA, ...)
from make_my_figure_core.grouping import guess_groups_from_names  # noqa: E402
gt = dlg.group_table
names_in_table = [gt.item(r, 0).text() for r in range(gt.rowCount()) if gt.item(r, 0)]
guess = guess_groups_from_names(names_in_table)
for r in range(gt.rowCount()):
    it0 = gt.item(r, 0)
    if it0 is None:
        continue
    it1 = gt.item(r, 1)
    if it1 is None:
        it1 = M.QTableWidgetItem(""); gt.setItem(r, 1, it1)
    it1.setText(guess.get(it0.text(), ""))
pump(10)
grab(dlg, "desktop_07_matrix_workflow_groups.png", "Matrix workflow tab: ② Define groups (groups typed per sample column)")
try:
    dlg._confirm_groups(); pump(30)
except Exception as exc:
    print("  confirm groups:", exc)
tw.setCurrentIndex(2); pump(20)
grab(dlg, "desktop_08_preprocessing_qc.png", "Matrix workflow tab: ③ Preprocess (raw-like)")
tw.setCurrentIndex(3); pump(20)
try:
    dlg._diagnose(); pump(120)
except Exception as exc:
    print("  diagnose:", exc)
grab(dlg, "desktop_08b_matrix_validation.png", "Matrix workflow tab: ④ Validation after Run diagnostics")
tw.setCurrentIndex(4); pump(30)
grab(dlg, "desktop_08c_matrix_recommend_generate.png", "Matrix workflow tab: ⑤ Recommend & generate")
dlg.hide()

# 09 recommendations panel (generic long table)
win.load_example("dot_strip_plot")
pump(40)
try:
    rp = win.findChildren(M.QGroupBox)
    rec = [g for g in rp if g.title() == "Recommended plots"][0]
    grab(rec, "desktop_09_plot_recommendations.png", "Recommended plots for a grouped-observation table")
except Exception as exc:
    print("  skip recommendations:", exc)

# 10 volcano editor (options incl. significance colours + label controls)
win.load_example("volcano_plot")
pump(40)
grab(win, "desktop_10_volcano_editor.png", "volcano example with options and labels")
grab(win.options_box, "desktop_10b_volcano_options.png", "volcano options: class colours, cutoffs, labels, duplicate policy")

# 11 figure preset: save dialog (captured via exec patch), then list after saving programmatically
win.load_example("scatterplot_with_regression")
pump(40)
_pending_dialog_name["name"] = "desktop_11_figure_preset_save.png"
win.action_save_preset()
_pending_dialog_name["name"] = None
from make_my_figure_core import presets as P  # noqa: E402
spec = win._current_spec
spec = dict(spec); spec["style"] = {"title_font_pt": 16, "palette_name": "colorblind_safe"}
P.PresetStore().save(P.extract_preset(spec, mode="style", name="Lab scatter style"))
P.PresetStore().save(P.extract_preset(spec, mode="full", name="Scatter full configuration"))
win._refresh_preset_list()
pump(10)
preset_box = [g for g in win.findChildren(M.QGroupBox) if g.title() == "Figure preset"][0]
try:
    win.preset_combo.setCurrentIndex(1)
except Exception:
    pass
pump(10)
grab(preset_box, "desktop_12_figure_preset_load.png", "Figure preset group with saved presets listed")

# 13 annotation controls: point picking on the volcano + label picks
win.load_example("volcano_plot")
pump(40)
win.chk_click_label.setChecked(True)
pump(10)
grab(win.findChildren(M.QGroupBox)[[g.title() for g in win.findChildren(M.QGroupBox)].index("4. Labels & size")],
     "desktop_13_annotation_controls.png", "Labels & size group with Point picking enabled")

# 14/15 figure builder with two saved panels
win._saved_panels.clear()
for pt in ("barplot_with_error_bar", "scatterplot_with_regression", "volcano_plot"):
    win.load_example(pt); pump(35)
    win._saved_panels.append({"plot_spec": dict(win._current_spec), "table": win.data.info.dataframe,
                              "aux": {}, "title": M.display_name(pt), "plot_type": pt})
from apps.desktop_app.stats_panel import FigureBuilderDialog  # noqa: E402
fb = FigureBuilderDialog(win.controller, win._saved_panels, win)
fb.resize(1280, 800); fb.show(); pump(60)
fb._update_preview(); pump(30)
grab(fb, "desktop_14_figure_builder.png", "Figure Builder with three generated panels")
fb.list.setCurrentRow(0); pump(10)
fb.pw_spin.setValue(6.0); fb.cols_combo.setCurrentText("2"); fb.rows_combo.setCurrentText("2"); pump(10)
fb._update_preview(); pump(40)
grab(fb, "desktop_15_figure_builder_resize.png", "first panel widened to 6 in; 2x2 grid")
fb.hide()

# 16 export controls
exp = [g for g in win.findChildren(M.QGroupBox) if g.title() == "5. Export"][0]
grab(exp, "desktop_16_export_options.png", "Export group: SVG/PNG/PDF/PlotSpec JSON, ZIP, template, panels")

# 17 multi-sheet workbook: the bundled example workbook
wb = os.path.join(ROOT, "examples", "Make_My_Figure_All_Example_Data.xlsx")
if os.path.exists(wb):
    win.load_path(wb); pump(60)
    grab(win.sheet_box, "desktop_17_multi_sheet_workbook.png", "Worksheet chooser for the bundled example workbook")
    grab(win, "desktop_17b_workbook_loaded.png", "workbook loaded: worksheet box, preview and figure")

# 18 help / about
_pending_dialog_name["name"] = "desktop_18_help.png"
win.action_help()
_pending_dialog_name["name"] = None
win.action_about()
with open(os.path.join(OUT, "desktop_about_text.json"), "w", encoding="utf-8") as fh:
    json.dump(_about_text, fh, indent=2)
print("about:", _about_text.get("text", "")[:160].replace("\n", " "))

with open(os.path.join(OUT, "desktop_capture_log.json"), "w", encoding="utf-8") as fh:
    json.dump({"captured": captured, "message_boxes": _messages}, fh, indent=2)
print(f"captured {sum(c['ok'] for c in captured)}/{len(captured)}")
