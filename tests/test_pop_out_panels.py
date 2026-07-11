"""Pop-out / pop-in panel manager tests (v0.5).

Require a Qt runtime; skipped cleanly where PySide6 can't load (e.g. headless
CI without system Qt libs). Run in an environment with PySide6 + pytest-qt.
"""

import pytest

# Qt loads native libraries only on the real class import (not on import_module),
# so guard everything and SKIP the whole module where Qt can't load headlessly
# (e.g. CI/sandbox without libxkbcommon) instead of erroring at collection.
try:
    from PySide6.QtWidgets import QLabel, QSplitter, QWidget

    from apps.desktop_app.panels_dock import PanelManager
except Exception as exc:  # noqa: BLE001
    pytest.skip(f"PySide6/Qt unavailable: {exc}", allow_module_level=True)


class _Settings:
    """Minimal QSettings-like stub for testing persistence logic."""

    def __init__(self):
        self._d = {}

    def value(self, k, default=None):
        return self._d.get(k, default)

    def setValue(self, k, v):
        self._d[k] = v

    def remove(self, k):
        self._d.pop(k, None)


@pytest.fixture
def workbench(qtbot):
    split = QSplitter()
    a, b = QLabel("figure"), QLabel("data")
    split.addWidget(a)
    split.addWidget(b)
    qtbot.addWidget(split)
    split.show()
    return split, a, b


def test_register_and_pop_out_and_dock(workbench, qtbot):
    split, a, b = workbench
    mgr = PanelManager(main_window=None, settings=_Settings())
    mgr.register("figure", "Figure", a)
    mgr.register("data", "Data", b)
    assert set(mgr.keys()) == {"figure", "data"}

    assert not mgr.is_floating("figure")
    mgr.pop_out("figure")
    assert mgr.is_floating("figure")
    # a is no longer a child of the splitter while floating
    assert a.parent() is not split
    assert split.count() == 1

    mgr.dock("figure")
    assert not mgr.is_floating("figure")
    assert split.count() == 2
    # docked back into its original slot (index 0)
    assert split.indexOf(a) == 0


def test_dock_all_and_toggle(workbench, qtbot):
    split, a, b = workbench
    mgr = PanelManager(main_window=None, settings=_Settings())
    mgr.register("figure", "Figure", a)
    mgr.register("data", "Data", b)
    mgr.toggle("figure")
    mgr.toggle("data")
    assert mgr.is_floating("figure") and mgr.is_floating("data")
    mgr.dock_all()
    assert not mgr.is_floating("figure") and not mgr.is_floating("data")
    assert split.count() == 2


def test_reset_layout_clears_geometry(workbench, qtbot):
    split, a, b = workbench
    settings = _Settings()
    mgr = PanelManager(main_window=None, settings=settings)
    mgr.register("figure", "Figure", a)
    mgr.pop_out("figure")
    mgr.dock("figure")               # writes panel_geo/figure
    assert settings.value("panel_geo/figure") is not None
    mgr.reset_layout()
    assert settings.value("panel_geo/figure") is None


def test_save_and_restore_floating_state(workbench, qtbot):
    split, a, b = workbench
    settings = _Settings()
    mgr = PanelManager(main_window=None, settings=settings)
    mgr.register("figure", "Figure", a)
    mgr.register("data", "Data", b)
    mgr.pop_out("data")
    mgr.save_state()
    assert "data" in (settings.value("panel_floating") or [])
    # dock, then restore -> data floats again
    mgr.dock_all()
    mgr.restore_state()
    assert mgr.is_floating("data")
    mgr.dock_all()
