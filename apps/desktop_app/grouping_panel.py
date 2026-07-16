"""Define groups in-app, without a separate metadata file.

Two workflows, one dialog:

* **Assign sample groups (wide matrix)** — for a features x samples matrix
  (e.g. an expression / count matrix): pick the feature-id column, assign each
  remaining (sample) column to a group, optionally pick features, and build a
  long, group-tagged table ready for bar/box/violin/stats.
* **Group by column values** — for a long table: map the values of an existing
  column to group labels, adding a new grouping column.

The dialog is a thin Qt layer over ``DesktopController`` group helpers; it emits
the resulting :class:`LoadedData` so the main window can adopt it.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

_MAX_FEATURES_LISTED = 2000


class GroupingDialog(QDialog):
    """Assign sample columns to groups, or derive a group column from values."""

    grouped = Signal(object)  # emits a controller.LoadedData

    def __init__(self, controller, data, parent=None, initial_state=None):
        super().__init__(parent)
        self.controller = controller
        self.data = data
        self.column_annotations = None   # group color-strip spec for a heatmap (wide mode)
        # Restore a prior assignment so reopening the dialog doesn't lose the user's
        # work; populated back into `result_state` on accept for the caller to keep.
        self._initial_state = dict(initial_state or {})
        self.result_state = None
        self.setWindowTitle("Define groups")
        self.resize(560, 560)

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Create groups from your data without a separate metadata file. "
            "Use the first tab for a wide matrix (samples in columns), or the "
            "second to label rows by an existing column's values.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_matrix_tab(), "Assign sample groups (wide matrix)")
        self.tabs.addTab(self._build_column_tab(), "Group by column values")
        layout.addWidget(self.tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.create_btn = buttons.addButton("Create grouped table", QDialogButtonBox.AcceptRole)
        self.create_btn.clicked.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # --- matrix (wide -> long) tab ---------------------------------------
    def _build_matrix_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        cols = list(self.data.info.columns)

        form = QFormLayout()
        self.feature_combo = QComboBox()
        self.feature_combo.addItems(cols)
        # default the feature id to the first non-numeric (identifier-ish) column
        numeric = set(self.data.info.numeric_columns)
        default_feat = next((c for c in cols if c not in numeric), cols[0] if cols else "")
        # Restore the feature column from a prior session when it still exists.
        prev_feat = self._initial_state.get("feature_col")
        if prev_feat in cols:
            default_feat = prev_feat
        if default_feat:
            self.feature_combo.setCurrentText(default_feat)
        self.feature_combo.currentIndexChanged.connect(lambda *_: self._refresh_matrix_tab())
        form.addRow("Feature id column", self.feature_combo)
        v.addLayout(form)

        v.addWidget(QLabel("Assign each sample column to a group (edit the Group column; "
                           "leave non-sample columns blank):"))
        self.sample_table = QTableWidget(0, 2)
        self.sample_table.setHorizontalHeaderLabels(["Sample column", "Group"])
        self.sample_table.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.sample_table)
        # Note listing numeric columns detected as annotations (e.g. annotationLevel),
        # which are left blank so they are not treated as sample measurements.
        self.annot_note = QLabel("")
        self.annot_note.setWordWrap(True)
        self.annot_note.setStyleSheet("color:#345; font-size:11px;")
        v.addWidget(self.annot_note)

        auto = QPushButton("Auto-guess groups from names")
        auto.clicked.connect(self._auto_guess_groups)
        v.addWidget(auto)

        # Output shape: long for bar/box/violin, or wide (matrix + group strip)
        # for a heatmap/PCA (a long reshape would collapse a heatmap to nothing).
        v.addWidget(QLabel("Use the grouped table for:"))
        self.mode_long = QRadioButton("Bar / box / violin comparisons (long table)")
        self.mode_long.setChecked(True)
        self.mode_wide = QRadioButton("Heatmap / PCA (keep the matrix + add a group color strip)")
        self.mode_diff = QRadioButton(
            "Differential screen (exactly 2 groups → results table with log2FC / p / FDR)")
        v.addWidget(self.mode_long)
        v.addWidget(self.mode_wide)
        v.addWidget(self.mode_diff)
        # Differential-screen method (only the two-group tests already in the app).
        diff_row = QHBoxLayout()
        diff_row.addWidget(QLabel("   DE test:"))
        self.diff_test_combo = QComboBox()
        for tid, label in self.controller.differential_test_choices():
            self.diff_test_combo.addItem(label, tid)
        diff_row.addWidget(self.diff_test_combo)
        v.addLayout(diff_row)
        diff_note = QLabel(
            "The differential screen expects a NORMALIZED matrix (e.g. voom / log2-CPM). "
            "It is a basic per-feature test + BH FDR — not a count-based model "
            "(DESeq2/edgeR/limma-voom). For raw counts, normalize first.")
        diff_note.setStyleSheet("color:#345; font-size:11px;")
        diff_note.setWordWrap(True)
        v.addWidget(diff_note)

        v.addWidget(QLabel("Features to include:"))
        self.all_features_radio = QRadioButton("All features")
        self.all_features_radio.setChecked(True)
        self.some_features_radio = QRadioButton("Only selected features (below)")
        v.addWidget(self.all_features_radio)
        v.addWidget(self.some_features_radio)
        self.feature_list = QListWidget()
        self.feature_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.feature_list.setMaximumHeight(120)
        v.addWidget(self.feature_list)

        self._refresh_matrix_tab()
        return w

    def _sample_columns(self) -> list:
        # Only numeric columns are plausible samples — drop text annotation
        # columns (e.g. geneSymbol / bioType) so they aren't offered as samples.
        feat = self.feature_combo.currentText()
        return self.controller.numeric_sample_columns(self.data, feat)

    def _refresh_matrix_tab(self, guess: bool = False):
        samples = self._sample_columns()
        feat = self.feature_combo.currentText()
        # Classify numeric columns into per-sample VALUE columns vs categorical
        # annotation columns (e.g. annotationLevel in {1,2,3}). Only value columns
        # are auto-guessed / pre-filled; annotation columns stay blank.
        try:
            from make_my_figure_core.grouping import value_matrix_columns
            value_cols, annot_cols = value_matrix_columns(self.data.info.dataframe, feat)
        except Exception:
            value_cols, annot_cols = samples, []
        value_set = {str(c) for c in value_cols}
        prev = {str(k): str(v) for k, v in (self._initial_state.get("assignment") or {}).items()}
        guessed = (self.controller.guess_sample_groups([s for s in samples if str(s) in value_set])
                   if guess else {})
        self.sample_table.blockSignals(True)
        self.sample_table.setRowCount(len(samples))
        for r, s in enumerate(samples):
            name_item = QTableWidgetItem(str(s))
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.sample_table.setItem(r, 0, name_item)
            # Priority: fresh guess (if requested) > restored prior assignment > blank.
            grp = guessed.get(s) if guess else None
            if grp is None:
                grp = prev.get(str(s), "")
            self.sample_table.setItem(r, 1, QTableWidgetItem(str(grp)))
        self.sample_table.blockSignals(False)
        if hasattr(self, "annot_note"):
            self.annot_note.setText(
                ("Numeric column(s) treated as annotations (left blank): "
                 + ", ".join(map(str, annot_cols))) if annot_cols else "")

        # feature list from the chosen id column's values
        self.feature_list.clear()
        feat = self.feature_combo.currentText()
        if feat in self.data.info.columns:
            values = self.data.info.dataframe[feat].astype(str).tolist()
            for val in values[:_MAX_FEATURES_LISTED]:
                self.feature_list.addItem(QListWidgetItem(val))
            if len(values) > _MAX_FEATURES_LISTED:
                self.feature_list.addItem(QListWidgetItem(
                    f"… {len(values) - _MAX_FEATURES_LISTED} more not shown"))

    def _auto_guess_groups(self):
        self._refresh_matrix_tab(guess=True)

    def _matrix_assignment(self) -> dict:
        s2g = {}
        for r in range(self.sample_table.rowCount()):
            name = self.sample_table.item(r, 0).text()
            grp = self.sample_table.item(r, 1)
            s2g[name] = grp.text().strip() if grp else ""
        return s2g

    def _selected_features(self):
        if self.all_features_radio.isChecked():
            return None
        feats = [i.text() for i in self.feature_list.selectedItems()
                 if not i.text().startswith("…")]
        return feats or None

    # --- column-value tab ------------------------------------------------
    def _build_column_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        cols = list(self.data.info.columns)

        form = QFormLayout()
        self.source_combo = QComboBox()
        self.source_combo.addItems(cols)
        # default to the first categorical column
        cats = self.data.info.categorical_columns or cols
        if cats:
            self.source_combo.setCurrentText(cats[0])
        self.source_combo.currentIndexChanged.connect(self._refresh_column_tab)
        form.addRow("Source column", self.source_combo)
        self.new_col_edit = QLineEdit("group")
        form.addRow("New group column name", self.new_col_edit)
        v.addLayout(form)

        v.addWidget(QLabel("Map each value to a group label (edit the Group column):"))
        self.value_table = QTableWidget(0, 2)
        self.value_table.setHorizontalHeaderLabels(["Value", "Group"])
        self.value_table.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.value_table)

        self._refresh_column_tab()
        return w

    def _refresh_column_tab(self):
        col = self.source_combo.currentText()
        if col not in self.data.info.columns:
            return
        values = list(dict.fromkeys(self.data.info.dataframe[col].astype(str).tolist()))
        self.value_table.setRowCount(min(len(values), _MAX_FEATURES_LISTED))
        for r, val in enumerate(values[:_MAX_FEATURES_LISTED]):
            v_item = QTableWidgetItem(val)
            v_item.setFlags(v_item.flags() & ~Qt.ItemIsEditable)
            self.value_table.setItem(r, 0, v_item)
            self.value_table.setItem(r, 1, QTableWidgetItem(val))  # default: same label

    def _value_mapping(self) -> dict:
        mapping = {}
        for r in range(self.value_table.rowCount()):
            val = self.value_table.item(r, 0).text()
            grp = self.value_table.item(r, 1)
            if grp and grp.text().strip():
                mapping[val] = grp.text().strip()
        return mapping

    # --- accept ----------------------------------------------------------
    def _on_accept(self):
        try:
            if self.tabs.currentIndex() == 0:
                s2g = self._matrix_assignment()
                # Remember the assignment so reopening the dialog restores it.
                self.result_state = {
                    "feature_col": self.feature_combo.currentText(),
                    "assignment": {k: v for k, v in s2g.items() if v},
                }
                if not any(v for v in s2g.values()):
                    raise ValueError("Assign at least one sample to a group.")
                if len({v for v in s2g.values() if v}) < 2:
                    QMessageBox.information(
                        self, "One group",
                        "Only one group is defined — statistics need at least two. "
                        "You can still build the table.")
                if self.mode_diff.isChecked():
                    # Differential screen: exactly 2 groups -> results table (log2FC/p/FDR).
                    if len({v for v in s2g.values() if v}) != 2:
                        raise ValueError("The differential screen needs exactly 2 groups; "
                                         "assign your samples to two groups only.")
                    loaded, dres = self.controller.run_differential_screen(
                        self.data, feature_col=self.feature_combo.currentText(),
                        group_labels=s2g, test=self.diff_test_combo.currentData())
                    # Persist the results table so it exists as a file.
                    import os as _os
                    import tempfile as _tempfile
                    src = getattr(self.data, "source_path", None)
                    outdir = _os.path.dirname(src) if src else _tempfile.gettempdir()
                    outpath = _os.path.join(outdir, _os.path.basename(loaded.table_name))
                    try:
                        self.controller.save_table(loaded.info.dataframe, outpath)
                        loaded.source_path = outpath
                    except Exception:
                        outpath = None
                    msg = dres.method_sentence()
                    if outpath:
                        msg += f"\n\nResults saved to: {outpath}"
                    if dres.warnings:
                        msg += "\n\n⚠ " + "\n⚠ ".join(dres.warnings)
                    msg += ("\n\nVolcano / MA / top-feature plots are now recommended from this "
                            "results table.")
                    QMessageBox.information(self, "Differential screen complete", msg)
                elif self.mode_wide.isChecked():
                    # Heatmap/PCA: keep the matrix (assigned samples only) + a group strip.
                    loaded, self.column_annotations = self.controller.group_from_matrix_wide(
                        self.data, sample_columns=self._sample_columns(),
                        sample_to_group=s2g, feature_col=self.feature_combo.currentText(),
                        features=self._selected_features())
                else:
                    loaded = self.controller.group_from_matrix(
                        self.data, sample_columns=self._sample_columns(),
                        sample_to_group=s2g, feature_col=self.feature_combo.currentText(),
                        features=self._selected_features())
            else:
                mapping = self._value_mapping()
                if not mapping:
                    raise ValueError("Map at least one value to a group.")
                new_col = self.new_col_edit.text().strip() or "group"
                loaded = self.controller.add_group_column(
                    self.data, source_col=self.source_combo.currentText(),
                    value_to_group=mapping, new_col=new_col)
        except Exception as exc:
            QMessageBox.warning(self, "Could not create groups", str(exc))
            return
        self.grouped.emit(loaded)
        self.accept()
