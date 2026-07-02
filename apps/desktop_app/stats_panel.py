"""Desktop Statistics panel and Figure Builder dialog (PySide6).

Both widgets are thin: they collect configuration and call into
:class:`DesktopController` / the core statistics + panels engines. Keeping the
Qt here (and out of the controller) means the statistics logic stays testable
without an event loop.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
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
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
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

        self.annotation_combo = self._combo(ANNOTATION_MODES)
        form.addRow("Annotation", self.annotation_combo)
        self.show_effect_cb = QCheckBox("Show effect size on figure")
        self.show_effect_cb.stateChanged.connect(lambda _=None: self.changed.emit())
        form.addRow(self.show_effect_cb)
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

    def stats_spec(self) -> Dict[str, Any]:
        ann = default_annotation()
        ann.update({
            "mode": self.annotation_combo.currentData(),
            "digits": self.digits_spin.value(),
            "show_effect": self.show_effect_cb.isChecked(),
            "font_size": self.fontsize_spin.value(),
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
        self.digits_spin.setValue(3)
        self.fontsize_spin.setValue(9.5)
        self.show_effect_cb.setChecked(False)
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
    """Assemble saved panels into a multi-panel composite and export it."""

    def __init__(self, controller, saved_panels: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Multi-panel Figure Builder")
        self.controller = controller
        self.saved_panels = saved_panels
        self._composite = None
        self.resize(560, 520)

        v = QVBoxLayout(self)
        form = QFormLayout()
        self.name_combo = QComboBox()
        self.name_combo.setEditable(True)
        self.name_combo.addItems(["Figure 1", "Figure 2", "Extended Data Figure 1",
                                  "Supplementary Figure 1"])
        form.addRow("Figure name", self.name_combo)
        self.cols_combo = QComboBox()
        self.cols_combo.addItems(["Auto", "1", "2", "3", "4"])
        form.addRow("Columns", self.cols_combo)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(60, 400)
        self.width_spin.setValue(180)
        form.addRow("Figure width (mm)", self.width_spin)
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(300)
        form.addRow("Panel DPI", self.dpi_spin)
        v.addLayout(form)

        v.addWidget(QLabel("Panels (order = A, B, C ...):"))
        self.list = QListWidget()
        self._refresh_list()
        v.addWidget(self.list)

        row = QHBoxLayout()
        up = QPushButton("Move up"); up.clicked.connect(lambda: self._move(-1))
        down = QPushButton("Move down"); down.clicked.connect(lambda: self._move(1))
        rm = QPushButton("Remove"); rm.clicked.connect(self._remove)
        dup = QPushButton("Duplicate"); dup.clicked.connect(self._duplicate)
        for b in (up, down, rm, dup):
            row.addWidget(b)
        v.addLayout(row)

        self.legend_text = QPlainTextEdit()
        self.legend_text.setReadOnly(True)
        self.legend_text.setPlaceholderText("Draft legend appears here after building.")
        self.legend_text.setMaximumHeight(90)
        v.addWidget(self.legend_text)

        act = QHBoxLayout()
        build = QPushButton("Build && export"); build.clicked.connect(self._build_export)
        act.addWidget(build)
        v.addLayout(act)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _refresh_list(self) -> None:
        self.list.clear()
        import string

        for i, p in enumerate(self.saved_panels):
            label = string.ascii_uppercase[i] if i < 26 else f"P{i+1}"
            title = p.get("title") or p.get("plot_type", "panel")
            QListWidgetItem(f"{label}. {title}", self.list)

    def _move(self, delta: int) -> None:
        i = self.list.currentRow()
        j = i + delta
        if 0 <= i < len(self.saved_panels) and 0 <= j < len(self.saved_panels):
            self.saved_panels[i], self.saved_panels[j] = self.saved_panels[j], self.saved_panels[i]
            self._refresh_list()
            self.list.setCurrentRow(j)

    def _remove(self) -> None:
        i = self.list.currentRow()
        if 0 <= i < len(self.saved_panels):
            self.saved_panels.pop(i)
            self._refresh_list()

    def _duplicate(self) -> None:
        i = self.list.currentRow()
        if 0 <= i < len(self.saved_panels):
            import copy

            self.saved_panels.insert(i + 1, copy.deepcopy(self.saved_panels[i]))
            self._refresh_list()

    def _build_export(self) -> None:
        if not self.saved_panels:
            QMessageBox.information(self, "No panels", "Save at least one plot as a panel first.")
            return
        from make_my_figure_core.panels import (
            FigureLayout,
            MultiPanelFigure,
            Panel,
            build_figure,
            draft_legend,
            export_multipanel,
            multipanel_sidecar,
        )

        ncols_txt = self.cols_combo.currentText()
        ncols = None if ncols_txt == "Auto" else int(ncols_txt)
        layout = FigureLayout(ncols=ncols, fig_width_mm=float(self.width_spin.value()),
                              panel_dpi=self.dpi_spin.value())
        mpf = MultiPanelFigure(name=self.name_combo.currentText(), layout=layout)
        for p in self.saved_panels:
            mpf.add_panel(Panel(plot_spec=p.get("plot_spec"), table=p.get("table"),
                                aux=p.get("aux") or {}, title=p.get("title", ""),
                                stats_spec=(p.get("plot_spec") or {}).get("statistics")))
        try:
            fig = build_figure(mpf)
        except Exception as exc:
            QMessageBox.critical(self, "Build failed", str(exc))
            return
        mpf.legend_text = draft_legend(mpf)
        self.legend_text.setPlainText(mpf.legend_text)
        path, _ = QFileDialog.getSaveFileName(self, "Export multi-panel figure",
                                              f"{mpf.name.replace(' ', '_')}.png",
                                              "PNG (*.png);;SVG (*.svg);;PDF (*.pdf)")
        if not path:
            return
        base, ext = path.rsplit(".", 1) if "." in path else (path, "png")
        export_multipanel(fig, base, [ext.lower(), "svg", "pdf"], dpi=self.dpi_spin.value())
        multipanel_sidecar(mpf, base)
        QMessageBox.information(self, "Exported", f"Wrote {mpf.name} and sidecar next to:\n{path}")
