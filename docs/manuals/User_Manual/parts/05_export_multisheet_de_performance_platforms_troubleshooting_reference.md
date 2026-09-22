## Part XVII — Exporting

### 70. Formats

| Format | Raster/vector | DPI | Text | Transparency | Size | Recommended use |
|---|---|---|---|---|---|---|
| **SVG** | vector | — | editable (`svg.fonttype: none`) | background is part of the figure | small for line/point plots; large for dense heatmaps | further editing in Illustrator/Inkscape; journals accepting SVG |
| **PDF** | vector | — | editable, fonts embedded as Type 42 | as SVG | as SVG | manuscript submission, print proofs |
| **EPS** | vector | — | Type 42 | no | as PDF | legacy submission systems |
| **PNG** | raster | 150–600 (Raster DPI) | rasterised | white background | grows with DPI² | slides, quick sharing, journals requiring raster |
| **TIFF** | raster, LZW-compressed | as PNG | rasterised | white | larger than PNG | journals requiring TIFF |

All exports use a tight bounding box that also includes the axis labels and title, so a long axis label is never clipped. Desktop buttons: **Export SVG / PNG / PDF** (figure file only), **Export PlotSpec JSON (specification only)**, **Save Figure Package (.mmfpackage)**, **Export all as ZIP** (SVG, PNG, PDF, `name.plot_spec.json`, `name.stats_spec.json` when statistics ran, and `name.mmfpackage`; TIFF/EPS are available through the core API). Browser: **SVG / PNG / PDF / PlotSpec JSON / Figure Package** downloads (plus **StatsSpec JSON** when statistics ran). The Figure Builder exports PNG + SVG + PDF + `name.figure_spec.json` with panel content embedded as raster at the export DPI, and **Save Figure Package…** for the portable composite.

![Browser: figure preview with the Export downloads (SVG, PNG, PDF, PlotSpec JSON).](../../assets/screenshots/streamlit_16_export.png)

### 71. Practical notes

- Exporting the same figure twice from the same PlotSpec and code gives the same content; file bytes may differ by timestamps.
- Choose the **Figure width** preset to match the journal column before exporting; fonts are then at their true point sizes.
- Very large PNGs (600 dpi, double column) can exceed 20 MB; 300 dpi is the usual requirement.

## Part XVIII — Multi-sheet Excel workbooks

### 72. Workflow

1. **Upload** a `.xlsx`/`.xlsm`/`.xls` (desktop: Open data file… or drag-and-drop; browser: Upload file).
2. The **📑 Worksheet** box lists **every** sheet in workbook order, including empty and notes sheets, and marks hidden ones. The active sheet loads first.
3. **Inspect**: each sheet shows a detected type and reason — `differential_results` (fold-change + p/FDR columns), `matrix`, `metadata`, `enrichment`, `documentation` (mostly text or blank), `generic`, `empty`, `unknown`. This is advisory: any sheet can be plotted.
4. **Switch** sheets in the box; mapping controls rebuild for the new columns, and the header-row choice (browser) applies per sheet.
5. **Provenance**: the PlotSpec `source` block records the workbook name, file hash, sheet name/index/type and header row; export file names start with the worksheet name (`<Sheet>_<plot_type>.png`).

![Desktop: the Worksheet chooser for the bundled example workbook.](../../assets/screenshots/desktop_17_multi_sheet_workbook.png)

![Desktop with the workbook loaded: worksheet box, preview and figure.](../../assets/screenshots/desktop_17b_workbook_loaded.png)

![Browser workbook browser with the bundled example workbook (40 sheets).](../../assets/screenshots/streamlit_17_multi_sheet_workbook.png)

**Several DE comparison sheets** in one workbook: plot each as a volcano from its own sheet; the exported PlotSpecs differ only in the sheet name and can be opened side by side in the Figure Builder.

## Part XIX — Differential results

### 73. Input

One row per feature with a **feature ID** (gene, protein, peptide), a **log fold change** (`logFC`, `log2FoldChange`), a **p-value** (`P.Value`, `pvalue`), optionally an **adjusted p / FDR** (`adj.P.Val`, `padj`) and an **average abundance** (`AveExpr`, `baseMean`, `logCPM`). These headers are recognised (edgeR, limma, DESeq2 conventions) and prefilled; you confirm them in *Map columns*.

### 74. Plots

- **Volcano** — x = log fold change, y = −log10 p (or FDR when **P column is FDR/adjusted** is ticked). **log2FC cutoff** and **p-value / FDR cutoff** draw the threshold lines and colour classes (up / down / not significant). Labels: top-N by extremity, a pasted list, or click-picked points; duplicate-label policy as in Part XIII.
- **MA** — x = average abundance, y = log fold change, coloured by significance at the **p_cutoff**.

