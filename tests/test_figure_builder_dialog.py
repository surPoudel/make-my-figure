"""Geometry + navigation regressions for the multi-panel Figure Builder dialog.

The user could not reach "Save figure..." without maximising the window, and the top
form rows were crushed into overlapping text. These tests measure the layout rather
than eyeballing it: nothing may render below its own minimum size hint, the exits must
stay pinned outside the scroll area, and the help paragraph must be fully drawn.

Qt aborts the interpreter if several top-level windows are torn down mid-suite, so this
module builds ONE MainWindow (module scope) and at most one dialog per test, always
closed in a finally block.
"""

import copy
import os
import sys

import pytest

# Qt loads its native libraries on the real class import, so guard the whole module and
# skip (not error) where PySide6 cannot load headlessly.
try:
    from PySide6.QtWidgets import QApplication  # noqa: F401
except Exception as exc:  # noqa: BLE001
    pytest.skip(f"PySide6/Qt unavailable: {exc}", allow_module_level=True)

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QAbstractButton,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QLabel,
    QScrollArea,
    QSpinBox,
    QSplitter,
)

from apps.desktop_app.main import MainWindow  # noqa: E402
from apps.desktop_app.stats_panel import FigureBuilderDialog  # noqa: E402


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    yield a


@pytest.fixture(scope="module")
def panel_source(app):
    """One MainWindow for the whole module, used only to mint realistic panel dicts."""
    win = MainWindow()
    for example in ("scatterplot_with_regression", "barplot_with_error_bar", "volcano_plot"):
        win.load_example(example)
        win.action_save_panel()
    assert len(win._saved_panels) == 3
    yield win
    win.close()


@pytest.fixture
def panels(panel_source):
    # Deep-copy so reorder/remove tests cannot leak into each other or into the window.
    return copy.deepcopy(panel_source._saved_panels)


def _open(panel_source, panels):
    """Show a builder dialog at its own default size, laid out and ready to measure."""
    dlg = FigureBuilderDialog(panel_source.controller, panels, panel_source)
    dlg.show()
    QApplication.processEvents()
    QApplication.processEvents()
    return dlg


def _controls_column(dlg):
    return dlg.controls_scroll.parentWidget()


# --- 1. the left column scrolls ---------------------------------------------------


def test_left_controls_live_in_a_scroll_area(app, panel_source, panels):
    dlg = _open(panel_source, panels)
    try:
        assert isinstance(dlg.controls_scroll, QScrollArea)
        assert dlg.controls_scroll.widgetResizable() is True
        assert dlg.controls_scroll.verticalScrollBarPolicy() == Qt.ScrollBarAsNeeded
        # the splitter between controls and preview survives
        split = dlg.findChild(QSplitter)
        assert split is not None and split.count() == 2
        assert split.widget(0) is _controls_column(dlg)
        # the form controls really are inside the scroll area, not siblings of it
        for widget in (dlg.name_combo, dlg.width_mm_spin, dlg.size_group, dlg.label_spin):
            assert dlg.controls_scroll.isAncestorOf(widget), widget
    finally:
        dlg.close()


def test_every_control_is_reachable_by_scrolling_at_the_default_size(app, panel_source, panels):
    dlg = _open(panel_source, panels)
    try:
        scroll = dlg.controls_scroll
        inner = scroll.widget()
        # The content is taller than the viewport (that was the whole complaint), so the
        # scroll area must expose exactly the overflow - no more, no less.
        overflow = inner.height() - scroll.viewport().height()
        assert overflow > 0, "content no longer overflows; the scroll test is vacuous"
        assert scroll.verticalScrollBar().maximum() == overflow
        # Scrolled to the bottom, the last control in the column is inside the viewport.
        scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
        QApplication.processEvents()
        bottom = dlg.legend_text.mapTo(scroll.viewport(), dlg.legend_text.rect().bottomLeft())
        assert bottom.y() <= scroll.viewport().height() + 1
        # ...and no sideways scrolling is ever needed at the opening width.
        assert scroll.horizontalScrollBar().maximum() == 0
    finally:
        dlg.close()


# --- 2. nothing is compressed -----------------------------------------------------


_MEASURED = (QComboBox, QSpinBox, QDoubleSpinBox, QLabel, QAbstractButton, QGroupBox)


