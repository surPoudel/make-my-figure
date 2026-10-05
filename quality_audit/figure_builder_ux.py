"""Can the user actually reach, read and use every control in the Figure Builder?

Reported from the running app: the left control column of the Multi-panel Figure
Builder cannot be scrolled, so the window has to be maximised before the save
buttons can be clicked; at smaller sizes the labels and fields are crushed into
overlapping, half-clipped text. This opens ``FigureBuilderDialog`` offscreen at a
range of window sizes against a realistic 4-panel composite and measures four
things per widget:

  reachability   is the widget inside the visible viewport - and if not, can the
                 user scroll to it, or must they resize the window?
  compression    is the widget drawn smaller than the size it asked for?
  clipped text   is a label's text elided, or its wrapped text cut off?
  overlap        do two sibling widgets' geometries intersect?

Every one of those four questions has a naive form that invents defects. The
filters that stop it are documented beside each check and in
``figure_builder_ux.md``; a verdict here is a hypothesis about this harness as
much as about the dialog.

    python quality_audit/figure_builder_ux.py
    python quality_audit/figure_builder_ux.py --sizes 980x640,1600x1000
    python quality_audit/figure_builder_ux.py --root /path/to/other/checkout
    python quality_audit/figure_builder_ux.py --verbose

Exit status is non-zero if any BLOCKING problem is found: a control the user
cannot reach without resizing the window, a widget squeezed below its own
minimumSizeHint, or two overlapping siblings.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import warnings

warnings.filterwarnings("ignore")
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_HERE = os.path.dirname(os.path.abspath(__file__))

# The window sizes to measure at. 980x640 is the dialog's own default (it calls
# resize(980, 640) in __init__), so it is the size the user actually gets on
# first open; 800x600 is deliberately smaller than anything the dialog was
# designed for, to show what happens on a laptop or a side-by-side window.
DEFAULT_SIZES = [(800, 600), (980, 640), (1200, 800), (1600, 1000)]

# A realistic composite: four different plot types, four different natural
# aspect ratios, four titles of different lengths. The panel titles feed the
# QListWidget, so a composite of four identically-named panels would understate
# how wide the list wants to be.
PANEL_PLOT_TYPES = [
    "scatterplot_with_regression",
    "barplot_with_error_bar",
    "boxplot_or_violin_with_points",
    "kaplan_meier_survival_curve",
]

# Verdicts ------------------------------------------------------------------
OK = "ok"
SCROLLABLE = "reachable-by-scroll"
UNREACHABLE = "UNREACHABLE"
PARTIAL = "PARTIALLY-CLIPPED"
SQUEEZED = "BELOW-MINIMUM"
UNDERSIZED = "below-sizeHint"
ELIDED = "TEXT-ELIDED"
TEXT_CUT = "WRAPPED-TEXT-CUT"
OVERLAP = "OVERLAP"
WINDOW_FLOOR = "WINDOW-TOO-TALL-TO-SHRINK"
WIDTH_FLOOR = "window-wider-than-asked"
OFF_SCREEN = "BELOW-THE-SCREEN-FOLD"

# Only these three mean "the user cannot do the thing". ``below-sizeHint`` is
# not among them: a sizeHint is a preference, and a layout that honours a
# stretch factor over a preference is behaving correctly. Treating every
# sizeHint shortfall as a defect flags most of the dialog and says nothing.
# Only the *height* floor blocks. A dialog that insists on being 570px wide
# rather than 560 is fine - every screen is wider than it is tall, and the
# controls the user cannot reach are the ones at the bottom. Blocking on the
# width floor turns a 10px rounding into a release-stopping finding.
BLOCKING = {UNREACHABLE, SQUEEZED, OVERLAP, TEXT_CUT, WINDOW_FLOOR, OFF_SCREEN}

# Usable desktop height on the screens this app is actually run on, after the
# taskbar / menu bar / window title bar are taken out. A dialog whose
# minimumSize is taller than this cannot be fitted on that screen at all - its
# bottom edge, and the save buttons on it, are off the display, and no amount of
# maximising brings them back. This is the mechanism behind the report; see the
# .md.
SCREENS = [("1366x768 laptop", 768, 710), ("1920x1080", 1080, 1010),
           ("1440x900 MacBook Air", 900, 840), ("2560x1440", 1440, 1370)]

# The controls the bug report is actually about: the user said they have to
# maximise the window to reach the save buttons. These get their own line in the
# summary so a regression in exactly that path is impossible to miss.
SPOTLIGHT = ("Save figure...", "Save Figure Package…", "Close")


# --- Qt safety --------------------------------------------------------------
# One QApplication for the whole run, reused if the process already has one, and
# never a second. One dialog alive at a time, closed and deleteLater'd (with the
# event loop pumped so the deletion actually happens) before the next is built.
# The suite has aborted on violations of both of these.
_APP = None


def _app():
    global _APP
    from PySide6.QtWidgets import QApplication

    if _APP is None:
        _APP = QApplication.instance() or QApplication([])
    return _APP


def _pump(n: int = 30) -> None:
    """Let the layout settle.

    Qt computes geometry lazily: a widget's size right after ``show()`` is the
    size it was constructed with, not the size the layout will give it. Measuring
    before the layout has run reports the whole dialog as compressed.
    """
    app = _app()
    for _ in range(n):
        app.processEvents()


# --- the composite under test ----------------------------------------------
def build_panels():
    from make_my_figure_core import examples

    panels = []
    for pt in PANEL_PLOT_TYPES:
        info, aux, spec = examples.load_example(pt)
        panels.append({
            "plot_spec": spec,
            "table": info.dataframe.copy(deep=True),
            "aux": {k: v.dataframe for k, v in aux.items()},
            "title": pt.replace("_", " ").capitalize(),
            "plot_type": pt,
        })
    return panels


# --- naming -----------------------------------------------------------------
def widget_names(dlg):
    """Map id(widget) -> the dialog attribute that holds it.

    Half the controls are stored on ``self`` (``self.width_mm_spin``) and half
    are locals in ``_build_controls`` (the Move up / Remove / Save buttons), so
    the fallback has to be the button text or the class name - otherwise the
    report names only half of what it finds and the other half is unactionable.
    """
    from PySide6.QtWidgets import QWidget

    out = {}
    for name in dir(dlg):
        if name.startswith("__"):
            continue
        try:
            value = getattr(dlg, name)
        except Exception:  # noqa: BLE001 - a property that raises is not a widget
            continue
        if isinstance(value, QWidget):
            out.setdefault(id(value), name)
    return out


def describe(widget, names):
    from PySide6.QtWidgets import QAbstractButton, QGroupBox, QLabel

    name = names.get(id(widget))
    if name:
        return name
    for getter in ("text", "title", "placeholderText"):
        if isinstance(widget, (QAbstractButton, QLabel, QGroupBox)) or getter == "placeholderText":
            try:
                text = getattr(widget, getter)()
            except Exception:  # noqa: BLE001
                continue
            if text:
                return f"{widget.__class__.__name__}({text[:44]!r})"
    if widget.objectName():
        return f"{widget.__class__.__name__}#{widget.objectName()}"
    return widget.__class__.__name__


def form_row_label(widget):
    """The QFormLayout label sitting beside a field, if there is one.

    A bare ``QDoubleSpinBox`` is three different controls in this dialog. Without
    its row label the report cannot say *which* spinner is unreachable.
    """
    from PySide6.QtWidgets import QFormLayout

    parent = widget.parentWidget()
    if parent is None:
        return ""
    for form in parent.findChildren(QFormLayout) + ([parent.layout()] if parent.layout() else []):
        if not isinstance(form, QFormLayout):
            continue
        for row in range(form.rowCount()):
            item = form.itemAt(row, QFormLayout.FieldRole)
            if item is not None and item.widget() is widget:
                lab = form.itemAt(row, QFormLayout.LabelRole)
                if lab is not None and lab.widget() is not None:
                    return lab.widget().text()
    return ""


# --- geometry ---------------------------------------------------------------
def rect_in(widget, root):
    from PySide6.QtCore import QPoint, QRect

    return QRect(widget.mapTo(root, QPoint(0, 0)), widget.size())


def visible_rect(widget, root):
    """The part of ``widget`` the user can actually see, in ``root`` coordinates.

    Computed by intersecting the widget's rectangle with every ancestor's
    rectangle up to the dialog, rather than by asking Qt for
    ``visibleRegion()``. ``visibleRegion()`` is derived from the paint system and
    returns an empty region for widgets that simply have not been painted yet
    under the offscreen platform plugin, which would report the entire dialog as
    invisible. Intersecting geometry asks the question the layout answers.
    """
    from PySide6.QtCore import QPoint, QRect

    rect = rect_in(widget, root)
    clip = QRect(QPoint(0, 0), root.size())
    ancestor = widget.parentWidget()
    while ancestor is not None:
        clip = clip.intersected(QRect(ancestor.mapTo(root, QPoint(0, 0)), ancestor.size()))
        if ancestor is root:
            break
        ancestor = ancestor.parentWidget()
    return rect, rect.intersected(clip)


def is_internal(widget, root):
    """True for a widget Qt built inside another widget.

    ``QDoubleSpinBox`` contains a ``QLineEdit``; an editable ``QComboBox``
    contains one too; ``QListWidget`` contains a viewport and two scrollbars.
    Counting those as separate controls triples the apparent widget count and
    produces findings the user has no way to act on - there is no "the line edit
    inside the DPI spinner" for them to reach.
    """
    from PySide6.QtWidgets import QAbstractItemView, QAbstractSpinBox, QComboBox

    ancestor = widget.parentWidget()
    while ancestor is not None and ancestor is not root:
        if isinstance(ancestor, (QAbstractSpinBox, QComboBox, QAbstractItemView)):
            return True
        ancestor = ancestor.parentWidget()
    return bool(widget.objectName().startswith("qt_"))


def scroll_ancestors(widget, root):
    from PySide6.QtWidgets import QAbstractScrollArea

    out = []
    ancestor = widget.parentWidget()
    while ancestor is not None and ancestor is not root:
        if isinstance(ancestor, QAbstractScrollArea):
            out.append(ancestor)
        ancestor = ancestor.parentWidget()
    return out


def _scroll_to(area, widget, root):
    """Scroll ``area`` as far as it can go toward showing ``widget`` whole.

    Deliberately NOT ``QScrollArea.ensureWidgetVisible``. That method scrolls to
    the widget's *input-method cursor rectangle* when the widget has one, and a
    QDoubleSpinBox does: it reports a 9x15 caret instead of its 23px self. The
    result is a scroll that stops 8px short, the widget stays clipped, and the
    harness calls a control unreachable that the user can simply scroll to. That
    mistake alone accounted for 19 of this audit's first 19 "blocking" findings,
    against a dialog whose scroll area works. Measured, not assumed:
    ``inputMethodQuery(Qt.ImCursorRectangle)`` returns QRect(-3, 0, 9, 15) for
    every spin box here against a base rect of QRect(x, 0, 1, 23).

    So the target scroll offset is computed from the widget's own rectangle in
    the scroll content's coordinates - which do not move when the view scrolls -
    clamped to what the scrollbar actually permits.
    """
    from PySide6.QtCore import QPoint

    content = area.widget() if hasattr(area, "widget") and area.widget() else area.viewport()
    if content is None or not _is_descendant(widget, content):
        return
    origin = widget.mapTo(content, QPoint(0, 0))
    for bar, pos, extent, span in (
            (area.verticalScrollBar(), origin.y(), widget.height(), area.viewport().height()),
            (area.horizontalScrollBar(), origin.x(), widget.width(), area.viewport().width())):
        lowest = pos + extent - span          # smallest offset showing the far edge
        highest = pos                         # largest offset still showing the near edge
        target = min(max(lowest, bar.minimum()), max(highest, bar.minimum()))
        bar.setValue(min(target, bar.maximum()))


def _is_descendant(widget, ancestor):
    node = widget
    while node is not None:
        if node is ancestor:
            return True
        node = node.parentWidget()
    return False


def check_reachability(widget, root):
    """Can the user get at this control without resizing the window?

    Three outcomes that look identical to a naive check and are completely
    different to the user:

    * fully visible - fine.
    * off-view but inside a scroll area that can scroll to it - fine, the user
      scrolls. Tested by actually scrolling (see ``_scroll_to``) and
      re-measuring, then restoring every scrollbar. Reading
      ``verticalScrollBar().maximum() > 0`` instead would pass a widget that sits
      beyond a scroll area's reach as readily as one inside it.
    * off-view with nothing that can scroll to it - the defect. The user must
      resize or maximise the window, which is exactly what was reported.
    """
    rect, vis = visible_rect(widget, root)
    if vis == rect:
        return OK, rect, vis
    areas = scroll_ancestors(widget, root)
    if areas:
        saved = [(a, a.horizontalScrollBar().value(), a.verticalScrollBar().value()) for a in areas]
        try:
            for area in areas:                      # innermost outward
                _scroll_to(area, widget, root)
            _pump(5)
            scrolled, after = visible_rect(widget, root)
            if not after.isEmpty() and after == scrolled:
                return SCROLLABLE, rect, vis
        finally:
            for area, hval, vval in saved:
                area.horizontalScrollBar().setValue(hval)
                area.verticalScrollBar().setValue(vval)
            _pump(5)
    if vis.isEmpty():
        return UNREACHABLE, rect, vis
    return PARTIAL, rect, vis


def check_compression(widget):
    """Is the widget drawn smaller than it asked to be?

    ``minimumSizeHint`` is the hard floor - below it a widget cannot render its
    own content, and that is the crushing the user described. ``sizeHint`` is a
    preference and is reported separately and non-blocking, because a layout
    that gives a stretchy widget less than its preferred size is doing its job,
    not failing.

    Word-wrapped labels are excluded from the *width* comparison entirely: a
    wrapped QLabel's sizeHint width is the width of the whole paragraph on one
    line, so every wrapped label in a 430 px column is "compressed" by hundreds
    of pixels and none of it means anything. Their real failure mode is vertical
    and is measured by ``check_label_text``.
    """
    from PySide6.QtWidgets import QLabel

    notes = []
    msh, sh = widget.minimumSizeHint(), widget.sizeHint()
    wrapped = isinstance(widget, QLabel) and widget.wordWrap()
    if msh.height() > 0 and widget.height() < msh.height():
        notes.append((SQUEEZED, f"height {widget.height()} < minimumSizeHint {msh.height()} "
                                f"({100 * (msh.height() - widget.height()) // msh.height()}% short)"))
    if not wrapped and msh.width() > 0 and widget.width() < msh.width():
        notes.append((SQUEEZED, f"width {widget.width()} < minimumSizeHint {msh.width()} "
                                f"({100 * (msh.width() - widget.width()) // msh.width()}% short)"))
    if not notes:
        if sh.height() > 0 and widget.height() < sh.height():
            notes.append((UNDERSIZED, f"height {widget.height()} < sizeHint {sh.height()}"))
        elif not wrapped and sh.width() > 0 and widget.width() < sh.width():
            notes.append((UNDERSIZED, f"width {widget.width()} < sizeHint {sh.width()}"))
    return notes


def check_label_text(label):
    """Is this label's text actually readable at the size it was given?

    Two different failures, and asking the wrong one of the two is the easiest
    way to produce a page of false findings:

    * a single-line label narrower than its text is *elided* - the user sees
      "Panel letters (A, B...". Proved by running the same elision Qt runs
      (``QFontMetrics.elidedText``) and comparing, not by trusting sizeHint.
    * a word-wrapped label shorter than its wrapped text is *cut* - the last
      lines are simply not drawn, with no ellipsis to warn anyone. Measured with
      ``heightForWidth`` at the width the label was actually given. The
      "Selected panel size" help paragraph is the known case.

    Skipped: labels with no text, labels showing a pixmap (the live preview), and
    labels whose text is drawn by something else. A pixmap label's text() is ""
    anyway, but the preview label is seeded with "Preview appears here." and
    keeps that string after the pixmap replaces it, so the pixmap test has to
    come first or the preview is reported as elided at every size.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFontMetrics

    pix = label.pixmap()
    if pix is not None and not pix.isNull():
        return []
    text = label.text()
    if not text.strip():
        return []
    notes = []
    inner = label.contentsRect()
    if label.wordWrap():
        needed = label.heightForWidth(max(inner.width(), 1))
        if needed > label.height():
            lost = needed - label.height()
            notes.append((TEXT_CUT, f"needs {needed}px tall at {inner.width()}px wide, "
                                    f"has {label.height()}px ({lost}px of text not drawn)"))
    else:
        metrics = QFontMetrics(label.font())
        if metrics.elidedText(text, Qt.ElideRight, inner.width()) != text:
            notes.append((ELIDED, f"text wants {metrics.horizontalAdvance(text)}px, "
                                  f"has {inner.width()}px"))
    return notes


