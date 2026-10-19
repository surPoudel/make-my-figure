"""Regression: the Qt binding must not release references it does not own.

v1.3.0 was built with PySide6/shiboken6 6.12.0, which releases one reference
too many per signal delivered to a Python slot (``True``: -1.000 per emit) and
per ``QTimer.singleShot`` callable (``None``: -1.005 per call), measured over
200 calls on Linux / Python 3.11. 6.11.2, which v1.2.x shipped and the lock
file pins, measures 0.000 on every probe. Under Python 3.11 the count reaches
zero and the interpreter frees a live object; on macOS that surfaced as
EXC_BAD_ACCESS in shiboken's mainThreadDeletionHandler.
"""
import re
from pathlib import Path

import pytest

try:
    from PySide6.QtWidgets import QApplication  # noqa: F401  (loads native Qt)

    from apps.desktop_app.binding_check import DRIFT_LIMIT, binding_refcount_drift
except Exception as exc:  # noqa: BLE001
    pytest.skip(f"PySide6/Qt unavailable: {exc}", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[1]


def test_signal_emit_and_single_shot_do_not_drift_reference_counts():
    drift = binding_refcount_drift(calls=200)
    assert set(drift) == {
        f"{op}:{obj}" for op in ("emit", "singleShot") for obj in ("True", "None", "argument")
    }
    bad = {k: v for k, v in drift.items() if abs(v) >= DRIFT_LIMIT}
    assert not bad, f"Qt binding miscounts references, per-call drift: {bad}"


def test_desktop_extra_excludes_the_pyside6_release_that_crashed_v130():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    spec = re.search(r'desktop\s*=\s*\["PySide6([^"]*)"\]', text)
    assert spec, "desktop extra must declare PySide6"
    assert "!=6.12.0" in spec.group(1)


def test_packaged_selftest_checks_the_bundled_binding():
    # CI runs --selftest on every built installer; this is the gate that fails a
    # build bundling a defective binding, whatever version pip resolved.
    src = (ROOT / "apps" / "desktop_app" / "main.py").read_text(encoding="utf-8")
    selftest = src[src.index("def _selftest("):src.index("def _mk_loaded(")]
    assert "assert_binding_refcounts_sound()" in selftest


def test_the_probe_leaves_an_application_that_can_create_widgets():
    # The probe used to create a bare QCoreApplication, so the next QWidget in the
    # process aborted the interpreter (a pytest worker died in MainWindow()).
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtWidgets import QApplication, QWidget

    binding_refcount_drift(calls=5)
    assert isinstance(QCoreApplication.instance(), QApplication)
    w = QWidget()
    w.deleteLater()


def test_a_one_time_release_during_the_probe_is_not_a_per_call_drift():
    """v1.3.2's Linux build under an X server: 165 references to None released once
    during the measurement read as -0.825 per call (165 / 200) for the sound 6.11.2."""
    from PySide6.QtCore import QTimer

    held = [[None] for _ in range(165)]

    def release():
        held.clear()

    # lands inside the singleShot measurement, as the X server's pending work did
    QTimer.singleShot(0, lambda: QTimer.singleShot(0, release))
    drift = binding_refcount_drift(calls=200)
    assert abs(drift["singleShot:None"]) < DRIFT_LIMIT, drift


def test_a_genuine_per_call_leak_is_still_caught(monkeypatch):
    """The 6.12.0 defect pattern - one reference to None lost per singleShot - must fail."""
    import ctypes
    import sys

    from PySide6.QtCore import QTimer

    from apps.desktop_app import binding_check

    real = QTimer.singleShot
    lost = []

    def leaky(msec, fn):
        def wrapped():
            ctypes.pythonapi.Py_DecRef(ctypes.py_object(None))    # what the defective binding did
            lost.append(1)
            fn()
        real(msec, wrapped)

    def give_back():
        while lost:
            lost.pop()
            ctypes.pythonapi.Py_IncRef(ctypes.py_object(None))

    before = sys.getrefcount(None)
    monkeypatch.setattr(QTimer, "singleShot", staticmethod(leaky))
    try:
        drift = binding_check.binding_refcount_drift(calls=200, rounds=3)
        with pytest.raises(RuntimeError, match="miscounts Python references"):
            binding_check.assert_binding_refcounts_sound(calls=100, rounds=3)
    finally:
        monkeypatch.undo()
        give_back()
    assert drift["singleShot:None"] == pytest.approx(-1.0, abs=0.05), drift
    assert abs(sys.getrefcount(None) - before) < 50
