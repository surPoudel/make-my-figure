# Make My Figure — v0.6.0 Implementation Plan

> **Status:** planning (Part 1). No v0.6 feature code is written until this plan exists.
> **Scope corrections locked in for v0.6.0:**
> 1. **No RNA-seq analysis.** No R / edgeR / limma / voom / raw-count DE / `RnaSeqSpec` /
>    RNA-seq UI/tests/docs. The app plots **generic** data: numeric / expression-like
>    matrices (→ heatmap, PCA, clustering, correlation) and **precomputed** differential /
>    feature-level results tables (→ volcano, MA). A visible note states the app does not
>    run differential expression.
> 2. **One style identity: `Publication`.** Journal-named profiles (Nature-/Science-/Cell-like
>    and their "learned" variants) are removed from the UI and user-facing docs. Old PlotSpecs
>    that reference removed names are migrated to `Publication` on load (non-fatal, with a
>    notice). Advanced appearance controls remain, under Publication.

This release is about making the app **fast, polished, intelligent, and publication-ready** —
not about adding many new plot types.

---

## 1. Current app architecture summary

Data flow: **loader → PlotSpec (validated) → renderer → RenderResult → export/sidecar**.

- **Core engine** `make_my_figure_core/` is frontend-agnostic. `plots/registry.py` is the
  wiring hub (`_RENDERERS`, `_DEFAULT_MAPPINGS`, `_DISPLAY_NAMES`, `render()`), re-exported via
  `make_my_figure_core/__init__.py`.
- **Two GUIs:** desktop (`apps/desktop_app/`, PySide6; `main.py` UI + `controller.py`
  GUI-free logic) and Streamlit (`apps/streamlit_app/streamlit_app.py`, a top-to-bottom script).
- **Validation** `spec/validate.py` (jsonschema Draft 2020-12 + app-level checks for known
  plot type / known style).
- **Export** wraps savefig in `_VECTOR_TEXT_RC` (editable SVG/PDF text) and writes a
  `.plot_spec.json` sidecar.
- **Statistics** `statistics/` — `run_statistics(df, stats_spec, plot_type, mapping)` → `StatsReport`;
  `TESTS` registry (17 tests); `recommend_tests(...)` advisory. Invariant: every drawn p-value
  comes from a stored `StatResult`; never fabricated.
- **Multi-panel** `panels/` — `build_figure(MultiPanelFigure)` composes panels (raster content +
  vector labels) → `export_multipanel` + `*.figure_spec.json`. Desktop `FigureBuilderDialog`
  (`stats_panel.py`).
- **Grouping** `grouping.py` (wide matrix → long tagged, add group column, guess groups).
- **DE-column detection** `de_detect.py` (`detect_de_columns` — best-guess volcano mapping across
  edgeR/limma/DESeq2 header conventions; pure pandas, **no** R; used for user confirmation only).
- **Advisory publication check** already exists: `qa/publication_check.py::check_publication_readiness(fig)`,
  called from `registry.render()` (lazy, try/except), stored in `metadata["publication_check"]`.

### Plot types (17)
`barplot_with_error_bar`, `grouped_barplot_with_error_bar`, `heatmap_clustered_matrix`,
`volcano_plot`, `scatterplot_with_regression`, `boxplot_or_violin_with_points`,
`lineplot_timecourse_with_error_band`, `ridge_or_density_plot`, `enrichment_dotplot`,
`kaplan_meier_survival_curve`, `stacked_bar_composition`, `waterfall_plot`,
`pca_scatter_from_matrix`, `oncoprint_mutation_heatmap`, `lollipop_mutation_plot`,
`roc_curve`, `forest_plot`.

**Not yet implemented** (referenced by the v0.6 prompt): network graph, Manhattan/Q-Q,
dose-response, MA plot, precision-recall, calibration, confusion matrix, UpSet, Sankey,
slopegraph, raincloud, standalone dendrogram, sample-correlation heatmap. The recommendation
engine and benchmarks will only recommend/recreate **existing** renderers; missing types are
documented as out-of-scope for v0.6 (a couple of low-cost ones — **MA plot** and
**sample-correlation heatmap** — may be added as thin renderers if time allows, since they are
directly implied by the "precomputed results" / "matrix" scope).

