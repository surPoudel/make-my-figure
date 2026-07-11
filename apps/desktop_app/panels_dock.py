"""Pop-out / pop-in panel manager for the desktop app (v0.5).

Lets users detach major workbench panels (figure, data, controls, statistics,
annotations, RNA-seq, QA/messages) into floating top-level windows — usable on a
second monitor — and dock them back to their original splitter position, without
losing any state (the *same* widget instances are reparented, never recreated).

Design choice: this is an **additive** manager that reparents widgets between
their home ``QSplitter`` slot and a floating ``QWidget`` window. It does not
convert the workbench to ``QDockWidget``s, so it can't break the existing
splitter layout. Floating windows are ordinary OS windows (multi-monitor,
resizable, not always-on-top). Layout (which panels float + geometry) persists
via ``QSettings``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


@dataclass
class _Panel:
    key: str
    title: str
    widget: QWidget
    home: QSplitter          # the splitter the widget normally lives in
    index: int               # its position within that splitter
    window: Optional[QWidget] = None   # floating window when detached


class _FloatWindow(QWidget):
    """A plain top-level window that docks its panel back when closed."""

    def __init__(self, manager: "PanelManager", key: str, title: str):
        super().__init__(None)  # top-level: a normal OS window
        self._manager = manager
        self._key = key
        self.setWindowTitle(f"{title} — Make My Figure")
        self.setWindowFlag(Qt.Window, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        bar = QHBoxLayout()
        bar.addWidget(QLabel(f"<b>{title}</b>"))
        bar.addStretch(1)
        dock_btn = QPushButton("⮊  Dock back")
        dock_btn.clicked.connect(lambda: self._manager.dock(key))
        bar.addWidget(dock_btn)
        lay.addLayout(bar)
        self._body = QVBoxLayout()
        lay.addLayout(self._body)

    def body_layout(self) -> QVBoxLayout:
        return self._body

    def closeEvent(self, event):  # noqa: N802 (Qt signature)
        # Closing a floating panel docks it back rather than destroying state.
        self._manager.dock(self._key)
        event.accept()


class PanelManager:
    """Registers panels and toggles them between docked and floating."""

    def __init__(self, main_window, settings=None):
        self._mw = main_window
        self._settings = settings
        self._panels: Dict[str, _Panel] = {}

    # --- registration -------------------------------------------------------
    def register(self, key: str, title: str, widget: QWidget) -> None:
        """Record a widget and where it currently lives (its splitter + index)."""
        home = widget.parent()
        # Walk up to the enclosing QSplitter (widgets may be wrapped).
        target = widget
        while home is not None and not isinstance(home, QSplitter):
            target = home
            home = home.parent()
        if not isinstance(home, QSplitter):
            return  # not in a splitter -> not poppable; skip silently
        self._panels[key] = _Panel(key=key, title=title, widget=target,
                                    home=home, index=home.indexOf(target))

    def keys(self) -> List[str]:
        return list(self._panels)

    def is_floating(self, key: str) -> bool:
        p = self._panels.get(key)
        return bool(p and p.window is not None)

    # --- toggle -------------------------------------------------------------
    def pop_out(self, key: str) -> None:
        p = self._panels.get(key)
        if p is None or p.window is not None:
            return
        # Remember current index so we can dock back to the same slot.
        p.index = p.home.indexOf(p.widget) if p.home.indexOf(p.widget) >= 0 else p.index
        win = _FloatWindow(self, key, p.title)
        p.widget.setParent(None)
        win.body_layout().addWidget(p.widget)
        p.widget.show()
        p.window = win
        # Restore geometry if we saved one.
        if self._settings is not None:
            geo = self._settings.value(f"panel_geo/{key}")
            if isinstance(geo, QByteArray) and not geo.isEmpty():
                win.restoreGeometry(geo)
            else:
                win.resize(720, 560)
        win.show()
        win.raise_()

    def dock(self, key: str) -> None:
        p = self._panels.get(key)
        if p is None or p.window is None:
            return
        win = p.window
        if self._settings is not None:
            self._settings.setValue(f"panel_geo/{key}", win.saveGeometry())
        p.widget.setParent(None)
        idx = min(max(p.index, 0), p.home.count())
        p.home.insertWidget(idx, p.widget)
        p.widget.show()
        p.window = None
        win.close()
        win.deleteLater()

    def toggle(self, key: str) -> None:
        self.dock(key) if self.is_floating(key) else self.pop_out(key)

    def dock_all(self) -> None:
        for key in list(self._panels):
            if self.is_floating(key):
                self.dock(key)

    def reset_layout(self) -> None:
        """Dock everything back and clear saved floating geometry."""
        self.dock_all()
        if self._settings is not None:
            for key in self._panels:
                self._settings.remove(f"panel_geo/{key}")

    # --- persistence --------------------------------------------------------
    def save_state(self) -> None:
        if self._settings is None:
            return
        floating = [k for k in self._panels if self.is_floating(k)]
        self._settings.setValue("panel_floating", floating)
        for key in floating:
            win = self._panels[key].window
            if win is not None:
                self._settings.setValue(f"panel_geo/{key}", win.saveGeometry())

    def restore_state(self) -> None:
        if self._settings is None:
            return
        floating = self._settings.value("panel_floating") or []
        if isinstance(floating, str):
            floating = [floating]
        for key in floating:
            if key in self._panels:
                self.pop_out(key)
