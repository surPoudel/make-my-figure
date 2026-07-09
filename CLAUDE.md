# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Make My Figure turns tabular data (CSV/TSV/XLSX) into publication-style scientific
figures. The reusable engine lives in `make_my_figure_core/` and is frontend-agnostic;
two GUIs (`apps/streamlit_app/`, `apps/desktop_app/`) consume it. There are 17 plot
types, journal-*like* style profiles, and a reproducibility sidecar (PlotSpec JSON).

> The `nature_like` / `science_like` / `cell_like` profiles are visual aesthetics only —
> not official journal templates. Never present them as guaranteeing journal compliance.
> This disclaimer is baked into rendered metadata (`base_metadata` in `plots/base.py`) —
> keep it.

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # core + streamlit + pytest
pip install -e ".[desktop]"              # adds PySide6 for the desktop app

# Run the apps
streamlit run apps/streamlit_app/streamlit_app.py
python -m apps.desktop_app.main

# Tests (pytest-qt drives the desktop GUI tests)
pytest                                    # full suite (testpaths=tests, see pyproject.toml)
pytest tests/test_renderers.py            # one file
pytest tests/test_renderers.py -k volcano # one test / pattern
pytest -k "not gui"                       # skip Qt GUI tests if PySide6 is absent

# Regenerate bundled data / assets (run after changing renderers or example schemas)
python scripts/generate_example_data.py   # rebuilds examples/ + example_data_manifest.json
python scripts/generate_stats_examples.py # rebuilds examples/statistics/ (11 stats workflows)
python scripts/generate_stats_qa_gallery.py  # reports/stats_qa_gallery.png (visual QA)
python scripts/generate_rnaseq_examples.py   # rebuilds examples/rnaseq/ (DE/matrix/raw-count)
python scripts/generate_rnaseq_qa_gallery.py # reports/rnaseq_qa_gallery.png (visual QA)
python scripts/build_learned_styles.py    # derives style_profiles/learned/*.json from figure_library/
python scripts/harvest_library.py --papers 10   # CC-BY-only figure harvest (network)

