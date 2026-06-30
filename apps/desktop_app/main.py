"""Make My Figure — desktop GUI (PySide6).

Zero-command app for non-technical scientists: open a data file, pick a plot
type and journal-like style, map columns, preview, and export SVG/PNG/PDF/
PlotSpec JSON (or a ZIP of all). Runs fully locally; no telemetry.

The GUI is intentionally thin — all plotting/validation/export lives in
``make_my_figure_core`` and ``apps.desktop_app.controller``.
"""

from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")  # figures are created headless, then embedded in a Qt canvas

# Make the repo importable when run from source (frozen apps bundle the package).
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from apps.desktop_app import help_content
from apps.desktop_app.controller import DesktopController, LoadedData
from make_my_figure_core.io.loaders import LoaderError
from make_my_figure_core.plots.base import RenderError
from make_my_figure_core.spec.validate import SpecValidationError

APP_NAME = "Make My Figure"
ORG_NAME = "MakeMyFigure"
ICON_PATH = os.path.join(_REPO_ROOT, "assets", "icons", "icon.png")
MAX_RECENT = 8


# ---------------------------------------------------------------------------
# Help dialog
# ---------------------------------------------------------------------------
class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Help")
        self.resize(640, 560)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Plot types tab
        browser = QTextBrowser()
        html = ["<h2>Supported plot types</h2>"]
        for e in help_content.plot_help():
            req = ", ".join(e["required_columns"]) or "—"
            opt = ", ".join(e["optional_columns"]) or "—"
            html.append(
                f"<h3>{e['title']}</h3>"
                f"<p>{e['description']}</p>"
                f"<p><b>Required columns:</b> {req}<br>"
                f"<b>Optional columns:</b> {opt}<br>"
                f"<b>Example file:</b> {e['example_file']}</p>"
                f"<p><i>{e['replacement_note']}</i></p><hr>"
            )
        browser.setHtml("".join(html))
        tabs.addTab(browser, "Plot types")

        fmt = QTextBrowser()
        fmt.setPlainText(help_content.FORMATTING)
        tabs.addTab(fmt, "Format your data")

        priv = QTextBrowser()
        priv.setPlainText(help_content.PRIVACY)
        tabs.addTab(priv, "Privacy")

        disc = QTextBrowser()
        disc.setPlainText(help_content.DISCLAIMER)
        tabs.addTab(disc, "Journal-like disclaimer")

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self, controller: DesktopController | None = None):
        super().__init__()
        self.controller = controller or DesktopController()
        self.settings = QSettings(ORG_NAME, APP_NAME)
        self.data: LoadedData | None = None
        self._mapping_widgets: dict[str, QComboBox] = {}
        self._option_widgets: dict[str, QWidget] = {}
        self._current_result = None
        self._current_spec = None
        self._canvas = None
        self._toolbar = None

        self.setWindowTitle(APP_NAME)
        self.resize(1180, 760)
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        self.setAcceptDrops(True)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.stack.addWidget(self._build_welcome())   # index 0
        self.stack.addWidget(self._build_workbench())  # index 1

        self._build_menu()
        self.statusBar().showMessage("Runs locally — your data never leaves this computer.")

    # --- welcome page ----------------------------------------------------
    def _build_welcome(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.addStretch(1)
        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 30px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Create publication-style scientific figures from your data")
        subtitle.setStyleSheet("font-size: 15px; color: #555;")
        subtitle.setAlignment(Qt.AlignCenter)
        v.addWidget(title)
        v.addWidget(subtitle)
        v.addSpacing(24)

        row = QHBoxLayout()
        row.addStretch(1)
        for label, slot in [
            ("Open data file", self.action_open_file),
            ("Use example data", self.action_open_example_dialog),
            ("Recent files", self.action_recent_dialog),
            ("Help", self.action_help),
        ]:
            b = QPushButton(label)
            b.setMinimumSize(150, 44)
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)

        note = QLabel(help_content.PRIVACY)
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignCenter)
        note.setStyleSheet("color: #777; font-size: 11px;")
        v.addSpacing(20)
        v.addWidget(note)
        v.addStretch(2)
        return page

    # --- workbench page --------------------------------------------------
    def _build_workbench(self) -> QWidget:
        splitter = QSplitter(Qt.Horizontal)

        # Left: controls in a scroll area
        controls = QWidget()
        cv = QVBoxLayout(controls)

        self.plot_combo = QComboBox()
        for pt, label in self.controller.plot_types():
            self.plot_combo.addItem(label, pt)
        self.plot_combo.currentIndexChanged.connect(self._on_plot_type_changed)

        self.style_combo = QComboBox()
        for s, label in self.controller.styles():
            self.style_combo.addItem(label, s)

        type_box = QGroupBox("1. Plot type & style")
        tb = QFormLayout(type_box)
        tb.addRow("Plot type", self.plot_combo)
        tb.addRow("Style profile", self.style_combo)
        cv.addWidget(type_box)

        self.mapping_box = QGroupBox("2. Map columns")
        self.mapping_form = QFormLayout(self.mapping_box)
        cv.addWidget(self.mapping_box)

        self.options_box = QGroupBox("3. Options")
        self.options_form = QFormLayout(self.options_box)
        cv.addWidget(self.options_box)

        labels_box = QGroupBox("4. Labels & size")
        lb = QFormLayout(labels_box)
        self.title_edit = QLineEdit()
        self.xlabel_edit = QLineEdit()
        self.ylabel_edit = QLineEdit()
        self.width_combo = QComboBox()
        self.width_combo.addItems(["single", "double"])
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setValue(300)
        lb.addRow("Title", self.title_edit)
        lb.addRow("X label", self.xlabel_edit)
        lb.addRow("Y label", self.ylabel_edit)
        lb.addRow("Width", self.width_combo)
        lb.addRow("Raster DPI", self.dpi_spin)
        cv.addWidget(labels_box)

        self.preview_btn = QPushButton("Update preview")
        self.preview_btn.clicked.connect(self.render_preview)
        cv.addWidget(self.preview_btn)

        export_box = QGroupBox("5. Export")
        eb = QVBoxLayout(export_box)
        for label, fmt in [("Export SVG", "svg"), ("Export PNG", "png"),
                           ("Export PDF", "pdf"), ("Export PlotSpec JSON", "json")]:
            b = QPushButton(label)
            b.clicked.connect(lambda _=False, f=fmt: self.export_single(f))
            eb.addWidget(b)
        zip_btn = QPushButton("Export all as ZIP")
        zip_btn.clicked.connect(self.export_zip)
        eb.addWidget(zip_btn)
        tmpl_btn = QPushButton("Save template (example table)")
        tmpl_btn.clicked.connect(self.action_save_template)
        eb.addWidget(tmpl_btn)
        cv.addWidget(export_box)
        cv.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(controls)
        scroll.setMinimumWidth(360)
        scroll.setMaximumWidth(440)
        splitter.addWidget(scroll)

        # Right: preview tabs
        right = QTabWidget()
        # data tab
        data_tab = QWidget()
        dv = QVBoxLayout(data_tab)
        self.table_widget = QTableWidget()
        self.dtype_label = QLabel("No data loaded.")
        self.dtype_label.setWordWrap(True)
        dv.addWidget(self.table_widget)
        dv.addWidget(self.dtype_label)
        right.addTab(data_tab, "Data preview")
        # figure tab
        fig_tab = QWidget()
        self.fig_layout = QVBoxLayout(fig_tab)
        self.warn_label = QLabel("")
        self.warn_label.setWordWrap(True)
        self.warn_label.setStyleSheet("color: #b00;")
        self.fig_layout.addWidget(self.warn_label)
        self.fig_placeholder = QLabel("Load data, then click “Update preview”.")
        self.fig_placeholder.setAlignment(Qt.AlignCenter)
        self.fig_layout.addWidget(self.fig_placeholder)
        right.addTab(fig_tab, "Figure preview")
        self.right_tabs = right
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([400, 780])
        return splitter

    # --- menu ------------------------------------------------------------
    def _build_menu(self) -> None:
        m = self.menuBar()
        filem = m.addMenu("&File")
        a_open = QAction("Open data file…", self)
        a_open.triggered.connect(self.action_open_file)
        filem.addAction(a_open)

        ex_menu = filem.addMenu("Open example")
        for pt, label in self.controller.plot_types():
            act = QAction(label, self)
            act.triggered.connect(lambda _=False, p=pt: self.load_example(p))
            ex_menu.addAction(act)

        self.recent_menu = filem.addMenu("Recent files")
        self._refresh_recent_menu()

        a_tmpl = QAction("Save template…", self)
        a_tmpl.triggered.connect(self.action_save_template)
        filem.addAction(a_tmpl)
        filem.addSeparator()
        a_quit = QAction("Quit", self)
        a_quit.triggered.connect(self.close)
        filem.addAction(a_quit)

        helpm = m.addMenu("&Help")
        a_help = QAction("Help…", self)
        a_help.triggered.connect(self.action_help)
        helpm.addAction(a_help)
        a_about = QAction("About", self)
        a_about.triggered.connect(self.action_about)
        helpm.addAction(a_about)

    # --- drag & drop -----------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.load_path(urls[0].toLocalFile())

    # --- actions ---------------------------------------------------------
    def action_open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open data file", "",
            "Data files (*.csv *.tsv *.txt *.xlsx *.xls);;All files (*)")
        if path:
            self.load_path(path)

    def action_open_example_dialog(self):
        items = [label for _, label in self.controller.plot_types()]
        from PySide6.QtWidgets import QInputDialog

        label, ok = QInputDialog.getItem(self, "Use example data",
                                         "Choose an example dataset:", items, 0, False)
        if ok and label:
            for pt, lab in self.controller.plot_types():
                if lab == label:
                    self.load_example(pt)
                    break

    def action_recent_dialog(self):
        recents = self._recent_files()
        if not recents:
            QMessageBox.information(self, "Recent files", "No recent files yet.")
            return
        from PySide6.QtWidgets import QInputDialog

        path, ok = QInputDialog.getItem(self, "Recent files", "Open:", recents, 0, False)
        if ok and path:
            self.load_path(path)

    def action_help(self):
        HelpDialog(self).exec()

    def action_about(self):
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<h3>{APP_NAME}</h3>"
            f"<p>Version {self.controller.version}</p>"
            "<p>Author: Make My Figure contributors (placeholder)</p>"
            "<p>License: MIT (placeholder)</p>"
            "<p>Website: https://example.com/make-my-figure (placeholder)</p>"
            "<p>Create publication-style scientific figures from your data — "
            "entirely on your computer.</p>"
            f"<p style='color:#777'>{help_content.DISCLAIMER}</p>")

    def action_save_template(self):
        pt = self.plot_combo.currentData()
        suggested = (self.controller.example_source_path(pt) or "template.csv")
        ext = os.path.splitext(suggested)[1] or ".csv"
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save template table", f"{pt}_template{ext}",
            "Data files (*.csv *.tsv);;All files (*)")
        if not dest:
            return
        try:
            self.controller.save_template(pt, dest)
            QMessageBox.information(self, "Template saved",
                                    f"Example table saved to:\n{dest}\n\n"
                                    "Replace the rows with your own data, keeping the column names.")
        except Exception as exc:
            QMessageBox.warning(self, "Could not save template", str(exc))

    # --- loading ---------------------------------------------------------
    def load_path(self, path: str):
        try:
            data = self.controller.load_file(path)
        except LoaderError as exc:
            QMessageBox.warning(self, "Could not load file",
                                f"{exc}\n\nSupported formats: .xlsx, .csv, .tsv.")
            return
        except Exception as exc:
            QMessageBox.critical(self, "Unexpected error", str(exc))
            return
        self._add_recent(path)
        self._set_data(data)

    def load_example(self, plot_type: str):
        try:
            data = self.controller.load_example(plot_type)
        except Exception as exc:
            QMessageBox.warning(self, "Could not load example", str(exc))
            return
        # Switch the plot type to match the example.
        idx = self.plot_combo.findData(plot_type)
        if idx >= 0:
            self.plot_combo.setCurrentIndex(idx)
        self._set_data(data)

    def _set_data(self, data: LoadedData):
        self.data = data
        self.stack.setCurrentIndex(1)
        self._populate_table()
        self._rebuild_mapping_and_options()
        self.statusBar().showMessage(f"Loaded {data.table_name} — runs locally.")
        self.render_preview()

    def _populate_table(self):
        df = self.data.info.dataframe
        head = df.head(50)
        self.table_widget.clear()
        self.table_widget.setColumnCount(len(head.columns))
        self.table_widget.setRowCount(len(head))
        self.table_widget.setHorizontalHeaderLabels([str(c) for c in head.columns])
        for r in range(len(head)):
            for c in range(len(head.columns)):
                self.table_widget.setItem(r, c, QTableWidgetItem(str(head.iat[r, c])))
        info = self.data.info
        dtypes = ", ".join(f"{c} ({'num' if c in info.numeric_columns else 'text'})"
                           for c in info.columns)
        warns = (" | ".join(info.warnings)) if info.warnings else "none"
        self.dtype_label.setText(
            f"{info.n_rows} rows × {len(info.columns)} columns.\n"
            f"Detected types: {dtypes}\nWarnings: {warns}")

    # --- dynamic controls ------------------------------------------------
    def _clear_form(self, form: QFormLayout):
        while form.rowCount():
            form.removeRow(0)

    def _column_options(self) -> list[str]:
        cols = list(self.data.info.columns) if self.data else []
        return ["(none)"] + cols

    def _metadata_options(self) -> list[str]:
        if self.data and "metadata" in self.data.aux:
            return ["(none)"] + list(self.data.aux["metadata"].columns)
        return ["(none)"]

    def _rebuild_mapping_and_options(self):
        pt = self.plot_combo.currentData()
        defaults = self.controller.default_mapping(pt)
        self._clear_form(self.mapping_form)
        self._mapping_widgets = {}
        col_opts = self._column_options()
        for field in self.controller.column_fields(pt):
            combo = QComboBox()
            combo.addItems(col_opts)
            default = defaults.get(field)
            if default in col_opts:
                combo.setCurrentText(default)
            combo.currentIndexChanged.connect(self.render_preview)
            self.mapping_form.addRow(field, combo)
            self._mapping_widgets[field] = combo
        # PCA metadata-based fields (color/shape)
        if self.controller.needs_metadata(pt):
            meta_opts = self._metadata_options()
            for field in self.controller.pca_metadata_fields():
                combo = QComboBox()
                combo.addItems(meta_opts)
                default = defaults.get(field)
                if default in meta_opts:
                    combo.setCurrentText(default)
                combo.currentIndexChanged.connect(self.render_preview)
                self.mapping_form.addRow(f"{field} (metadata)", combo)
                self._mapping_widgets[field] = combo

        # options
        self._clear_form(self.options_form)
        self._option_widgets = {}
        for opt in self.controller.options(pt):
            w = self._make_option_widget(opt)
            self.options_form.addRow(opt.label, w)
            self._option_widgets[opt.key] = w

    def _make_option_widget(self, opt) -> QWidget:
        if opt.kind == "bool":
            w = QCheckBox()
            w.setChecked(bool(opt.default))
            w.stateChanged.connect(self.render_preview)
            return w
        if opt.kind == "choice":
            w = QComboBox()
            w.addItems([str(c) for c in (opt.choices or [])])
            if opt.default is not None:
                w.setCurrentText(str(opt.default))
            w.currentIndexChanged.connect(self.render_preview)
            return w
        # number
        if opt.decimals and opt.decimals > 0:
            w = QDoubleSpinBox()
            w.setDecimals(opt.decimals)
        else:
            w = QSpinBox()
        if opt.minimum is not None:
            w.setMinimum(opt.minimum)
        if opt.maximum is not None:
            w.setMaximum(opt.maximum)
        if opt.step is not None:
            w.setSingleStep(opt.step)
        if opt.default is not None:
            w.setValue(opt.default)
        w.valueChanged.connect(self.render_preview)
        return w

    def _collect_mapping(self) -> dict:
        mapping = {}
        for key, combo in self._mapping_widgets.items():
            val = combo.currentText()
            mapping[key] = None if val == "(none)" else val
        for key, w in self._option_widgets.items():
            if isinstance(w, QCheckBox):
                mapping[key] = w.isChecked()
            elif isinstance(w, QComboBox):
                mapping[key] = w.currentText()
            elif isinstance(w, (QSpinBox, QDoubleSpinBox)):
                mapping[key] = w.value()
        return mapping

    def _on_plot_type_changed(self):
        if self.data is not None:
            self._rebuild_mapping_and_options()
            self.render_preview()

    # --- render ----------------------------------------------------------
    def _build_spec(self):
        pt = self.plot_combo.currentData()
        style = self.style_combo.currentData()
        layout = {}
        if self.title_edit.text().strip():
            layout["title"] = self.title_edit.text().strip()
        if self.xlabel_edit.text().strip():
            layout["x_label"] = self.xlabel_edit.text().strip()
        if self.ylabel_edit.text().strip():
            layout["y_label"] = self.ylabel_edit.text().strip()
        return self.controller.build_spec(
            pt, style, self.data.table_name, self._collect_mapping(),
            layout=layout, width=self.width_combo.currentText(), dpi=self.dpi_spin.value())

    def render_preview(self):
        if self.data is None:
            return
        try:
            spec = self._build_spec()
            result = self.controller.render(spec, self.data)
        except (RenderError, SpecValidationError) as exc:
            self._show_warning(str(exc))
            return
        except Exception as exc:
            self._show_warning(f"Unexpected error: {exc}")
            return
        self._current_spec = spec
        self._current_result = result
        warns = result.warnings or []
        self.warn_label.setText(("⚠ " + " | ".join(warns)) if warns else "")
        self._show_figure(result.figure)
        self.right_tabs.setCurrentIndex(1)

    def _show_warning(self, msg: str):
        self.warn_label.setText("⚠ " + msg)
        self.right_tabs.setCurrentIndex(1)

    def _show_figure(self, fig):
        # Remove old canvas/toolbar and release the previous figure to avoid leaks.
        if self._canvas is not None:
            old_fig = self._canvas.figure
            self._canvas.setParent(None)
            self._canvas = None
            if old_fig is not None and old_fig is not fig:
                import matplotlib.pyplot as plt

                plt.close(old_fig)
        if self._toolbar is not None:
            self._toolbar.setParent(None)
            self._toolbar = None
        if self.fig_placeholder is not None:
            self.fig_placeholder.setParent(None)
            self.fig_placeholder = None
        canvas = FigureCanvasQTAgg(fig)
        toolbar = NavigationToolbar2QT(canvas, self)
        self.fig_layout.addWidget(toolbar)
        self.fig_layout.addWidget(canvas)
        canvas.draw()
        self._canvas = canvas
        self._toolbar = toolbar

    # --- export ----------------------------------------------------------
    def _ensure_rendered(self) -> bool:
        if self._current_result is None:
            self.render_preview()
        if self._current_result is None:
            QMessageBox.warning(self, "Nothing to export", "Load data and preview a figure first.")
            return False
        return True

    def export_single(self, fmt: str):
        if not self._ensure_rendered():
            return
        pt = self.plot_combo.currentData()
        if fmt == "json":
            dest, _ = QFileDialog.getSaveFileName(self, "Export PlotSpec JSON",
                                                  f"{pt}.plot_spec.json", "JSON (*.json)")
            if not dest:
                return
            import json

            sidecar = {"plot_spec": self._current_spec,
                       "render_metadata": {k: v for k, v in self._current_result.metadata.items()
                                           if k != "spec"}}
            with open(dest, "w", encoding="utf-8") as fh:
                json.dump(sidecar, fh, indent=2)
            self.statusBar().showMessage(f"Saved {dest}")
            return
        dest, _ = QFileDialog.getSaveFileName(self, f"Export {fmt.upper()}",
                                              f"{pt}.{fmt}", f"{fmt.upper()} (*.{fmt})")
        if not dest:
            return
        base = os.path.splitext(dest)[0]
        try:
            from make_my_figure_core.plots.registry import export_figure

            export_figure(self._current_result.figure, base, [fmt], dpi=self.dpi_spin.value())
            self.statusBar().showMessage(f"Saved {base}.{fmt}")
        except Exception as exc:
            QMessageBox.warning(self, "Export failed", str(exc))

    def export_zip(self):
        if not self._ensure_rendered():
            return
        pt = self.plot_combo.currentData()
        dest, _ = QFileDialog.getSaveFileName(self, "Export all as ZIP",
                                              f"{pt}_figure_bundle.zip", "ZIP (*.zip)")
        if not dest:
            return
        try:
            data = self.controller.export_bundle(
                self._current_spec, self._current_result,
                ["svg", "png", "pdf"], dpi=self.dpi_spin.value(), basename=pt)
            with open(dest, "wb") as fh:
                fh.write(data)
            self.statusBar().showMessage(f"Saved bundle {dest}")
        except Exception as exc:
            QMessageBox.warning(self, "Export failed", str(exc))

    # --- recent files ----------------------------------------------------
    def _recent_files(self) -> list[str]:
        vals = self.settings.value("recent_files", [])
        if isinstance(vals, str):
            vals = [vals]
        return [p for p in (vals or []) if p and os.path.exists(p)]

    def _add_recent(self, path: str):
        recents = self._recent_files()
        if path in recents:
            recents.remove(path)
        recents.insert(0, path)
        self.settings.setValue("recent_files", recents[:MAX_RECENT])
        self._refresh_recent_menu()

    def _refresh_recent_menu(self):
        if not hasattr(self, "recent_menu"):
            return
        self.recent_menu.clear()
        recents = self._recent_files()
        if not recents:
            act = QAction("(none)", self)
            act.setEnabled(False)
            self.recent_menu.addAction(act)
            return
        for p in recents:
            act = QAction(p, self)
            act.triggered.connect(lambda _=False, path=p: self.load_path(path))
            self.recent_menu.addAction(act)


def _selftest() -> int:
    """Headless self-check used by packaging smoke tests and frozen builds.

    Loads an example, renders it, and exports a ZIP to a temp dir. Returns 0 on
    success. Run with: ``MakeMyFigure --selftest``.
    """
    import tempfile

    ctrl = DesktopController()
    failures = []
    tmp = tempfile.mkdtemp(prefix="mmf_selftest_")
    from make_my_figure_core.plots.registry import available_plot_types

    for pt in available_plot_types():
        try:
            data = ctrl.load_example(pt)
            spec = ctrl.build_spec(pt, "nature_like", data.table_name, ctrl.default_mapping(pt))
            result = ctrl.render(spec, data)
            blob = ctrl.export_bundle(spec, result, ["svg", "png", "pdf"], basename=pt)
            assert blob and len(blob) > 300
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{pt}: {exc}")
    if failures:
        sys.stderr.write("SELFTEST FAILURES:\n" + "\n".join(failures) + "\n")
        return 1
    sys.stdout.write(f"SELFTEST OK: {len(available_plot_types())} plot types rendered + exported.\n")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
