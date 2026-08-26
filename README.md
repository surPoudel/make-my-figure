# Make My Figure

**Publication-ready scientific plots and multi-panel figures from common data tables.**

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Plot types](https://img.shields.io/badge/plot%20types-37-blueviolet)
![Style](https://img.shields.io/badge/style-Publication-8a2be2)
![Platforms](https://img.shields.io/badge/platforms-macOS%20%7C%20Windows%20%7C%20Linux%2FWSL-lightgrey)

---

## 1. Overview

Make My Figure turns tabular data (CSV / TSV / XLSX) into polished scientific plots
and multi-panel figures. Upload a table, pick a plot, confirm how your columns map to
the plot, and get a clean, consistent, export-ready figure — without writing custom
plotting code or hand-fixing every axis, legend, font, and export.

It is for researchers, students, and analysts who want **publication-quality plots
quickly and reproducibly**, with sensible defaults and full control when they need it.

## 2. Key principles

- **Local-first** — runs on your machine; no cloud upload, no telemetry.
- **Deterministic Python** — plots and statistics are computed with numpy / pandas /
  scipy / statsmodels; same input, same output.
- **User-confirmed mapping** — the app suggests column roles but never silently guesses;
  you confirm before anything is plotted or analyzed.
- **One visible style: Publication** — a general, manuscript-ready visual style.
- **Traceable statistics** — every p-value/FDR/effect drawn on a figure comes from a
  stored result you can export.
- **Reproducible specs** — every export writes a JSON sidecar describing exactly what
  was made.
- **High-quality export** — PNG (high-DPI), and vector PDF / SVG with editable text.
- **No silent preprocessing** — you confirm every transform; the original data are kept.
- **No AI/API required** and **no R required** for the core workflow.

## 3. What you can make

38 plot types, grouped by what you're trying to show:

- **Basic comparisons** — bar, grouped bar, box, violin, dot/strip, beeswarm, raincloud.
- **Distributions** — histogram (binned counts, as panels per group or overlaid, with a
  frequency-polygon option) and ridge/density (smoothed). Reach for the histogram when
  the shape matters: a density estimate can render two modes as one shoulder.
- **Relationships** — scatter, scatter with regression readout, correlation heatmap,
  Bland–Altman.
- **Time / trajectory** — line & time-course (with error band), paired slopegraph,
  swimmer, spider/radar.
- **Matrix & omics-style** — heatmap, clustered heatmap, PCA, hierarchical dendrogram,
  MA plot, volcano (from a precomputed table or a computed feature-level summary).
- **Statistical / model** — forest, ROC, precision–recall, calibration, confusion
  matrix, Kaplan–Meier.
- **Genomics-style summaries** — Manhattan, Q–Q, oncoprint, lollipop.
- **Composition / set / flow / network** — stacked composition, UpSet, Sankey/alluvial,
  network graph.
- **Other** — enrichment dot plot, waterfall, dose–response, and embedding scatter
  (UMAP/t-SNE) **from precomputed coordinates**.

## 4. Typical workflows

**A. Table → plot.** Upload data → choose a plot → map columns (suggested, you confirm)
→ preview → adjust Publication settings → export PNG/SVG/PDF plus a PlotSpec JSON.
Multi-sheet Excel workbooks show a **Worksheet** dropdown (every sheet selectable —
notes/empty included); the selected sheet drives everything and exports are named per
worksheet. See [docs/MULTI_SHEET_EXCEL.md](docs/MULTI_SHEET_EXCEL.md).

**B. Matrix workflow.** Upload a feature-by-sample matrix → explicitly map feature /
annotation / sample-value columns → upload or build sample metadata → validate groups →
get plot recommendations → generate heatmap / PCA / correlation / selected-feature
plots → optionally compute a feature-level differential summary → generate volcano / MA
/ ranked-effect plots.

**C. Raw-like matrix QC & preprocessing.** Run QC diagnostics → inspect value
distributions, per-sample boxplots, missingness, zero fraction, sample totals, sample
correlation, PCA, mean–variance → choose a preprocessing workflow → **confirm before
applying** → create a derived matrix → compare before/after QC → use the derived matrix
downstream. Nothing is applied silently; the original matrix is preserved.

**D. Statistics & annotations.** Choose a test → confirm groups → compute
p-values / FDR / effect sizes → add significance brackets and labels → export a
StatsSpec and a method sentence.

**E. Figure Builder.** Add generated plots (or imported panels) → arrange a grid → add
panel labels → export a multi-panel figure with a figure spec.

## 5. Publication style

There is **one visible style: Publication** — a general manuscript-ready look with an
**Arial-first font stack and safe fallbacks** (`Arial → Helvetica → DejaVu Sans →
sans-serif`; no font files are bundled), colorblind-aware palettes (including a fully
monochrome black-and-white option), readable margins and spacing, label-spacing and
tick-rotation controls, and vector-safe export.

Style controls are **plot-aware**: a control either affects the active plot or is
flagged/disabled with a reason — no control silently does nothing (see
[docs/PLOT_STYLE_CONTROLS.md](docs/PLOT_STYLE_CONTROLS.md)).

> Publication is a general visual style, **not** an official journal template, and it
> makes **no claim** of compliance with any journal's formatting requirements. Always
> check your target journal's own author guidelines.

## 6. Data mapping & safety

- The app **suggests** column roles but does not silently guess — you confirm them.
- **Annotation columns are never treated as sample/measurement values.**
- **No silent normalization** and **no silent statistics** — you opt in and confirm.
- Every p-value shown on a figure comes from a **stored result**, never fabricated.

## 7. Statistics

Implemented with scipy + statsmodels (no R). Supported methods include: Student's and
Welch's t-tests, Mann–Whitney U, paired t-test, Wilcoxon signed-rank, one-way ANOVA,
Kruskal–Wallis, Dunn's post-hoc, chi-square, Fisher's exact, log-rank and Cox
proportional-hazards, Pearson/Spearman correlation, linear regression, and a
generalized linear model (GLM) regression (Gaussian / binomial / Poisson /
negative-binomial / Gamma). Multiple-testing correction: Benjamini–Hochberg, Bonferroni,
Holm. Effect sizes and confidence intervals are reported where implemented.

You are responsible for choosing a scientifically appropriate test. Configuration is
captured in a **StatsSpec**, results in a stored table, and a **method sentence**
describes what was run (including any preprocessing). Volcano/MA plots can use the raw
**p-value** or the adjusted **p-value / FDR** where available, and the choice is stored
in the spec. See [docs/STATISTICS.md](docs/STATISTICS.md) and
[docs/FEATURE_LEVEL_STATISTICS.md](docs/FEATURE_LEVEL_STATISTICS.md).

## 8. Reproducibility

Every export writes a JSON sidecar so a figure can be traced and rebuilt. The specs:

- **PlotSpec** — the plot type, mapping, style, and options.
- **StatsSpec** — the statistics configuration and results.
- **MatrixSpec** / **MetadataSpec** — confirmed matrix column roles and sample→group map.
- **PreprocessingSpec** — the exact, ordered preprocessing chain applied to a matrix.
- **FigureSpec** — multi-panel figure layout.

Results tables and method sentences are exportable alongside the figures.

## 9. Installation

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install -e ".[desktop]"     # adds the desktop GUI (PySide6)
```

Optional extras (only these exist):

- `desktop` — the PySide6 desktop app.
- `dev` — test tooling (`pytest`, `pytest-qt`).
- `count-de` — an **optional, Python-only** count-model differential path (PyDESeq2).
  Never required; no R.

## 10. Running the apps

**Streamlit (web UI)** — no Qt required:

```bash
python -m pip install -e .
streamlit run apps/streamlit_app/streamlit_app.py --server.fileWatcherType none
```

**Desktop (PySide6)** — requires the `desktop` extra:

```bash
python -m pip install -e ".[desktop]"
python -m apps.desktop_app.main
```

**Desktop on WSL/Linux** also needs Qt system libraries (otherwise you'll see
`Failed to import Qt binding modules` — the app now prints this exact guidance):

```bash
sudo apt install -y libxkbcommon0 libxkbcommon-x11-0 libgl1 libegl1 \
    libxcb-cursor0 libxcb-xinerama0 libxcb-keysyms1 libxcb-randr0 \
    libxcb-render-util0 libxcb-shape0 libxcb-icccm4 libxcb-image0 \
    libxcb-xfixes0 libdbus-1-3
python -m pip install -e ".[desktop]"
python -m apps.desktop_app.main
```

Build a desktop installer for your OS (build/test the Windows `.exe` from native
Windows Python, not WSL):

```bash
python scripts/build_desktop.py
```

Both frontends use the **same core renderer and PlotSpec**, so a figure looks the same
whether you build it in Streamlit or the desktop app.

**Performance note.** Under WSL, `/mnt/c` (Windows drive) and OneDrive-synced folders
are slow for file I/O. For responsive development keep the repo and data on the local
filesystem — `~/Developer/make_my_figure` on macOS/Linux/WSL, `C:\Developer\make_my_figure`
on Windows — and run Streamlit with the file watcher off on synced folders:

```bash
streamlit run apps/streamlit_app/streamlit_app.py --server.fileWatcherType none
```

Both apps show a build banner (Streamlit sidebar / desktop status bar) with the version,
git commit, platform, and backend, so you can confirm you're running the code you pulled.

## 11. Quick verification

```bash
python -m pytest -q
python scripts/run_cross_platform_qc.py --output reports/release_cross_platform_qc/current_platform
```

The QC harness renders every plot type deterministically and writes a report
(`qc_report.md`, `qc_summary.csv`, `platform_manifest.json`) you can compare across
platforms — see [docs/CROSS_PLATFORM_QC.md](docs/CROSS_PLATFORM_QC.md). (If the
`pytest-qt` plugin can't load Qt on a headless Linux box, run
`python -m pytest -q -p "no:pytest-qt" --ignore=tests/test_desktop_gui.py`.)

## 12. Privacy

- The desktop app runs entirely locally.
- **No telemetry, no cloud upload.**
- **No AI/API is required** for core plotting or statistics.
- Your data stay on your machine; exports are written where you choose.

## 13. Limitations

- Publication is a general style, **not** an official journal template, and does not
  guarantee compliance with any journal.
- Make My Figure is a plotting and reporting tool, **not a substitute for statistical
  review** — you choose the appropriate methods.
- Very large matrices may need filtering / top-variable-feature selection for responsive
  heatmaps and networks.
- Recreating a specific published figure exactly requires the original source data,
  methods, dimensions, fonts, and clear licensing.
- Cross-platform output may differ slightly in fonts/spacing depending on installed
  fonts and the Matplotlib backend.
- The optional count-model differential path is Python-only and entirely optional; **no
  R is used anywhere.**

## 14. Documentation

- [Quickstart](docs/QUICKSTART.md)
- [Multi-sheet Excel workbooks](docs/MULTI_SHEET_EXCEL.md)
- [Matrix workflow](docs/MATRIX_WORKFLOW.md)
- [Raw-like QC & preprocessing](docs/PREPROCESSING_QC.md) ·
  [Normalization methods](docs/NORMALIZATION_METHODS.md) ·
  [Raw-counts tutorial](docs/RAW_COUNTS_TUTORIAL.md)
- [Statistics](docs/STATISTICS.md) ·
  [Feature-level differential summary](docs/FEATURE_LEVEL_STATISTICS.md)
- [Annotations](docs/ANNOTATIONS.md) · [Volcano annotations](docs/VOLCANO_ANNOTATIONS.md)
- [Multi-panel figures](docs/MULTI_PANEL_FIGURES.md) ·
  [Network graph](docs/NETWORK_GRAPH.md)
- [Publication style](docs/PUBLICATION_STYLE.md) ·
  [Plot style controls](docs/PLOT_STYLE_CONTROLS.md)
- [Exporting publication figures](docs/EXPORTING_PUBLICATION_FIGURES.md)
- [Cross-platform QC](docs/CROSS_PLATFORM_QC.md)

## 15. Citation

Formal citation information will be added after an archival release. For now, please
cite the GitHub repository and the release version you used.

## 16. License

Released under the [MIT License](LICENSE).
