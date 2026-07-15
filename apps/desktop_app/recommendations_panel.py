"""Recommended Figures panel (desktop).

After a table is loaded, Make My Figure profiles it and suggests appropriate
figures. Each card shows the plot type, a confidence, the reason, detected
columns, and any warnings, with actions to Generate the plot, add it to the
Figure Builder, or dismiss it. Expensive suggestions require confirmation before
generating (no heavy analysis runs automatically).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class RecommendationsPanel(QGroupBox):
    """Lists figure recommendations with Generate / Add to Builder / Dismiss."""

    generateRequested = Signal(object)       # emits a Recommendation
    addToBuilderRequested = Signal(object)   # emits a Recommendation

    def __init__(self, parent=None):
        super().__init__("Recommended figures", parent)
        self.setObjectName("recommendationsPanel")
        outer = QVBoxLayout(self)
        self._intro = QLabel("Load a table to see suggested figures.")
        self._intro.setWordWrap(True)
        outer.addWidget(self._intro)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._host = QWidget()
        self._vbox = QVBoxLayout(self._host)
        self._vbox.setAlignment(Qt.AlignTop)
        self._scroll.setWidget(self._host)
        outer.addWidget(self._scroll)
        self._cards: list[QWidget] = []

    def set_recommendations(self, rec_spec) -> None:
        """Populate from a RecommendationSpec (or clear if None)."""
        for c in self._cards:
            c.setParent(None)
        self._cards.clear()
        recs = list(getattr(rec_spec, "recommendations", []) or [])
        if not recs:
            self._intro.setText("No figure recommendations for this table.")
            return
        schema = getattr(rec_spec, "schema", "")
        self._intro.setText(
            f"Detected data type: <b>{schema}</b>. "
            f"{len(recs)} suggested figure(s) — all use the Publication style.")
        for rec in recs:
            self._vbox.addWidget(self._make_card(rec))

    def _make_card(self, rec) -> QWidget:
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        v = QVBoxLayout(card)
        conf = int(round(float(getattr(rec, "confidence", 0)) * 100))
        title = QLabel(f"<b>{getattr(rec, 'display_name', rec.plot_type)}</b>  "
                       f"<span style='color:#666'>({conf}% match)</span>")
        title.setTextFormat(Qt.RichText)
        v.addWidget(title)
        why = QLabel(getattr(rec, "why", ""))
        why.setWordWrap(True)
        why.setStyleSheet("color:#333;")
        v.addWidget(why)
        kind = getattr(rec, "kind", "direct")
        if kind == "transform":
            tnote = QLabel("↻ Reshapes your data and saves a new CSV, then plots it.")
            tnote.setStyleSheet("color:#0a6; font-size:11px;")
            tnote.setWordWrap(True)
            v.addWidget(tnote)
        instr = getattr(rec, "instructions", None)
        if instr:
            il = QLabel("ℹ " + str(instr))
            il.setStyleSheet("color:#345; font-size:11px;")
            il.setWordWrap(True)
            v.addWidget(il)
        missing = getattr(rec, "missing_mappings", None) or []
        if missing:
            m = QLabel("Needs: " + ", ".join(str(x) for x in missing))
            m.setStyleSheet("color:#8a6d00;")
            m.setWordWrap(True)
            v.addWidget(m)
        for w in (getattr(rec, "warnings", None) or []):
            wl = QLabel("⚠ " + str(w))
            wl.setStyleSheet("color:#a03; font-size:11px;")
            wl.setWordWrap(True)
            v.addWidget(wl)

        row = QHBoxLayout()
        gen = QPushButton("Generate")
        gen.setToolTip("Create this plot now (Publication style).")
        gen.setEnabled(getattr(rec, "plot_spec_draft", None) is not None)
        gen.clicked.connect(lambda _=False, r=rec: self.generateRequested.emit(r))
        row.addWidget(gen)
        add = QPushButton("Add to Figure Builder")
        add.setEnabled(getattr(rec, "plot_spec_draft", None) is not None)
        add.clicked.connect(lambda _=False, r=rec: self.addToBuilderRequested.emit(r))
        row.addWidget(add)
        dismiss = QPushButton("Dismiss")
        dismiss.clicked.connect(lambda _=False, c=card: self._dismiss(c))
        row.addWidget(dismiss)
        v.addLayout(row)
        self._cards.append(card)
        return card

    def _dismiss(self, card: QWidget) -> None:
        card.setParent(None)
        if card in self._cards:
            self._cards.remove(card)