## 2. Current plot/style architecture

- `StyleProfile` (dataclass, `styles/engine.py`) holds publication-ready **tokens**: typography
  (base/axis/tick/legend/title/annotation/panel-label pt, family, color), axes (spine width, tick
  width/length/direction, top/right spine, grid), data marks (line width, marker size/edge/alpha,
  errorbar/bar widths), legend (frameon/loc/outside/ncol), sizing (single/double column mm,
  export DPI, preferred exports), colors (`palette`, `sequential_cmap`, `diverging_cmap`).
- `rc_params()` maps tokens → matplotlib rcParams; `apply()` uses an rc_context; `with_overrides()`
  applies GUI/PlotSpec overrides (incl. `palette_name` → `NAMED_PALETTES`).
- **Three profile sources:** built-in `publication` (`_publication_profile()`); starter journal JSON
  (`nature_like`/`science_like`/`cell_like` — *only* palette/cmap/width are read; the tiny ~7pt
  journal fonts are intentionally discarded); learned JSON (`style_profiles/learned/*.json`).
- `list_profiles()` → `["publication", nature_like, science_like, cell_like,
  nature_like_learned, science_like_learned, cell_like_learned]`.
- `NAMED_PALETTES`: `publication`, `colorblind_safe`, `high_contrast`, `grayscale`, + journal.

### Style limitations (motivating v0.6 Part 3)
- Defaults are reasonable but still read as "clean Matplotlib," not manuscript panels: spine/tick
  weight, marker edges, legend placement, colorbar styling, threshold/label typography on volcano,
  bracket/annotation styling, panel spacing, and margins can all be tightened.
- Journal-named profiles conflate "aesthetic palette" with "journal identity" — removed in v0.6.
- No single, opinionated, benchmark-validated default that guarantees good margins/legend/label
  density out of the box.

## 3. Suspected performance bottlenecks

- **Canvas rebuilt every render:** `_show_figure` calls `_clear_figure` (deleteLater old
  canvas/toolbar + `plt.close`) then constructs a fresh `FigureCanvasQTAgg` + `NavigationToolbar2QT`
  on **every** preview. Expensive and causes flicker/lag.
- **Everything on the GUI thread:** no `QThread`/`QThreadPool`/`QRunnable` anywhere in `apps/`.
  Rendering, statistics, clustering (heatmap uses `scipy.cluster.hierarchy`), and export all block
  the event loop → UI freeze on large data / heavy plots.
- **Eager scipy import:** `statistics/runner.py` imports all five test modules at import time, each
  doing `from scipy import stats` at module top-level → scipy is pulled in as soon as statistics is
  touched (and transitively during many imports).
- **No debounce:** slider/spinbox/text changes re-render synchronously per event.
- **Full table into a QTableWidget:** first 50 rows only today (good), but no shape/summary-first
  path for very wide/large tables, and no virtualization.
- **No caching:** column detection, data summaries, clustering/layout, and (future) recommendations
  recompute every time.
- **No preview-vs-final split:** interactive edits render at full publication settings.

## 4. Windows-specific performance risks

- **OneDrive-synced repo path** (a working directory inside a cloud-synced folder): file I/O and
  first-access reads can be slow / trigger cloud hydration. File dialogs and example loads pay this.
- **PyInstaller one-folder first launch** on Windows: Defender/SmartScreen scan + cold DLL load
  (Qt plugins, scipy/statsmodels submodules bundled) → slow first start; document expected delay.
- **Qt event-loop blocking** shows more on Windows (compositor differences vs macOS) — synchronous
  render/stat/export feel worse.
- **Matplotlib font cache** rebuild on first run.
- Bundled `collect_submodules("scipy"/"statsmodels"/"patsy")` inflate startup import graph.

## 5. Current statistics / figure-builder / QC status

- **Statistics:** implemented and pinned against scipy/statsmodels (`test_statistics_core.py`).
  `recommend_tests` already returns `{suggested, primary, notes}` per plot type + group count.
