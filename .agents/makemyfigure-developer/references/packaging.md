# Packaging reference — MakeMyFigure

Reconstructed from the live checkout on 2026-09-17 (`main` at bb45c12). Paths are
relative to the repository root. Two distinct artefact families exist:

1. **Python distribution** (`make_my_figure_core` wheel + sdist) — built with
   `python -m build`, *not* by CI.
2. **Desktop application** (PyInstaller one-folder app wrapped per OS) — built by
   `scripts/build_*.{ps1,sh}` locally or by `.github/workflows/build_desktop_releases.yml`.

## 1. Python package metadata

### `pyproject.toml`

- Build backend: `setuptools>=61.0` (`setuptools.build_meta`).
- Project name `make_my_figure_core`; `requires-python = ">=3.9"`; MIT licence via
  `license = {file = "LICENSE"}` plus classifiers (added in commit 81157f1, PR #10).
- **Version is dynamic**: `dynamic = ["version"]` and
  `[tool.setuptools.dynamic] version = { attr = "make_my_figure_core.version.__version__" }`.
  The single source of truth is `make_my_figure_core/version.py` (`__version__ = "1.1.0"`).
- Runtime dependencies are bounded ranges "next major excluded" (pandas, numpy,
  matplotlib, scipy, statsmodels, openpyxl, jsonschema, networkx, adjustText, pillow).
- Extras: `app` (streamlit), `desktop` (PySide6), `build` (pyinstaller, pillow),
  `dev` (pytest, pytest-qt), `import-panels` (pymupdf, cairosvg), `count-de` (pydeseq2).
- Packages: `[tool.setuptools.packages.find] include = ["make_my_figure_core*"]`;
  package data `make_my_figure_core = ["_bundled/**/*"]`; `include-package-data = true`.

### `setup.py` — resource staging into `_bundled/`

The four resource folders read at runtime (`schemas/`, `style_profiles/`, `mock_data/`,
`examples/`) live at the repo root. `setup.py` subclasses `build_py` and, after the
standard build, copies each folder into `<build_lib>/make_my_figure_core/_bundled/<name>`
(ignoring `__pycache__`). It never writes into the source tree. The tuple
`BUNDLED_DIRS = ("schemas", "style_profiles", "mock_data", "examples")` must match
`make_my_figure_core/resources.py::BUNDLED_DIRS`; `tests/test_package_data.py`
enforces the agreement. `resources.project_base()` resolves, in order: env override,
`sys._MEIPASS` (frozen), the staged `_bundled/` dir, then the checkout root.

History: every wheel before commit c5b2389 (2026-08-25, "Merge the packaging fix so a
built wheel can actually render") lacked these folders and `render()` failed on
`schemas/plot_spec.schema.json` — the docstring in `setup.py` records this.

### `MANIFEST.in`

`graft` of the same four folders plus `LICENSE`, `README.md`, `pyproject.toml`;
`recursive-exclude` of `__pycache__` and `*.py[co]`. This is what lets an sdist build
stage the resources too.

### Requirements files

- `requirements.txt` — the bounded ranges again plus `streamlit` and `pytest`
  (what `README.md` tells source users to install).
- `requirements-lock.txt` — exact versions the v1.1.0 release and its suite were run
  with (pandas 2.2.3, numpy 2.1.2, matplotlib 3.10.8, scipy 1.17.1, statsmodels 0.14.6,
  streamlit 1.62.0, pytest 9.1.1, PySide6 6.11.2, pytest-qt 4.5.0; Python 3.11 on
  Windows 11 and WSL2). Use `python -m pip install -r requirements-lock.txt` for a
  reproducible environment.

### Building the wheel and sdist

```bash
python -m pip install --upgrade build
python -m build                       # -> dist/make_my_figure_core-<ver>-py3-none-any.whl, dist/make_my_figure_core-<ver>.tar.gz
python -m venv /tmp/mmf-smoke && /tmp/mmf-smoke/bin/pip install dist/*.whl
/tmp/mmf-smoke/bin/python -c "import make_my_figure_core.resources as r; print(r.project_base(), r.missing_bundled_dirs())"
```

The v1.1.0 audit (§7) smoke-tested exactly this: version 1.1.0, 38 plot types, exports
PNG/PDF/SVG/TIFF/EPS, resources resolved from `site-packages/make_my_figure_core/_bundled/schemas`.
`dist/` is git-ignored; built wheels were briefly tracked (commits 30c6b9e ... 5695683,
"Rebuild the distribution at ...") and removed again in f68a2f3.

## 2. Desktop application

### `packaging/make_my_figure.spec` (PyInstaller)

- Entry script `apps/desktop_app/main.py`; `APP_NAME = "MakeMyFigure"`; one-folder
  `COLLECT` output `dist/MakeMyFigure/`, plus a `BUNDLE` (`dist/MakeMyFigure.app`,
  bundle id `com.makemyfigure.desktop`) on macOS whose `CFBundleShortVersionString`
  comes from the `MMF_VERSION` environment variable (default `0.1.0` if unset — always
  build via `scripts/build_desktop.py`, which sets it).
- `datas`: the four resource folders, `assets/icons/`, and since PR #10 `LICENSE`,
  `README.md`, `CHANGELOG.md` at the bundle top level (`_internal/LICENSE` in the
  built app).
- `hiddenimports`: matplotlib agg/svg/pdf/ps/qtagg backends, PIL, all of `scipy`,
  `statsmodels`, `patsy`; `collect_data_files("statsmodels")`. `tkinter` excluded.
  `console=False`, `upx=False`, no strip.
- Icon: `assets/icons/icon.ico` on Windows, `icon.icns` on macOS, if present.

### `packaging/windows_installer.iss` (Inno Setup)

Compiled with `iscc /DMyAppVersion=<ver> packaging\windows_installer.iss`; consumes
`dist\MakeMyFigure\*`, writes `dist\MakeMyFigure-<ver>-Setup.exe`, installs to
`{autopf}\MakeMyFigure`, shows `LICENSE`, optional desktop icon, launches after
install. `SignTool=` is commented out (see `docs/CODE_SIGNING.md`).

### Build scripts

| Script | Host | Output in `dist/` |
|---|---|---|
| `scripts/build_desktop.py [--clean]` | any | `MakeMyFigure/` (or `MakeMyFigure.app`); sets `MMF_VERSION` from `version.py` and runs `python -m PyInstaller packaging/make_my_figure.spec --noconfirm` |
| `scripts/build_windows.ps1` | Windows PowerShell | always `MakeMyFigure-<ver>-windows.zip`; `MakeMyFigure-<ver>-Setup.exe` if `iscc.exe` is on PATH |
| `scripts/build_macos.sh` | macOS | `icon.icns` via `iconutil`, `MakeMyFigure-<ver>.dmg` via `hdiutil`, fallback `MakeMyFigure-<ver>-macos.zip` |
| `scripts/build_linux.sh` | Linux | always `MakeMyFigure-<ver>-linux-<uname -m>.tar.gz`; `MakeMyFigure-<ver>.AppImage` if `appimagetool` is on PATH |
| `scripts/make_icons.py` | any (needs Pillow) | placeholder bar-chart icons into `assets/icons/` (`icon.png`, `icon.ico`, `icon_<n>.png`) |

All three per-OS scripts read the version from `make_my_figure_core.version` and call
`build_desktop.py --clean`; version-stamped file names date from commit f68a2f3
(v1.1.0). Before that (v1.0.0 and earlier) assets were unversioned
(`MakeMyFigure-Setup.exe`, `MakeMyFigure.dmg`, ...), which is what
`docs/RELEASE_CHECKLIST.md` and `docs/BUILD_INSTALLERS.md` still list.

Builds are not cross-compilable: each OS artefact is built on that OS
(`docs/BUILD_INSTALLERS.md`, "Notes / gotchas"). The CI workflow is therefore the
only way to produce all three from one machine; see `release-workflow.md`.

### Smoke test of a built app

```bash
QT_QPA_PLATFORM=offscreen ./dist/MakeMyFigure/MakeMyFigure --selftest      # Linux
QT_QPA_PLATFORM=offscreen ./dist/MakeMyFigure/MakeMyFigure --selftest      # macOS (CI runs the one-folder launcher, which PyInstaller emits beside the .app)
.\dist\MakeMyFigure\MakeMyFigure.exe --selftest                            # Windows (windowed exe prints nothing; check exit code)
```

`--selftest` is implemented in `apps/desktop_app/main.py::_selftest` and renders +
exports every registered plot type ("SELFTEST OK: 38 plot types rendered + exported;
statistics OK" on the v1.1.0 runners).

## 3. Documentation to keep in step

- `docs/BUILD_INSTALLERS.md` — prerequisites, one-command build, per-OS scripts,
  expected artefact table, icon rebranding. Its artefact names are the pre-v1.1.0
  unversioned ones and its "CI ... does not publish a public release on its own"
  sentence is out of date (the workflow does `gh release create` on a `v*` tag).
- `docs/CODE_SIGNING.md` — optional Authenticode / Developer ID + notarisation.
  Signing secrets (`WINDOWS_CERT_PFX_BASE64`, `WINDOWS_CERT_PASSWORD`,
  `APPLE_DEVELOPER_ID`, `APPLE_ID`, `APPLE_APP_PASSWORD`, `APPLE_TEAM_ID`) are only
  *detected* by the scripts; the actual `signtool` / `codesign` calls are commented
  placeholders. All published releases are unsigned.
- `docs/WINDOWS_PERFORMANCE.md` — why a frozen Windows build is slow on first launch
  (Defender scan, cold DLL load, Matplotlib font cache), OneDrive hydration, background
  workers in `apps/desktop_app/workers.py`; measurement via
  `python scripts/benchmark_performance.py --quick`.
- `docs/DESKTOP_APP.md` §"Run it from source" and the OneDrive warning.

## 4. Known runtime constraints

- **Linux binaries need glibc >= 2.38** (built on the `ubuntu-latest` = Ubuntu 24.04
  runner). Ubuntu 22.04 and current WSL2 Ubuntu images cannot run the tar.gz/AppImage;
  use the wheel or a source install. Recorded in `docs/RELEASE_NOTES_v1.1.0.md`
  (commit e57cb68), `README.md` line 40 and the v1.1.0 release body.
- Desktop app on Linux/WSL needs Qt system libraries
  (`libxkbcommon0 libgl1 libegl1 libxcb-*`); `apps/desktop_app/main.py` prints the
  `apt install` line when the PySide6 import fails.
- Installers are unsigned: SmartScreen / Gatekeeper first-launch steps in
  `docs/CODE_SIGNING.md` and the Quick Start.
- Bundles are large (~100-190 MB) because Qt, NumPy, SciPy and Matplotlib are inside.
- Do not build or run from a cloud-synced folder if you can avoid it
  (`docs/WINDOWS_PERFORMANCE.md`, `docs/DESKTOP_APP.md`).

## 5. Building a LOCAL test application on the host OS

Prerequisite on every OS (from `docs/BUILD_INSTALLERS.md`):

```bash
python -m pip install -e ".[desktop,build]"
python scripts/make_icons.py          # once; regenerates placeholder icons
```

**Windows (PowerShell, from the repo root)**

```powershell
.\scripts\build_windows.ps1                       # zip always; Setup.exe if Inno Setup's iscc.exe is on PATH
.\dist\MakeMyFigure\MakeMyFigure.exe --selftest   # exit code 0 = OK
.\dist\MakeMyFigure\MakeMyFigure.exe              # launch
```

**macOS**

```bash
chmod +x scripts/build_macos.sh && ./scripts/build_macos.sh   # .app + .dmg (or -macos.zip)
open dist/MakeMyFigure.app
```

**Linux / WSL2** (needs the Qt libs above; `appimagetool` optional)

```bash
chmod +x scripts/build_linux.sh && ./scripts/build_linux.sh
QT_QPA_PLATFORM=offscreen ./dist/MakeMyFigure/MakeMyFigure --selftest
./dist/MakeMyFigure/MakeMyFigure
```

Just the raw app folder on any OS: `python scripts/build_desktop.py --clean`.

## 6. Launching from source (no binary build)

Entry points confirmed in `README.md` lines 52-59 and `docs/DESKTOP_APP.md` line 79:

```bash
python -m pip install -r requirements.txt          # core + browser app + pytest
python -m pip install -e ".[desktop]"              # adds PySide6 for the desktop app
python -m apps.desktop_app.main                    # desktop app (add --debug for diagnostics)
streamlit run apps/streamlit_app/streamlit_app.py  # browser app, no Qt needed
```

`apps/desktop_app/main.py` inserts the repo root on `sys.path`, so no install is
strictly required to run it from a checkout. The status bar shows
`Make My Figure v<ver> · <commit> · <platform> · <backend>` from
`make_my_figure_core.version.build_banner()`; if the commit does not match
`git rev-parse --short HEAD`, a stale installed package is shadowing the checkout
(`docs/CROSS_PLATFORM_QC.md`).

## Verify this is still current

```bash
grep -n 'dynamic\|version\|package-data\|_bundled' pyproject.toml setup.py | head -20
ls packaging scripts/build_* scripts/make_icons.py && grep -n 'MMF_VERSION\|LICENSE' packaging/make_my_figure.spec
grep -n 'glibc' README.md docs/RELEASE_NOTES_v1.1.0.md
grep -n 'python -m apps\|streamlit run' README.md docs/DESKTOP_APP.md docs/RELEASE_CHECKLIST.md
```
