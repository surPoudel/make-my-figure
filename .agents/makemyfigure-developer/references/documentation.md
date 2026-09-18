# Documentation: layout, manuals, changelog, versions, per-plot template

Documented from the code on branch `feature/makemyfigure-developer-agent` (forked from
`main` on 2026-09-17, version `1.1.0`). Paths are relative to the repository root.

## 1. `docs/` layout

`docs/` is flat topic notes plus two subtrees:

- **Feature / topic notes** (`docs/*.md`, hand-written): data and workflow (`QUICKSTART.md`, `DESKTOP_APP.md`, `EXAMPLE_DATA.md`, `DATA_TEMPLATES.md`, `MULTI_SHEET_EXCEL.md`, `RAW_COUNTS_TUTORIAL.md`), plot-type requirements (`PLOT_TYPE_REQUIREMENTS.md`, `V0_4_NEW_PLOT_TYPES.md`), per-feature plot docs (`NETWORK_GRAPH.md`, `HIERARCHICAL_CLUSTERING.md`, `VOLCANO_ANNOTATIONS.md`, `HEATMAP_HIGHLIGHTING.md`, `ANNOTATIONS.md`, `STATISTICAL_ANNOTATIONS.md`, `STATISTICAL_ANNOTATION_FORMATTING.md`), statistics (`STATISTICS.md`, `FEATURE_LEVEL_STATISTICS.md`, `COUNT_MODEL_DE_INVESTIGATION.md`), matrix workflow (`MATRIX_WORKFLOW.md`, `PREPROCESSING_QC.md`, `NORMALIZATION_METHODS.md`, `INTERNAL_STANDARD_NORMALIZATION.md`, `TRANSFORMATIONS.md`), recommendations (`RECOMMENDED_FIGURES.md`, `PLOT_RECOMMENDATIONS.md`), style/export (`PUBLICATION_STYLE.md`, `STYLE_PROFILES.md`, `PLOT_STYLE_CONTROLS.md`, `STYLE_REFERENCE_AUDIT.md`, `EXPORTING_PUBLICATION_FIGURES.md`, `MULTI_PANEL_FIGURES.md`, `IMPORT_EXTERNAL_PANELS.md`, `POP_OUT_PANELS.md`), QC (`PUBLICATION_QC.md`, `V0_5_PUBLICATION_QC_PLAN.md`, `PUBLICATION_BENCHMARKS.md`, `CROSS_PLATFORM_QC.md`, `CROSS_PLATFORM_UI_QC.md`, `WINDOWS_PERFORMANCE.md`), release engineering (`BUILD_INSTALLERS.md`, `CODE_SIGNING.md`, `RELEASE_CHECKLIST.md`, `REPO_EXCLUSIONS.md`, `RELEASE_NOTES_v0.2.md`, `RELEASE_NOTES_v1.0.0.md`, `RELEASE_NOTES_v1.1.0.md`), and per-release "what's new"/plan notes (`V0_5_NEW_FEATURES.md`, `V0_6_NEW_FEATURES.md`, `V0_6_IMPLEMENTATION_PLAN.md`, `V0_6_PUBLICATION_STYLE_LESSONS.md`).
- **`docs/releases/<tag>/`** — release audit trail; on main only `v1.1.0/` (`release_v1.1.0_audit.md` + branch-audit CSV, SHA256 lists).
- **`docs/manuals/`** — the two manuals, their assets and the audit CSVs (below).

Absent on main: `docs/manual_assets/` and `docs/manual_audit/` (those names appear only as untracked dirs in another working copy; the tracked equivalents are `docs/manuals/assets/` and `docs/manuals/audit/`). There is no `mkdocs`/Sphinx site.

## 2. Manuals (`docs/manuals/`) and how they are built

```
docs/manuals/
  Quick_Start/MakeMyFigure_Quick_Start.src.md   <- the SOURCE you edit
  Quick_Start/MakeMyFigure_Quick_Start.md       <- generated (banner + src)
  Quick_Start/MakeMyFigure_Quick_Start.{docx,pdf}
  User_Manual/parts/01_..05_*.md                <- SOURCES (03_plot_catalog.md is generated)
  User_Manual/MakeMyFigure_User_Manual.{md,docx,pdf}   <- generated
  assets/{diagrams,figures,screenshots}/        <- all tracked
  audit/{current_capabilities.md, known_documentation_limitations.md,
         manual_instruction_validation.csv, screenshot_inventory.csv,
         v1.1.0_documentation_validation.csv}
```

`scripts/build_manuals.py` (needs `pandoc`, `PyMuPDF`, `markdown`):

