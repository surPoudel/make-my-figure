"""Prepare an ordinary experimental table: column roles, transformations, factorial ANOVA.

For tables from ecology, entomology, agriculture, physiology... — one row per
observation, columns named however the experimenter named them. This is not the
matrix workflow: nothing here normalises, filters or treats numeric columns as
expression values. Three steps, each explicit:

1. **Columns** — the user says which column is the response, which are factors,
   covariates, time, the experimental unit (subject/colony). Suggestions are
   shown with their reason and never applied silently.
2. **Transform** — chosen numeric columns gain a derived column (``log10(x)``)
   beside the original. The preview shows original and transformed values, the
   number of invalid values and what will happen to them, before anything is
   applied. The original table is never changed.
3. **Factorial analysis** — checks whether the chosen design can be estimated
   and explains why not when it cannot; runs the ANOVA only when it can.
"""
from __future__ import annotations

from typing import List, Optional

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from make_my_figure_core.statistics.factorial import check_design, factorial_anova, model_coefficients
from make_my_figure_core.statistics.models import StatsError
from make_my_figure_core.tabular import (
    METHODS,
    ROLE_LABELS,
    ROLES,
    ColumnRoles,
    TableTransform,
    TransformError,
    preview_transform,
    suggest_roles,
)

_METHOD_LABELS = {
    "log10": "log10(x)", "log2": "log2(x)", "ln": "Natural log  ln(x)",
    "sqrt": "Square root  √x", "zscore": "z-score  (x − mean) / SD",
}
_NONE = "(none)"