def check_overlap(root, considered):
    """Do two sibling widgets' rectangles intersect?

    In a dialog built entirely from QLayouts this should never fire, and saying
    so is part of the result: the "overlapping text" the user sees is elision and
    compression, not geometric overlap. The check is kept as a guard against a
    future hand-placed widget, and because ruling it out is what lets the other
    three findings be stated confidently.

    Exclusions, each of which otherwise fires on correct code: invisible widgets
    (a QStackedWidget's non-current pages are exactly stacked); Qt-internal
    children (``qt_scrollarea_viewport`` sits under the scrollbars' container by
    design); a QSplitter's handles; and zero-area widgets, which "intersect"
    nothing but compare oddly.
    """
    from PySide6.QtWidgets import QSplitterHandle

    by_parent = {}
    for widget in considered:
        parent = widget.parentWidget()
        if parent is None:
            continue
        by_parent.setdefault(id(parent), []).append(widget)
    found = []
    for siblings in by_parent.values():
        for i, a in enumerate(siblings):
            if isinstance(a, QSplitterHandle) or a.width() <= 0 or a.height() <= 0:
                continue
            for b in siblings[i + 1:]:
                if isinstance(b, QSplitterHandle) or b.width() <= 0 or b.height() <= 0:
                    continue
                if a.geometry().intersects(b.geometry()):
                    found.append((a, b, a.geometry().intersected(b.geometry())))
    return found


