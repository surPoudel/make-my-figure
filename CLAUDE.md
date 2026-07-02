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
- Statistics/p-value features are on the roadmap and **not implemented** — don't fabricate them.
