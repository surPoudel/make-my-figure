"""Desktop Statistics panel and Figure Builder dialog (PySide6).

Both widgets are thin: they collect configuration and call into
:class:`DesktopController` / the core statistics + panels engines. Keeping the
Qt here (and out of the controller) means the statistics logic stays testable
without an event loop.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from make_my_figure_core.statistics import TESTS
from make_my_figure_core.statistics.schemas import default_annotation

_NONE = "(none)"

TEST_CHOICES = [("auto", "Auto-suggest")] + [(tid, info.label) for tid, info in TESTS.items()]
MODE_CHOICES = [
    ("auto", "Automatic"),
    ("all_pairs", "Compare all groups (pairwise)"),
    ("vs_control", "Compare to control"),
    ("within_x", "Compare within each x category"),
    ("selected_pairs", "Selected pairs"),
    ("omnibus", "Omnibus only"),
]
CORRECTION_CHOICES = [
    ("benjamini_hochberg", "Benjamini-Hochberg FDR"),
    ("bonferroni", "Bonferroni"),
    ("holm", "Holm-Bonferroni"),
    ("none", "None"),
]
ANNOTATION_MODES = [("stars", "Stars (*, **)"), ("p", "Exact p-values"), ("both", "Stars + p")]

# Rich annotation content selector (Part 2).
# Where the annotation sits. "bracket" spans the two compared categories; "above_bar" puts one
# label over each compared bar and leaves the reference bar unmarked, which is the convention when
# every condition is tested against a single control - brackets would stack one per comparison and
# take most of the panel height.
ANNOTATION_PLACEMENT_CHOICES = [
    ("bracket", "Bracket between the compared bars"),
    ("above_bar", "Above each bar (needs a control group)"),
]

ANNOTATION_CONTENT_CHOICES = [
    ("stars", "Stars only"),
    ("p", "P-value only"),
    ("p_adj", "Adjusted p-value only"),
    ("p_stars", "P-value + stars"),
    ("stat", "Statistic only"),
    ("effect", "Effect size only"),
    ("p_stat", "P-value + statistic"),
    ("p_effect", "P-value + effect size"),
    ("full", "Full compact"),
    ("flags", "Custom (checkboxes)"),
    ("custom", "Custom template"),
]


class StatisticsPanel(QGroupBox):
    """Collapsible-ish statistics controls that produce a StatsSpec dict."""

    changed = Signal()
    runRequested = Signal()

    def __init__(self, controller, parent=None):
        super().__init__("6. Statistics", parent)
        self.controller = controller
        self._report = None
        self.setCheckable(True)
        self.setChecked(False)
        self.toggled.connect(lambda _=None: self.changed.emit())

        outer = QVBoxLayout(self)
        form = QFormLayout()

        self.enable_cb = QCheckBox("Enable statistics")
        self.enable_cb.stateChanged.connect(lambda _=None: self.changed.emit())
        form.addRow(self.enable_cb)

        self.test_combo = self._combo(TEST_CHOICES)
        form.addRow("Test", self.test_combo)
        self.mode_combo = self._combo(MODE_CHOICES)
        form.addRow("Comparison", self.mode_combo)

        self.group_combo = self._combo([(_NONE, _NONE)])
        self.subgroup_combo = self._combo([(_NONE, _NONE)])
        self.subject_combo = self._combo([(_NONE, _NONE)])
        self.reference_combo = self._combo([(_NONE, _NONE)])
        form.addRow("Group column", self.group_combo)
        form.addRow("Subgroup column", self.subgroup_combo)
        form.addRow("Subject/pair ID", self.subject_combo)
        form.addRow("Control group", self.reference_combo)

        self.correction_combo = self._combo(CORRECTION_CHOICES)
        form.addRow("Correction", self.correction_combo)

        self.annotation_combo = self._combo(ANNOTATION_CONTENT_CHOICES)
        form.addRow("Annotation shows", self.annotation_combo)
        self.placement_combo = self._combo(ANNOTATION_PLACEMENT_CHOICES)
        self.placement_combo.setToolTip(
            "Above-bar placement compares every condition to the control group and puts one label "
            "over each bar. Comparisons it cannot attribute to a single bar fall back to brackets.")
        form.addRow("Annotation placement", self.placement_combo)
        self.template_edit = QLineEdit()
        self.template_edit.setPlaceholderText("{effect_symbol} = {effect}, p = {p}")
        self.template_edit.setToolTip("Tokens: {p} {p_adj} {stars} {stat_symbol} {stat} "
                                      "{effect_symbol} {effect} {ci} {test_short} {n} {comparison}")
        self.template_edit.textChanged.connect(lambda _=None: self.changed.emit())
        self.template_edit.setVisible(False)
        form.addRow("Custom template", self.template_edit)
        self.annotation_combo.currentIndexChanged.connect(self._on_content_changed)
        self.show_effect_cb = QCheckBox("Show effect size on figure")
        self.show_effect_cb.stateChanged.connect(lambda _=None: self.changed.emit())
        form.addRow(self.show_effect_cb)
        self.hide_ns_cb = QCheckBox("Hide non-significant annotations")
        self.hide_ns_cb.stateChanged.connect(lambda _=None: self.changed.emit())
        form.addRow(self.hide_ns_cb)
        self.posthoc_cb = QCheckBox("Post-hoc pairwise after omnibus")
        self.posthoc_cb.stateChanged.connect(lambda _=None: self.changed.emit())
        form.addRow(self.posthoc_cb)

        self.digits_spin = QSpinBox()
        self.digits_spin.setRange(1, 6)
        self.digits_spin.setValue(3)
        self.digits_spin.valueChanged.connect(lambda _=None: self.changed.emit())
        form.addRow("P-value decimals", self.digits_spin)
        self.fontsize_spin = QDoubleSpinBox()
        self.fontsize_spin.setRange(4.0, 24.0)
        self.fontsize_spin.setValue(9.5)
        self.fontsize_spin.setSingleStep(0.5)
        self.fontsize_spin.valueChanged.connect(lambda _=None: self.changed.emit())
        form.addRow("Annotation font pt", self.fontsize_spin)
        outer.addLayout(form)

        # Buttons.
        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("Run statistics")
        self.run_btn.clicked.connect(self.runRequested.emit)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._on_clear)
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self._on_reset)
        for b in (self.run_btn, self.clear_btn, self.reset_btn):
            btn_row.addWidget(b)
        outer.addLayout(btn_row)

        self.suggest_label = QLabel("")
        self.suggest_label.setWordWrap(True)
        self.suggest_label.setStyleSheet("color: #555; font-size: 11px;")
        outer.addWidget(self.suggest_label)

        # Results table + method text.
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Comparison", "Test", "p", "adj p", "effect", "n"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(120)
        outer.addWidget(self.table)

        self.method_text = QPlainTextEdit()
        self.method_text.setReadOnly(True)
        self.method_text.setPlaceholderText("Method sentence appears here after running statistics.")
        self.method_text.setMaximumHeight(90)
        outer.addWidget(self.method_text)

        exp_row = QHBoxLayout()
        self.export_table_btn = QPushButton("Export stats table")
        self.export_table_btn.clicked.connect(self._on_export_table)
        self.export_method_btn = QPushButton("Export method report")
        self.export_method_btn.clicked.connect(self._on_export_method)
        self.copy_method_btn = QPushButton("Copy method sentence")
        self.copy_method_btn.clicked.connect(self._on_copy_method)
        for b in (self.export_table_btn, self.export_method_btn, self.copy_method_btn):
            exp_row.addWidget(b)
        outer.addLayout(exp_row)

    # --- helpers ---------------------------------------------------------
    def _combo(self, choices) -> QComboBox:
        c = QComboBox()
        for value, label in choices:
            c.addItem(label, value)
        c.currentIndexChanged.connect(lambda _=None: self.changed.emit())
        return c

    def set_columns(self, columns: List[str]) -> None:
        """Populate the column choosers (keeps current selection if still valid)."""
        opts = [_NONE] + [c for c in columns if c and c != _NONE]
        for combo in (self.group_combo, self.subgroup_combo, self.subject_combo, self.reference_combo):
            current = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            for o in opts:
                combo.addItem(o, o)
            if current in opts:
                combo.setCurrentText(current)
            combo.blockSignals(False)

    def set_reference_values(self, values: List[str]) -> None:
        current = self.reference_combo.currentData()
        self.reference_combo.blockSignals(True)
        self.reference_combo.clear()
        self.reference_combo.addItem(_NONE, _NONE)
        for v in values:
            self.reference_combo.addItem(str(v), str(v))
        if current:
            self.reference_combo.setCurrentText(str(current))
        self.reference_combo.blockSignals(False)

    def set_suggestions(self, rec: Dict[str, Any]) -> None:
        notes = " ".join(rec.get("notes", []))
        primary = rec.get("primary")
        txt = ""
        if primary:
            label = dict(TEST_CHOICES).get(primary, primary)
            txt = f"Suggested: {label}. {notes}"
        elif notes:
            txt = notes
        self.suggest_label.setText(txt)

    def is_enabled(self) -> bool:
        return self.isChecked() and self.enable_cb.isChecked()

    def _on_content_changed(self) -> None:
        self.template_edit.setVisible(self.annotation_combo.currentData() == "custom")
        self.changed.emit()

    def stats_spec(self) -> Dict[str, Any]:
        content = self.annotation_combo.currentData()
        ann = default_annotation()
        ann.update({
            "content": content,
            "template": self.template_edit.text().strip(),
            "digits": self.digits_spin.value(),
            "show_effect": self.show_effect_cb.isChecked(),
            "hide_nonsignificant": self.hide_ns_cb.isChecked(),
            "font_size": self.fontsize_spin.value(),
            "placement": self.placement_combo.currentData(),
        })

        def _val(combo):
            v = combo.currentData()
            return None if v in (None, _NONE) else v

        return {
            "enabled": self.is_enabled(),
            "test": self.test_combo.currentData(),
            "comparison_mode": self.mode_combo.currentData(),
            "correction": self.correction_combo.currentData(),
            "posthoc": self.posthoc_cb.isChecked(),
            "group_column": _val(self.group_combo),
            "subgroup_column": _val(self.subgroup_combo),
            "subject_column": _val(self.subject_combo),
            "reference_group": _val(self.reference_combo),
            "annotate": True,
            "annotation": ann,
        }

    def load_spec(self, stats: Dict[str, Any]) -> None:
        """Populate the controls from a stored statistics spec (reverse of
        :meth:`stats_spec`). Used when reopening a saved PlotSpec so re-rendering
        after an edit keeps the figure's statistical annotations."""
        if not isinstance(stats, dict):
            return

        def _set(combo, value):
            if value in (None, "", _NONE):
                return
            for i in range(combo.count()):
                if combo.itemData(i) == value:
                    combo.setCurrentIndex(i)
                    return
            # a reference value not yet in the list: add it so it round-trips
            combo.addItem(str(value), value)
            combo.setCurrentIndex(combo.count() - 1)

        self.setChecked(True)
        self.enable_cb.setChecked(bool(stats.get("enabled", True)))
        _set(self.test_combo, stats.get("test"))
        _set(self.mode_combo, stats.get("comparison_mode"))
        _set(self.correction_combo, stats.get("correction"))
        self.posthoc_cb.setChecked(bool(stats.get("posthoc", False)))
        _set(self.group_combo, stats.get("group_column"))
        _set(self.subgroup_combo, stats.get("subgroup_column"))
        _set(self.subject_combo, stats.get("subject_column"))
        _set(self.reference_combo, stats.get("reference_group"))
        ann = stats.get("annotation") or {}
        _set(self.annotation_combo, ann.get("content"))
        if ann.get("template"):
            self.template_edit.setText(str(ann["template"]))
        if ann.get("digits") is not None:
            try:
                self.digits_spin.setValue(int(ann["digits"]))
            except (TypeError, ValueError):
                pass
        if ann.get("font_size") is not None:
            try:
                self.fontsize_spin.setValue(float(ann["font_size"]))
            except (TypeError, ValueError):
                pass
        _set(self.placement_combo, ann.get("placement") or "bracket")
        self.show_effect_cb.setChecked(bool(ann.get("show_effect", False)))
        self.hide_ns_cb.setChecked(bool(ann.get("hide_nonsignificant", False)))
        self._on_content_changed()

    def show_report(self, report) -> None:
        """Populate the table + method text from a StatsReport (or clear)."""
        self._report = report
        self.table.setRowCount(0)
        if report is None:
            self.method_text.setPlainText("")
            return
        rows = self.controller.stats_table_rows(report)
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, key in enumerate(["comparison", "test", "p_value", "adjusted_p", "effect_size", "n"]):
                self.table.setItem(i, j, QTableWidgetItem(str(row.get(key, ""))))
        text = report.method_paragraph or ""
        if report.warnings:
            text += "\n\nWarnings: " + " | ".join(report.warnings)
        self.method_text.setPlainText(text)

    # --- button handlers -------------------------------------------------
    def _on_clear(self) -> None:
        self.enable_cb.setChecked(False)
        self.show_report(None)
        self.changed.emit()

    def _on_reset(self) -> None:
        self.test_combo.setCurrentIndex(0)
        self.mode_combo.setCurrentIndex(0)
        self.correction_combo.setCurrentIndex(0)
        self.annotation_combo.setCurrentIndex(0)
        self.template_edit.clear()
        self.template_edit.setVisible(False)
        self.digits_spin.setValue(3)
        self.fontsize_spin.setValue(9.5)
        self.show_effect_cb.setChecked(False)
        self.hide_ns_cb.setChecked(False)
        self.posthoc_cb.setChecked(False)
        self.changed.emit()

    def _on_export_table(self) -> None:
        if self._report is None:
            QMessageBox.information(self, "No statistics", "Run statistics first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export statistics table", "statistics.csv",
                                              "CSV (*.csv);;TSV (*.tsv)")
        if not path:
            return
        sep = "\t" if path.lower().endswith(".tsv") else ","
        self.controller.export_stats_table(self._report, path, sep=sep)

    def _on_export_method(self) -> None:
        if self._report is None:
            QMessageBox.information(self, "No statistics", "Run statistics first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export method report", "methods.md",
                                              "Markdown (*.md);;JSON (*.json)")
        if not path:
            return
        fmt = "json" if path.lower().endswith(".json") else "markdown"
        self.controller.export_method_report(self._report, path, fmt=fmt)

    def _on_copy_method(self) -> None:
        if self._report is None:
            return
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(self._report.method_paragraph or "")


