# Milestone 1 Summary — Make My Figure

Date: 2026-06-30

## What was built

A working core engine + dashboard for five publication-style plot types.

### Repository structure
```
make_my_figure/
  io/loaders.py          # CSV/TSV/XLSX loading, delimiter sniffing, ID-as-string, missing-value reporting
  spec/validate.py       # PlotSpec validation vs schemas/plot_spec.schema.json + app-level checks
  styles/engine.py       # Journal-like style profiles -> rcParams, palettes, mm sizing
  plots/
    base.py              # RenderResult, stats helpers (SEM/SD/CI95), figure sizing, metadata
    barplot.py           # bar plot with error bars
    grouped_barplot.py   # grouped bar plot with error bars
    heatmap.py           # clustered heatmap (SciPy linkage)
    volcano.py           # volcano plot with cutoffs + labels
    scatter.py           # scatter with optional regression
    registry.py          # plot registry, default mappings, render(), export, sidecar
app/streamlit_app.py     # dashboard: upload/sample -> map -> style -> preview -> export
scripts/generate_examples.py
tests/                   # 42 tests (loaders, validation, styles, renderers, app smoke)
docs/QUICKSTART.md
reports/example_figures/ # rendered PNG/SVG examples
pyproject.toml, requirements.txt, LICENSE, .gitignore
```

### Capabilities delivered
- **Loaders**: delimiter inference, sample/ID columns preserved as strings, numeric vs
  categorical detection, missing-value counts, clear `LoaderError` messages. Bytes and
  file-like (Streamlit upload) inputs supported. XLSX via openpyxl.
- **Validation**: JSON Schema (Draft 2020-12) validation against the bundled
  `plot_spec.schema.json`, plus app-level checks for known plot types and known styles;
  collects all errors with field locations.
- **Style engine**: three starter profiles (`nature_like`, `science_like`, `cell_like`)
  driven entirely by tokens — fonts, line/spine widths, column widths in mm,
  colorblind-aware (Okabe–Ito-based) palettes, diverging/sequential colormaps. SVG/PDF
  text kept editable (`svg.fonttype=none`, `pdf.fonttype=42`).
- **5 renderers**, each returning a figure + metadata record (columns used, stats,
  style, export dims, disclaimer). No renderer mutates input data (test-enforced).
- **Dashboard**: data source picker (bundled sample or upload), table preview +
  warnings, plot/style/column mapping, label & size controls, live preview, and
  downloads for SVG / PNG / PDF / PlotSpec JSON. Errors are surfaced, never silent.
- **Reproducibility sidecar**: `*.plot_spec.json` written alongside every exported figure.

## How it was tested

`pytest -q` → **42 passed**.
- `test_loaders.py`: CSV/TSV/XLSX, delimiter inference, ID-as-string, missing values, empty input.
- `test_validate.py`: schema load, valid/invalid specs, unknown plot type/style, bad format enum.
- `test_styles.py`: profiles present, tokens, palette cycling, sizing, editable-text rcParams.
- `test_renderers.py`: all 5 plot types × 3 styles render and export SVG/PNG/PDF + sidecar;
  no-mutation contract; volcano/scatter/heatmap/bar specific assertions; clear error on missing column.
- `test_app_smoke.py`: Streamlit `AppTest` runs the dashboard for every sample plot type with no exception.

Headless `streamlit run` boot check returned HTTP 200.

## Constraints honored
- No papers, DOIs, figures, or journal rules fabricated.
- No copyrighted assets downloaded; only bundled synthetic mock data used.
- Style profiles are explicitly "*-like" with a disclaimer in metadata and UI; no claim of
  official Nature/Science/Cell compliance.

## What remains for Milestone 2
- Remaining manuscript plot types from the manifest: box/violin+points, line/time-course with
  error band, enrichment dot plot, Kaplan–Meier, stacked composition, waterfall, PCA scatter,
  oncoprint, lollipop, ROC, forest, ridge/density.
- Panel labels (A/B/C), multi-panel figure composition, and legend-placement controls.
- Statistical annotations (significance brackets) where valid; TIFF/EPS export surfaced in UI.
- Non-overlapping volcano/scatter label placement (current labels can collide when dense).
- CLI (`makefig render`, `makefig app`) and CI workflow under `.github/workflows/`.
- GitHub Pages docs site build.
- Phases 4+ (post-2020 open-access paper/figure/data curation pipeline) — not started.
