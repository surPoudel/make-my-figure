# Release Checklist

> Publishing a public release requires explicit maintainer action. CI builds
> artifacts but does not create a public GitHub Release on its own.

## 1. Pre-flight

- [ ] Update the version in **one place**: `make_my_figure_core/version.py`
      (`pyproject.toml` reads it dynamically; the About dialog reads it too).
- [ ] `pytest -q` passes locally (core + desktop + packaging tests).
- [ ] `python -m apps.desktop_app.main` launches and renders an example.
- [ ] `streamlit run apps/streamlit_app/streamlit_app.py` still works (web app).
- [ ] Update `README.md` / `docs/` if features changed.
- [ ] Confirm icons in `assets/icons/` are the intended ones (replace placeholders).

## 2. Local build verification (per OS, ideally)

- [ ] Windows: `./scripts/build_windows.ps1` → app launches; ZIP (and `.exe` if Inno) produced.
- [ ] macOS: `./scripts/build_macos.sh` → `.app` launches; `.dmg` produced.
- [ ] Linux: `./scripts/build_linux.sh` → app launches; AppImage/tarball produced.
- [ ] In each build: open an example, change plot type/style, export SVG/PNG/PDF/JSON and a ZIP.

## 3. CI build

- [ ] Push a tag `vX.Y.Z` **or** run the "Build desktop releases" workflow manually.
- [ ] Download and smoke-test the artifacts for each OS.

## 4. Signing (optional)

- [ ] If signing: confirm secrets are set (see `CODE_SIGNING.md`); verify signed apps
      launch without warnings.
- [ ] If unsigned: note the expected OS warnings in the release notes.

## 5. Publish (manual, requires explicit approval)

- [ ] Create the GitHub Release and attach artifacts:
      `MakeMyFigure-Setup.exe`, `MakeMyFigure.dmg`, `MakeMyFigure.AppImage`
      (+ portable ZIP/tarball fallbacks).
- [ ] Release notes: version, what changed, the journal-like disclaimer, and the
      unsigned-app guidance if applicable.
- [ ] Update download links in the docs site if used.

## 6. Post-release

- [ ] Tag verified; artifacts downloadable.
- [ ] Bump `version.py` to the next dev version if desired.
