"""Detect a Qt binding that miscounts Python references.

PySide6/shiboken6 6.12.0 releases one reference too many on two paths the app
uses constantly: delivering a signal to a Python slot, and firing a
``QTimer.singleShot`` callable. Measured on Linux, Python 3.11, 2 000 calls
each: ``True`` lost 1.005 references per ``emit`` and ``None`` lost 1.002 per
``singleShot``, against 0.000 on 6.11.2. Under Python 3.11 those objects are
not immortal, so the count reaches zero and the interpreter frees an object
that is still in use — a fatal error or a segfault inside the next Python
callback. v1.3.0 shipped 6.12.0 (v1.2.x shipped 6.11.2), and macOS users saw
``EXC_BAD_ACCESS`` in ``mainThreadDeletionHandler`` under a SignalManager
callback.

``binding_refcount_drift`` repeats each operation and reports the change in
reference count per call. A correct binding drifts by 0; the defective one by
about -1. ``assert_binding_refcounts_sound`` turns that into a check the
packaged ``--selftest`` runs, so a build that bundles a defective binding
fails CI instead of reaching users.
"""
from __future__ import annotations

import sys

# |drift| per call at or above this is a reference-counting defect. A sound
# binding measures 0.000; the 6.12.0 defect measures about 1.0.
DRIFT_LIMIT = 0.5


class _Arg:
    """A fresh, non-immortal object to pass through a signal."""


def binding_refcount_drift(calls: int = 200) -> dict[str, float]:
    """Return the per-call reference-count drift for each probed operation."""
    from PySide6.QtCore import QCoreApplication, QObject, QTimer, Signal

    app = QCoreApplication.instance() or QCoreApplication(sys.argv[:1])

    class _Emitter(QObject):
        sig = Signal(object)

    emitter = _Emitter()
    received = []
    emitter.sig.connect(lambda value: received.append(value is not None))

    def counts(arg):
        return {
            "True": sys.getrefcount(True),
            "None": sys.getrefcount(None),
            "argument": sys.getrefcount(arg),
        }

    arg = _Arg()
    before = counts(arg)
    for _ in range(calls):
        emitter.sig.emit(arg)
    received.clear()
    app.processEvents()
    after = counts(arg)
    drift = {f"emit:{k}": (after[k] - before[k]) / calls for k in before}

    fired = []
    before = counts(arg)
    for _ in range(calls):
        QTimer.singleShot(0, lambda: fired.append(1))
    while len(fired) < calls:
        app.processEvents()
    fired.clear()
    after = counts(arg)
    drift.update({f"singleShot:{k}": (after[k] - before[k]) / calls for k in before})
    return drift


def assert_binding_refcounts_sound(calls: int = 200) -> dict[str, float]:
    """Raise ``RuntimeError`` naming the binding if any operation drifts."""
    drift = binding_refcount_drift(calls)
    bad = {k: v for k, v in drift.items() if abs(v) >= DRIFT_LIMIT}
    if bad:
        import PySide6
        import shiboken6

        raise RuntimeError(
            f"PySide6 {PySide6.__version__} / shiboken6 {shiboken6.__version__} "
            f"miscounts Python references (per-call drift {bad}); this binding "
            "crashes the app. Build with a different PySide6 version."
        )
    return drift


if __name__ == "__main__":  # python -m apps.desktop_app.binding_check
    import PySide6

    print(PySide6.__version__, binding_refcount_drift())
