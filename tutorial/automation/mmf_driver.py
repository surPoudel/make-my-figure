"""Drive the REAL Make My Figure desktop application for tutorials.

The driver instantiates the production ``MainWindow`` (apps/desktop_app/main.py) and operates
its actual widgets: the plot-type combo, the "2. Map columns" combos, the "3. Options" widgets,
the statistics panel, the preset panel, export buttons, the figure-package actions and the
Figure Builder. Nothing is mocked and no tutorial code lives inside the application.

Two modes:

* ``offscreen`` (default) - Qt's offscreen platform. Widgets are rendered at a fixed size and
  grabbed to PNG. This is how tutorial screenshots are produced: real widgets, no display needed.
* ``onscreen`` - a normal window on the current display, with a pause after every action, so a
  screen recorder (OBS, ffmpeg, the OS recorder) can film the real application while the driver
  performs the tutorial steps. Recording is deliberately NOT part of this module.

File dialogs and message boxes are intercepted only when a step needs a path or an answer
(e.g. saving a figure package to a known file). Dialogs that the tutorial wants to show
(Save Figure Preset, Figure Builder) are opened for real; the driver fills their fields and
grabs them before accepting.

The driver never writes into the user's real settings: it points QSettings at a temporary
directory so recent files, splitter state and presets from an author's machine do not leak into
screenshots.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

WINDOW_W, WINDOW_H = 1680, 1000


def _prepare_environment(mode: str, presets_dir: str, settings_dir: str) -> None:
    if mode == "offscreen":
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    # Isolated preset library and settings so the author's machine never shows in a capture.
    os.environ["MAKE_MY_FIGURE_PRESETS"] = presets_dir
    os.environ["XDG_CONFIG_HOME"] = settings_dir          # Linux QSettings location
    os.environ.setdefault("QT_SCALE_FACTOR", "1")
    os.environ.setdefault("QT_FONT_DPI", "96")


@dataclass
class Capture:
    name: str
    path: str
    widget: str
    size: str
    note: str = ""


@dataclass
class DriverLog:
    captures: List[Capture] = field(default_factory=list)
    checks: List[Dict[str, Any]] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append({"check": name, "ok": bool(ok), "detail": detail})
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} {detail}")


class DriverError(RuntimeError):
    pass


class MMFDriver:
    """Operate the real desktop application through its widgets."""

    def __init__(self, *, mode: str = "offscreen", out_dir: str, pause: float = 0.0,
                 presets_dir: Optional[str] = None, window_size=(WINDOW_W, WINDOW_H)):
        self.mode = mode
        self.out_dir = out_dir
        self.pause = pause
        self.log = DriverLog()
        os.makedirs(out_dir, exist_ok=True)
        self._tmp = tempfile.mkdtemp(prefix="mmf_tutorial_")
        self.presets_dir = presets_dir or os.path.join(self._tmp, "presets")
        os.makedirs(self.presets_dir, exist_ok=True)
        _prepare_environment(mode, self.presets_dir, os.path.join(self._tmp, "settings"))

        from PySide6.QtWidgets import QApplication  # noqa: E402
        from PySide6.QtCore import QSettings  # noqa: E402

        self.app = QApplication.instance() or QApplication(["make-my-figure-tutorial"])
        # Belt and braces: QSettings into the temp dir on every platform.
        QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, os.path.join(self._tmp, "settings"))
        QSettings.setDefaultFormat(QSettings.IniFormat)

        from apps.desktop_app import main as M  # noqa: E402

        self.M = M
        self.win = M.MainWindow()
        self.win.resize(*window_size)
        self.win.show()
        self.pump(30)
        self._dialog_answers: List[Any] = []
        self.controls_width = 600
        self._layout_for_capture()

    def _layout_for_capture(self) -> None:
        """Give the control column a readable width (the app's own default splitter position is
        restored from the user's settings, which are isolated here, so the first-run default is
        narrow). Only geometry is changed, never content."""
        from PySide6.QtWidgets import QSplitter

        sp = self.win.findChild(QSplitter, "mainSplitter")
        if sp is not None:
            total = max(sp.width(), 1000)
            sp.setSizes([self.controls_width, total - self.controls_width])
        self.pump(10)

    # ------------------------------------------------------------- inspection
    def control_scroll(self):
        from PySide6.QtWidgets import QScrollArea, QWidget

        w = self.win.findChild(QWidget, "controlPanel")
        return w if isinstance(w, QScrollArea) else None

    def scroll_to(self, target: str) -> None:
        """Scroll the control column so that a group (mapping, options, stats, preset, ...) is
        visible, as a user would before the next action."""
        sa = self.control_scroll()
        w = self._target_widget(target)
        if sa is not None:
            sa.ensureWidgetVisible(w, 0, 0)
        self.pump(10)

    def recommendation_cards(self) -> List[Dict[str, str]]:
        """Read the 'Recommended figures' cards exactly as the live panel shows them."""
        from PySide6.QtWidgets import QLabel

        cards = []
        panel = self.win.recommend_panel
        for card in panel.findChildren(self.M.QWidget, options=self.M.Qt.FindChildrenRecursively):
            labels = [l.text() for l in card.findChildren(QLabel) if l.parent() is card]
            if labels and "match" in labels[0]:
                cards.append({"title": labels[0], "text": labels[1] if len(labels) > 1 else ""})
        if not cards:  # fall back to any label mentioning a match percentage
            seen = set()
            for l in panel.findChildren(QLabel):
                t = l.text()
                if "% match" in t and t not in seen:
                    seen.add(t); cards.append({"title": t, "text": ""})
        return cards

    def recommendation_header(self) -> str:
        from PySide6.QtWidgets import QLabel

        for l in self.win.recommend_panel.findChildren(QLabel):
            if "Detected data type" in l.text():
                return l.text()
        return ""

    def detected_types_text(self) -> str:
        return self.win.dtype_label.text()

    def result_metadata(self) -> Dict[str, Any]:
        r = self.win._current_result
        return dict(r.metadata) if r is not None else {}

    def current_spec(self) -> Dict[str, Any]:
        return dict(self.win._current_spec or {})

    # ------------------------------------------------------------------ basics
    def pump(self, n: int = 20, dt: float = 0.03) -> None:
        for _ in range(n):
            self.app.processEvents()
            time.sleep(dt)

    def wait(self, seconds: Optional[float] = None) -> None:
        """Pause so a viewer can follow (on-screen recording); no-op when pause is 0."""
        s = self.pause if seconds is None else seconds
        end = time.time() + s
        while time.time() < end:
            self.app.processEvents()
            time.sleep(0.02)

    def step(self, text: str) -> None:
        self.log.steps.append({"step": text})
        print(f"- {text}")

    # ---------------------------------------------------------------- captures
    def capture(self, name: str, target: str = "window", note: str = "") -> str:
        """Grab a real widget to PNG. target: window | controls | figure | data | messages |
        mapping | options | stats | preset | export | welcome | builder | <attribute name>."""
        self.pump(12)
        w = self._target_widget(target)
        path = os.path.join(self.out_dir, name if name.endswith(".png") else name + ".png")
        ok = w.grab().save(path)
        if not ok:
            raise DriverError(f"could not save {path}")
        self.log.captures.append(Capture(name, path, target, f"{w.width()}x{w.height()}", note))
        print(f"  captured {os.path.basename(path)} ({target}, {w.width()}x{w.height()})")
        return path

    def _target_widget(self, target: str):
        win = self.win
        table = {
            "window": win, "welcome": win.stack.widget(0), "workbench": win.stack.widget(1),
            "mapping": win.mapping_box, "options": win.options_box, "stats": win.stats_panel,
            "figure": win.fig_container, "data": win.table_widget, "messages": win.warn_label,
            "recommendations": win.recommend_panel,
        }
        if target in table:
            return table[target]
        if target == "controls":
            return win.findChild(self.M.QWidget, "controlPanel") or win
        if target == "controls_full":
            sa = self.control_scroll()
            return sa.widget() if sa is not None else win
        if target == "style":
            return win.findChildren(self.M.QGroupBox)[0] if False else self._group_box("5. Publication style")
        if target == "export":
            return self._group_box("5. Export")
        if target == "multipanel":
            return self._group_box("6. Multi-panel figure")
        if target == "labels":
            return self._group_box("4. Labels & style") or self._group_box("4. Labels & size")
        if target == "plottype":
            return self._group_box("1. Plot type & style")
        if target == "preset":
            return win.preset_combo.parentWidget()
        if hasattr(win, target):
            return getattr(win, target)
        raise DriverError(f"unknown capture target {target!r}")

    def _group_box(self, title: str):
        from PySide6.QtWidgets import QGroupBox

        for gb in self.win.findChildren(QGroupBox):
            if gb.title() == title:
                return gb
        raise DriverError(f"no group box titled {title!r}; have {[g.title() for g in self.win.findChildren(QGroupBox)]}")

    def group_titles(self) -> List[str]:
        from PySide6.QtWidgets import QGroupBox

        return [g.title() for g in self.win.findChildren(QGroupBox)]

    # ------------------------------------------------------------- data steps
    def open_file(self, path: str) -> None:
        """Equivalent of File > Open data file... (or drag and drop) with a chosen path."""
        path = os.path.abspath(path)
        if not os.path.exists(path):
            raise DriverError(f"dataset missing: {path}")
        self.step(f"Open data file: {os.path.basename(path)}")
        self.win.load_path(path)
        self.pump(25)
        self.log.check("data loaded", self.win.data is not None, os.path.basename(path))
        self.wait()

    def open_example(self, plot_type: str) -> None:
        self.step(f"File > Open example > {self.M.display_name(plot_type)}")
        self.win.load_example(plot_type)
        self.pump(25)
        self.wait()

    def columns(self) -> List[str]:
        return list(self.win.data.info.columns) if self.win.data is not None else []

    # ------------------------------------------------------------ plot steps
    def select_plot(self, plot_type: str) -> None:
        """Choose an entry of the '1. Plot type & style' combo by plot id or display name."""
        combo = self.win.plot_combo
        idx = combo.findData(plot_type)
        if idx < 0:
            idx = combo.findText(plot_type)
        if idx < 0:
            raise DriverError(f"plot type {plot_type!r} is not in the plot-type combo")
        self.step(f"Plot type: {combo.itemText(idx)}")
        combo.setCurrentIndex(idx)
        self.pump(25)
        self.wait()

    def mapping_widgets(self) -> Dict[str, Any]:
        return dict(getattr(self.win, "_mapping_widgets", {}) or {})

    def current_mapping(self) -> Dict[str, Any]:
        return self.win._collect_mapping()

    def set_mapping(self, field: str, column: Optional[str]) -> None:
        """Set one row of '2. Map columns' (the row label is the role name shown in the app)."""
        widgets = self.mapping_widgets()
        if field not in widgets:
            raise DriverError(f"role {field!r} is not offered for this plot type; rows are {list(widgets)}")
        combo = widgets[field]
        text = "(none)" if column is None else str(column)
        idx = combo.findText(text)
        if idx < 0:
            raise DriverError(f"column {text!r} is not a choice for role {field!r}: {[combo.itemText(i) for i in range(combo.count())]}")
        self.step(f"Map columns: {field} <- {text}")
        combo.setCurrentIndex(idx)
        self.pump(20)
        self.wait()

    def set_value_columns(self, columns: List[str]) -> None:
        """Select the VALUE columns list shown for matrix plots (heatmap, PCA, clustering)."""
        lw = getattr(self.win, "_value_cols_widget", None)
        if lw is None:
            raise DriverError("this plot type has no 'Value columns' list")
        self.step(f"Value columns: {', '.join(columns)}")
        want = set(columns)
        for i in range(lw.count()):
            it = lw.item(i)
            it.setSelected(it.text() in want)
        self.pump(10)
        self.win.render_preview()
        self.pump(25)
        self.wait()

    def set_multi_columns(self, field: str, columns: List[str]) -> None:
        widgets = getattr(self.win, "_multi_col_widgets", {}) or {}
        if field not in widgets:
            raise DriverError(f"no multi-column role {field!r}; have {list(widgets)}")
        lw = widgets[field]
        want = set(columns)
        for i in range(lw.count()):
            it = lw.item(i)
            it.setSelected(it.text() in want)
        self.step(f"{field}: {', '.join(columns)}")
        self.pump(10)
        self.win.render_preview()
        self.pump(25)
        self.wait()

    def option_widgets(self) -> Dict[str, Any]:
        return dict(getattr(self.win, "_option_widgets", {}) or {})

    def set_option(self, key: str, value: Any) -> None:
        """Set a control in '3. Options' by option key (as listed in ui_hints) or by label."""
        from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit

        widgets = self.option_widgets()
        w = widgets.get(key)
        if w is None:
            # allow the human-readable label
            for opt in self.win.controller.options(self.win.plot_combo.currentData()):
                if opt.label == key and opt.key in widgets:
                    w = widgets[opt.key]
                    key = opt.key
                    break
        if w is None:
            raise DriverError(f"option {key!r} not shown for this plot type; have {list(widgets)}")
        self.step(f"Options: {key} = {value}")
        if isinstance(w, QCheckBox):
            w.setChecked(bool(value))
        elif isinstance(w, QComboBox):
            idx = w.findText(str(value))
            if idx < 0:
                raise DriverError(f"{value!r} is not a choice for {key!r}: {[w.itemText(i) for i in range(w.count())]}")
            w.setCurrentIndex(idx)
        elif isinstance(w, (QSpinBox, QDoubleSpinBox)):
            w.setValue(value)
        elif isinstance(w, QLineEdit):
            w.setText(str(value))
        else:
            raise DriverError(f"unsupported option widget {type(w).__name__} for {key!r}")
        self.pump(20)
        self.wait()

    def set_labels(self, title: Optional[str] = None, xlabel: Optional[str] = None,
                   ylabel: Optional[str] = None, width: Optional[str] = None,
                   dpi: Optional[int] = None) -> None:
        """'4. Labels & size': title, axis labels, figure width preset and DPI."""
        parts = []
        if title is not None:
            self.win.title_edit.setText(title); parts.append(f"title={title!r}")
        if xlabel is not None:
            self.win.xlabel_edit.setText(xlabel); parts.append(f"x={xlabel!r}")
        if ylabel is not None:
            self.win.ylabel_edit.setText(ylabel); parts.append(f"y={ylabel!r}")
        if width is not None:
            idx = self.win.width_combo.findText(width)
            if idx < 0:
                raise DriverError(f"width {width!r} not in {[self.win.width_combo.itemText(i) for i in range(self.win.width_combo.count())]}")
            self.win.width_combo.setCurrentIndex(idx); parts.append(f"width={width}")
        if dpi is not None:
            self.win.dpi_spin.setValue(int(dpi)); parts.append(f"dpi={dpi}")
        self.step("Labels & size: " + ", ".join(parts))
        self.pump(10)
        self.wait()

    def update_preview(self) -> bool:
        self.step("Update preview")
        self.win.render_preview()
        self.pump(30)
        ok = self.win._current_result is not None
        self.log.check("figure rendered", ok, self.win.warn_label.text()[:160] if not ok else "")
        self.wait()
        return ok

    def rendered(self) -> bool:
        return self.win._current_result is not None

    def message_text(self) -> str:
        return self.win.warn_label.text()

    # ------------------------------------------------------------- statistics
    def enable_statistics(self, *, test: Optional[str] = None, comparison: Optional[str] = None,
                          group_column: Optional[str] = None, subgroup_column: Optional[str] = None,
                          subject_column: Optional[str] = None, reference_group: Optional[str] = None,
                          correction: Optional[str] = None, annotation: Optional[str] = None,
                          placement: Optional[str] = None, posthoc: Optional[bool] = None,
                          hide_ns: Optional[bool] = None) -> None:
        """Tick 'Enable statistics' and set the panel's combos (values are the ids used by the
        statistics registry, e.g. test='welch_t', comparison='all_pairs', correction='holm')."""
        sp = self.win.stats_panel
        # The panel is a checkable group box ("6. Statistics") that is OFF by default, and it
        # holds a second switch, the "Enable statistics" checkbox. Both must be on.
        if sp.isCheckable():
            sp.setChecked(True)
        sp.enable_cb.setChecked(True)
        self.pump(5)

        def _set(combo, value, what):
            if value is None:
                return
            for i in range(combo.count()):
                if combo.itemData(i) == value or combo.itemText(i) == value:
                    combo.setCurrentIndex(i)
                    return
            raise DriverError(f"{what} {value!r} is not offered: "
                              f"{[(combo.itemData(i), combo.itemText(i)) for i in range(combo.count())]}")

        _set(sp.test_combo, test, "test")
        _set(sp.mode_combo, comparison, "comparison")
        _set(sp.group_combo, group_column, "group column")
        _set(sp.subgroup_combo, subgroup_column, "subgroup column")
        _set(sp.subject_combo, subject_column, "subject column")
        _set(sp.reference_combo, reference_group, "control group")
        _set(sp.correction_combo, correction, "correction")
        _set(sp.annotation_combo, annotation, "annotation")
        _set(sp.placement_combo, placement, "placement")
        if posthoc is not None:
            sp.posthoc_cb.setChecked(bool(posthoc))
        if hide_ns is not None:
            sp.hide_ns_cb.setChecked(bool(hide_ns))
        self.step("Statistics: " + ", ".join(f"{k}={v}" for k, v in
                  dict(test=test, comparison=comparison, group=group_column, correction=correction,
                       annotation=annotation).items() if v is not None))
        self.pump(10)
        self.wait()

    def run_statistics(self) -> bool:
        self.step("Run statistics")
        self.win.stats_panel.run_btn.click()
        self.pump(60)
        rep = getattr(self.win.stats_panel, "_report", None)
        ok = rep is not None and self.win.stats_panel.table.rowCount() > 0
        self.log.check("statistics ran", ok,
                       f"{self.win.stats_panel.table.rowCount()} comparison row(s)" if ok else self.win.warn_label.text()[:160])
        self.wait()
        return ok

    def stats_panel_text(self) -> str:
        """The method sentence shown under the statistics table."""
        return self.win.stats_panel.method_text.toPlainText()

    def stats_table_rows(self) -> List[Dict[str, str]]:
        t = self.win.stats_panel.table
        heads = [t.horizontalHeaderItem(j).text() if t.horizontalHeaderItem(j) else str(j) for j in range(t.columnCount())]
        rows = []
        for i in range(t.rowCount()):
            rows.append({heads[j]: (t.item(i, j).text() if t.item(i, j) else "") for j in range(t.columnCount())})
        return rows

    def export_stats_table(self, dest: str) -> str:
        dest = os.path.abspath(dest)
        self.step(f"Statistics: Export stats table -> {os.path.basename(dest)}")
        mb = self._patch_messagebox()
        try:
            with self._file_dialog_returning(dest):
                self.win.stats_panel.export_table_btn.click()
                self.pump(20)
        finally:
            mb.restore()
        self.log.check("stats table exported", os.path.exists(dest), dest)
        return dest

    def export_method_report(self, dest: str) -> str:
        dest = os.path.abspath(dest)
        self.step(f"Statistics: Export method report -> {os.path.basename(dest)}")
        mb = self._patch_messagebox()
        try:
            with self._file_dialog_returning(dest):
                self.win.stats_panel.export_method_btn.click()
                self.pump(20)
        finally:
            mb.restore()
        self.log.check("method report exported", os.path.exists(dest), dest)
        return dest

    # ---------------------------------------------------------------- presets
    def save_preset(self, name: str, mode: str = "style", capture_dialog: Optional[str] = None) -> str:
        """Figure preset > Save current...: fill the real 'Save Figure Preset' dialog."""
        from PySide6.QtWidgets import QDialog, QLineEdit, QRadioButton

        drv = self
        orig = QDialog.exec

        def _exec(dlg, *a, **k):
            if dlg.windowTitle() != "Save Figure Preset":
                return orig(dlg, *a, **k)
            edit = dlg.findChild(QLineEdit)
            edit.setText(name)
            rbs = dlg.findChildren(QRadioButton)
            (rbs[0] if mode == "style" else rbs[1]).setChecked(True)
            dlg.show(); drv.pump(15)
            if capture_dialog:
                drv._grab_widget(dlg, capture_dialog, "Save Figure Preset dialog")
            drv.wait()
            dlg.hide()
            return QDialog.Accepted

        QDialog.exec = _exec
        try:
            self.step(f"Figure preset: Save current as {name!r} ({mode})")
            self.win.action_save_preset()
            self.pump(20)
        finally:
            QDialog.exec = orig
        path = self.win._selected_preset_path()
        self.log.check("preset saved", bool(path) and os.path.exists(path), os.path.basename(path or ""))
        self.wait()
        return path

    def select_preset(self, name: str) -> None:
        combo = self.win.preset_combo
        idx = combo.findText(name)
        if idx < 0:
            for i in range(combo.count()):
                if name in combo.itemText(i):
                    idx = i
                    break
        if idx < 0:
            raise DriverError(f"preset {name!r} not listed: {[combo.itemText(i) for i in range(combo.count())]}")
        combo.setCurrentIndex(idx)
        self.pump(5)

    def apply_preset(self, name: str) -> str:
        from PySide6.QtWidgets import QMessageBox

        self.select_preset(name)
        self.step(f"Figure preset: Apply {name!r}")
        info = self._patch_messagebox()
        try:
            self.win.action_apply_preset()
            self.pump(30)
        finally:
            info.restore()
        status = self.win.preset_status.text()
        self.log.check("preset applied", status.startswith("Applied preset"), status[:120])
        self.wait()
        return status

    # --------------------------------------------------------------- exports
    def export(self, fmt: str, dest: str) -> str:
        """The PNG / SVG / PDF / ... buttons under '5. Export' with a chosen destination."""
        dest = os.path.abspath(dest)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        self.step(f"Export {fmt.upper()} -> {os.path.basename(dest)}")
        with self._file_dialog_returning(dest):
            self.win.export_single(fmt)
            self.pump(30)
        expected = dest if fmt == "json" else os.path.splitext(dest)[0] + f".{fmt}"
        self.log.check(f"export {fmt}", os.path.exists(expected), expected)
        self.wait()
        return expected

    def export_zip(self, dest: str) -> str:
        dest = os.path.abspath(dest)
        self.step(f"Export all as ZIP -> {os.path.basename(dest)}")
        with self._file_dialog_returning(dest):
            self.win.export_zip()
            self.pump(40)
        self.log.check("export zip", os.path.exists(dest), dest)
        self.wait()
        return dest

    def save_package(self, dest: str, capture_question: Optional[str] = None) -> str:
        """5. Export > Save Figure Package (.mmfpackage): answers the real confirmation with Save."""
        dest = os.path.abspath(dest)
        self.step(f"Save Figure Package -> {os.path.basename(dest)}")
        mb = self._patch_messagebox(capture_name=capture_question)
        try:
            with self._file_dialog_returning(dest):
                self.win.action_save_package()
                self.pump(50)
        finally:
            mb.restore()
        self.log.check("figure package saved", os.path.exists(dest), dest)
        self.wait()
        return dest

    def open_package(self, path: str) -> None:
        path = os.path.abspath(path)
        self.step(f"File > Open Figure Package... -> {os.path.basename(path)}")
        mb = self._patch_messagebox()
        try:
            self.win.open_package_path(path)
            self.pump(50)
        finally:
            mb.restore()
        self.log.check("package opened and rendered", self.win._current_result is not None)
        self.wait()

    def open_plotspec(self, path: str, data_path: Optional[str] = None) -> None:
        """File > Open PlotSpec...: the app reads the specification and then asks for the data
        file it needs (a PlotSpec carries no data); `data_path` answers that second dialog."""
        path = os.path.abspath(path)
        answers = [path] + ([os.path.abspath(data_path)] if data_path else [])
        self.step(f"File > Open PlotSpec... -> {os.path.basename(path)}" + (f" + data {os.path.basename(data_path)}" if data_path else ""))
        mb = self._patch_messagebox()
        try:
            with self._file_dialog_returning(answers, open_dialog=True):
                self.win.action_open_plotspec()
                self.pump(50)
        finally:
            mb.restore()
        self.log.check("plotspec opened and rendered", self.win._current_result is not None)
        self.wait()

    def home(self, capture_question: Optional[str] = None) -> None:
        """Home / Upload New Data. When a plot exists the app asks 'Return to upload page?' with
        the buttons 'Save PlotSpec first…', 'Clear and continue' and 'Cancel'; the driver presses
        'Clear and continue' (optionally grabbing the real box first)."""
        self.step("Home / Upload New Data")
        guard = self._patch_dialog_exec(click_text="Clear and continue", capture_name=capture_question)
        try:
            self.win.action_home_upload()
            self.pump(20)
        finally:
            guard.restore()
        self.log.check("returned to start screen", self.win.stack.currentIndex() == 0)
        self.wait()

    def _patch_dialog_exec(self, click_text: Optional[str] = None, capture_name: Optional[str] = None):
        """Intercept instance-level QMessageBox.exec (dialogs built with addButton and exec(),
        which would block offscreen): show, optionally grab, press the named button (or the
        default / first accept-role button) and return."""
        from PySide6.QtWidgets import QMessageBox

        drv = self
        orig_exec = QMessageBox.exec

        def _exec(box, *a, **k):
            box.show(); drv.pump(15)
            drv.log.steps.append({"messagebox": "instance", "title": box.windowTitle(), "text": box.text()[:300],
                                  "buttons": [b.text() for b in box.buttons()]})
            if capture_name:
                drv._grab_widget(box, capture_name, f"{box.windowTitle()} (question)")
            target = None
            for b in box.buttons():
                if click_text and b.text().replace("…", "...") == click_text.replace("…", "..."):
                    target = b
                    break
            if target is None:
                target = box.defaultButton()
            if target is None:
                for b in box.buttons():
                    if box.buttonRole(b) in (QMessageBox.AcceptRole, QMessageBox.YesRole):
                        target = b
                        break
            if target is None and box.buttons():
                target = box.buttons()[0]
            if target is not None:
                target.click()
            drv.pump(5)
            box.hide()
            return 0

        QMessageBox.exec = _exec

        class _R:
            def restore(self_inner):
                QMessageBox.exec = orig_exec

        return _R()

    # ---------------------------------------------------------- multi-panel
    def save_panel(self) -> int:
        self.step("6. Multi-panel figure: Save current plot as panel")
        self.win.action_save_panel()
        self.pump(10)
        n = len(self.win._saved_panels)
        self.log.check("panel saved", n > 0, f"{n} panel(s)")
        self.wait()
        return n

    def figure_builder(self, actions: Optional[Callable[[Any], None]] = None,
                       capture_name: Optional[str] = None, save_figure: Optional[str] = None,
                       save_package: Optional[str] = None) -> Dict[str, Any]:
        """Open the real Multi-panel Figure Builder dialog, optionally run `actions(dialog)`,
        grab it, save the composite figure and/or a package, then close it."""
        from PySide6.QtWidgets import QDialog

        from apps.desktop_app.stats_panel import FigureBuilderDialog

        self.step("Open Figure Builder...")
        result: Dict[str, Any] = {}
        dlg = FigureBuilderDialog(self.win.controller, self.win._saved_panels, self.win)
        dlg.resize(1500, 900)
        dlg.show()
        self.pump(60)
        if actions:
            actions(dlg)
            self.pump(40)
        if capture_name:
            self._grab_widget(dlg, capture_name, "Multi-panel Figure Builder")
        if save_figure:
            self.step(f"Figure Builder: Save figure... -> {os.path.basename(save_figure)}")
            mb = self._patch_messagebox()
            try:
                with self._file_dialog_returning(os.path.abspath(save_figure)):
                    self._click_button(dlg, "Save figure...")
                    self.pump(60)
            finally:
                mb.restore()
            base = os.path.splitext(os.path.abspath(save_figure))[0]
            produced = [p for p in (base + ext for ext in (".png", ".pdf", ".svg", ".tiff")) if os.path.exists(p)]
            if not produced and os.path.exists(os.path.abspath(save_figure)):
                produced = [os.path.abspath(save_figure)]
            self.log.check("composite figure saved", bool(produced), ", ".join(os.path.basename(p) for p in produced))
            result["figure_files"] = produced
        if save_package:
            self.step(f"Figure Builder: Save Figure Package... -> {os.path.basename(save_package)}")
            mb = self._patch_messagebox()
            try:
                with self._file_dialog_returning(os.path.abspath(save_package)):
                    self._click_button(dlg, "Save Figure Package…")
                    self.pump(60)
            finally:
                mb.restore()
            self.log.check("composite package saved", os.path.exists(save_package), save_package)
            result["package"] = save_package
        self.wait()
        dlg.hide()
        dlg.deleteLater()
        self.pump(10)
        return result


    # ------------------------------------------------- experimental presets / preview & apply
    def show_experimental_presets(self, on: bool = True) -> List[str]:
        """Tick 'Show experimental presets' in the Figure preset panel; returns the list entries."""
        chk = getattr(self.win, "chk_experimental_presets", None)
        if chk is None:
            raise DriverError("this build has no 'Show experimental presets' checkbox")
        self.step(f"Figure preset: Show experimental presets = {on}")
        chk.setChecked(bool(on))
        self.pump(15)
        combo = self.win.preset_combo
        entries = [combo.itemText(i) for i in range(combo.count())]
        self.log.check("experimental presets listed", any("experimental" in e.lower() or "(N)" in e or "(S)" in e or "(C)" in e or "observations" in e for e in entries) if on else True,
                       f"{len(entries)} entries")
        self.wait()
        return entries

    def preview_preset(self, name: str, *, apply: bool = True, capture_name: Optional[str] = None) -> Dict[str, Any]:
        """Figure preset > Preview & apply...: open the REAL preview dialog for the selected preset,
        grab it, read the change list and the safety line, then press Apply (or Cancel)."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QPlainTextEdit

        self.select_preset(name)
        self.step(f"Figure preset: Preview & apply... for {name!r} -> {'Apply' if apply else 'Cancel'}")
        drv = self
        info: Dict[str, Any] = {}
        orig = QDialog.exec

        def _exec(dlg, *a, **k):
            if not dlg.windowTitle().startswith("Preview preset"):
                return orig(dlg, *a, **k)
            dlg.show(); drv.pump(25)
            info["title"] = dlg.windowTitle()
            texts = dlg.findChildren(QPlainTextEdit)
            info["changes"] = texts[0].toPlainText() if texts else ""
            labels = [l.text() for l in dlg.findChildren(QLabel)]
            info["safety"] = next((t for t in labels if t.startswith(("Checked:", "Refused:"))), "")
            info["notice"] = next((t for t in labels if "synthetic" in t.lower() or "your data" in t.lower()), "")
            bb = dlg.findChildren(QDialogButtonBox)
            info["buttons"] = [b.text() for b in bb[0].buttons()] if bb else []
            if capture_name:
                drv._grab_widget(dlg, capture_name, info["title"])
            drv.wait()
            dlg.hide()
            return QDialog.Accepted if apply else QDialog.Rejected

        QDialog.exec = _exec
        mb = self._patch_messagebox()
        try:
            self.win.action_preview_preset()
            self.pump(40)
        finally:
            QDialog.exec = orig
            mb.restore()
        info["status"] = self.win.preset_status.text()
        self.log.check("preset preview opened", bool(info.get("title")), info.get("title", ""))
        if apply:
            self.log.check("preset applied from preview", info["status"].startswith("Applied"), info["status"][:120])
        self.wait()
        return info

    # ------------------------------------------------------------- utilities
    def _grab_widget(self, widget, name: str, note: str = "") -> str:
        self.pump(10)
        path = os.path.join(self.out_dir, name if name.endswith(".png") else name + ".png")
        if not widget.grab().save(path):
            raise DriverError(f"could not save {path}")
        self.log.captures.append(Capture(name, path, type(widget).__name__, f"{widget.width()}x{widget.height()}", note))
        print(f"  captured {os.path.basename(path)} ({note}, {widget.width()}x{widget.height()})")
        return path

    def _click_button(self, parent, text: str) -> None:
        from PySide6.QtWidgets import QPushButton

        for b in parent.findChildren(QPushButton):
            if b.text() == text:
                b.click()
                return
        raise DriverError(f"button {text!r} not found in {type(parent).__name__}; have "
                          f"{[b.text() for b in parent.findChildren(QPushButton)]}")

    def _file_dialog_returning(self, path, open_dialog: bool = False):
        """Context manager: QFileDialog.getSaveFileName / getOpenFileName return `path`; when
        `path` is a list, successive dialogs receive successive entries (e.g. Open PlotSpec asks
        for the specification first and then for the data file)."""
        from PySide6.QtWidgets import QFileDialog

        drv = self
        queue = list(path) if isinstance(path, (list, tuple)) else [path]

        def _next(*a, **k):
            p = queue.pop(0) if len(queue) > 1 else queue[0]
            drv.log.steps.append({"dialog": "file", "title": a[1] if len(a) > 1 else "", "path": p})
            return (p, "")

        class _Ctx:
            def __enter__(self_inner):
                self_inner.orig_save = QFileDialog.getSaveFileName
                self_inner.orig_open = QFileDialog.getOpenFileName
                QFileDialog.getSaveFileName = staticmethod(_next)
                QFileDialog.getOpenFileName = staticmethod(_next)
                return self_inner

            def __exit__(self_inner, *exc):
                QFileDialog.getSaveFileName = self_inner.orig_save
                QFileDialog.getOpenFileName = self_inner.orig_open
                return False

        return _Ctx()

    def _patch_messagebox(self, capture_name: Optional[str] = None):
        """Answer QMessageBox.question with the default button (Save / Yes) and let information /
        warning boxes return immediately, recording their text so a tutorial can quote it."""
        from PySide6.QtWidgets import QMessageBox

        drv = self
        seen: List[Dict[str, str]] = []
        orig = {n: getattr(QMessageBox, n) for n in ("question", "information", "warning", "critical")}

        def _mk(kind):
            def _fn(parent, title, text, *a, **k):
                seen.append({"kind": kind, "title": title, "text": text})
                drv.log.steps.append({"messagebox": kind, "title": title, "text": text[:400]})
                if capture_name and kind == "question":
                    box = QMessageBox(parent)
                    box.setWindowTitle(title); box.setText(text)
                    box.setStandardButtons(a[0] if a else QMessageBox.Ok)
                    box.show(); drv.pump(15)
                    drv._grab_widget(box, capture_name, f"{title} (confirmation)")
                    box.hide(); box.deleteLater()
                if kind == "question":
                    default = k.get("defaultButton") or (a[1] if len(a) > 1 else None)
                    if default not in (None, QMessageBox.NoButton):
                        return default
                    for cand in (QMessageBox.Save, QMessageBox.Yes, QMessageBox.Ok):
                        if a and (a[0] & cand):
                            return cand
                    return QMessageBox.Yes
                return QMessageBox.Ok
            return _fn

        for n in orig:
            setattr(QMessageBox, n, staticmethod(_mk(n)))

        class _Restore:
            messages = seen

            def restore(self_inner):
                for n, f in orig.items():
                    setattr(QMessageBox, n, f)

        return _Restore()

    def write_log(self, name: str = "driver_log.json") -> str:
        path = os.path.join(self.out_dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"captures": [c.__dict__ for c in self.log.captures], "checks": self.log.checks,
                       "steps": self.log.steps}, fh, indent=2)
        return path

    def close(self) -> None:
        try:
            self.win.close()
        except Exception:  # noqa: BLE001
            pass
        self.pump(5)
        shutil.rmtree(self._tmp, ignore_errors=True)