- `banner(title)` injects **MakeMyFigure version** (`make_my_figure_core.version.__version__`), **commit** (`build_info()["commit"]`) and today's **date** at the top of both manuals.
- `assemble_user_manual()` concatenates `User_Manual/parts/*.md` in name order and re-anchors `](../../assets/` links to `](../assets/`.
- `stamp_quick_start()` writes `.md` from `.src.md`.
- `build_docx()` runs pandoc (`--toc`, implicit figures); `build_pdf()` typesets with PyMuPDF Story (`render_story`) — no LaTeX. `main()` prints page and image counts.

Supporting scripts (all write only inside `docs/manuals/`):

| Script | Needs | Writes |
|---|---|---|
| `scripts/build_plot_catalog_part.py` | registry, `ui_hints`, capabilities, examples | `User_Manual/parts/03_plot_catalog.md` (Part X, generated; hand prose only in its `PURPOSE`/`STATS_PLOTS`/`LIMITS` dicts) |
| `scripts/build_manual_diagrams.py` | matplotlib only | `assets/diagrams/*.png|svg` (contains a hard-coded plot count in a box label) |
| `scripts/manual_capture_desktop.py` | PySide6, `QT_QPA_PLATFORM=offscreen`, `MAKE_MY_FIGURE_PRESETS` temp dir | `assets/screenshots/*.png` + `desktop_capture_log.json`; drives the real `MainWindow`, replaces `QDialog.exec` with grab-and-cancel |
| `scripts/manual_capture_streamlit.py` | running Streamlit on `:8501` (`MMF_STREAMLIT_URL`), Playwright Chromium | `assets/screenshots/*.png` + `streamlit_capture_log.json` |
| `scripts/manual_screenshot_inventory.py` | the capture logs + manual sources | `audit/screenshot_inventory.csv` |
| `scripts/manual_validate_instructions.py` | offscreen Qt, Streamlit `AppTest` | `audit/manual_instruction_validation.csv` (PASS/FAIL per documented instruction; `record`/`step` helpers) |
| `scripts/validate_documented_workflows.py` | controller + core only | `audit/v1.1.0_documentation_validation.csv` (**file name is version-specific**; `OUT` is hard-coded — rename for the next release) |

The order used for v1.1.0 is written in `docs/manuals/audit/known_documentation_limitations.md` → "Rebuilding": capture desktop → capture streamlit → catalogue part → validate instructions → screenshot inventory → `build_manuals.py`. The catalogue figures in `assets/figures/` are **not** produced by any of these; see `examples-gallery.md` §5.

`docs/manuals/audit/current_capabilities.md` is the fact table ("impl / tested / desktop / browser / documented / limitation") that the manuals were written against; keep it in step when a feature changes.

## 3. `CHANGELOG.md` conventions

- Top-level `# Changelog`, then `## Unreleased` **before** the explanatory paragraph ("All notable changes … single, evolving `Publication` style"), then one `## [x.y.z] — <headline>` per release, newest first (`[1.1.0]`, `[1.0.0]`, `[1.0.0-rc1]`, `[0.6.1]`, `[0.6.0]`, `[0.5.3]` …).
- Sub-sections actually used: `### Added`, `### Changed`, `### Fixed`, `### Validation`, `### Documentation`, `### Packaging`, `### Notes`, `### Integrity`, and topical variants like `### Added — plot types`, `### Added — annotations`, `### Changed — annotations & clustering on existing plots`, `### Added — desktop`, `### Added — supporting`.
- Style: bullet per change, bold lead phrase, backticked identifiers (`presets.py`, `histogram_distribution`, option names), short justification of *why*, and cross-references to the report or doc that proves it (`reports/figure_preset_qc/`, `docs/releases/...`). New plot types are recorded as **Added** with their registry key and the input forms/options they accept.
- The `Unreleased` block currently holds two bullets (licence bundling; dependency bounds + `requirements-lock.txt`). Add new work there; move to a versioned header at release time together with the `version.py` bump.

## 4. README plot list and other count-bearing places

`README.md` §3 "What you can make" opens with a bold plot-type count and lists types grouped by family (Comparisons, Distributions, Relationships, Time/trajectory, Matrix & omics-style, Statistical/model, Genomics-style, Composition/set/flow/network, Other). Line 9 has a shields.io badge with the count; §10 Limitations names the three types whose label placement is unseeded. When a plot type is added: update the badge, the count sentence, and the family bullet.

Other hard-coded counts that must move together: `tests/test_renderers_m2.py` and `tests/test_desktop_controller.py` (registry size assertions), `scripts/build_manual_diagrams.py` (box label), the generated header of `docs/manuals/User_Manual/parts/03_plot_catalog.md` (re-run the script), and `docs/manuals/audit/current_capabilities.md` prose.