def _settle(seconds: float = 2.0) -> None:
    """Pump the event loop for real time, not just queued events.

    The dialog debounces its preview behind a 250 ms single-shot QTimer, and the
    preview pixmap is what gives the right-hand pane its size. ``processEvents``
    alone never advances the clock, so the timer never fires, and the dialog is
    measured in a state the user never sees.
    """
    import time

    app = _app()
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)


def open_dialog(panels, width, height):
    from apps.desktop_app.stats_panel import FigureBuilderDialog

    dlg = FigureBuilderDialog(None, panels, None)
    dlg.resize(width, height)
    dlg.show()
    _pump(40)
    _settle(2.0)          # let the debounced preview render and resize the panes
    _pump(40)
    return dlg


def close_dialog(dlg):
    """Tear one dialog down completely before the next is built.

    The preview timer has to be stopped first: a 250 ms single-shot left armed on
    a dialog that is being deleted fires into a dead object. The temp assets dir
    the dialog makes in ``__init__`` is removed here too, otherwise a full run
    leaves one behind per size.
    """
    import shutil

    for attr in ("_preview_timer",):
        timer = getattr(dlg, attr, None)
        if timer is not None:
            try:
                timer.stop()
            except Exception:  # noqa: BLE001
                pass
    assets = getattr(dlg, "_assets_dir", None)
    dlg.close()
    dlg.setParent(None)
    dlg.deleteLater()
    _pump(40)
    if assets and os.path.isdir(assets):
        shutil.rmtree(assets, ignore_errors=True)


