# Testing gates

1. **Unit / integration suite** - `run_tests.py` (quick gates or full headless suite; `--gui` adds
   `tests/test_desktop_gui.py` offscreen). Counts are parsed from pytest's summary line, never typed in.
2. **Wheel smoke test** - `smoke_test_install.py`: fresh venv in a temp dir, `pip install <wheel>`,
   probe run with the temp dir as cwd so the checkout cannot shadow the install. Checks import path
   is `site-packages`, `__version__`, registry size, `resources.missing_bundled_dirs() == []`,
   render + PNG/PDF export of the bundled boxplot example, one Welch t-test through the renderer.
3. **Desktop self-test** - the built executable's `--selftest` (`apps/desktop_app/main.py::_selftest`):
   renders every registered plot type, exports, figure-package round trip, Welch brackets, two-way
   ANOVA (statsmodels + patsy). Prints `SELFTEST OK: N plot types rendered + exported; ...`.
   `build_current_platform.py` runs it and records the line. Offscreen: `QT_QPA_PLATFORM=offscreen`
   is set automatically when no display is present (WSL also needs the Qt runtime libraries on
   `LD_LIBRARY_PATH`, see `local-model-runtime.md`).
4. **Artefact validation** - `validate_artifacts.py`: names, sizes, archive integrity, embedded
   version, executable present, size ratio to the previous release (0.5x-2x).
5. **Reconciliation** - `reconcile_platforms.py`: same commit, same version, clean tree, self-test
   OK for every staged platform.
6. **Manual launch** (author, per OS, before publishing): open the installer, open an example,
   change plot type and style, export PNG/SVG/PDF, save and reopen a `.mmfpackage`. Not scriptable
   from here; the checklist in `docs/RELEASE_CHECKLIST.md` section 2 applies.

Runtime reference points measured on WSL (2026-09-23, repository on OneDrive): wheel+sdist build 2m19s,
wheel smoke test 46 s, PyInstaller one-folder build 9-10 min in the clean venv, `--selftest` of the bundle
4-10 min, release-gate pytest subset 34 passed / 2 skipped in 21 s. A full `release_manager.py build-local`
run took about 25 min.
