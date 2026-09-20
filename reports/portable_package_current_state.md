# Portable figure package — current state of the live code (v1.1.0, commit 8fc78e9)

Audit date: 2026-09-11. Branch `feature/portable-figure-package-v1.1.1` (worktree `make_my_plot_v111`), created from `main` at
`8fc78e9` with a clean status. Every statement below was read from the code, not from the manuals or the manuscript.
File references are relative to the repository root.

## 1. What every specification contains today

| Record | Where defined | Shape | What it holds | What it does not hold |
|---|---|---|---|---|
| **PlotSpec** | plain `dict`; JSON Schema `schemas/plot_spec.schema.json`; validator `make_my_figure_core/spec/validate.py:60` | required `plot_type`, `input_table`, `mapping`, `journal_style`, `output`; optional `layout`, `statistics`, `source`, `annotations`, `column_annotations`; undeclared `style` written by both apps (root has no `additionalProperties: false`) | plot type, column roles and options, style overrides, layout, statistics *configuration*, manual annotations, worksheet provenance (`source`), click-to-label picks | any row values; a resolvable data path; any checksum of a CSV/TSV; statistics *results*; software version |
| **StatsSpec** | `dict`; `make_my_figure_core/statistics/schemas.py` (`default_stats_spec`, `normalize_stats_spec`, `stats_sidecar_payload`) | config keys (`test`, `comparison_mode`, `correction`, `alpha`, columns, `annotation` block…) | embedded in the PlotSpec under `statistics` (config only) **and** written as `<base>.stats_spec.json` (config + `results` list of `StatResult.to_dict()`, method paragraph, versions) | nothing reads the results back: `StatResult.from_dict`/`StatsReport.from_dict` have **zero callers**; `render()` always recomputes (`plots/stats_integration.py:47-53`) |
| **MatrixSpec** | `@dataclass`, `matrix_workflow/matrix_spec.py:29` | `source_file`, `source_workbook`, `source_sheet`, `feature_id_column`, `value_columns`, `value_type`, policies, `app_version` | in memory only (desktop wizard attribute, Streamlit session state) | never written to disk by any export |
| **SampleMetadataSpec** | `@dataclass`, `matrix_workflow/metadata_spec.py:21` | `sample_id_column`, `group_column`, `batch_column`, `paired_id_column`, `covariate_columns`, `sample_to_group` | in memory only | never written; the PlotSpec keeps only `source.source_metadata.{group_column, groups, source_metadata_id}` — the sample→group map is dropped |
| **PreprocessingSpec** | `@dataclass`, `matrix_workflow/preprocessing_spec.py:42` | ordered `preprocessing_steps` with method, parameters, QC before/after, `source_matrix_id`, `output_matrix_id` (literal `"processed"` by default) | in memory only; QC report writes prose (`preprocessing_reports.py:137`) | never written as JSON; the PlotSpec keeps one prose `method_sentence()` string + a 12-hex hash of that sentence (`plots/handoff.py:112-116`) |
| **FigureSpec** | `panels/models.py` (`Panel`, `FigureLayout`, `MultiPanelFigure`) + `panels/builder.py:336` `multipanel_sidecar` | `{"figure": {name, panels[], layout, legend_text}, "draft_legend", "disclaimer"}`; each panel embeds its `plot_spec`, `stats_spec`, sizes, `image_path` (basename), `image_meta` | written by the desktop Figure Builder "Save figure…" | **panel tables are not serialised** (`has_prerendered_figure` bool only); `panel_from_dict` has no GUI caller; no "Open FigureSpec" exists |
| **Figure Preset** | `presets.py` (`PRESET_EXTENSION = ".mmfpreset.json"`, layout preset `.mmflayout.json`) | reusable style/config, format-versioned, `preset_contains_data()` refuses data | — | correct as designed: no data, no table name, no provenance |

## 2. What every export mode writes

Desktop (`apps/desktop_app/main.py:542-556`, handlers `export_single` 2870-2899, `export_zip` 2902-2918):