def audit_size(panels, width, height):
    """Measure one window size. Returns a list of row dicts."""
    from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QLabel, QLineEdit, QListWidget,
                                   QPushButton, QSpinBox, QWidget)

    interactive = (QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPushButton, QListWidget)
    dlg = open_dialog(panels, width, height)
    actual_w, actual_h = dlg.width(), dlg.height()
    names = widget_names(dlg)
    rows = []
    considered = []
    try:
        # Qt enforces minimumSize even under the offscreen plugin, so resize()
        # to something smaller than the dialog's floor silently gives a larger
        # window. Measuring the result and calling it "fine at 800x600" is a
        # false pass on the very thing being tested, so the mismatch is a
        # finding in its own right - and it is the finding: a dialog that
        # refuses to shrink does not fit the screen, and its bottom row of
        # buttons is unreachable by any means.
        if actual_w > width or actual_h > height:
            code = WINDOW_FLOOR if actual_h > height else WIDTH_FLOOR
            rows.append({
                "size": f"{width}x{height}", "actual": f"{actual_w}x{actual_h}",
                "widget": "(the dialog itself)", "row_label": "", "class": "FigureBuilderDialog",
                "check": "window-floor", "verdict": code,
                "detail": f"asked for {width}x{height}, minimumSize forced {actual_w}x{actual_h}",
                "x": 0, "y": 0, "w": actual_w, "h": actual_h, "enabled": True})
        for widget in dlg.findChildren(QWidget):
            if is_internal(widget, dlg):
                continue
            # A widget the dialog has deliberately hidden is not a defect. This is
            # the single most important filter: without it every page of a
            # QStackedWidget and every popup view is reported unreachable.
            if not widget.isVisible():
                continue
            is_control = isinstance(widget, interactive)
            is_label = isinstance(widget, QLabel)
            if not (is_control or is_label):
                continue
            considered.append(widget)
            label = describe(widget, names)
            row_label = form_row_label(widget) if is_control else ""
            kind = widget.__class__.__name__
            verdict, rect, vis = check_reachability(widget, dlg)
            findings = []
            if verdict != OK:
                findings.append((verdict, f"rect {rect.width()}x{rect.height()} at "
                                          f"({rect.x()},{rect.y()}), visible "
                                          f"{vis.width()}x{vis.height()}"))
            findings.extend(check_compression(widget))
            if is_label:
                findings.extend(check_label_text(widget))
            if not findings:
                findings = [(OK, "")]
            for code, note in findings:
                rows.append({
                    "size": f"{width}x{height}", "actual": f"{actual_w}x{actual_h}",
                    "widget": label, "row_label": row_label,
                    "class": kind, "check": _check_of(code), "verdict": code, "detail": note,
                    "x": rect.x(), "y": rect.y(), "w": rect.width(), "h": rect.height(),
                    "enabled": widget.isEnabled(),
                })
        for a, b, inter in check_overlap(dlg, considered):
            rows.append({
                "size": f"{width}x{height}", "actual": f"{actual_w}x{actual_h}",
                "widget": f"{describe(a, names)} / {describe(b, names)}",
                "row_label": "", "class": f"{a.__class__.__name__}/{b.__class__.__name__}",
                "check": "overlap", "verdict": OVERLAP,
                "detail": f"overlap {inter.width()}x{inter.height()} in shared parent",
                "x": inter.x(), "y": inter.y(), "w": inter.width(), "h": inter.height(),
                "enabled": True,
            })
    finally:
        close_dialog(dlg)
    return rows


