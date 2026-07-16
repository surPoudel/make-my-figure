"""Guided matrix workflow for the desktop app (thin Qt over the controller).

Steps (tabs, gated by confirmation): ① map columns -> ② define groups ->
③ validation -> ④ recommend & generate. Heavy work (the feature-level
differential summary) runs on a background thread so the UI stays responsive,
with a busy state and cancel. Generated plots can be saved (PNG/SVG/PDF) or added
to the Figure Builder. No silent guessing: annotation columns are not values, and
nothing renders until the mapping is confirmed. Generic feature matrix — no
raw-count pipeline, no R.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
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
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from make_my_figure_core.plots.registry import export_figure, figure_to_bytes

_NONE = "(none)"


class _Worker(QThread):
    """Run a callable off the UI thread; emit its result or an error string."""

    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn):
        super().__init__()
        self._fn = fn
        self._cancelled = False

    def run(self):  # noqa: D401 - QThread entry point
        try:
            result = self._fn()
        except Exception as exc:  # noqa: BLE001
            if not self._cancelled:
                self.failed.emit(str(exc))
            return
        if not self._cancelled:
            self.done.emit(result)

    def cancel(self):
        self._cancelled = True


class MatrixWizardDialog(QDialog):
    """Map a feature matrix, define groups, recommend + generate plots."""

    def __init__(self, controller, data, saved_panels: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.controller = controller
        self.data = data
        self.saved_panels = saved_panels
        self.matrix_spec = None
        self.metadata = None
        self.diff_table = None
        self._current = None      # (spec, result, PlotInputs) for the previewed plot
        self._worker: Optional[_Worker] = None

        self.setWindowTitle("Matrix workflow")
        self.resize(820, 720)
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Map a feature-by-sample matrix, define groups, then generate publication "
            "plots. Nothing is plotted until you confirm the mapping — annotation columns "
            "are never treated as measurements. Generic feature matrix (no raw-count "
            "pipeline, no R).")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self._raw_data = None          # stash of the pre-preprocessing data (for revert)
        self._raw_spec = None
        self._prep_spec = None         # applied PreprocessingSpec (for traceable stats)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_map_tab(), "① Map columns")
        self.tabs.addTab(self._build_groups_tab(), "② Define groups")
        self.tabs.addTab(self._build_preprocess_tab(), "③ Preprocess (raw-like)")
        self.tabs.addTab(self._build_validate_tab(), "④ Validation")
        self.tabs.addTab(self._build_generate_tab(), "⑤ Recommend & generate")
        for i in (1, 2, 3, 4):
            self.tabs.setTabEnabled(i, False)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs)

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close)

    def _scrollable(self, w: QWidget) -> QScrollArea:
        """Wrap a tab body so its buttons are never clipped (high-DPI / small screens)."""
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setWidget(w)
        return sa

    # --- Step 1: map columns --------------------------------------------
    def _build_map_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        cols = list(self.data.info.columns)
        sug = self.controller.matrix_suggest_spec(self.data)

        form = QFormLayout()
        self.feature_combo = QComboBox()
        self.feature_combo.addItems(cols)
        if sug.feature_id_column in cols:
            self.feature_combo.setCurrentText(sug.feature_id_column)
        self.display_combo = QComboBox()
        self.display_combo.addItems([_NONE] + cols)
        if sug.feature_display_column in cols:
            self.display_combo.setCurrentText(sug.feature_display_column)
        self.vtype_combo = QComboBox()
        self.vtype_combo.addItems(list(self.controller.matrix_value_types()))
        self.vtype_combo.setCurrentText("unknown_user_confirmed")
        form.addRow("Feature ID column", self.feature_combo)
        form.addRow("Feature display column", self.display_combo)
        form.addRow("Value scale (you confirm)", self.vtype_combo)
        v.addLayout(form)

        v.addWidget(QLabel("Select the VALUE (sample/measurement) columns. Numeric "
                           "annotation columns (e.g. a 1/2/3 level code) are left "
                           "unselected by default — check them only if they are real "
                           "measurements. Everything unselected becomes an annotation."))
        self.value_list = QListWidget()
        self.value_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.value_list.setMaximumHeight(220)
        value_set = set(map(str, sug.value_columns))
        for c in cols:
            it = QListWidgetItem(str(c))
            self.value_list.addItem(it)
            it.setSelected(str(c) in value_set)
        v.addWidget(self.value_list)

        self.map_note = QLabel("")
        self.map_note.setStyleSheet("color:#345; font-size:11px;")
        self.map_note.setWordWrap(True)
        v.addWidget(self.map_note)

        confirm = QPushButton("Confirm mapping")
        confirm.setStyleSheet("font-weight:bold; padding:6px;")
        confirm.clicked.connect(self._confirm_mapping)
        v.addWidget(confirm)
        v.addStretch(1)
        return self._scrollable(w)

    def _confirm_mapping(self):
        import make_my_figure_core.matrix_workflow as mw

        feature_id = self.feature_combo.currentText()
        display = self.display_combo.currentText()
        display = None if display == _NONE else display
        value_cols = [i.text() for i in self.value_list.selectedItems()
                      if i.text() not in (feature_id, display)]
        if not value_cols:
            QMessageBox.warning(self, "No value columns", "Select at least one value column.")
            return
        annotation = [c for c in self.data.info.columns
                      if c not in (feature_id, display) and c not in value_cols]
        self.matrix_spec = mw.MatrixSpec(
            source_file=self.data.table_name, feature_id_column=feature_id,
            feature_display_column=display, annotation_columns=annotation,
            value_columns=value_cols, value_type=self.vtype_combo.currentText(),
            confirmed_by_user=True)
        self.diff_table = None
        self.map_note.setText(f"Confirmed: {len(value_cols)} value columns; "
                              f"{len(annotation)} annotation column(s).")
        for i in (1, 2, 3, 4):
            self.tabs.setTabEnabled(i, True)
        self._refresh_groups_tab()

    # --- Step 2: groups --------------------------------------------------
    def _build_groups_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Assign each value column to a group (edit the Group column; "
                           "leave blank to exclude a column):"))
        self.group_table = QTableWidget(0, 2)
        self.group_table.setHorizontalHeaderLabels(["Sample column", "Group"])
        self.group_table.horizontalHeader().setStretchLastSection(True)
        self.group_table.setMaximumHeight(320)
        v.addWidget(self.group_table)
        # Quick-fill helper: apply one label to the currently selected rows.
        fill_row = QHBoxLayout()
        self.fill_group_edit = QLineEdit()
        self.fill_group_edit.setPlaceholderText("group label for selected rows")
        fill_btn = QPushButton("Apply to selected rows")
        fill_btn.clicked.connect(self._fill_selected_group)
        fill_row.addWidget(self.fill_group_edit)
        fill_row.addWidget(fill_btn)
        v.addLayout(fill_row)
        confirm = QPushButton("Confirm groups")
        confirm.setStyleSheet("font-weight:bold; padding:6px;")
        confirm.clicked.connect(self._confirm_groups)
        v.addWidget(confirm)
        self.groups_note = QLabel("")
        self.groups_note.setStyleSheet("color:#345; font-size:11px;")
        v.addWidget(self.groups_note)
        v.addStretch(1)
        return self._scrollable(w)

    def _fill_selected_group(self):
        """Write the label from the quick-fill box into the selected rows' Group cell."""
        label = self.fill_group_edit.text().strip()
        rows = {i.row() for i in self.group_table.selectedIndexes()}
        for r in rows:
            self.group_table.setItem(r, 1, QTableWidgetItem(label))

    def _refresh_groups_tab(self):
        if self.matrix_spec is None:
            return
        vals = list(self.matrix_spec.value_columns)
        prev = self.metadata.sample_to_group if self.metadata else {}
        self.group_table.blockSignals(True)
        self.group_table.setRowCount(len(vals))
        for r, s in enumerate(vals):
            name = QTableWidgetItem(str(s))
            name.setFlags(name.flags() & ~Qt.ItemIsEditable)
            self.group_table.setItem(r, 0, name)
            self.group_table.setItem(r, 1, QTableWidgetItem(str(prev.get(str(s), ""))))
        self.group_table.blockSignals(False)

    def _confirm_groups(self):
        s2g = {}
        for r in range(self.group_table.rowCount()):
            name = self.group_table.item(r, 0).text()
            grp = self.group_table.item(r, 1)
            if grp and grp.text().strip():
                s2g[name] = grp.text().strip()
        if len({v for v in s2g.values()}) < 1:
            QMessageBox.warning(self, "No groups", "Assign at least one group.")
            return
        self.metadata = self.controller.matrix_metadata_from_assignment(s2g)
        self.diff_table = None
        sizes = self.metadata.group_sizes()
        self.groups_note.setText("Groups: " + ", ".join(f"{g} (n={n})" for g, n in sizes.items()))
        self._refresh_generate_tab()

    # --- Step 3: preprocess (raw-like matrices) -------------------------
    def _build_preprocess_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Optional: for raw-like / unnormalized / skewed matrices. "
                           "Nothing is applied until you click Apply — the raw matrix is "
                           "kept and every step is saved. Skip this step if your matrix is "
                           "already normalized."))
        diag_btn = QPushButton("Run diagnostics")
        diag_btn.clicked.connect(self._diagnose)
        v.addWidget(diag_btn)
        self.diag_text = QTextEdit(); self.diag_text.setReadOnly(True)
        self.diag_text.setMaximumHeight(150)
        v.addWidget(self.diag_text)
        # QC plot gallery: preview any QC plot of the CURRENT matrix (raw or processed).
        qc_row = QHBoxLayout()
        qc_row.addWidget(QLabel("QC plot:"))
        self.qc_kind_combo = QComboBox()
        for c in self.controller.matrix_qc_plot_catalog():
            self.qc_kind_combo.addItem(c["label"], c["key"])
        qc_row.addWidget(self.qc_kind_combo, 1)
        qc_btn = QPushButton("Preview")
        qc_btn.clicked.connect(self._preview_qc)
        qc_row.addWidget(qc_btn)
        v.addLayout(qc_row)
        self.qc_preview = QLabel("Run diagnostics, then preview a QC plot.")
        self.qc_preview.setAlignment(Qt.AlignCenter)
        self.qc_preview.setMinimumHeight(240)
        self.qc_preview.setStyleSheet("border:1px solid #ccc; color:#678;")
        v.addWidget(self.qc_preview)
        v.addWidget(QLabel("Recommended preprocessing (you choose; not applied automatically):"))
        self.prep_combo = QComboBox()
        self.prep_combo.currentIndexChanged.connect(self._on_prep_rec_changed)
        v.addWidget(self.prep_combo)
        self.prep_reason = QLabel(""); self.prep_reason.setWordWrap(True)
        self.prep_reason.setStyleSheet("color:#345; font-size:11px;")
        v.addWidget(self.prep_reason)
        row = QHBoxLayout()
        self.prep_apply = QPushButton("Apply preprocessing → use processed matrix")
        self.prep_apply.setStyleSheet("font-weight:bold; padding:6px;")
        self.prep_apply.clicked.connect(self._apply_preprocessing)
        self.prep_report = QPushButton("Save before/after QC report…")
        self.prep_report.clicked.connect(self._save_before_after)
        row.addWidget(self.prep_apply); row.addWidget(self.prep_report)
        v.addLayout(row)
        self.prep_revert = QPushButton("↩ Revert to raw matrix"); self.prep_revert.setEnabled(False)
        self.prep_revert.clicked.connect(self._revert_preprocessing)
        v.addWidget(self.prep_revert)
        self.prep_status = QLabel(""); self.prep_status.setWordWrap(True)
        self.prep_status.setStyleSheet("color:#345; font-size:11px;")
        v.addWidget(self.prep_status)
        v.addStretch(1)
        return self._scrollable(w)

    def _refresh_preprocess_tab(self):
        if self.matrix_spec is None or self.diag_text.toPlainText().strip():
            return
        self._diagnose()

    def _diagnose(self):
        if self.matrix_spec is None:
            return
        qc = self.controller.matrix_diagnose(self.data, self.matrix_spec)
        lines = [f"Suspected data type: {qc.suspected_data_type}",
                 f"Features: {qc.n_features} | Samples: {qc.n_samples}",
                 f"Overall skew: {qc.skewness_summary.get('overall', 0):.2f} | "
                 f"zeros: {qc.zero_fraction:.1%} | negatives: {qc.negative_value_fraction:.1%}",
                 f"Value range: [{qc.min:.1f}, {qc.max:.1f}]", ""]
        lines += [f"⚠ {x}" for x in qc.warnings]
        self.diag_text.setPlainText("\n".join(lines))
        self.prep_combo.blockSignals(True); self.prep_combo.clear()
        for rec in self.controller.matrix_preprocessing_recommendations(qc):
            self.prep_combo.addItem(rec.name, rec)
        self.prep_combo.blockSignals(False)
        self._on_prep_rec_changed()

    def _on_prep_rec_changed(self, *_):
        rec = self.prep_combo.currentData()
        if rec is None:
            self.prep_reason.setText(""); return
        methods = " → ".join(s["method"] for s in rec.steps)
        warn = ("  ⚠ " + "; ".join(rec.warnings)) if rec.warnings else ""
        self.prep_reason.setText(f"Steps: {methods}\n{rec.reason}{warn}")

    def _preview_qc(self):
        """Render one QC plot of the current (raw or processed) matrix inline."""
        if self.matrix_spec is None:
            return
        kind = self.qc_kind_combo.currentData()
        try:
            _spec, result = self.controller.matrix_qc_plot(
                self.data, self.matrix_spec, kind, metadata=self.metadata)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "QC plot failed", str(exc))
            return
        png = figure_to_bytes(result.figure, "png", dpi=130)
        pix = QPixmap(); pix.loadFromData(png, "PNG")
        self.qc_preview.setPixmap(pix.scaledToWidth(min(720, pix.width()),
                                                    Qt.SmoothTransformation))

    def _apply_preprocessing(self):
        rec = self.prep_combo.currentData()
        if rec is None or not rec.steps:
            return
        self.prep_apply.setEnabled(False)
        self.prep_status.setText("Applying preprocessing…")
        data, spec, steps = self.data, self.matrix_spec, list(rec.steps)
        meta = self.metadata

        def job():
            return self.controller.matrix_apply_preprocessing(data, spec, steps, metadata=meta)

        self._worker = _Worker(job)
        self._worker.done.connect(self._on_prep_done)
        self._worker.failed.connect(self._on_prep_failed)
        self._worker.start()

    def _on_prep_done(self, res):
        derived, dspec, ps = res
        if self._raw_data is None:                       # stash raw once
            self._raw_data, self._raw_spec = self.data, self.matrix_spec
        self.data, self.matrix_spec = derived, dspec
        self._prep_spec = ps                             # for traceable differential stats
        self.diff_table = None
        self.prep_apply.setEnabled(True); self.prep_revert.setEnabled(True)
        self.prep_status.setText("✓ Now using processed matrix. " + ps.method_sentence())
        self._refresh_generate_tab()

    def _on_prep_failed(self, msg):
        self.prep_apply.setEnabled(True)
        self.prep_status.setText("")
        QMessageBox.warning(self, "Preprocessing failed", msg)

    def _revert_preprocessing(self):
        if self._raw_data is not None:
            self.data, self.matrix_spec = self._raw_data, self._raw_spec
            self._raw_data = self._raw_spec = None
            self._prep_spec = None
            self.diff_table = None
            self.prep_revert.setEnabled(False)
            self.prep_status.setText("Reverted to the raw matrix.")
            self._refresh_generate_tab()

    def _save_before_after(self):
        rec = self.prep_combo.currentData()
        if rec is None or not rec.steps:
            QMessageBox.information(self, "No workflow", "Pick a preprocessing workflow first.")
            return
        out = QFileDialog.getExistingDirectory(self, "Choose a folder for the QC report")
        if not out:
            return
        data, spec, steps, meta = self.data, self.matrix_spec, list(rec.steps), self.metadata
        self.prep_status.setText("Building before/after QC report…")

        def job():
            return self.controller.matrix_before_after_report(data, spec, steps, out, metadata=meta)

        self._worker = _Worker(job)
        self._worker.done.connect(lambda _r, o=out: self.prep_status.setText(f"✓ QC report written to {o}"))
        self._worker.failed.connect(lambda m: QMessageBox.warning(self, "Report failed", m))
        self._worker.start()

    # --- Step 4: validation ---------------------------------------------
    def _build_validate_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        self.validate_text = QTextEdit()
        self.validate_text.setReadOnly(True)
        v.addWidget(self.validate_text)
        return self._scrollable(w)

    def _refresh_validate_tab(self):
        if self.matrix_spec is None:
            return
        rep = self.controller.matrix_validate(self.data, self.matrix_spec, self.metadata)
        s = rep.summary
        lines = [f"Features: {s.get('n_features', 0)}",
                 f"Samples (value columns): {s.get('n_samples', 0)}",
                 f"Annotation columns: {s.get('n_annotation_columns', 0)}",
                 f"Groups: {s.get('n_groups', 0)}  {s.get('group_sizes', {})}",
                 f"Missing values: {s.get('n_missing_values', 0)}",
                 f"Duplicate feature ids: {s.get('n_duplicate_features', 0)}",
                 f"Value scale: {s.get('value_type')}", ""]
        if rep.errors:
            lines.append("ERRORS:")
            lines += [f"  ✗ {e}" for e in rep.errors]
        if rep.warnings:
            lines.append("Warnings:")
            lines += [f"  ⚠ {w}" for w in rep.warnings]
        if rep.ok and not rep.warnings:
            lines.append("✓ Validation passed.")
        self.validate_text.setPlainText("\n".join(lines))

    # --- Step 4: recommend & generate -----------------------------------
    def _build_generate_tab(self) -> QWidget:
        outer = QScrollArea()
        outer.setWidgetResizable(True)
        w = QWidget()
        v = QVBoxLayout(w)

        # differential summary
        diff_box = QGroupBox("Feature-level differential summary (optional — enables "
                             "volcano / MA / ranked effect)")
        dl = QFormLayout(diff_box)
        two, multi, corrections = self.controller.matrix_stats_choices()
        self.test_combo = QComboBox(); self.test_combo.addItems(list(two) + list(multi))
        self.corr_combo = QComboBox(); self.corr_combo.addItems(list(corrections))
        self.ga_combo = QComboBox(); self.gb_combo = QComboBox()
        dl.addRow("Test", self.test_combo)
        dl.addRow("Correction", self.corr_combo)
        dl.addRow("Group A", self.ga_combo)
        dl.addRow("Group B", self.gb_combo)
        diff_btn_row = QHBoxLayout()
        self.diff_btn = QPushButton("Compute differential summary")
        self.diff_btn.clicked.connect(self._compute_differential)
        self.diff_cancel = QPushButton("Cancel"); self.diff_cancel.setEnabled(False)
        self.diff_cancel.clicked.connect(self._cancel_worker)
        diff_btn_row.addWidget(self.diff_btn); diff_btn_row.addWidget(self.diff_cancel)
        dl.addRow(diff_btn_row)
        self.diff_status = QLabel(""); self.diff_status.setWordWrap(True)
        dl.addRow(self.diff_status)
        v.addWidget(diff_box)

        # style controls (Publication) — same knobs as the main workbench, applied
        # to every plot generated here.
        v.addWidget(self._build_style_group())

        # recommendations
        rec_box = QGroupBox("Recommended plots")
        rl = QVBoxLayout(rec_box)
        self.rec_combo = QComboBox()
        self.rec_combo.currentIndexChanged.connect(self._on_rec_changed)
        rl.addWidget(self.rec_combo)
        self.rec_reason = QLabel(""); self.rec_reason.setWordWrap(True)
        self.rec_reason.setStyleSheet("color:#345; font-size:11px;")
        rl.addWidget(self.rec_reason)
        self.feature_list = QListWidget()
        self.feature_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.feature_list.setMaximumHeight(110)
        self.feature_label = QLabel("Feature(s) to show (blank = most variable):")
        rl.addWidget(self.feature_label); rl.addWidget(self.feature_list)
        topn_row = QHBoxLayout()
        self.topn_label = QLabel("Top N:")
        self.topn_spin = QSpinBox(); self.topn_spin.setRange(5, 200); self.topn_spin.setValue(30)
        topn_row.addWidget(self.topn_label); topn_row.addWidget(self.topn_spin); topn_row.addStretch()
        rl.addLayout(topn_row)
        gen = QPushButton("Generate plot")
        gen.clicked.connect(self._generate)
        rl.addWidget(gen)
        v.addWidget(rec_box)

        # preview + actions
        self.preview = QLabel("No plot yet.")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(320)
        self.preview.setStyleSheet("border:1px solid #ccc;")
        v.addWidget(self.preview)
        self.gen_warn = QLabel(""); self.gen_warn.setWordWrap(True)
        self.gen_warn.setStyleSheet("color:#345; font-size:11px;")
        v.addWidget(self.gen_warn)
        actions = QHBoxLayout()
        for label, fmt in (("Save PNG", "png"), ("Save SVG", "svg"), ("Save PDF", "pdf")):
            b = QPushButton(label)
            b.clicked.connect(lambda _=False, f=fmt: self._save(f))
            actions.addWidget(b)
        add_btn = QPushButton("➕ Add to Figure Builder")
        add_btn.clicked.connect(self._add_to_builder)
        actions.addWidget(add_btn)
        v.addLayout(actions)

        outer.setWidget(w)
        return outer

    def _refresh_generate_tab(self):
        # group combos for the differential summary
        groups = self.metadata.groups() if self.metadata else []
        for combo in (self.ga_combo, self.gb_combo):
            cur = combo.currentText()
            combo.blockSignals(True); combo.clear(); combo.addItems(groups)
            if cur in groups:
                combo.setCurrentText(cur)
            combo.blockSignals(False)
        # feature list for selected-feature plots
        if self.matrix_spec is not None:
            fid = self.matrix_spec.feature_id_column
            feats = self.data.info.dataframe[fid].astype(str).tolist()[:5000]
            self.feature_list.clear()
            for f in feats:
                self.feature_list.addItem(QListWidgetItem(f))
        self._refresh_recommendations()

    def _refresh_recommendations(self):
        if self.matrix_spec is None:
            return
        has_diff = self.diff_table is not None
        recs = self.controller.matrix_recommendations(self.data, self.matrix_spec,
                                                      self.metadata, has_differential=has_diff)
        self._recs = [r for r in recs if r.readiness_status == "ready"]
        self.rec_combo.blockSignals(True)
        self.rec_combo.clear()
        for r in self._recs:
            self.rec_combo.addItem(r.label, r)
        self.rec_combo.blockSignals(False)
        self._on_rec_changed()

    def _on_rec_changed(self, *_):
        rec = self.rec_combo.currentData()
        if rec is None:
            self.rec_reason.setText("")
            return
        self.rec_reason.setText(rec.reason)
        is_group = rec.key in ("box_by_group", "dot_by_group", "raincloud_by_group", "bar_by_group")
        is_topn = rec.key in ("top_variable_heatmap", "ranked_effect")
        self.feature_label.setVisible(is_group)
        self.feature_list.setVisible(is_group)
        self.topn_label.setVisible(is_topn)
        self.topn_spin.setVisible(is_topn)

    def _compute_differential(self):
        gate = self.controller.matrix_can_run_statistics(self.matrix_spec, self.metadata)
        if not gate.ok:
            QMessageBox.warning(self, "Cannot run", "\n".join(gate.errors))
            return
        test = self.test_combo.currentText()
        _two, multi, _c = self.controller.matrix_stats_choices()
        ga = self.ga_combo.currentText()
        gb = None if test in multi else (self.gb_combo.currentText() or None)
        if test not in multi and gb == ga:
            QMessageBox.warning(self, "Groups", "Choose two different groups.")
            return
        self.diff_btn.setEnabled(False); self.diff_cancel.setEnabled(True)
        self.diff_status.setText("Computing differential summary…")

        ps = self._prep_spec
        prep_note = ps.method_sentence() if ps else ""
        prep_id = ps.output_matrix_id if ps else None

        def job():
            return self.controller.matrix_differential_summary(
                self.data, self.matrix_spec, self.metadata, group_a=ga, group_b=gb,
                test=test, correction=self.corr_combo.currentText(),
                preprocessing_note=prep_note, source_matrix_id=prep_id,
                preprocessing_spec_id=prep_id)

        self._worker = _Worker(job)
        self._worker.done.connect(self._on_diff_done)
        self._worker.failed.connect(self._on_diff_failed)
        self._worker.start()

    def _on_diff_done(self, res):
        self.diff_btn.setEnabled(True); self.diff_cancel.setEnabled(False)
        self.diff_table = res.table
        self.diff_status.setText("✓ " + res.method_sentence())
        self._refresh_recommendations()

    def _on_diff_failed(self, msg):
        self.diff_btn.setEnabled(True); self.diff_cancel.setEnabled(False)
        self.diff_status.setText("")
        QMessageBox.warning(self, "Differential summary failed", msg)

    def _cancel_worker(self):
        if self._worker is not None:
            self._worker.cancel()
        self.diff_btn.setEnabled(True); self.diff_cancel.setEnabled(False)
        self.diff_status.setText("Cancelled.")

    def _build_style_group(self) -> QGroupBox:
        """Compact Publication style controls applied to every generated plot."""
        box = QGroupBox("Style (Publication)")
        form = QFormLayout(box)
        self.pal_combo = QComboBox()
        self.pal_combo.addItems(["publication", "colorblind_safe", "high_contrast", "grayscale"])
        self.font_combo = QComboBox()
        self.font_combo.addItems(["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans",
                                  "Times New Roman"])
        self.axis_pt = QSpinBox(); self.axis_pt.setRange(6, 28); self.axis_pt.setValue(12)
        self.tick_pt = QSpinBox(); self.tick_pt.setRange(6, 24); self.tick_pt.setValue(10)
        self.legend_pt = QSpinBox(); self.legend_pt.setRange(5, 22); self.legend_pt.setValue(10)
        self.marker_sz = QSpinBox(); self.marker_sz.setRange(4, 200); self.marker_sz.setValue(45)
        self.line_w = QDoubleSpinBox(); self.line_w.setRange(0.2, 6.0); self.line_w.setSingleStep(0.2)
        self.line_w.setValue(1.8)
        self.legend_outside = QCheckBox("Legend outside")
        form.addRow("Palette", self.pal_combo)
        form.addRow("Font", self.font_combo)
        form.addRow("Axis label pt", self.axis_pt)
        form.addRow("Tick label pt", self.tick_pt)
        form.addRow("Legend pt", self.legend_pt)
        form.addRow("Marker size", self.marker_sz)
        form.addRow("Line width", self.line_w)
        form.addRow(self.legend_outside)
        return box

    def _style_overrides(self) -> dict:
        """Collect the Style controls into a spec['style'] override dict."""
        return {
            "palette_name": self.pal_combo.currentText(),
            "font_family": self.font_combo.currentText(),
            "axis_font_pt": float(self.axis_pt.value()),
            "tick_label_pt": float(self.tick_pt.value()),
            "legend_pt": float(self.legend_pt.value()),
            "marker_size": float(self.marker_sz.value()),
            "line_width_pt": float(self.line_w.value()),
            "legend_outside": bool(self.legend_outside.isChecked()),
        }

    def _generate(self):
        rec = self.rec_combo.currentData()
        if rec is None:
            return
        selected = None
        if rec.key in ("box_by_group", "dot_by_group", "raincloud_by_group", "bar_by_group"):
            selected = [i.text() for i in self.feature_list.selectedItems()] or None
        params = {"top_n": int(self.topn_spin.value())}
        try:
            spec, result, pi = self.controller.matrix_build_plot(
                self.data, rec, self.matrix_spec, metadata=self.metadata,
                differential_table=self.diff_table, selected_features=selected, params=params,
                style_overrides=self._style_overrides())
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Could not generate", str(exc))
            return
        self._current = (spec, result, pi)
        png = figure_to_bytes(result.figure, "png", dpi=150)
        pix = QPixmap()
        pix.loadFromData(png, "PNG")
        self.preview.setPixmap(pix.scaledToWidth(min(760, pix.width()), Qt.SmoothTransformation))
        notes = list(pi.warnings) + list(result.warnings or [])
        self.gen_warn.setText(" | ".join(notes) if notes else "")

    def _save(self, fmt: str):
        if self._current is None:
            QMessageBox.information(self, "No plot", "Generate a plot first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, f"Save {fmt.upper()}", f"figure.{fmt}",
                                              f"{fmt.upper()} (*.{fmt})")
        if not path:
            return
        base = path[:-(len(fmt) + 1)] if path.lower().endswith("." + fmt) else path
        _spec, result, _pi = self._current
        export_figure(result.figure, base, [fmt], dpi=300)
        self.gen_warn.setText(f"Saved {path}")

    def _add_to_builder(self):
        if self._current is None:
            QMessageBox.information(self, "No plot", "Generate a plot first.")
            return
        import copy

        spec, _result, pi = self._current
        rec = self.rec_combo.currentData()
        self.saved_panels.append({
            "plot_spec": copy.deepcopy(spec),
            "table": pi.dataframe.copy(deep=True),
            "aux": {k: v.copy(deep=True) for k, v in (pi.aux or {}).items()},
            "title": rec.label if rec else "Matrix plot",
            "plot_type": pi.plot_type,
        })
        QMessageBox.information(self, "Added",
                                f"Added to the Figure Builder ({len(self.saved_panels)} panel(s)).")

    # --- tab housekeeping ------------------------------------------------
    def _on_tab_changed(self, index: int):
        if index == 2:
            self._refresh_preprocess_tab()
        elif index == 3:
            self._refresh_validate_tab()
        elif index == 4:
            self._refresh_generate_tab()
