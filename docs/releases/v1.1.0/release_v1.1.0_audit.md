# MakeMyFigure v1.1.0 — release audit

Written on the integration branch `release/v1.1.0-integration` before it was merged into
`main`. Every statement below is backed by a command that was actually run on 2026-09-06; the
commands are given so the audit can be repeated on the tagged commit.

## 1. Scope and provenance

| Item | Value |
|---|---|
| Previous stable release | `v1.0.0` (52360b9) |
| Base of the integration branch | `main` at 7c8b5a5 (identical to `origin/main`) |
| Integration branch | `release/v1.1.0-integration` |
| Version string | `make_my_figure_core/version.py` → `1.1.0` (single definition; `pyproject.toml` reads it dynamically) |
| Branch/commit audit | `docs/releases/v1.1.0/release_v1.1.0_branch_audit.csv` (91 commit rows across 18 candidate branches) |

Integration method, per commit class in the branch audit:

- `fix/collaborator-concerns-c1-c3` (19 commits, software/tests/benchmark/packaging only): fast-forward merge.
- Software commits that lived on figure-working branches: cherry-picked with `-x` (five from
  the Figure 4 branch, five from the Figure 5 branch; four textual conflicts resolved keeping
  both sides — see commit messages of 253e926, 7f9fb02, 17eb340, 7433b3f, 8ec7381).
- Two mixed commits (18e46ce, a36d8d9): only the software diff was ported
  (`tests/test_band_and_axis_scale.py`, renderer changes) — the figure-working paths were never
  checked out on this branch.
- Two manuscript-only commits (f91785d, 5dc45e9): excluded.
- Renderer refinements that existed only as uncommitted edits in the figure worktrees were
  ported by hand with tests (`tests/test_v1_1_renderer_options.py`, 11 tests; commit 92fd71e).
- No manuscript branch was merged. `git log main..release/v1.1.0-integration` lists 37 commits,
  none of which touches a manuscript path.

## 2. Features verified present (live code)

| Feature | Evidence |
|---|---|
| 38 plot types | `len(available_plot_types()) == 38`; `MakeMyFigure --selftest` on all three CI runners reports "38 plot types rendered + exported" |
| 18 statistical procedures | `len(make_my_figure_core.statistics.TESTS) == 18` |
| Figure presets (style / full), preset store, import/export/delete | `presets.py`; `scripts/validate_documented_workflows.py` row "Save a Figure preset …" PASS |
| Histogram plot type | `histogram_distribution` in the registry; plot catalogue (User Manual Part X) regenerated from the registry |
| Axis-range / tick overrides, axis scales | `plots/base.apply_axis_overrides`; `tests/test_band_and_axis_scale.py` |
| Multi-sheet Excel workbook browser | `io/workbook.py`; validation row "Open a multi-sheet workbook …" PASS (9-sheet bundled fixture, sheet switch, provenance) |
| Matrix workflow (MatrixSpec → metadata → PreprocessingSpec → PCA / heatmap) | validation row "Matrix workflow smoke path" PASS; original matrix unchanged (`df.equals`) |
| Figure Builder + FigureSpec rebuild | validation row "Figure Builder …" PASS |
| Export formats PNG / TIFF / PDF / SVG / EPS + PlotSpec sidecar | validation rows 1–2 PASS; SVG text kept as text |
| Packaged resources inside the wheel | fresh-venv smoke: schemas resolved from `site-packages/make_my_figure_core/_bundled/schemas` |

## 3. The seven R-validated fixes

All present on the integration branch (commit 7fdee5e via the fix branch) and pinned by
`tests/test_r_validation_regressions.py`:

```
python -m pytest tests/test_r_validation_regressions.py -q -p no:pytest-qt
7 passed in 10.25s
```

1. r × c Fisher's exact test: seeded Monte Carlo, 200,000 resamples, method recorded.
2. ROC AUC — tied scores collapsed to one operating point (order-independent).
3. Average precision — same tie handling.
4. Quantile normalisation — Bolstad/limma average-rank tie handling.
5. `voom` — unscaled prior (voom definition), not a library-size-scaled prior.
6. Mann–Whitney effect size sign in the feature-level summary.
7. Last-bit near-ties in rank tests treated as ties.

## 4. R validation benchmark (`benchmarks/r_validation/`)

Re-run against the release-candidate code (commit 92fd71e; the Python side re-executed, R
reference outputs re-used from `results/R/`, `benchmark_manifest.json` records the commit and
timestamps). Totals from `FINAL_VALIDATION_MATRIX.csv`:

| Class | Count |
|---|---|
| Comparisons | 2,625 |
| EXACT | 2,491 |
| NUMERICALLY_EQUIVALENT | 34 |
| ACCEPTABLE_IMPLEMENTATION_DIFFERENCE | 53 |
| UPSTREAM_INPUT_DIFFERENCE | 43 |
| NOT_COMPARED | 4 |
| METHOD_MISMATCH | 0 |
| FAIL | 0 |
| NEEDS_REVIEW | 0 |

