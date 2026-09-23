# Release history (derived from git tags, GitHub releases and CI runs on 2026-09-23)

| Tag | Date (release) | Commit | Tag type | version.py | Assets | Notes |
|---|---|---|---|---|---|---|
| v0.1.0 | 2026-07-03 | 66ba3c3 | lightweight | 0.1.0 | 5 unversioned installers | first desktop release |
| v0.2.0 | 2026-07-10 | 44ca6b0 | lightweight | 0.2.0 | 5 | `docs/RELEASE_NOTES_v0.2.md` |
| v0.3.0 | 2026-07-10 | 65a1222 (origin: 5f9cff5) | lightweight | 0.3.0 | 5 | local/origin tag differ |
| v0.4.0 | 2026-07-11 | 453733d | lightweight | 0.4.0 | 5 | 35 plot types era |
| v0.5.0 | 2026-07-11 | 80127c7 (origin: eb5cfa4) | lightweight | 0.5.0 | 5 | two CI runs, tag re-pointed |
| v0.5.1 | 2026-07-12 | 5fb87a0 (origin: b58f0f5) | lightweight | 0.5.1 | 5 | one failed + one successful CI run |
| v0.5.2 | 2026-07-12 | cec834a | lightweight | 0.5.2 | 5 | |
| v0.5.3 | 2026-07-13 | 2867a29 | lightweight | 0.5.3 | 5 | |
| v0.6.1 | 2026-07-15 | 309ca6e | annotated | 0.6.1 | 7 (+ wheel, sdist) | first wheel/sdist on the release |
| v1.0.0-rc1 | 2026-07-17 | dc49b8e | annotated | 1.0.0rc1 | 5 | not marked pre-release on GitHub |
| v1.0.0 | 2026-07-19 (tag 07-18) | f815f41 | annotated | 1.0.0 | 5 | `docs/RELEASE_NOTES_v1.0.0.md` |
| v1.1.0 | 2026-09-06 | 3da8563 | annotated | 1.1.0 | 10 | versioned names, manuals PDFs, wheel, sdist, SHA256SUMS.txt; audit in `docs/releases/v1.1.0/`; 38 plot types, 18 statistical procedures |
| (v1.1.1) | prepared 2026-09-20 on `main` (dc99f07, HEAD 84458dd) | - | not tagged | 1.1.1 | none | figure packages, chord diagram (39 plot types), pandas-3 fix; release notes and CHANGELOG ready |

Asset names before v1.1.0: `MakeMyFigure-linux.tar.gz`, `MakeMyFigure-Setup.exe`,
`MakeMyFigure-windows.zip`, `MakeMyFigure.AppImage`, `MakeMyFigure.dmg` (unversioned; the CI
workflow's default names). From v1.1.0 the names carry the version and the wheel/sdist/manuals/
checksums are attached by hand: this is the set `_common.EXPECTED_PUBLIC_ARTIFACTS` encodes.

CI: every tag push ran `Build desktop releases` successfully (v0.5.1 once failed first). A manual
`workflow_dispatch` on `main` on 2026-09-17 rebuilt the v1.1.0-era artefacts (commit f7f1f46) - so
the installers attached to v1.1.0 are not necessarily byte-identical to a fresh build of 3da8563;
PyInstaller output is not bit-reproducible across runs anyway. Compare by size class and self-test,
not by hash.

v1.1.0 asset sizes (reference for `validate_artifacts.py --compare-release v1.1.0`): linux tar.gz 188 MB,
AppImage 188 MB, Setup.exe 104 MB, windows.zip 152 MB, dmg 137 MB, Quick Start PDF 2 MB, User Manual
PDF 6 MB, wheel and sdist ~1 MB each.

Machine-readable records: `release_history/v0.6.1.json`, `v1.0.0-rc1.json`, `v1.0.0.json`, `v1.1.0.json`
(from `record_release.py`), `TEMPLATE.json` for future entries.