| Action | Files | Specs included |
|---|---|---|
| Export SVG / PNG / PDF | one figure file | **none** (no sidecar) |
| Export PlotSpec JSON | `<stem>.plot_spec.json` = `{"plot_spec": …, "render_metadata": …}` | PlotSpec only |
| Save PlotSpec (Home-dialog button, 1847-1861) | `<plot_type>.plot_spec.json` = **bare** spec dict | PlotSpec only — a *different shape* from the export above |
| **Export all as ZIP** | `<stem>.svg`, `.png`, `.pdf`, `<stem>.plot_spec.json`, `<stem>.stats_spec.json` (only when `result.stats_report` exists) via `registry.export_bundle_bytes` (`plots/registry.py:519-551`) | PlotSpec, StatsSpec. **Not** MatrixSpec, SampleMetadataSpec, PreprocessingSpec, FigureSpec, and **no data** |
| Figure Builder "Save figure…" (`stats_panel.py:909-952`) | `<base>.<ext>`, `.svg`, `.pdf`, `<base>.figure_spec.json`, `figure_builder_assets/` | FigureSpec with embedded panel PlotSpecs; no tables |
| Matrix wizard "Save before/after QC report" | PNG/PDF/SVG plots, `qc_summary.csv`, `preprocessing_report.md` | prose only |
| Save Figure preset | `<name>.mmfpreset.json` in the user preset library | preset (no data) |

Streamlit (`apps/streamlit_app/streamlit_app.py:1286-1314`): SVG, PNG, PDF, `plot_spec.json` (sidecar shape), `stats_spec.json` when statistics ran. **No ZIP export, no FigureSpec.**

The manual statements "Every export writes `name.plot_spec.json`" and "Export all as ZIP (every format incl. TIFF/EPS plus sidecars)" are not what the desktop code does: single-format buttons write no sidecar, and the ZIP is hard-coded to svg/png/pdf.

## 3. What PlotSpec reload requires

`DesktopController.load_plotspec` (`apps/desktop_app/controller.py:164-196`) and `MainWindow.action_open_plotspec` (`main.py:1708-1749`):

1. The JSON must have a top-level `plot_type` — so the file written by the app's own "Export PlotSpec JSON" button (`{"plot_spec": …}`) is **rejected** with "This file is not a PlotSpec (no 'plot_type')". Only the bare form from "Save PlotSpec" reopens.
2. The data file must exist **next to the JSON** under `basename(input_table)`, or be the only `*.csv/*.tsv/*.txt/*.xlsx/*.xls` in that folder; otherwise the user is asked to pick a file.
3. No checksum, column check or row-count check is made. A changed file of the same name renders silently.
4. For Excel sources `input_table` is `"book.xlsx [Sheet]"` (never a path) and `load_file` reopens the **active/first sheet**; the recorded `source.source_sheet_name` is not used. Multi-sheet figures can silently come from the wrong worksheet.
5. Streamlit's "Open PlotSpec" needs the user to upload both files; same absence of checks.

## 4. How source tables are identified

`input_table` is a display label, never a path: `basename(path)` for CSV/TSV, `"<workbook> [<sheet>]"` for Excel, `"<plot_type> (example)"` for bundled examples, synthetic names such as `"<name> [processed]"`, `"<name> (grouped)"`, `"<name> · <recommendation key>"` for derived tables (`controller.py:118,146,158-163,254,268,623,711`). `LoadedData.source_path` exists in memory (`controller.py:56`) but is never written to any spec.

## 5. Checksums that exist today

| Digest | Where | What it hashes |
|---|---|---|
| `source_workbook_hash` | `io/workbook.py:205-207` → `TableInfo.source_workbook_hash` → `spec["source"]` | whole **workbook file bytes**, truncated to 16 hex (64 bits); Excel sources only; written but **never compared** on reopen |
| `image_meta["sha256"]` | `figure_import.py:55-60` | imported panel asset file (full digest) |
| `source_matrix_id`, `source_metadata_id`, `source_preprocessing_id`, `source_stats_id` | `plots/handoff.py:62-122` | 12-hex hashes of *metadata strings* (column names, group names, prose sentence), not of data |

There is **no digest of any DataFrame, worksheet or CSV payload** anywhere in the core, and no checksum is checked on any load path.

## 6. Workbooks and sheets

`io/workbook.py` inspects all sheets (hidden/empty stay selectable), `load_excel_sheet` records `source_workbook_name/hash`, `source_sheet_name/index/type`, `source_header_row` in `TableInfo.provenance()`; merged-header expansion uses openpyxl merged ranges. Provenance reaches the PlotSpec `source` block and the mirrored `statistics.source`. On reload nothing consults it (see §3.4).