The only change against the previous run is one additional plot-derived metadata key
(`ma_plot.lfc_cutoff`); the class totals are unchanged. The feature-level screen is compared
with limma-voom, edgeR and DESeq2 as concordance only; no claim of full limma-voom equivalence
is made anywhere in the code, README, changelog or manuals (checked with `git grep -i voom`).

## 5. Test suite

Host: Linux (WSL2), Python 3.11, Qt offscreen via conda-forge runtime libraries.

| Run | Command | Result |
|---|---|---|
| Full suite | `python -m pytest -q -p no:pytest-qt --ignore=tests/test_desktop_gui.py` | **1644 passed, 5 skipped, 0 failed, 0 xfail** (952 s) |
| Desktop GUI module | `LD_LIBRARY_PATH=<qt libs> QT_QPA_PLATFORM=offscreen python -m pytest tests/test_desktop_gui.py -v` | **41 passed, 0 failed** (see §5a) |
| R-validation regressions | `python -m pytest tests/test_r_validation_regressions.py -q` | 7 passed |
| v1.1 renderer options | `python -m pytest tests/test_v1_1_renderer_options.py -q` | 11 passed |
| Release guardrails | `python -m pytest tests/test_release_guardrails.py -q` | 6 passed |

The 5 skips are optional-dependency guards (`count-de` extra message path, statsmodels/fitz/
openpyxl `importorskip` guards) — none is a disabled failing test.

### 5a. GUI tests

The Qt GUI module (41 tests) first hung at `test_define_groups_matrix_to_long`: the test built a
3-row toy matrix whose four numeric columns have at most three distinct values each, so the
value/annotation classifier (in place since v1.0.0, commit a4e99c2) treats them as annotation
columns, no groups are guessed, and the dialog's Accept shows a modal warning that blocks under
the offscreen platform. The test also asserted equality of two empty strings. It was repaired to
use a 12-row intensity matrix and to press *Guess groups* explicitly (the dialog never guesses
silently). A second test, `test_open_plotspec_reproduces_benchmark_panel`, hard-coded
`ridge_or_density_plot` for a benchmark panel that commit b894de3 (also in v1.0.0) had corrected
to a scatter plot; it now reads the expected plot type and roles from the PlotSpec it opens. No
application code changed for either. Final run of the whole module: **41 passed, 0 failed (296 s)**.

## 6. Documentation gate

| Check | Result |
|---|---|
| README counts vs code | 38 plot types, 18 statistical procedures — both read from the live registries |
| Quick Start | native install first (DMG / Setup.exe / tar.gz-AppImage), then source install; WSL2 as a separate row |
| User Manual | 27 parts / 77 numbered sections; installation per platform (§9 macOS, §10 Windows, §11 Linux, §12 WSL2); Figure presets §53–60 including the dataset A → preset → dataset B walkthrough and categorical colour behaviour; Matrix workflow Part VII–VIII; statistics Part IX (voom described as a transform only; quantile ties); multi-sheet Excel Part XVIII; Figure Builder Part XVI with the raster-panel / vector-text limit; export formats Part XVII (PNG/TIFF/PDF/SVG/EPS) |
| Screenshots | 34 screenshots recaptured from the running v1.1.0 apps (desktop 23/23, browser 11/11), bundled synthetic data only; `docs/manuals/audit/screenshot_inventory.csv` 34 rows, all OK; no private path in any capture log |
| Workflows actually executed | `docs/manuals/audit/v1.1.0_documentation_validation.csv` — 8/8 PASS (`scripts/validate_documented_workflows.py`); `manual_instruction_validation.csv` — 22/22 PASS |
| PDFs | `MakeMyFigure_Quick_Start.pdf` 14 pages / 14 figures; `MakeMyFigure_User_Manual.pdf` 80 pages / 72 figures; every page rendered and inspected (cover, contents, page numbers, headings, screenshots, captions, code blocks); no image extends beyond the page; no near-empty page; no `1.0.0`, local path or private term in the text; the cover em-dash defect (rendered as `?` by the base Helvetica font) was fixed by using DejaVu Sans for cover and footer |
| Release copies | `MakeMyFigure_v1.1.0_Quick_Start.pdf`, `MakeMyFigure_v1.1.0_User_Manual.pdf` (byte copies of the committed PDFs, attached to the GitHub Release) |

## 7. Packaging gate