class TableWorkflowDialog(QDialog):
    """Roles → transformations (with preview) → factorial analysis, for one table."""

    def __init__(self, controller, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Prepare table — roles, transformations, factorial analysis")
        self.resize(1040, 820)
        self.controller = controller
        self.raw = controller.raw_of(data)
        self.rawdf: pd.DataFrame = self.raw.info.dataframe
        ctx = getattr(data, "table_context", None) or {}
        record = ctx.get("record")
        self.transforms: List[TableTransform] = list(record.transform_objects) if record else []
        self.roles = (ColumnRoles.from_dict(record.column_roles) if record is not None and record.column_roles
                      else ColumnRoles())
        self.result_data = None          # LoadedData to hand back to the editor on Apply
        self.plot_request = None         # {"y": column, "x": factor, "group": factor2} when asked
        self.anova_table: Optional[pd.DataFrame] = None

        v = QVBoxLayout(self)
        intro = QLabel(
            f"<b>{self.raw.table_name}</b> — {len(self.rawdf)} rows × {self.rawdf.shape[1]} columns. "
            "The original table is never modified: transformations add new columns beside the original "
            "ones, and every step is recorded and saved with the figure.")
        intro.setWordWrap(True)
        v.addWidget(intro)
        self.tabs = QTabWidget()
        v.addWidget(self.tabs, 1)
        self.tabs.addTab(self._build_roles_tab(), "1  Columns")
        self.tabs.addTab(self._build_transform_tab(), "2  Transform")
        self.tabs.addTab(self._build_analysis_tab(), "3  Factorial analysis")
        self.tabs.currentChanged.connect(self._on_tab)

        self.chk_plot = QCheckBox("After applying, plot the response by the first factor")
        self.chk_plot.setChecked(True)
        v.addWidget(self.chk_plot)
        bb = QDialogButtonBox()
        self.btn_apply = bb.addButton("Apply", QDialogButtonBox.AcceptRole)
        self.btn_reset = bb.addButton("Reset", QDialogButtonBox.ResetRole)
        self.btn_cancel = bb.addButton(QDialogButtonBox.Cancel)
        self.btn_apply.setToolTip("Build the derived table from the original table and the listed "
                                  "transformations, and use it in the plot editor.")
        self.btn_reset.setToolTip("Forget the listed transformations and restore the suggested roles.")
        self.btn_apply.clicked.connect(self._apply)
        self.btn_reset.clicked.connect(self._reset)
        self.btn_cancel.clicked.connect(self.reject)
        v.addWidget(bb)
        self._refresh_transform_list()
        self._refresh_preview()

    # ------------------------------------------------------------------ roles
    def _build_roles_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        note = QLabel("Assign what each column means. Suggestions are guesses from names and values; "
                      "your choice always wins. Mark the experimental unit (e.g. colony) as "
                      "<i>Subject</i>: rows from the same unit are not independent replicates.")
        note.setWordWrap(True)
        lay.addWidget(note)
        self.roles_table = QTableWidget(len(self.rawdf.columns), 5)
        self.roles_table.setHorizontalHeaderLabels(["Column", "Type", "Example values", "Suggested", "Role"])
        self.roles_table.verticalHeader().setVisible(False)
        self.roles_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        hdr = self.roles_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        self._suggestions = {s.column: s for s in suggest_roles(self.rawdf)}
        self._role_combos = {}
        for i, col in enumerate(self.rawdf.columns):
            s = self.rawdf[col]
            kind = "number" if pd.api.types.is_numeric_dtype(s) else "text"
            n_miss = int(s.isna().sum())
            sample = ", ".join(str(x) for x in s.dropna().unique()[:5])
            self.roles_table.setItem(i, 0, QTableWidgetItem(str(col)))
            self.roles_table.setItem(i, 1, QTableWidgetItem(kind + (f" ({n_miss} missing)" if n_miss else "")))
            self.roles_table.setItem(i, 2, QTableWidgetItem(sample))
            sug = self._suggestions.get(col)
            it = QTableWidgetItem(ROLE_LABELS[sug.role] if sug else "")
            if sug:
                it.setToolTip(sug.reason)
            self.roles_table.setItem(i, 3, it)
            combo = QComboBox()
            for r in ROLES:
                combo.addItem(ROLE_LABELS[r], r)
            chosen = self.roles.roles.get(col) or (sug.role if sug else "metadata")
            combo.setCurrentIndex(max(0, combo.findData(chosen)))
            combo.currentIndexChanged.connect(self._roles_changed)
            self._role_combos[col] = combo
            self.roles_table.setCellWidget(i, 4, combo)
        lay.addWidget(self.roles_table, 1)
        btn = QPushButton("Use all suggestions")
        btn.clicked.connect(self._use_suggestions)
        lay.addWidget(btn, 0, Qt.AlignLeft)
        self._roles_changed()
        return w

    def _use_suggestions(self):
        for col, combo in self._role_combos.items():
            sug = self._suggestions.get(col)
            combo.setCurrentIndex(max(0, combo.findData(sug.role if sug else "metadata")))

    def _roles_changed(self, *_):
        roles = ColumnRoles()
        for col, combo in self._role_combos.items():
            roles.set(col, combo.currentData())
        self.roles = roles
        if hasattr(self, "an_response"):
            self._fill_analysis_from_roles()

    # -------------------------------------------------------------- transform
    def _numeric_columns(self) -> List[str]:
        return [c for c in self.rawdf.columns if pd.api.types.is_numeric_dtype(self.rawdf[c])]

    def _build_transform_tab(self) -> QWidget:
        w = QWidget()
        outer = QHBoxLayout(w)
        left = QVBoxLayout()
        box = QGroupBox("New transformation")
        f = QFormLayout(box)
        self.tf_column = QComboBox()
        self.tf_column.addItems([str(c) for c in self._numeric_columns()])
        self.tf_method = QComboBox()
        for m in METHODS:
            self.tf_method.addItem(_METHOD_LABELS.get(m, m), m)
        self.tf_offset = QDoubleSpinBox()
        self.tf_offset.setDecimals(6)
        self.tf_offset.setRange(-1e12, 1e12)
        self.tf_offset.setValue(0.0)
        self.tf_offset.setToolTip("Added to every value before the transformation: log10(x + offset). "
                                  "0 by default — no value is shifted unless you choose to, and the "
                                  "offset is recorded with the result.")
        self.tf_invalid = QComboBox()
        self.tf_invalid.addItem("Refuse — fix the data or choose an offset", "refuse")
        self.tf_invalid.addItem("Record as missing in the new column (original kept)", "missing")
        self.tf_invalid.setToolTip("What to do with values the transformation is not defined for "
                                   "(0 or negatives for a log). Nothing is replaced silently.")
        f.addRow("Column", self.tf_column)
        f.addRow("Transformation", self.tf_method)
        f.addRow("Offset", self.tf_offset)
        f.addRow("Invalid values", self.tf_invalid)
        for wdg in (self.tf_column, self.tf_method, self.tf_invalid):
            wdg.currentIndexChanged.connect(self._refresh_preview)
        self.tf_offset.valueChanged.connect(self._refresh_preview)
        left.addWidget(box)
        self.tf_summary = QLabel("")
        self.tf_summary.setWordWrap(True)
        self.tf_summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        left.addWidget(self.tf_summary)
        self.btn_add = QPushButton("Add this transformation")
        self.btn_add.clicked.connect(self._add_transform)
        left.addWidget(self.btn_add)
        left.addWidget(QLabel("Transformations to apply (each adds a new column):"))
        self.tf_list = QListWidget()
        left.addWidget(self.tf_list, 1)
        self.btn_remove = QPushButton("Remove selected")
        self.btn_remove.clicked.connect(self._remove_transform)
        left.addWidget(self.btn_remove)
        outer.addLayout(left, 2)

        right = QVBoxLayout()
        right.addWidget(QLabel("Preview — original vs transformed (first 200 rows):"))
        self.preview_table = QTableWidget(0, 2)
        self.preview_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        right.addWidget(self.preview_table, 1)
        outer.addLayout(right, 3)
        return w

    def _current_transform(self) -> Optional[TableTransform]:
        if not self.tf_column.currentText():
            return None
        return TableTransform(self.tf_column.currentText(), self.tf_method.currentData(),
                              float(self.tf_offset.value()), self.tf_invalid.currentData())

    def _refresh_preview(self, *_):
        t = self._current_transform()
        if t is None:
            self.tf_summary.setText("This table has no numeric columns to transform.")
            self.btn_add.setEnabled(False)
            return
        self.tf_offset.setEnabled(bool(METHODS[t.method]["offset"]))
        if not METHODS[t.method]["offset"] and t.offset:
            self.tf_offset.setValue(0.0)
            return
        try:
            pv = preview_transform(self.rawdf, t, already_transformed=[x.target for x in self.transforms])
        except TransformError as exc:
            self.tf_summary.setText(f"<span style='color:#a00'>{exc}</span>")
            self.btn_add.setEnabled(False)
            return
        dup = any(x.target == pv.output_column for x in self.transforms)
        fmt = (lambda x: "—" if x is None else f"{x:.6g}")
        lines = [f"<b>{pv.output_column}</b>",
                 f"Column: {t.column} · transformation: {_METHOD_LABELS.get(t.method, t.method)}"
                 + (f" · base {METHODS[t.method]['base']:g}" if METHODS[t.method]["base"] else "")
                 + f" · offset {pv.offset:g}",
                 f"Valid: {pv.n_valid} · invalid: {pv.n_invalid} · missing: {pv.n_missing}"
                 + (f" · text: {pv.n_non_numeric}" if pv.n_non_numeric else ""),
                 f"Original range: {fmt(pv.original_min)} – {fmt(pv.original_max)} → "
                 f"transformed: {fmt(pv.transformed_min)} – {fmt(pv.transformed_max)}"]
        for n in pv.notes:
            lines.append(f"<span style='color:#555'>{n}</span>")
        for p in pv.problems:
            lines.append(f"<span style='color:#a00'>✖ {p}</span>")
        if dup:
            lines.append("<span style='color:#a00'>✖ This transformation is already in the list.</span>")
        self.tf_summary.setText("<br>".join(lines))
        self.btn_add.setEnabled(pv.can_apply and not dup)
        self.preview_table.setRowCount(len(pv.original))
        self.preview_table.setHorizontalHeaderLabels([f"{t.column} (original)", pv.output_column])
        invalid = set(pv.invalid_rows)
        for i, (a, b) in enumerate(zip(pv.original, pv.transformed)):
            ia = QTableWidgetItem(fmt(a))
            ib = QTableWidgetItem("invalid → missing" if i in invalid and t.invalid == "missing"
                                  else ("invalid" if i in invalid else fmt(b)))
            if i in invalid:
                ib.setForeground(Qt.red)
            self.preview_table.setItem(i, 0, ia)
            self.preview_table.setItem(i, 1, ib)

    def _add_transform(self):
        t = self._current_transform()
        if t is not None:
            self.transforms.append(t)
            self._refresh_transform_list()
            self._refresh_preview()

    def _remove_transform(self):
        row = self.tf_list.currentRow()
        if 0 <= row < len(self.transforms):
            del self.transforms[row]
            self._refresh_transform_list()
            self._refresh_preview()

    def _refresh_transform_list(self):
        self.tf_list.clear()
        for t in self.transforms:
            extra = " (invalid → missing)" if t.invalid == "missing" else ""
            self.tf_list.addItem(QListWidgetItem(f"{t.target}{extra}"))
        if hasattr(self, "an_response"):
            self._fill_analysis_from_roles()

    # --------------------------------------------------------------- analysis
    def _build_analysis_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        note = QLabel("Factorial ANOVA / ANCOVA with up to three factors. The design is checked first; "
                      "if it cannot be estimated (confounded factors, empty combinations, no residual "
                      "degrees of freedom, repeated measurements of one subject, a constant response) "
                      "the reason is shown and nothing is computed.")
        note.setWordWrap(True)
        lay.addWidget(note)
        form = QFormLayout()
        self.an_response = QComboBox()
        self.an_factors = [QComboBox() for _ in range(3)]
        self.an_covariates = QListWidget()
        self.an_covariates.setMinimumHeight(64)
        self.an_covariates.setMaximumHeight(96)
        self.an_subject = QComboBox()
        self.an_inter = QComboBox()
        self.an_inter.addItem("Full factorial (all interactions)", "full")
        self.an_inter.addItem("Main effects only", "main")
        self.an_ss = QComboBox()
        self.an_ss.addItem("Type II sums of squares (default)", 2)
        self.an_ss.addItem("Type III (sum-to-zero contrasts)", 3)
        form.addRow("Response", self.an_response)
        for i, cb in enumerate(self.an_factors):
            form.addRow(f"Factor {i + 1}", cb)
        form.addRow("Covariates (tick)", self.an_covariates)
        form.addRow("Subject / colony", self.an_subject)
        form.addRow("Model", self.an_inter)
        form.addRow("Sums of squares", self.an_ss)
        lay.addLayout(form)
        row = QHBoxLayout()
        self.btn_check = QPushButton("Check design")
        self.btn_run = QPushButton("Run ANOVA")
        self.btn_export_anova = QPushButton("Export ANOVA table (CSV)…")
        self.btn_export_anova.setEnabled(False)
        self.btn_export_coef = QPushButton("Export coefficients (CSV)…")
        self.btn_export_coef.setEnabled(False)
        self.btn_export_coef.clicked.connect(self._export_coefficients)
        self.btn_check.clicked.connect(self._check)
        self.btn_run.clicked.connect(self._run)
        self.btn_export_anova.clicked.connect(self._export_anova)
        for b in (self.btn_check, self.btn_run, self.btn_export_anova, self.btn_export_coef):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        self.an_report = QPlainTextEdit()
        self.an_report.setReadOnly(True)
        self.an_report.setMinimumHeight(150)
        lay.addWidget(self.an_report, 3)
        self.an_table = QTableWidget(0, 7)
        self.an_table.setHorizontalHeaderLabels(["Term", "df", "Sum of squares", "F", "P", "Partial η²",
                                                 "Residual df"])
        self.an_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.an_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Coefficients: R's summary(lm) under contr.sum, validated against R.
        coef_page = QWidget()
        cl = QVBoxLayout(coef_page)
        cl.setContentsMargins(0, 0, 0, 0)
        self.coef_note = QLabel(
            "Sum-to-zero coding: each level's coefficient is its deviation from the mean of all "
            "levels; the last level of each factor has no row (it is minus the sum of the others). "
            "A covariate's coefficient is its slope. 95 % confidence intervals.")
        self.coef_note.setWordWrap(True)
        self.coef_note.setStyleSheet("color:#555;")
        cl.addWidget(self.coef_note)
        self.coef_table = QTableWidget(0, 8)
        self.coef_table.setHorizontalHeaderLabels(["Coefficient", "Estimate", "Std. error", "t", "P",
                                                   "95 % CI low", "95 % CI high", "Residual df"])
        self.coef_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.coef_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.coef_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        cl.addWidget(self.coef_table, 1)
        self.result_tabs = QTabWidget()
        self.result_tabs.addTab(self.an_table, "ANOVA table")
        self.result_tabs.addTab(coef_page, "Coefficients")
        lay.addWidget(self.result_tabs, 2)
        self.coef_df = None
        self._fill_analysis_from_roles()
        return w

    def _analysis_frame(self) -> pd.DataFrame:
        """Raw table plus the listed derived columns (so a transformed response can be analysed).

        Cached on the transformation list: rebuilding it per refresh, per column,
        cost 3.8 s each time on a million-row table."""
        if not self.transforms:
            return self.rawdf
        key = tuple(t.target for t in self.transforms) + tuple(t.invalid for t in self.transforms)
        cached = getattr(self, "_frame_cache", None)
        if cached is not None and cached[0] == key:
            return cached[1]
        from make_my_figure_core.tabular import apply_table_transforms

        try:
            derived, _ = apply_table_transforms(self.rawdf, self.transforms, stamp_time=False,
                                                with_checksums=False)
        except TransformError:
            derived = self.rawdf
        self._frame_cache = (key, derived)
        return derived

    def _fill_analysis_from_roles(self):
        frame = self._analysis_frame()
        frame_cols = [str(c) for c in frame.columns]
        numeric = [c for c in frame_cols if pd.api.types.is_numeric_dtype(frame[c])]
        responses = self.roles.columns("response") + [t.target for t in self.transforms]
        keep = self.an_response.currentText()
        self.an_response.blockSignals(True)
        self.an_response.clear()
        self.an_response.addItems(list(dict.fromkeys(responses + [c for c in numeric if c not in responses])))
        if keep:
            self.an_response.setCurrentIndex(max(0, self.an_response.findText(keep)))
        self.an_response.blockSignals(False)
        factors = self.roles.columns("factor") + self.roles.columns("time")
        for i, cb in enumerate(self.an_factors):
            keep = cb.currentText()
            cb.blockSignals(True)
            cb.clear()
            cb.addItem(_NONE)
            cb.addItems(frame_cols)
            if keep and keep != _NONE:
                cb.setCurrentIndex(max(0, cb.findText(keep)))
            elif i < len(factors):
                cb.setCurrentIndex(max(0, cb.findText(factors[i])))
            cb.blockSignals(False)
        ticked = {self.an_covariates.item(i).text() for i in range(self.an_covariates.count())
                  if self.an_covariates.item(i).checkState() == Qt.Checked}
        if not ticked:
            ticked = set(self.roles.columns("covariate"))
        self.an_covariates.clear()
        for c in numeric:
            it = QListWidgetItem(c)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if c in ticked else Qt.Unchecked)
            self.an_covariates.addItem(it)
        keep = self.an_subject.currentText()
        self.an_subject.clear()
        self.an_subject.addItem(_NONE)
        self.an_subject.addItems(frame_cols)
        subj = keep if keep and keep != _NONE else (self.roles.columns("subject") or [_NONE])[0]
        self.an_subject.setCurrentIndex(max(0, self.an_subject.findText(subj)))

    def _design_args(self):
        factors = [cb.currentText() for cb in self.an_factors if cb.currentText() not in ("", _NONE)]
        covs = [self.an_covariates.item(i).text() for i in range(self.an_covariates.count())
                if self.an_covariates.item(i).checkState() == Qt.Checked]
        subject = self.an_subject.currentText()
        return dict(response=self.an_response.currentText(), factors=factors, covariates=covs,
                    subject=None if subject in ("", _NONE) else subject,
                    interactions=self.an_inter.currentData())

    def _check(self):
        a = self._design_args()
        rep = check_design(self._analysis_frame(), a["response"], a["factors"], covariates=a["covariates"],
                           subject=a["subject"], interactions=a["interactions"])
        cells = "\n".join("  " + ", ".join(f"{k}={v}" for k, v in c.items() if k != "n") + f": n = {c['n']}"
                          for c in rep.cells[:40])
        more = f"\n  … {len(rep.cells) - 40} more" if len(rep.cells) > 40 else ""
        self.an_report.setPlainText(f"Model: {rep.formula}\n\n{rep.explanation()}\n\n"
                                    f"Observations per factor combination:\n{cells}{more}")
        return rep

    def _run(self):
        rep = self._check()
        self.an_table.setRowCount(0)
        self.coef_table.setRowCount(0)
        self.btn_export_anova.setEnabled(False)
        self.btn_export_coef.setEnabled(False)
        self.coef_df = None
        if not rep.estimable:
            return
        a = self._design_args()
        try:
            res = factorial_anova(self._analysis_frame(), a["response"], a["factors"], covariates=a["covariates"],
                                  subject=a["subject"], interactions=a["interactions"],
                                  ss_type=int(self.an_ss.currentData()))
        except StatsError as exc:
            self.an_report.appendPlainText(f"\n{exc}")
            return
        rows = [{"term": r.group_a, "df": r.df, "sum_sq": r.extra["sum_sq"], "F": r.statistic,
                 "p_value": r.p_value, "partial_eta_squared": r.effect_size, "residual_df": r.df2,
                 "ss_type": r.extra["ss_type"], "model": r.extra["formula"], "n": r.n_total} for r in res]
        self.anova_table = pd.DataFrame(rows)
        self.an_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [r["term"], f"{r['df']:g}", f"{r['sum_sq']:.6g}", f"{r['F']:.4g}",
                    f"{r['p_value']:.3g}", f"{r['partial_eta_squared']:.3f}", f"{r['residual_df']:g}"]
            for j, v in enumerate(vals):
                self.an_table.setItem(i, j, QTableWidgetItem(v))
        self.an_report.appendPlainText(f"\n{res[0].test_name} on {res[0].n_total} observations. "
                                       "Partial η² = SS_term / (SS_term + SS_residual).")
        self.btn_export_anova.setEnabled(True)
        try:
            coef = model_coefficients(self._analysis_frame(), a["response"], a["factors"],
                                      covariates=a["covariates"], subject=a["subject"],
                                      interactions=a["interactions"])
        except StatsError as exc:
            self.an_report.appendPlainText(f"\nCoefficients not available: {exc}")
            return
        self.coef_df = coef.assign(model=res[0].extra["formula"], n=res[0].n_total)
        self.coef_table.setRowCount(len(coef))
        for i, r in coef.iterrows():
            vals = [r["label"], f"{r['estimate']:.6g}", f"{r['std_error']:.4g}", f"{r['t']:.4g}",
                    f"{r['p_value']:.3g}", f"{r['ci_low']:.4g}", f"{r['ci_high']:.4g}", f"{r['residual_df']:g}"]
            for j, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if j == 0:
                    item.setToolTip(r["meaning"])
                self.coef_table.setItem(i, j, item)
        self.btn_export_coef.setEnabled(True)

    def _export_anova(self):
        if self.anova_table is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export ANOVA table", "anova.csv", "CSV (*.csv)")
        if path:
            self.anova_table.to_csv(path, index=False)

    def _export_coefficients(self):
        if self.coef_df is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export coefficients", "coefficients.csv", "CSV (*.csv)")
        if path:
            self.coef_df.to_csv(path, index=False)

    # ------------------------------------------------------------- dialog
    def _on_tab(self, index):
        if index == 2:
            self._fill_analysis_from_roles()

    def _reset(self):
        self.transforms = []
        self._refresh_transform_list()
        self._use_suggestions()
        self.tf_offset.setValue(0.0)
        self.tf_invalid.setCurrentIndex(0)
        self._refresh_preview()

    def _apply(self):
        try:
            self.result_data = self.controller.derive_table(self.raw, self.transforms, roles=self.roles)
        except TransformError as exc:
            QMessageBox.warning(self, "Transformation not applied", str(exc))
            return
        if self.chk_plot.isChecked():
            factors = self.roles.columns("factor") + self.roles.columns("time")
            response = self.an_response.currentText() or (self.roles.columns("response") or [None])[0]
            if response:
                self.plot_request = {"y": response, "x": factors[0] if factors else None,
                                     "group": factors[1] if len(factors) > 1 else None}
        self.accept()