def _check_of(code):
    return {WINDOW_FLOOR: "window-floor", WIDTH_FLOOR: "window-floor",
            OFF_SCREEN: "screen-fit", OK: "-", SCROLLABLE: "reachability", UNREACHABLE: "reachability",
            PARTIAL: "reachability", SQUEEZED: "compression", UNDERSIZED: "compression",
            ELIDED: "clipped-text", TEXT_CUT: "clipped-text", OVERLAP: "overlap"}.get(code, "?")


def self_test():
    """Prove every check can still fire.

    The lesson from ``option_efficacy.py`` was that a control class scoring 0%
    is a broken instrument, not a clean codebase - and three of these four
    checks report zero on the current dialog. Zero is only meaningful if the
    check is known to be alive, so each one is fired here against a widget built
    to fail it. If any line below reports MISSED, every zero in the table above
    is worthless and the harness is lying.

    Runs in the one shared QApplication, on throwaway widgets that are deleted
    before the real dialog is built.
    """
    from PySide6.QtWidgets import QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

    results = []
    host = QWidget()
    host.resize(200, 120)
    host.show()
    _pump(10)

    long_text = "Panel letters and a great deal more text than will ever fit here"
    elide_me = QLabel(long_text, host)
    elide_me.setWordWrap(False)
    elide_me.setGeometry(0, 0, 40, 20)
    _pump(5)
    results.append(("clipped-text / elided single line",
                    any(c == ELIDED for c, _ in check_label_text(elide_me))))

    cut_me = QLabel(long_text * 3, host)
    cut_me.setWordWrap(True)
    cut_me.setGeometry(0, 24, 90, 12)
    _pump(5)
    results.append(("clipped-text / cut wrapped paragraph",
                    any(c == TEXT_CUT for c, _ in check_label_text(cut_me))))

    squeeze_me = QPushButton("A button with a long caption", host)
    squeeze_me.setGeometry(0, 40, 12, 6)
    _pump(5)
    results.append(("compression / below minimumSizeHint",
                    any(c == SQUEEZED for c, _ in check_compression(squeeze_me))))

    over_a = QPushButton("one", host)
    over_a.setGeometry(0, 60, 80, 20)
    over_b = QPushButton("two", host)
    over_b.setGeometry(40, 70, 80, 20)
    over_a.show()
    over_b.show()
    _pump(5)
    results.append(("overlap / two siblings intersect",
                    bool(check_overlap(host, [over_a, over_b]))))

    # Out of view with nothing to scroll -> UNREACHABLE.
    far = QPushButton("far below the fold", host)
    far.setGeometry(0, 4000, 120, 24)
    far.show()
    _pump(5)
    verdict, _r, _v = check_reachability(far, host)
    results.append(("reachability / unreachable, no scroll area", verdict == UNREACHABLE))

    # The same widget inside a scroll area that can reach it -> not a defect.
    host2 = QWidget()
    host2.resize(200, 120)
    area = QScrollArea(host2)
    area.setGeometry(0, 0, 200, 120)
    area.setWidgetResizable(True)
    inner = QWidget()
    layout = QVBoxLayout(inner)
    for i in range(40):
        layout.addWidget(QPushButton(f"button {i}", inner))
    last = inner.findChildren(QPushButton)[-1]
    area.setWidget(inner)
    host2.show()
    _pump(20)
    verdict2, _r, _v = check_reachability(last, host2)
    results.append(("reachability / off-view but scrollable", verdict2 == SCROLLABLE))

    for widget in (host, host2):
        widget.close()
        widget.setParent(None)
        widget.deleteLater()
    _pump(20)
    return results