# Desktop installers
python scripts/build_desktop.py           # or scripts/build_{windows.ps1,macos.sh,linux.sh}
```

The version is defined once in `make_my_figure_core/version.py`; `pyproject.toml` reads it
dynamically and the desktop About dialog imports it. Bump it there only.

## Architecture

Data flows: **loader → PlotSpec (validated) → renderer → RenderResult → export/sidecar**.

- `plots/registry.py` is the single wiring hub and the import surface for both GUIs and
  tests. It holds `_RENDERERS`, `_DEFAULT_MAPPINGS`, `_DISPLAY_NAMES`, and the `render()`
  entrypoint. `render()` validates the spec, resolves the style profile, applies
  `style.with_overrides(spec["style"])`, dispatches to the renderer, then runs an advisory
  publication-readiness check. Everything the frontends need is re-exported from
  `make_my_figure_core/__init__.py`.

- **Adding a plot type** means touching several files in lockstep: create
  `plots/<name>.py` with a module-level `PLOT_TYPE` constant and a
  `render(spec, df, style)` function; register it in `plots/registry.py` (`_RENDERERS`,
  `_DEFAULT_MAPPINGS`, `_DISPLAY_NAMES`); add its column/option hints to `ui_hints.py`
  (so both GUIs pick it up without GUI-specific code); add a mock sample in `mock_data/`
  wired into `tests/conftest.py`'s `PLOT_SAMPLES`; and regenerate examples.

- **Renderer contract** (`plots/base.py`): each renderer receives a validated spec dict, a
  DataFrame, and a resolved `StyleProfile`, and returns `RenderResult(figure, metadata,
  warnings)`. Renderers must **never mutate the input DataFrame** (copy first — see
  `barplot.py`). Pull styling from style *tokens* (font sizes, widths, palette) via the
  shared helpers (`figure_size`, `style_axes`, `place_legend`, `summarize_error`,
  `base_metadata`, `require_columns`, `coerce_numeric`) rather than hard-coding — this is
  what keeps every plot consistent within a profile. Renderers needing extra tables (e.g.
  PCA metadata) declare an `aux` parameter; the registry only passes `aux` when the
  signature has it (`inspect.signature` check).

- **Style engine** (`styles/engine.py`): `StyleProfile` is a dataclass of publication-ready
  token defaults. Three sources of profiles: the built-in `publication` default; starter
  profiles from `style_profiles/starter_journal_style_profiles.json`; and *learned*
  profiles from `style_profiles/learned/*.json`. Note the starter JSON's ~7pt journal print
  sizes are intentionally ignored — only palette, colormaps, and column widths are taken
  from it; the readable dataclass defaults win. GUI/PlotSpec overrides flow through
  `with_overrides` (including `palette_name` → `NAMED_PALETTES`).

- **Validation** (`spec/validate.py`): jsonschema Draft 2020-12 against
  `schemas/plot_spec.schema.json` (the schema is deliberately permissive), plus app-level
  checks (known plot type / known style) for actionable messages.

- **Export** (registry): `export_figure` / `figure_to_bytes` / `export_bundle_bytes` wrap
  savefig in `_VECTOR_TEXT_RC` so SVG/PDF text stays **editable** (not outlined). Every
  export writes a `.plot_spec.json` sidecar (`write_sidecar`) recording spec + metadata for
  reproducibility.

- **Desktop app**: `apps/desktop_app/controller.py` holds all GUI-free logic (load, list
  types/styles, build spec, render, export) and is unit-tested without a Qt event loop;
  `main.py` is the thin PySide6 layer that must not touch plotting internals directly.

- **Resource resolution** (`resources.py`): `resource_path()` resolves bundled folders
  (`schemas/`, `style_profiles/`, `mock_data/`, `examples/`) for both dev checkouts and
  PyInstaller-frozen builds (`sys._MEIPASS`). Never hard-code dev-only paths to these; set
  `MAKE_MY_FIGURE_RESOURCES` to override the base in tests.

- **Statistics** (`statistics/`): a frontend-agnostic engine. `run_statistics(df,
  stats_spec, plot_type, mapping)` (in `runner.py`) is the single entrypoint both apps
  call; it resolves comparisons, dispatches to the test modules (`pairwise`, `anova`,
  `nonparametric`, `categorical`, `survival`), applies multiple-testing correction across
  the pairwise family, and returns a `StatsReport` of `StatResult`s. **Invariant: every
  p-value drawn on a figure comes from a stored `StatResult`** — renderers never format
  p-values themselves. Uses scipy + statsmodels only (log-rank, Dunn's, and effect sizes
  are native; no lifelines/scikit-posthocs). Config is a `StatsSpec` dict (see
  `schemas.py`) embedded in the PlotSpec under `statistics`; exports write a
  `*.stats_spec.json` sidecar. Correctness is pinned against scipy/statsmodels in
  `tests/test_statistics_core.py`.

- **Stats on renderers**: renderers compute per-category x-positions + data tops and call
  `plots/stats_integration.run_and_annotate(...)`, which runs stats and draws via the
  shared bracket engine `plots/stats_overlay.py` (auto-stacking, y-limit expansion). The
  report rides out on `RenderResult.stats_report` and is serialized into
  `metadata["statistics_report"]` (note: `base_metadata` separately echoes the raw config
  under `metadata["statistics"]` — don't confuse the two). Integrated in: barplot,
  box_violin, grouped_barplot (within-x brackets), scatter/survival/stacked (corner panels).

- **RNA-seq** (`rnaseq/`): three input modes behind one detection entrypoint
  (`detect.detect_input_mode`). Mode A precomputed DE table → `de_table.parse_de_table` +
  `classify_de` + `volcano_spec_from_de` (p-values read verbatim, never recomputed). Mode B
  normalized matrix → `expression.build_expression_matrix` + transforms/gene-selection +
  `heatmap_spec_from_expression` (feeds the core heatmap renderer; optional sample-annotation
  strips via `spec["column_annotations"]`). Mode C raw counts + metadata → `runner.run_de_pipeline`
  shells out to R (subprocess **arg list**, never a shell string) running one of `rscript.DE_SCRIPTS`:
  `edger_limma_voom` (**edgeR TMM+filter + limma-voom + eBayes moderated t**, generalizes
  `test_matrix/pipeline_*.R`) or `deseq2` (**DESeq2 median-of-ratios + NB GLM + Wald**, VST matrix);
  select via `run_de_pipeline(..., method=)`. Both add covariates/batch and normalize output columns
  to one schema (`logFC/AveExpr/t/P.Value/adj.P.Val`) so plotting is method-agnostic.
  `check_r_environment(method=)` gates it; missing R/packages raises `RDependencyError` — **never a
  t-test fallback**. `r_setup.install_r_environment()` is the on-demand installer (downloads
  micromamba, builds a private conda env with r-base + bioconductor-edger/limma/deseq2 in the app-data
  dir); `find_rscript` prefers `MAKE_MY_FIGURE_RSCRIPT` → managed env → PATH, so the base installer is
  never bloated with R. `spec.RnaSeqSpec` is the reproducibility record. `load_rnaseq_table`
  promotes R's unnamed row-name (gene id) into a `gene_id` column. Loaders' index inference already
  lands that id as the frame index; detection relies on it. R is optional and usually absent in
  dev/CI, so R-dependent tests skip. GUI: `apps/desktop_app/rnaseq_panel.py` (`RnaSeqDialog`) and
  `apps/streamlit_app/rnaseq_view.py`.

- **Statistics annotations** (`statistics/method_reporting.py`): `render_annotation(result, cfg)`
  is the single label builder — content modes (stars/p/p_adj/stat/effect/combos/full/flags) and a
  custom `{token}` template via `annotation_tokens` (bare values). Only reads stored `StatResult`
  values; hiding a field on the figure never drops it from the exported StatsSpec. Config lives in
  the annotation block (`schemas.default_annotation`), back-compatible with the old `mode`.

- **App navigation**: desktop `MainWindow.reset_to_upload()` (File → Home / Upload New Data, or the
  workbench button) clears data/spec/result/stats/rnaseq and returns to the welcome page without
  restart — distinct from the Matplotlib toolbar `home` (zoom/pan reset). Streamlit clears
  `st.session_state` + reruns.

- **Multi-panel** (`panels/`): `build_figure(MultiPanelFigure)` composes panels (rendered
  from their PlotSpecs) into a labelled grid; panel content is embedded as `panel_dpi`
  raster while labels stay vector. `export_multipanel` + `multipanel_sidecar` write the
  figure and a `*.figure_spec.json`. Desktop UI: `apps/desktop_app/stats_panel.py` holds
  both the `StatisticsPanel` and `FigureBuilderDialog` (thin Qt over the controller/core).

- **Harvest** (`harvest/`): a license-gated, HTTPS-only pipeline that downloads figures/data
  **only** from CC BY/CC BY-SA/CC0 open-access papers into `figure_library/` (git-ignored).
  It derives *aggregate* visual conventions for learned profiles — it never copies or
  reproduces published figures. Keep that boundary intact.

## Conventions

- `examples/` (per-plot templates, committed) is generated from `scripts/generate_example_data.py`
  and read via `examples.py` + `example_data_manifest.json` — edit the generator, not the
  outputs. `mock_data/` holds the golden test inputs.
- `app/` (singular) is a stale empty leftover; the live frontends are under `apps/` (plural).
- Statistics, annotations, multi-panel, and RNA-seq are **implemented** (see the sections above).
  The invariant across all of them: **never fabricate a statistic/p-value** — every value shown
  comes from a stored result, and RNA-seq DE never falls back to a t-test when R is absent.
- `test_matrix/` holds the user's real RNA-seq example inputs (DE table, voom matrix, metadata,
  config, reference R script). `examples/rnaseq/` holds small committed synthetic/derived copies
  used by tests; R-dependent tests skip when `Rscript` is unavailable.
