# Plot-aware style controls

The single visible style is **Publication**. Not every style control applies to
every plot type, so the app is **plot-aware and honest**: a control either affects
the active plot, or it is flagged/disabled with a reason. There are **no silent
no-op controls**.

## How it works

`make_my_figure_core/styles/capabilities.py` declares, per plot type, which controls
apply (`PlotStyleCapabilities`). Helpers:

- `get_style_capabilities(plot_type)` — the capability flags for a plot type.
- `filter_style_controls_for_plot(plot_type, style_spec)` — keep only supported keys.
- `validate_style_controls_for_plot(plot_type, style_spec)` — `(key, ok, reason)` list.
- `warn_ignored_style_controls(plot_type, style_spec)` — warnings for present-but-
  unsupported controls. The render path calls this, so an inapplicable control shows
  up as a warning on the result (and in the Streamlit style panel as a caption).

## Universal controls (apply to essentially all plots)

Font family; title / axis / tick / annotation font sizes; title & axis-label padding;
figure width/height; DPI; background; export format.

## Plot-specific controls (examples)

| Plot family | Extra controls |
|---|---|
| bars / box / violin / points | categorical **palette**, marker size |
| heatmap / clustering / confusion | continuous **colormap** + colorbar (no per-point marker) |
| volcano / MA | significance colors, label colors, marker size |
| PCA / scatter | group colors, marker size, regression readout |
| line / KM / ROC / PR | line width (marker optional) |
| **network** | node colors, edge colors, node size, edge width, layout, labels, legend |
| sankey / stacked bar | category colors |

## Unsupported controls

If a control does not apply to the active plot it is **not silently ignored**:

- the render result carries a warning (`"Style control 'marker_size' does not apply to
  network plots …; it was ignored"`), and
- the Streamlit style panel shows an "ⓘ Not applicable to …" caption.

Examples: x/y axis-label padding and marker size do not apply to axis-free **network**
plots (use node/edge colors, node size, edge width instead); a heatmap colormap does
not apply to a bar plot; node colors do not apply to a bar plot.

## Design rule

Do **not** force every control to be global. Some are universal, some are
plot-specific, some are irrelevant — and the UI/engine makes that explicit. See
[PUBLICATION_STYLE.md](PUBLICATION_STYLE.md) and [NETWORK_GRAPH.md](NETWORK_GRAPH.md).