def screen_fit(panels):
    """Does the dialog fit on the screens people run it on?

    The decisive measurement, and the one the per-size table cannot make: Qt
    honours ``minimumSize`` whatever the window manager is asked for, so if the
    dialog's own floor is 902px tall it is 902px tall on a 768px laptop, with
    its bottom 190px - including the entire save/close row - below the edge of
    the display. Maximising does not help, because maximising cannot make a
    screen taller. Reported separately from the widget table because it is a
    property of the dialog, not of any one control.
    """
    from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QLineEdit, QListWidget,
                                   QPushButton, QSpinBox, QWidget)

    dlg = open_dialog(panels, 1600, 1000)
    floor = dlg.minimumSize()
    hint = dlg.minimumSizeHint()
    close_dialog(dlg)
    out = [(name, usable, floor.height() <= usable) for name, _total, usable in SCREENS]

    # Name the controls that end up below the edge of the smallest screen when
    # the dialog is squeezed as small as it will go. "Something is off-screen"
    # is not actionable; "the three save buttons are off-screen" is.
    lost = []
    worst = min(usable for _n, _t, usable in SCREENS)
    if floor.height() > worst:
        dlg = open_dialog(panels, floor.width(), floor.height())
        names = widget_names(dlg)
        interactive = (QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPushButton, QListWidget)
        try:
            for widget in dlg.findChildren(QWidget):
                if not isinstance(widget, interactive) or is_internal(widget, dlg):
                    continue
                if not widget.isVisible():
                    continue
                rect = rect_in(widget, dlg)
                if rect.y() >= worst:          # entirely past the edge of the display
                    lost.append((describe(widget, names), form_row_label(widget), rect.y()))
        finally:
            close_dialog(dlg)
    return floor, hint, out, sorted(lost, key=lambda t: t[2])


