# Artefact validation

Script: `validate_artifacts.py --version X.Y.Z [--compare-release vA.B.C]` -> `reports/artifact_validation.json`.

| Artefact | Checks |
|---|---|
| wheel | zip integrity; `METADATA Version == v`; `_bundled/schemas` present |
| sdist | `make_my_figure_core/version.py` inside says `v`; `pyproject.toml` present |
| windows zip | zip integrity; `MakeMyFigure.exe` member |
| Setup.exe | `MZ` header |
| dmg | non-empty (verify with `hdiutil verify` on a Mac) |
| macos zip | zip integrity; `Contents/MacOS/MakeMyFigure` member |
| linux tar.gz | `MakeMyFigure/MakeMyFigure` member |
| AppImage | ELF header + AppImage type-2 magic `AI\x02` at offset 8 |
| manual PDFs | `%PDF-` header |

All: file name equals the expected name for the version (`_common.EXPECTED_PUBLIC_ARTIFACTS`); size
above a plausibility floor (installers >= 40-80 MB, python dists >= 0.5 MB); with `--compare-release`
the size ratio to the same-named asset of the previous release must be within 0.5x-2x. A ratio
outside the band is the signature of a polluted build environment (too big) or missing hidden
imports / data files (too small): escalate to the author, do not publish.

Manifests: each platform folder carries `platform_build_manifest.json` (commit, dirty, host, tool
versions, self-test line, artefact hashes); `reconcile_platforms.py` compares them.