- **Figure Builder:** implemented (`panels/builder.py`, desktop `FigureBuilderDialog`). Panels
  reproducible from specs; raster content + vector labels; `*.figure_spec.json` sidecar.
- **Publication QC:** an advisory `check_publication_readiness(fig)` exists (figure-size, clipping,
  missing axis labels, small fonts, dense ticks, legend overlap). No scoring, no suggested fixes,
  no auto-fix, no UI button, no export gate, no test file. v0.6 extends this into a scored module.
- **Recommendations:** none today (only stats-test recommendation exists).

## 6. Proposed v0.6 modules

New / changed, grouped by workstream:

### A. Style → single `Publication`
- `styles/engine.py`: keep `publication` as the one user-facing profile; retain journal palette
  entries **only** as internal named-palette options (not as profiles). `list_profiles()` returns
  `["publication"]` (+ optional internal `publication_accessible`, `publication_grayscale` used by
  palette toggles, not shown as separate "styles"). Add `LEGACY_STYLE_ALIASES = {nature_like,
  science_like, cell_like, *_learned, journal_like → "publication"}` and apply in `load_profile`
  and in spec normalization so **old PlotSpecs still load** (with a one-time notice/warning).
- `spec/validate.py`: accept legacy names by normalizing before the `known_styles` check.
- Desktop `controller.STYLE_LABELS` / `styles()`, `main.py` style panel, Streamlit style selectbox,
  `help_content.py`: expose only **Publication**; advanced controls (font/line/marker/palette/legend/
  DPI/size + colorblind-safe / grayscale palette toggles) stay under Publication.

### B. Publication style engine upgrade
- `styles/publication_style_engine.py` (new): a thin, documented layer that produces the polished
  Publication token defaults (and the accessible/grayscale palette variants), plus per-plot-type
  refinements applied via existing style helpers. General improvements (margins, legend outside,
  colorbar sizing, volcano threshold/label typography, bracket/annotation styling, panel spacing)
  land in the **shared** helpers / tokens — never as per-plot hacks.
- `style_profiles/publication_default.json` + internal `publication_accessible.json`,
  `publication_grayscale.json`; `style_profiles/learned/v0_6_publication_learned.json` from
  aggregate benchmark lessons. `docs/V0_6_PUBLICATION_STYLE_LESSONS.md`.

### C. Publication QC scoring + gate
- `qc/publication_score.py` (new): `score_publication(result_or_fig, spec=None, report=None)` →
  `PublicationScore(level: pass|warn|fail, score, checks=[{id, level, message, suggestion,
  element}])`. Reuses/extends `qa/publication_check.py`. Adds: export DPI at chosen size, raster
  panel resolution, contrast, label crowding (heatmap rows, volcano labels, network density when
  present), missing method/stat report, missing units-where-expected.
- `qc/auto_fix.py`: `suggest_fixes` / `apply_fixes(spec)` for enlarge-figure, legend-outside,
  hide-excess-labels, increase-margins, increase-font, increase-DPI.
- UI: **Publication QC** button; pre-export warning dialog (Export anyway / Auto-fix / Review /
  Cancel). Never blocks experts.

### D. Recommendation engine
- `recommendations/` (new): `data_profiler.py` (shape, dtypes, missingness, dup IDs, group/subject/
  survival/pvalue/logFC/count-matrix/expression-matrix/correlation/adjacency/label-score/genomic/
  dose-response/network/mutation/enrichment detection), `schema_detector.py`, `plot_recommender.py`,
  `stat_recommender.py` (wraps existing `recommend_tests`), `recommendation_models.py`
  (`DataSpec`, `AnalysisSpec`, `RecommendationSpec`, `Recommendation`), `recommendation_runner.py`
  (single entrypoint `recommend_for_table(...)` and `recommend_after_analysis(...)`).
  **No `RnaSeqSpec`. No "run DE".** For count-like/numeric matrix + metadata → PCA, clustered
  heatmap, hierarchical clustering, sample-correlation heatmap, selected-feature plots, group
  comparison plots (when valid group/value columns exist). For precomputed differential tables
  (logFC + p/FDR) → volcano, MA (if avg-abundance column), top-feature table, top-feature heatmap
  (only if a compatible matrix is also uploaded), effect-size/summary plots.
