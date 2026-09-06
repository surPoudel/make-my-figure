## Part XI — Publication controls

### 41. The Publication style

There is one style, **Publication**: a general manuscript-ready visual style with readable sizes (title 14 pt, axis labels 12 pt, ticks 10 pt, annotations 10 pt), thin spines, no grid, a colour-blind-aware default palette, and editable text in vector exports. It is **not** an official journal template; the exported metadata carries a disclaimer to that effect. Older PlotSpecs that named one of the removed, journal-named style profiles are migrated to Publication when loaded, with a notice.

### 42. Shared controls

Desktop: tick **5. Publication style** to enable the group (unticked, the defaults apply). Browser: the five expanders under **5. Publication style**.

| Group | Controls | Where the value goes |
|---|---|---|
| ① Figure | width preset (default / single / onehalf / double column), raster DPI (150–600), left/right/top/bottom margins (0 = auto), auto-fix layout | layout / output |
| ② Typography | palette, font (desktop only), title pt, axis label pt, tick label pt, annotation pt, marker size, line width, axis/spine width, grid | style tokens |
| ③ Axes & labels | title, x label, y label (in *4. Labels & size* on desktop), x/y tick angle (auto / 0 / 45 / 90), x/y label padding, title padding | layout |
| ④ Legend | location (auto, inside upper/lower left/right, outside right/left/top/bottom), legend pt, legend outside | layout / style |
| ⑤ Colorbar | location (default/right/left/top/bottom), pad, size | mapping (read by colorbar-capable plots) |

**Reset to publication defaults** returns every control to the defaults.

![Publication style controls (desktop).](../../assets/screenshots/desktop_04_publication_controls.png)

![Publication style expanders (browser).](../../assets/screenshots/streamlit_04_publication_controls.png)

### 43. Capability-aware honesty

Not every control applies to every plot: bars have no markers, a heatmap has no categorical palette, a network has no axes. Which controls a renderer honours is declared per plot type in `styles/capabilities.py`, and that table is **generated from the renderer source** and checked by a test, so a control shown for a plot is one the code reads. When a control does not apply the app says so — a caption under the controls (desktop) or yellow notices under the figure (browser). Because the browser app always sends every style token, a bar plot shows notices for marker size, line width and legend controls even at their defaults; they are informational.

### 44. Axis ranges and ticks

Some plot types expose **x_min / x_max / y_min / y_max** and **y ticks** options (histogram, Kaplan-Meier, forest plot); line plots also take a layout **x/y axis scale** (linear, log, symlog — a log axis is skipped when the data include non-positive values). A range that would hide plotted data is **refused** with a message, never silently clipped — a truncated axis overstates differences. Leave the field on *(auto)* to let the figure choose.

## Part XII — Colour customisation

### 45. Where colours come from

| Colour model | Plots | Control |
|---|---|---|
| Categorical palette (one colour per category/series) | bar, grouped bar, box/violin, strip, beeswarm, raincloud, line, ridge, histogram, KM, ROC, PR, calibration, dose-response, forest, waterfall, stacked, swimmer, spider, Sankey, UpSet, lollipop, oncoprint, dendrogram, paired slopegraph, MA, Manhattan, PCA, embedding, network | **Palette** (publication, colorblind_safe, high_contrast, grayscale) |
| Continuous colormap (+ colorbar) | clustered heatmap, hierarchical clustering, confusion matrix, enrichment dot plot, embedding (continuous colour), network (node colour by value) | `colormap` option (heatmaps: auto, RdBu_r, coolwarm, seismic, RdYlBu_r, PuOr, BrBG, viridis, magma, cividis, Blues, YlOrRd, Greys); the palette also switches the sequential/diverging maps (grayscale → Greys/gray) |
| Significance classes | volcano (`color_up`, `color_down`, `color_ns`), MA (`color_ns`) | options with a curated colour list; the palette does not apply to the volcano and the app says so |
| Threshold-line colour | Manhattan (`cutoff_line_color`, style, width) | options |
| Node / edge mapping | network (`node_color`, `node_cmap`, `edge_color`, `edge_color_positive`, `edge_color_negative`, `label_color`, custom node-colour JSON in the browser) | options |
| Point / line colour | paired slopegraph (`point_color`, `line_color`) | options |
| Cell borders / separators | heatmap (`cell_border_color`, `group_separator_color`) | options |

Colours in option lists are hex values and named Matplotlib colours from curated lists; there is **no free colour picker** in either app. A colour that is not in a list can be set by editing the PlotSpec JSON (any Matplotlib colour name or hex) and reopening it.

### 46. Volcano example

![Volcano options: up/down/not-significant colours, cutoffs, labelling and duplicate-label policy.](../../assets/screenshots/desktop_10b_volcano_options.png)

