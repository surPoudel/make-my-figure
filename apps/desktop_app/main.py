"""Make My Figure — desktop GUI (PySide6).

Zero-command app for non-technical scientists: open a data file, pick a plot
type, map columns, preview in the Publication style, and export SVG/PNG/PDF/
PlotSpec JSON (or a ZIP of all). Runs fully locally; no telemetry.

The GUI is intentionally thin — all plotting/validation/export lives in
``make_my_figure_core`` and ``apps.desktop_app.controller``.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pandas as pd

import matplotlib

matplotlib.use("Agg")  # figures are created headless, then embedded in a Qt canvas

# Make the repo importable when run from source (frozen apps bundle the package).
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Friendly guard: the desktop app needs a Qt binding (PySide6). Importing the
# Matplotlib Qt backend below would otherwise fail with a cryptic
# "Failed to import Qt binding modules" message. Catch both "not installed" and
# "installed but native libs missing" (e.g. libEGL on headless Linux/WSL) and print
# exactly how to fix it, plus the Streamlit fallback. Tests guard with
# importorskip("PySide6"), so this only fires on the real `-m` launch path.
try:
    from PySide6.QtWidgets import QApplication as _QtImportCheck  # noqa: F401
except Exception as _qt_exc:  # noqa: BLE001
    import sys as _sys

    _low = str(_qt_exc).lower()
    _needs_apt = any(tok in _low for tok in ("libegl", "libxkb", "libgl", "xcb", "cannot open shared object"))
    _msg = [
        "",
        "Make My Figure desktop app could not start: a Qt binding (PySide6) is unavailable.",
        f"  ({type(_qt_exc).__name__}: {_qt_exc})",
        "",
        "Install the desktop dependencies into THIS environment:",
        '    python -m pip install -e ".[desktop]"',
        "",
    ]
    if _needs_apt:
        _msg += [
            "On Linux/WSL you also need Qt system libraries:",
            "    sudo apt install -y libxkbcommon0 libxkbcommon-x11-0 libgl1 libegl1 \\",
            "        libxcb-cursor0 libxcb-xinerama0 libxcb-keysyms1 libxcb-randr0 \\",
            "        libxcb-render-util0 libxcb-shape0 libxcb-icccm4 libxcb-image0 \\",
            "        libxcb-xfixes0 libdbus-1-3",
            "",
        ]
    _msg += [
        "Or use the Streamlit app instead (no Qt required):",
        "    streamlit run apps/streamlit_app/streamlit_app.py --server.fileWatcherType none",
        "",
    ]
    _sys.stderr.write("\n".join(_msg))
    # Clean exit when launched directly (python -m apps.desktop_app.main); re-raise
    # the original ImportError when imported (so tests skip via importorskip exactly
    # as before, rather than hitting an uncatchable SystemExit).
    if __name__ == "__main__":
        raise SystemExit(1)
    raise

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from PySide6.QtCore import Qt, QSettings, QTimer
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
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from apps.desktop_app import help_content
from apps.desktop_app.controller import DesktopController, LoadedData

# Plot types that consume a features x samples matrix: the user picks which columns
# are the value (measurement) columns; numeric annotation columns are left out.
_MATRIX_PLOT_TYPES = {
    "heatmap_clustered_matrix",
    "pca_scatter_from_matrix",
    "hierarchical_clustering",
    "hierarchical_dendrogram",
}
from make_my_figure_core import ui_hints
from make_my_figure_core.io.loaders import LoaderError
from make_my_figure_core.io import workbook as workbook_io
from make_my_figure_core.plots.base import RenderError
from make_my_figure_core.plots.registry import display_name
from make_my_figure_core.spec.validate import SpecValidationError
from make_my_figure_core.styles.engine import USER_PALETTES

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
        "frontend": "desktop",
        "app_version": __version__,
        "git_commit": _git_commit(),
        "desktop_app_file": os.path.abspath(__file__),
        "core_package_path": os.path.dirname(os.path.abspath(make_my_figure_core.__file__)),
        "repo_root": _REPO_ROOT,
        "current_working_dir": os.getcwd(),
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "matplotlib": matplotlib.__version__,
        "matplotlib_backend": matplotlib.get_backend(),
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
        tabs.addTab(disc, "Publication style disclaimer")

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close)


class _AspectView(QWidget):
    """Holds a matplotlib canvas and keeps the figure's width:height ratio.

    The Qt Agg canvas otherwise stretches the figure to the pane, changing its
    aspect and clipping tight-laid-out labels/legends. This letterboxes the canvas
    (centred, correct proportions) so the WHOLE figure is always visible — matching
    what a saved file looks like — while staying fully interactive.
    """

    def __init__(self, canvas, aspect: float, parent=None):
        super().__init__(parent)
        self._canvas = canvas
        self._aspect = aspect if aspect and aspect > 0 else 1.0
        canvas.setParent(self)

    def set_aspect(self, aspect: float) -> None:
        self._aspect = aspect if aspect and aspect > 0 else 1.0
        self._relayout()

    def resizeEvent(self, event):
        self._relayout()
        super().resizeEvent(event)

    def _relayout(self) -> None:
        # Letterbox the canvas to the figure's aspect (centred). We do NOT re-run
        # tight_layout here: it is incompatible with the make_axes_locatable divider
        # axes used by heatmap/clustering (colorbar, cluster strip, dendrogram) and
        # collapses the main axes into a corner. The figure keeps the margins its
        # renderer designed; the whole figure is shown scaled to fit.
        W, H = self.width(), self.height()
        if W <= 0 or H <= 0:
            return
        w = W
        h = int(round(w / self._aspect))
        if h > H:
            h = H
            w = int(round(h * self._aspect))
        x = (W - w) // 2
        y = (H - h) // 2
        self._canvas.setGeometry(x, y, max(1, w), max(1, h))


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
        # Debounce for continuous controls (sliders/spin): coalesce a burst of
        # value changes into one render so dragging stays responsive (esp. Windows).
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(180)
        self._render_timer.timeout.connect(self.render_preview)
        self._auto_recommend = True
        self._data_before_transform = None   # original data stashed before a reshape
        self._canvas = None
        self._fig_view = None             # aspect-preserving holder for the canvas
        self._identify_mode = False       # click-to-identify/label on the canvas
        self._picked_labels = {}          # plot_type -> [labels] chosen by clicking (legacy)
        self._picked_points = {}          # plot_type -> [point_id] chosen by clicking (identity)
        self._pick_cols = {}              # plot_type -> label column to annotate by
        self._label_offsets = {}          # plot_type -> {label: [dx, dy]} manual moves (legacy)
        self._point_offsets = {}          # plot_type -> {point_id: [dx, dy]} manual moves
        self._drag_label = None           # (plot_type, label) currently being dragged
        self._pending_column_annotations = None   # group color strip from "Define groups"
        # Matrix-Workflow → plot-editor handoff: suggested mappings/defaults applied
        # once when opening a recommendation, and provenance recorded on the PlotSpec.
        self._handoff_mapping = {}
        self._handoff_provenance = {}
        self._matrix_dialog = None        # persisted so returning preserves wizard state
        self._toolbar = None
        self._suppress_change = False   # re-entrancy guard for plot-type changes
        self._debug = False             # set by --debug: verbose toolbar/canvas logging

        self.setWindowTitle(APP_NAME)
        self.resize(1180, 760)
        # Build/version banner in the status bar so a user can confirm they run the
        # freshly-pulled code (not a stale installed package).
        try:
            from make_my_figure_core.version import build_banner
            self.statusBar().showMessage(build_banner())
        except Exception:  # noqa: BLE001
            pass
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        self.setAcceptDrops(True)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.stack.addWidget(self._build_welcome())   # index 0
        self.stack.addWidget(self._build_workbench())  # index 1

        # Pop-out / pop-in panel manager (v0.5): detach panels to another monitor
        # and dock them back without losing state. Guarded so a failure here can
        # never stop the app from starting.
        self._panels = None
        try:
            from apps.desktop_app.panels_dock import PanelManager

            self._panels = PanelManager(self, self.settings)
            self._panels.register("figure", "Figure", self.fig_container)
            self._panels.register("data", "Data & Messages", self.right_tabs)
            self._panels.register("controls", "Plot Controls", self._controls_scroll)
        except Exception:
            self._panels = None

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
        # Stacked (not a fixed-width row): full labels stay visible at any pane width,
        # DPI, or OS font metric — a horizontal row clipped "Matrix workflow…" on macOS.
        nav_row = QVBoxLayout()
        self.home_btn = QPushButton("\U0001F3E0  Home / Upload New Data")
        self.home_btn.setToolTip("Return to the upload page to load a different dataset "
                                 "(clears the current data, plot, and statistics).")
        self.home_btn.clicked.connect(self.action_home_upload)
        nav_row.addWidget(self.home_btn)
        self.groups_btn = QPushButton("\U0001F5C2  Define groups…")
        self.groups_btn.setToolTip("Assign sample columns to groups (wide matrix) or label rows "
                                   "by a column's values — no metadata file needed.")
        self.groups_btn.clicked.connect(self.action_define_groups)
        nav_row.addWidget(self.groups_btn)
        self.matrix_btn = QPushButton("\U0001F9EE  Matrix workflow…")
        self.matrix_btn.setToolTip("Guided workflow for a feature-by-sample matrix: map "
                                   "columns, define groups, get plot recommendations, and "
                                   "generate publication plots.")
        self.matrix_btn.clicked.connect(self.action_matrix_wizard)
        nav_row.addWidget(self.matrix_btn)
        cv.addLayout(nav_row)

        # Worksheet selector — shown only for multi-sheet Excel workbooks. Every
        # worksheet is listed (notes/empty/hidden included); classification is
        # advisory. Switching sheets reloads that sheet and clears stale state.
        self.sheet_box = QGroupBox("\U0001F4D1  Worksheet")
        _sbl = QVBoxLayout(self.sheet_box)
        self.sheet_combo = QComboBox()
        self.sheet_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.sheet_combo.setToolTip("Choose any worksheet in the uploaded workbook.")
        self.sheet_combo.currentIndexChanged.connect(self._on_sheet_changed)
        _sbl.addWidget(self.sheet_combo)
        self.sheet_info_label = QLabel("")
        self.sheet_info_label.setWordWrap(True)
        self.sheet_info_label.setStyleSheet("color:#345; font-size:11px;")
        _sbl.addWidget(self.sheet_info_label)
        self.sheet_box.setVisible(False)
        self._current_workbook_id = None
        cv.addWidget(self.sheet_box)

        self.plot_combo = QComboBox()
        # A no-plot placeholder so uploading data does not immediately draw a chart;
        # the user picks a plot type when ready (data=None means "nothing selected").
        # Shared with the Streamlit app via ui_strings for cross-frontend consistency.
        from make_my_figure_core.ui_strings import PLOT_TYPE_PLACEHOLDER
        self.plot_combo.addItem(PLOT_TYPE_PLACEHOLDER, None)
        for pt, label in self.controller.plot_types():
            self.plot_combo.addItem(label, pt)
        self.plot_combo.currentIndexChanged.connect(self._on_plot_type_changed)

        self.style_combo = QComboBox()
        for s, label in self.controller.styles():
            self.style_combo.addItem(label, s)

        type_box = QGroupBox("1. Plot type & style")
        tb = QFormLayout(type_box)
        tb.addRow("Plot type", self.plot_combo)
        tb.addRow("Style", self.style_combo)
        cv.addWidget(type_box)

        # Recommended figures (intelligent suggestions after upload).
        from apps.desktop_app.recommendations_panel import RecommendationsPanel

        self.recommend_panel = RecommendationsPanel()
        self.recommend_panel.generateRequested.connect(self._on_generate_recommendation)
        self.recommend_panel.addToBuilderRequested.connect(self._on_add_recommendation_to_builder)
        cv.addWidget(self.recommend_panel)

        # Shown only after a recommendation reshapes/replaces the data (transform,
        # grouping, or differential screen) so the user can undo it. The reshaped
        # CSV stays on disk; this only restores the in-app table + its own recs.
        self.revert_btn = QPushButton("↩  Revert to original data")
        self.revert_btn.setToolTip("Restore the data you had before the last reshape / "
                                   "grouping / differential screen (the saved CSV is kept).")
        self.revert_btn.clicked.connect(self.action_revert_data)
        self.revert_btn.setVisible(False)
        cv.addWidget(self.revert_btn)

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
        # Click-to-identify / label (volcano & scatter): clicking a point shows
        # its name in the status bar and toggles a label on it (saved in PlotSpec).
        self.chk_click_label = QCheckBox("Click a point to identify / label it")
        self.chk_click_label.setToolTip(
            "Volcano & scatter: click near a point to see its gene/sample name; "
            "clicking toggles a label on that point (stored in the PlotSpec).")
        self.chk_click_label.toggled.connect(self._on_click_label_toggled)
        lb.addRow("Point picking", self.chk_click_label)
        cv.addWidget(labels_box)

        cv.addWidget(self._build_preset_panel())
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

        self.qc_btn = QPushButton("Publication QC")
        self.qc_btn.setToolTip("Check the current figure for publication readiness "
                               "and optionally auto-fix common issues before export.")
        self.qc_btn.clicked.connect(self.action_publication_qc)
        cv.addWidget(self.qc_btn)

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
        # Minimum from content; no hard max cap (the splitter controls width). A fixed
        # 480px cap previously clipped wide controls/labels regardless of window size.
        scroll.setMinimumWidth(340)
        self._controls_scroll = scroll          # referenced by the pop-out manager
        splitter.addWidget(scroll)
        scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

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
    # --- Figure presets -------------------------------------------------------------------
    # Save a figure's configuration once and apply it to new data later. Everything here is a thin
    # layer over make_my_figure_core.presets, which both frontends share; the desktop app only
    # moves values between the preset and its widgets.

    def _preset_store(self):
        from make_my_figure_core.presets import PresetStore
        return PresetStore()

    def _build_preset_panel(self) -> QWidget:
        box = QGroupBox("Figure preset")
        box.setToolTip("A reusable configuration for this plot type: fonts, colours, layout, "
                       "legend and export settings (a style preset), or the whole configuration "
                       "including column roles and thresholds (a full preset). Presets never "
                       "contain your data.")
        outer = QVBoxLayout(box)
        self.preset_combo = QComboBox()
        self.preset_combo.setToolTip("Presets saved for this plot type, plus universal ones.")
        outer.addWidget(self.preset_combo)
        row1 = QHBoxLayout()
        for label, slot, tip in (
                ("Apply", self.action_apply_preset,
                 "Apply the selected preset to the current figure."),
                ("Save preset…", self.action_save_preset,
                 "Save the current configuration as a preset."),
                ("Delete", self.action_delete_preset, "Delete the selected preset.")):
            b = QPushButton(label); b.setToolTip(tip); b.clicked.connect(slot); row1.addWidget(b)
        outer.addLayout(row1)
        row2 = QHBoxLayout()
        for label, slot, tip in (
                ("Import…", self.action_import_preset,
                 "Add a preset file (.mmfpreset.json) to your library."),
                ("Export…", self.action_export_preset,
                 "Write the selected preset to a file to share it."),
                ("Reset to Publication defaults", self.action_reset_style,
                 "Return every style control to the Publication defaults.")):
            b = QPushButton(label); b.setToolTip(tip); b.clicked.connect(slot); row2.addWidget(b)
        outer.addLayout(row2)
        self.preset_status = QLabel("")
        self.preset_status.setWordWrap(True)
        self.preset_status.setStyleSheet("color: #666;")
        outer.addWidget(self.preset_status)
        self._refresh_preset_list()
        return box

    def _refresh_preset_list(self) -> None:
        combo = getattr(self, "preset_combo", None)
        if combo is None:
            return
        pt = self.plot_combo.currentData() if hasattr(self, "plot_combo") else None
        current = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("(choose a preset)", None)
        try:
            entries = self._preset_store().list(pt) if pt else self._preset_store().list()
        except Exception as exc:  # noqa: BLE001 - an unreadable library must not break the UI
            entries = []
            self.preset_status.setText(f"Preset library unavailable: {exc}")
        for e in entries:
            combo.addItem(e.label, e.path)
        idx = combo.findData(current)
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)
        if hasattr(self, "preset_status") and entries is not None:
            n = len(entries)
            self.preset_status.setText(
                f"{n} preset{'s' if n != 1 else ''} for this plot type." if pt else "")

    def _selected_preset_path(self):
        combo = getattr(self, "preset_combo", None)
        return combo.currentData() if combo is not None else None

    def action_apply_preset(self):
        from make_my_figure_core.presets import PresetError, apply_preset, load_preset

        path = self._selected_preset_path()
        if not path:
            QMessageBox.information(self, "Figure preset", "Choose a preset to apply first.")
            return
        if self.data is None or self.plot_combo.currentData() is None:
            QMessageBox.information(self, "Figure preset",
                                    "Load data and choose a plot type, then apply the preset.")
            return
        try:
            preset = load_preset(path)
            base = self._build_spec()
            result = apply_preset(preset, base, columns=list(self.data.info.columns))
        except PresetError as exc:
            QMessageBox.warning(self, "Cannot apply preset", str(exc))
            return
        self._apply_spec_to_controls(result.spec, keep_plot_type=True)
        msg = [f"Applied preset “{preset.get('name', '')}”: {len(result.applied)} setting(s)."]
        if result.skipped:
            msg.append(f"{len(result.skipped)} setting(s) do not apply to this plot type.")
        self.preset_status.setText(" ".join(msg))
        if result.unresolved_roles:
            lines = [f"• {role}: wanted {wanted!r}" for role, wanted in result.unresolved_roles.items()]
            QMessageBox.information(
                self, "Choose columns for this data",
                "The preset named columns this table does not have. Nothing was substituted - "
                "pick a column for each of these in “Map columns”:\n\n" + "\n".join(lines))
        for w in result.warnings:
            if "universal settings" in w:
                self.preset_status.setText(self.preset_status.text() + " " + w)
        self.render_preview()

    def action_save_preset(self):
        from PySide6.QtWidgets import QDialogButtonBox, QRadioButton

        from make_my_figure_core.presets import PresetError, extract_preset

        if self.data is None or self.plot_combo.currentData() is None:
            QMessageBox.information(self, "Save preset",
                                    "Render a figure first, then save its configuration.")
            return
        pt = self.plot_combo.currentData()
        dlg = QDialog(self)
        dlg.setWindowTitle("Save Figure Preset")
        form = QVBoxLayout(dlg)
        name_row = QFormLayout()
        name_edit = QLineEdit(f"{display_name(pt)} preset")
        name_row.addRow("Preset name", name_edit)
        form.addLayout(name_row)
        style_rb = QRadioButton("Figure style only  -  fonts, colours, layout, legend, export. "
                                "Portable: apply to any data of this plot type.")
        full_rb = QRadioButton("Full figure configuration  -  also column roles, thresholds, "
                               "axis labels and statistics. Asks for remapping on new data.")
        style_rb.setChecked(True)
        form.addWidget(style_rb); form.addWidget(full_rb)
        note = QLabel("Neither kind contains your data or the table's name.")
        note.setStyleSheet("color: #666;")
        form.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept); buttons.rejected.connect(dlg.reject)
        form.addWidget(buttons)
        if dlg.exec() != QDialog.Accepted:
            return
        name = name_edit.text().strip() or f"{display_name(pt)} preset"
        try:
            spec = self._current_spec or self._build_spec()
            preset = extract_preset(spec, mode="style" if style_rb.isChecked() else "full",
                                    name=name)
            path = self._preset_store().save(preset)
        except PresetError as exc:
            QMessageBox.warning(self, "Cannot save preset", str(exc))
            return
        self._refresh_preset_list()
        idx = self.preset_combo.findData(path)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self.statusBar().showMessage(f"Saved preset “{name}”.", 5000)

    def action_import_preset(self):
        from make_my_figure_core.presets import PresetError

        path, _ = QFileDialog.getOpenFileName(
            self, "Import Figure preset", "",
            "Figure preset (*.mmfpreset.json);;PlotSpec JSON (*.plot_spec.json *.json);;All files (*)")
        if not path:
            return
        try:
            dest = self._preset_store().import_file(path)
        except (PresetError, OSError, ValueError) as exc:
            QMessageBox.warning(self, "Cannot import preset", str(exc))
            return
        self._refresh_preset_list()
        idx = self.preset_combo.findData(dest)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self.statusBar().showMessage("Preset imported.", 4000)

    def action_export_preset(self):
        from make_my_figure_core.presets import PRESET_EXTENSION, PresetError, load_preset

        path = self._selected_preset_path()
        if not path:
            QMessageBox.information(self, "Export preset", "Choose a preset to export first.")
            return
        try:
            preset = load_preset(path)
        except PresetError as exc:
            QMessageBox.warning(self, "Cannot export preset", str(exc))
            return
        from make_my_figure_core.presets import safe_filename
        dest, _ = QFileDialog.getSaveFileName(
            self, "Export Figure preset", safe_filename(preset.get("name", "preset")) + PRESET_EXTENSION,
            "Figure preset (*.mmfpreset.json)")
        if not dest:
            return
        try:
            self._preset_store().export_file(path, dest)
        except (PresetError, OSError) as exc:
            QMessageBox.warning(self, "Cannot export preset", str(exc))
            return
        self.statusBar().showMessage(f"Exported preset to {dest}", 5000)

    def action_delete_preset(self):
        path = self._selected_preset_path()
        if not path:
            QMessageBox.information(self, "Delete preset", "Choose a preset to delete first.")
            return
        name = self.preset_combo.currentText()
        if QMessageBox.question(self, "Delete preset", f"Delete {name}? This cannot be undone.") \
                != QMessageBox.Yes:
            return
        self._preset_store().delete(path)
        self._refresh_preset_list()
        self.statusBar().showMessage("Preset deleted.", 4000)

    def _apply_spec_to_controls(self, spec: dict, *, keep_plot_type: bool = False) -> None:
        """Push every value in ``spec`` into the matching control - mapping, options, labels,
        size, style tokens, layout geometry, colorbar and statistics.

        This is the one place a spec becomes widget state, used by both “Open PlotSpec” and
        “Apply preset”. A value with no widget is left in the spec's hands; a widget with no
        value keeps what it had.
        """
        self._loading_spec = True
        prev = self._suppress_change
        self._suppress_change = True
        try:
            pt = spec.get("plot_type")
            if not keep_plot_type:
                idx = self.plot_combo.findData(pt)
                if idx >= 0:
                    self.plot_combo.setCurrentIndex(idx)
                self._rebuild_mapping_and_options()
            mapping = spec.get("mapping") or {}
            for key, val in mapping.items():
                if val is None:
                    continue
                w = self._mapping_widgets.get(key)
                if w is not None:
                    i = w.findText(str(val))
                    if i >= 0:
                        w.setCurrentIndex(i)
                    continue
                lw = (getattr(self, "_multi_col_widgets", None) or {}).get(key)
                if lw is None and key == "value_columns":
                    lw = getattr(self, "_value_cols_widget", None)
                if lw is not None and isinstance(val, (list, tuple)):
                    wanted = {str(v) for v in val}
                    for j in range(lw.count()):
                        item = lw.item(j)
                        item.setSelected(item.text() in wanted)
                    continue
                ow = self._option_widgets.get(key)
                if ow is None:
                    continue
                try:
                    if isinstance(ow, QCheckBox):
                        ow.setChecked(bool(val))
                    elif isinstance(ow, QComboBox):
                        j = ow.findText(str(val))
                        if j >= 0:
                            ow.setCurrentIndex(j)
                    elif isinstance(ow, (QSpinBox, QDoubleSpinBox)):
                        ow.setValue(type(ow.value())(val))
                except Exception:  # noqa: BLE001 - one bad value must not abort the restore
                    pass
            # optional numerics the spec does not mention go back to "(auto)"
            for key, ow in self._option_widgets.items():
                if isinstance(ow, (QSpinBox, QDoubleSpinBox)) and ow.property("mmf_optional") \
                        and key not in mapping:
                    ow.setValue(ow.minimum())
            layout = spec.get("layout") or {}
            self.title_edit.setText(str(layout.get("title", "") or ""))
            self.xlabel_edit.setText(str(layout.get("x_label", "") or ""))
            self.ylabel_edit.setText(str(layout.get("y_label", "") or ""))
            cw = layout.get("column_width")
            if cw:
                k = self.width_combo.findText(str(cw))
                if k >= 0:
                    self.width_combo.setCurrentIndex(k)
            dpi = (spec.get("output") or {}).get("dpi")
            if dpi:
                try:
                    self.dpi_spin.setValue(int(dpi))
                except Exception:  # noqa: BLE001
                    pass
            style = spec.get("style") or {}
            has_layout_geometry = any(k in layout for k in (
                "x_tick_rotation", "y_tick_rotation", "legend_location", "x_label_pad",
                "y_label_pad", "title_pad", "margin_left", "margin_right", "margin_top",
                "margin_bottom", "auto_fix_layout"))
            has_colorbar = any(k in mapping for k in ("colorbar_location", "colorbar_pad",
                                                      "colorbar_shrink"))
            if (style or has_layout_geometry or has_colorbar) and getattr(self, "_style_box", None):
                self._style_box.setChecked(True)
                pal = style.get("palette_name")
                if pal:
                    kp = self.palette_combo.findData(pal)
                    if kp >= 0:
                        self.palette_combo.setCurrentIndex(kp)
                fam = style.get("font_family")
                fam = fam[0] if isinstance(fam, (list, tuple)) and fam else fam
                if fam:
                    kf = self.font_combo.findData(fam)
                    if kf >= 0:
                        self.font_combo.setCurrentIndex(kf)
                for widget, skey in [(self.sp_title, "title_font_pt"), (self.sp_axis, "axis_font_pt"),
                                     (self.sp_tick, "tick_label_pt"), (self.sp_legend, "legend_pt"),
                                     (self.sp_annot, "annotation_pt"), (self.sp_marker, "marker_size"),
                                     (self.sp_linew, "line_width_pt"), (self.sp_spine, "spine_width_pt")]:
                    if skey in style:
                        try:
                            widget.setValue(type(widget.value())(style[skey]))
                        except Exception:  # noqa: BLE001
                            pass
                if "legend_outside" in style:
                    self.chk_legend_outside.setChecked(bool(style["legend_outside"]))
                if "grid" in style:
                    self.chk_grid.setChecked(bool(style["grid"]))
                # layout geometry
                for combo, key in ((self.cmb_xrot, "x_tick_rotation"), (self.cmb_yrot, "y_tick_rotation")):
                    if key in layout:
                        j = combo.findText(str(int(layout[key])) if str(layout[key]).lstrip("-").isdigit()
                                           else str(layout[key]))
                        combo.setCurrentIndex(j if j >= 0 else 0)
                if "legend_location" in layout:
                    j = self.cmb_legloc.findText(str(layout["legend_location"]))
                    self.cmb_legloc.setCurrentIndex(j if j >= 0 else 0)
                for key, w in (("x_label_pad", self.sp_xpad), ("y_label_pad", self.sp_ypad),
                               ("title_pad", self.sp_titlepad), ("margin_left", self.sp_ml),
                               ("margin_right", self.sp_mr), ("margin_top", self.sp_mt),
                               ("margin_bottom", self.sp_mb)):
                    if key in layout:
                        try:
                            w.setValue(float(layout[key]))
                        except (TypeError, ValueError):
                            pass
                self.chk_autofix.setChecked(bool(layout.get("auto_fix_layout", False)))
                # colorbar geometry rides in the mapping
                if "colorbar_location" in mapping:
                    j = self.cmb_cbloc.findText(str(mapping["colorbar_location"]))
                    self.cmb_cbloc.setCurrentIndex(j if j >= 0 else 0)
                if "colorbar_pad" in mapping:
                    self.sp_cbpad.setValue(float(mapping["colorbar_pad"]))
                if "colorbar_shrink" in mapping:
                    self.sp_cbshrink.setValue(float(mapping["colorbar_shrink"]))
            stats = spec.get("statistics")
            if stats and hasattr(self, "stats_panel"):
                try:
                    self.stats_panel.load_spec(stats)
                except Exception:  # noqa: BLE001
                    pass
        finally:
            self._suppress_change = prev
            self._loading_spec = False

    def _build_style_panel(self) -> QWidget:
        # Grouped Publication controls: Typography / Axes & labels / Legend / Colorbar
        # / Figure margins — mirroring the Streamlit sidebar sections. Every control
        # maps to the shared StyleProfile or layout engine (no silent no-ops).
        box = QGroupBox("5. Publication style")
        box.setCheckable(True)
        box.setChecked(False)   # unchecked disables the controls (defaults apply)
        outer = QVBoxLayout(box)

        def _spin(minv, maxv, val, step=1, dbl=False):
            w = QDoubleSpinBox() if dbl else QSpinBox()
            w.setRange(minv, maxv)
            w.setSingleStep(step)
            w.setValue(val)
            w.valueChanged.connect(self._schedule_render)   # debounced
            return w

        def _combo(items, connect=True):
            c = QComboBox()
            c.addItems(items)
            if connect:
                c.currentIndexChanged.connect(self.render_preview)
            return c

        # ② Typography
        self.palette_combo = QComboBox()
        self.palette_combo.addItem("(publication default)", None)
        for name in USER_PALETTES:
            self.palette_combo.addItem(name, name)
        self.palette_combo.currentIndexChanged.connect(self.render_preview)
        self.font_combo = QComboBox()
        self.font_combo.addItem("(publication default)", None)
        for _fam in ("Arial", "Helvetica", "Liberation Sans", "DejaVu Sans", "Times New Roman"):
            self.font_combo.addItem(_fam, _fam)
        self.font_combo.currentIndexChanged.connect(self.render_preview)
        self.sp_title = _spin(8, 28, 14)
        self.sp_axis = _spin(8, 28, 12)
        self.sp_tick = _spin(6, 24, 10)
        self.sp_annot = _spin(6, 24, 10)
        self.sp_marker = _spin(6, 300, 45)
        self.sp_linew = _spin(0.5, 6.0, 1.8, 0.1, dbl=True)
        self.sp_spine = _spin(0.4, 4.0, 1.1, 0.1, dbl=True)
        self.chk_grid = QCheckBox()
        self.chk_grid.stateChanged.connect(self.render_preview)
        typo = QGroupBox("② Typography")
        tf = QFormLayout(typo)
        tf.addRow("Palette", self.palette_combo)
        tf.addRow("Font", self.font_combo)
        tf.addRow("Title pt", self.sp_title)
        tf.addRow("Axis label pt", self.sp_axis)
        tf.addRow("Tick label pt", self.sp_tick)
        tf.addRow("Annotation pt", self.sp_annot)
        tf.addRow("Marker size", self.sp_marker)
        tf.addRow("Line width", self.sp_linew)
        tf.addRow("Axis/spine width", self.sp_spine)
        tf.addRow("Grid", self.chk_grid)
        outer.addWidget(typo)

        # ③ Axes & labels
        self.cmb_xrot = _combo(["auto", "0", "45", "90"])
        self.cmb_yrot = _combo(["auto", "0", "45", "90"])
        self.sp_xpad = _spin(0, 40, 0, 1, dbl=True)
        self.sp_ypad = _spin(0, 40, 0, 1, dbl=True)
        self.sp_titlepad = _spin(0, 40, 0, 1, dbl=True)
        axesb = QGroupBox("③ Axes & labels")
        af = QFormLayout(axesb)
        af.addRow("X tick angle", self.cmb_xrot)
        af.addRow("Y tick angle", self.cmb_yrot)
        af.addRow("X label padding", self.sp_xpad)
        af.addRow("Y label padding", self.sp_ypad)
        af.addRow("Title padding", self.sp_titlepad)
        outer.addWidget(axesb)

        # ④ Legend
        self.cmb_legloc = _combo(["auto", "inside upper right", "inside upper left",
                                  "inside lower right", "inside lower left", "outside right",
                                  "outside left", "outside top", "outside bottom"])
        self.sp_legend = _spin(6, 24, 10)
        self.chk_legend_outside = QCheckBox()
        self.chk_legend_outside.stateChanged.connect(self.render_preview)
        legb = QGroupBox("④ Legend")
        lf = QFormLayout(legb)
        lf.addRow("Location", self.cmb_legloc)
        lf.addRow("Legend pt", self.sp_legend)
        lf.addRow("Legend outside", self.chk_legend_outside)
        outer.addWidget(legb)

        # ⑤ Colorbar (heatmap / clustering / confusion / enrichment)
        self.cmb_cbloc = _combo(["default", "right", "left", "top", "bottom"])
        self.sp_cbpad = _spin(0.0, 0.4, 0.0, 0.02, dbl=True)
        self.sp_cbshrink = _spin(0.3, 1.0, 1.0, 0.1, dbl=True)
        cbb = QGroupBox("⑤ Colorbar (heatmaps etc.)")
        cf = QFormLayout(cbb)
        cf.addRow("Location", self.cmb_cbloc)
        cf.addRow("Pad (0 = default)", self.sp_cbpad)
        cf.addRow("Size", self.sp_cbshrink)
        outer.addWidget(cbb)

        # ① Figure margins + auto-fix
        self.sp_ml = _spin(0.0, 0.5, 0.0, 0.02, dbl=True)
        self.sp_mr = _spin(0.0, 0.5, 0.0, 0.02, dbl=True)
        self.sp_mt = _spin(0.0, 0.5, 0.0, 0.02, dbl=True)
        self.sp_mb = _spin(0.0, 0.5, 0.0, 0.02, dbl=True)
        self.chk_autofix = QCheckBox()
        self.chk_autofix.stateChanged.connect(self.render_preview)
        figb = QGroupBox("① Figure margins")
        gf = QFormLayout(figb)
        gf.addRow("Left (0 = auto)", self.sp_ml)
        gf.addRow("Right (0 = auto)", self.sp_mr)
        gf.addRow("Top (0 = auto)", self.sp_mt)
        gf.addRow("Bottom (0 = auto)", self.sp_mb)
        gf.addRow("Auto-fix layout", self.chk_autofix)
        outer.addWidget(figb)

        reset = QPushButton("Reset to publication defaults")
        reset.clicked.connect(self.action_reset_style)
        outer.addWidget(reset)

        box.toggled.connect(lambda _=False: self.render_preview())
        self._style_box = box
        return box

    def _collect_layout_controls(self):
        """Return (layout_fragment, colorbar_mapping) from the grouped panel; empty
        when the style box is unchecked. Layout keys feed the shared layout engine;
        colorbar keys are read from the mapping by colorbar-capable renderers."""
        if not getattr(self, "_style_box", None) or not self._style_box.isChecked():
            return {}, {}
        lay = {}
        if self.cmb_xrot.currentText() != "auto":
            lay["x_tick_rotation"] = int(self.cmb_xrot.currentText())
        if self.cmb_yrot.currentText() != "auto":
            lay["y_tick_rotation"] = int(self.cmb_yrot.currentText())
        if self.cmb_legloc.currentText() != "auto":
            lay["legend_location"] = self.cmb_legloc.currentText()
        for key, w in (("x_label_pad", self.sp_xpad), ("y_label_pad", self.sp_ypad),
                       ("title_pad", self.sp_titlepad), ("margin_left", self.sp_ml),
                       ("margin_right", self.sp_mr), ("margin_top", self.sp_mt),
                       ("margin_bottom", self.sp_mb)):
            if w.value() > 0:
                lay[key] = float(w.value())
        if self.chk_autofix.isChecked():
            lay["auto_fix_layout"] = True
        cb = {}
        if self.cmb_cbloc.currentText() != "default":
            cb["colorbar_location"] = self.cmb_cbloc.currentText()
        if self.sp_cbpad.value() > 0:
            cb["colorbar_pad"] = float(self.sp_cbpad.value())
        if self.sp_cbshrink.value() < 1.0:
            cb["colorbar_shrink"] = float(self.sp_cbshrink.value())
        return lay, cb

    def _collect_style_overrides(self) -> dict:
        """Return spec['style'] overrides from the advanced panel (or {})."""
        if not getattr(self, "_style_box", None) or not self._style_box.isChecked():
            return {}
        ov = {
            "title_font_pt": float(self.sp_title.value()),
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
        font = self.font_combo.currentData()
        if font:
            ov["font_family"] = font
        return ov

    def action_reset_style(self):
        self.palette_combo.setCurrentIndex(0)
        self.font_combo.setCurrentIndex(0)
        self.sp_title.setValue(14)
        self.sp_axis.setValue(12); self.sp_tick.setValue(10); self.sp_legend.setValue(10)
        self.sp_annot.setValue(10); self.sp_marker.setValue(45)
        self.sp_linew.setValue(1.8); self.sp_spine.setValue(1.1)
        for _c in (self.cmb_xrot, self.cmb_yrot, self.cmb_legloc, self.cmb_cbloc):
            _c.setCurrentIndex(0)
        for _s in (self.sp_xpad, self.sp_ypad, self.sp_titlepad, self.sp_ml, self.sp_mr,
                   self.sp_mt, self.sp_mb, self.sp_cbpad):
            _s.setValue(0.0)
        self.sp_cbshrink.setValue(1.0)
        self.chk_autofix.setChecked(False)
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
        a_open_spec = QAction("Open PlotSpec… (reproduce a saved figure)", self)
        a_open_spec.setShortcut("Ctrl+Shift+O")
        a_open_spec.triggered.connect(self.action_open_plotspec)
        filem.addAction(a_open_spec)

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

        preset_menu = filem.addMenu("Figure preset")
        for label, slot in (("Apply selected preset", self.action_apply_preset),
                            ("Save preset…", self.action_save_preset),
                            ("Import preset…", self.action_import_preset),
                            ("Export selected preset…", self.action_export_preset),
                            ("Delete selected preset", self.action_delete_preset),
                            ("Reset to Publication defaults", self.action_reset_style)):
            act = QAction(label, self)
            act.triggered.connect(slot)
            preset_menu.addAction(act)
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

        # Pop-out / pop-in panels (v0.5) — detach to another monitor, dock back.
        if getattr(self, "_panels", None) is not None:
            viewm.addSeparator()
            for key, label in (("figure", "Pop Out Figure"),
                               ("data", "Pop Out Data Table"),
                               ("controls", "Pop Out Controls")):
                act = QAction(label, self)
                act.triggered.connect(lambda _=False, k=key: self._panels.toggle(k))
                viewm.addAction(act)
            a_dock_all = QAction("Dock All Panels", self)
            a_dock_all.triggered.connect(lambda: self._panels.dock_all())
            viewm.addAction(a_dock_all)

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
        if getattr(self, "_panels", None) is not None:
            try:
                self._panels.reset_layout()   # dock any floating panels first
            except Exception:
                pass
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
        # A genuinely new dataset starts a fresh Matrix Workflow + no handoff state.
        self._handoff_mapping = {}
        self._handoff_provenance = {}
        self._matrix_dialog = None
        # Uploaded data starts with NO plot selected — don't auto-draw a chart.
        prev = self._suppress_change
        self._suppress_change = True
        try:
            self.plot_combo.setCurrentIndex(0)     # the "Choose a plot type…" placeholder
        finally:
            self._suppress_change = prev
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
        self._picked_labels = {}          # clear click-to-label picks for new data
        self._picked_points = {}
        self._pick_cols = {}
        self._label_offsets = {}
        self._point_offsets = {}
        self._drag_label = None
        self._pending_column_annotations = None
        self.stack.setCurrentIndex(1)
        self._populate_sheet_selector(data)
        self._populate_table()
        self._rebuild_mapping_and_options()
        self.statusBar().showMessage(self._source_status(data))
        self.render_preview()
        if getattr(self, "_auto_recommend", True):
            self._refresh_recommendations()
        # Loading/setting data is a clean state — no reshape to revert (a reshape
        # path re-marks it right after calling this).
        self._data_before_transform = None
        if hasattr(self, "revert_btn"):
            self.revert_btn.setVisible(False)

    def _source_status(self, data: LoadedData) -> str:
        """Status-bar text showing workbook + worksheet when applicable."""
        if data and data.is_workbook and data.sheet_name:
            wb = data.workbook.source_filename
            return (f"Workbook: {wb}  ·  Worksheet: {data.sheet_name} — runs locally.")
        return f"Loaded {data.table_name} — runs locally."

    def _populate_sheet_selector(self, data: LoadedData) -> None:
        """Show/refresh the worksheet dropdown for a multi-sheet Excel workbook."""
        if not (data and data.is_workbook):
            self.sheet_box.setVisible(False)
            self._current_workbook_id = None
            return
        wbk = data.workbook
        prev = self._suppress_change
        self._suppress_change = True
        try:
            if self._current_workbook_id != wbk.file_hash:
                # New workbook: rebuild the dropdown (all sheets, workbook order).
                self.sheet_combo.clear()
                for name in wbk.sheet_names:
                    label = f"{name}  (hidden)" if wbk.is_hidden(name) else name
                    self.sheet_combo.addItem(label, name)
                    i = self.sheet_combo.count() - 1
                    self.sheet_combo.setItemData(i, name, Qt.ToolTipRole)  # full name
                self._current_workbook_id = wbk.file_hash
            idx = self.sheet_combo.findData(data.sheet_name)
            if idx >= 0:
                self.sheet_combo.setCurrentIndex(idx)
        finally:
            self._suppress_change = prev
        stype = data.info.source_sheet_type or "unknown"
        self.sheet_info_label.setText(
            f"{wbk.n_sheets} worksheet(s). Detected type: {stype}. "
            f"{data.info.n_rows} rows × {len(data.info.columns)} cols. "
            "Every sheet is selectable; classification is advisory.")
        self.sheet_box.setVisible(True)

    def _on_sheet_changed(self, _idx: int) -> None:
        """Load a newly selected worksheet, clearing stale mapping/plot/stats."""
        if self._suppress_change or not (self.data and self.data.is_workbook):
            return
        sheet = self.sheet_combo.currentData()
        if not sheet or sheet == self.data.sheet_name:
            return
        try:
            new_data = self.controller.load_workbook_sheet(
                self.data.workbook, sheet, source=self.data.source_path)
        except LoaderError as exc:
            # Empty/malformed sheet stays selectable but cannot be plotted.
            self.sheet_info_label.setText(
                f"Worksheet '{sheet}': {exc}\nPlotting disabled — pick another worksheet.")
            self.statusBar().showMessage(f"{sheet}: cannot plot this worksheet.")
            return
        # Reset the plot type to the placeholder so a stale plot/mapping is cleared.
        prev = self._suppress_change
        self._suppress_change = True
        try:
            self.plot_combo.setCurrentIndex(0)
        finally:
            self._suppress_change = prev
        if hasattr(self, "stats_panel") and hasattr(self.stats_panel, "reset"):
            try:
                self.stats_panel.reset()
            except Exception:
                pass
        self._set_data(new_data)

    def _mark_reshaped(self, original: "LoadedData | None") -> None:
        """Remember the pre-reshape data and show the Revert button."""
        self._data_before_transform = original
        if hasattr(self, "revert_btn"):
            self.revert_btn.setVisible(original is not None)

    def action_revert_data(self):
        """Restore the data as it was before the last reshape/group/differential."""
        orig = self._data_before_transform
        if orig is None:
            return
        # Reverting drops any Matrix-Workflow handoff provenance for the derived plot.
        self._handoff_provenance = {}
        self._handoff_mapping = {}
        self._set_data(orig)   # clears the stash, hides the button, re-renders + re-recommends
        self.statusBar().showMessage("Reverted to the original data.", 5000)

    # --- recommended figures ---------------------------------------------
    def _refresh_recommendations(self):
        if not hasattr(self, "recommend_panel") or self.data is None:
            return
        try:
            rec_spec = self.controller.recommend_for_loaded(self.data)
        except Exception as exc:  # recommendations must never break the app
            self.recommend_panel.set_recommendations(None)
            self.statusBar().showMessage(f"Recommendations unavailable: {exc}", 4000)
            return
        self.recommend_panel.set_recommendations(rec_spec)

    def _apply_recommendation(self, rec) -> bool:
        """Set the plot type + column mappings from a recommendation and render.

        Expensive recommendations require explicit confirmation first."""
        draft = getattr(rec, "plot_spec_draft", None)
        if not draft:
            # guidance recs (e.g. "run stats to get p/FDR for a volcano") are
            # informational — show the how-to instead of generating.
            instr = getattr(rec, "instructions", None)
            self._show_warning(instr or "This recommendation has no ready-to-generate spec.")
            return False
        # Transform recs first reshape the data (and save the reshaped CSV), then plot.
        tf = getattr(rec, "transform", None)
        if tf:
            import os as _os
            import tempfile as _tempfile
            original = self.data   # keep so the user can revert the reshape
            try:
                newdata = self.controller.apply_transform(self.data, tf)
            except Exception as exc:
                self._show_warning(f"Could not reshape the data: {exc}")
                return False
            outname = _os.path.basename(str(tf.get("output_filename") or newdata.table_name))
            src = getattr(self.data, "source_path", None)
            outdir = _os.path.dirname(src) if src else _tempfile.gettempdir()
            outpath = _os.path.join(outdir, outname)
            try:
                self.controller.save_table(newdata.info.dataframe, outpath)
                newdata.source_path = outpath
                self.statusBar().showMessage(f"Reshaped data saved to {outpath}", 8000)
            except Exception as exc:
                self._show_warning(f"Reshaped the data but could not save the CSV: {exc}")
            self.data = newdata
            self._populate_table()
            self._mark_reshaped(original)   # enable "Revert to original data"
        if getattr(rec, "requires_confirmation", False):
            resp = QMessageBox.question(
                self, "Generate figure?",
                f"'{getattr(rec, 'display_name', rec.plot_type)}' may be slow on this "
                "data (e.g. clustering/PCA). Generate it now?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if resp != QMessageBox.Yes:
                return False
        pt = rec.plot_type
        idx = self.plot_combo.findData(pt)
        if idx < 0:
            self._show_warning(f"Plot type '{pt}' is not available.")
            return False
        prev = self._suppress_change
        self._suppress_change = True
        try:
            self.plot_combo.setCurrentIndex(idx)
            self._rebuild_mapping_and_options()
        finally:
            self._suppress_change = prev
        mapping = dict(draft.get("mapping", {}))
        for key, val in mapping.items():
            w = self._mapping_widgets.get(key)
            if w is not None and val is not None:
                i = w.findText(str(val))
                if i >= 0:
                    w.setCurrentIndex(i)
                continue
            ow = self._option_widgets.get(key)
            if ow is not None:
                try:
                    if isinstance(ow, QCheckBox):
                        ow.setChecked(bool(val))
                    elif isinstance(ow, QComboBox):
                        j = ow.findText(str(val))
                        if j >= 0:
                            ow.setCurrentIndex(j)
                    elif isinstance(ow, (QSpinBox, QDoubleSpinBox)) and val is not None:
                        ow.setValue(val)
                except Exception:
                    pass
        self.render_preview()
        return True

    def action_open_plotspec(self):
        """Open a saved PlotSpec JSON (+ its data) and reproduce the exact figure."""
        import os as _os

        path, _ = QFileDialog.getOpenFileName(
            self, "Open PlotSpec", "", "PlotSpec JSON (*.plot_spec.json *.json)")
        if not path:
            return
        try:
            spec, data_path = self.controller.load_plotspec(path)
        except Exception as exc:
            self._show_warning(f"Could not read PlotSpec: {exc}")
            return
        if not data_path:
            data_path, _ = QFileDialog.getOpenFileName(
                self, "Select the data file for this PlotSpec", _os.path.dirname(path),
                "Data (*.csv *.tsv *.txt *.xlsx *.xls)")
            if not data_path:
                self._show_warning("A data file is needed to reproduce this PlotSpec.")
                return
        try:
            loaded = self.controller.load_file(data_path)
        except Exception as exc:
            self._show_warning(f"Could not load data '{_os.path.basename(data_path)}': {exc}")
            return
        self.data = loaded
        self.stack.setCurrentIndex(1)
        self._populate_table()
        # Best-effort: reflect the spec in the controls (so later edits round-trip).
        self._apply_plotspec_to_ui(spec)
        # Guarantee: render the spec exactly as saved (independent of widget round-trip).
        try:
            result = self.controller.render(spec, loaded)
        except Exception as exc:
            self._show_warning(f"Opened the PlotSpec but rendering failed: {exc}")
            return
        self._display_result(spec, result)
        if getattr(self, "_auto_recommend", True):
            self._refresh_recommendations()
        self._add_recent(data_path)
        self.statusBar().showMessage(
            f"Opened PlotSpec {_os.path.basename(path)} — runs locally.", 5000)

    def _apply_plotspec_to_ui(self, spec: dict):
        """Populate the controls from a loaded PlotSpec (no intermediate renders)."""
        self._apply_spec_to_controls(spec)

    def _on_generate_recommendation(self, rec):
        if self._apply_recommendation(rec):
            self.statusBar().showMessage(
                f"Generated {display_name(rec.plot_type)} from recommendation.", 4000)

    def _on_add_recommendation_to_builder(self, rec):
        if self._apply_recommendation(rec):
            self.action_save_panel()

    def action_publication_qc(self):
        """Score the current figure for publication readiness; offer auto-fixes."""
        if getattr(self, "_current_result", None) is None:
            self._show_warning("Render a figure first, then run Publication QC.")
            return
        report = getattr(self._current_result, "stats_report", None)
        score = self.controller.publication_qc(self._current_result, self._current_spec,
                                                stats_report=report)
        self._show_publication_qc_dialog(score)

    def _show_publication_qc_dialog(self, score):
        from PySide6.QtWidgets import QDialog, QDialogButtonBox

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Publication QC — {score.level.upper()} ({score.score}/100)")
        dlg.resize(560, 420)
        v = QVBoxLayout(dlg)
        head = QLabel(score.summary)
        head.setWordWrap(True)
        v.addWidget(head)
        issues = score.issues() if hasattr(score, "issues") else score.checks
        if not issues:
            v.addWidget(QLabel("No publication-readiness issues detected. ✓"))
        for c in issues:
            lvl = getattr(c, "level", "warn")
            icon = {"fail": "✗", "warn": "⚠", "pass": "✓"}.get(lvl, "•")
            row = QLabel(f"{icon} <b>{getattr(c, 'message', '')}</b><br>"
                         f"<span style='color:#555'>{getattr(c, 'suggestion', '')}</span>")
            row.setTextFormat(Qt.RichText)
            row.setWordWrap(True)
            v.addWidget(row)
        fixes = self.controller.qc_suggested_fixes(score, self._current_spec or {})
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        if fixes:
            autofix = buttons.addButton("Auto-fix && re-render", QDialogButtonBox.ApplyRole)
            autofix.clicked.connect(lambda: self._apply_qc_fixes([f["id"] for f in fixes], dlg))
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)
        v.addWidget(buttons)
        dlg.exec()

    def _apply_qc_fixes(self, fix_ids, dlg=None):
        if getattr(self, "_current_spec", None) is None:
            return
        try:
            new_spec = self.controller.apply_qc_fixes(self._current_spec, fix_ids)
            result = self.controller.render(new_spec, self.data)
        except Exception as exc:
            self._show_warning(f"Auto-fix failed: {exc}")
            return
        self._current_spec = new_spec
        self._current_result = result
        self._display_result(result)
        self.statusBar().showMessage("Applied publication QC auto-fixes.", 4000)
        if dlg is not None:
            dlg.accept()

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

        Clears dataset, plot spec, render result, figure preview, and statistics
        panel results — without restarting the app.
        """
        self.data = None
        self._current_spec = None
        self._current_result = None
        # Drop multi-sheet workbook context so a new upload starts clean.
        self._current_workbook_id = None
        # Drop Matrix-Workflow handoff/dialog state.
        self._handoff_mapping = {}
        self._handoff_provenance = {}
        self._matrix_dialog = None
        if hasattr(self, "sheet_box"):
            self.sheet_box.setVisible(False)
        self._clear_figure(show_placeholder=True)
        if hasattr(self, "stats_panel"):
            self.stats_panel.show_report(None)
            self.stats_panel.enable_cb.setChecked(False)
        if hasattr(self, "warn_label"):
            self.warn_label.setText("Validation messages and warnings appear here.")
        self._hide_example_prompt()
        self.stack.setCurrentIndex(0)
        self.statusBar().showMessage("Ready — load a data file or an example to begin.")

    def action_define_groups(self):
        """Open the in-app grouping dialog and adopt the resulting table."""
        if self.data is None:
            self._show_warning("Load a data file first, then define groups.")
            return
        from apps.desktop_app.grouping_panel import GroupingDialog

        dlg = GroupingDialog(self.controller, self.data, self,
                             initial_state=getattr(self, "_grouping_state", None))
        dlg.grouped.connect(self._adopt_grouped_data)
        dlg.exec()
        # Remember the assignment so reopening the dialog restores prior groups.
        if getattr(dlg, "result_state", None):
            self._grouping_state = dlg.result_state
        # A wide (heatmap/PCA) grouping carries a group color-strip spec; apply it
        # to the heatmap and re-render so the groups are visible.
        ann = getattr(dlg, "column_annotations", None)
        if ann:
            self._pending_column_annotations = ann
            self.render_preview()

    def action_matrix_wizard(self):
        """Open the guided matrix workflow (map -> groups -> recommend -> generate).

        The dialog instance is persisted on the window so returning to the Matrix
        Workflow after opening a recommendation in the plot editor preserves its
        state (mapping, groups, preprocessing, differential summary)."""
        if self.data is None:
            self._show_warning("Load a data file first, then open the matrix workflow.")
            return
        from apps.desktop_app.matrix_wizard import MatrixWizardDialog

        dlg = self._matrix_dialog
        if dlg is None:
            dlg = MatrixWizardDialog(self.controller, self.data, self._saved_panels, self)
            self._matrix_dialog = dlg
        dlg.pending_handoff = None
        dlg.exec()
        # Wizard-generated plots may have been added to the Figure Builder.
        self.panel_count_label.setText(f"{len(self._saved_panels)} panel(s) saved.")
        # "Open in plot editor" sets a pending handoff, then closes the dialog.
        handoff = getattr(dlg, "pending_handoff", None)
        if handoff is not None:
            dlg.pending_handoff = None
            self._apply_plot_handoff(handoff)

    def _apply_plot_handoff(self, handoff):
        """Load a Matrix-Workflow recommendation into the full plot editor.

        Wraps the plot-ready derived data as the active dataset, preselects the
        recommended plot type, pre-populates the suggested mappings/option defaults,
        and records matrix/metadata/preprocessing/stats/workbook provenance on the
        PlotSpec — so the user gets the *same* full controls, preview, annotation,
        export, and Figure Builder as the normal workflow."""
        loaded = self.controller.loaded_from_handoff(handoff)
        original = self.data
        # Suggested mappings + option defaults are applied once by _rebuild.
        self._handoff_mapping = {**(handoff.mappings or {}), **(handoff.defaults or {})}
        self._handoff_provenance = dict(handoff.provenance or {})
        col_ann = (handoff.spec_extra or {}).get("column_annotations")
        # Preselect the plot type BEFORE _set_data so exactly one rebuild runs.
        prev = self._suppress_change
        self._suppress_change = True
        try:
            idx = self.plot_combo.findData(handoff.plot_type)
            if idx >= 0:
                self.plot_combo.setCurrentIndex(idx)
        finally:
            self._suppress_change = prev
        self._set_data(loaded)
        self._mark_reshaped(original)   # revertible: return to the matrix table
        # _set_data cleared pending column annotations; restore the group strip.
        if col_ann:
            self._pending_column_annotations = col_ann
            self.render_preview()
        prov = handoff.provenance or {}
        self.statusBar().showMessage(
            f"Opened matrix {handoff.plot_type} in the plot editor — full controls "
            f"available. Source: {prov.get('source_sheet_name') or prov.get('source_matrix_id', 'matrix')}.")

    def _adopt_grouped_data(self, loaded):
        """Replace the active dataset with a derived (grouped/differential) table.

        Keeps the original data so the user can revert if they don't like it."""
        original = self.data
        self._set_data(loaded)             # clears the revert stash...
        self._mark_reshaped(original)      # ...then mark this as a revertible reshape
        self.statusBar().showMessage(f"Loaded {loaded.table_name} — runs locally.")

    def _populate_table(self):
        df = self.data.info.dataframe
        # Editable preview of the first rows; edits write back to the DataFrame and
        # re-render (see _on_table_cell_edited). Signals are blocked while filling.
        self._table_rows = min(50, len(df))
        head = df.head(self._table_rows)
        self.table_widget.blockSignals(True)
        try:
            self.table_widget.clear()
            self.table_widget.setColumnCount(len(head.columns))
            self.table_widget.setRowCount(len(head))
            self.table_widget.setHorizontalHeaderLabels([str(c) for c in head.columns])
            for r in range(len(head)):
                for c in range(len(head.columns)):
                    self.table_widget.setItem(r, c, QTableWidgetItem(str(head.iat[r, c])))
        finally:
            self.table_widget.blockSignals(False)
        # Readable, resizable headers: full name in a tooltip (never altered), columns
        # user-resizable, and a per-column width cap so many sample columns don't each
        # become extremely wide. First columns (feature id / annotation) get more room.
        hdr = self.table_widget.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        self.table_widget.resizeColumnsToContents()
        for c, colname in enumerate(head.columns):
            it = self.table_widget.horizontalHeaderItem(c)
            if it is not None:
                it.setToolTip(str(colname))
            cap = 260 if c < 2 else 140
            if self.table_widget.columnWidth(c) > cap:
                self.table_widget.setColumnWidth(c, cap)
        # Connect once; edits are live.
        if not getattr(self, "_table_edit_connected", False):
            self.table_widget.itemChanged.connect(self._on_table_cell_edited)
            self._table_edit_connected = True
        info = self.data.info
        dtypes = ", ".join(f"{c} ({'num' if c in info.numeric_columns else 'text'})"
                           for c in info.columns)
        warns = (" | ".join(info.warnings)) if info.warnings else "none"
        extra = "" if len(df) <= self._table_rows else \
            f" (editing the first {self._table_rows} rows)"
        self.dtype_label.setText(
            f"{info.n_rows} rows × {len(info.columns)} columns{extra}. "
            "Edit cells to update the figure live.\n"
            f"Detected types: {dtypes}\nWarnings: {warns}")

    def _volcano_prefill(self, plot_type: str, col_opts: list) -> dict:
        """Best-guess volcano column mapping from the current data (user confirms).

        Uses the DE-table column detector so edgeR (``logFC``/``P.Value``), DESeq2
        (``log2FoldChange``/``pvalue``/``padj``), and other headers auto-map. Only
        fills fields whose detected column exists; leaves the rest for the user.
        """
        if self.data is None:
            return {}
        try:
            from make_my_figure_core.de_detect import detect_de_columns

            det = detect_de_columns(self.data.info.dataframe)
        except Exception:
            return {}
        mapping = {}
        # x = log fold change; p = raw p-value (user can switch to adjusted p);
        # label = gene symbol (fall back to gene id).
        if det.get("logFC") in col_opts:
            mapping["x"] = det["logFC"]
        if det.get("p_value") in col_opts:
            mapping["p"] = det["p_value"]
        elif det.get("adj_p") in col_opts:
            mapping["p"] = det["adj_p"]
        lbl = det.get("gene_symbol") or det.get("gene_id")
        if lbl in col_opts:
            mapping["label"] = lbl
        if mapping and hasattr(self, "warn_label"):
            self.warn_label.setText(
                "Detected DE columns — confirm in 'Map columns': "
                + ", ".join(f"{k}={v}" for k, v in mapping.items())
                + ". Change any selection if the guess is wrong.")
        return mapping

    def _on_table_cell_edited(self, item):
        """Write an edited cell back into the DataFrame and re-render.

        Numeric columns are re-coerced (a non-numeric entry becomes NaN with a
        warning) so plots stay valid. Row r in the widget maps to df.iloc[r].
        """
        if self.data is None:
            return
        df = self.data.info.dataframe
        r, c = item.row(), item.column()
        if r >= len(df) or c >= len(df.columns):
            return
        col = df.columns[c]
        text = item.text()
        was_numeric = col in self.data.info.numeric_columns
        try:
            if was_numeric:
                # Convert to the column's numeric type up front (invalid -> NaN),
                # so assigning never clashes with a float column's dtype.
                value = pd.to_numeric(pd.Series([text]), errors="coerce").iloc[0]
                if str(text).strip() != "" and pd.isna(value):
                    self._show_warning(f"'{text}' is not numeric for column '{col}'; set to NaN.")
                df.iloc[r, c] = value
            else:
                if df[col].dtype != object:
                    df[col] = df[col].astype(object)
                df.iloc[r, c] = text
        except Exception as exc:  # never let an edit crash the app
            self._show_warning(f"Could not apply edit: {exc}")
            return
        # Re-render from the mutated data.
        self.render_preview()

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

    def _group_value_prefill(self, plot_type: str, col_opts: list) -> dict:
        """Best-guess mapping for distribution/group-value plots so picking the
        plot type manually doesn't leave x/y/group empty. Uses the data profiler
        to find a grouping (categorical) column + numeric value column(s). The
        user can always override via the selectors."""
        GV = {"ridge_or_density_plot", "boxplot_or_violin_with_points",
              "barplot_with_error_bar", "grouped_barplot_with_error_bar",
              "scatterplot_with_regression"}
        if self.data is None or plot_type not in GV:
            return {}
        try:
            from make_my_figure_core.recommendations.data_profiler import profile_table

            prof = profile_table(self.data.info.dataframe)
        except Exception:
            return {}
        group = prof.role_column("group")
        numerics = [c for c in prof.numeric_columns if c in col_opts]
        m: dict = {}
        if plot_type == "ridge_or_density_plot":
            if numerics:
                m["x"] = numerics[0]
            m["group"] = group
        elif plot_type in ("boxplot_or_violin_with_points", "barplot_with_error_bar",
                           "grouped_barplot_with_error_bar"):
            m["x"] = group
            if numerics:
                m["y"] = numerics[0]
        elif plot_type == "scatterplot_with_regression":
            if len(numerics) >= 2:
                m["x"], m["y"] = numerics[0], numerics[1]
        return {k: v for k, v in m.items() if v and v in col_opts}

    def _rebuild_mapping_and_options(self):
        pt = self.plot_combo.currentData()
        self._clear_form(self.mapping_form)
        self._mapping_widgets = {}
        self._value_cols_widget = None
        if pt is None:
            # No plot type selected — clear the option controls too and stop.
            self._clear_form(self.options_form)
            self._option_widgets = {}
            self._multi_col_widgets = {}
            return
        defaults = self.controller.default_mapping(pt)
        col_opts = self._column_options()
        # For a DE/volcano table, auto-detect logFC / p-value / label columns
        # (works for edgeR, DESeq2, and other tools) and prefill the dropdowns.
        # The user always confirms/overrides via the selectors — we never guess
        # silently. See _volcano_prefill.
        if pt == "volcano_plot":
            prefill = self._volcano_prefill(pt, col_opts)
        else:
            prefill = self._group_value_prefill(pt, col_opts)
        handoff_map = self._handoff_mapping or {}
        self._multi_col_widgets = {}
        for field in self.controller.column_fields(pt):
            if ui_hints.is_multi_column(field) and not (field == "value_columns"
                                                          and pt in _MATRIX_PLOT_TYPES):
                # Several columns, one per series. A single combo here would quietly plot only
                # the first of them - a three-group survival curve would come out as one curve
                # and look finished. For matrix plots "value_columns" keeps its own richer widget
                # below; for anything else (a wide-form histogram) it is an ordinary multi-select,
                # otherwise the role would have no control at all.
                lw = QListWidget()
                lw.setSelectionMode(QListWidget.ExtendedSelection)
                lw.setMaximumHeight(120)
                lw.setToolTip("Pick one column per series. Repeated spreadsheet headers arrive "
                              "disambiguated (e.g. event, event.1, event.2) — select them all.")
                pre = handoff_map.get(field) or defaults.get(field) or []
                if isinstance(pre, str):
                    pre = [pre]
                pre_set = {str(x) for x in pre}
                for c in self.data.info.columns if self.data is not None else []:
                    it = QListWidgetItem(str(c))
                    lw.addItem(it)
                    it.setSelected(str(c) in pre_set)
                lw.itemSelectionChanged.connect(self.render_preview)
                self.mapping_form.addRow(field, lw)
                self._multi_col_widgets[field] = lw
                continue
            combo = QComboBox()
            combo.addItems(col_opts)
            # Prefer the curated default when that column actually exists in the
            # uploaded data (keeps bundled examples exact); otherwise fall back to
            # the auto-detected prefill (volcano DE columns / group-value guess).
            # A Matrix-Workflow handoff's suggested mapping takes top priority.
            d = defaults.get(field)
            default = d if d in col_opts else prefill.get(field, d)
            if field in handoff_map and str(handoff_map[field]) in col_opts:
                default = str(handoff_map[field])
            if default in col_opts:
                combo.setCurrentText(default)
            combo.currentIndexChanged.connect(self.render_preview)
            label = field
            self.mapping_form.addRow(label, combo)
            self._mapping_widgets[field] = combo
        # Matrix plots: let the user choose which columns are the VALUE (measurement)
        # columns. Populate every non-id column and pre-select the auto-detected
        # value columns, so numeric annotation columns (e.g. annotationLevel coded
        # 1/2/3) are left out unless the user opts them in.
        self._value_cols_widget = None
        if pt in _MATRIX_PLOT_TYPES and self.data is not None:
            id_field = "matrix_row_id" if pt == "pca_scatter_from_matrix" else "row_id"
            id_col = self._mapping_widgets.get(id_field)
            id_name = id_col.currentText() if id_col else None
            cols = [c for c in self.data.info.columns if c != id_name]
            try:
                from make_my_figure_core.grouping import value_matrix_columns
                value_cols, _annot = value_matrix_columns(self.data.info.dataframe, id_name)
            except Exception:
                value_cols = cols
            lw = QListWidget()
            lw.setSelectionMode(QListWidget.ExtendedSelection)
            lw.setMaximumHeight(150)
            # A handoff can pre-select the exact value columns from the matrix mapping.
            if handoff_map.get("value_columns"):
                value_cols = [c for c in handoff_map["value_columns"] if c in cols]
            value_set = set(map(str, value_cols))
            for c in cols:
                it = QListWidgetItem(str(c))
                lw.addItem(it)
                it.setSelected(str(c) in value_set)
            lw.itemSelectionChanged.connect(self.render_preview)
            self.mapping_form.addRow("Value columns", lw)
            self._value_cols_widget = lw

        # PCA metadata-based fields (color/shape)
        if self.controller.needs_metadata(pt):
            meta_opts = self._metadata_options()
            for field in self.controller.pca_metadata_fields():
                combo = QComboBox()
                combo.addItems(meta_opts)
                default = defaults.get(field)
                if field in handoff_map and str(handoff_map[field]) in meta_opts:
                    default = str(handoff_map[field])
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
        self._refresh_preset_list()

        # Apply a Matrix-Workflow handoff's suggested option defaults (e.g. volcano
        # use_fdr / heatmap scale) once, then clear so later manual edits stick.
        if handoff_map:
            for key, w in self._option_widgets.items():
                if key not in handoff_map:
                    continue
                val = handoff_map[key]
                prev = self._suppress_change
                self._suppress_change = True
                try:
                    if isinstance(w, QCheckBox):
                        w.setChecked(bool(val))
                    elif isinstance(w, QComboBox):
                        if str(val) in [w.itemText(i) for i in range(w.count())]:
                            w.setCurrentText(str(val))
                    elif isinstance(w, (QSpinBox, QDoubleSpinBox)):
                        try:
                            w.setValue(type(w.value())(val))
                        except (TypeError, ValueError):
                            pass
                finally:
                    self._suppress_change = prev
            self._handoff_mapping = {}   # one-shot: consumed on this rebuild

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
        else:
            # An option with no default is optional: leaving it alone must mean "auto", not
            # "send the minimum". A spin box cannot be empty, so Qt's special-value text is used -
            # at the minimum it displays "(auto)" and _collect_mapping omits the key entirely.
            # Without this, x_min/x_max would both arrive as their minimum and an axis-range
            # option meant to be blank would silently constrain the figure.
            w.setSpecialValueText("(auto)")
            w.setValue(w.minimum())
            w.setProperty("mmf_optional", True)
            hint = "Leave at \u201c(auto)\u201d to let the figure choose."
            w.setToolTip(f"{w.toolTip()}\n{hint}" if w.toolTip() else hint)
        w.valueChanged.connect(self._schedule_render)   # debounced (continuous control)
        return w

    def _schedule_render(self, *_):
        """Debounced render for continuous controls (coalesces rapid changes)."""
        self._render_timer.start()

    def _collect_mapping(self) -> dict:
        mapping = {}
        for key, combo in self._mapping_widgets.items():
            val = combo.currentText()
            mapping[key] = None if val == "(none)" else val
        # Explicit value-column selection for matrix plots (heatmap/PCA/clustering).
        lw = getattr(self, "_value_cols_widget", None)
        if lw is not None:
            chosen = [i.text() for i in lw.selectedItems()]
            if chosen:
                mapping["value_columns"] = chosen
        # Other multi-column roles (e.g. survival_columns) collected the same way.
        for field, widget in (getattr(self, "_multi_col_widgets", None) or {}).items():
            picked = [i.text() for i in widget.selectedItems()]
            if picked:
                mapping[field] = picked
        for key, w in self._option_widgets.items():
            if isinstance(w, QCheckBox):
                mapping[key] = w.isChecked()
            elif isinstance(w, QComboBox):
                mapping[key] = w.currentText()
            elif isinstance(w, (QSpinBox, QDoubleSpinBox)):
                # An optional numeric sitting at its minimum reads as "(auto)": omit it so the
                # renderer applies its own default instead of being handed a sentinel.
                if w.property("mmf_optional") and w.value() == w.minimum():
                    continue
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

        if pt is None:
            # Back to the "no plot" placeholder — clear controls + figure, show prompt.
            self._rebuild_mapping_and_options()
            self.render_preview()
            return

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
        mapping = self._collect_mapping()
        # Shared layout controls (tick rotation / legend / margins / padding) + colorbar.
        _lay, _cb = self._collect_layout_controls()
        layout.update(_lay)
        mapping.update(_cb)
        # Merge worksheet provenance with any Matrix-Workflow handoff provenance so
        # the exported PlotSpec is traceable to its matrix/preprocessing/stats source.
        source = {**(self.data.source_provenance() or {}), **(self._handoff_provenance or {})}
        spec = self.controller.build_spec(
            pt, style, self.data.table_name, mapping,
            layout=layout, width=self.width_combo.currentText(), dpi=self.dpi_spin.value(),
            statistics=stats_spec, source=source or None)
        overrides = self._collect_style_overrides()
        if overrides:
            spec["style"] = overrides
        # Inject click-to-label picks for this plot type (stored in the PlotSpec
        # so they persist through export/reload).
        import json as _json
        point_picks = self._picked_points.get(pt)
        if point_picks:
            # Point-identity selection (volcano/MA duplicate-safe).
            spec.setdefault("mapping", {})["selected_points"] = list(point_picks)
            col = self._pick_cols.get(pt)
            if col:
                spec["mapping"]["label"] = col
            poffsets = {k: v for k, v in (self._point_offsets.get(pt) or {}).items()
                        if k in point_picks}
            if poffsets:
                spec["mapping"]["point_offsets"] = _json.dumps(poffsets)
        picks = self._picked_labels.get(pt)
        if picks:
            spec.setdefault("mapping", {})["selected_labels"] = list(picks)
            col = self._pick_cols.get(pt)
            if col:
                spec["mapping"]["label"] = col
        # Per-label manual offsets (from click-drag / move) persist in the PlotSpec.
        offsets = {k: v for k, v in (self._label_offsets.get(pt) or {}).items()
                   if not picks or k in picks}
        if offsets:
            spec.setdefault("mapping", {})["label_offsets"] = _json.dumps(offsets)
        # Group color strip from "Define groups" (wide/heatmap mode).
        if pt == "heatmap_clustered_matrix" and self._pending_column_annotations:
            spec["column_annotations"] = self._pending_column_annotations
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
        if self.data is None or getattr(self, "_loading_spec", False):
            return
        if self.plot_combo.currentData() is None:
            # No plot type chosen yet — show a prompt instead of drawing anything.
            self._clear_figure(show_placeholder=True)
            if self.fig_placeholder is not None:
                self.fig_placeholder.setText(
                    "Data loaded. Choose a plot type above to render a figure —\n"
                    "or click “🧮 Matrix workflow…” for a guided feature-matrix workflow.")
            self._current_result = None
            self._current_spec = None
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
            # The canvas may live inside the aspect-view holder; remove whichever
            # is actually in the layout.
            if self._fig_view is not None:
                self.fig_layout.removeWidget(self._fig_view)
                self._fig_view.setParent(None)
                self._fig_view.deleteLater()
                self._fig_view = None
            else:
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
        canvas.setFocusPolicy(Qt.StrongFocus)   # needed for key/scroll interactions
        toolbar = NavigationToolbar2QT(canvas, self.fig_container)
        toolbar.setObjectName("figureToolbar")
        self.fig_layout.addWidget(toolbar)
        # Keep the figure's aspect so the WHOLE plot is visible (not stretched/clipped).
        # Fall back to a plain expanding canvas if the aspect holder can't be built.
        try:
            w_in, h_in = fig.get_size_inches()
            view = _AspectView(canvas, float(w_in) / float(h_in) if h_in else 1.0,
                               self.fig_container)
            self.fig_layout.addWidget(view, 1)
            self._fig_view = view
        except Exception:
            canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.fig_layout.addWidget(canvas, 1)
            self._fig_view = None
        self._canvas = canvas
        self._toolbar = toolbar
        # Click-to-identify / label: map a click on the live canvas to a data
        # point (volcano/scatter) and optionally label it. Guarded so a wiring
        # issue can never break rendering.
        try:
            canvas.mpl_connect("button_press_event", self._on_canvas_pick)
        except Exception:
            pass
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

    # --- click-to-identify / label --------------------------------------
    def _on_click_label_toggled(self, on: bool) -> None:
        self._identify_mode = bool(on)
        if on:
            self.statusBar().showMessage(
                "Point picking on: click near a point (volcano/scatter) to "
                "identify and label it.", 5000)

    def _on_canvas_pick(self, event) -> None:
        """Map a canvas click to the nearest data point; identify + toggle a label."""
        if not self._identify_mode or self._current_result is None:
            return
        if event.inaxes is None or event.xdata is None or event.ydata is None:
            return
        meta = self._current_result.metadata or {}
        points = meta.get("pickable_points")
        if not points:
            self.statusBar().showMessage(
                "Point picking works on volcano and scatter plots.", 4000)
            return
        from make_my_figure_core.plots.base import nearest_pickable

        ax = event.inaxes
        xspan = abs(ax.get_xlim()[1] - ax.get_xlim()[0]) or 1.0
        yspan = abs(ax.get_ylim()[1] - ax.get_ylim()[0]) or 1.0
        best, dist = nearest_pickable(points, event.xdata, event.ydata, xspan, yspan)
        if best is None or dist > 0.05:      # click missed every point
            self.statusBar().showMessage("No point near the click.", 3000)
            return
        name = best["label"]
        self.statusBar().showMessage(
            f"{name}   (x={best['x']:.3g}, y={best['y']:.3g})", 8000)
        if self._current_spec is None:
            return
        # Toggle a label on the clicked point. Picks are kept per plot type (so
        # they survive the spec being rebuilt from the controls) and injected in
        # _build_spec, which stores them in the PlotSpec => persists on export.
        plot_type = self._current_spec.get("plot_type")
        col = meta.get("pick_label_column")
        # Renderers that support duplicate features (volcano/MA) toggle by POINT
        # identity so two rows sharing a gene symbol stay independent; older
        # renderers still toggle by label text.
        if meta.get("pick_label_key") == "selected_points":
            pid = best.get("point_id") or f"row_{best.get('index', 0)}"
            picks = self._picked_points.setdefault(plot_type, [])
            if pid in picks:
                picks.remove(pid)             # click the same point again to remove
                action = "removed label"
            else:
                picks.append(pid)
                action = "labeled"
        else:
            picks = self._picked_labels.setdefault(plot_type, [])
            if name in picks:
                picks.remove(name)            # click again to remove
                action = "removed label"
            else:
                picks.append(name)
                action = "labeled"
        if col:
            self._pick_cols[plot_type] = col
        self.statusBar().showMessage(f"{action}: {name}", 6000)
        self.render_preview()                 # re-render with the updated labels

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
        ms = getattr(self, "main_splitter", None)
        main_state = self.settings.value("main_splitter_state")
        ok = False
        if main_state is not None and ms is not None:
            try:
                ok = bool(ms.restoreState(main_state))
            except Exception:  # noqa: BLE001
                ok = False
        # Validate against a degenerate/stale persisted layout (collapsed control pane
        # or a left pane hogging the window); fall back to a proportional default.
        if ms is not None:
            sizes = ms.sizes()
            left = sizes[0] if sizes else 0
            total = sum(sizes)
            if (not ok) or left < 300 or (total > 0 and left > 0.6 * total):
                ms.setSizes([400, 820])
        right_state = self.settings.value("right_splitter_state")
        rs = getattr(self, "right_splitter", None)
        if right_state is not None and rs is not None:
            try:
                rs.restoreState(right_state)
            except Exception:  # noqa: BLE001
                pass

    def closeEvent(self, event):
        self._save_splitter_state()
        try:
            if getattr(self, "_panels", None) is not None:
                self._panels.save_state()
                self._panels.dock_all()   # avoid orphaned floating windows on quit
        except Exception:
            pass
        super().closeEvent(event)

    # --- export ----------------------------------------------------------
    def _ensure_rendered(self) -> bool:
        if self._current_result is None:
            self.render_preview()
        if self._current_result is None:
            QMessageBox.warning(self, "Nothing to export", "Load data and preview a figure first.")
            return False
        return True

    def _export_basename(self, pt: str) -> str:
        """Default export stem — sheet-aware so per-worksheet exports never collide."""
        prov = self.data.info.provenance() if (self.data and self.data.info) else {}
        wb_name = prov.get("source_workbook_name") or (
            self.data.table_name if self.data else "figure")
        return workbook_io.output_basename(wb_name, prov.get("source_sheet_name"), pt)

    def export_single(self, fmt: str):
        if not self._ensure_rendered():
            return
        pt = self.plot_combo.currentData()
        stem = self._export_basename(pt)
        if fmt == "json":
            dest, _ = QFileDialog.getSaveFileName(self, "Export PlotSpec JSON",
                                                  f"{stem}.plot_spec.json", "JSON (*.json)")
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
                                              f"{stem}.{fmt}", f"{fmt.upper()} (*.{fmt})")
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
        stem = self._export_basename(pt)
        dest, _ = QFileDialog.getSaveFileName(self, "Export all as ZIP",
                                              f"{stem}_bundle.zip", "ZIP (*.zip)")
        if not dest:
            return
        try:
            data = self.controller.export_bundle(
                self._current_spec, self._current_result,
                ["svg", "png", "pdf"], dpi=self.dpi_spin.value(), basename=stem)
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
            spec = ctrl.build_spec(pt, "publication", data.table_name, ctrl.default_mapping(pt))
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
