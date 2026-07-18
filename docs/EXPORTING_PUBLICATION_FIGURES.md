# Exporting Publication Figures

Make My Figure exports **SVG, PDF, PNG, and a PlotSpec JSON** sidecar. Every plot
is publication-styled by default (readable fonts, strong contrast, clean axes,
non-overlapping legends).

> **Worksheet-aware names:** when the data comes from a multi-sheet Excel workbook,
> export filenames include the worksheet name (e.g. `Sol_24M_vs_6M_volcano.svg`) so
> outputs from different sheets never overwrite each other, and the PlotSpec/StatsSpec
> sidecars record the workbook + worksheet provenance. See
> [MULTI_SHEET_EXCEL.md](MULTI_SHEET_EXCEL.md).

## Which format to use

| Format | Use for | Notes |
|---|---|---|
| **SVG** | Final manuscript editing | Vector; **text stays editable** (`svg.fonttype=none`) so you can adjust labels in Illustrator/Inkscape. |
| **PDF** | Vector submission / print | Vector; fonts embedded as editable text (`pdf.fonttype=42`). |
| **PNG** | Slides, previews, quick sharing | Raster; default **300 DPI**, selectable up to 600 DPI. |
| **PlotSpec JSON** | Reproducibility | Records plot type, column mapping, style, and output settings. |

**Prefer SVG or PDF for final figures** — they scale losslessly and keep text as
real, editable characters, so a journal (or you) can restyle text without
re-rendering. Use **PNG at 300–600 DPI** where a raster is required.

## How to export

- **Desktop app** — the "Export" panel: SVG / PNG / PDF / PlotSpec JSON, or
  "Export all as ZIP". Set **Raster DPI** in "Labels & size".
- **Streamlit app** — download buttons under the preview.

## Export-safe layout

- Exports use a **tight bounding box**, so outside legends and long labels are
  never clipped in the file.
- Vector text mode is applied automatically at save time (SVG/PDF keep editable
  text) regardless of the on-screen preview.
- Choose a figure **width preset** (`default`, `single`, `onehalf`, `double`) to
  match your target column width; sizes are defined in mm.

## Custom style presets

Adjust fonts, line widths, markers, palette, and legend placement in the app's
style controls (see [STYLE_PROFILES.md](STYLE_PROFILES.md)). The settings are
carried in the PlotSpec's `style` block, so exporting the PlotSpec JSON captures
your custom look for reuse.

> Publication-style aesthetics only — not a guarantee of official
> journal compliance. Bundled example data are synthetic.

## Statistics and multi-panel exports

When statistics are enabled, exporting also writes a `*.stats_spec.json` sidecar
alongside the figure. It records the configuration, every result (test, groups,
n, p-value, adjusted p-value, correction, effect size, CI), the method paragraph,
and library versions — so the statistics are fully reproducible. The statistics
config is also embedded in the PlotSpec under `statistics`. Results tables export
as CSV/TSV and method reports as Markdown or JSON. See
[STATISTICS.md](STATISTICS.md).

For composite figures, the Figure Builder exports SVG/PDF/PNG plus a
`*.figure_spec.json` sidecar (panel labels, per-panel PlotSpecs/StatsSpecs, layout,
and a draft legend). Panel content is embedded at the chosen DPI while labels stay
vector; each panel remains independently exportable as vector from its PlotSpec.
See [MULTI_PANEL_FIGURES.md](MULTI_PANEL_FIGURES.md).
