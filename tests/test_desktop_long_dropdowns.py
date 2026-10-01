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


def test_the_size_boxes_cannot_be_set_to_an_unusable_value(window):
    """0 means auto; anything between 0 and the floor snaps out of the dead zone.

    A figure a fraction of an inch across is never intended, and the control
    should not let it be dialled in at all rather than relying on a later
    correction in the renderer.
    """
    window.size_units.setCurrentText("inches")
    floor = window._size_floor_in_current_units()
    for name in ("fig_w_mm", "fig_h_mm"):
        box = getattr(window, name)
        box.setValue(0.0)
        assert box.value() == 0.0, f"{name}: 0 must stay 0 (auto)"
        for attempt in (0.1, 0.5, round(floor - 0.05, 2)):
            box.setValue(attempt)
            assert box.value() == pytest.approx(floor, abs=0.02), \
                f"{name}: {attempt} in should snap to {floor:.2f}, got {box.value()}"
        box.setValue(4.0)
        assert box.value() == pytest.approx(4.0)
        box.setValue(0.0)


def test_switching_units_keeps_the_same_physical_size(window):
    """Changing the unit is a change of display, not of intent."""
    window.size_units.setCurrentText("inches")
    window.fig_w_mm.setValue(4.0)
    window.fig_h_mm.setValue(2.0)
    as_mm_w = window._size_value_to_mm(window.fig_w_mm.value())
    window.size_units.setCurrentText("mm")
    assert window.fig_w_mm.value() == pytest.approx(101.6, abs=1.0)
    assert window._size_value_to_mm(window.fig_w_mm.value()) == pytest.approx(as_mm_w, abs=1.0)
    window.size_units.setCurrentText("inches")
    assert window.fig_w_mm.value() == pytest.approx(4.0, abs=0.05)
    window.fig_w_mm.setValue(0.0)
    window.fig_h_mm.setValue(0.0)


def test_figure_size_lives_in_its_own_section_not_under_labels(window):
    """Figure dimensions are not a label property."""
    from PySide6.QtWidgets import QGroupBox
    titles = [g.title() for g in window.findChildren(QGroupBox)]
    assert any("Figure size" in t for t in titles), titles
    assert not any("Labels & size" in t for t in titles), titles
