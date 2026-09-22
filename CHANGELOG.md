# Changelog

## Unreleased

### Fixed

- **Renderers draw the same figure on every supported pandas version.** Every `sort_values` in the plot renderers now uses a stable sort, so rows that tie on the sort key keep their table order instead of an arbitrary order that differed between pandas 2 (`object` columns) and pandas 3 (default `str` columns). Found by the whole-library render fingerprint: stacked composition bars ordered by a grouping column were drawn as S01, S14, S13, ... on pandas 2 and S01, S02, S03, ... on pandas 3 for the same data. Also affects tie-breaking in the oncoprint gene order (equal frequencies), lollipop draw order and top-n labels, volcano / MA label ranking, enrichment and network top-n selection, and the waterfall, calibration, precision-recall, Manhattan and spider sorts; values, counts and statistics are unchanged. Regression tests: `tests/test_renderer_sort_stability.py`.

All notable changes to Make My Figure are recorded here. This project uses a
single, evolving `Publication` style — it does not target or claim compliance
with any journal.

## [1.1.1] — Reproducible figure packages, Circos chord diagram, compatibility fixes

Prepared on `main` on 2026-09-20. The `v1.1.1` tag, installers and GitHub release follow after the author's final check.

### Added — plot types

- **Circos-style chord diagram** (`chord_diagram`, `make_my_figure_core/plots/chord_diagram.py`):
  flows between categories that share one set, from an edge list with one row per link
  (`source`, `target`, optional numeric `value`, optional `group`). Segments are sized by total
  flow, ribbons by link value; options with explicit scopes for segment order, gap, start angle,
  ribbon colouring (source / target / group), transparency, labels (radial / tangential), total
  tick marks and the group legend (style), and for the minimum link value, directed reading
  (ribbons narrow toward the target) and self-links (config). No statistics: a chord diagram
  summarises flows. Bundled synthetic example (six cell types, compartment group), catalogue
  entry and figure, focused tests (`tests/test_chord_diagram.py`), and a low-confidence
  recommendation (0.55) alongside the network graph for `source`/`target` edge lists. Genomic
  multi-track Circos (ideogram coordinates, heatmap or histogram rings) is out of scope for
  this version; the ring geometry leaves room for tracks.

### Added — reproducible figure packages
- **Reproducible figure packages (`.mmfpackage`)** — one portable file that reopens a figure on
  another computer without the original data files: the PlotSpec (or FigureSpec + every panel's
  PlotSpec/StatsSpec), a frozen lossless copy of the exact table(s) the plot used (`mmftable`
  JSON: doubles bit-exact incl. NaN/±Inf/−0.0, missing values, strings, categories, dates), the
  original CSV/TSV/XLSX when available, the StatsSpec with results, the MatrixSpec /
  SampleMetadataSpec / PreprocessingSpec with both the original and the derived matrix, imported
  panel images, PNG/SVG/PDF previews, the software environment, and `manifest.json` (format
  version 1, JSON Schema `schemas/figure_package_manifest.schema.json`) with a SHA-256 for every
  file. Core: `make_my_figure_core.package` (writer, reader, assembly helpers, security scan).