def test_no_control_is_compressed_below_its_minimum(app, panel_source, panels):
    dlg = _open(panel_source, panels)
    try:
        undersized = []
        for cls in _MEASURED:
            for widget in dlg.findChildren(cls):
                if not widget.isVisibleTo(dlg):
                    continue
                need = widget.minimumSizeHint()
                if widget.height() < need.height() - 1 or widget.width() < need.width() - 1:
                    undersized.append((type(widget).__name__,
                                       (widget.text() if hasattr(widget, "text") else "")[:40],
                                       (widget.width(), widget.height()),
                                       (need.width(), need.height())))
        assert undersized == [], undersized
    finally:
        dlg.close()


def test_form_rows_keep_their_natural_height(app, panel_source, panels):
    dlg = _open(panel_source, panels)
    try:
        # These are the rows the user's screenshot showed squashed into each other.
        for widget in (dlg.name_combo, dlg.cols_combo, dlg.rows_combo, dlg.width_mm_spin,
                       dlg.wspace_spin, dlg.hspace_spin, dlg.label_style_combo, dlg.dpi_spin):
            assert widget.height() >= widget.sizeHint().height(), widget
    finally:
        dlg.close()


def test_panel_size_help_text_is_fully_drawn(app, panel_source, panels):
    dlg = _open(panel_source, panels)
    try:
        hint = dlg.size_hint_label
        assert hint.wordWrap() is True
        assert hint.width() > 0
        # A wrapped label needs heightForWidth rows; anything less cuts the paragraph off.
        assert hint.height() >= hint.heightForWidth(hint.width())
        # and the whole label is inside the scrollable content, not clipped out of it
        inner = dlg.controls_scroll.widget()
        bottom_right = hint.mapTo(inner, hint.rect().bottomRight())
        assert bottom_right.y() <= inner.height()
        assert bottom_right.x() <= inner.width()
    finally:
        dlg.close()


def test_no_single_line_label_is_elided(app, panel_source, panels):
    dlg = _open(panel_source, panels)
    try:
        clipped = []
        for label in dlg.findChildren(QLabel):
            if not label.isVisibleTo(dlg) or label.wordWrap() or not label.text():
                continue
            needed = label.fontMetrics().horizontalAdvance(label.text())
            if label.width() < needed:
                clipped.append((label.text(), label.width(), needed))
        assert clipped == [], clipped
    finally:
        dlg.close()


# --- 3. the exits stay put --------------------------------------------------------


def _action_buttons(dlg):
    wanted = {"Save figure...", "Save Figure Package…", "Close"}
    found = {b.text(): b for b in dlg.findChildren(QAbstractButton) if b.text() in wanted}
    assert set(found) == wanted, sorted(found)
    return found


def test_action_buttons_are_pinned_outside_the_scroll_area(app, panel_source, panels):
    dlg = _open(panel_source, panels)
    try:
        scroll = dlg.controls_scroll
        for name, button in _action_buttons(dlg).items():
            assert not scroll.isAncestorOf(button), name
            assert dlg.action_bar.isAncestorOf(button), name
    finally:
        dlg.close()


def test_action_buttons_stay_visible_while_the_column_scrolls(app, panel_source, panels):
    dlg = _open(panel_source, panels)
    try:
        buttons = _action_buttons(dlg)
        before = {n: b.mapTo(dlg, b.rect().topLeft()) for n, b in buttons.items()}
        bar = dlg.rect()
        for name, button in buttons.items():
            assert button.isVisibleTo(dlg), name
            top_left = before[name]
            assert bar.contains(top_left), (name, top_left)
            assert bar.contains(top_left.x() + button.width() - 1,
                                top_left.y() + button.height() - 1), name
        sb = dlg.controls_scroll.verticalScrollBar()
        sb.setValue(sb.maximum())
        QApplication.processEvents()
        after = {n: b.mapTo(dlg, b.rect().topLeft()) for n, b in buttons.items()}
        assert after == before, "scrolling the controls moved the action buttons"
    finally:
        dlg.close()


# --- 4. panel navigation ----------------------------------------------------------


def test_panel_rows_lead_with_their_letter(app, panel_source, panels):
    dlg = _open(panel_source, panels)
    try:
        rows = [dlg.list.item(i).text() for i in range(dlg.list.count())]
        assert len(rows) == 3
        assert [r[0] for r in rows] == ["A", "B", "C"]
    finally:
        dlg.close()


