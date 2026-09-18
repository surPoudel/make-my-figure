# Visual QC: scoring, layout checks, render matrix, scientific freeze

Documented from the code on branch `feature/makemyfigure-developer-agent` (forked from
`main` on 2026-09-17, version `1.1.0`). Paths are relative to the repository root.
All QC in this codebase is **advisory**: nothing blocks render or export.

## 1. The three QC layers in the core

| Layer | Module | Entry point | Runs when |
|---|---|---|---|
| Publication readiness (v0.5) | `make_my_figure_core/qa/publication_check.py` | `check_publication_readiness(fig) -> PublicationCheckResult` | inside `registry.render` on every render; stored as `result.metadata["publication_check"]` |
| Layout QC (clipping/overlap) | `make_my_figure_core/qa/layout_qc.py` | `check_layout(fig, *, min_font_pt=6.0) -> LayoutQCReport`; `auto_fix_layout(fig, spec=None) -> list[str]` | inside `registry.render` on every render → `metadata["layout_qc"]`; auto-fix only when `spec["layout"]["auto_fix_layout"]` is set |
| Publication score (v0.6) | `make_my_figure_core/qc/publication_score.py`, `qc/auto_fix.py` | `score_publication(*, result=None, figure=None, spec=None, stats_report=None) -> PublicationScore`; `suggest_fixes(score, spec)`; `apply_fixes(spec, fix_ids)` | on demand: desktop "Publication QC" button (`apps/desktop_app/main.py`, via `controller.publication_qc`), Streamlit "Publication QC" expander, and the QC galleries |

### 1.1 `publication_check.py`

Thresholds: `MIN_LABEL_PT = 9.0`, `MIN_TICK_PT = 8.0`, figure smaller than 3.0 × 1.9 in warns. Checks: small figure; content tight-bbox > 112 % of figure size ("may be clipped in the fixed preview" — exports use `bbox_inches="tight"`); axes missing x/y labels (decorative axes are skipped when the renderer sets `ax._colorbar = True`); axis label < 9 pt; tick label < 8 pt; dense x tick labels; legend inside the axes overlapping data; weak contrast. It never mutates the figure. The memory checklist for adding a plot type says every new renderer must pass this check on its example.

### 1.2 `layout_qc.py`

Bounding-box based, "approximate and honest". `LayoutIssue(category, severity, artist, message, suggested_fix, auto_fixable)` with categories `clipping | overlap | font | density | missing_label | colorbar`; constants `_MIN_FONT_PT = 6.0`, `_OVERLAP_FRAC = 0.35`, `_CLIP_TOL_PX = 1.5`. `auto_fix_layout` is layout-only ("never changes data, colors, or statistics"): rotates crowded x tick labels to 45°, then enlarges/adjusts margins so nothing is clipped, returning the list of applied fixes which `registry.render` records under `metadata["layout_fixes"]`. Tests: `tests/test_layout_qc.py` (`test_clipped_figure_flags_clipping_with_structured_fields`, `test_auto_fix_reduces_clipping`, `test_layout_qc_never_crashes_on_any_plot_type`, …).

### 1.3 `publication_score.py` / `auto_fix.py`

`PublicationScore(level, score, checks, summary)`; `Check(id, level, message, suggestion, element)`. Score starts at 100, minus `_WARN_PENALTY = 12` per warn and `_FAIL_PENALTY = 30` per fail. Thresholds: `MIN_EXPORT_DPI_WARN = 300`, `MIN_EXPORT_DPI_FAIL = 150`, `MIN_PANEL_DPI = 200`, `HEATMAP_ROW_LABEL_WARN = 60`, `VOLCANO_LABEL_WARN = 40`, `GENERIC_TICK_WARN = 30`. Check ids: `missing_axis_labels`, `readability`, `legend_overlap`, `tick_density` (folded in from `publication_check`), `export_dpi`, `panel_resolution` (uses `panels/models.py::panel_dpi`, default 300), `low_contrast`, `heatmap_row_density`, `label_crowding`, `missing_method_report`, `missing_units`. Fix ids in `auto_fix.FIXES`: `enlarge_figure`, `legend_outside`, `hide_excess_labels`, `increase_margins`, `increase_font`, `increase_dpi`; `apply_fixes` deep-copies and never mutates the input spec (`tests/test_publication_qc.py::test_apply_fixes_does_not_mutate_input`).

