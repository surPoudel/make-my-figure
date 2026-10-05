# macOS build

Wrapper: `scripts/build_macos.sh` -> `iconutil` (.icns from `assets/icons/icon_*.png`) -> `scripts/build_desktop.py
--clean` (PyInstaller `.app` bundle) -> `hdiutil create -volname "Make My Figure" -format UDZO` -> fallback
`MakeMyFigure-<v>-macos.zip` when hdiutil fails. Unsigned unless `APPLE_DEVELOPER_ID` (and the notarisation
secrets described in `docs/CODE_SIGNING.md`) are present; they never are in this project's history.
Agent: `build_current_platform.py` on the Mac (clean venv at `~/.cache/makemyfigure-release/venv-macos-py3.11`);
self-test runs `dist/MakeMyFigure.app/Contents/MacOS/MakeMyFigure --selftest`.

## Practical notes (from the author's MacBook sessions, September 2026)
- Do not build inside the OneDrive `CloudStorage` folder: `pip install -e` and PyInstaller stall while
  OneDrive indexes `.venv` and `build/`. `git clone` the repository to `~/src/make_my_figure` and check out
  the release commit there.
- Python 3.11 via python.org or Homebrew; PySide6 wheels exist for both arm64 and x86_64. CI's
  `macos-latest` runner is arm64 (Apple silicon); an Intel Mac produces an x86_64 `.app`. Record the
  architecture (the manifest stores `platform.machine()`); v1.1.0's dmg came from the CI runner.
- Gatekeeper: first launch of the unsigned app needs right-click -> Open or *Privacy & Security -> Open Anyway*.
  The release notes carry that sentence (`release_notes_draft.py`).
- `hdiutil` is part of macOS; no extra tools.

## Artefacts
`MakeMyFigure-<v>.dmg` (expected) or `MakeMyFigure-<v>-macos.zip` (fallback, reported as unexpected name by
`validate_artifacts.py` so the author notices). v1.1.0 dmg: 137 MB.
