"""Fast checks for the v0.6 performance infrastructure (workers + benchmarks)."""

import matplotlib
import pytest

matplotlib.use("Agg")


def test_workers_api_present():
    pytest.importorskip("PySide6")
    from apps.desktop_app import workers

    assert hasattr(workers, "Task")
    assert hasattr(workers, "WorkerSignals")
    assert callable(workers.run_in_background)
    assert callable(workers.global_pool)


def test_task_runs_and_reports_finished():
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

    from apps.desktop_app import workers

    app = QCoreApplication.instance() or QCoreApplication([])
    got = {}

    def slow_add(a, b, progress_cb=None):
        if progress_cb:
            progress_cb("working")
        return a + b

    loop = QEventLoop()
    task = workers.Task(slow_add, 2, 3)
    task.signals.finished.connect(lambda r: (got.setdefault("result", r), loop.quit()))
    task.signals.error.connect(lambda e: (got.setdefault("error", e), loop.quit()))
    QTimer.singleShot(5000, loop.quit)  # safety timeout
    workers.global_pool().start(task)
    loop.exec()

    assert got.get("result") == 5, got


def test_task_reports_error():
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

    from apps.desktop_app import workers

    QCoreApplication.instance() or QCoreApplication([])
    got = {}

    def boom():
        raise ValueError("kaboom")

    loop = QEventLoop()
    task = workers.Task(boom)
    task.signals.finished.connect(lambda r: loop.quit())
    task.signals.error.connect(lambda e: (got.setdefault("error", e), loop.quit()))
    QTimer.singleShot(5000, loop.quit)
    workers.global_pool().start(task)
    loop.exec()

    assert "kaboom" in got.get("error", "")


def test_benchmark_core_runs_and_reports():
    """The benchmark battery returns a timings dict and renders a report."""
    import importlib.util
    import os

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    path = os.path.join(root, "scripts", "benchmark_performance.py")
    spec = importlib.util.spec_from_file_location("benchmark_performance", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # tiny internal timing helper works
    t = mod._timeit(lambda: sum(range(1000)), repeats=2)
    assert t["best"] >= 0 and t["runs"] == 2

    results = mod.run_benchmarks(quick=True, repeats=1)
    assert "render" in results and "example_load" in results
    # at least one common plot rendered without error
    assert any("error" not in v for v in results["render"].values())
    report = mod.render_report(results)
    assert "performance report" in report.lower()
