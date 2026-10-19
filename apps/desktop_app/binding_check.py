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


def binding_refcount_drift(calls: int = 200, rounds: int = 5) -> dict[str, float]:
    """Return the per-call reference-count drift for each probed operation.

    Each operation is measured in ``rounds`` rounds of ``calls`` calls and the
    **median** per-call drift is reported. A defective binding loses a reference
    on every call, so every round reads about -1. Anything else the process does
    meanwhile (a widget freed by a pending event, a figure redrawn) changes the
    counts once, in one round only. With a single round that one-time change was
    divided by the call count and read as a per-call drift: the v1.3.2 Linux
    build, run under an X server, released 165 references to ``None`` once during
    the measurement and reported -0.825 (165 / 200) for PySide6 6.11.2, the
    binding that measures 0.000 everywhere else.
    """
    import gc
    import statistics

    from PySide6.QtCore import QCoreApplication, QObject, QTimer, Signal

    # Create the full QApplication when none exists. A bare QCoreApplication made
    # here outlives the probe, and every QWidget created later in the process
    # then aborts ("Cannot create a QWidget without QApplication") - it took down
    # a test worker that ran this probe before a window test.
    app = QCoreApplication.instance()
    if app is None:
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication(sys.argv[:1])
        except Exception:  # noqa: BLE001 - no widget support: the core probe still works
            app = QCoreApplication(sys.argv[:1])

    def settle():
        # Let what is already queued (deferred deletions, pending redraws) run, and
        # collect garbage, before a count is taken.
        for _ in range(3):
            app.processEvents()
            gc.collect()

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

    def emit_round(arg):
        before = counts(arg)
        for _ in range(calls):
            emitter.sig.emit(arg)
        received.clear()
        app.processEvents()
        after = counts(arg)
        return {k: (after[k] - before[k]) / calls for k in before}

    def single_shot_round(arg):
        fired = []
        before = counts(arg)
        for _ in range(calls):
            QTimer.singleShot(0, lambda: fired.append(1))
        while len(fired) < calls:
            app.processEvents()
        fired.clear()
        after = counts(arg)
        return {k: (after[k] - before[k]) / calls for k in before}

    arg = _Arg()
    settle()
    drift: dict[str, float] = {}
    for name, one_round in (("emit", emit_round), ("singleShot", single_shot_round)):
        per_round = []
        for _ in range(max(1, rounds)):
            per_round.append(one_round(arg))
        for key in per_round[0]:
            drift[f"{name}:{key}"] = float(statistics.median(r[key] for r in per_round))
    return drift


def assert_binding_refcounts_sound(calls: int = 200, rounds: int = 5) -> dict[str, float]:
    """Raise ``RuntimeError`` naming the binding if any operation drifts."""
    drift = binding_refcount_drift(calls, rounds)
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
