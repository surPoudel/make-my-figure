# Build summary — preprocessing/QC apps release candidate

## Environment (this run)
- Platform: **Linux (WSL2)** — `Linux 6.6.87.2-microsoft-standard-WSL2`
- Python: **3.11.8** (miniconda)
- PyInstaller: **6.19.0** (installed)
- PySide6: **6.11.1** (installed as a package, but **cannot load** — see below)

## Desktop build: NOT run in this sandbox (honest status)
`python scripts/build_desktop.py` was **not executed** here. Reason: PySide6 fails to
import in this WSL sandbox because the Qt runtime needs `libEGL.so.1`, which is not
installed:

```
ImportError: libEGL.so.1: cannot open shared object file: No such file or directory
```

PyInstaller analyses the app by importing its modules, so the Qt import failure would
break the build before producing a usable artifact. Rather than emit a broken/partial
binary or fake a result, the build is deferred to an environment with the Qt system
libraries present.

**No build artifact was produced. No `dist/` was created. No Windows `.exe` was built.**

## How to build (run in the appropriate native environment)

### WSL/Linux (produces a **Linux** build only)
First install the Qt runtime libs, then build:
```bash
sudo apt-get install -y libegl1 libxkbcommon0 libxcb-cursor0   # Qt runtime deps
python -m pip install -e ".[desktop]"
python -m pytest -q -p "no:pytest-qt" --ignore=tests/test_desktop_gui.py
python scripts/build_desktop.py        # or scripts/build_linux.sh
```

### Native Windows (required for the distributable **.exe**)
Use PowerShell / Command Prompt on Windows (NOT WSL):
```powershell
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install -e ".[desktop]"
python -m pytest -q
python scripts\build_desktop.py        # or scripts\build_windows.ps1
```

> Platform note (per request): a Windows `.exe` must be built from native Windows
> Python/PowerShell. This candidate does **not** claim a Windows executable was built
> from WSL.

## Artifacts to record after a real build
| Field | Value |
|-------|-------|
| Artifact name(s) | (fill after build, e.g. `dist/MakeMyFigure`) |
| Artifact size(s) | (fill after build) |
| Platform | Linux / Windows / macOS |
| Python version | 3.11.8 |
| Build command | `python scripts/build_desktop.py` |

Generated installers/executables should stay **outside git** (or be attached manually
later) — do not commit large binaries.