Set **Up-regulated colour**, **Down-regulated colour** and **Not-significant colour** in *3. Options*; the points recolour immediately. Save a style preset to reuse the three colours on every volcano.

### 47. Category mapping example

A categorical palette assigns colours in category order. To fix which category gets which colour, order the categories in your table (or in the grouping step) — the first category takes the first palette colour. Per-category manual colour maps exist only for the network graph (custom node-colour JSON, browser) and oncoprint alteration classes (fixed).

## Part XIII — Annotations

### 48. Click to label (desktop)

Tick **Point picking — Click a point to identify / label it** (4. Labels & size). On volcano, MA, scatter and embedding plots, clicking near a point shows its name in the status bar and **toggles a label** on it; clicking again removes it. Volcano and MA toggle by *point identity* (row), so two rows sharing a gene symbol are independent; other plots toggle by label text. Selections are stored in the PlotSpec (`selected_points` / `selected_labels`) and survive export and reload.

![Labels & size with Point picking enabled.](../../assets/screenshots/desktop_13_annotation_controls.png)

Manual offsets: the desktop app does **not** currently support dragging a label; offsets stored in a PlotSpec (`label_offsets`, `point_offsets`) are honoured when rendering.

### 49. Label points (browser)

The **Label points (annotate)** expander (volcano, MA): choose **Points to label** from the list, then **Move which label** with **x offset / y offset (pt)** and **Reset this label position**. The same AnnotationState round-trips into the PlotSpec as the desktop picks.

![Browser volcano with the Label points expander.](../../assets/screenshots/streamlit_10_volcano_editor.png)

### 50. Duplicate feature labels (volcano and MA)

Several rows may share one symbol (peptides of a protein, probes of a gene). **Duplicate label handling:** *Label every selected point* (`all`), *one representative per label* (`unique`), or *representative + count* (`count`). The **representative** is chosen by rule: smallest p-value, smallest adjusted p, largest absolute effect, highest absolute statistic, or first row. Row identity is never collapsed in the data — only in what is labelled.

### 51. Other label controls (volcano/MA)

In *3. Options*: **Show labels** (master switch); **Label mode** (e.g. `top_fdr`); **Top N labels**, **Top N up**, **Top N down** (how many extreme features get labels); **Label by** (which column supplies the text, e.g. `symbol`); **Arrows to points** (leader lines); **Label background box**; **Duplicate labels** / **Representative point** / **Append (n=…) count** (§50). Label collisions are resolved automatically with `adjustText`.

### 52. Manual annotation layer

A PlotSpec may carry an `annotations` list — text, arrow, callout, box, region, bracket, hline, vline — with coordinates in data, axes or figure space, colour, font size, line width, alpha and z-order. They are applied to every plot type on render and exported with the figure. There is no in-app drawing editor for generated plots; imported Figure Builder panels accept annotations through the builder. Positions are data-specific and travel only in a **full** preset (with a warning that they may need moving).

## Part XIV — Figure presets

![PlotSpec versus Figure preset.](../../assets/diagrams/plotspec_vs_preset.png)

### 53. What a preset is

A **Figure preset** is the reusable part of a figure's configuration, saved without the data. A **PlotSpec** is the exact record of one figure including the table name and its columns. Presets are files (`*.mmfpreset.json`, format `make_my_figure.figure_preset`, version 1) kept in a per-user library that both apps share.

Two kinds:

- **Figure style only** — typography tokens, palette, layout geometry (width preset, tick angles, paddings, margins, legend location, colorbar geometry), export defaults (formats, size, DPI), statistical *display* settings (annotation content/placement), and the plot's **visual** options. Portable to any dataset of the same plot type; universal parts (fonts, palette, layout) also apply to other plot types.
- **Full figure configuration** — all of the above **plus** column roles, analytical options (thresholds, bins, clustering method…), axis labels, the statistics test block, and manual annotations. Applies only to the same plot type.

Never in a preset: the table name, worksheet provenance, row values, click-selected points and their offsets.

### 54. Which options are visual

Every plot option declares a **scope** in the registry. Visual (style) examples: box vs violin, histogram bars/line, panel arrangement, colormap, node colours, error-bar type, tick angle, show/hide fit statistics. Analytical (full only) examples: volcano/MA/Manhattan thresholds, bin width and count, clustering distance/linkage, `k`, axis limits, input form, `top_n`, correlation cutoffs. The default for a new option is analytical, so a threshold cannot leak into a lab style by omission. The plot catalogue (Part X) lists both sets for each plot.

### 55. Saving

**Desktop:** *Figure preset* group → **Save preset…** → name → *Figure style only* or *Full figure configuration* → **Save**. **Browser:** *Figure preset* expander → *Save preset* form → name → *Save* radio → **Save**; a **Download the saved preset** button appears. The preset is written to the library and listed for its plot type.