| Artefact | How built | Evidence |
|---|---|---|
| `make_my_figure_core-1.1.0-py3-none-any.whl`, `make_my_figure_core-1.1.0.tar.gz` | `python -m build` from the integration branch | fresh venv install → version 1.1.0, 38 plot types, exports PNG/PDF/SVG/TIFF/EPS, resources resolved from site-packages |
| `MakeMyFigure-1.1.0.dmg` (the `-macos.zip` is only a fallback when hdiutil fails; not produced) | GitHub Actions macOS runner | workflow_dispatch run 34043384212 — job success; `--selftest` "SELFTEST OK: 38 plot types rendered + exported; statistics OK" |
| `MakeMyFigure-1.1.0-Setup.exe`, `-windows.zip` | GitHub Actions Windows runner (Inno Setup) | same run — job success; `MakeMyFigure.exe --selftest` step exit 0 (the windowed executable prints no console output) |
| `MakeMyFigure-1.1.0.AppImage`, `MakeMyFigure-1.1.0-linux-x86_64.tar.gz` | GitHub Actions Ubuntu runner | same run — job success; "SELFTEST OK" |

No new build tooling was introduced; the existing `scripts/build_*.{sh,ps1}`,
`packaging/make_my_figure.spec`, `packaging/windows_installer.iss` and
`.github/workflows/build_desktop_releases.yml` were version-stamped only. The installers for the
release are rebuilt from the `v1.1.0` tag by the same workflow, which uploads them to the
GitHub Release; `SHA256SUMS.txt` is computed from the downloaded release assets afterwards.

Staged asset checksums (wheel, sdist, manuals) at the time of writing:

```
d9ac22bc79db1fa02b2757c6693287b34253d003a22fae76947338c3381fb3c5  MakeMyFigure_v1.1.0_Quick_Start.pdf
20e244a5aa89c4331e9784f9314163dc6f4d58e394573864ca4046ecb363543b  MakeMyFigure_v1.1.0_User_Manual.pdf
d9ef415047b28ec6f57c042d24559776bd0cafec6dd5f1a7be8aa96a5b782a38  make_my_figure_core-1.1.0-py3-none-any.whl
46c99eb94f21657d20bb5facdb68e5b05c13158e8090b766d25b07ab1bc7c6fe  make_my_figure_core-1.1.0.tar.gz
```

## 8. Privacy and repository-content audit (integration branch)

Commands: `git ls-files`, `git ls-files | grep -i -E "manuscript|JUMP|Concerns|PRIVATE_REFERENCE|EndNote|\.enl|claude|prompt|\.ttf|\.otf|publisher"`,
`git grep -n -i -E "manuscriptv[0-9]|JUMPlib|JUMPptm|PRIVATE_REFERENCE_ONLY|<local-user>|OneDrive|/mnt/c/Users"`.

Findings and actions:

- No manuscript draft, Results/Methods/Discussion text, figure working folder, publisher
  figure, writing template, EndNote library, citation/editorial audit, private dataset or font
  file is tracked.
- `claude_code/CLAUDE_CODE_MASTER_PROMPT.md`, `claude_code/LAUNCH_PROMPT_SHORT.md` and
  `CLAUDE.md` (assistant instruction files, tracked since before v1.0.0) were removed from the
  tree and git-ignored (commit 1cd2a0b). They remain in the local checkout only.
- `benchmarks/r_validation/reports/METHODS_FOR_MANUSCRIPT.md` (a methods-text draft) was
  removed from the tree and git-ignored; `results/manuscript_validation_table.csv` was renamed
  `validation_summary_table.csv` (content unchanged, references updated).
- The committed cross-platform QC manifest contained the local user path; it was redacted and
  the QC script now writes `<redacted>`.
- `reports/collaborator_concerns/` (six diagnostic notes about a collaborator's unpublished
  workbooks, quoting their messages and describing the workbook structure) was removed from the
  tree and git-ignored; the C1–C3 fixes themselves are covered by tests in `tests/`.
- `docs/manual_audit/` (a stale duplicate of `docs/manuals/audit/` from the first documentation
  run) was removed from the tree; `docs/manuals/audit/` was updated to v1.1.0.
- Remaining matches of "OneDrive" / "/mnt/c" are generic performance advice about cloud-synced
  folders (desktop app warning, docs), not local paths. `reports/collaborator_concerns/*.md`
  mention the untracked `Concerns/` folder only to state that nothing from it is tracked.
- `dist/` wheels are untracked; `benchmarks/r_validation/results/R/*.rds` and the manual PDF
  build cache are git-ignored.

## 9. Gate summary

| Gate | Status |
|---|---|
| Software-only integration (no manuscript branch merged) | PASS |
| Features present | PASS |
| Seven R-validated fixes + regression tests | PASS |
| R benchmark re-run, 0 FAIL / 0 NEEDS_REVIEW | PASS |
| Full test suite | PASS (1644 passed, 5 skipped) |
| Version 1.1.0 in the single source of truth | PASS |
| CHANGELOG / README / release notes | PASS |
| Documentation gate (manuals, screenshots, workflow validation, PDFs) | PASS |
| Packaging gate (wheel/sdist smoke; native builds + self-test on three runners) | PASS |
| Privacy audit | PASS after the actions in §8 |

Only after the gates above passed was the integration branch merged into `main` and the
annotated tag `v1.1.0` created.
