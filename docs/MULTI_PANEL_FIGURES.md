# Multi-panel figures

The Figure Builder assembles individual plots into a labelled composite
(Figure 1A, 1B, 1C, …) ready for a manuscript.

## Workflow (desktop app)

1. Build a plot as usual (map columns, choose a style, add statistics).
2. Click **"Save current plot as panel"** — this stores the panel's PlotSpec +
   data (and StatsSpec if statistics are enabled).
3. Repeat for each panel.
4. Click **"Open Figure Builder…"**. The builder opens with a **live preview**
   on the right that re-renders as you change anything — nothing is written to
   disk until you click **Save**.
5. Set the **figure name** (e.g. *Figure 1*, *Extended Data Figure 1*,
   *Supplementary Figure 3*).
6. Choose the **number of columns** (Auto / 1 / 2 / 3 / 4) and the export DPI.
7. Reorder, remove, or duplicate panels — labels A, B, C… update automatically.
8. Select a panel and set its **approximate size in inches** (width × height,
   like Matplotlib's `figsize` — e.g. 4×4 is square, 4×6 is taller). Leave the
   height on **auto** to keep the panel's own aspect ratio. Panels are always
   scaled *without distortion*, so a larger number just yields a larger version
   of the same figure.
9. Adjust the figure-wide **fonts** (general text, axis labels, tick numbers,
   legend, and the bold panel letters) — sensible publication defaults are
   pre-filled.
10. When the layout looks right, click **"Save figure…"** to write SVG + PDF +
    PNG and a `*.figure_spec.json` sidecar, plus a draft legend.

## Layout

- **Automatic grid** by default (roughly square); or fix the column count.
- Column widths and row heights follow each panel's requested size; panel
  content is **scaled uniformly (never stretched)** and letterboxed within its
  cell if the requested box doesn't match its natural aspect ratio.
- Bold, top-left **panel labels** are drawn as vector text with a consistent
  offset, clear of the axes.
- Per-panel titles are **off by default** (the panel letter + the figure legend
  already identify each panel); they can be re-enabled programmatically.
- Consistent margins and spacing; unused trailing grid cells are hidden.

## Vector vs raster

Panel *content* is embedded at the configured DPI (default 300) while panel
labels and titles remain **editable vector text**. This always produces a
correct, aligned composite without a fragile SVG-splicing step. Because each
panel's PlotSpec is recorded in the sidecar, any individual panel can still be
re-exported as fully vector SVG/PDF from its spec.

For fully-vector composites, export each panel as SVG/PDF individually and
assemble them in Illustrator/Inkscape; use the Figure Builder for fast,
reproducible, review-ready composites.

## The figure sidecar

`*.figure_spec.json` records the figure name, every panel's label/title/PlotSpec/
StatsSpec, the layout settings, and a **draft** auto-generated legend. The draft
legend is assembled from panel titles, variables, and statistics method reports;
it is clearly marked as a draft and never fabricates biological interpretation —
verify and expand it before publication.

## Programmatic use

```python
from make_my_figure_core.panels import (
    MultiPanelFigure, FigureLayout, Panel, build_figure, export_multipanel,
)

mpf = MultiPanelFigure(name="Figure 1", layout=FigureLayout(ncols=2, fig_width_mm=180))
mpf.add_panel(Panel(plot_spec=spec_a, table=df_a, title="Treatment effect"))
mpf.add_panel(Panel(plot_spec=spec_b, table=df_b, title="Survival"))
fig = build_figure(mpf)
export_multipanel(fig, "Figure_1", ["svg", "pdf", "png"], dpi=300)
```

## Imported external panels (v0.5)

The Figure Builder can also import an **existing figure file** (PNG/JPG/TIFF, or
PDF/SVG with an optional converter) and place it as a panel alongside Make My
Figure plots — for assembling figures that mix, e.g., a generated volcano with a
microscopy image or a Prism/BioRender export. Use **“Import panel from file…”**.
Imported assets are copied into `figure_builder_assets/` and recorded in the
FigureSpec (basename + checksum + dims/DPI + crop/fit settings). Imported PDF/SVG
are rasterized in the composite. See
**[IMPORT_EXTERNAL_PANELS.md](IMPORT_EXTERNAL_PANELS.md)** for formats, controls,
warnings, annotations, and limitations.
