"""Model diagnostics window: R's four ``plot(lm)`` panels for the current figure's model."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from make_my_figure_core.statistics.diagnostics import (
    DiagnosticsError,
    diagnostic_figure,
    diagnostics_for_plot,
    panel_choices,
    summary_text,
)


class DiagnosticsDialog(QDialog):
    """Residuals vs Fitted, Normal Q-Q, Scale-Location, Residuals vs Leverage."""

    def __init__(self, data, spec: Dict[str, Any], style=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Model diagnostics")
        self.resize(860, 900)
        self.df: pd.DataFrame = data.info.dataframe
        self.spec = spec
        self.style = style
        self.diag = None

        v = QVBoxLayout(self)
        intro = QLabel(
            "The model behind the statistics, drawn as R's plot(lm). Look for: no pattern and an even band "
            "in <b>Residuals vs Fitted</b>; points on the line in <b>Normal Q-Q</b>; a flat line in "
            "<b>Scale-Location</b> (a rising line means the variance grows with the mean - unequal "
            "variances); no point beyond the Cook's distance 0.5 / 1 lines in <b>Residuals vs Leverage</b>. "
            "Numbered points are rows of the table.")
        intro.setWordWrap(True)
        v.addWidget(intro)
        form = QFormLayout()
        self.panel_combo = QComboBox()
        for p in panel_choices(self.df, spec):
            self.panel_combo.addItem(p, p)
        form.addRow("Panel", self.panel_combo)
        self.response_combo = QComboBox()
        y = (spec.get("mapping") or {}).get("y")
        nums = [c for c in self.df.columns if pd.api.types.is_numeric_dtype(self.df[c])]
        for c in ([y] if y in nums else []) + [c for c in nums if c != y]:
            self.response_combo.addItem(str(c), c)
        self.response_combo.setToolTip("Compare the model on another response - e.g. log10(Growth_cm) made in "
                                       "Prepare table - to see whether a transformation evens the variance.")
        form.addRow("Response", self.response_combo)
        v.addLayout(form)
        self.panel_combo.currentIndexChanged.connect(self._refresh)
        self.response_combo.currentIndexChanged.connect(self._refresh)

        self.canvas_holder = QVBoxLayout()
        v.addLayout(self.canvas_holder, 1)
        self.canvas: Optional[FigureCanvasQTAgg] = None
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        v.addWidget(self.summary)

        row = QHBoxLayout()
        self.btn_save = QPushButton("Save figure…")
        self.btn_save.clicked.connect(self._save_figure)
        self.btn_csv = QPushButton("Save values (CSV)…")
        self.btn_csv.setToolTip("Fitted values, residuals, standardized residuals, leverage and Cook's distance "
                                "for every observation.")
        self.btn_csv.clicked.connect(self._save_values)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        for b in (self.btn_save, self.btn_csv):
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(close)
        v.addLayout(row)
        self._refresh()

    def _refresh(self, *_args) -> None:
        import matplotlib.pyplot as plt

        if self.canvas is not None:
            self.canvas_holder.removeWidget(self.canvas)
            plt.close(self.canvas.figure)
            self.canvas.deleteLater()
            self.canvas = None
        try:
            self.diag = diagnostics_for_plot(self.df, self.spec, panel=self.panel_combo.currentData(),
                                             response=self.response_combo.currentData())
        except DiagnosticsError as exc:
            self.diag = None
            self.summary.setText(f"<span style='color:#b00'>{exc}</span>")
            self.btn_save.setEnabled(False)
            self.btn_csv.setEnabled(False)
            return
        fig = diagnostic_figure(self.diag, self.style)
        self.canvas = FigureCanvasQTAgg(fig)
        self.canvas_holder.addWidget(self.canvas)
        self.btn_save.setEnabled(True)
        self.btn_csv.setEnabled(True)
        self.summary.setText(summary_text(self.diag))

    def _save_figure(self) -> None:
        if self.canvas is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save diagnostic plots", "model_diagnostics.png",
                                              "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)")
        if path:
            self.canvas.figure.savefig(path, dpi=300)

    def _save_values(self) -> None:
        if self.diag is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save diagnostic values", "model_diagnostics.csv",
                                              "CSV (*.csv)")
        if path:
            try:
                self.diag.table().to_csv(path, index=False)
            except OSError as exc:
                QMessageBox.warning(self, "Not saved", str(exc))
