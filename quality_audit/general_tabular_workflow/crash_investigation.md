# macOS crash investigation — v1.3.0 desktop app

Status: **root cause identified with measured evidence on Linux; not yet
reproduced or verified on macOS hardware.** Do not call the macOS crash fixed
until a packaged build is run on a Mac (see "Remaining uncertainty").

## Report

| | |
|---|---|
| App | MakeMyFigure v1.3.0, packaged (CI build, run 38016886624) |
| Machine | MacBook Pro 14-inch (Nov 2024), Apple M4 Pro, 24 GB — `Mac16,8` |
| OS | macOS 27.0.1 ("Golden Gate"), from the reporter's About-This-Mac recording |
| Signal | `EXC_BAD_ACCESS (SIGSEGV)`, `KERN_INVALID_ADDRESS at 0x0`, main thread |
| Stack (summary) | libshiboken6 `mainThreadDeletionHandler` · PySide6 `SignalManager` · Python callback execution |
| Full `.ips` | **not obtained** — the supplied screenshot arrived as a blank image |

## Bundled binding versions (from the CI build logs)

| Release | macOS runner | PySide6 / shiboken6 bundled |
|---|---|---|
| v1.2.0 | macos-latest | 6.11.2 |
| v1.2.1 | macos-latest | 6.11.2 |
| **v1.3.0** | macos-26-arm64 | **6.12.0** |

The release workflow installs `pip install -e ".[desktop,build]"`, resolving the
unpinned `PySide6>=6.5,<7` to the newest release. The test workflow installs
`requirements-lock.txt` (6.11.2). So **every test of v1.3.0 ran on 6.11.2 and
the shipped app ran on 6.12.0** — the shipped binding was never tested.

## What `mainThreadDeletionHandler` does (shiboken 6.11.2 / 6.12.0 source)

`basewrapper.cpp` `SbkDeallocWrapperCommon`: when a Python-owned wrapper of a
`delete-in-main-thread` type (`QWidget`, `QWindow`, `QQuickItem`,
`QQuickTransform`) is deallocated off the main thread, shiboken records the raw
C++ pointer and calls `Py_AddPendingCall(mainThreadDeletionHandler)`; the main
thread later runs `BindingManager::runDeletionInMainThread()`, calling each
destructor without re-checking the pointer. Pending calls run when the main
thread next executes Python — i.e. inside a SignalManager slot callback, which
matches the reported stack. 6.12.0 changed this function (wrapper unregistered
earlier; `cppPointer()` accessor).

## Hypotheses tested

Machine: WSL2 Linux, Python 3.11, offscreen Qt. Scripts in `crash_repro/`.
`MALLOC_PERTURB_=165` poisons freed memory so a use-after-free cannot pass silently.

### H1 — app code: detached canvas freed by GC on a worker thread → double delete — **refuted**

`_clear_figure` does `setParent(None)` then `deleteLater()` on the old canvas and
toolbar (`apps/desktop_app/main.py`). Measured ownership (`deletelater_ownership.py`):

| State | refcount | owned by Python | collectable |
|---|---|---|---|
| new, unparented | 2 | True | yes |
| `setParent(None)` | 2 | True | yes |
| `setParent(None)` + `deleteLater()` | 3 | **False** | **no** |

`deleteLater()` hands ownership back to C++ and pins the wrapper (identical on
6.11.2 and 6.12.0), so a deleteLater'd widget can never reach the
main-thread-deletion queue. Stress runs agree: 598/598 detached canvases freed on
a worker thread, **0** still alive-and-Python-owned at that moment; 1 500
canvas/toolbar teardown cycles with concurrent workers, no crash.

### H2 — the bundled binding miscounts references — **confirmed**

Per-call reference-count drift, 200 and 2 000 calls (`op_refcount_drift.py`,
`apps/desktop_app/binding_check.py`):

| Operation | 6.11.2 | 6.12.0 |
|---|---|---|
| `Signal.emit` → Python slot | 0.000 | **`True` −1.000 / −1.005**; fatal `bool_dealloc` by N = 200 |
| `QTimer.singleShot(0, callable)` | 0.000 | **`None` −1.002 / −1.005**; fatal `none_dealloc` by N = 2 000 |
| `QCoreApplication.postEvent` (2 000 000 calls) | ok | fatal `none_dealloc` |
| QWidget freed on main / worker thread | 0.000 | −0.001 to −0.04 |

The path named in the report — Python-owned widgets freed on a `QThread`,
destroyed by `mainThreadDeletionHandler` under a SignalManager callback
(`main_thread_deletion_stress.py`): **6.11.2 survived 20 000 cycles twice;
6.12.0 aborted in both runs** (`bool_dealloc`).

Under Python 3.11 (`True`/`None` are not immortal until 3.12) each over-release
walks a live object's count towards zero; when it gets there the object is freed
while still referenced. On glibc that is caught as a fatal abort; on macOS, whose
allocator zero-fills freed small blocks, a later call through the freed object
reads a null vtable — consistent with `KERN_INVALID_ADDRESS at 0x0` inside the
next Python callback.

### H3 — click-to-label re-render inside the canvas's own mouse event — not pursued

`_on_canvas_pick` → `render_preview()` tears down the canvas handling the event.
Because `deleteLater()` defers destruction (H1), the C++ object outlives the
event. Kept as a code-quality note, not a crash cause.

## Fix (branch `hotfix/pyside6-6.12.0-refcount-crash`, from `v1.3.0`)

1. `pyproject.toml`: `desktop = ["PySide6>=6.5,!=6.12.0,<7"]` — `pip` now resolves 6.11.2.
2. `apps/desktop_app/binding_check.py`: measures the drift above.
3. `--selftest` (run by CI on every built installer, including the macOS `.app`)
   fails if the bundled binding drifts — a future defective release fails the
   build rather than reaching users.
4. `tests/test_qt_binding_refcounts.py`: passes on 6.11.2 (3/3); on 6.12.0 fails
   with `{'emit:True': -1.0, 'singleShot:None': -1.065}`.

Not done, deliberately: app-code lifetime changes (H1 refuted; changing working
teardown code without a reproduced defect violates rule 10).

## Remaining uncertainty

- **No full `.ips`.** Without its backtrace, the link between the 6.12.0 defect
  and this specific crash is strong (same release boundary, same code path,
  same crash class) but inferential.
- **Not reproduced on macOS.** All measurements are Linux builds of the same
  PySide6 versions. Needed before declaring fixed: build the hotfix in CI, run
  the `.app` on the reporter's Mac (or any Apple-silicon Mac on macOS 26/27),
  and use it for a session that previously crashed.
- The triggering user action is unknown. The defect is cumulative (every signal
  emit), so the crash time depends on how much the app was used, not on one action.
- Upstream: no PySide6 release after 6.12.0 exists yet (PyPI, 2026-10-13); report
  the drift measurements to Qt's bug tracker (PYSIDE project).
