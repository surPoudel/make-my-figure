# Multi-panel figures

The Figure Builder assembles individual plots into a labelled composite
(Figure 1A, 1B, 1C, …) ready for a manuscript.

## Workflow (desktop app)

1. Build a plot as usual (map columns, choose a style, add statistics).
2. Click **"Save current plot as panel"** — this stores the panel's PlotSpec +
   data (and StatsSpec if statistics are enabled).
3. Repeat for each panel.
4. Click **"Open Figure Builder…"**.
5. Set the **figure name** (e.g. *Figure 1*, *Extended Data Figure 1*,
   *Supplementary Figure 3*).
6. Choose the **number of columns** (Auto / 1 / 2 / 3 / 4), figure width, and
   panel DPI.
7. Reorder, remove, or duplicate panels — labels A, B, C… update automatically.
8. Click **"Build & export"** to write SVG + PDF + PNG and a
   `*.figure_spec.json` sidecar, plus a draft legend.

## Layout

- **Automatic grid** by default (roughly square); or fix the column count.
- Row heights adapt to each row's panel aspect ratios so panels are not
  distorted.
- Bold, top-left **panel labels** are drawn as vector text with a consistent
  offset, clear of the axes.
- Optional per-panel titles.
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