## 5. Where version strings appear (current: `1.1.0`)

Single source of truth: `make_my_figure_core/version.py::__version__`. Everything else must read it or be updated by hand.

Reads it programmatically (no edit needed):
- `pyproject.toml` `[tool.setuptools.dynamic] version = { attr = "make_my_figure_core.version.__version__" }`
- `apps/desktop_app/controller.py` (`version = __version__`), `apps/desktop_app/main.py` (About/diagnostics, status-bar `build_banner()`), Streamlit sidebar banner
- `scripts/build_windows.ps1`, `scripts/build_macos.sh`, `scripts/build_linux.sh` (shell out to Python for `VER`); `packaging/windows_installer.iss` receives it from the PowerShell script
- `scripts/build_manuals.py` banner

Hand-maintained literals that contain the version (grep hits for `1.1.0` on this commit):
- `README.md` — badge (line ~6), installer table and file names (`MakeMyFigure-1.1.0.dmg`, `-Setup.exe`, `-windows.zip`, `-linux-x86_64.tar.gz`, `.AppImage`), the status-bar example, the wheel name in §2, and the citation in §11 (`Make My Figure v1.1.0`, release tag URL).
- `requirements-lock.txt` header comment.
- `CHANGELOG.md` release header `## [1.1.0]` (and a future `Unreleased` → `[x.y.z]` move).
- `docs/RELEASE_NOTES_v1.1.0.md` (per-release file; a new release gets a new file, README §8/§11 link updated).
- `docs/releases/v1.1.0/*` (audit trail; new dir per release).
- `docs/manuals/**/*.md|docx|pdf` (banner injected at build time), `docs/manuals/audit/known_documentation_limitations.md` and `current_capabilities.md` ("Version documented/audited: 1.1.0"), the `v1.1.0_documentation_validation.csv` file name and its `version_current` column, and `scripts/validate_documented_workflows.py::OUT`.
- `.github/workflows/build_desktop_releases.yml` mentions `v1.1.0` only as an example tag in the `workflow_dispatch` input description.
- `mock_data/plot_schema_manifest.json` carries an old `"version": "0.1.0"` — historical, not the app version.

`tests/test_style_leaks_and_version.py` and `tests/test_release_guardrails.py` guard some of this (journal-name leaks, single visible style, no R runtime dependency); `docs/RELEASE_CHECKLIST.md` §1 says "update the version in one place".

## 6. Per-plot documentation template

There is no single canonical per-plot page on main; a plot type is documented in up to four places with different shapes:

1. **`docs/PLOT_TYPE_REQUIREMENTS.md`** — `### <Display name>  (\`<registry_key>\`)`, one-sentence use case, `**Required columns:**` list, `**Optional columns:**` list. Covers the original types; v0.4 types are in the table in `docs/V0_4_NEW_PLOT_TYPES.md` (`| Plot type (id) | Use case | Required | Optional | Notes / limitations |`); v0.5 types have their own files. **Gaps on this commit:** `histogram_distribution` is documented only in `CHANGELOG.md` and the generated manual catalogue — no `docs/*.md` mentions it; and `PLOT_TYPE_REQUIREMENTS.md` entries still list `**Recommended styles:** nature_like, science_like, cell_like`, which contradicts the single-Publication-style policy enforced by `tests/test_release_guardrails.py`. Fix both when next editing the file.
2. **Per-feature doc** (pattern from `docs/NETWORK_GRAPH.md`, `docs/HIERARCHICAL_CLUSTERING.md`): `# <Name> (vX.Y)`, then `## Input` / `## Input modes`, `## Options` or `## Style controls`, behaviour sections, `## Exporting …`, `## Validation / friendly errors`, `## Limitations / TODO`.
3. **Generated catalogue entry** (`scripts/build_plot_catalog_part.py::section`): Registry key · Purpose · When to use · Required/optional input (example columns) · Column mapping (+ example mapping JSON) · Statistics supported · Colour controls · Annotation controls · Axis controls · Legend/colorbar controls · Plot-specific controls (style scope) · Analytical options (config scope) · Recommended export · Figure preset support · Example data path · Known limitations · figure.
4. **Example README** (`examples/by_plot_type/<slug>/README.md`, generated by `generate_example_data._readme`): columns, how to replace with your own data, common mistakes.

Recommended template for a new plot type's `docs/<PLOT>.md` (mirrors the catalogue so the two do not contradict):

```
# <Display name> (`<registry_key>`)          # what it shows, one paragraph
## Required data                              # long/wide form, one row per …, aux table?
## Column mapping                             # each ui_hints.COLUMN_FIELDS key, multi-select flags
## Options                                    # ui_hints.OPTIONS keys, scope (style|config), defaults
## Statistics                                 # supported tests / "none on figure"; how p-values are read
## Customization                              # palette/colormap, legend, axes overrides, annotations
## Example                                    # examples/by_plot_type/<slug>/, plotspec.json snippet
## Export & reproducibility                   # vector text, PlotSpec sidecar, preset behaviour
## Limitations
```