def test_long_panel_title_does_not_widen_the_column(app, panel_source, panels):
    panels[1]["title"] = "Relative luminescence of transfected HEK293T across all timepoints"
    dlg = _open(panel_source, panels)
    try:
        before = dlg.controls_scroll.widget().width()
        dlg.list.setCurrentRow(1)
        QApplication.processEvents()
        assert dlg.controls_scroll.widget().width() == before
        assert dlg.controls_scroll.horizontalScrollBar().maximum() == 0
        assert len(dlg.size_group.title()) < 60
    finally:
        dlg.close()


def test_selected_panel_is_named_in_the_size_group(app, panel_source, panels):
    dlg = _open(panel_source, panels)
    try:
        dlg.list.setCurrentRow(1)
        QApplication.processEvents()
        title = dlg.size_group.title()
        assert "B" in title and panels[1]["title"][:20] in title
        assert dlg.size_group.isEnabled()
    finally:
        dlg.close()


def test_list_offers_drag_to_reorder(app, panel_source, panels):
    dlg = _open(panel_source, panels)
    try:
        assert dlg.list.dragDropMode() == dlg.list.DragDropMode.InternalMove
        assert dlg.list.defaultDropAction() == Qt.MoveAction
    finally:
        dlg.close()


def test_dragging_a_row_reorders_the_panels(app, panel_source, panels):
    dlg = _open(panel_source, panels)
    try:
        titles = [p["title"] for p in panels]
        # An internal-move drop is exactly a takeItem + insertItem on the view.
        dlg.list.insertItem(2, dlg.list.takeItem(0))
        dlg.list.setCurrentRow(2)
        QApplication.processEvents()
        assert [p["title"] for p in dlg.saved_panels] == [titles[1], titles[2], titles[0]]
        # the backing list object is shared with MainWindow, so it must be mutated in place
        assert dlg.saved_panels is panels
        # the dragged panel stays selected, and the letters are renumbered
        assert dlg.list.currentRow() == 2
        assert [dlg.list.item(i).text()[0] for i in range(3)] == ["A", "B", "C"]
        assert titles[0] in dlg.list.item(2).text()
    finally:
        dlg.close()


def test_alt_arrow_keys_move_the_selected_panel(app, panel_source, panels):
    dlg = _open(panel_source, panels)
    try:
        titles = [p["title"] for p in panels]
        dlg.list.setCurrentRow(0)
        QTest.keyClick(dlg.list, Qt.Key_Down, Qt.AltModifier)
        QApplication.processEvents()
        assert [p["title"] for p in dlg.saved_panels] == [titles[1], titles[0], titles[2]]
        assert dlg.list.currentRow() == 1
        QTest.keyClick(dlg.list, Qt.Key_Up, Qt.AltModifier)
        QApplication.processEvents()
        assert [p["title"] for p in dlg.saved_panels] == titles
        assert dlg.list.currentRow() == 0
    finally:
        dlg.close()


def test_move_up_down_still_work_and_refresh_letters(app, panel_source, panels):
    dlg = _open(panel_source, panels)
    try:
        titles = [p["title"] for p in panels]
        dlg.list.setCurrentRow(2)
        dlg._move(-1)
        QApplication.processEvents()
        assert [p["title"] for p in dlg.saved_panels] == [titles[0], titles[2], titles[1]]
        assert dlg.list.currentRow() == 1
        assert titles[2] in dlg.list.item(1).text()
    finally:
        dlg.close()


def test_removing_and_duplicating_do_not_trip_the_reorder_sync(app, panel_source, panels):
    dlg = _open(panel_source, panels)
    try:
        titles = [p["title"] for p in panels]
        dlg.list.setCurrentRow(1)
        dlg._duplicate()
        QApplication.processEvents()
        assert [p["title"] for p in dlg.saved_panels] == [titles[0], titles[1], titles[1],
                                                          titles[2]]
        dlg.list.setCurrentRow(0)
        dlg._remove()
        QApplication.processEvents()
        assert [p["title"] for p in dlg.saved_panels] == [titles[1], titles[1], titles[2]]
    finally:
        dlg.close()


# --- 5. default window size -------------------------------------------------------


def test_default_size_is_bigger_than_the_old_980x640(app, panel_source, panels):
    dlg = _open(panel_source, panels)
    try:
        want_w, want_h = dlg._preferred_size(1240, 900)
        assert (dlg.width(), dlg.height()) == (want_w, want_h)
        avail = QApplication.primaryScreen().availableGeometry()
        # it asks for more than the cramped old default, but never more than the screen
        assert want_w >= min(1240, avail.width() - 80)
        assert want_h >= min(900, avail.height() - 80)
        assert dlg.width() <= avail.width() and dlg.height() <= avail.height()
    finally:
        dlg.close()


