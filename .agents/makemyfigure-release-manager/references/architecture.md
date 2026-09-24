# Release architecture of MakeMyFigure (as found in the repository, 2026-09-23)

## Source of truth for the version
`make_my_figure_core/version.py` -> `__version__`. `pyproject.toml` declares
`[tool.setuptools.dynamic] version = { attr = "make_my_figure_core.version.__version__" }`.
`scripts/build_desktop.py` exports it as `MMF_VERSION` for the PyInstaller spec; the About dialog
and `--selftest` read it. Other places that *repeat* it (and must be kept in step by hand or by
`scripts/build_manuals.py`) are enumerated by `_common.version_locations()`.

## Distributions
| Artefact | Built by | Contents |
|---|---|---|
| `make_my_figure_core-<v>-py3-none-any.whl`, `.tar.gz` | `python -m build` (setuptools; `setup.py` stages `schemas/`, `style_profiles/`, `mock_data/`, `examples/` into `make_my_figure_core/_bundled/`) | core renderer, statistics, package format; no GUI |
| `dist/MakeMyFigure/` (Windows, Linux) / `dist/MakeMyFigure.app` (macOS) | `scripts/build_desktop.py` -> PyInstaller one-folder app from `packaging/make_my_figure.spec` (entry `apps/desktop_app/main.py`; `datas` = the four resource folders, icons, LICENSE, README, CHANGELOG; `collect_submodules` scipy/statsmodels/patsy; excludes tkinter) | desktop app |
| `MakeMyFigure-<v>-windows.zip`, `MakeMyFigure-<v>-Setup.exe` | `scripts/build_windows.ps1` (Compress-Archive; Inno Setup `packaging/windows_installer.iss` when `iscc.exe` is on PATH) | |
| `MakeMyFigure-<v>.dmg` (fallback `-macos.zip`) | `scripts/build_macos.sh` (iconutil -> .icns, `hdiutil create -format UDZO`) | unsigned unless Apple secrets |
| `MakeMyFigure-<v>-linux-<arch>.tar.gz`, `MakeMyFigure-<v>.AppImage` | `scripts/build_linux.sh` (tar; AppDir + `appimagetool` when on PATH) | glibc of the build host |
| `MakeMyFigure_v<v>_Quick_Start.pdf`, `_User_Manual.pdf` | `scripts/build_manuals.py` (pandoc -> docx -> pdf) | |
| `SHA256SUMS.txt` | this agent (`generate_checksums.py`), format of `sha256sum` | |

## Continuous integration
`.github/workflows/build_desktop_releases.yml`: triggers on tag push `v*` and `workflow_dispatch`;
matrix windows-latest / macos-latest / ubuntu-latest; Python 3.11; `pip install -e ".[desktop,build]"`;
`scripts/make_icons.py`; per-OS build script; smoke `MakeMyFigure --selftest`; uploads the
installers as workflow artefacts and attaches them to the release when triggered by a tag. Wheel,
sdist, manuals and `SHA256SUMS.txt` have always been uploaded by hand afterwards (v1.1.0).

## What the agent adds (nothing replaces project scripts)
The agent wraps the project's build mechanism; it does not reimplement it. Its own contributions
are verification (preflight, private-file scan, version agreement), a clean build environment,
staging with manifests, cross-platform reconciliation, checksums, validation, reporting, gated
publication and the ledger. See `scripts/*.py` docstrings for the exact contract of each.

## Layout of staging
```
release_staging/<version>/
  python/    wheel, sdist, python_build_manifest.json
  linux/     tar.gz, AppImage, platform_build_manifest.json
  windows/   Setup.exe, windows.zip, platform_build_manifest.json
  macos/     dmg (or macos.zip), platform_build_manifest.json
  manuals/   the two PDFs (copied from docs/manuals after scripts/build_manuals.py)
  checksums/ SHA256SUMS.txt, release_artifacts.json
  RELEASE_NOTES_DRAFT.md, RELEASE_REPORT.md, reconciliation.json, rc_plan.json
```
