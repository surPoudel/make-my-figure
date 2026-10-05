# Preflight (what must be true before trusting a build)

Script: `scripts/release_preflight.py [--version X.Y.Z] [--tests quick|full|skip] [--allow-dirty] [--for-release]`
Output: `reports/release_preflight.json`, table on stdout, exit 1 on STOP.

| Area | Check | Level when false | Rationale |
|---|---|---|---|
| git | working tree clean | STOP for modified tracked files or untracked files inside shipped paths (`make_my_figure_core/`, `apps/`, `schemas/`, `style_profiles/`, `mock_data/`, `examples/`, `assets/`, `packaging/`, build scripts, packaging metadata); WARN for untracked files elsewhere; WARN with `--allow-dirty` | a manifest must describe a reproducible commit; untracked benchmark/doc/report files cannot enter an artefact |
| git | branch is `main` | WARN (STOP `--for-release`) | tags are cut from main |
| git | HEAD present on origin | WARN (STOP `--for-release`) | a tag must point at a commit that exists publicly |
| version | version.py == requested, PEP 440 form | STOP | |
| version | every documented location agrees | STOP | see versioning.md |
| version | release notes file exists | WARN (STOP `--for-release`) | |
| version | CHANGELOG has the section | STOP | release text comes from here |
| tag | `vX.Y.Z` not yet created (local + origin) | STOP | versions are used once |
| files | 15 packaging inputs present | STOP | spec, .iss, build scripts, CI workflow, icons, pyproject, setup.py, MANIFEST.in, LICENSE, CHANGELOG, README |
| private | private_file_check on the tree | STOP on any STOP finding | public repository |
| facts | live counts import | WARN | reported in the notes |
| tests | pytest quick gates / full suite | STOP on failure | counts parsed from pytest output |
| tools | build, twine, PyInstaller importable; gh logged in | WARN | gh only needed to publish |

Quick gates = `tests/test_r_validation_regressions.py tests/test_release_guardrails.py
tests/test_packaging.py tests/test_package_data.py` (the release-critical subset named in
`docs/releases/v1.1.0/release_v1.1.0_audit.md`). The full headless suite is
`python -m pytest -q -p no:pytest-qt --ignore=tests/test_desktop_gui.py` (README section 9); the GUI
module needs PySide6 and an offscreen Qt platform (`run_tests.py --gui`).

## Private-file policy (`private_file_check.py`)
STOP names: `.env*`, private keys/certificates, `PRIVATE_REFERENCE_ONLY/`, anything containing
`manuscript`, `Manuscript_`, `MakeMyFigure_manuscript`, `MakeMyFigure_submission`, Office documents
outside `docs/manuals/`, assistant session folders (`claude_code/`, `.claude/`), `CLAUDE*.md`,
`Suresh_*`. STOP contents: credential assignments, GitHub/AWS/API tokens, private key blocks.
WARN: scratch folders, videos, screenshots outside the manuals/tutorial, PDFs outside
manuals/benchmarks, OneDrive / home paths in text, files > 25 MB. The same rules run on the sdist,
wheel and app folder (`--sdist`, `--wheel`, `--app`).

## One definition of "dirty" (`_common.tree_state()`)
Used by preflight, the wheel/sdist manifest, the platform manifests and reconciliation: modified tracked
files, or untracked files inside shipped paths, make the tree dirty; untracked files elsewhere are recorded
(`tree_state.untracked_other`) but do not block. RELEASE mode additionally requires every staged build's
commit to equal HEAD (`reconcile_platforms.py --expect-commit HEAD`), so a build made before a later commit
must be redone.
