"""Long dropdowns must stay reachable as the registry grows.

Qt's default combo popup grows to fit every entry and can run past the bottom of
the screen with no scrollbar, leaving the entries below it unreachable. The plot
list crossed that threshold at 45 plot types; this guards the fix so adding more
never silently hides them again.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="desktop GUI tests need PySide6")

from PySide6.QtWidgets import QApplication, QComboBox  # noqa: E402


@pytest.fixture(scope="module")
def window(qapp_args=None):
    app = QApplication.instance() or QApplication([])
    from apps.desktop_app.main import MainWindow
    win = MainWindow()
    yield win
    win.close()


def test_plot_type_dropdown_lists_every_registered_plot_type(window):
    from make_my_figure_core.plots.registry import available_plot_types
    # +1 for the "no plot selected" placeholder
    assert window.plot_combo.count() == len(available_plot_types()) + 1


def test_plot_type_dropdown_popup_is_scrollable(window):
    """The whole point: entries past the visible window must be reachable."""
    combo = window.plot_combo
    assert combo.count() > combo.maxVisibleItems(), \
        "test is meaningless unless the list is longer than the popup"
    assert "combobox-popup" in (combo.styleSheet() or ""), \
        "Qt only honours maxVisibleItems (and draws a scrollbar) with combobox-popup: 0"
    combo.showPopup()
    try:
        bar = combo.view().verticalScrollBar()
        assert bar is not None and bar.maximum() > 0, \
            "popup has no scroll range, so the lower entries cannot be reached"
    finally:
        combo.hidePopup()


def test_popup_is_capped_rather_than_growing_with_the_list(window):
    combo = window.plot_combo
    row = max(combo.view().sizeHintForRow(0), 1)
    combo.showPopup()
    try:
        height = combo.view().height()
    finally:
        combo.hidePopup()
    assert height < row * combo.count(), \
        "popup grew to fit every entry, which is what runs it off the screen"


def test_every_long_dropdown_is_scrollable(window):
    """Any combo that can outgrow the screen needs the same treatment."""
    for name in ("plot_combo", "preset_combo"):
        combo = getattr(window, name, None)
        if isinstance(combo, QComboBox):
            assert "combobox-popup" in (combo.styleSheet() or ""), \
                f"{name} can grow with use but has the default non-scrollable popup"
