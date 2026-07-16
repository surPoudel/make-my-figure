# Make My Figure

**Publication-style scientific figures from Excel, CSV, and TSV data — without hours of manual formatting.**

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-640%2B%20passing-brightgreen)
![Plot types](https://img.shields.io/badge/plot%20types-37-orange)
![Desktop](https://img.shields.io/badge/desktop-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

Make My Figure is a research-software tool for scientists who need publication-ready
figures but don't want to spend hours manually adjusting fonts, legends, colors, axes,
figure sizes, and export settings. Load a table, choose a plot type, apply the Publication
style, preview the figure, fine-tune the formatting, and export a manuscript-ready file.

> **Publication style, not an official template.** Make My Figure does not provide
> official journal templates or claim compliance with any journal's formatting
> requirements. The Publication style is a general manuscript-ready visual style.

---

## Why this exists

After the analysis is done, researchers still spend a lot of time reformatting plots to
look publication-ready — resizing text, fixing legends that overlap the data, choosing
readable colorblind-safe palettes, cleaning up axes, and exporting at the right size and
resolution. It's repetitive, easy to get wrong, and hard to reproduce.

Make My Figure aims to reduce that repetitive formatting work: it produces strong,
readable figures **by default**, keeps the settings reproducible, and makes high-quality
scientific figures accessible to people who would rather not write plotting code.

## What Make My Figure can do

- Load **CSV, TSV, and Excel** files
- Start from built-in **example/template datasets** for every plot type
- Generate common **biological, biomedical, and scientific** plot types
- Apply **publication-style defaults automatically**
- Apply a polished **Publication style** (adjust fonts, palette, sizes, DPI)
- Adjust **font sizes, line widths, marker sizes, palettes, legends, figure size, and DPI**
- Compute **publication-grade statistics** and annotate figures with significance
  brackets, p-values, and effect sizes — with **transparent method reporting**
  (see [docs/STATISTICS.md](docs/STATISTICS.md))
- Build **multi-panel figures** (Figure 1A, 1B, 1C…) with the
  [Figure Builder](docs/MULTI_PANEL_FIGURES.md) — arrange panels with a **live
  preview**, set each panel's **approximate size** and the figure-wide **fonts**,
  and save only once the layout looks right (panels are scaled without distortion)
- **Preview** figures interactively
- Export **SVG, PDF, PNG, a PlotSpec JSON, and a StatsSpec JSON** sidecar
- **Save templates** so you can replace the example data with your own
- Run as a **Streamlit** web/developer app
- Run as a **desktop app** on Windows, macOS, and Linux
- Keep your **data local** in the desktop app (no telemetry, no cloud upload)

## Matrix workflow (feature-by-sample matrices)

Upload a **feature matrix** (expression / protein / metabolite / any numeric
feature-by-sample table) and:

1. **map** the feature id / annotation / value columns (suggested, then *you
   confirm* — annotation columns like a numeric `annotationLevel` are never treated
   as measurements);
2. **build metadata** — upload a table or assign samples to groups in-app;
3. get **plot recommendations** based on your confirmed mapping;
4. apply recommended **transformations** (wide→long, z-score, top-variable, PCA,
   clustering, correlation, group means, …);
5. generate **publication plots** (heatmap, clustered heatmap, PCA, correlation,
   selected-feature box/violin, volcano/MA from a feature-level differential
   summary) and add them to the Figure Builder.

The app **does not guess silently** — you confirm mappings and groups. Statistics
are **traceable** (every drawn value comes from a stored result). There is **no
raw-count RNA-seq pipeline and no R**; precomputed differential tables are
supported, and normalized matrices can be analysed with generic feature-level
statistics when you choose the method. See
[docs/MATRIX_WORKFLOW.md](docs/MATRIX_WORKFLOW.md),
[docs/TRANSFORMATIONS.md](docs/TRANSFORMATIONS.md),
[docs/FEATURE_LEVEL_STATISTICS.md](docs/FEATURE_LEVEL_STATISTICS.md), and
[docs/PLOT_RECOMMENDATIONS.md](docs/PLOT_RECOMMENDATIONS.md).

## Raw-like matrix QC and preprocessing

If your matrix is **raw / unnormalized / skewed** (count-like or intensity-like),
both apps have an optional preprocessing step — Streamlit's **🧪 Preprocess
(raw-like)** expander and the desktop wizard's **③ Preprocess (raw-like)** tab:

1. **upload** the matrix and **explicitly map** feature / annotation / value columns;
2. **build metadata** (upload or assign groups in-app);
3. **run QC diagnostics** and preview **QC plots** (value distribution, per-sample
   box, per-sample total/median signal, missingness, zero fraction, sample
   correlation, PCA, mean–variance);
4. **choose** a recommended preprocessing workflow (e.g. total-sum/CPM → `log2(x+1)`,
   median-scale, row z-score) — nothing is applied until you **confirm**;
5. **compare before/after** QC and use the clearly-named **derived matrix** (e.g.
   *total-sum + log2 matrix*) for downstream plots and statistics;
6. **export** publication-ready figures (PNG/SVG/PDF).

Guarantees: preprocessing is **never silent**; the **original matrix is preserved**;
every derived matrix is **traceable** (recorded in a `PreprocessingSpec`); statistics
**include the preprocessing chain in their method sentence** and record the source
matrix / preprocessing-spec id; **no R** and **no API/AI** are required for the core
workflow; there is **no raw RNA-seq-branded pipeline** (generic feature-matrix terms
throughout). An optional Python-only count model (PyDESeq2, `pip install -e
".[count-de]"`) is available but never required. See
[docs/RAW_COUNTS_TUTORIAL.md](docs/RAW_COUNTS_TUTORIAL.md),
[docs/PREPROCESSING_QC.md](docs/PREPROCESSING_QC.md), and
[docs/NORMALIZATION_METHODS.md](docs/NORMALIZATION_METHODS.md).

## Statistics, annotations, and multi-panel figures

Make My Figure computes common statistical tests and draws publication-style
annotations directly on figures — but it **reports every method transparently and
never fabricates a p-value.** Each result records the exact test, the groups
compared, the sample size, pairing, the p-value, the adjusted p-value, the
correction method, the effect size, and (where applicable) a confidence interval.

- **Tests:** Student's/Welch's t-test, Mann–Whitney U, paired t-test, Wilcoxon
  signed-rank, one-way/two-way/repeated-measures ANOVA, Kruskal–Wallis (+ Dunn),
  chi-square, Fisher's exact, log-rank, Cox hazard ratios, Pearson/Spearman
  correlation, and linear regression.
- **Corrections:** Benjamini–Hochberg FDR, Bonferroni, Holm, or none.
- **Annotations:** auto-stacked significance brackets on bar/box/violin/grouped
  plots, corner stats panels for scatter/survival/categorical, stars or exact
  p-values, optional effect sizes.
- **Reporting:** an automatic method sentence + methods paragraph, exportable as
  Markdown/JSON and a CSV/TSV results table, plus a reproducible `StatsSpec` JSON.
- **Multi-panel:** save plots as panels and assemble a labelled composite in a
  live-preview builder. Choose each panel's approximate size (width × height in
  inches) and the figure-wide text/axis/legend font sizes; panels are scaled
  proportionally (never stretched), and nothing is written until you're happy
  with the layout.

> **You choose the test.** Make My Figure can compute common statistical tests,
> but users are responsible for choosing tests appropriate to their experimental
> design. The app flags common design issues but does **not** replace statistical
> review. See [docs/STATISTICS.md](docs/STATISTICS.md),
> [docs/STATISTICAL_ANNOTATIONS.md](docs/STATISTICAL_ANNOTATIONS.md), and
> [docs/MULTI_PANEL_FIGURES.md](docs/MULTI_PANEL_FIGURES.md).

### Flexible statistical annotations

On-figure statistics are fully configurable: show **stars**, **exact p**,
**adjusted p (q)**, **test statistic** (`t`, `F`, `U`, `W`, `χ²`, `HR`), **effect
size** (`d`, `g`, `r`, `η²`, `OR`), combinations, or a **custom `{token}`
template** — with per-field decimals, `p < 0.001` style, `n.s.` labels, and a
hide-nonsignificant option. Every value shown comes from the stored StatsSpec
result (hiding it on the figure never removes it from the export). See
[docs/STATISTICAL_ANNOTATION_FORMATTING.md](docs/STATISTICAL_ANNOTATION_FORMATTING.md).

### Volcano from a DE-result table (confirmable columns)

Already have a **differential-expression result table** (from edgeR/limma, DESeq2,
or any tool)? Drop it in and pick **Volcano plot**. The app **auto-detects** the
log-fold-change and p-value columns across the common header conventions —
edgeR/limma (`logFC` / `P.Value` / `adj.P.Val`) and DESeq2 (`log2FoldChange` /
`pvalue` / `padj`) — and lets you **confirm or override** each column in *Map
columns*, so mismatched headers never silently select the wrong column. P-values
are read verbatim from your table; Make My Figure **never computes or fabricates
statistics**. You get Up/Down/n.s. classification, threshold lines, gene labels,
and a count subtitle.

> Make My Figure does not run a differential-expression pipeline — bring a
> normalized matrix (→ heatmap / PCA) or a DE-result table (→ volcano). You remain
> responsible for confirming the upstream analysis matches your study design.

### Define groups in-app — no metadata file needed

Have a **count / expression matrix** (features in rows, samples in columns) but no
separate metadata file? Use **Define groups…** (desktop button; Streamlit
"🗂 Define groups" expander) to:

- **Assign sample groups (wide matrix):** pick the feature-id column, assign each
  sample column to a group (auto-guessed from sample names, fully editable), and
  optionally pick features. The app reshapes the matrix to a long, group-tagged
  table ready for **bar / box / violin plots and statistics**.
- **Group by column values:** for a long table, map an existing column's values to
  group labels, adding a new grouping column you can map and compare.

Column mapping is also **confirmable**: for volcano plots the app auto-detects the
log-fold-change and p-value columns across edgeR (`logFC`/`P.Value`) and DESeq2
(`log2FoldChange`/`pvalue`/`padj`) headers, then lets you confirm or override the
guess in "Map columns" — so mismatched headers never silently pick the wrong column.

And the **preview table is editable**: change a cell (desktop) or edit rows
(Streamlit `data_editor`) and the figure re-renders live from the updated data.

### Return to upload without restarting

Loaded an example and want your own data? Use **Home / Upload New Data** (desktop:
top-left button or File menu; Streamlit: the "Reset / Upload new data" sidebar
button) to clear the dataset, plot, and statistics and return to
the upload page — no restart. It's distinct from the Matplotlib toolbar "home"
(which only resets plot zoom/pan).

## Supported plot types

The current renderers (37):

**Core (17):**

- Bar plot with error bars
- Grouped bar plot with error bars
- Box / violin plot with points
- Scatter plot (with optional regression line)
- Line / time-course plot with error band
- Clustered heatmap
- Volcano plot
- Enrichment dot plot
- Kaplan–Meier survival curve
- Stacked composition bar plot
- Waterfall plot
- PCA scatter (expression matrix + sample metadata)
- Oncoprint mutation heatmap
- Lollipop mutation plot
- ROC curve
- Forest plot
- Ridge / density plot

**New in v0.4 (18):**

- Dot / strip plot
- Beeswarm plot
- Paired dot plot / slopegraph
- Raincloud plot
- Hierarchical clustering dendrogram
- MA plot (differential expression)
- Manhattan plot (GWAS)
- Q-Q plot (p-value / quantile)
- Bland-Altman (method agreement)
- Precision-recall curve
- Confusion matrix
- Calibration plot
- Dose-response curve
- UpSet plot (set intersections)
- Swimmer plot
- Spider plot (longitudinal change)
- Sankey / alluvial (two-stage)
- UMAP / t-SNE embedding scatter

**New in v0.5 (2):**

- Network graph / interaction network
- Hierarchical clustering (heatmap + k clusters)

See **[docs/PLOT_TYPE_REQUIREMENTS.md](docs/PLOT_TYPE_REQUIREMENTS.md)** for the required and
optional columns of each plot type, **[docs/V0_4_NEW_PLOT_TYPES.md](docs/V0_4_NEW_PLOT_TYPES.md)**
for the v0.4 additions, and **[docs/V0_5_NEW_FEATURES.md](docs/V0_5_NEW_FEATURES.md)** for the
v0.5 features below.

## New in v0.5: networks, annotations, docking & clustering

- **Network graph** — edge-list / adjacency / correlation inputs, force-directed
  and other layouts, filtering, centrality metrics, exportable edge/node tables
  ([docs/NETWORK_GRAPH.md](docs/NETWORK_GRAPH.md)).
- **Universal manual annotations** — text, arrows, callouts, highlight boxes /
  regions, brackets on any plot, stored in the PlotSpec
  ([docs/ANNOTATIONS.md](docs/ANNOTATIONS.md)).
- **Volcano annotation controls** — labels on/off, top-N / selected / pasted
  gene lists, arrows from displaced labels ([docs/VOLCANO_ANNOTATIONS.md](docs/VOLCANO_ANNOTATIONS.md)).
- **Heatmap highlighting & clustering** — highlight a pasted gene list, cluster
  color strips, k selection ([docs/HEATMAP_HIGHLIGHTING.md](docs/HEATMAP_HIGHLIGHTING.md),
  [docs/HIERARCHICAL_CLUSTERING.md](docs/HIERARCHICAL_CLUSTERING.md)).
- **Full hierarchical clustering** — clustered heatmap, dendrogram, and a
  clustering-result view that cuts into *k* clusters and exports the assignment.
- **Pop-out / pop-in desktop panels** — detach the figure, data, or controls to
  another monitor and dock them back ([docs/POP_OUT_PANELS.md](docs/POP_OUT_PANELS.md)).
- **Click to identify / label points (desktop)** — on volcano & scatter, click a
  point to see its gene/sample name and toggle a label on it (saved in the PlotSpec).
- **Import external panels into the Figure Builder** — assemble existing figures
  from R / Python / Prism / Illustrator / BioRender / microscopy (PNG/JPG/TIFF;
  PDF/SVG with an optional converter) alongside generated plots, with crop/fit,
  resolution warnings, annotations, and reproducible copied assets
  ([docs/IMPORT_EXTERNAL_PANELS.md](docs/IMPORT_EXTERNAL_PANELS.md)).

> Clustering and network visualizations are exploratory summaries. Users are
> responsible for interpreting biological meaning and confirming that chosen
> distance metrics, thresholds, and filters are appropriate.

## Publication-style defaults

Every plot is styled to be publication-ready out of the box, so the first figure you see is
already clean:

- readable fonts (≈12 pt axis labels, 10 pt ticks)
- clean axes (thin spines, no chartjunk, top/right spines hidden)
- **colorblind-aware, high-contrast** palettes (not the default Matplotlib cycle)
- non-overlapping legends where possible (placed outside the data when needed)
- sensible figure sizes and margins
- export-safe layout (tight bounding boxes so labels/legends aren't clipped)
- vector-friendly **SVG/PDF** output with **editable text**

You can still refine everything from the app's style controls. After each render, a
lightweight **publication-readiness check** flags likely issues (text too small, legend
overlap, possible clipping, missing labels). It's advisory and never blocks export.
More detail: **[docs/STYLE_PROFILES.md](docs/STYLE_PROFILES.md)**.

## Example data and templates

Every plot type ships with a **synthetic** example dataset. These double as **templates**:
open one, click **Save template**, then replace the rows with your own data while keeping the
column names. See **[docs/EXAMPLE_DATA.md](docs/EXAMPLE_DATA.md)** and
**[docs/DATA_TEMPLATES.md](docs/DATA_TEMPLATES.md)**.

> The bundled example datasets are **synthetic** and are **not** copied from published
> papers. Published figures may be consulted as *visual style references only* where
> licensing permits local analysis; the tool does not copy published figures and does not
> present the synthetic examples as real biological findings.

## Apps

### Streamlit app

```bash
streamlit run apps/streamlit_app/streamlit_app.py
```

A browser-based interface — convenient for development, testing, and quick use.

### Desktop app

```bash
python -m apps.desktop_app.main
```

A zero-command desktop application (PySide6) with a live figure preview, an interactive
toolbar (pan/zoom/home/save), and resizable panels. Standalone installers can be built for
Windows, macOS, and Linux so end users don't need the command line. See
**[docs/DESKTOP_APP.md](docs/DESKTOP_APP.md)** and
**[docs/BUILD_INSTALLERS.md](docs/BUILD_INSTALLERS.md)**.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

For the desktop app's extra dependencies:

```bash
pip install -e ".[desktop]"
```

A step-by-step guide is in **[docs/QUICKSTART.md](docs/QUICKSTART.md)**.

## Quick start

1. Open the app (desktop or Streamlit).
2. Choose **Use example data**, or upload a **CSV / TSV / XLSX** file.
3. Select a **plot type**.
4. Map columns to roles (if needed).
5. Choose a **style profile**.
6. **Preview** the figure.
7. Adjust formatting if you like (fonts, palette, legend, size, DPI).
8. **Export** SVG, PDF, PNG, and the PlotSpec JSON.

## Reproducibility

Each figure can be exported alongside a **PlotSpec JSON** file that records the plot type,
column mapping, style profile, formatting options, and export settings. This makes figures
easier to reproduce, revise, and share. See
**[docs/EXPORTING_PUBLICATION_FIGURES.md](docs/EXPORTING_PUBLICATION_FIGURES.md)**.

## Privacy

- The desktop app runs **entirely on your computer**.
- Your data does not need to leave the machine.
- There is **no telemetry and no cloud upload**. Any such feature would only ever be added
  if explicitly implemented and clearly documented.

## Roadmap

Planned directions (not yet implemented unless stated elsewhere):

### Statistics support (shipped)

Commonly used statistical tests, figure annotations, and transparent method
reporting are now implemented (see
[docs/STATISTICS.md](docs/STATISTICS.md)):

- **Two-group tests:** Student's t-test, Welch's t-test, Mann–Whitney U, paired t-test,
  Wilcoxon signed-rank
- **Multi-group tests:** one-way ANOVA, two-way ANOVA, repeated-measures ANOVA,
  Kruskal–Wallis (with Dunn's post-hoc)
- **Categorical tests:** chi-square, Fisher's exact
- **Survival / model statistics:** log-rank test for Kaplan–Meier curves, and Cox
  hazard-ratio display (with an explicit proportional-hazards caveat)
- **Correlation / regression:** Pearson, Spearman, linear regression
- **Multiple-testing correction:** Benjamini–Hochberg (FDR), Bonferroni, Holm
- **Figure annotations:** p-value labels, significance brackets, effect sizes, confidence
  intervals, and automatic method reporting

Statistics are **transparent and reproducible**: each result reports the exact test used,
its assumptions, the sample size, the effect size, and the correction method, and is saved
in a `StatsSpec` JSON sidecar.

### Other planned items

- A Python (and possibly R) package API
- More Publication style refinements
- Better automatic label-collision avoidance
- More biomedical plot templates
- Smoother GraphPad/Prism-like workflows
- Improved style auditing from open-access figures
- PowerPoint / Illustrator-friendly SVG/PDF export
- Batch rendering

## Contributing

The project is under active development and feedback is very welcome. Useful areas:

- testing with real scientific workflows
- suggesting missing plot types
- improving example templates
- UI/UX feedback
- documentation
- statistical-method review (for the planned statistics features)
- packaging and installers
- accessibility and colorblind-safe palettes

Please open an issue or pull request to get started.

## License

Released under the **MIT License** — see [LICENSE](LICENSE).

## Citation

Citation information will be added once the project reaches a stable release.

---

<sub>Developer notes: internal design docs live in [`docs/`](docs/), and the original
research-software prompt/mock-data bundle used to bootstrap the project is kept under
[`claude_code/`](claude_code/) and [`reports/`](reports/).</sub>
