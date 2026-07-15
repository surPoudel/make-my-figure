"""Background-execution helpers for the desktop GUI (v0.6 responsiveness).

Long tasks — statistics, clustering, layout, exports, and figure *construction* —
should not run on the Qt GUI thread, or the window freezes (felt most on Windows).
This module wraps Qt's ``QThreadPool`` / ``QRunnable`` so any callable can run off
the GUI thread and deliver its result back via signals.

Threading note for matplotlib:
    A matplotlib ``Figure`` may be *built* inside a worker (the Agg backend is fine
    for offscreen figure construction). The interactive **canvas**, however, must be
    created/updated on the GUI thread. So the pattern is: do the heavy figure work
    inside ``fn`` and return the ``Figure``; then attach it to a canvas in the
    ``on_done`` callback, which Qt delivers on the GUI thread.

The module imports PySide6 at import time (the class definitions need ``QObject`` /
``QRunnable``). It does not require a running ``QApplication`` to be imported, but
``global_pool()`` and running a ``Task`` do require a Qt application instance.
"""

from __future__ import annotations

import traceback
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class WorkerSignals(QObject):
    """Signals available from a running :class:`Task`.

    - ``finished(object)``: emitted with the callable's return value on success.
    - ``error(str)``: emitted with a formatted traceback/message on failure.
    - ``progress(str)``: optional human-readable progress updates from the task.
    """

    finished = Signal(object)
    error = Signal(str)
    progress = Signal(str)


class Task(QRunnable):
    """Run ``fn(*args, **kwargs)`` on a worker thread and report via signals.

    If ``fn`` accepts a ``progress_cb`` keyword, a callback is injected that emits
    the :attr:`WorkerSignals.progress` signal, so long tasks can report status.
    """

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = dict(kwargs)
        self.signals = WorkerSignals()
        # Inject a progress callback only if the target function wants one.
        try:
            import inspect

            if "progress_cb" in inspect.signature(fn).parameters:
                self.kwargs.setdefault("progress_cb", self.signals.progress.emit)
        except (TypeError, ValueError):
            pass

    def run(self) -> None:  # QRunnable entry point (worker thread)
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception:  # noqa: BLE001 - surface any failure to the GUI
            self.signals.error.emit(traceback.format_exc())
            return
        self.signals.finished.emit(result)


def global_pool() -> QThreadPool:
    """Return the shared application-wide thread pool."""
    return QThreadPool.globalInstance()


def run_in_background(
    pool: Optional[QThreadPool],
    fn: Callable[..., Any],
    on_done: Callable[[Any], None],
    on_error: Optional[Callable[[str], None]] = None,
    on_progress: Optional[Callable[[str], None]] = None,
    *args: Any,
    **kwargs: Any,
) -> Task:
    """Build a :class:`Task`, wire callbacks, start it, and return it.

    ``on_done`` / ``on_error`` / ``on_progress`` run on the GUI thread (Qt queues
    the signal emissions). Keep GUI mutations (canvas, widgets) in those callbacks.
    """
    task = Task(fn, *args, **kwargs)
    task.signals.finished.connect(on_done)
    if on_error is not None:
        task.signals.error.connect(on_error)
    if on_progress is not None:
        task.signals.progress.connect(on_progress)
    (pool or global_pool()).start(task)
    return task
