# Make My Figure

**Publication-ready scientific plots and multi-panel figures from common data tables — with a
machine-readable record of how every panel was made.**

![Version](https://img.shields.io/badge/version-1.1.0-blue)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Plot types](https://img.shields.io/badge/plot%20types-38-blueviolet)
![Statistics](https://img.shields.io/badge/statistical%20procedures-18-blueviolet)
![Platforms](https://img.shields.io/badge/platforms-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)

---

## 1. Overview

Make My Figure turns tabular data — CSV/TSV/TXT files and Excel workbooks — into
manuscript-style plots and multi-panel figures, and records how each figure was made.
Load a table, pick (or accept a recommended) plot, confirm how your columns map to it,
adjust the Publication style, run statistics where they belong, assemble panels, and
export vector and raster files together with the JSON specifications that let the figure
be rebuilt later.

One engine (`make_my_figure_core`) serves two interfaces: a **desktop application**
(Qt/PySide6) and a **browser application** (Streamlit). Both run entirely on your own
computer: no cloud upload, no telemetry, no account, and no R installation.

## 2. Install

### Packaged application (no Python needed)

Download the installer for your system from the
[Releases page](https://github.com/surPoudel/make-my-figure/releases) (current release
**v1.1.0**) and check the file against `SHA256SUMS.txt` if you want to verify it.

| System | File | Steps |
|---|---|---|
| **macOS** | `MakeMyFigure-1.1.0.dmg` | Open the DMG, drag *Make My Figure* to *Applications*, launch. The bundle is not notarised: on first launch right-click → **Open**, or allow it under *System Settings → Privacy & Security*. |
| **Windows** | `MakeMyFigure-1.1.0-Setup.exe` (or `MakeMyFigure-1.1.0-windows.zip`) | Run the installer (or unzip and start `MakeMyFigure\MakeMyFigure.exe`). SmartScreen may warn about an unsigned program; choose *More info → Run anyway* if you trust the source. |
| **Linux** | `MakeMyFigure-1.1.0-linux-x86_64.tar.gz` (or `MakeMyFigure-1.1.0.AppImage`) | Unpack the tarball and run `MakeMyFigure/MakeMyFigure`, or `chmod +x` the AppImage and run it. The desktop app needs the usual Qt system libraries (`libxkbcommon0 libgl1 libegl1 libxcb-*`). Built on Ubuntu 24.04: needs glibc 2.38 or newer (Ubuntu 24.04+, Fedora 39+, Debian 13+); on older distributions use the wheel or the source install. |
| **WSL2** (Linux running under Windows) | no native package | WSL2 is not native Windows: use the source install below with WSLg (Windows 11), or run the browser app inside WSL2 and open it in a Windows browser. |

On launch the desktop status bar shows `Make My Figure v1.1.0 · <commit> · <platform> · <backend>`;
**Help → About** shows the same version.

### From source (desktop and browser apps, development)

```bash
git clone https://github.com/surPoudel/make-my-figure.git
cd make-my-figure
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt               # core + browser app + pytest
python -m pip install -e ".[desktop]"                   # adds the PySide6 desktop app

streamlit run apps/streamlit_app/streamlit_app.py       # browser app (no Qt required)
python -m apps.desktop_app.main                         # desktop app
```

Python 3.10–3.12 is recommended. Optional extras: `desktop` (PySide6), `dev` (pytest,
pytest-qt), `build` (PyInstaller), `import-panels` (PDF/SVG panel import), `count-de`
(an opt-in, Python-only count-model differential path; never required). Installing the
wheel (`pip install make_my_figure_core-1.1.0-py3-none-any.whl`) gives the engine and the
bundled resources for use from your own scripts, without a GUI.

On Linux/WSL2 the desktop app needs Qt system libraries; if PySide6 cannot load, the app
prints the exact `apt install` line and exits cleanly, and the browser app is unaffected.

## 3. What you can make

**38 plot types**, all drawn through one registry and one style layer:

- **Comparisons** — bar, grouped bar, box/violin with points, dot/strip, beeswarm, raincloud.
- **Distributions** — histogram (binned; panels per group or overlaid; frequency polygon)
  and ridge/density (smoothed).
- **Relationships** — scatter with regression readout, Bland–Altman, correlation heatmap.
- **Time / trajectory** — line and time-course with SEM/SD/CI/IQR/range bands and a
  second style-by category, paired slopegraph, swimmer, spider/radar.
- **Matrix & omics-style** — clustered heatmap, hierarchical clustering, dendrogram, PCA,
  volcano and MA plots from precomputed differential tables (or from the in-app
  feature-level summary).
- **Statistical / model** — forest, ROC, precision–recall, calibration, confusion matrix,
  Kaplan–Meier survival (subject-level or precomputed curves).
- **Genomics-style summaries** — Manhattan, Q–Q, oncoprint, lollipop.
- **Composition / set / flow / network** — stacked composition, UpSet, Sankey/alluvial,
  network graph.
- **Other** — enrichment dot plot, waterfall, dose–response, embedding scatter (UMAP/t-SNE
  from precomputed coordinates).

## 4. The workflow

1. **Load** delimited text or Excel. Multi-sheet workbooks show a **Worksheet** selector
   (every sheet selectable, advisory classification, worksheet-aware output names and
   provenance); stacked and merged header rows are handled.
2. **Map columns.** Column roles are suggested (edgeR/limma/DESeq2 headers are recognised
   for differential tables) and always confirmed by you; nothing is substituted silently.
3. **Recommendations.** A rule-based engine profiles the table and proposes plots,
   compatible transformations and tests with a reason each. Advisory only.
4. **Matrix workflow** for feature × sample matrices: explicit feature / annotation /
   value columns (MatrixSpec), sample groups from metadata or built in-app
   (SampleMetadataSpec), QC diagnostics, preprocessing with confirmation and a derived
   table (PreprocessingSpec), recommendations, then the full plot editor.
5. **Statistics** on the plot (below) and **annotations** (click-to-label, duplicate-label
   policies, a manual annotation layer).
6. **Publication style** — one manuscript-ready style with typography, palette, axes,
   legend, colorbar and margin controls; a control that does not apply to the current plot
   is flagged, not ignored. Axis ranges, ticks and scales where they make sense; a range
   that would hide data is refused.
7. **Figure presets** — save a plot's configuration and apply it to other data
   (section 6).
8. **Figure Builder** — assemble generated and imported panels into a labelled grid and
   export the composite with its FigureSpec.
9. **Export** — SVG, PDF and EPS (text kept as text, TrueType fonts embedded), PNG and
   TIFF (chosen DPI), always with a PlotSpec sidecar and a StatsSpec when statistics ran.

## 5. Statistics

Eighteen procedures, implemented with SciPy and statsmodels (no R): Student's and Welch's
*t*, paired *t*, Mann–Whitney U, Wilcoxon signed-rank, one-way / two-way /
repeated-measures ANOVA, Kruskal–Wallis with Dunn's post hoc, chi-square, Fisher's exact
(r × c by seeded Monte Carlo), log-rank and Cox proportional hazards, Pearson and Spearman
correlation, linear regression, and GLM regression (Gaussian, binomial, Poisson,
negative-binomial, Gamma). Multiple-testing correction: Benjamini–Hochberg, Holm,
Bonferroni. Effect sizes and confidence intervals where defined. Every p-value drawn on a
figure comes from a stored result; renderers never format statistics themselves.

Every test, correction, normalisation, QC metric, PCA, clustering and the feature-level
screen has been compared with independent R implementations
([benchmarks/r_validation](benchmarks/r_validation/README.md)): 2,625 comparisons, no
failures, documented convention differences kept apart from agreement. The in-app
feature-level screen (per-feature *t*/rank tests on log-CPM) is compared with limma-voom,
edgeR and DESeq2 as **concordance only** — it is a screen, not a replacement for those
models, and Make My Figure never recomputes the statistics of an imported DE table.

## 6. Figure presets

A **Figure preset** is the reusable part of a plot's configuration, separated from the data:

- **Style** — typography, palette, marker and line sizes, geometry, legend and colorbar
  placement, export size/DPI and the visual plot options (violin vs box, histogram bars vs
  polygon, heatmap colormap, node colours …).
- **Full** — everything above plus column roles, thresholds, axis labels and the
  statistics test. Applied to new data, it uses what fits and asks you to choose a column
  for any role the new table lacks.

Presets never contain your data, the table name or worksheet provenance; categorical
colours are assigned to the new data's categories in palette order, not copied by name.
Both apps offer Apply, Save preset…, Import, Export, Delete and Reset. The Figure Builder
has a **Layout preset** (grid, panel sizes, gutters, label style — no panel content).

## 7. Reproducibility records

| Record | Contents |
|---|---|
| **PlotSpec** | plot type, table (and workbook/worksheet), column roles, options, style, layout, annotations, export settings — the record of one plot |
| **StatsSpec** | test, comparisons, correction, statistics, p and adjusted p, effect sizes — every value drawn on the figure |
| **MatrixSpec / SampleMetadataSpec** | confirmed matrix column roles; sample → group assignment |
| **PreprocessingSpec** | the ordered, confirmed transformation chain that produced a derived matrix |
| **FigureSpec** | one multi-panel composite: canvas, grid, letters, per-panel size, PlotSpec/StatsSpec and source identity |
| **Figure preset / Layout preset** | reusable configuration without data |

All are plain JSON written next to every export. A specification records the *identity* of
a source table, not its contents, so rebuilding a figure needs the data to remain
available.

## 8. Documentation

- **Quick Start** — `docs/manuals/Quick_Start/MakeMyFigure_Quick_Start.pdf` (also attached to each release)
- **User Manual** — `docs/manuals/User_Manual/MakeMyFigure_User_Manual.pdf` (27 parts: interface, data, mapping, recommendations, matrix workflow, statistics, plot catalogue, publication controls, colours, annotations, Figure presets, PlotSpec, Figure Builder, exports, multi-sheet Excel, differential results, performance, cross-platform notes, troubleshooting, reference)
- Topic notes in `docs/`: [Matrix workflow](docs/MATRIX_WORKFLOW.md), [Multi-sheet Excel](docs/MULTI_SHEET_EXCEL.md), [Statistics](docs/STATISTICS.md), [Feature-level statistics](docs/FEATURE_LEVEL_STATISTICS.md), [Normalization methods](docs/NORMALIZATION_METHODS.md), [Annotations](docs/ANNOTATIONS.md), [Multi-panel figures](docs/MULTI_PANEL_FIGURES.md), [Plot style controls](docs/PLOT_STYLE_CONTROLS.md), [Exporting](docs/EXPORTING_PUBLICATION_FIGURES.md), [Cross-platform QC](docs/CROSS_PLATFORM_QC.md), [Building installers](docs/BUILD_INSTALLERS.md)
- [CHANGELOG](CHANGELOG.md)

## 9. Verification

```bash
python -m pytest -q                                   # full suite
python -m pytest tests/test_r_validation_regressions.py -q
python scripts/run_cross_platform_qc.py --output reports/release_cross_platform_qc/current_platform
```

If the `pytest-qt` plugin cannot load Qt on a headless machine, run
`python -m pytest -q -p "no:pytest-qt" --ignore=tests/test_desktop_gui.py`.

## 10. Limitations

- Publication is a general style, not an official journal template, and does not
  guarantee compliance with any journal's requirements.
- Make My Figure is a plotting and reporting tool, not a substitute for statistical
  review; you choose the appropriate method, and recommendations are advisory.
- Differential expression is not computed from counts (the optional `count-de` extra is
  separate); imported DE tables are plotted as given.
- Output can differ slightly between machines through installed fonts and backend text
  metrics; three plot types (volcano, lollipop, network) place labels with an unseeded
  repulsion search, so label coordinates vary between renders while data marks do not.
- Multi-panel composites embed panel content as raster at the export DPI; single-plot
  exports are fully vector.
- Very large matrices may need filtering or top-variable-feature selection for responsive
  heatmaps and networks.

## 11. Citation and releases

Please cite the release you used: **Make My Figure v1.1.0**,
https://github.com/surPoudel/make-my-figure/releases/tag/v1.1.0. A formal software
citation will be added when an archival record exists.

## 12. License

Released under the [MIT License](LICENSE).