def minimum_usable_height(panels, width=1200, lo=360, hi=1100):
    """The shortest window at which nothing is UNREACHABLE.

    The single number the bug report is about: below this the user has to resize
    or maximise. Binary search, one dialog alive at a time. Returns None if even
    ``hi`` leaves something out of reach.
    """
    def ok_at(height):
        bad = [r for r in audit_size(panels, width, height) if r["verdict"] == UNREACHABLE]
        return not bad

    if not ok_at(hi):
        return None
    while lo < hi:
        mid = (lo + hi) // 2
        if ok_at(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sizes", default=None,
                        help="comma-separated WxH list (default 800x600,980x640,1200x800,1600x1000)")
    parser.add_argument("--root", default=os.path.dirname(_HERE),
                        help="checkout to import the app from (default: this repo)")
    parser.add_argument("--csv", default=os.path.join(_HERE, "figure_builder_ux.csv"))
    parser.add_argument("--min-height", action="store_true",
                        help="also binary-search the shortest window with nothing unreachable")
    parser.add_argument("--verbose", action="store_true", help="list every widget, not just findings")
    args = parser.parse_args(argv)

    sys.path.insert(0, os.path.abspath(args.root))
    sizes = DEFAULT_SIZES
    if args.sizes:
        sizes = [tuple(int(n) for n in part.lower().split("x")) for part in args.sizes.split(",")]

    _app()
    print("self-test: can each check still fire?")
    checks = self_test()
    for name, fired in checks:
        print(f"   {'fires ' if fired else 'MISSED'}  {name}")
    if not all(fired for _n, fired in checks):
        print("\nA check that cannot fire makes every zero below meaningless. Stopping.")
        return 2
    print()
    panels = build_panels()
    rows = []
    for width, height in sizes:
        rows.extend(audit_size(panels, width, height))

    with open(args.csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["size", "actual", "widget", "row_label", "class",
                                                    "check", "verdict", "detail",
                                                    "x", "y", "w", "h", "enabled"])
        writer.writeheader()
        writer.writerows(rows)

    report(rows, sizes, args.verbose)

    floor, hint, fits, lost = screen_fit(panels)
    print(f"\n== does the dialog fit on a real screen? " + "=" * 34)
    print(f"   dialog minimumSize {floor.width()}x{floor.height()} "
          f"(minimumSizeHint {hint.width()}x{hint.height()})")
    for name, usable, ok_here in fits:
        verdict = "fits" if ok_here else (f"DOES NOT FIT - bottom {floor.height() - usable}px "
                                          f"of the dialog is off the display")
        print(f"   {name:<24} {usable:>5}px usable height  {verdict}")
    if not all(f[2] for f in fits):
        rows.append({"size": "-", "actual": f"{floor.width()}x{floor.height()}",
                     "widget": "(the dialog itself)", "row_label": "",
                     "class": "FigureBuilderDialog", "check": "screen-fit", "verdict": WINDOW_FLOOR,
                     "detail": f"minimumSize height {floor.height()}px exceeds usable height of "
                               + ", ".join(n for n, _u, okk in fits if not okk),
                     "x": 0, "y": 0, "w": floor.width(), "h": floor.height(), "enabled": True})
    if lost:
        print(f"\n   {len(lost)} control(s) past the bottom edge of the smallest screen, "
              f"with the window as small as it will go:")
        for name, row_label, y in lost:
            shown = name + (f" [{row_label}]" if row_label else "")
            print(f"      y={y:<5} {shown}")
            rows.append({"size": "-", "actual": f"{floor.width()}x{floor.height()}",
                         "widget": name, "row_label": row_label, "class": "", "check": "screen-fit",
                         "verdict": OFF_SCREEN,
                         "detail": f"top edge at y={y}, below the {min(u for _n, _t, u in SCREENS)}px "
                                   f"usable height of a 1366x768 laptop",
                         "x": 0, "y": y, "w": 0, "h": 0, "enabled": True})

    if args.min_height:
        found = minimum_usable_height(panels)
        print(f"\nShortest window (at 1200px wide) with nothing unreachable: "
              f"{found if found else 'none up to 1100px'}")

    blocking = [r for r in rows if r["verdict"] in BLOCKING]
    print(f"\nFull table: {args.csv}")
    print(f"{len(blocking)} blocking finding(s)." if blocking else "No blocking findings.")
    return 1 if blocking else 0