## 7. Derived matrices

`run_preprocessing` (`matrix_workflow/preprocessing.py:216-238`) returns the derived frame, derived MatrixSpec and PreprocessingSpec. The desktop wraps it as an in-memory `LoadedData` named `"<table> [processed]"` with no `source_path` (`controller.py:702-712`); Streamlit keeps it in `st.session_state`. The derived matrix is never written by an export; the only disk artifacts are QC report plots and prose. The identifier `output_matrix_id` is the constant `"processed"`; `PreprocessingSpec.metadata_spec_id` is never assigned.

## 8. FigureSpec panel resolution

`Panel.to_dict()` embeds `plot_spec` and `stats_spec` by value, records sizes and, for imported panels, `image_path` as a basename plus `image_meta` (with sha256). It omits `table`/`aux`. `panel_from_dict(d, assets_dir)` (`panels/builder.py:248`) restores geometry and imported images but leaves `table=None`; `_render_panel_figure` then raises "has neither a figure nor a plot_spec+table". The only GUI consumer of `figure_spec.json` is the layout-preset importer, which keeps geometry and "leaves its panels behind" (`presets.py:718-735`). Imported assets live during the session in an uncleaned `tempfile.mkdtemp` (`stats_panel.py:424-426`) referenced by absolute path, so imported panels do not survive a restart.

## 9. Behaviour when source data changed or are missing

| Situation | PlotSpec reopen today |
|---|---|
| Source file edited, same name | loads and renders the new values, no warning |
| Source file missing, one other table in the folder | that table is adopted silently |
| Source file missing, several/no tables | user is asked to choose; no verification of the choice |
| Different columns | `SpecValidationError`/`RenderError` surfaced as "Opened the PlotSpec but rendering failed" |
| Excel workbook | active sheet is used regardless of the recorded sheet |
| Derived (matrix-workflow) table | cannot be reopened at all: the processed table exists nowhere on disk |
| Composite | cannot be reopened: no tables in the FigureSpec, no GUI route |

## 10. Other facts relevant to the design

- Recent files: `QSettings("MakeMyFigure","Make My Figure")["recent_files"]`, max 8 plain paths, no type marker (`main.py:2922-2949`); dropped files go to `load_file` with no extension filter (`main.py:1285-1292`).
- Landing page: `_build_welcome` (`main.py:360-393`) with four buttons: Open data file, Use example data, Recent files, Help.
- Version: `make_my_figure_core/version.py` `__version__ = "1.1.0"`, `build_info()` gives commit/platform; the PlotSpec carries no version.
- Float handling: delimited text is parsed with `float_precision="round_trip"` (`io/loaders.py:313-322`), bit-exact against the Excel path (`tests/test_loader_float_round_trip.py`); exports use pandas default `to_csv` formatting, so a CSV written by the app is *not* guaranteed to round-trip.
- Packaging: PyInstaller one-folder, Inno Setup on Windows, DMG on macOS, tar.gz/AppImage on Linux; **no file association** of any kind exists (`.iss` has no `[Registry]`, no `CFBundleDocumentTypes`, no `MimeType=`).
- Tests: the non-GUI suite runs with `python -m pytest -q -p no:pytest-qt --ignore=tests/test_desktop_gui.py`; `tests/test_desktop_controller.py:70-78` pins the ZIP content to exactly `scatter.svg/.png/.pdf/.plot_spec.json`.
- Existing "bundle" concepts: the ZIP export, the `_bundled` resource staging, the PyInstaller `BUNDLE`. There is no reloadable container format.

## 11. Consequences for the manuscript sentence under review

"StatsSpec, PlotSpec, and FigureSpec are written alongside every export" is true only for: PlotSpec via the ZIP/Export-JSON buttons and Streamlit downloads; StatsSpec via the ZIP and Streamlit downloads when statistics ran; FigureSpec via the Figure Builder save. It is not true for the single-format desktop buttons, and none of MatrixSpec, SampleMetadataSpec or PreprocessingSpec is written anywhere. A PlotSpec never reproduces a figure on its own, and a FigureSpec cannot be reopened. See `reports/v1.1.1_manuscript_claim_audit.md` for the sentence-level audit.
