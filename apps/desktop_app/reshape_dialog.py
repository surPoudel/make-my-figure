"""Wide → long dialog: gather repeated-measurement columns into one row per observation.

The wide table is never modified. The dialog builds a
:class:`~make_my_figure_core.tabular.WideToLong` record; the editor derives the
long table from the wide one through it, saves a copy beside the wide file and
keeps "Revert to original data" available.
"""
from __future__ import annotations

from typing import List, Optional

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from make_my_figure_core.tabular import (
    WideToLong,
    preview_wide_to_long,
    suggest_wide_to_long,
    wide_to_long,
)

_PREVIEW_ROWS = 12


class ReshapeDialog(QDialog):
    """Choose the columns to gather and name the new columns; preview the long table."""

    def __init__(self, controller, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reshape wide → long")
        self.resize(900, 700)
        self.controller = controller
        self.raw = controller.raw_of(data)
        self.widedf: pd.DataFrame = self.raw.info.dataframe
        self.result_spec: Optional[WideToLong] = None
        current = controller.reshape_of(data)
        suggestion = suggest_wide_to_long(self.widedf)
        start = current or (suggestion.spec if suggestion else None)

        v = QVBoxLayout(self)
        intro = QLabel(
            f"<b>{self.raw.table_name}</b> — {len(self.widedf)} rows × {self.widedf.shape[1]} columns.<br>"
            "Tick the columns that hold the <i>same measurement</i> repeated (e.g. Month_4, Month_6, …). "
            "They become two columns: one for the column name (e.g. <b>Month</b> = 4, 6, …) and one for "
            "the value (e.g. <b>Growth_cm</b>). Every other column is repeated on each row. "
            "The wide table is not changed; the long table is saved beside it as a new file.")
        intro.setWordWrap(True)
        intro.setTextFormat(Qt.RichText)
        v.addWidget(intro)
        self.suggest_label = QLabel(("Suggested: " + suggestion.reason) if suggestion and not current else "")
        self.suggest_label.setWordWrap(True)
        self.suggest_label.setStyleSheet("color: #2a6;")
        v.addWidget(self.suggest_label)

        top = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("Columns to gather"))
        self.col_list = QListWidget()
        for c in self.widedf.columns:
            it = QListWidgetItem(str(c))
            it.setData(Qt.UserRole, c)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            on = start is not None and c in start.value_columns
            it.setCheckState(Qt.Checked if on else Qt.Unchecked)
            self.col_list.addItem(it)
        self.col_list.itemChanged.connect(self._refresh)
        left.addWidget(self.col_list, 1)
        btns = QHBoxLayout()
        self.btn_numeric = QPushButton("Tick numeric")
        self.btn_numeric.setToolTip("Tick every numeric column (then untick identifiers such as Replicate).")
        self.btn_numeric.clicked.connect(self._tick_numeric)
        self.btn_none = QPushButton("Untick all")
        self.btn_none.clicked.connect(lambda: self._set_all(False))
        btns.addWidget(self.btn_numeric)
        btns.addWidget(self.btn_none)
        left.addLayout(btns)
        top.addLayout(left, 1)

        form = QFormLayout()
        self.names_to = QLineEdit(", ".join(start.names_to) if start else "name")
        self.names_to.setToolTip("Name of the new column that holds the gathered column names. Several "
                                 "names separated by commas split each column name at the separator "
                                 "below (e.g. 'Species, Age' for columns named A_Young, B_Old).")
        self.values_to = QLineEdit(start.values_to if start else "value")
        self.values_to.setToolTip("Name of the new column that holds the values (e.g. Growth_cm).")
        self.prefix = QLineEdit(start.names_prefix if start else "")
        self.prefix.setToolTip("Text removed from the start of every gathered column name "
                               "('Month_' turns Month_4 into 4).")
        self.sep = QLineEdit((start.names_sep or "") if start else "")
        self.sep.setToolTip("Split each column name at this text, one part per name above. Leave empty "
                            "to keep the whole name.")
        self.numeric = QCheckBox("Names that are all numbers become numbers (4, 6, 8 rather than '4', '6', '8')")
        self.numeric.setChecked(start.numeric_names if start else True)
        self.drop = QCheckBox("Leave out empty cells (no observation)")
        self.drop.setChecked(start.drop_missing if start else True)
        form.addRow("Column names go to", self.names_to)
        form.addRow("Values go to", self.values_to)
        form.addRow("Remove prefix", self.prefix)
        form.addRow("Split names at", self.sep)
        form.addRow(self.numeric)
        form.addRow(self.drop)
        for w in (self.names_to, self.values_to, self.prefix, self.sep):
            w.textChanged.connect(self._refresh)
        for w in (self.numeric, self.drop):
            w.stateChanged.connect(self._refresh)
        top.addLayout(form, 2)
        v.addLayout(top, 1)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        v.addWidget(self.status)
        self.preview = QTableWidget(0, 0)
        self.preview.setMinimumHeight(220)
        v.addWidget(self.preview, 1)

        bb = QDialogButtonBox()
        self.btn_apply = bb.addButton("Reshape and use", QDialogButtonBox.AcceptRole)
        self.btn_remove = bb.addButton("Use the wide table", QDialogButtonBox.ResetRole)
        self.btn_remove.setToolTip("Drop the recorded reshape and go back to the wide table.")
        self.btn_remove.setVisible(current is not None)
        bb.addButton(QDialogButtonBox.Cancel)
        self.btn_apply.clicked.connect(self._accept)
        self.btn_remove.clicked.connect(self._remove)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.removed = False
        self._refresh()

    # --- helpers -----------------------------------------------------------------------------
    def _checked(self) -> List[str]:
        out = []
        for i in range(self.col_list.count()):
            it = self.col_list.item(i)
            if it.checkState() == Qt.Checked:
                out.append(it.data(Qt.UserRole))
        return out

    def _set_all(self, on: bool) -> None:
        self.col_list.blockSignals(True)
        for i in range(self.col_list.count()):
            self.col_list.item(i).setCheckState(Qt.Checked if on else Qt.Unchecked)
        self.col_list.blockSignals(False)
        self._refresh()

    def _tick_numeric(self) -> None:
        self.col_list.blockSignals(True)
        for i in range(self.col_list.count()):
            it = self.col_list.item(i)
            num = pd.api.types.is_numeric_dtype(self.widedf[it.data(Qt.UserRole)])
            it.setCheckState(Qt.Checked if num else Qt.Unchecked)
        self.col_list.blockSignals(False)
        self._refresh()

    def spec(self) -> WideToLong:
        names = tuple(n.strip() for n in self.names_to.text().split(",") if n.strip()) or ("name",)
        return WideToLong(value_columns=tuple(self._checked()), names_to=names,
                          values_to=self.values_to.text().strip(), names_prefix=self.prefix.text(),
                          names_sep=self.sep.text() or None, numeric_names=self.numeric.isChecked(),
                          drop_missing=self.drop.isChecked())

    def _refresh(self, *_args) -> None:
        spec = self.spec()
        pv = preview_wide_to_long(self.widedf, spec)
        self.btn_apply.setEnabled(pv.can_apply)
        if not pv.can_apply:
            self.status.setStyleSheet("color: #b00;")
            self.status.setText(" ".join(pv.problems))
            self.preview.setRowCount(0)
            self.preview.setColumnCount(0)
            return
        self.status.setStyleSheet("color: #222;")
        self.status.setText(f"{pv.n_rows_in} rows → {pv.n_rows_out} rows. " + " ".join(pv.notes))
        long, _ = wide_to_long(self.widedf.head(max(1, _PREVIEW_ROWS)), spec)
        head = long.head(_PREVIEW_ROWS)
        self.preview.setColumnCount(head.shape[1])
        self.preview.setHorizontalHeaderLabels([str(c) for c in head.columns])
        self.preview.setRowCount(len(head))
        for i, row in enumerate(head.itertuples(index=False)):
            for j, val in enumerate(row):
                self.preview.setItem(i, j, QTableWidgetItem(str(val)))
        self.preview.resizeColumnsToContents()

    def _accept(self) -> None:
        spec = self.spec()
        if preview_wide_to_long(self.widedf, spec).can_apply:
            self.result_spec = spec
            self.accept()

    def _remove(self) -> None:
        self.removed = True
        self.result_spec = None
        self.accept()
