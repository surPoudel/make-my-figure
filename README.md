# Make My Figure

A research-software app that turns a CSV/TSV/XLSX table into a manuscript-style
scientific figure with **Nature-like / Science-like / Cell-like** aesthetics, and
exports SVG/PNG/PDF plus a reproducible `PlotSpec` JSON sidecar.

> These are *-like style profiles only — not official journal templates, and not a
> guarantee of submission compliance.

**Milestones 1 & 2 are implemented**: loaders, schema validation, style engine,
and **all 17 plot types** from the mock-data manifest (bar/grouped bar, box/violin,
line/time-course, ridge, scatter, heatmap, volcano, enrichment dot plot, Kaplan-Meier,
stacked composition, waterfall, PCA, oncoprint, lollipop, ROC, forest).
See **[docs/QUICKSTART.md](docs/QUICKSTART.md)** to install and run, and the
**[reports/](reports/)** summaries for status.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run apps/streamlit_app/streamlit_app.py   # web dashboard
pytest -q                                           # tests
```

**Milestone 4** refactors the engine into a reusable core package
(`make_my_figure_core/`) shared by two frontends, and adds a **zero-command
desktop app** (PySide6) for non-technical users — open a file, pick a plot type
and style, preview, and export SVG/PNG/PDF/PlotSpec JSON. See
**[docs/DESKTOP_APP.md](docs/DESKTOP_APP.md)** and
**[docs/BUILD_INSTALLERS.md](docs/BUILD_INSTALLERS.md)**.

```bash
pip install -e ".[desktop]"
python -m apps.desktop_app.main          # run desktop app from source
python scripts/build_desktop.py          # build a standalone app (see build docs)
```

### Layout
```
make_my_figure_core/   reusable engine (loaders, validation, styles, renderers,
                       export, provenance, mock-data + UI hints)
apps/streamlit_app/    web/developer frontend
apps/desktop_app/      PySide6 desktop frontend (controller.py + main.py)
examples/              synthetic example/template dataset for every plot type
```

### Example / template data

Every supported plot type ships with a clean **synthetic** example dataset
(CSV/TSV/XLSX + PlotSpec + README) under `examples/by_plot_type/`, plus a combined
workbook and a machine-readable manifest. Use them via **Use example data** in
either app, or **Save template** to export a table and replace it with your own data.

```bash
python scripts/generate_example_data.py   # regenerate all examples (seed 42, CC0)
```

Docs: **[EXAMPLE_DATA.md](docs/EXAMPLE_DATA.md)** ·
**[DATA_TEMPLATES.md](docs/DATA_TEMPLATES.md)** ·
**[PLOT_TYPE_REQUIREMENTS.md](docs/PLOT_TYPE_REQUIREMENTS.md)**. Published papers/figures
are used only as visual style references; bundled example data are synthetic and must
not be cited as real findings.

**Milestone 3** adds a license-aware, HTTPS-only harvesting pipeline that builds a
curated library of open-access, post-2020 Nature/Science/Cell-family papers,
downloading figures + data **only** under CC BY / CC BY-SA / CC0 (license confirmed
by two independent sources), with full provenance. See **[docs/HARVEST.md](docs/HARVEST.md)**.

```bash
python scripts/harvest_library.py --out figure_library --papers 10
```

---

## Prompt and mock-data bundle

This bundle also contains a Claude Code master prompt plus reproducible mock input tables for a manuscript-style scientific figure app.

## Contents

- `claude_code/CLAUDE_CODE_MASTER_PROMPT.md` — full implementation prompt for Claude Code.
- `claude_code/LAUNCH_PROMPT_SHORT.md` — shorter prompt that points Claude Code to the full prompt.
- `mock_data/` — CSV/TSV examples for common high-impact biology/biomedical plot types.
- `mock_data/plot_schema_manifest.json` — machine-readable map of plot types, file paths, required columns, and suggested defaults.
- `schemas/plot_spec.schema.json` — starter JSON schema for figure specifications.
- `style_profiles/starter_journal_style_profiles.json` — starter journal-like style tokens; these are not official journal templates.
- `make_my_figure_mock_data.xlsx` — workbook version of the same mock tables for users who prefer Excel.

## How users should replace mock data

For each table, keep the required column names and replace the rows with real data. The app should also allow users to map their own column names to the required roles. Do not assume column order; validate by column name and type.

## Plot types covered

- barplot_with_error_bar: `mock_data/barplot_error_raw.csv`
- grouped_barplot_with_error_bar: `mock_data/grouped_barplot_error.csv`
- boxplot_or_violin_with_points: `mock_data/box_violin_points.csv`
- scatterplot_with_regression: `mock_data/scatter_regression.csv`
- lineplot_timecourse_with_error_band: `mock_data/line_timecourse.tsv`
- heatmap_clustered_matrix: `mock_data/heatmap_expression_matrix.tsv`
- volcano_plot: `mock_data/volcano_plot.csv`
- enrichment_dotplot: `mock_data/enrichment_dotplot.csv`
- kaplan_meier_survival_curve: `mock_data/survival_km.csv`
- stacked_bar_composition: `mock_data/stacked_composition.csv`
- waterfall_plot: `mock_data/waterfall_response.csv`
- pca_scatter_from_matrix: `mock_data/pca_expression_matrix.tsv + mock_data/pca_sample_metadata.csv`
- oncoprint_mutation_heatmap: `mock_data/oncoprint_long.csv`
- lollipop_mutation_plot: `mock_data/lollipop_mutations.csv`
- roc_curve: `mock_data/roc_curve_scores.csv`
- forest_plot: `mock_data/forest_plot.csv`
- ridge_or_density_plot: `mock_data/ridge_density.csv`

## Reproducibility

All mock data were generated with a fixed random seed (`42`) and are synthetic. They are safe to redistribute and are not derived from real patient data or copyrighted figures.

## Legal note for paper/figure harvesting

The Claude Code prompt requires open-access/license-aware harvesting. The app should not bundle third-party figures or data unless the license clearly permits it and provenance is stored.