![Save Figure Preset (desktop).](../../assets/screenshots/desktop_11_figure_preset_save.png)

### 56. Applying

Choose a preset for the current plot type (universal presets are listed for every type) → **Apply**. The controls move to the preset's values — including tick angles, legend location, margins, colorbar geometry, options and (full presets) column roles — and the figure re-renders. The status line reports how many settings applied and how many did not apply to this plot type.

![Figure preset group with saved presets (desktop).](../../assets/screenshots/desktop_12_figure_preset_load.png)

![Figure preset expander (browser).](../../assets/screenshots/streamlit_11_figure_preset.png)

### 57. Compatibility, remapping, warnings

- A **full** preset saved for another plot type is refused (its roles and thresholds mean nothing elsewhere).
- A **style** preset saved for another plot type applies its universal parts and lists the plot-specific options it dropped.
- A full preset whose columns the new table lacks reports each missing role — *"wanted 'x_marker' … nothing was substituted"* — and leaves that role for you to set in *Map columns*. Statistics columns the table lacks are cleared and reported the same way.
- Manual annotations from a full preset are restored at their saved positions with a warning.

### 58. Import, export, delete, reset, sharing

**Import…** adds a `.mmfpreset.json` (or an old PlotSpec / sidecar, converted to a full preset) to the library. **Export…** writes the selected preset to a file for a colleague. **Delete** removes it from the library. **Reset to Publication defaults** returns every style control to the defaults without touching the library. To share a lab style, export `Lab_Default_Heatmap.mmfpreset.json` and have colleagues import it.

### 59. Storage location and versioning

| OS | Library folder |
|---|---|
| Windows | `%APPDATA%\MakeMyFigure\presets` |
| macOS | `~/Library/Application Support/MakeMyFigure/presets` |
| Linux | `$XDG_DATA_HOME/make_my_figure/presets` (default `~/.local/share/make_my_figure/presets`) |

The environment variable `MAKE_MY_FIGURE_PRESETS` overrides the folder (portable installs, shared network folders, tests). Files carry `format_version`; a preset from a newer version is refused with a clear message rather than misread. Foreign JSON files in the folder are ignored.

### 60. Lab workflow

1. Finalise a heatmap (colormap, fonts, colorbar placement, cell borders, double-column width).
2. **Save preset…** → *Lab Heatmap* → *Figure style only*.
3. Months later, load a new matrix, choose *Clustered heatmap*, **Apply** *Lab Heatmap*.
4. Adjust only what is data-specific: feature/value columns, clustering method, title.
5. Export; the PlotSpec of the new figure records everything, including that the preset's values are in effect.

**Worked example with bundled data (dataset A → preset → dataset B).** You can repeat this with the two apps' bundled examples; it is also executed by the release validation script (`scripts/validate_documented_workflows.py`, results in `docs/manuals/audit/v1.1.0_documentation_validation.csv`).

1. *Dataset A:* **File → Open example → Box / violin with points** (desktop) or *Bundled sample → Box / violin with points* (browser). Set **Palette** to *colorblind_safe*, **Marker size** to 30 and, in *3. Options*, **Point size** to 20.
2. **Save preset…** → *Lab box style* → *Figure style only*. The file `Lab_box_style.mmfpreset.json` appears in the preset library (Section 59); it contains the palette, the marker size and the point size but no column names and no data rows.
3. *Dataset B:* open your own CSV with a different group column and value column (any two-column long table), choose *Box / violin with points*, map `x` and `y` yourself.
4. **Apply** *Lab box style*. The palette, marker size and point size move to the saved values; your `x`/`y` mapping is untouched because a style preset never carries roles. The status line reports how many settings applied.
5. Export. The new PlotSpec records the applied values, so the figure is reproducible without the preset file.

If you had saved a **full** configuration in step 2 instead, step 4 would also try to restore the roles `x = group` and `y = value`; when dataset B has no columns with those names the status line lists each unresolved role ("wanted 'x' … nothing was substituted") and you map them in *Map columns*.

**Categorical colours after applying a preset.** A preset stores the *palette*, not a table of category → colour pairs. Categories of dataset B receive the palette colours in the order in which they appear in dataset B (Section 47), so the first category in B gets the first palette colour even if a category of the same name was second in A. To pin a category to a colour, order the categories in the table (or in the grouping step) identically in both datasets. The exceptions are plots whose colours are options rather than palette entries — volcano and MA class colours (`color_up`, `color_down`, `color_ns`), Manhattan threshold-line colour, network node/edge colours, paired-slopegraph point/line colours: these are style options and are carried by the preset exactly.

## Part XV — PlotSpec and reproducibility

### 61. What a PlotSpec records