Docs: `docs/PUBLICATION_QC.md` is accurate to this code (check table, fix table, "no automatic fix" list). `docs/V0_5_PUBLICATION_QC_PLAN.md` is the historical 12-area plan (statistics oracles, exports, reproducibility, GUI, docs) whose results live under `outputs/publication_qc/*.md` (tracked) — it still says "37 types"; treat its numbers as historical.

## 2. The layout engine the checks rely on

- `plots/base.py::apply_publication_layout(fig, ax, spec, style)` — applies `spec["layout"]` (tick rotation/pad, axis-label pad, title pad, margins) at the end of every render, from `registry.render`, so all plot types honour the same controls; empty layout is a no-op.
- `plots/base.py::autorotate_xticklabels(ax, style, rotation="auto")` — chooses 0/45/90° from label count and length and shrinks fonts as categories grow. This is what `tests/test_xlabel_overlap_qc.py` verifies with 20 sample-name-like labels (`_xlabels_overlap` compares adjacent tick-label window extents) across box/violin/bar/dot-strip/beeswarm/raincloud, with and without an explicit `x_tick_rotation`.
- `plots/base.py::place_legend(..., force_outside=...)`, `resolve_legend_location`, `figure_size(spec, style, aspect=...)` (mm-based `output.width_mm/height_mm` → inches) and `plots/label_policy.py` (duplicate-label policy for volcano/MA point labels) are the other shared pieces.
- `plots/stats_overlay.py` draws brackets/stars from `AnnotationItem`s and expands the y-axis so nothing clips; `plots/stats_integration.py::run_and_annotate` runs statistics once and returns the `StatsReport`. Renderers must not place brackets themselves.
- Style tokens (`styles/engine.py::StyleProfile`): `base_font_pt 11`, `axis_font_pt 12`, `tick_label_pt 10`, `legend_pt 10`, `legend_title_pt 11`, `title_font_pt 13`, `annotation_pt 9.5`, `panel_label_pt 13`, `spine_width_pt 1.1`, `line_width_pt 1.8`, `marker_size 45`, `legend_outside False`, `font_family` stack. `styles/capabilities.py` declares which of these each renderer honours; `registry.render` appends a warning for controls a plot type ignores (`warn_ignored_style_controls`), and `scripts/audit_style_capabilities.py` + `tests/test_style_capabilities_audit.py` keep the declaration truthful by scanning renderer source. The Publication style is defined in code (`styles/publication_style_engine.py`, `engine.py`); `style_profiles/` only holds the starter and learned JSONs.

## 3. Existing scripts that already do part of a render matrix

| Script | Axis it varies | Output |
|---|---|---|
| `scripts/generate_figure_qc_gallery.py` | DEFAULT vs ADJUSTED layout/annotation controls per case (`_cases()` yields e.g. `pca_small_markers`/`pca_large_markers`, `manhattan`/`manhattan_custom`, `paired_independent_colors`, `ma_labeled`, `volcano_labeled`, `clustered_heatmap`, `upset`, `swimmer`); exports PNG/PDF/SVG, counts warnings, contact sheet | `reports/figure_qc_release_candidate/{qc_summary.csv,qc_report.md}` (tracked) |
| `scripts/build_figure_preset_qc.py` | every registry type × `STYLE_CHANGES` (title 17 pt, axis 11 pt, annotation 8.5 pt, line 2.6 pt, marker 70, legend 8 pt) × `LAYOUT_CHANGES` (45° ticks, left margin, double column, legend outside right) × `OUTPUT_CHANGES` (450 dpi) × a plot-specific visual option; then a **different dataset** (`_new_dataset`: mock file or perturbed example) | `reports/figure_preset_qc/all_plot_preset_matrix.csv` with `COLUMNS` per check (`style_roundtrip`, `color_roundtrip`, `typography_roundtrip`, `layout_roundtrip`, `legend_roundtrip`, `annotation_roundtrip`, `plot_specific_roundtrip`, `new_data_safe`, `png/pdf/svg_export`, `status`, `notes`) + README (tracked); `tests/test_figure_preset_qc.py` runs the same `check_plot` per type |
| `scripts/generate_publication_qc_gallery.py`, `scripts/generate_v0_6_qc_gallery.py` | every type from its example, scored with `score_publication` | `reports/publication_qc_gallery/{qc_summary.csv,qc_report.md}` (tracked), PNGs ignored |
| `scripts/run_cross_platform_qc.py` | same renders per OS: success, artefacts, element counts, fonts/backends (no pixel diff) | `reports/release_cross_platform_qc/<platform>/` |
| `scripts/generate_style_qa_gallery.py`, `generate_v04_qa_gallery.py`, `generate_v05_qa_gallery.py`, `generate_stats_qa_gallery.py` | style profiles / release subsets / statistics examples, for eyeballing | `outputs/style_qa_gallery/`, `reports/v04_qa/` (PNGs tracked), `reports/stats_qa_gallery.png` |
| `benchmarks/publication_recreation/scripts/evaluate_recreations.py` | real-data panels; writes `qc/visual_qc.md` (exports non-empty, publication-readiness passed, iterations) and `qc/scientific_qc.md` (mapping traced to source columns, row/col counts, transforms) per panel | `benchmarks/publication_recreation/recreated_panels/<id>/qc/` (tracked) |