- Each `Recommendation`: id, plot_type, confidence, why, required-mappings-found, missing-mappings,
  suggested statistics, suggested style (**Publication**), suggested thresholds, estimated render
  cost, warnings, one-click PlotSpec draft.
- Post-analysis: after stats / after a precomputed differential table is present, recommend
  annotated box/violin/raincloud (raincloud absent → box/violin), effect-size forest, multi-panel
  summary, volcano/MA/top-feature-heatmap/enrichment/forest as applicable.

### E. Recommendation UI (desktop + Streamlit)
- "Recommended Figures" panel: per-rec type/confidence/why/detected-columns/warnings + buttons
  Generate / Edit mappings / Add to Figure Builder / Save / Dismiss. Optional fast thumbnail.
- Settings: auto-show after upload (on/off), auto lightweight previews (on/off), **always** ask
  before expensive analysis (default on, cannot silently run heavy work).

### F. Windows performance / responsiveness (cross-cutting)
- `apps/desktop_app/workers.py` (new): `QThreadPool` + `QRunnable` `Task` wrapper with
  finished/error/progress signals; used for render, statistics, clustering, export.
- Lazy imports: make scipy import lazy in the stats test modules (import inside functions) so
  touching `statistics` doesn't eagerly pull scipy; keep statsmodels lazy (already is).
- Debounced rendering: a `QTimer` single-shot debounce on control changes (~150–250 ms).
- Preview vs final: `render(..., quality="preview"|"final")` — preview lowers raster/DPI and skips
  the most expensive polish; export always uses final. Stored in PlotSpec/output block.
- Canvas reuse: update the existing `FigureCanvasQTAgg` (swap figure) instead of destroy/recreate;
  keep toolbar wired.
- Data preview: shape/columns/dtypes/summary first; first N rows; guard very wide tables.
- Caching: `core/cache.py` (or `functools.lru_cache` + content hash) for data summaries, column
  detection, recommendations, clustering/layout keyed on inputs+settings; FB thumbnails.
- `scripts/benchmark_performance.py` + `outputs/performance/v0_6_performance_report.md`.

### G. License-safe benchmark recreation
- `benchmarks/publication_recreation/` (manifest.json, README.md, datasets/, recreated_panels/,
  style_notes/). Scripts: `curate_publication_benchmarks.py` (download license-safe public data,
  checksum, provenance; **skip gracefully** offline; never fetch prohibited content),
  `recreate_publication_panels.py` (render via the app's normal path, export PNG/SVG/PDF/PlotSpec,
  run publication QC), `evaluate_publication_recreations.py` (checklist-based; optional similarity
  only if a license-permitted reference image exists).
- ≥10 license-safe datasets; ≥10 **generic** panel types (volcano/MA from *precomputed* tables,
  heatmap/PCA/clustering from matrices, KM, grouped box/violin+stats, scatter/regression, enrichment
  dot, forest, ROC/PR, waterfall, oncoprint/lollipop). Never labeled "RNA-seq workflow."
  `V0_6_BENCHMARK_RECREATION_REPORT.md`.

### H. Gallery + tests + docs + version
- `outputs/publication_qc/v0_6/` gallery + README. Comprehensive tests (below). Docs. Version 0.6.0.

## 7. Testing / QC strategy

- **Unit:** style migration (legacy names → Publication), publication_score checks (missing labels,
  small raster, dense heatmap/network, low DPI), auto-fix effects, data_profiler schema detection
  per data type, plot_recommender outputs per data type (matrix, matrix+metadata, precomputed
  differential table, survival, classification, network edge list, GWAS, dose-response, paired,
  enrichment), stat_recommender, recommendation_runner end-to-end draft PlotSpec renders.
- **Regression:** existing statistics, renderers, styles, grouping, de_detect, multipanel, loaders,
  validate, examples, packaging must still pass. Desktop launches; Streamlit imports.
