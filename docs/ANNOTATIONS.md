# Universal manual annotations (v0.5)

Make My Figure has a reproducible manual-annotation layer that works on **any**
plot type — not just statistics. Annotations are stored in the PlotSpec under
`annotations` (a list of `AnnotationSpec` objects) and drawn as **vector**
artists after the plot renders, so SVG/PDF export keeps them editable and the
figure regenerates exactly from its spec.

## Annotation kinds
| `kind` | Draws | Uses |
|---|---|---|
| `text` | a text label at a point | `xy`, `text` |
| `arrow` | an arrow between two points | `xy` (head), `xy2` (tail) |
| `callout` | text at `xy2` pointing to `xy` | `xy`, `xy2`, `text` |
| `box` | an outlined rectangle | `xy`, `xy2` corners |
| `region` | a translucent shaded rectangle (ROI) | `xy`, `xy2` |
| `bracket` | a grouping bracket + label | `xy`, `xy2` |
| `hline` / `vline` | a reference line | `xy` (y or x) |

## Fields
`kind`, `annotation_id`, `text`, `xy`, `xy2`, `coords` (`data` | `axes` |
`figure`), `color`, `font_size`, `font_weight`, `box`, `arrow`, `arrow_style`,
`line_width`, `alpha`, `layer` (z-order), `visible`, `created_by`
(`user`/`statistics`/`volcano`/`heatmap`/`clustering`), and an optional semantic
`target` record. Unset styling inherits publication-grade defaults from the
active style profile.

## Coordinate systems
- `data` (default): anchored to the axes' data values (e.g. a gene's log2FC / −log10p).
- `axes`: 0–1 fraction of the axes (e.g. a corner note).
- `figure`: 0–1 fraction of the whole figure (e.g. a panel label).

## Example
```json
"annotations": [
  {"kind": "region", "xy": [1.0, 3.0], "xy2": [5.0, 9.0], "text": "cluster A", "color": "#0072B2"},
  {"kind": "callout", "xy": [4.2, 6.1], "xy2": [7.0, 8.0], "text": "hit", "arrow": true},
  {"kind": "text", "coords": "figure", "xy": [0.02, 0.96], "text": "A", "font_weight": "bold", "font_size": 16}
]
```

## Selecting targets
Feature/sample/point highlighting that needs a data lookup is handled inside the
relevant renderers (e.g. volcano `selected_labels` / `label_list`, heatmap
`highlight_rows`/`highlight_columns` — paste a gene list). Those renderers may
also emit coordinate annotations through this shared layer.

## Export
Vector formats (SVG/PDF) keep annotation text/shapes editable; PNG rasterizes
them at the export DPI. The `annotations` block is written into the PlotSpec
sidecar for full reproducibility. A single malformed annotation is skipped
without breaking the render or export.
