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

## Clipping / overlap QC (advisory)

Every render runs an advisory layout check (`make_my_figure_core/qa/layout_qc.py`,
stored on the result as `metadata["layout_qc"]`). It reports likely problems as
structured issues — `category` (clipping / overlap / font / density / missing_label /
colorbar), `severity` (warning / fail), the affected `artist`, a `message`, a
`suggested_fix`, and whether an **auto-fix** is available. Detection is bbox-based and
**approximate/honest** — it flags likely issues rather than guaranteeing perfection,
and it only inspects tick labels that are actually within the axes view (Matplotlib's
phantom out-of-range ticks are ignored).

Opt into automatic repair by setting `layout["auto_fix_layout"] = true`: the engine
rotates overcrowded x tick labels, reserves label room via tight layout, and grows the
figure to fit clipped content — **layout only, never changing any data, colors, or
statistics**. Applied fixes are listed in `metadata["layout_autofix_applied"]`.

## The styling contract

Seven rules every styling change is held to. They are not aspirations: each one
has a test that fails when it is broken, named beside it. A new plot type or a
new control inherits all seven.

1. **A visible control works.** If a control is shown for a plot type, moving it
   changes that plot. A control that cannot act is hidden, not disabled-with-a-
   shrug and not silently ignored. The capability registry decides, the GUI asks
   it, and the render path warns when a spec carries a key the plot cannot use.
   *(`test_legend_geometry.py`, `test_axis_label_visibility.py`, and the
   capability-driven sweep in `quality_audit/v1.2.2/styling_audit.py`.)*

2. **Legends are positionable.** Location, offset in points, gap to the plot and
   internal padding, on every plot type that draws a legend — through the shared
   `place_legend` path, never per renderer. Geometry is not relocation: nudging a
   legend must leave it where its plot type put it.
   *(`test_legend_geometry.py`.)*

3. **Colour semantics match the plot.** Four kinds of colour decision and they do
   not substitute for each other: categorical palettes for nominal groups,
   sequential maps for ordered magnitudes, diverging maps for signed values about
   a centre, and a named colour per artist for a semantic class (up / down /
   not significant) or a single accent. A sequential map is never offered for
   nominal categories — it would claim an order the data does not have.
   *(`test_palette_system.py`, `test_semantic_class_colors.py`.)*

4. **Categorical palettes scale with the group count.** Any N gets a colour. When
   N exceeds the palette's distinct capacity the render says so and names
   palettes that would fit, checked against their real capacity. Two different
   groups are never quietly given one colour. Individual categories can be
   overridden by name or by position, in any matplotlib colour including HEX.
   *(`test_palette_system.py`, 2 / 3 / 5 / 8 / 10 / 14 groups.)*

5. **No scientific value changes through styling.** Classifications, thresholds,
   limits, counts, p-values and fitted parameters are identical whatever the
   figure is coloured or positioned like. Every styling test asserts the numbers
   as well as the pixels.
   *(`test_semantic_class_colors.py`; the `science` column of the audit, which
   compares every numeric field of the render metadata.)*

6. **Preview, export, spec, package and builder agree.** A control's effect
   survives the PlotSpec, a style preset, a Figure Package and the Figure
   Builder, and two exports of the same figure are byte-identical. Text that is
   fitted to its axes is fitted for the size it is drawn at, so a 110-dpi preview
   and a 300-dpi export differ in fine text placement by design — within one
   output size the result is deterministic.
   *(the `roundtrip`, `export` and `export_parity` columns of the audit.)*

7. **A new plot starts clean.** Plot-local styling — palette, overrides, legend
   geometry, axis visibility — resets when the plot type changes. Nothing leaks
   from the previous figure.
   *(`test_axis_label_visibility.py::test_a_new_plot_starts_with_the_axes_shown_again`
   and the reset paths in `apps/desktop_app/main.py::reset_plot_styling`.)*

### Where to make a styling change

In the shared infrastructure, not in a renderer:

| Concern | The one place |
|---|---|
| categorical colour, overrides, capacity | `StyleProfile.color_for` (`styles/engine.py`) |
| the palette catalogue | `PALETTE_GROUPS` (`styles/engine.py`) |
| legend placement and geometry | `place_legend` / `offset_legend` (`plots/base.py`) |
| which controls a plot type shows | `styles/capabilities.py` |
| axis ticks and labels | `apply_publication_layout` (`plots/base.py`) |

A renderer that reaches past these opts out of everything they provide — which is
how a plot ended up unable to honour a per-category colour while advertising that
it could.
