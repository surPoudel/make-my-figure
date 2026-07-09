"""Make My Figure — desktop GUI (PySide6).

Zero-command app for non-technical scientists: open a data file, pick a plot
type and journal-like style, map columns, preview, and export SVG/PNG/PDF/
PlotSpec JSON (or a ZIP of all). Runs fully locally; no telemetry.

The GUI is intentionally thin — all plotting/validation/export lives in
``make_my_figure_core`` and ``apps.desktop_app.controller``.
"""

from __future__ import annotations

import os
import subprocess
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
    QSizePolicy,
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
from make_my_figure_core.plots.registry import display_name
from make_my_figure_core.spec.validate import SpecValidationError
from make_my_figure_core.styles.engine import NAMED_PALETTES

APP_NAME = "Make My Figure"
ORG_NAME = "MakeMyFigure"
ICON_PATH = os.path.join(_REPO_ROOT, "assets", "icons", "icon.png")
MAX_RECENT = 8


def _git_commit() -> str:
    """Return the short git commit of the loaded source, or 'unknown'."""
    try:
        out = subprocess.run(
            ["git", "-C", _REPO_ROOT, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5)
        if out.returncode == 0:
            commit = out.stdout.strip()
            dirty = subprocess.run(
                ["git", "-C", _REPO_ROOT, "status", "--porcelain"],
                capture_output=True, text=True, timeout=5)
            if dirty.returncode == 0 and dirty.stdout.strip():
                commit += "+dirty"
            return commit or "unknown"
    except Exception:
        pass
    return "unknown"


def _on_cloud_folder() -> bool:
    """Heuristic: is the source under a cloud-sync folder (OneDrive/iCloud/Dropbox)?"""
    p = _REPO_ROOT.lower()
    return any(s in p for s in ("onedrive", "icloud", "dropbox", "google drive", "com~apple~clouddocs"))


def debug_info() -> dict:
    """Diagnostic facts to confirm exactly which source is running."""
    import make_my_figure_core
    from make_my_figure_core.version import __version__

    return {
        "app_version": __version__,
        "git_commit": _git_commit(),
        "desktop_app_file": os.path.abspath(__file__),
        "core_package_path": os.path.dirname(os.path.abspath(make_my_figure_core.__file__)),
        "repo_root": _REPO_ROOT,
        "current_working_dir": os.getcwd(),
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "matplotlib": matplotlib.__version__,
        "frozen": bool(getattr(sys, "frozen", False)),
        "cloud_synced_folder": _on_cloud_folder(),
    }


def debug_info_text() -> str:
    di = debug_info()
    lines = [f"{APP_NAME} — debug info", "-" * 32]
    lines += [f"{k}: {v}" for k, v in di.items()]
    if di["cloud_synced_folder"]:
        lines += ["", "WARNING: running from a cloud-synced folder (OneDrive/iCloud/Dropbox).",
                  "Stale/locked files are possible. Prefer a local clone, e.g. ~/Developer/make-my-figure."]
    return "\n".join(lines)


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
        self._rnaseq_state = None
        self._canvas = None
        self._toolbar = None
        self._suppress_change = False   # re-entrancy guard for plot-type changes
        self._debug = False             # set by --debug: verbose toolbar/canvas logging

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
        geom = self.settings.value("window_geometry")
        if geom is not None:
            self.restoreGeometry(geom)
        di = debug_info()
        msg = (f"v{di['app_version']} ({di['git_commit']}) — src: {di['desktop_app_file']} — "
               "runs locally, no data leaves this computer.")
        if di["cloud_synced_folder"]:
            msg = "⚠ cloud-synced source — " + msg
        self.statusBar().showMessage(msg)

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
        self.main_splitter = splitter = QSplitter(Qt.Horizontal)

        # Left: controls in a scroll area
        controls = QWidget()
        cv = QVBoxLayout(controls)

        # App-level navigation: return to the upload/welcome page without quitting.
        # (Distinct from the Matplotlib toolbar 'home', which only resets zoom/pan.)
        nav_row = QHBoxLayout()
        self.home_btn = QPushButton("\U0001F3E0  Home / Upload New Data")
        self.home_btn.setToolTip("Return to the upload page to load a different dataset "
                                 "(clears the current data, plot, and statistics).")
        self.home_btn.clicked.connect(self.action_home_upload)
        nav_row.addWidget(self.home_btn)
        self.rnaseq_btn = QPushButton("\U0001F9EC  RNA-seq…")
        self.rnaseq_btn.setToolTip("Open the RNA-seq workflow (DE volcano, heatmap, raw-count DE).")
        self.rnaseq_btn.clicked.connect(self.action_rnaseq)
        nav_row.addWidget(self.rnaseq_btn)
        cv.addLayout(nav_row)

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
        self.width_combo.addItems(["default", "single", "onehalf", "double"])
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setValue(300)
        lb.addRow("Title", self.title_edit)
        lb.addRow("X label", self.xlabel_edit)
        lb.addRow("Y label", self.ylabel_edit)
        lb.addRow("Figure width", self.width_combo)
        lb.addRow("Raster DPI", self.dpi_spin)
        cv.addWidget(labels_box)

        cv.addWidget(self._build_style_panel())

        # Statistics panel (statistical tests, annotations, method reporting).
        from apps.desktop_app.stats_panel import StatisticsPanel

        self.stats_panel = StatisticsPanel(self.controller)
        self.stats_panel.changed.connect(self.render_preview)
        self.stats_panel.runRequested.connect(self.render_preview)
        cv.addWidget(self.stats_panel)
        self._saved_panels: list = []

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

        panel_box = QGroupBox("6. Multi-panel figure")
        pb = QVBoxLayout(panel_box)
        save_panel_btn = QPushButton("Save current plot as panel")
        save_panel_btn.clicked.connect(self.action_save_panel)
        pb.addWidget(save_panel_btn)
        self.panel_count_label = QLabel("0 panels saved.")
        pb.addWidget(self.panel_count_label)
        fb_btn = QPushButton("Open Figure Builder…")
        fb_btn.clicked.connect(self.action_figure_builder)
        pb.addWidget(fb_btn)
        cv.addWidget(panel_box)
        cv.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(controls)
        scroll.setMinimumWidth(320)
        scroll.setMaximumWidth(480)
        splitter.addWidget(scroll)

        # Right: RStudio-like vertical splitter.
        #   top    = data / messages tabs
        #   bottom = LIVE matplotlib figure (toolbar + canvas), gets most space
        self.right_splitter = QSplitter(Qt.Vertical)

        self.right_tabs = QTabWidget()
        data_tab = QWidget()
        dv = QVBoxLayout(data_tab)
        self.table_widget = QTableWidget()
        self.dtype_label = QLabel("No data loaded.")
        self.dtype_label.setWordWrap(True)
        dv.addWidget(self.table_widget)
        dv.addWidget(self.dtype_label)
        self.right_tabs.addTab(data_tab, "Data preview")

        msg_tab = QWidget()
        mv = QVBoxLayout(msg_tab)
        self.warn_label = QLabel("Validation messages and warnings appear here.")
        self.warn_label.setWordWrap(True)
        self.warn_label.setStyleSheet("color: #b00;")
        mv.addWidget(self.warn_label)
        # Shown when uploaded data is incompatible with the selected plot type.
        self.example_prompt_btn = QPushButton("Use example data for this plot type")
        self.example_prompt_btn.setVisible(False)
        self.example_prompt_btn.clicked.connect(self._load_example_for_current_type)
        mv.addWidget(self.example_prompt_btn)
        mv.addStretch(1)
        self.right_tabs.addTab(msg_tab, "Messages")
        self.right_splitter.addWidget(self.right_tabs)

        # Bottom pane: the live figure container. The canvas (added on render)
        # has an Expanding size policy, so it grows/shrinks with the splitter
        # and the window automatically.
        self.fig_container = QWidget()
        self.fig_layout = QVBoxLayout(self.fig_container)
        self.fig_layout.setContentsMargins(2, 2, 2, 2)
        self.fig_placeholder = QLabel("Load data to see the live figure preview here.")
        self.fig_placeholder.setAlignment(Qt.AlignCenter)
        self.fig_layout.addWidget(self.fig_placeholder)
        self.right_splitter.addWidget(self.fig_container)

        self.right_tabs.setMinimumHeight(80)
        self.fig_container.setMinimumHeight(220)
        self.right_splitter.setStretchFactor(0, 0)   # tabs: keep small
        self.right_splitter.setStretchFactor(1, 1)   # figure: most of the space
        self.right_splitter.setSizes([220, 560])
        self.right_splitter.setOpaqueResize(True)

        splitter.addWidget(self.right_splitter)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([400, 820])
        splitter.setOpaqueResize(True)

        # Object names for inspection / debugging / widget-tree dumps.
        splitter.setObjectName("mainSplitter")
        self.right_splitter.setObjectName("rightSplitter")
        self.right_tabs.setObjectName("dataMessagesTabs")
        self.table_widget.setObjectName("dataPreviewTable")
        msg_tab.setObjectName("messagePanel")
        self.warn_label.setObjectName("validationMessageLabel")
        self.fig_container.setObjectName("figurePanel")
        scroll.setObjectName("controlPanel")
        # Restore persisted sizes first (restoreState resets handleWidth and
        # childrenCollapsible), THEN pin wide, non-collapsible handles so the
        # drag targets stay easy to grab across sessions.
        self._restore_splitter_state()
        for sp in (splitter, self.right_splitter):
            sp.setHandleWidth(10)
            sp.setChildrenCollapsible(False)
        return splitter

    # --- advanced style panel -------------------------------------------
    def _build_style_panel(self) -> QWidget:
        box = QGroupBox("5. Style (publication defaults)")
        box.setCheckable(True)
        box.setChecked(False)   # collapsed-ish: unchecked disables the controls
        form = QFormLayout(box)

        self.palette_combo = QComboBox()
        self.palette_combo.addItem("(profile default)", None)
        for name in NAMED_PALETTES:
            self.palette_combo.addItem(name, name)
        self.palette_combo.currentIndexChanged.connect(self.render_preview)

        def _spin(minv, maxv, val, step=1, dbl=False):
            w = QDoubleSpinBox() if dbl else QSpinBox()
            w.setRange(minv, maxv)
            w.setSingleStep(step)
            w.setValue(val)
            w.valueChanged.connect(self.render_preview)
            return w

        self.sp_axis = _spin(8, 28, 12)
        self.sp_tick = _spin(6, 24, 10)
        self.sp_legend = _spin(6, 24, 10)
        self.sp_annot = _spin(6, 24, 10)
        self.sp_marker = _spin(6, 300, 45)
        self.sp_linew = _spin(0.5, 6.0, 1.8, 0.1, dbl=True)
        self.sp_spine = _spin(0.4, 4.0, 1.1, 0.1, dbl=True)
        self.chk_legend_outside = QCheckBox()
        self.chk_legend_outside.stateChanged.connect(self.render_preview)
        self.chk_grid = QCheckBox()
        self.chk_grid.stateChanged.connect(self.render_preview)

        form.addRow("Palette", self.palette_combo)
        form.addRow("Axis label pt", self.sp_axis)
        form.addRow("Tick label pt", self.sp_tick)
        form.addRow("Legend pt", self.sp_legend)
        form.addRow("Annotation pt", self.sp_annot)
        form.addRow("Marker size", self.sp_marker)
        form.addRow("Line width", self.sp_linew)
        form.addRow("Axis/spine width", self.sp_spine)
        form.addRow("Legend outside", self.chk_legend_outside)
        form.addRow("Grid", self.chk_grid)

        reset = QPushButton("Reset to publication defaults")
        reset.clicked.connect(self.action_reset_style)
        form.addRow(reset)

        box.toggled.connect(lambda _=False: self.render_preview())
        self._style_box = box
        return box

    def _collect_style_overrides(self) -> dict:
        """Return spec['style'] overrides from the advanced panel (or {})."""
        if not getattr(self, "_style_box", None) or not self._style_box.isChecked():
            return {}
        ov = {
            "axis_font_pt": float(self.sp_axis.value()),
            "tick_label_pt": float(self.sp_tick.value()),
            "legend_pt": float(self.sp_legend.value()),
            "annotation_pt": float(self.sp_annot.value()),
            "marker_size": float(self.sp_marker.value()),
            "line_width_pt": float(self.sp_linew.value()),
            "regression_line_width": float(self.sp_linew.value()),
            "spine_width_pt": float(self.sp_spine.value()),
            "legend_outside": self.chk_legend_outside.isChecked(),
            "grid": self.chk_grid.isChecked(),
        }
        pal = self.palette_combo.currentData()
        if pal:
            ov["palette_name"] = pal
        return ov

    def action_reset_style(self):
        self.palette_combo.setCurrentIndex(0)
        self.sp_axis.setValue(12); self.sp_tick.setValue(10); self.sp_legend.setValue(10)
        self.sp_annot.setValue(10); self.sp_marker.setValue(45)
        self.sp_linew.setValue(1.8); self.sp_spine.setValue(1.1)
        self.chk_legend_outside.setChecked(False); self.chk_grid.setChecked(False)
        self.statusBar().showMessage("Style reset to publication defaults.", 4000)
        self.render_preview()

    # --- menu ------------------------------------------------------------
    def _build_menu(self) -> None:
        m = self.menuBar()
        filem = m.addMenu("&File")
        a_home = QAction("Home / Upload New Data", self)
        a_home.setShortcut("Ctrl+Shift+H")
        a_home.triggered.connect(self.action_home_upload)
        filem.addAction(a_home)
        filem.addSeparator()
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

        # View menu — layout controls.
        viewm = m.addMenu("&View")
        a_reset = QAction("Reset Layout", self)
        a_reset.triggered.connect(self.action_reset_layout)
        viewm.addAction(a_reset)
        a_maxfig = QAction("Maximize Figure Panel", self)
        a_maxfig.triggered.connect(self.action_maximize_figure)
        viewm.addAction(a_maxfig)
        self.a_show_data = QAction("Show Data Preview", self, checkable=True)
        self.a_show_data.setChecked(True)
        self.a_show_data.toggled.connect(self.action_toggle_data_preview)
        viewm.addAction(self.a_show_data)

        helpm = m.addMenu("&Help")
        a_help = QAction("Help…", self)
        a_help.triggered.connect(self.action_help)
        helpm.addAction(a_help)
        a_about = QAction(f"About {APP_NAME}", self)
        a_about.triggered.connect(self.action_about)
        helpm.addAction(a_about)
        a_dbg = QAction("Copy debug info", self)
        a_dbg.triggered.connect(self.action_copy_debug_info)
        helpm.addAction(a_dbg)
        a_tbdiag = QAction("Diagnose toolbar", self)
        a_tbdiag.triggered.connect(self.action_diagnose_toolbar)
        helpm.addAction(a_tbdiag)

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
        di = debug_info()
        rows = "".join(f"<tr><td style='color:#666'>{k}</td>"
                       f"<td><code>{v}</code></td></tr>" for k, v in di.items())
        cloud = ("<p style='color:#b00'><b>Note:</b> running from a cloud-synced folder "
                 "(OneDrive/iCloud/Dropbox). If changes don't seem to apply, run from a local "
                 "clone such as <code>~/Developer/make-my-figure</code>.</p>"
                 if di["cloud_synced_folder"] else "")
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<h3>{APP_NAME}</h3>"
            f"<p>Version {di['app_version']} (commit {di['git_commit']})</p>"
            "<p>Author: Make My Figure contributors (placeholder)</p>"
            "<p>License: MIT (placeholder)</p>"
            "<p>Website: https://example.com/make-my-figure (placeholder)</p>"
            "<p>Create publication-style scientific figures from your data — "
            "entirely on your computer.</p>"
            f"{cloud}"
            "<hr><b>Debug info</b> (Help → Copy debug info to copy):"
            f"<table>{rows}</table>"
            f"<p style='color:#777'>{help_content.DISCLAIMER}</p>")

    def action_copy_debug_info(self):
        text = debug_info_text()
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage("Debug info copied to clipboard.", 5000)

    def action_diagnose_toolbar(self):
        """Run a live toolbar self-test and show the result in the running app."""
        if self.data is None or self._current_result is None:
            self.load_example("lollipop_mutation_plot")
        state = self.diagnose_toolbar_state()
        test = self.run_toolbar_selftest()
        di = debug_info()

        def ok(v):
            return "✅" if v is True else ("❌" if v is False else f"⚠ {v}")

        functional = all(v is True for v in test.values()) if "error" not in test else False
        lines = [
            f"Toolbar functional: {'YES ✅' if functional else 'NO ❌'}",
            "",
            "Live self-test (what the buttons do):",
            f"  Home resets view: {ok(test.get('home_resets_view'))}",
            f"  Pan mode wired:   {ok(test.get('pan_mode_wired'))}",
            f"  Zoom mode wired:  {ok(test.get('zoom_mode_wired'))}",
            f"  Save writes file: {ok(test.get('save_writes_file'))}",
            "",
            "Wiring:",
            f"  canvas class: {state['canvas_class']} (QtAgg: {ok(state['canvas_is_qtagg'])})",
            f"  toolbar class: {state['toolbar_class']}",
            f"  toolbar.canvas is current canvas: {ok(state['toolbar_canvas_matches'])}",
            f"  canvas.figure is current figure: {ok(state['canvas_figure_matches_result'])}",
            f"  toolbar/canvas enabled: {ok(state['toolbar_enabled'])}/{ok(state['canvas_enabled'])}",
            f"  actions: {', '.join(a['name'] for a in state['actions'])}",
            "",
            "Running source (confirm this is your latest code):",
            f"  version {di['app_version']} commit {di['git_commit']}",
            f"  file: {di['desktop_app_file']}",
        ]
        if di["cloud_synced_folder"]:
            lines += ["", "⚠ This source is in a cloud-synced folder (OneDrive/iCloud/Dropbox).",
                      "  If the app shows old behavior, run from a local clone (see docs)."]
        QApplication.clipboard().setText("\n".join(lines))
        box = QMessageBox(self)
        box.setWindowTitle("Toolbar diagnostic")
        box.setText("\n".join(lines) + "\n\n(Copied to clipboard.)")
        box.exec()

    # --- View menu / layout actions --------------------------------------
    def action_reset_layout(self):
        self.main_splitter.setSizes([400, 820])
        self.right_splitter.setSizes([220, 560])
        if not self.a_show_data.isChecked():
            self.a_show_data.setChecked(True)   # also un-hides the data panel
        self.right_tabs.setVisible(True)
        for key in ("main_splitter_state", "right_splitter_state", "window_geometry"):
            self.settings.remove(key)
        self.statusBar().showMessage("Layout reset.", 4000)

    def action_maximize_figure(self):
        total = sum(self.right_splitter.sizes()) or 780
        self.right_splitter.setSizes([self.right_tabs.minimumHeight(), total])
        self.statusBar().showMessage("Figure panel maximized.", 4000)

    def action_toggle_data_preview(self, checked: bool):
        self.right_tabs.setVisible(checked)

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

    def action_save_panel(self):
        """Capture the current plot (spec + data) as a multi-panel builder panel."""
        if self.data is None or getattr(self, "_current_spec", None) is None:
            QMessageBox.information(self, "No plot", "Render a plot before saving it as a panel.")
            return
        import copy

        aux = {k: v.dataframe for k, v in self.data.aux.items()} if self.data.aux else {}
        title = self.title_edit.text().strip() or display_name(self.plot_combo.currentData())
        self._saved_panels.append({
            "plot_spec": copy.deepcopy(self._current_spec),
            "table": self.data.info.dataframe.copy(deep=True),
            "aux": aux,
            "title": title,
            "plot_type": self.plot_combo.currentData(),
        })
        self.panel_count_label.setText(f"{len(self._saved_panels)} panel(s) saved.")
        self.statusBar().showMessage(f"Saved panel '{title}'.", 4000)

    def action_figure_builder(self):
        from apps.desktop_app.stats_panel import FigureBuilderDialog

        dlg = FigureBuilderDialog(self.controller, self._saved_panels, self)
        dlg.exec()
        self.panel_count_label.setText(f"{len(self._saved_panels)} panel(s) saved.")

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
        # Switch the plot type to match the example (guard against re-entrancy so
        # setting the combo doesn't recursively re-trigger the change handler).
        prev = self._suppress_change
        self._suppress_change = True
        try:
            idx = self.plot_combo.findData(plot_type)
            if idx >= 0:
                self.plot_combo.setCurrentIndex(idx)
        finally:
            self._suppress_change = prev
        self._hide_example_prompt()
        self._set_data(data)
        self.statusBar().showMessage(f"Loaded {plot_type} example data — runs locally.")

    def _set_data(self, data: LoadedData):
        self.data = data
        self.stack.setCurrentIndex(1)
        self._populate_table()
        self._rebuild_mapping_and_options()
        self.statusBar().showMessage(f"Loaded {data.table_name} — runs locally.")
        self.render_preview()

    # --- app-level navigation: return to upload page ---------------------
    def _has_unsaved_work(self) -> bool:
        return self.data is not None and getattr(self, "_current_spec", None) is not None

    def action_home_upload(self):
        """Return to the upload/welcome page, clearing the session after an
        optional confirmation. Distinct from the Matplotlib toolbar 'home'."""
        if self._has_unsaved_work():
            box = QMessageBox(self)
            box.setWindowTitle("Return to upload page?")
            box.setIcon(QMessageBox.Question)
            box.setText("Return to the upload page and clear the current data?")
            box.setInformativeText("Your current dataset, plot, and statistics will be cleared.")
            save_btn = box.addButton("Save PlotSpec first…", QMessageBox.ActionRole)
            clear_btn = box.addButton("Clear and continue", QMessageBox.AcceptRole)
            cancel_btn = box.addButton("Cancel", QMessageBox.RejectRole)
            box.setDefaultButton(cancel_btn)
            box.exec()
            clicked = box.clickedButton()
            if clicked is cancel_btn:
                return
            if clicked is save_btn:
                if not self._save_plotspec_dialog():
                    return  # save cancelled -> abort navigation
        self.reset_to_upload()

    def _save_plotspec_dialog(self) -> bool:
        """Save the current PlotSpec JSON; returns True if written."""
        if getattr(self, "_current_spec", None) is None:
            return False
        import json

        pt = self.plot_combo.currentData()
        dest, _ = QFileDialog.getSaveFileName(self, "Save PlotSpec", f"{pt}.plot_spec.json",
                                              "PlotSpec JSON (*.json)")
        if not dest:
            return False
        with open(dest, "w", encoding="utf-8") as fh:
            json.dump(self._current_spec, fh, indent=2)
        self.statusBar().showMessage(f"Saved PlotSpec to {dest}", 5000)
        return True

    def reset_to_upload(self):
        """Clear the active session and show the upload/welcome page.

        Clears dataset, plot spec, render result, figure preview, statistics
        panel results, and any RNA-seq state — without restarting the app.
        """
        self.data = None
        self._current_spec = None
        self._current_result = None
        self._rnaseq_state = None
        self._clear_figure(show_placeholder=True)
        if hasattr(self, "stats_panel"):
            self.stats_panel.show_report(None)
            self.stats_panel.enable_cb.setChecked(False)
        if hasattr(self, "warn_label"):
            self.warn_label.setText("Validation messages and warnings appear here.")
        self._hide_example_prompt()
        self.stack.setCurrentIndex(0)
        self.statusBar().showMessage("Ready — load a data file or an example to begin.")

    def action_rnaseq(self):
        """Open the RNA-seq workflow dialog."""
        from apps.desktop_app.rnaseq_panel import RnaSeqDialog

        dlg = RnaSeqDialog(self.controller, self)
        dlg.exec()

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

        # statistics: refresh column choosers + advisory suggestions
        if hasattr(self, "stats_panel"):
            cols = [c for c in self._column_options() if c != "(none)"]
            self.stats_panel.set_columns(cols)
            try:
                rec = self.controller.recommend_tests(pt, defaults, self.data)
                self.stats_panel.set_suggestions(rec)
            except Exception:
                pass

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
        """Keep plot type, dataset, mappings, PlotSpec and preview in sync.

        When the plot type changes we reset the column mappings to that type's
        defaults and try to render the *currently loaded* data. If that data is
        not compatible with the new plot type:
          * for bundled example data -> automatically load the new type's example;
          * for user-uploaded data -> clear the stale figure and offer to load
            the matching example (never keep showing the previous plot).
        """
        if self.data is None or self._suppress_change:
            return
        pt = self.plot_combo.currentData()
        self._hide_example_prompt()

        # When browsing bundled examples, switching plot type should show THAT
        # plot type's own example (each example is designed for its plot type),
        # rather than reusing the previous example's columns.
        if self.data.is_example:
            self._load_example_for_current_type()
            return

        # User-uploaded data: keep it if it is compatible with the new plot type;
        # otherwise clear the stale figure and offer to load the matching example.
        self._rebuild_mapping_and_options()      # reset mappings to defaults for pt
        spec, result, err = self._try_build_and_render()
        if result is not None:
            self._display_result(spec, result)
            return
        self._clear_figure()
        self._current_result = None
        self._current_spec = None
        self._show_warning(
            f"Your uploaded data does not have the columns required for "
            f"“{display_name(pt)}”.\n{err}")
        self._show_example_prompt(pt)

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
        stats_spec = self.stats_panel.stats_spec() if hasattr(self, "stats_panel") else None
        spec = self.controller.build_spec(
            pt, style, self.data.table_name, self._collect_mapping(),
            layout=layout, width=self.width_combo.currentText(), dpi=self.dpi_spin.value(),
            statistics=stats_spec)
        overrides = self._collect_style_overrides()
        if overrides:
            spec["style"] = overrides
        return spec

    def _try_build_and_render(self):
        """Return (spec, result, error_msg). result is None if rendering failed."""
        try:
            spec = self._build_spec()
            result = self.controller.render(spec, self.data)
            return spec, result, None
        except (RenderError, SpecValidationError) as exc:
            return None, None, str(exc)
        except Exception as exc:  # never let a render error leave a stale figure
            return None, None, f"Unexpected error: {exc}"

    def _display_result(self, spec, result):
        self._current_spec = spec
        self._current_result = result
        self._hide_example_prompt()
        warns = list(result.warnings or [])
        check = result.metadata.get("publication_check", {})
        lines = [check.get("summary", "")] if check else []
        if warns:
            lines.append("⚠ " + " | ".join(warns))
        self.warn_label.setText("\n".join([ln for ln in lines if ln]) or "No warnings.")
        # Show the messages tab if there is anything actionable, else data preview.
        self.right_tabs.setCurrentIndex(1 if (warns or not check.get("passed", True)) else 0)
        self.statusBar().showMessage(check.get("summary", "Rendered."), 6000)
        if hasattr(self, "stats_panel"):
            self.stats_panel.show_report(getattr(result, "stats_report", None))
        self._show_figure(result.figure)          # figure is always visible below

    def render_preview(self):
        if self.data is None:
            return
        spec, result, err = self._try_build_and_render()
        if result is None:
            # Clear the stale figure so a previous plot never lingers on error.
            self._clear_figure()
            self._current_result = None
            self._current_spec = None
            self._show_warning(err)
            return
        self._display_result(spec, result)

    def _show_warning(self, msg: str):
        self.warn_label.setText("⚠ " + msg)
        self.right_tabs.setCurrentIndex(1)

    def _clear_figure(self, show_placeholder: bool = True):
        """Remove the current canvas/toolbar and release the matplotlib figure.

        Old widgets are detached AND scheduled for deletion with deleteLater()
        so no stale canvas/toolbar lingers to intercept events or draw.
        """
        if self._toolbar is not None:
            self.fig_layout.removeWidget(self._toolbar)
            self._toolbar.setParent(None)
            self._toolbar.deleteLater()
            self._toolbar = None
        if self._canvas is not None:
            old_fig = self._canvas.figure
            self.fig_layout.removeWidget(self._canvas)
            self._canvas.setParent(None)
            self._canvas.deleteLater()
            self._canvas = None
            if old_fig is not None:
                import matplotlib.pyplot as plt

                plt.close(old_fig)
        if self.fig_placeholder is not None:
            self.fig_placeholder.setParent(None)
            self.fig_placeholder.deleteLater()
            self.fig_placeholder = None
        if show_placeholder:
            self.fig_placeholder = QLabel("No figure to show — see the Messages tab above.")
            self.fig_placeholder.setAlignment(Qt.AlignCenter)
            self.fig_layout.addWidget(self.fig_placeholder)

    def _show_figure(self, fig):
        # Replace any previous canvas/toolbar so the toolbar always drives the
        # currently visible figure (no stale references left behind).
        self._clear_figure(show_placeholder=False)
        canvas = FigureCanvasQTAgg(fig)
        canvas.setObjectName("figureCanvas")
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        canvas.setFocusPolicy(Qt.StrongFocus)   # needed for key/scroll interactions
        toolbar = NavigationToolbar2QT(canvas, self.fig_container)
        toolbar.setObjectName("figureToolbar")
        # Toolbar on top, canvas fills the rest (stretch = 1) — nothing overlays it.
        self.fig_layout.addWidget(toolbar)
        self.fig_layout.addWidget(canvas, 1)
        self._canvas = canvas
        self._toolbar = toolbar
        canvas.setFocus()
        canvas.draw()
        # Seed the navigation history with the current view so Home / Back /
        # Forward work immediately (matplotlib otherwise starts with an empty
        # stack, making Home a no-op until the user first pans/zooms).
        try:
            toolbar.update()
            toolbar.push_current()
        except Exception:
            pass
        canvas.draw_idle()
        if self._debug:
            self._wire_debug_logging(canvas, toolbar)
            self._dbg(f"render: canvas_id={id(canvas)} figure_id={id(canvas.figure)} "
                      f"toolbar_id={id(toolbar)} bound={toolbar.canvas is canvas}")

    # --- debug logging (behind --debug) ----------------------------------
    def _dbg(self, msg: str) -> None:
        if self._debug:
            print(f"[toolbar-debug] {msg}", flush=True)

    def _wire_debug_logging(self, canvas, toolbar) -> None:
        for act in toolbar.actions():
            if act.text():
                act.triggered.connect(
                    lambda _=False, name=act.text(): self._dbg(
                        f"action '{name}' triggered; mode={self._toolbar.mode!r}"))
        for evt in ("button_press_event", "button_release_event", "motion_notify_event"):
            canvas.mpl_connect(
                evt, lambda e, name=evt: self._dbg(
                    f"canvas {name} at ({e.x},{e.y}) inaxes={e.inaxes is not None}"))

    # --- diagnostics -----------------------------------------------------
    def diagnose(self) -> dict:
        """Verify the live figure/canvas/toolbar wiring (used by tests + --debug)."""
        canvas = self._canvas
        toolbar = self._toolbar
        result = self._current_result
        checks = {
            "has_current_result": result is not None,
            "has_canvas": canvas is not None,
            "has_toolbar": toolbar is not None,
            "canvas_is_qt_agg": canvas is not None and isinstance(canvas, FigureCanvasQTAgg),
            "toolbar_is_qt": toolbar is not None and isinstance(toolbar, NavigationToolbar2QT),
            "toolbar_bound_to_current_canvas": (
                canvas is not None and toolbar is not None and toolbar.canvas is canvas),
            "canvas_has_result_figure": (
                canvas is not None and result is not None and canvas.figure is result.figure),
            "toolbar_actions_present": (
                toolbar is not None and len(toolbar.actions()) > 0),
        }
        return checks

    def widget_tree(self, widget=None, depth: int = 0, lines=None) -> str:
        """Return a text dump of the widget tree (class, objectName, state, geometry)."""
        from PySide6.QtWidgets import QWidget

        if lines is None:
            lines = []
        w = widget or self.centralWidget()
        if isinstance(w, QWidget):
            g = w.geometry()
            lines.append(
                f"{'  ' * depth}{w.metaObject().className()} "
                f"name='{w.objectName()}' visible={w.isVisible()} enabled={w.isEnabled()} "
                f"geom=({g.x()},{g.y()},{g.width()}x{g.height()})")
            for child in w.children():
                if isinstance(child, QWidget):
                    self.widget_tree(child, depth + 1, lines)
        return "\n".join(lines)

    def diagnose_toolbar_state(self) -> dict:
        """Detailed report of the toolbar<->canvas wiring for support/debugging."""
        c, tb = self._canvas, self._toolbar
        actions = []
        if tb is not None:
            for a in tb.actions():
                if a.text():
                    actions.append({"name": a.text(), "enabled": a.isEnabled()})
        return {
            "active_figure_id": id(c.figure) if c is not None else None,
            "active_canvas_id": id(c) if c is not None else None,
            "toolbar_id": id(tb) if tb is not None else None,
            "canvas_class": type(c).__name__ if c is not None else None,
            "toolbar_class": type(tb).__name__ if tb is not None else None,
            "canvas_is_qtagg": isinstance(c, FigureCanvasQTAgg) if c is not None else False,
            "toolbar_is_qt": isinstance(tb, NavigationToolbar2QT) if tb is not None else False,
            "toolbar_canvas_matches": (c is not None and tb is not None and tb.canvas is c),
            "canvas_figure_matches_result": (
                c is not None and self._current_result is not None
                and c.figure is self._current_result.figure),
            "toolbar_enabled": tb.isEnabled() if tb is not None else False,
            "canvas_enabled": c.isEnabled() if c is not None else False,
            "fig_container_enabled": self.fig_container.isEnabled(),
            "actions": actions,
            "nav_history_len": (len(tb._nav_stack) if tb is not None
                                and hasattr(tb, "_nav_stack") else None),
        }

    def run_toolbar_selftest(self) -> dict:
        """Exercise the toolbar operations in-process and report pass/fail.

        This runs the SAME operations the toolbar buttons invoke (zoom via a view
        change + Home to restore, and Save via the canvas), proving the toolbar is
        functionally connected to the current figure without needing screen input.
        """
        import os
        import tempfile

        results = {}
        c, tb = self._canvas, self._toolbar
        if c is None or tb is None or not c.figure.axes:
            return {"error": "no active figure/canvas"}
        ax = c.figure.axes[0]
        x0, y0 = ax.get_xlim(), ax.get_ylim()
        # Home/Back/Forward: change the view, push it, then Home should restore x0.
        try:
            tb.update()
            tb.push_current()                      # baseline (home)
            ax.set_xlim(x0[0] + (x0[1] - x0[0]) * 0.25, x0[0] + (x0[1] - x0[0]) * 0.75)
            tb.push_current()                      # a "zoomed" view in history
            tb.home()                              # should restore baseline
            c.draw_idle()
            xr = ax.get_xlim()
            results["home_resets_view"] = bool(abs(xr[0] - x0[0]) < 1e-6 and abs(xr[1] - x0[1]) < 1e-6)
        except Exception as exc:
            results["home_resets_view"] = f"error: {exc}"
        ax.set_xlim(*x0); ax.set_ylim(*y0)
        # Pan/Zoom mode toggles are wired.
        try:
            tb.pan(); m1 = str(tb.mode); tb.pan()
            tb.zoom(); m2 = str(tb.mode); tb.zoom()
            results["pan_mode_wired"] = "pan" in m1.lower()
            results["zoom_mode_wired"] = "zoom" in m2.lower()
        except Exception as exc:
            results["pan_mode_wired"] = f"error: {exc}"
        # Save: write the active figure to a temp file.
        try:
            dest = os.path.join(tempfile.mkdtemp(), "toolbar_selftest.png")
            c.figure.savefig(dest, dpi=150)
            results["save_writes_file"] = bool(os.path.exists(dest) and os.path.getsize(dest) > 500)
        except Exception as exc:
            results["save_writes_file"] = f"error: {exc}"
        return results

    # --- example-data prompt (for incompatible user uploads) -------------
    def _show_example_prompt(self, plot_type: str):
        self.example_prompt_btn.setText(f"Load {display_name(plot_type)} example data")
        self.example_prompt_btn.setVisible(True)

    def _hide_example_prompt(self):
        self.example_prompt_btn.setVisible(False)

    def _load_example_for_current_type(self):
        self.load_example(self.plot_combo.currentData())

    # --- layout persistence (RStudio-like remembered panels) -------------
    def _save_splitter_state(self):
        try:
            if getattr(self, "main_splitter", None) is not None:
                self.settings.setValue("main_splitter_state", self.main_splitter.saveState())
            if getattr(self, "right_splitter", None) is not None:
                self.settings.setValue("right_splitter_state", self.right_splitter.saveState())
            self.settings.setValue("window_geometry", self.saveGeometry())
        except Exception:
            pass  # never let layout persistence break the app

    def _restore_splitter_state(self):
        main_state = self.settings.value("main_splitter_state")
        if main_state is not None and getattr(self, "main_splitter", None) is not None:
            self.main_splitter.restoreState(main_state)
        right_state = self.settings.value("right_splitter_state")
        if right_state is not None and getattr(self, "right_splitter", None) is not None:
            self.right_splitter.restoreState(right_state)

    def closeEvent(self, event):
        self._save_splitter_state()
        super().closeEvent(event)

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
    # Exercise the statistics engine end-to-end so a frozen build fails loudly if
    # scipy/statsmodels/patsy are not bundled (two-way ANOVA needs patsy).
    stats_ok = []
    try:
        import numpy as _np
        import pandas as _pd

        rng = _np.random.default_rng(0)
        # (a) bar plot with pairwise Welch t-tests + brackets (scipy path)
        bar = _pd.DataFrame([{"g": g, "y": float(rng.normal(m, 0.3))}
                             for g, m in [("A", 1.0), ("B", 2.0), ("C", 1.5)] for _ in range(8)])
        s = ctrl.build_spec("barplot_with_error_bar", "publication", "bar.csv",
                            {"x": "g", "y": "y"},
                            statistics={"enabled": True, "test": "welch_t",
                                        "comparison_mode": "all_pairs"})
        r = ctrl.render(s, _mk_loaded(bar))
        assert r.stats_report is not None and len(r.stats_report.results) == 3
        stats_ok.append("welch_t brackets")
        # (b) grouped two-way ANOVA (statsmodels + patsy path)
        gb = _pd.DataFrame([{"geno": geno, "trt": trt, "expr": float(rng.normal(b, 0.2))}
                            for geno, trt, b in [("WT", "V", 1.0), ("WT", "D", 1.8),
                                                 ("KO", "V", 0.9), ("KO", "D", 1.1)]
                            for _ in range(6)])
        s2 = ctrl.build_spec("grouped_barplot_with_error_bar", "publication", "gb.csv",
                             {"x": "geno", "group": "trt", "y": "expr"},
                             statistics={"enabled": True, "test": "two_way_anova"})
        r2 = ctrl.render(s2, _mk_loaded(gb))
        assert r2.stats_report is not None and len(r2.stats_report.results) >= 3
        stats_ok.append("two-way ANOVA (statsmodels+patsy)")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"statistics: {exc}")

    if failures:
        sys.stderr.write("SELFTEST FAILURES:\n" + "\n".join(failures) + "\n")
        return 1
    sys.stdout.write(f"SELFTEST OK: {len(available_plot_types())} plot types rendered + "
                     f"exported; statistics OK ({', '.join(stats_ok)}).\n")
    return 0


def _mk_loaded(df):
    """Wrap a DataFrame as a LoadedData for controller.render in the selftest."""
    class _Info:
        dataframe = df

    return LoadedData(info=_Info(), table_name="selftest.csv")


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    debug = "--debug" in sys.argv
    if debug:
        # Print exactly which source is loaded before creating any window.
        print(debug_info_text())
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))
    win = MainWindow()
    win._debug = debug
    win.show()
    if debug:
        # Load an example, then dump the diagnostic checks + widget tree.
        win.load_example("barplot_with_error_bar")
        print("\n[diagnose]")
        for k, v in win.diagnose().items():
            print(f"  {k}: {v}")
        print("\n[diagnose_toolbar_state]")
        for k, v in win.diagnose_toolbar_state().items():
            print(f"  {k}: {v}")
        print("\n[toolbar self-test]")
        for k, v in win.run_toolbar_selftest().items():
            print(f"  {k}: {v}")
        print("\n[widget tree]")
        print(win.widget_tree())
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