def report(rows, sizes, verbose):
    order = [WINDOW_FLOOR, OFF_SCREEN, WIDTH_FLOOR, UNREACHABLE, PARTIAL, SQUEEZED, TEXT_CUT, ELIDED, OVERLAP,
             UNDERSIZED, SCROLLABLE, OK]
    print("Multi-panel Figure Builder - reach, fit and legibility of every control")
    print(f"composite: {len(PANEL_PLOT_TYPES)} panels ({', '.join(PANEL_PLOT_TYPES)})\n")
    header = f"{'asked':>10} {'got':>10} | " + " ".join(f"{v[:13]:>14s}" for v in order)
    print(header)
    print("-" * len(header))
    for width, height in sizes:
        key = f"{width}x{height}"
        here = [r for r in rows if r["size"] == key]
        counts = {v: sum(1 for r in here if r["verdict"] == v) for v in order}
        got = here[0]["actual"] if here else key
        print(f"{key:>10} {got:>10} | " + " ".join(f"{counts[v]:>14d}" for v in order))

    for width, height in sizes:
        key = f"{width}x{height}"
        here = [r for r in rows if r["size"] == key and (verbose or r["verdict"] != OK)]
        bad = [r for r in here if r["verdict"] != OK and r["verdict"] != SCROLLABLE]
        got = next((r["actual"] for r in rows if r["size"] == key), key)
        suffix = "" if got == key else f"  (window refused to shrink; actually {got})"
        print(f"\n== {key}{suffix} " + "=" * 40)
        # describe() names an unnamed button QPushButton('Save figure...'), so
        # the spotlight has to match on the text inside, not on equality.
        spot = [r for r in rows if r["size"] == key
                and any(s in r["widget"] for s in SPOTLIGHT)]
        bad_spot = [r for r in spot if r["verdict"] not in (OK, SCROLLABLE, UNDERSIZED)]
        if bad_spot:
            for r in bad_spot:
                print(f"   save/close bar: {r['widget']} -> {r['verdict']} ({r['detail']})")
        elif spot:
            how = {r["verdict"] for r in spot}
            print(f"   save/close bar: {len(spot)} button(s), "
                  + ("reachable by scrolling" if SCROLLABLE in how else "fully visible"))
        else:
            print("   save/close bar: NOT FOUND - the harness could not identify the save buttons")
        if not bad:
            print("   nothing else to report")
        for r in sorted(bad, key=lambda r: (order.index(r["verdict"]), r["y"])):
            name = r["widget"] + (f" [{r['row_label']}]" if r["row_label"] else "")
            print(f"   {r['verdict']:<18} {name:<42} {r['class']:<16} {r['detail']}")


if __name__ == "__main__":
    raise SystemExit(main())
