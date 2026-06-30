# Milestone 4 Summary — Zero-command desktop app + core refactor

Date: 2026-06-30

## What was built

### 1. Reusable core package (`make_my_figure_core/`)
The engine was refactored out of the old `make_my_figure` package into a
frontend-agnostic core, shared by both apps:
- data loading (`io/`), PlotSpec validation (`spec/`), journal style profiles
  (`styles/`), 17 plot renderers (`plots/`), export logic (figures + sidecar +
  ZIP bundle in `plots/registry.py`), provenance helpers, harvest pipeline
  (`harvest/`), **mock-data helpers** (`data.py`), shared **UI hints**
  (`ui_hints.py`), frozen-aware **resource resolution** (`resources.py`), and a
  single-source **version** (`version.py`).
- Resource paths (`schemas/`, `style_profiles/`, `mock_data/`) resolve via
  `sys._MEIPASS` when frozen, so the same code works in dev and in a packaged app.

### 2. Streamlit frontend kept (`apps/streamlit_app/`)
Moved from `app/` to `apps/streamlit_app/streamlit_app.py`; still works
(`streamlit run apps/streamlit_app/streamlit_app.py`). Not modified functionally.

### 3. New desktop frontend (`apps/desktop_app/`, PySide6)
- `controller.py` — GUI-free logic (catalog, load file/example, build spec,
  render, export, save template). Fully unit-tested without Qt.
- `main.py` — Qt UI: welcome screen (Open data file / Use example data / Recent
  files / Help), data import with **drag-and-drop**, table preview + detected
  column types + friendly errors, plot workflow (type, Nature/Science/Cell-like
  style, column dropdowns, dynamic options, **live preview**, validation
  warnings), export to **SVG/PNG/PDF/PlotSpec JSON/ZIP**, “Open example” for
  every plot type, “Save template”, in-app **Help** (plot descriptions from the
  manifest, formatting guide, privacy, journal-like disclaimer), and **About**
  showing the single-sourced version. Privacy is stated on the welcome screen
  and status bar; no telemetry, no network.
- `help_content.py` — help text; plot descriptions/required columns read from
  the bundled manifest (not invented).
- A `--selftest` headless mode renders + exports all 17 plot types (used by CI
  and to validate frozen builds).

### 4. Packaging
- `packaging/make_my_figure.spec` — PyInstaller spec; bundles resource folders,
  matplotlib SVG/PDF/PS/Agg/QtAgg backends, SciPy; builds a one-folder app and a
  macOS `.app` (BUNDLE) with Info.plist + icon.
- `scripts/build_desktop.py` (cross-platform driver, injects version),
  `scripts/build_windows.ps1`, `scripts/build_macos.sh`, `scripts/build_linux.sh`,
  `scripts/make_icons.py` (placeholder icons), `packaging/windows_installer.iss`
  (Inno Setup, optional).
- `assets/icons/` — placeholder PNG/ICO + sized PNGs (icns generated on macOS).
- `.github/workflows/build_desktop_releases.yml` — builds on windows/macos/ubuntu
  latest, smoke-tests the built binary (`--selftest`), uploads artifacts. Signing
  steps are **guarded by secrets** and never fail unsigned builds. No public
  publish.
- Versioning is single-sourced in `make_my_figure_core/version.py`; `pyproject.toml`
  reads it dynamically; About displays it.

### Expected release artifacts
| OS | Primary | Fallback |
|----|---------|----------|
| Windows | `MakeMyFigure-Setup.exe` (Inno) | `MakeMyFigure-windows.zip` |
| macOS | `MakeMyFigure.dmg` | `MakeMyFigure-macos.zip` (zipped `.app`) |
| Linux | `MakeMyFigure.AppImage` | `MakeMyFigure-linux.tar.gz` |

### Docs
`docs/DESKTOP_APP.md`, `docs/BUILD_INSTALLERS.md`, `docs/RELEASE_CHECKLIST.md`,
`docs/CODE_SIGNING.md`.

## Tests

`pytest -q` → **139 passed** (was 116). New: `test_desktop_controller.py` (load →
render → export all formats + ZIP + save template for all 17 types),
`test_desktop_gui.py` (offscreen Qt: welcome page, load/render, switch plot
types, export ZIP), `test_packaging.py` (single-source version, spec/scripts/CI
presence, frozen resource resolution). All prior core tests pass under the new
`make_my_figure_core` import path.

**Verified a real PyInstaller build** on macOS: the frozen
`dist/MakeMyFigure/MakeMyFigure --selftest` loads bundled mock data and renders +
exports SVG/PNG/PDF for all 17 plot types (exit 0). Resource bundling confirmed
in both the one-folder app and the `.app`.

## Constraints honored
- Streamlit app preserved and working. Plot logic lives in core, not the GUI.
- Packaged app requires neither Python nor a command line for end users.
- No public publish/deploy; no paid services; no secrets accessed (signing reads
  user-provided env/secrets only). Work stayed in-repo. Journal-like disclaimer
  shown in Help and About; no official-compliance claims.

## Still needs manual work
- **Real builds for Windows and Linux** must run on those OSes (or via the CI
  workflow) — PyInstaller can't cross-compile. The macOS build is verified here.
- **Code signing / notarization** (Windows Authenticode, Apple Developer ID +
  notarization) — placeholders only; requires certificates/secrets you provide
  (see `docs/CODE_SIGNING.md`). Unsigned apps trigger OS warnings.
- **`.dmg` / AppImage / `.exe`** wrappers depend on host tools (hdiutil,
  appimagetool, Inno Setup); portable ZIP/tarball fallbacks always build.
- Replace placeholder **icons** and the author/URL/license placeholders in
  `pyproject.toml`, the Inno script, and About.
- Publishing a public GitHub Release is a deliberate manual step (needs your
  approval).