class FigureBuilderDialog(QDialog):
    """Assemble saved panels into a multi-panel composite.

    Left: controls (order, per-panel size in inches, fonts). Right: a LIVE
    preview that re-renders on every change, so the figure can be laid out and
    tuned before it's ever saved. Nothing is written until "Save figure...".
    """

    # Publication-ready font defaults (points), matching the style profile.
    _FONT_DEFAULTS = {"text": 11.0, "axis": 12.0, "tick": 10.0, "legend": 10.0, "label": 14.0}

    def __init__(self, controller, saved_panels: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Multi-panel Figure Builder")
        self.controller = controller
        self.saved_panels = saved_panels
        # Give every panel an explicit default width so the size field matches
        # what's drawn; height stays "auto" (follows the panel's own ratio).
        for p in self.saved_panels:
            p.setdefault("width_in", 3.2)
            p.setdefault("height_in", None)
        self._composite = None
        self._syncing = False           # guard against feedback while loading fields
        # Managed assets folder for imported external panels (copied on import).
        import tempfile

        self._assets_dir = tempfile.mkdtemp(prefix="mmf_figure_builder_assets_")
        self.resize(980, 640)

        # Debounce timer: coalesce rapid control changes into one re-render.
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(250)
        self._preview_timer.timeout.connect(self._update_preview)

        split = QSplitter(Qt.Horizontal, self)
        split.addWidget(self._build_controls())
        split.addWidget(self._build_preview())
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)

        outer = QVBoxLayout(self)
        outer.addWidget(split)

        self._refresh_list()
        if self.saved_panels:
            self.list.setCurrentRow(0)
        self._schedule_preview()

    # --- construction -------------------------------------------------------
    def _build_controls(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)

        form = QFormLayout()
        self.name_combo = QComboBox()
        self.name_combo.setEditable(True)
        self.name_combo.addItems(["Figure 1", "Figure 2", "Extended Data Figure 1",
                                  "Supplementary Figure 1"])
        self.name_combo.currentTextChanged.connect(self._schedule_preview)
        form.addRow("Figure name", self.name_combo)
        self.cols_combo = QComboBox()
        self.cols_combo.addItems(["Auto", "1", "2", "3", "4"])
        self.cols_combo.currentTextChanged.connect(self._schedule_preview)
        form.addRow("Columns", self.cols_combo)
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(300)
        form.addRow("Export DPI", self.dpi_spin)
        v.addLayout(form)

        v.addWidget(QLabel("Panels (order = A, B, C ...):"))
        imp_row = QHBoxLayout()
        imp_btn = QPushButton("Import panel from file…")
        imp_btn.setToolTip("Add an existing figure (PNG/JPG/TIFF/PDF/SVG) as a panel")
        imp_btn.clicked.connect(self._import_panel)
        imp_row.addWidget(imp_btn)
        imp_row.addStretch(1)
        v.addLayout(imp_row)
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._on_panel_selected)
        v.addWidget(self.list)

        row = QHBoxLayout()
        up = QPushButton("Move up"); up.clicked.connect(lambda: self._move(-1))
        down = QPushButton("Move down"); down.clicked.connect(lambda: self._move(1))
        rm = QPushButton("Remove"); rm.clicked.connect(self._remove)
        dup = QPushButton("Duplicate"); dup.clicked.connect(self._duplicate)
        for b in (up, down, rm, dup):
            row.addWidget(b)
        v.addLayout(row)

        # --- per-panel size (inches) ---
        self.size_group = QGroupBox("Selected panel size")
        sg = QFormLayout(self.size_group)
        hint = QLabel("Approximate size in inches (1 in = 2.54 cm). Width × height, "
                      "like Matplotlib's figsize — e.g. 4×4 is square, 4×6 is taller. "
                      "The panel keeps its own proportions (never stretched), so a larger "
                      "number just makes a larger version of the same figure.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        sg.addRow(hint)
        self.pw_spin = QDoubleSpinBox()
        self.pw_spin.setRange(1.0, 12.0); self.pw_spin.setSingleStep(0.5)
        self.pw_spin.setValue(3.2); self.pw_spin.setSuffix(" in")
        self.pw_spin.valueChanged.connect(self._on_size_changed)
        sg.addRow("Width", self.pw_spin)
        self.ph_spin = QDoubleSpinBox()
        self.ph_spin.setRange(0.0, 12.0); self.ph_spin.setSingleStep(0.5)
        self.ph_spin.setValue(0.0); self.ph_spin.setSuffix(" in")
        self.ph_spin.setSpecialValueText("auto (keep ratio)")
        self.ph_spin.valueChanged.connect(self._on_size_changed)
        sg.addRow("Height", self.ph_spin)
        self.size_group.setEnabled(False)
        v.addWidget(self.size_group)

        # --- figure-wide fonts ---
        font_group = QGroupBox("Fonts (points, applied to all panels)")
        fg = QFormLayout(font_group)
        self.text_spin = self._font_spin(self._FONT_DEFAULTS["text"])
        self.axis_spin = self._font_spin(self._FONT_DEFAULTS["axis"])
        self.tick_spin = self._font_spin(self._FONT_DEFAULTS["tick"])
        self.legend_spin = self._font_spin(self._FONT_DEFAULTS["legend"])
        self.label_spin = self._font_spin(self._FONT_DEFAULTS["label"])
        fg.addRow("Text (general)", self.text_spin)
        fg.addRow("Axis labels", self.axis_spin)
        fg.addRow("Tick numbers", self.tick_spin)
        fg.addRow("Legend", self.legend_spin)
        fg.addRow("Panel letters (A, B ...)", self.label_spin)
        v.addWidget(font_group)

        self.legend_text = QPlainTextEdit()
        self.legend_text.setReadOnly(True)
        self.legend_text.setPlaceholderText("Draft legend appears here.")
        self.legend_text.setMaximumHeight(80)
        v.addWidget(self.legend_text)

        act = QHBoxLayout()
        save = QPushButton("Save figure..."); save.clicked.connect(self._save)
        act.addWidget(save)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        act.addWidget(close)
        v.addLayout(act)

        w.setMaximumWidth(430)
        return w

    def _font_spin(self, default: float) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(4.0, 40.0); s.setSingleStep(0.5); s.setValue(default); s.setSuffix(" pt")
        s.valueChanged.connect(self._schedule_preview)
        return s

    def _build_preview(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(QLabel("Live preview"))
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setStyleSheet("background: #f5f5f5;")
        self.preview_label = QLabel("Preview appears here.")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_scroll.setWidget(self.preview_label)
        v.addWidget(self.preview_scroll)
        return w

    # --- panel list ---------------------------------------------------------
    def _refresh_list(self) -> None:
        self.list.clear()
        import string

        for i, p in enumerate(self.saved_panels):
            label = string.ascii_uppercase[i] if i < 26 else f"P{i+1}"
            title = p.get("title") or p.get("plot_type", "panel")
            QListWidgetItem(f"{label}. {title}", self.list)

    def _on_panel_selected(self, i: int) -> None:
        if not (0 <= i < len(self.saved_panels)):
            self.size_group.setEnabled(False)
            return
        self._syncing = True
        p = self.saved_panels[i]
        self.size_group.setEnabled(True)
        self.pw_spin.setValue(float(p.get("width_in") or 3.2))
        self.ph_spin.setValue(float(p.get("height_in") or 0.0))
        self._syncing = False

    def _on_size_changed(self, _=None) -> None:
        if self._syncing:
            return
        i = self.list.currentRow()
        if 0 <= i < len(self.saved_panels):
            self.saved_panels[i]["width_in"] = float(self.pw_spin.value())
            h = float(self.ph_spin.value())
            self.saved_panels[i]["height_in"] = h if h > 0 else None
        self._schedule_preview()

    def _move(self, delta: int) -> None:
        i = self.list.currentRow()
        j = i + delta
        if 0 <= i < len(self.saved_panels) and 0 <= j < len(self.saved_panels):
            self.saved_panels[i], self.saved_panels[j] = self.saved_panels[j], self.saved_panels[i]
            self._refresh_list()
            self.list.setCurrentRow(j)
            self._schedule_preview()

    def _remove(self) -> None:
        i = self.list.currentRow()
        if 0 <= i < len(self.saved_panels):
            self.saved_panels.pop(i)
            self._refresh_list()
            self._schedule_preview()

    def _duplicate(self) -> None:
        i = self.list.currentRow()
        if 0 <= i < len(self.saved_panels):
            import copy

            self.saved_panels.insert(i + 1, copy.deepcopy(self.saved_panels[i]))
            self._refresh_list()
            self._schedule_preview()

    # --- building -----------------------------------------------------------
    def _make_layout(self):
        from make_my_figure_core.panels import FigureLayout

        ncols_txt = self.cols_combo.currentText()
        ncols = None if ncols_txt == "Auto" else int(ncols_txt)
        return FigureLayout(
            ncols=ncols,
            panel_dpi=self.dpi_spin.value(),
            label_size=float(self.label_spin.value()),
            base_font_pt=float(self.text_spin.value()),
            axis_font_pt=float(self.axis_spin.value()),
            tick_label_pt=float(self.tick_spin.value()),
            legend_pt=float(self.legend_spin.value()),
        )

    def _build_mpf(self):
        from make_my_figure_core.panels import MultiPanelFigure, Panel

        mpf = MultiPanelFigure(name=self.name_combo.currentText(), layout=self._make_layout())
        for p in self.saved_panels:
            if p.get("image_path"):   # imported external-figure panel
                mpf.add_panel(Panel(
                    title=p.get("title", ""), width_in=p.get("width_in"),
                    height_in=p.get("height_in"), image_path=p["image_path"],
                    image_meta=p.get("image_meta") or {}, fit_mode=p.get("fit_mode", "contain"),
                    border=bool(p.get("border", False)), auto_trim=bool(p.get("auto_trim", False)),
                    rotate=int(p.get("rotate", 0)), background=p.get("background", "white"),
                    crop=p.get("crop") or {}, annotations=p.get("annotations") or [],
                    source_name=(p.get("image_meta") or {}).get("original_filename", "")))
            else:
                mpf.add_panel(Panel(
                    plot_spec=p.get("plot_spec"), table=p.get("table"),
                    aux=p.get("aux") or {}, title=p.get("title", ""),
                    stats_spec=(p.get("plot_spec") or {}).get("statistics"),
                    width_in=p.get("width_in"), height_in=p.get("height_in")))
        return mpf

    def _import_panel(self) -> None:
        """Import an external figure file (PNG/JPG/TIFF/PDF/SVG) as a new panel."""
        from make_my_figure_core.panels import import_external_panel

        path, _ = QFileDialog.getOpenFileName(
            self, "Import figure panel", "",
            "Figures (*.png *.jpg *.jpeg *.tif *.tiff *.webp *.bmp *.pdf *.svg);;All files (*)")
        if not path:
            return
        panel, asset = import_external_panel(path, self._assets_dir, width_in=3.2)
        if asset.error:
            QMessageBox.warning(self, "Could not import", asset.error)
            return
        meta = dict(asset.metadata)
        meta["warnings"] = list(asset.warnings)
        self.saved_panels.append({
            "image_path": panel.image_path, "image_meta": meta, "width_in": 3.2,
            "title": "", "fit_mode": "contain",
            "plot_type": f"imported:{meta.get('file_type', 'file')}",
        })
        self._refresh_list()
        self.list.setCurrentRow(len(self.saved_panels) - 1)
        if asset.warnings:
            QMessageBox.information(self, "Imported (with notes)", "\n".join(asset.warnings))
        self._schedule_preview()

    def _schedule_preview(self, *args) -> None:
        self._preview_timer.start()

    def _update_preview(self) -> None:
        import io

        import matplotlib.pyplot as plt

        from make_my_figure_core.panels import build_figure, draft_legend

        if not self.saved_panels:
            self.preview_label.setText("Save at least one plot as a panel first.")
            return
        mpf = self._build_mpf()
        try:
            fig = build_figure(mpf)
        except Exception as exc:  # noqa: BLE001 - surface errors in the preview pane
            self.preview_label.setText(f"Preview error:\n{exc}")
            return
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=110, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        pix = QPixmap()
        pix.loadFromData(buf.getvalue())
        avail = self.preview_scroll.viewport().width() - 8
        if avail > 40 and pix.width() > avail:
            pix = pix.scaledToWidth(avail, Qt.SmoothTransformation)
        self.preview_label.setPixmap(pix)
        mpf.legend_text = draft_legend(mpf)
        self.legend_text.setPlainText(mpf.legend_text)

    def _save(self) -> None:
        if not self.saved_panels:
            QMessageBox.information(self, "No panels", "Save at least one plot as a panel first.")
            return
        from make_my_figure_core.panels import (
            build_figure,
            draft_legend,
            export_multipanel,
            multipanel_sidecar,
        )

        mpf = self._build_mpf()
        try:
            fig = build_figure(mpf)
        except Exception as exc:
            QMessageBox.critical(self, "Build failed", str(exc))
            return
        mpf.legend_text = draft_legend(mpf)
        path, _ = QFileDialog.getSaveFileName(self, "Save multi-panel figure",
                                              f"{mpf.name.replace(' ', '_')}.png",
                                              "PNG (*.png);;SVG (*.svg);;PDF (*.pdf)")
        if not path:
            return
        base, ext = path.rsplit(".", 1) if "." in path else (path, "png")
        export_multipanel(fig, base, [ext.lower(), "svg", "pdf"], dpi=self.dpi_spin.value())
        multipanel_sidecar(mpf, base)
        # Copy imported assets next to the figure so the FigureSpec reloads them.
        extra = ""
        if any(p.get("image_path") for p in self.saved_panels):
            import os
            import shutil

            dest = os.path.join(os.path.dirname(os.path.abspath(base)), "figure_builder_assets")
            os.makedirs(dest, exist_ok=True)
            for p in self.saved_panels:
                src = p.get("image_path")
                if src and os.path.exists(src):
                    shutil.copy2(src, os.path.join(dest, os.path.basename(src)))
            extra = "\nImported panel assets copied to ./figure_builder_assets/ — keep this " \
                    "folder with the FigureSpec to reload the figure."
        import matplotlib.pyplot as plt

        plt.close(fig)
        QMessageBox.information(self, "Saved", f"Wrote {mpf.name} and sidecar next to:\n{path}{extra}")