![Desktop volcano editor.](../../assets/screenshots/desktop_10_volcano_editor.png)

### 75. Raw p versus FDR

The y axis plots whatever column you mapped to `p`. Tick **P column is FDR/adjusted** so the axis label says FDR and the cutoff is interpreted on the adjusted scale. Nothing is recomputed: **Make My Figure does not replace specialist differential-expression inference** (DESeq2, edgeR, limma). It reads the values you provide. The Matrix Workflow's *differential summary* is a per-feature t/Mann-Whitney/ANOVA screen on a normalised matrix, labelled as such.

## Part XX — Performance and large datasets

- Rendering runs in background workers on the desktop; continuous controls are debounced so dragging a slider triggers one render.
- **Heatmap / clustering**: rows are capped at **`max_features` = 2 000** by default (adjustable 50–50 000), chosen by variance; highlighted rows survive the cap. Integer annotation columns are dropped from the value matrix and reported.
- **Volcano / MA with ~50 000 rows**: rendering is fast; labelling is the cost — keep top-N labels modest (tens), use the duplicate-label policy `unique`, and prefer PNG for previews.
- **Networks**: filter with `min_weight` / `corr_cutoff` / `top_n_edges` / `min_degree` before layout; use `seed` for reproducible layouts.
- **Browser app**: each control change re-runs the script; large tables make every interaction slower — pre-filter, or use the desktop app.
- **Windows** first launch of the packaged app is slow while the bundle is unpacked and scanned; later launches are quicker. See `docs/WINDOWS_PERFORMANCE.md`.

No timing figures are quoted here because none were benchmarked for this manual.

## Part XXI — Cross-platform notes

| | macOS | Windows | Linux | WSL |
|---|---|---|---|---|
| Native desktop | packaged `.dmg` or source | `.exe` installer / zip or source | AppImage / tar.gz or source (needs Qt libs) | source; needs WSLg or an X server |
| Browser app | source | source | source | source (open the URL from Windows) |
| Fonts | Arial/Helvetica present | Arial present | DejaVu Sans fallback | DejaVu Sans |
| Paths | `~/Library/Application Support/MakeMyFigure/presets` | `%APPDATA%\MakeMyFigure\presets` | `~/.local/share/make_my_figure/presets` | as Linux |
| Known | unsigned bundle needs right-click → Open | SmartScreen prompt; slower first launch | missing `libxkbcommon` etc. on minimal images | no display → use the browser app |

Figures rendered on different platforms differ slightly in font metrics and spacing; the style is the same, the pixels are not guaranteed identical. Emoji in button labels depend on an installed emoji font.

## Part XXII — Troubleshooting

Each entry: **Problem · Likely cause · Diagnose · Fix**.

- **App does not start (desktop).** Qt binding missing or unloadable. Run `python -c "import PySide6.QtWidgets"`; the app prints the exact `apt install` list on Linux. Fix: `pip install -e ".[desktop]"`; install the Qt system libraries; or use the browser app.
- **`Python not found` / `py` not recognised (Windows).** Python not on PATH. Reinstall Python ticking *Add to PATH*, or use the full path to `python.exe`.
- **`libxkbcommon.so.0: cannot open shared object file`.** Minimal Linux/WSL image. Install the listed Qt libraries.
- **PowerShell refuses to activate the venv.** Execution policy. `Set-ExecutionPolicy -Scope Process RemoteSigned`, then activate.
- **WSL: no window appears.** No display. Use WSLg (Windows 11) or the browser app.
- **Banner shows an old commit / features missing.** An installed package shadows the checkout. `python -m pip install -e .` in the checkout; confirm with the banner.
- **`ModuleNotFoundError: pandas` although a venv seems active.** Stale venv label or wrong interpreter first on PATH. Deactivate everything; create and activate a fresh venv in the project folder.
- **`numpy.dtype size changed` on macOS.** Two environments stacked. One fresh venv.
- **pip fails compiling a PySide6 template.** Old interpreter. Use Python 3.10+ and `pip install --no-compile`.
- **Wrong worksheet plotted.** Active sheet loaded by default. Choose the sheet in **📑 Worksheet**; check the `source` block of the PlotSpec.
- **Plot selector blank / "Choose a plot type…".** By design after upload: pick a plot type or a recommendation.
- **Figure does not change when I move a control.** The control does not apply to this plot (a notice says so), or the Publication style group is unticked (desktop). Tick the group; check Messages.
- **Statistics slow.** Many groups × many comparisons with post-hoc; reduce comparisons (vs control) or groups.
- **Stale figure after an error.** The app clears the figure on error and shows the message; fix the mapping and re-render.
- **Preset "cannot be applied".** A full preset for another plot type. Save a style preset for cross-type reuse, or open the matching plot type.
- **Preset applied but a column role is empty.** The new table lacks that column; the app listed it — choose one in *Map columns*.
- **Missing font.** The requested family is not installed; Matplotlib falls back to DejaVu Sans. Install the font or choose one installed.
- **PDF looks different from the screen.** Font substitution or DPI; the vector export is authoritative. Check fonts and the width preset.
- **Labels overlap.** Reduce top-N, enable `unique` duplicate policy, enlarge the figure width, or reposition (browser offsets / PlotSpec).
- **Large heatmap slow.** Rows above `max_features` are trimmed by variance; lower `max_features` or pre-filter.
- **Figure Builder panel clipped or blurry.** Panel too small for its content or raster DPI too low; increase its width or the Export DPI; import vector files with the `import-panels` extra.
- **Excel header wrong.** Title rows above the header, or merged/stacked headers. Browser: choose the header row / two stacked rows, tick forward fill; desktop: remove the title rows first.
- **"Survival probabilities as event column" error.** You mapped an already-computed curve as a 0/1 event column. Set **Input form → precomputed** and pick the S(t) columns.