def test_preferred_size_clamps_to_a_small_screen(app, panel_source, panels):
    dlg = _open(panel_source, panels)
    try:
        avail = QApplication.primaryScreen().availableGeometry()
        w, h = dlg._preferred_size(10_000, 10_000)
        assert w <= max(640, avail.width() - 80)
        assert h <= max(480, avail.height() - 80)
    finally:
        dlg.close()


# --- 7. the size controls reach the figure ----------------------------------------
#
# The reported complaint was end to end: "I tried to increase height of plot
# keeping same width, it did not work". The builder's own tests prove the layout
# maths; these prove the dialog is actually wired to it, which is where the fix
# would otherwise be invisible.

def _drawn_boxes(dlg):
    """Every panel's drawn box, in inches, from a real build."""
    from make_my_figure_core.panels.builder import build_figure

    figure = build_figure(dlg._build_mpf())
    figure.canvas.draw()
    w_in, h_in = (float(v) for v in figure.get_size_inches())
    boxes = [(ax.get_position().width * w_in, ax.get_position().height * h_in)
             for ax in figure.axes]
    import matplotlib.pyplot as plt
    plt.close(figure)
    return boxes


def test_the_height_spin_changes_the_drawn_panel(app, panel_source, panels):
    """Setting a height used to do nothing at all: it only fed the row height,
    while the image was always fitted to the cell WIDTH at its own aspect."""
    dlg = _open(panel_source, panels)
    try:
        dlg.list.setCurrentRow(0)
        QApplication.processEvents()
        dlg.ph_spin.setValue(0.0)                    # auto
        QApplication.processEvents()
        auto_h = _drawn_boxes(dlg)[0][1]

        dlg.ph_spin.setValue(round(auto_h * 2.0, 2))
        QApplication.processEvents()
        taller_w, taller_h = _drawn_boxes(dlg)[0]

        assert taller_h > auto_h * 1.5, (
            f"asked for {auto_h * 2:.2f} in tall, drew {taller_h:.2f} in "
            f"(auto was {auto_h:.2f} in)")
    finally:
        dlg.close()


def test_the_height_spin_does_not_distort_the_panel(app, panel_source, panels):
    """Taller must mean re-drawn taller, not stretched. A stretched scientific
    figure is a misleading one."""
    dlg = _open(panel_source, panels)
    try:
        dlg.list.setCurrentRow(0)
        QApplication.processEvents()
        dlg.pw_spin.setValue(3.0)
        dlg.ph_spin.setValue(4.5)
        QApplication.processEvents()
        width, height = _drawn_boxes(dlg)[0]
        assert height > width, (
            f"asked for 3.0 x 4.5 in (portrait) and drew {width:.2f} x {height:.2f}")
    finally:
        dlg.close()


def test_the_fill_cell_box_exists_and_is_off_by_default(app, panel_source, panels):
    """Keeping a panel's proportions stays the default; filling is opt-in."""
    dlg = _open(panel_source, panels)
    try:
        dlg.list.setCurrentRow(0)
        QApplication.processEvents()
        assert dlg.fill_cell_check.isVisible()
        assert not dlg.fill_cell_check.isChecked()
    finally:
        dlg.close()


def test_ticking_fill_cell_reaches_the_built_figure(app, panel_source, panels):
    """The field round-trips in saved files; this is the part that was missing -
    that the dialog can actually set it."""
    dlg = _open(panel_source, panels)
    try:
        dlg.list.setCurrentRow(1)
        QApplication.processEvents()
        dlg.fill_cell_check.setChecked(True)
        QApplication.processEvents()
        assert dlg.saved_panels[1].get("fill_cell") is True
        panel = dlg._build_mpf().panels[1]
        assert panel.fill_cell is True, "the checkbox never reached the Panel"
    finally:
        dlg.close()


def test_the_size_help_no_longer_claims_height_is_ignored(app, panel_source, panels):
    """The old text said the panel "keeps its own proportions ... a larger number
    just makes a larger version", which described the bug, not the behaviour."""
    dlg = _open(panel_source, panels)
    try:
        text = dlg.size_hint_label.text()
        assert "just makes a larger version" not in text
        assert "fill" in text.lower(), "the help never mentions the new control"
    finally:
        dlg.close()