- **Desktop:** *Open Figure Package* on the landing page and File menu (Ctrl+Shift+P), *Save
  Reproducible Figure Package…* (Ctrl+Shift+S) and *Save Figure Package (.mmfpackage)* in the
  Export group with a privacy notice ("Figure packages include the data required to reproduce the
  figure"), content list and size estimate; packages open from drag-and-drop and *Recent files*
  (📦); composite packages reopen in the Figure Builder with their layout and frozen panel data;
  Figure Builder *Save Figure Package…*; Help tab *Files & reproducibility*.
- **Browser:** *Data source → Open Figure Package* and a *Figure Package* download.
- On opening a package the statistics are recomputed from the frozen data and compared with the
  stored StatsSpec, and a recorded preprocessing chain is replayed on the frozen source and
  compared with the frozen derived matrix; differences are reported, frozen values are never
  replaced.
- Exported PlotSpecs carry `source.source_table_sha256`, a content digest of the plotted table;
  *Open PlotSpec* warns when the data it finds differ from the recorded table.
- `PreprocessingStep.user_parameters` records the requested parameters so a chain can be replayed
  exactly (older records are replayed by signature filtering).

### Changed
- **Export all as ZIP** now contains the publication files, `name.plot_spec.json`,
  `name.stats_spec.json` (when statistics ran), **`name.mmfpackage`** and a README.
- Desktop wording makes the three artifacts unmistakable: *Export PlotSpec JSON (specification
  only)*, *Open PlotSpec… (specification only; needs the data file)*, Figure preset (no data),
  Figure package (frozen data + specifications).
- *Open PlotSpec* accepts the `{"plot_spec": …, "render_metadata": …}` sidecar written by *Export
  PlotSpec JSON* (previously only the bare spec from *Save PlotSpec* reopened).

### Security
- Packages are untrusted input: member names are checked (no `..`, absolute paths, drive letters,
  backslashes, control characters), symbolic links and device entries are rejected, entry count,
  entry size, total size and compression ratio are capped, unlisted or altered files fail the
  integrity check, nothing is unpickled or executed.

### Documentation
- `docs/FIGURE_PACKAGES.md`; Quick Start and User Manual (Parts I §6, XV §61–63a, XVI §68, XVII
  §70, XXIII, XXIV, glossary) describe PlotSpec vs Figure preset vs Figure package and the
  eight-step "Sharing a reproducible figure" workflow; `reports/portable_package_current_state.md`
  (live-code audit of v1.1.0), `reports/v1.1.1_manuscript_claim_audit.md`,
  `reports/v1.1.1_manual_acceptance_test.md`.

### Fixed — library compatibility
- Figure-package tables written with pandas 3 (default `str` dtype) reopen with their dtype
  intact; on pandas 2 they reopen as `object`, which is what that pandas infers itself
  (`make_my_figure_core/package/tabledata.py`, test in `tests/test_figure_package_integrity.py`).
- The figure-preset QC script no longer writes into read-only pandas 3 array views.

### Packaging
- Packaging: the MIT `LICENSE`, `README.md` and `CHANGELOG.md` are bundled at the top level of the
  desktop builds (Windows zip and installer, macOS app, Linux tar.gz/AppImage); the installer shows
  the licence; `pyproject.toml` declares the licence and classifiers.
- Dependencies: bounded ranges (next major excluded) in `pyproject.toml` and `requirements.txt`, and
  a new `requirements-lock.txt` with the exact versions the release was tested with.

## [1.1.0] — Figure presets, validated statistics, export and packaging fixes

### Added
- **Figure presets for every plot type** (`presets.py`; desktop *Figure preset* panel and
  browser expander: Apply, Save preset…, Import, Export, Delete, Reset). A preset is the
  reusable part of a PlotSpec — **style** mode (typography, palette, geometry, legend and
  colorbar placement, export size, visual plot options) or **full** mode (adds column roles,
  thresholds, labels, statistics test). It never contains the table, its name, values or
  worksheet provenance; roles a new table cannot satisfy are reported, never substituted.
  Every option now declares a scope (`Option.scope`), and a registry-wide QC matrix
  (`reports/figure_preset_qc/`) pins save → apply → export → round-trip for all 38 types.
  Figure Builder **Layout presets** (`.mmflayout.json`) carry grid, panel sizes, gutters and
  label style without panel content.
- **Histogram plot type** (`histogram_distribution`): long or wide input (declared, not
  guessed), one panel per group or overlaid, bars and/or frequency polygon, counts /
  frequency / percent / density, cumulative option, mean/median markers, axis-range and tick
  controls. Complements the ridge/density plot, which smooths.
- **Survival curves:** explicit `precomputed` input form for already-computed S(t) columns
  (multi-column role), validated 0/1 event indicator with a two-level recoding message,
  `y_scale` fraction/percent, reference line, group labels, curve style; a log-rank test is
  refused on a precomputed curve with an explanation.
- **Axis-range and tick overrides** (`x_min`, `x_max`, `y_ticks`, `ends_and_midpoint`) for
  survival, histogram and forest plots. A range that would hide plotted data is refused
  rather than clipped silently. Layout `x_scale` / `y_scale` (`linear` | `log` | `symlog`)
  for line plots; a log axis is skipped for non-positive data.
- **Line / time-course bands:** `iqr` and `range` (median-centred) in addition to SEM / SD /
  CI95; `style_by` mapping varies line style and marker by a second category while colour
  follows the first.
- **Oncoprint:** `order` (frequency | input) and `show_sample_labels` options.
- **Box/violin:** `point_size`; **volcano:** `show_legend`; **MA plot:** optional
  `lfc_cutoff` so significance can follow a published definition; **heatmap:** an explicit
  layout `aspect` overrides the row-count height heuristic; `title_font_weight` style token
  honoured by every renderer that draws a title.
- **Multi-column roles** (`value_columns`, `survival_columns`) render as multi-select lists in
  both frontends; optional numeric options can be left blank ("(auto)") in the desktop app.
- **Independent R validation benchmark** (`benchmarks/r_validation/`): every statistical test,
  correction, normalisation/transform, QC metric, PCA, clustering and differential screen
  compared with independent R implementations (base R, survival, car, rstatix, effectsize,
  MASS, dunn.test, limma, edgeR, DESeq2) on 26 seeded synthetic datasets, the bundled examples
  and a public RSEM count matrix; 2,625 comparisons, no failures; classes EXACT /
  NUMERICALLY_EQUIVALENT / ACCEPTABLE_IMPLEMENTATION_DIFFERENCE / UPSTREAM_INPUT_DIFFERENCE /
  METHOD_MISMATCH kept apart; the feature-level screen is compared with limma-voom, edgeR and
  DESeq2 as concordance only. Regression tests in `tests/test_r_validation_regressions.py`.
- **User Manual and Quick Start** (`docs/manuals/`, generated Markdown, DOCX and PDF with
  screenshots from bundled example data) and a plot catalogue generated from the registry.

### Changed
- The browser app reads column roles and options from the shared `ui_hints` registry (its
  own copy had drifted: 19 plot types had no mapping controls).
- Tick density follows the style's tick font even when a figure is drawn outside the style
  context (Figure Builder rasterisation); rotated multi-line category labels are joined on
  one line.
- Exports use a tight bounding box that includes axis labels and titles, so a long axis label
  is no longer clipped.
- Streamlit single-plot exports keep text as text (editable SVG/PDF).

### Fixed
- **Six numerical defects found by the R validation:** r × c Fisher's exact test used an
  unseeded Monte Carlo p-value (now seeded, 200,000 resamples, method recorded); ROC AUC and
  average precision depended on input row order for tied scores (ties collapsed to one
  operating point); quantile normalisation broke ties by sort order (now Bolstad/limma
  average-rank algorithm); `voom` used a library-size-scaled prior (now the voom definition);
  the Mann–Whitney effect size in the feature-level summary had the wrong sign; last-bit
  near-ties in rank tests are treated as ties.
- Delimited-text floats are parsed correctly rounded (`float_precision="round_trip"`), so a
  CSV and an XLSX of the same table load to the same doubles.
- The Publication font stack (Arial → Helvetica → DejaVu Sans) is written as a concrete,
  installed family list, so exports, Figure Builder letters/titles, re-placed legends and
  manual annotations keep the profile font instead of falling back to DejaVu Sans.
- Style presets transfer the palette in order to plots with new categories (regression test).
- Installed wheels ship the bundled resources (schemas, style profiles, mock data, examples)
  inside the package; `pip install` of a wheel could previously not render anything.
- Five stale tests repaired: browser smoke test picker index; AppTest session-state proxy; the
  desktop grouping-dialog test used a 3-row toy matrix whose columns are (correctly) classified
  as annotations and expected groups to be guessed without pressing *Guess groups*, so it
  blocked on a modal warning offscreen; the PlotSpec round-trip test hard-coded a plot type
  that the benchmark had since corrected.
- Desktop About dialog shows the real licence and repository instead of placeholders.

### Validation
- Full test suite on Linux (Qt offscreen where available); R benchmark re-run against the
  release candidate (see `docs/releases/v1.1.0/release_v1.1.0_audit.md`).

### Documentation
- README rewritten for v1.1.0 (native installers first; plot and statistics counts from code).
- `docs/manuals/`: Quick Start and User Manual regenerated for v1.1.0.

### Packaging
- `setup.py` + `MANIFEST.in` stage resources into the wheel; `pyproject.toml` build extra.
- Native installers (macOS DMG, Windows Setup.exe, Linux AppImage/tar.gz) are built on the
  GitHub Actions native runners when a version tag is pushed, with a `--selftest` smoke test.

## [1.0.0] — First stable release

Supersedes `1.0.0-rc1`, adding the release-candidate fixes plus first-class
multi-sheet Excel support, duplicate feature-label handling, and a unified Matrix
Workflow. One user-facing **Publication** style; reproducible PlotSpec/StatsSpec
sidecars; no R dependency and no fabricated statistics.

### Added
- **Multi-sheet Excel workbook browser** (Desktop + Streamlit): every worksheet is
  selectable (documentation/empty/hidden included), advisory sheet classification,
  worksheet-aware output names, and workbook/sheet provenance on the PlotSpec. See
  [docs/MULTI_SHEET_EXCEL.md](docs/MULTI_SHEET_EXCEL.md).
- **Duplicate feature labels for Volcano & MA**: per-point identity with all /
  unique / count label policies and deterministic representative selection, so rows
  sharing a gene symbol stay independently labelable. See
  [docs/VOLCANO_ANNOTATIONS.md](docs/VOLCANO_ANNOTATIONS.md).

### Changed
- **Unified Matrix Workflow.** The Matrix Workflow now prepares data + recommendations
  and hands off to the *same* full plot editor as the normal workflow (one canonical
  PlotSpec, full controls, annotations, export, and Figure Builder) — no second reduced
  plot UI. Matrix/metadata/preprocessing/statistics/workbook provenance travels into
  the exported PlotSpec. See [docs/MATRIX_WORKFLOW.md](docs/MATRIX_WORKFLOW.md).

## [1.0.0-rc1] — Responsive cross-platform UI and deterministic defaults

### Fixed
- **Clipped desktop controls (macOS/Windows).** The top-nav buttons were laid out
  in a fixed-width horizontal row inside a control pane hard-capped at 480px, which
  clipped the **"Matrix workflow…"** button. Buttons are now stacked vertically and
  the pane's max-width cap is removed, so full labels stay visible at any pane
  width, DPI, or OS font metric.
- **Truncated recommendation cards.** The nested scroll area in the Recommended
  Figures panel could collapse to a sliver and cut cards mid-sentence; it now has a
  minimum height so at least a full card is readable.
- **Over-wide / truncated data-preview columns.** Preview columns are now
  user-resizable, width-capped, and carry header tooltips showing the full column
  name.
- **Stale persisted splitter sizes.** Degenerate/outdated saved splitter geometry is
  validated on restore and falls back to a proportional default instead of leaving
  the control pane unusably narrow.
- **Streamlit silently defaulted to a bar plot.** On upload the app auto-selected
  the first plot type and rendered it; it now shows a **"— Choose a plot type… —"**
  placeholder and renders nothing until a real plot is chosen — matching the desktop
  app's existing behavior.

### Changed
- Placeholder text, the visible style name, and top-level workflow action labels now
  live in a shared `make_my_figure_core/ui_strings.py` so the Streamlit and desktop
  frontends stay in lockstep.

### Notes
- Cross-platform UI QC runbook added (`docs/CROSS_PLATFORM_UI_QC.md`). The visual
  fixes are covered by source-level guardrail tests; on-device verification on macOS
  (Retina) and Windows (125/150/200% scaling) is still recommended before release.

## [0.6.1] — Open PlotSpec, transform-aware recommendations, in-app differential screen

### Added
- **Open PlotSpec** (desktop File menu + Streamlit data source): reopen a saved
  `*.plot_spec.json` (+ its data) and reproduce the exact figure — restores plot
  type, mappings, style, and statistics.
- **Transform-aware recommendations**: plots reachable by reshaping the data
  (wide→long ridge/box, correlation heatmap, category-frequency bar). On Generate
  the app reshapes the data, **saves the new CSV**, and plots it.
- **Guidance recommendations** (informational): e.g. volcano/MA from a matrix
  explain that a precomputed fold-change + p-value/FDR table is required and that
  Make My Figure does not compute or fabricate those statistics.
- **In-app differential screen** (Define groups → "Differential screen"): a basic
  per-feature two-group test (Welch/Student's t or Mann–Whitney — the app's
  existing two-group tests) + Benjamini–Hochberg FDR + log2 fold-change on a
  **normalized** matrix, writing a results table (log2FC/p/FDR/AveExpr) that then
  drives volcano/MA/top-feature recommendations. It is transparently labeled as a
  basic screen — **NOT** a count-based model (DESeq2/edgeR/limma-voom) and **not**
  RNA-seq-from-raw-counts; normalize before running.
- **Heatmap `log_zscore` scale** (log then per-row z-score) + a nudge when a raw-
  count-like matrix is left unscaled.

### Fixed
- Recommendation engine now detects unnamed categorical group columns (e.g.
  `species`) so group/value tables get box/violin/ridge/bar suggestions; manually
  picking a distribution plot auto-prefills x/y/group.
- **Revert to original data**: reshaping the data (a transform recommendation,
  grouping, or the differential screen) no longer traps you on the transformed
  table. A "↩ Revert to original data" button appears and restores the pre-reshape
  data and its own recommendations (the saved reshaped CSV is kept on disk).

## [0.6.0] — Publication style, recommendations, QC, benchmarks, performance

Focus: fast, polished, intelligent, publication-ready — not more plot types.

### Added
- **Intelligent figure recommendations** (`make_my_figure_core/recommendations/`):
  profiles an uploaded table and suggests appropriate figures (from the existing
  37 plot types) with confidence, reason, detected mappings, suggested statistics,
  and a one-click PlotSpec draft. Surfaced as a **Recommended Figures** panel
  (desktop) and expander (Streamlit); expensive suggestions require confirmation.
- **Publication QC** (`make_my_figure_core/qc/`): scored pass/warn/fail readiness
  check with suggested and one-click auto-fixes. Desktop **Publication QC** button
  + Streamlit expander.
- **License-safe publication benchmark recreation** (`benchmarks/publication_recreation/`,
  branch `benchmarks/publication-recreation`): recreates real-data publication-style
  panels through the app with scientific + visual QC and full provenance.
- **Performance:** `apps/desktop_app/workers.py` (QThreadPool background layer),
  debounced rendering for continuous controls, `scripts/benchmark_performance.py`.

### Changed
- **Single `Publication` style identity.** Journal-named profiles (Nature-/Science-/
  Cell-like and their "learned" variants) are removed from the UI and docs; advanced
  appearance controls remain under Publication. Old PlotSpecs referencing removed
  profile names are migrated to `Publication` on load, with a non-intrusive notice.

### Notes
- Make My Figure does not run RNA-seq differential expression (no R/edgeR/limma/
  voom). It plots generic matrices (→ heatmap/PCA/clustering) and precomputed
  differential results tables (→ volcano/MA). Users confirm that recommended
  figures/tests match their design. The Publication style is a general
  manuscript-ready visual style, not an official journal template.

## [0.5.3] — grouped heatmaps + cleaner "Define groups"

### Fixed
- **"Define groups" listed non-sample columns.** The wide-matrix group assignment
  showed every non-id column (including RNA-seq annotation columns like
  `geneSymbol` / `bioType` / `annotationLevel`) and auto-assigned each a group.
  Now only **numeric** columns are offered as samples (text annotation columns are
  dropped), groups start **blank** (assign only your real samples; anything left
  blank — e.g. a numeric annotation column — is excluded), and "Auto-guess from
  names" is opt-in.
- **Heatmap showed nothing after grouping.** Grouping only reshaped to *long*,
  which collapses a heatmap to a single "value" column. The Define-groups dialog
  now has an output choice: **long** (bar/box/violin) or **wide** (heatmap/PCA).
  Wide keeps the matrix (assigned samples only) and adds a **group color strip**,
  so a grouped heatmap actually renders. Verified end-to-end on a real 12-sample /
  55k-gene RSEM matrix + metadata.

### Added
- `grouping.numeric_sample_columns()` and `grouping.wide_grouped_matrix()`
  (returns the wide matrix + a column-annotation group strip); controller
  `group_from_matrix_wide()` / `numeric_sample_columns()`.

## [0.5.2] — memory guards for large matrices + RNA-seq parsing

### Fixed
- **Out-of-memory on large matrices.** Hierarchical clustering builds an O(n²)
  distance matrix, so a big feature axis (e.g. a ~55k-gene RSEM count table)
  exhausted RAM and crashed the app. The clustered heatmap, standalone
  dendrogram, and hierarchical-clustering plot now **cap the feature (row) axis
  to the top-N most variable rows** (default 2,000, configurable via
  `max_features`) before clustering/display, with a clear warning. Highlighted
  rows are always kept. PCA is unaffected (it SVDs the small samples×features
  orientation — no O(n²) — and was already memory-safe).
- **RNA-seq matrices with annotation columns.** Count matrices commonly carry
  columns like `geneSymbol` / `bioType` / `annotationLevel` before the samples.
  The heatmap/dendrogram/hierarchical-clustering now drop non-numeric annotation
  columns automatically and accept an `exclude_columns` list for numeric-looking
  ones; they also report exactly which columns were used as samples. PCA now
  restricts to the columns present in the metadata's sample-id column, so
  annotation columns are no longer mistaken for samples.

### Notes
- Defaults preserve prior output for normal-sized matrices. For a readable
  publication heatmap, subsetting to top-variable genes was already best practice;
  this just makes it automatic and memory-safe instead of crashing.

## [0.5.1] — click to identify / label points

### Added
- **Click-to-identify / click-to-label** on the desktop live canvas for **volcano**
  and **scatter** plots: enable *"Click a point to identify / label it"* (Labels &
  size), then click near a point to see its gene/sample name + coordinates in the
  status bar and toggle a label on it. Added labels are stored in the PlotSpec
  (`mapping.selected_labels`) so they persist on export/reload; click again to
  remove. Picks are kept per plot type and reset on new data.
- Core (GUI-independent) helpers: `build_pickable_points`, `nearest_pickable`,
  `choose_label_column`, `resolve_point_labels`; renderers emit
  `metadata['pickable_points']` + `pick_label_column`. Scatter now honors
  `selected_labels` (label only the chosen points).

### Notes
- Interactive desktop feature — exports remain static; only the labels you add
  persist. Covers volcano + scatter (other plot types label by name). No
  drag-to-reposition. The Qt click handler is additive/guarded but should be
  smoke-tested in the desktop app.

## [0.5.0] — networks, annotations, docking & clustering

Builds on v0.4 (37 plot types total). Focus: publication-ready, refine-in-app
figures. No breaking changes — existing plots, statistics annotations, exports,
PlotSpec, desktop app, and Streamlit app are unchanged.

### Added — plot types
- **Network graph** (`network_graph`): edge-list / adjacency-matrix /
  correlation-network inputs; spring/kamada-kawai/circular/shell/spectral/
  multipartite/fixed layouts (reproducible via a stored seed); filtering
  (weight, |r|, p/FDR, top-N edges/nodes, min degree, remove isolates); node
  metrics (degree, betweenness/closeness/eigenvector centrality) and a network
  summary; exportable filtered edge + node-metric tables. NetworkX-based.
- **Hierarchical clustering** (`hierarchical_clustering`): cut the tree into `k`
  clusters, cluster color strip, exported cluster-assignment table + summary;
  scaling (row/col z-score, center, log) and distance/linkage options.

### Added — annotations
- **Universal manual annotation layer** (`spec['annotations']`,
  `make_my_figure_core/annotations.py`): text, arrow, callout, box, region,
  bracket, and reference lines in data/axes/figure coordinates, drawn as vector
  artists and applied to every plot type through the central render path.

### Changed — annotations & clustering on existing plots
- **Volcano**: labels on/off, six label modes (top-FDR / top-|log2FC| / top
  up+down / selected / pasted list / all-significant), displaced-label arrows,
  label boxes/colors/size, auto `Up/Down/FDR` subtitle, and a max-labels warning.
- **Heatmap**: scaling + distance/linkage options, `cluster_k_rows` /
  `cluster_k_columns` color strips with exported assignments, `sort_by_cluster`,
  and gene/sample highlighting via a pasted list (bold labels when others hidden).

### Added — desktop
- **Pop-out / pop-in panels** (`apps/desktop_app/panels_dock.py`): detach the
  Figure, Data & Messages, or Plot Controls panels to floating (multi-monitor)
  windows and dock them back with state preserved; View-menu actions + Dock All;
  layout persisted via `QSettings`. Additive (reparenting, not `QDockWidget`).

### Added — supporting
- Shared `make_my_figure_core/clustering.py` (scaling, metric/linkage validation,
  k-cut, assignment table, color mapping, summary).
- `networkx` and `adjustText` added as dependencies.
- Docs: `V0_5_NEW_FEATURES.md`, `NETWORK_GRAPH.md`, `ANNOTATIONS.md`,
  `VOLCANO_ANNOTATIONS.md`, `HEATMAP_HIGHLIGHTING.md`, `HIERARCHICAL_CLUSTERING.md`,
  `POP_OUT_PANELS.md`; example data for the new types (incl. edge-list /
  adjacency / correlation network files); v0.5 visual QA gallery.

## [0.4.0] — manuscript plot-type expansion

Adds **18 new plot types** (17 → 35) covering a much broader range of
publication figures, wired through the existing registry, validation, style,
publication-readiness check, and export/sidecar systems. No breaking changes:
all existing plot types, statistics annotations, exports, and app navigation are
unchanged.

### Added — new plot types
- **Group comparison & distributions:** dot / strip plot, beeswarm plot, paired
  dot plot / slopegraph, raincloud plot.
- **Relationships & trends:** dose-response curve (4PL fit + EC50/IC50), spider
  plot (longitudinal per-patient change).
- **High-dimensional / omics:** hierarchical clustering dendrogram, MA plot,
  UMAP / t-SNE embedding scatter (precomputed coordinates).
- **Genomics & variants:** Manhattan plot (genome-wide + suggestive lines),
  Q-Q plot (p-value with genomic inflation λ, or quantile mode).
- **Clinical & survival:** swimmer plot.
- **Model performance:** precision-recall curve (AUPRC), confusion matrix
  (counts / row / column / total normalization), calibration plot (Brier score).
- **Set overlap & flow:** UpSet plot, Sankey / alluvial (two-stage).
- **Method comparison / QC:** Bland-Altman plot.

### Added — supporting
- `make_my_figure_core/plots/_v04_shared.py`: shared helpers (matrix parsing,
  hierarchical linkage, jitter / quasi-beeswarm, summary overlays, flexible
  column detection, −log10(p)); numpy/scipy only — no new dependencies.
- A bundled synthetic example dataset + PlotSpec for every new plot type
  (regenerate via `scripts/generate_example_data.py`).
- `scripts/generate_v04_qa_gallery.py`: renders each new plot and a contact
  sheet to `reports/v04_qa/` for visual QA.
- `docs/V0_4_NEW_PLOT_TYPES.md`: use cases, required/optional columns, and
  documented limitations for every new type.
- `tests/test_v04_plots.py`: per-type render, export, no-mutation, validator,
  and publication-readiness tests, plus metadata-correctness checks.

### Integrity
- No fabricated statistics: AUPRC, accuracy, Brier score, IC50/EC50, and genomic
  inflation λ are computed only from valid inputs and otherwise omitted with a
  warning. Differential-expression p-values are read verbatim, never recomputed.
- Documented limitations: quasi-beeswarm (not force-directed); two-stage Sankey
  only; embedding takes precomputed coordinates (no `.h5ad`/AnnData yet);
  dendrogram computes linkage from the matrix (no precomputed-linkage input yet);
  UpSet shows the top 20 intersections.

## [0.3.0]
- Multi-panel Figure Builder: live preview, per-panel size (inches), figure-wide
  font controls, and undistorted (letterboxed) panel scaling; per-panel titles
  off by default.

## [0.2.0]
- Figure-first workflow; in-app grouping; volcano from a DE-result table with
  confirmable columns.

## [0.1.0]
- First desktop release.
