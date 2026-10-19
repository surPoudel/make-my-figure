"""Capture the tutorial screenshots from the REAL desktop application.

Drives ``apps.desktop_app.main.MainWindow`` and the "Prepare table" dialog
exactly as a user would (load the workbook, assign roles, preview and apply a
transformation, switch the axis scale, check a factorial design, save and reopen
a Figure Package) and grabs each window to ``screenshots/``.

Run (from the repository root):
    QT_QPA_PLATFORM=offscreen python tutorial/general_tabular_data/make_screenshots.py
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib  # noqa: E402

matplotlib.use("Agg")

from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from apps.desktop_app.main import MainWindow  # noqa: E402
from apps.desktop_app.table_workflow import TableWorkflowDialog  # noqa: E402

OUT = os.path.join(HERE, "screenshots")
BEE = os.path.join(ROOT, "tests", "fixtures", "bee_demo_workbook.xlsx")
SIM = os.path.join(HERE, "data", "simulated_bee_factorial.csv")


def grab(widget, name):
    QApplication.processEvents()
    QTest.qWait(150)
    path = os.path.join(OUT, name)
    widget.grab().save(path)
    print("wrote", os.path.relpath(path, ROOT))
    return path


def apply_dialog(win, actions):
    dlg = TableWorkflowDialog(win.controller, win.data, win)
    dlg.show()
    actions(dlg)
    return dlg


def main():
    os.makedirs(OUT, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    win.resize(1500, 950)
    win.show()

    # 1. import the bee workbook
    win.load_path(BEE)
    grab(win, "01_bee_workbook_imported.png")

    # 2. roles
    dlg = apply_dialog(win, lambda d: d.tabs.setCurrentIndex(0))
    dlg.resize(1100, 720)
    grab(dlg, "02_assign_column_roles.png")

    # 3. transform preview
    dlg.tabs.setCurrentIndex(1)
    dlg.tf_column.setCurrentText("bee body size_mm")
    dlg.tf_method.setCurrentIndex(dlg.tf_method.findData("log10"))
    grab(dlg, "03_transform_preview_log10.png")

    # 4. the factorial design the workbook cannot support
    dlg.tabs.setCurrentIndex(2)
    for i, f in enumerate(("treatment", "social setting", "time")):
        dlg.an_factors[i].setCurrentText(f)
    dlg.an_response.setCurrentText("total quantity")
    dlg.an_subject.setCurrentText("(none)")
    dlg._run()
    grab(dlg, "04_three_way_design_not_estimable.png")

    # 5. apply the log10 transformation and plot it
    dlg.tabs.setCurrentIndex(1)
    dlg._add_transform()
    dlg.an_response.setCurrentText("log10(bee body size_mm)")
    dlg._apply()
    new = dlg.result_data
    win._handoff_mapping = {"x": "treatment", "y": "log10(bee body size_mm)"}
    prev = win._suppress_change
    win._suppress_change = True
    win.plot_combo.setCurrentIndex(win.plot_combo.findData("boxplot_or_violin_with_points"))
    win._suppress_change = prev
    win._set_data(new)
    win._handoff_mapping = {}
    win._data_before_transform = win.controller.raw_of(new)
    win.revert_btn.setVisible(True)
    grab(win, "05_boxplot_of_log10_derived_column.png")
    dlg.close()

    # 6-7. simulated replicated dataset: raw values, then the same raw values on a log10 axis
    win.load_path(SIM)
    win.plot_combo.setCurrentIndex(win.plot_combo.findData("dot_strip_plot"))
    win._mapping_widgets["x"].setCurrentText("treatment")
    win._mapping_widgets["y"].setCurrentText("quantity per bee")
    win.render_preview()
    grab(win, "06_raw_values_linear_axis.png")
    win._style_box.setChecked(True)
    w = win._axis_scale_widgets["y"]
    w["scale"].setCurrentIndex(w["scale"].findData("log10"))
    w["fmt"].setCurrentIndex(w["fmt"].findData("plain"))
    win.render_preview()
    win._axis_scale_group.setFocus()
    grab(win, "07_raw_values_on_log10_axis.png")

    # 8. a replicated three-way design that IS estimable
    dlg = apply_dialog(win, lambda d: d.tabs.setCurrentIndex(0))
    dlg.resize(1100, 860)
    dlg.tabs.setCurrentIndex(1)
    dlg.tf_column.setCurrentText("quantity per bee")
    dlg.tf_method.setCurrentIndex(dlg.tf_method.findData("log10"))
    dlg._add_transform()
    dlg.tabs.setCurrentIndex(2)
    dlg.an_response.setCurrentText("log10(quantity per bee)")
    for i, f in enumerate(("treatment", "social setting", "time (day)")):
        dlg.an_factors[i].setCurrentText(f)
    dlg.an_subject.setCurrentText("colony id")
    dlg._run()
    grab(dlg, "08_three_way_anova_replicated_design.png")
    dlg.result_tabs.setCurrentIndex(1)
    grab(dlg, "08b_coefficients.png")
    dlg.close()

    # 9. save and reopen a Figure Package of the derived table. Back to a linear
    # axis first: a log axis over the log10 column would be a double log, which the
    # app refuses (and says so in Messages).
    w["scale"].setCurrentIndex(0)
    w["fmt"].setCurrentIndex(0)
    dlg = TableWorkflowDialog(win.controller, win.data, win)
    dlg.tf_column.setCurrentText("quantity per bee")
    dlg.tf_method.setCurrentIndex(dlg.tf_method.findData("log10"))
    dlg._add_transform()
    dlg._apply()
    win._set_data(dlg.result_data)
    win._mapping_widgets["x"].setCurrentText("treatment")
    win._mapping_widgets["y"].setCurrentText("log10(quantity per bee)")
    win.render_preview()
    content = win.controller.package_content(win.data, win._current_spec, win._current_result,
                                             matrix=win._matrix_context(), name="tutorial")
    pkg = os.path.join(tempfile.mkdtemp(), "tutorial.mmfpackage")
    with open(pkg, "wb") as fh:
        fh.write(win.controller.package_bytes(content))
    win2 = MainWindow()
    win2.resize(1500, 950)
    win2.show()
    win2.load_path(pkg)
    grab(win2, "09_reopened_figure_package.png")
    win2.close()

    # 10-11. facet grids on the mock plant-growth design (2 species x 2 ages x 3 N x 4 months)
    win.load_path(os.path.join(HERE, "data", "mock_plant_growth.csv"))
    win.plot_combo.setCurrentIndex(win.plot_combo.findData("boxplot_or_violin_with_points"))
    for f, col in (("x", "Month"), ("y", "Growth_cm"), ("hue", "Nitrogen_Concentration"),
                   ("facet_row", "Age"), ("facet_col", "Species")):
        win._mapping_widgets[f].setCurrentText(col)
    win.title_edit.setText("Distribution of Plant Growth Over Time")
    win.ylabel_edit.setText("Growth (cm)")
    win._style_box.setChecked(True)
    win.cmb_legloc.setCurrentText("outside bottom")
    win.render_preview()
    grab(win, "10_faceted_boxplot.png")
    win.plot_combo.setCurrentIndex(win.plot_combo.findData("lineplot_timecourse_with_error_band"))
    for f, col in (("x", "Month"), ("y", "Growth_cm"), ("color", "Nitrogen_Concentration"),
                   ("facet_row", "Age"), ("facet_col", "Species")):
        win._mapping_widgets[f].setCurrentText(col)
    win._option_widgets["error_display"].setCurrentText("bars")
    win.title_edit.setText("Plant Growth Trajectory Over Time")
    win.ylabel_edit.setText("Mean Growth (cm) ± SE")
    win.xlabel_edit.setText("Time (Months)")
    win.render_preview()
    grab(win, "11_faceted_lineplot.png")
    win.close()
    app.processEvents()


if __name__ == "__main__":
    main()