`plot_type`, `input_table`, `mapping` (roles + options + click selections), `journal_style`, `output` (formats, width/height mm, DPI), `layout` (labels, geometry, legend, margins), `style` (token overrides), `statistics` (test, comparison, correction, annotation, columns), `annotations`, `column_annotations` (heatmap group strips), `source` (workbook name and hash, worksheet name/index/type, header row, Matrix Workflow provenance). The sidecar adds `render_metadata`: rows and columns used, plot-specific facts (bins, n per group, clusters…), the publication check, layout QC, software versions for statistics, and the Publication disclaimer.

### 62. Reload

**Desktop:** *File → Open PlotSpec…* — pick the JSON; the app looks for the data table by name next to it (or the only data file in that folder) and otherwise asks. Every control is restored through the same path a preset uses. **Browser:** *Data source → Open PlotSpec* — upload the JSON and the data table. The figure is **reconstructable under a recorded software environment**: same code, same data, same figure. Different machines may differ in fonts and text metrics; that is expected and not a reproducibility failure.

### 63. Related records

`name.stats_spec.json` (every statistical result), `name.figure_spec.json` (a composite: panels with their PlotSpecs, layout, draft legend), MatrixSpec / SampleMetadataSpec / PreprocessingSpec inside the Matrix Workflow provenance and QC report.

## Part XVI — Figure Builder

![Figure Builder provenance: generated and imported panels, the composite, the FigureSpec and layout preset.](../../assets/diagrams/figure_builder_provenance.png)

### 64. Opening it and adding panels

Render a plot, then **Save current plot as panel** (5. Export / 6. Multi-panel figure group); the counter shows *N panels saved*. **Add to Figure Builder** on a recommendation card does the same for that recommended plot. Then **Open Figure Builder…**.

![Figure Builder (desktop).](../../assets/screenshots/desktop_14_figure_builder.png)

### 65. Importing external panels

**Import panel from file…**: PNG, JPG/JPEG, TIF/TIFF, WEBP, BMP directly; PDF, SVG and EPS when the optional `import-panels` extra is installed (`pip install -e ".[import-panels]"`: PyMuPDF and cairosvg) — those are **rasterised at 300 dpi** on import. The file is copied into a managed assets folder and recorded (original name, dimensions, DPI, checksum, page). Imported panels have their own controls: fit mode (contain / fill / crop / stretch), crop fractions, rotate (0/90/180/270), flip, auto-trim, background, border, and annotations in normalised coordinates. Publication-readiness warnings flag low resolution or stretching.

### 66. Layout controls

| Control | Effect |
|---|---|
| Figure name | title used in the draft legend and file names |
| Columns / Rows | grid (Auto derives one from the panel count) |
| Figure width (mm) | overall width; 89 mm ≈ single column, 180 mm ≈ double |
| Horizontal / Vertical gutter | spacing between cells (fractions) |
| Panel labels | A B C / a b c / 1 2 3, bold, top-left of each panel |
| Export DPI | raster DPI for the embedded panel content |
| Selected panel size — Width / Height (inches) | the panel's cell size; proportions are preserved (never stretched); Height *auto* follows the panel's own ratio |
| Move up / Move down / Remove / Duplicate | order = label order |
| Fonts (points, applied to all panels) | text, axis labels, tick numbers, legend, panel letters |

There is **no** free x/y positioning, z-order or snap grid: the builder is a grid with per-cell sizes and width/height ratios derived from the widest/tallest panel per column/row.

![Figure Builder after widening panel A and setting a 2 × 2 grid.](../../assets/screenshots/desktop_15_figure_builder_resize.png)

### 67. Layout presets

**Layout preset** group: **Save…** (grid, gutters, width, label style, fonts, per-panel sizes — no panel content), **Apply** to the current panels (sizes are applied positionally; a count mismatch is reported), **Import…** (a `.mmflayout.json`, or a `.figure_spec.json` whose geometry is taken and panels left behind), **Export…**, **Delete**. Files use format `make_my_figure.figure_layout_preset` in the same library folder as figure presets.

### 68. Export and FigureSpec

**Save figure…** writes PNG (and SVG and PDF alongside) at the export DPI, plus `name.figure_spec.json` (panels with PlotSpecs, stats specs, sizes, imported-asset records, layout, auto-drafted legend text — verify the draft before use). Imported assets are copied to `figure_builder_assets/` next to the figure so the FigureSpec reloads.

**Warning:** the composite embeds each panel as a **raster** image at the export DPI; only panel letters and titles are vector text, even in the SVG/PDF. For fully vector output export single plots directly.

### 69. Browser Figure Builder

Inside the guided Matrix workflow, step **⑤ Figure Builder** lists the panels generated in that session, takes a **Columns** value and **Compose multi-panel figure** offers PNG/SVG/PDF downloads; **Clear Figure Builder** empties it. Per-panel sizing, imports and layout presets are desktop-only.