Keep every option name identical to `ui_hints.OPTIONS[plot_type]` and every mapping key identical to `ui_hints.COLUMN_FIELDS[plot_type]`; the catalogue is generated from those, so a mismatch is immediately visible in the manual.

## 6a. Docs known to be stale on this commit

Found while cross-checking prose against code on 2026-09-17; fix opportunistically, and
do not copy their claims into new text:

- `docs/RECOMMENDED_FIGURES.md` schema table — MA, Manhattan/Q-Q, dose-response,
  network graph and paired slopegraph are now real recommendations (see
  `recommendations.md` §3).
- `docs/PLOT_TYPE_REQUIREMENTS.md` — `**Recommended styles:** nature_like, science_like,
  cell_like` lines contradict the single Publication style; `histogram_distribution`
  has no entry anywhere under `docs/*.md`.
- `docs/V0_5_PUBLICATION_QC_PLAN.md` and `docs/PUBLICATION_BENCHMARKS.md` mention
  "37 types" / "no renderer for Manhattan, network, dose-response" — historical.
- `docs/PLOT_RECOMMENDATIONS.md` documents the matrix-workflow recommender despite
  its generic name; `docs/RECOMMENDED_FIGURES.md` is the table recommender.
- `scripts/validate_documented_workflows.py::OUT` and the CSV it writes are named for
  `v1.1.0`; the next release needs a rename or a version-derived file name.
- `mock_data/plot_schema_manifest.json` still says `"version": "0.1.0"` and covers only
  the early plot types — it is a test fixture index, not a catalogue.

## 6b. Docs touch list when a plot type is added or changed

In addition to the code/test/example checklist in `examples-gallery.md` §7:

1. `CHANGELOG.md` → `## Unreleased` → `### Added` (or `### Changed`/`### Fixed`), with
   the registry key and every new option name.
2. `README.md` §3 family bullet, the bold count sentence, and the plot-types badge;
   §10 if the renderer has a documented limitation (e.g. unseeded label placement).
3. `docs/PLOT_TYPE_REQUIREMENTS.md` (or a new `docs/<PLOT>.md` using the §6 template,
   linked from `PLOT_TYPE_REQUIREMENTS.md`'s header note and README §8).
4. `scripts/build_plot_catalog_part.py` dicts (`PURPOSE`, `LIMITS`, `STATS_PLOTS`),
   then regenerate Part X and the manual (`documentation.md` §2 order).
5. `docs/manuals/audit/current_capabilities.md` row(s) for the feature, and
   `docs/manuals/User_Manual/parts/02_*` §22 "Roles by plot family" if a new mapping
   role or family appears.
6. `docs/RECOMMENDED_FIGURES.md` only if a recommendation rule was added.
7. `docs/STATISTICS.md` / `docs/STATISTICAL_ANNOTATIONS.md` if the plot gains on-figure
   statistics; `docs/PLOT_STYLE_CONTROLS.md` if it introduces a new style-scoped option.
8. Release time: `docs/RELEASE_NOTES_v<x.y.z>.md`, `docs/releases/v<x.y.z>/`, README
   installer table and citation, `requirements-lock.txt` header — after bumping
   `make_my_figure_core/version.py`.

## 7. Documentation checks that exist as tests

- `tests/test_examples.py::test_readme_per_plot_exists` — example READMEs.
- `tests/test_style_capabilities_audit.py` — capability declarations agree with renderer source (the catalogue's colour facts depend on this).
- `tests/test_release_guardrails.py` — no journal-style names in visible text, no RNA-seq/journal labels in matrix UIs.
- `tests/test_publication_recreation_manifest.py`, `tests/test_one_publication_recreation.py`, `tests/test_ten_publication_recreation.py` — benchmark reports exist and avoid over-claims.
- Absent on main: a test that README's plot list, badge, `PLOT_TYPE_REQUIREMENTS.md`, and the registry agree; a link checker for `docs/`; a check that `CHANGELOG.md` has an `Unreleased` block.

## Verify this is still current

```bash
grep -n "__version__ =" make_my_figure_core/version.py
grep -rn "1\.1\.0" README.md requirements-lock.txt CHANGELOG.md scripts/validate_documented_workflows.py | head
grep -n "^## \|^### " CHANGELOG.md | head -12
ls docs/manuals/User_Manual/parts docs/manuals/audit && grep -n "^def " scripts/build_manuals.py
```