## Part XXIII — Reproducible lab workflows

**1. Same scatter style across experiments.** Finalise one scatter (fonts, palette, fit statistics shown, legend outside right). Save preset *Lab scatter* (style). For every later experiment: load, choose *Scatter plot*, map x/y/colour, **Apply** *Lab scatter*, export. Only the mapping and title are ever set by hand.

**2. Reusable heatmap preset.** As §60: *Lab Heatmap* (style) carries colormap, cell borders, colorbar position and fonts; the clustering method and value columns remain per dataset.

**3. DE result → volcano → preset → Figure Builder.** Load the DE table (or the DE sheet of a workbook), confirm the detected columns, set thresholds and class colours, label top genes, save *Lab volcano* (full, to keep thresholds). **Save current plot as panel** for each comparison, then compose in the Figure Builder with a 1 × 3 grid; save the layout preset *Three volcanoes*.

**4. Matrix → QC → transformation → PCA/heatmap.** Matrix Workflow: map, confirm raw scale, groups from metadata, `log2` → `median_scale` → `row_zscore` steps, **Run diagnostics**, save the before/after report, **Open in plot editor** for the heatmap and PCA; the PlotSpecs carry the preprocessing identifiers and method sentence, and **Save Figure Package** stores the MatrixSpec, SampleMetadataSpec, PreprocessingSpec, the original and the derived matrix with the plot.

**6. Sharing a reproducible figure with another laboratory.** Finalise the plot → **Save Figure Package** → send the one `.mmfpackage` file → the collaborator opens Make My Figure → **Open Figure Package** → integrity is verified → the figure opens with the frozen data and configuration → they inspect, edit and re-export. No original data file, worksheet or sidecar folder is needed.

**5. Multi-sheet workbook → several comparisons → separate exports.** Upload once; for each DE sheet choose it, apply *Lab volcano*, export — file names start with the sheet name and each PlotSpec's `source` names the sheet.

## Part XXIV — Files generated by Make My Figure

```
<Sheet>_<plot_type>.png / .svg / .pdf / .tiff / .eps   the figure(s); the stem is the worksheet
                                                       name (or the file stem) plus the plot type
<stem>.plot_spec.json                                  PlotSpec + render metadata (Export PlotSpec JSON, ZIP, browser)
<stem>.stats_spec.json                                 every statistical result (ZIP and browser, when statistics ran)
<stem>.mmfpackage                                      figure package: specification + frozen data + records + previews
                                                       + manifest with SHA-256 per file (Save Figure Package; also in the ZIP)
Figure_1.png / .svg / .pdf                             Figure Builder composite
Figure_1.figure_spec.json                              FigureSpec (panels, PlotSpecs, layout, draft legend; table identities only)
Figure_1.mmfpackage                                    composite figure package (FigureSpec + panel specs + tables + images)
figure_builder_assets/                                 copies of imported panel files
<table> (grouped)  /  <table>__diff.csv                grouped table / differential screen (Define groups)
<report folder>/before_after_contact_sheet.pdf, .png   Matrix Workflow before/after QC report
                 + one vector file per QC plot
<name>.csv, <name>.md                                  statistics table and method report (you name them)
<preset library>/*.mmfpreset.json                      Figure presets (per-user folder, Part XIV)
<preset library>/*.mmflayout.json                      Figure Builder layout presets
```

## Part XXV — Limitations