`tests/test_xlabel_overlap_qc.py`, `tests/test_tick_density_follows_font.py`, `tests/test_font_survives_export.py`, `tests/test_layout_and_annotations.py` are the unit-level slices of the same idea.

### 3.1 The render-matrix idea (not implemented as one script on main)

Absent on main: a single harness that renders **each plot type** across a fixed set of data-shape variants and stores a contact sheet + QC table per variant. The pieces exist (example loader, `_perturb` in the preset QC, `score_publication`, `check_layout`, contact-sheet code in the galleries), so a new script can compose them. Suggested variant axes, each rendered with Publication defaults unless the axis says otherwise:

1. **default** — the bundled example as-is (baseline, matches the manual catalogue figure).
2. **few groups / many groups** — 2 categories vs ≥ 12 categories (legend growth, palette cycling, tick rotation).
3. **small n / large n** — 3 points per group vs thousands of rows (marker overplotting, density warnings, heatmap row-label crowding at > 60, volcano label crowding at > 40).
4. **long labels** — 20+ sample-name-like categories (the `_COLS` pattern from `test_xlabel_overlap_qc.py`) and long legend entries.
5. **statistics on** — a `StatsSpec` with brackets/stars or a corner panel (bracket stacking, y-axis expansion, `missing_method_report`).
6. **presets** — style preset and full preset applied to a second dataset (reuse `build_figure_preset_qc.check_plot`).
7. **physical size** — single vs double column (`layout.column_width`), 89 mm vs 183 mm width, 300 vs 150 dpi (the `export_dpi` fail path).

Record per cell: plot type, variant, `score_publication().score/level`, `check_layout().issues` count by category, export sizes, warnings, and the PNG path; fail the run on renderer exceptions only, and diff the CSV against the committed one in review.

## 4. Visual checklist (what a reviewer looks at on each PNG)

Derived from the thresholds above and the prose in `docs/PUBLICATION_QC.md`, `docs/EXPORTING_PUBLICATION_FIGURES.md` ("Export-safe layout"), `docs/V0_6_PUBLICATION_STYLE_LESSONS.md`, and the benchmark `visual_qc.md` files:

- **Font sizes** — axis labels ≥ 9 pt, ticks ≥ 8 pt, nothing below 6 pt anywhere; title/annotation sizes follow the `StyleProfile` tokens, not renderer literals.
- **Marker sizes / line widths** — `marker_size` and `line_width_pt` visibly respond when changed (the preset QC's `color_roundtrip`/`typography_roundtrip`/`plot_specific_roundtrip` catch dead controls); markers distinguishable at 89 mm width.
- **Contrast** — text luminance vs background (`low_contrast`); significance colours from the Publication palette; no grey-on-grey.
- **Labels and units** — every non-decorative axis labelled; unit-bearing quantities carry a unit (`missing_units` advisory); no duplicated or truncated tick text; rotated multi-line ticks joined on one line (`test_rotated_multiline_tick_labels_are_joined_on_one_line`).
- **Legend** — outside the data when it would overlap (`legend_overlap`), width ≤ axes width for panel use, entries not clipped at the figure edge.
- **Whitespace** — margins from the layout spec; no large empty bands from over-expanded y-limits after bracket stacking.
- **Clipping** — tight bbox within 112 % of the figure; nothing cut in the fixed preview; colorbars and outside legends fully inside the exported bbox.
- **Overlap** — adjacent tick labels do not intersect; point labels de-overlapped (`dedupe_labels_by_distance`, `label_policy`); annotations do not sit on data.
- **Brackets** — stacked without crossing, star/p text above the bracket, y-axis expanded so the top bracket is inside the axes.
- **Physical size** — `output.width_mm/height_mm` honoured (`figure_size`), dpi ≥ 300 at that size, vector text editable in SVG/PDF (`svg.fonttype none`, `pdf.fonttype 42` — `_VECTOR_TEXT_RC` in the registry).

## 5. "Scientific freeze": data and statistics unchanged by rendering

The contract is that rendering and QC are pure with respect to inputs: renderers receive the caller's `DataFrame` and must not mutate it; QC/auto-fix never touch data, colours or statistics; the `PlotSpec` sidecar re-renders to the same scientific metadata. `registry.render` itself does **not** copy the frame — each renderer is responsible.

Existing tests that pin this:

- Input immutability: `tests/test_renderers.py::test_renderer_does_not_mutate_input` (deep copy before, `assert_frame_equal` after, over `plot_case`), `tests/test_v04_plots.py` (same pattern for v0.4 types), `tests/test_histogram_distribution.py` (two places), `tests/test_survival_input_forms.py` (`df.equals(before)`), `tests/test_preprocessing_transforms.py` ("Original matrix never mutated"), `tests/test_matrix_transformations.py`, `tests/test_preprocessing_qc_plots.py`.
- Spec immutability: `tests/test_publication_qc.py::test_apply_fixes_does_not_mutate_input`.
- Statistics not recomputed by renderers: brackets are drawn from stored `AnnotationItem`/`StatResult` objects (`plots/stats_overlay.py`, `plots/annotation_state.py`); tests in `tests/test_stats_annotations.py`, `tests/test_annotation_state.py`, `tests/test_stats_integration.py`, `tests/test_statistics_oracle_validation.py` (scipy/statsmodels oracle) and `scripts/statistics_oracle.py`.
- Re-render fingerprints: `tests/test_reproducibility_export_qc.py::test_plotspec_roundtrip_reproduces_key_metadata` reloads the sidecar and asserts `plot_type`, `data_columns_used`, and numeric fingerprints (`n_up`, `n_down`, `n_ns`, `n_clusters`, `matrix_shape`) match; `test_volcano_annotation_settings_roundtrip`, `test_manual_annotationspec_roundtrip`.
- Presets: `build_figure_preset_qc` checks `new_data_safe` (no value from the original table travels in a preset) and JSON byte-for-byte round-trips.
- Benchmarks: `qc/scientific_qc.md` per panel traces every mapping to a source column and records row/column counts and transforms.

Absent on main: a test that hashes the *input file* and the *statistics report* before and after a full app-level render+export cycle, and a test that `score_publication`/`check_layout` leave `result.metadata` numeric keys untouched. The pieces (`RenderResult.metadata`, `StatsReport`, `pd.util.hash_pandas_object`) make this a small addition to `tests/test_reproducibility_export_qc.py`.

## 5a. What each committed QC table contains

Reading these CSVs in review is faster than re-rendering everything:

- `reports/release_cross_platform_qc/<platform>/qc_summary.csv` — columns
  `plot_type, render_status, export_png, export_pdf, export_svg, n_axes,
  n_legend_labels, n_warnings, forbidden_style_label, font_used, notes`. Compare
  `render_status`/element counts across platforms; `font_used` legitimately differs.
- `reports/publication_qc_gallery/qc_summary.csv` — `name, group, status, qc_level,
  qc_score, warnings` for every registry type plus the matrix-workflow plots
  (`group` distinguishes them). A drop in `qc_score` for an unchanged type is a regression.
- `reports/figure_qc_release_candidate/qc_summary.csv` — `name, plot_type, status,
  png, pdf, svg, n_warnings` per DEFAULT/ADJUSTED case.
- `reports/figure_preset_qc/all_plot_preset_matrix.csv` — one row per type with
  PASS/FAIL/N/A per check (`COLUMNS` in `build_figure_preset_qc.py`); `notes` must
  explain every N/A. `color_controls_audit.csv` (from `audit_style_capabilities.py`)
  lists which colour controls each renderer really consumes.
- `benchmarks/publication_recreation/reports/benchmark_summary_table.csv` — per
  real-data panel: passed / QC flags / iterations.

## 5b. Multi-panel figures

`make_my_figure_core/panels/builder.py` composes panels by embedding each panel's
content as a raster at `FigureLayout.panel_dpi` (default 300, `panels/models.py`)
while panel labels and titles stay vector text. This is a documented trade-off (no
SVG splicing); `score_publication` warns via `panel_resolution` when `panel_dpi` is
below `MIN_PANEL_DPI = 200`. Each panel remains independently exportable as vector
from its own PlotSpec. Tests: `tests/test_multipanel.py`, `tests/test_imported_panels.py`,
`tests/test_pop_out_panels.py`; the layout/legend rules for panels are in
`docs/MULTI_PANEL_FIGURES.md` and `docs/IMPORT_EXTERNAL_PANELS.md`.

## 5c. Lessons already learned from real-data recreations

`docs/V0_6_PUBLICATION_STYLE_LESSONS.md` records what the benchmark iterations changed
and what they left alone. Apply these as PlotSpec-level choices, not per-renderer hacks:

- legend outside (`style.legend_outside = True`) for multi-series panels; a general
  "≥ 4 series → outside" rule is suggested but not yet encoded in the engine;
- final-pass export at 400 dpi with SVG/PDF as the primary artefact;
- double-column width for wide layouts (network, heatmap, PCA, confusion matrix);
- units belong in axis labels (the `missing_units` advisory exists for this);
- slim heatmap colorbars with few ticks; fixed `seed=42` for network layouts.

The `docs/V0_5_PUBLICATION_QC_PLAN.md` "high-risk" list (two-way/RM ANOVA and log-rank
correctness, bracket/group alignment, dense networks and crowded labels, tight-bbox
clipping, headless-untestable desktop pop-outs) is still the right place to look first
when a visual regression is suspected.

## 5d. Reviewing a gallery change

1. Regenerate the relevant tracked table(s) from §3 and diff them against `main`.
2. Open the PNGs for any row whose `qc_score`, `n_warnings`, element counts or
   PASS/FAIL changed; open a handful of unchanged rows as controls.
3. Walk the §4 checklist on each opened PNG at 100 % zoom and at the intended
   physical width (89 mm single column ≈ 3.5 in).
4. Confirm the scientific fingerprints (§5) did not move: compare `n_up/n_down/n_ns`,
   `n_clusters`, `matrix_shape` and the statistics report in the sidecars.
5. Commit the regenerated CSV/MD together with the code change; never commit the
   git-ignored PNGs under `reports/publication_qc_gallery/per_plot/` or `outputs/`.

## 6. Where QC results surface

- `RenderResult.metadata["publication_check"]`, `["layout_qc"]`, `["layout_fixes"]`, `["statistics_report"]`; written to the `*.plot_spec.json` sidecar by `registry.write_sidecar` and the StatsSpec sidecar by `write_stats_sidecar`.
- Desktop: "Publication QC" dialog (`main.py`, title shows level and score) with "Auto-fix & re-render"; Streamlit: the "Publication QC — ready-to-export checks" expander.
- Reports committed under `reports/` (see the table in §3) and `outputs/publication_qc/*.md`; the v1.1.0 release audit (`docs/releases/v1.1.0/release_v1.1.0_audit.md`) records which were refreshed for the release.

## Verify this is still current

```bash
grep -n "^[A-Z_]* = \|Check(\"" make_my_figure_core/qc/publication_score.py | head -30
grep -n "publication_check\|layout_qc\|auto_fix_layout" make_my_figure_core/plots/registry.py
grep -n "STYLE_CHANGES\|LAYOUT_CHANGES\|OUTPUT_CHANGES\|^COLUMNS" scripts/build_figure_preset_qc.py
MPLBACKEND=Agg python -m pytest -q -p no:pytest-qt tests/test_publication_qc.py tests/test_layout_qc.py tests/test_xlabel_overlap_qc.py tests/test_reproducibility_export_qc.py
```