- **String-scan test:** fail if user-facing UI/docs contain `Nature-like|Science-like|Cell-like|
  journal-like` (allow clearly-marked historical changelog entries). Also assert no RNA-seq
  analysis terms are advertised as capabilities.
- **GUI (offscreen):** recommendations panel appears after load; Generate creates a plot; generated
  plot adds to Figure Builder; warnings visible; expensive analysis requires confirmation; only
  `Publication` style shown.
- **Performance:** `benchmark_performance.py` runs; long tasks use workers where implemented;
  profiling completes quickly on examples.
- **Benchmark:** manifest validates; ≥10 entries each with provenance + license; curate script
  skips gracefully offline; recreate works on available/synthetic-fallback data and emits
  PlotSpec + figure + QC report.

Run commands (Mac/Linux/Windows):
```
python -m pytest -p no:pytest-qt --ignore=tests/test_desktop_gui.py     # non-GUI
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_desktop_gui.py     # GUI (Linux CI needs libEGL)
```

## 8. Acceptance criteria (v0.6.0)

1. Windows sluggishness profiled; meaningful fixes implemented or documented.
2. Long tasks don't freeze the desktop UI where feasible (background workers + progress).
3. Publication default style visibly improved.
4. Publication QC scoring + warnings exist (module + UI + export gate).
5. ≥10 license-safe benchmark datasets curated/prepared (or graceful skip with provenance recorded).
6. ≥10 publication-style panels recreated from data via the app path.
7. Benchmark provenance + license metadata documented.
8. Benchmark recreation report exists.
9. General style improvements extracted from benchmark work (learned Publication defaults).
10. Recommendation engine profiles uploaded data.
11. Recommendations work for matrices, metadata, precomputed differential tables, statistics
    outputs, and common scientific schemas — **without** recommending RNA-seq DE.
12. User can click a recommended plot and generate it.
13. Generated recommended plot can be saved or added to Figure Builder.
14. Expensive analyses require confirmation.
15. All existing features still work (statistics, Figure Builder, imported panels, grouping, volcano).
16–21. Statistics/renderer/style/grouping/multipanel tests pass; desktop launches; Streamlit imports.
22. Visual QA gallery exists.
23. Docs updated (no journal-specific or RNA-seq-analysis claims; cautions added).
24. Known limitations documented.
25. Commit created (`Add v0.6 publication benchmarks recommendations and performance QC`).
26. Push status reported. **No public tag/release without explicit approval.**

Plus (from corrections): only `Publication` in UI; no journal claims in docs; old PlotSpecs with
removed names still load; no RNA-seq analysis workflow present; no `RnaSeqSpec`; no R/edgeR/limma/
voom dependency; precomputed differential tables still drive volcano/MA; generic matrices still
drive heatmap/PCA/clustering/recommendations.

## 9. Sequencing (self-QC loop)

1. ✅ Audit repo + write this plan.
2. Style simplification → Publication (+ backward-compat migration + tests).
3. Publication style engine upgrade (general defaults) + learned profile.
4. Publication QC scoring module + auto-fix + tests; wire QC button + export gate.
5. Recommendation engine core + models + tests.
6. Recommendation UI (desktop + Streamlit) + expensive-analysis confirmation.
7. Windows performance: lazy scipy, debounce, canvas reuse, background worker, preview/final,
   table summary-first, caching; `benchmark_performance.py` + report.
8. Benchmark system: manifest + scripts + ≥10 datasets (graceful) + recreate + evaluate + report.
9. Visual QA gallery.
10. Full test suite; fix; docs; version 0.6.0 + changelog.
11. Commit; report push status. No public release.

**Honesty gates:** do not claim readiness if figures still look exploratory; do not mark a
benchmark recreation "passed" if the scientific content/method is wrong; do not mark the
recommendation engine "passed" if it suggests inappropriate plots with high confidence; never
label recreations "exact" unless legal and true — use "publication-grade recreation" /
"scientifically equivalent reproduction" / "style-aligned recreation".