- Publication is a general style, not an official journal template; it does not guarantee acceptance.
- Statistical design and method choice remain the researcher's responsibility; suggestions are advisory; Dunnett's test is not implemented.
- No DE inference; DE values are read verbatim. The Matrix Workflow differential summary is a screen.
- Very large matrices are trimmed by variance (`max_features`); very large networks need filtering.
- Figure Builder composites rasterise panel content; no free positioning or z-order; the browser builder is columns-only.
- Desktop: no header-row selector, no drag-to-move for labels; browser: no font-family control, no EPS/TIFF buttons.
- Colour choices are from curated lists (no colour picker); per-category manual colour maps only for network nodes.
- The recommendation engine is rule-based.
- No transformation is ever applied silently; conversely nothing is auto-normalised for you.
- Cross-platform font differences; no byte-identical guarantee.
- Packaged v1.1.1 installers are built from the same tagged source as this manual; the two cosmetic Qt defects below are present in them as well.
- Statistics annotation is not available on the line/time-course plot.

## Part XXVI — Glossary

- **PlotSpec** — the JSON record of one figure: plot type, table, roles, options, style, layout, statistics, annotations, provenance.
- **StatsSpec** — the JSON record of the statistical results drawn on / computed for a figure.
- **MatrixSpec** — the confirmed structure of a feature × sample matrix (feature id, value columns, value scale, policies).
- **PreprocessingSpec / PreprocessingStep** — the ordered, confirmed transformation steps applied to a matrix, with QC before/after.
- **SampleMetadataSpec** — the sample → group (and other attribute) assignment used by the Matrix Workflow.
- **FigureSpec** — the JSON record of a multi-panel composite (panels, PlotSpecs, layout, legend draft).
- **Figure preset** — reusable configuration without data: style-only or full configuration.
- **Figure package** — one portable `.mmfpackage` file: PlotSpec/FigureSpec + frozen data + StatsSpec/Matrix/Preprocessing records + assets + previews + checksums; reopens without the original files.
- **Layout preset** — reusable Figure Builder geometry without panel content.
- **Derived matrix** — a new table produced by preprocessing or grouping; the source table is unchanged.
- **Publication style** — the single visual style profile (tokens for fonts, widths, palette).
- **Mapping** — the assignment of table columns to plot roles (and the plot's options).
- **Recommendation** — an advisory plot suggestion with score and reason from the table's shape.
- **Annotation identity** — a picked point is remembered by row identity (volcano/MA) or label text (other plots) so labels survive re-rendering.

## Part XXVII — Quick reference

**Input format → workflow**

| Format | Workflow |
|---|---|
| CSV/TSV/TXT long table | Quick plot: map x/y/group |
| Excel single sheet | as CSV; merged headers recovered |
| Excel multi-sheet | choose the worksheet; each has its own header row and provenance |
| Feature × sample matrix | Quick plot (heatmap/PCA) or Matrix Workflow (QC, preprocessing, groups) |
| Wide columns of unequal length | Histogram (Input form → wide) or Define groups → grouped table |
| Precomputed DE table | Volcano / MA |
| Subject-level survival | Kaplan-Meier (subject_level) · Precomputed S(t) | Kaplan-Meier (precomputed) |

**Data type → recommended plots** — see Part VI §25.

**Plot → required columns** — see Part X (each section's *Column mapping*).

**Statistics → required data**

| Method | Data |
|---|---|
| t-tests, Mann-Whitney | numeric value + group column with two levels (paired: + subject id) |
| ANOVA / Kruskal / Dunn | numeric value + group (≥ 3 levels); two-way: + subgroup; RM: + subject |
| Chi-square / Fisher | two categorical columns |
| Pearson / Spearman / regression / GLM | two numeric columns (GLM: several predictors) |
| Log-rank / Cox | time, 0/1 event, group (subject-level) |

**Export format → use** — see Part XVII §70.

**Specification → purpose**

| File | Purpose |
|---|---|
| `.plot_spec.json` | the recipe of one figure (needs the source data) |
| `.stats_spec.json` | every statistic behind it |
| `.figure_spec.json` | the recipe of a composite (needs the panel tables) |
| `.mmfpackage` | reopen a figure or composite anywhere: recipe + frozen data |
| `.mmfpreset.json` | reuse a configuration on new data |
| `.mmflayout.json` | reuse a composite layout |

**Preset type → purpose**

| Preset | Carries | Use when |
|---|---|---|
| Figure style only | fonts, palette, geometry, legend/colorbar, export, visual options | "make all our figures of this kind look like this" |
| Full figure configuration | + roles, thresholds, labels, statistics, annotations | repeat the same analysis on the next dataset |
| Layout preset | grid, sizes, gutters, labels, fonts | reuse a multi-panel arrangement |
