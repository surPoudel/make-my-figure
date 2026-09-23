"""Pilot: multi-panel figure with the Figure Builder (two panels from two datasets)."""
TITLE = "Figure Builder: a two-panel composite"
DATASETS = ["group_comparison.csv", "relationship_data.csv"]


def run(drv, ctx):
    from PySide6.QtWidgets import QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit
    drv.open_file(ctx.dataset("group_comparison.csv"))
    drv.select_plot("boxplot_or_violin_with_points")
    drv.set_mapping("x", "group"); drv.set_mapping("y", "response")
    drv.set_labels(title="Response by group", ylabel="Response (a.u.)")
    drv.update_preview()
    ctx.fact("multipanel_buttons", [b.text() for b in drv._target_widget("multipanel").findChildren(drv.M.QPushButton)])
    drv.scroll_to("multipanel")
    drv.capture("01_multipanel_group", "multipanel", "6. Multi-panel figure group")
    n = drv.save_panel()
    ctx.fact("panel_count_label_after_first", drv.win.panel_count_label.text())
    drv.open_file(ctx.dataset("relationship_data.csv"))
    drv.select_plot("scatterplot_with_regression")
    drv.set_mapping("x", "expression_a"); drv.set_mapping("y", "expression_b"); drv.set_mapping("color", "cell_line")
    drv.set_labels(title="Expression A vs B")
    drv.update_preview()
    n = drv.save_panel()
    ctx.fact("panel_count_label_after_second", drv.win.panel_count_label.text())
    drv.capture("02_two_panels_saved", "multipanel")

    facts = {}

    def inspect(dlg):
        facts["form_rows"] = [l.text() for l in dlg.findChildren(drv.M.QLabel) if l.text().endswith((":",)) or l.text() in
                              ("Figure name", "Columns", "Rows", "Figure width", "Horizontal gutter", "Vertical gutter",
                               "Panel labels", "Export DPI", "Width", "Height")]
        combos = {c.objectName() or i: [c.itemText(k) for k in range(c.count())] for i, c in enumerate(dlg.findChildren(QComboBox))}
        facts["combo_choices"] = {str(k): v for k, v in combos.items() if v}
        facts["buttons"] = [b.text() for b in dlg.findChildren(drv.M.QPushButton)]
        facts["groupboxes"] = [g.title() for g in dlg.findChildren(drv.M.QGroupBox)]
        lst = dlg.findChildren(drv.M.QListWidget)
        if lst:
            facts["panel_list"] = [lst[0].item(i).text() for i in range(lst[0].count())]
        # two columns, one row
        for sp in dlg.findChildren(QSpinBox):
            pass

    res = drv.figure_builder(actions=inspect, capture_name="03_figure_builder",
                             save_figure=ctx.out("composite.png"), save_package=ctx.out("composite.mmfpackage"))
    for k, v in facts.items():
        ctx.fact(f"builder_{k}", v)
    ctx.fact("builder_result", res)
    drv.write_log()
