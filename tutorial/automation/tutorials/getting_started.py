"""Getting started: start screen, menus, Help, example data, the main layout."""
TITLE = "Getting started with the desktop application"
DATASETS = []


def run(drv, ctx):
    from PySide6.QtWidgets import QDialog, QMenu, QPushButton, QTabWidget

    win = drv.win
    ctx.fact("window_title", win.windowTitle())
    ctx.fact("start_buttons", [b.text() for b in win.stack.widget(0).findChildren(QPushButton)])
    ctx.fact("menus", [a.text() for a in win.menuBar().actions()])
    for a in win.menuBar().actions():
        m = a.menu()
        if m is not None:
            ctx.fact(f"menu_{a.text().replace('&', '')}", [x.text() for x in m.actions() if x.text()])
    drv.capture("01_start_screen", "window", "start screen")

    # File menu, opened for real
    file_menu = [m for m in win.menuBar().findChildren(QMenu) if m.title().replace("&", "") == "File"][0]
    file_menu.move(win.mapToGlobal(win.rect().topLeft()))
    file_menu.show()
    drv.pump(15)
    drv._grab_widget(file_menu, "02_file_menu", "File menu")
    file_menu.hide()

    # Help dialog (tabs) - opened for real, grabbed, closed
    orig = QDialog.exec

    def _exec(dlg, *a, **k):
        dlg.show(); drv.pump(20)
        tabs = dlg.findChildren(QTabWidget)
        ctx.fact("help_tabs", [tabs[0].tabText(i) for i in range(tabs[0].count())] if tabs else [])
        drv._grab_widget(dlg, "03_help_dialog", "Help dialog")
        dlg.hide()
        return QDialog.Rejected

    QDialog.exec = _exec
    try:
        win.action_help()
    finally:
        QDialog.exec = orig

    # Example data: the app's own bundled example for the box / violin plot
    drv.open_example("boxplot_or_violin_with_points")
    ctx.fact("status_after_example", win.statusBar().currentMessage())
    ctx.fact("example_columns", drv.columns())
    ctx.fact("group_boxes", drv.group_titles())
    ctx.fact("right_tabs", [win.right_tabs.tabText(i) for i in range(win.right_tabs.count())])
    drv.capture("04_workspace", "window", "main layout with example data")
    drv.capture("05_controls_full", "controls_full", "the whole control column, top to bottom")
    win.right_tabs.setCurrentIndex(1)
    drv.pump(10)
    drv.capture("06_messages_tab", "window", "Messages tab")
    win.right_tabs.setCurrentIndex(0)
    drv.write_log()
