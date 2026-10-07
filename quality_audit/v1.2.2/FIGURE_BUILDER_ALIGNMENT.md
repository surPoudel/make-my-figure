# Figure Builder: measured alignment and panel sizing

Reported against the v1.2.1 build with two screenshots and a saved
`Figure_1.mmfpackage`: four unmodified example plots (bar with error bars,
clustered heatmap, scatter with regression, volcano) added as panels A-D of a
2x2 figure, then panel C widened from 3.2 in to 4.2 in.

Every number below is from `make_my_figure_core.panels.builder.panel_frames`,
which reports where each panel's **plotting frame** - not its picture - landed
on the composite, in inches. The reproduction harness loads the user's own
package, so these are that figure, not a stand-in.

## What was wrong, and what it measures now

| # | Reported | Before | After |
|---|----------|--------|-------|
| 1 | "As I try to increase width of C, the alignment between A and C changed" | A.x0 - C.x0 = **0.408 in** at C = 4.2 in | **0.0000 in**, at C = 3.2 / 4.2 / 5.0 in |
| 2 | B -> D alignment | 0.000 in (already held) | 0.0000 in |
| 3 | Widening C moved A | A's frame x0 **0.726 -> 0.839 in**, width 2.378 -> 2.250 in | x0 **0.664 -> 0.664 in**, width 2.732 -> 2.730 in |
| 4 | "The plot should be unchanged and reduced as exact to put in panel" | a panel asked for 3.2 in got a **2.684 in** cell (0.84x, which the help text apologised for) | **3.200 in**, exactly |
| 5 | Row bottoms/tops | panel *images* top-aligned; the plots inside them were not | frame tops equal to **0.002 in** per row |
| 6 | "The text kill the scatterplot C" | the 6-line regression box measured **209 px against a 210 px axes** - the full width of the plot - and its legend took **38%** of the panel | box <= 65% of the axes width and <= 28% of its area; legend moved inside |
| 7 | Volcano count line | wrapped onto **3 lines**, the last reading `1)` | **1-2 balanced lines** |
| 8 | Panel A's y-axis label | drawn as `measurement (mean ± SE` - cropped | full text, wrapped or shrunk to fit |
| 9 | Type sizes across panels | axis labels **12.0 pt in C, 10.21 pt in A** | one value in every panel |
| 10 | "Diminish heatmap and the fonts should also decrease" | 30 row labels became an illegible grey stack | type scales with the smallest panel; labels thin to 1 in 3 and say so |

## How the alignment works now

`build_figure` is three steps instead of one:

1. **Draw every panel as it was finalized** and measure two boxes: the image
   box, and the union of its data axes. The difference is the pad - the inches
   of y-axis label, tick numbers, legend and colourbar wrapped around the plot.
2. **Draw each panel again at the size it will occupy**, and re-measure. A panel
   drawn smaller may wrap its title or drop a tick, so the first measurement is
   only good enough to reserve room with.
3. **Build the grid from the second measurement** and place each panel by its
   frame: one shared left edge down each column, one shared top edge across each
   row. The figure size is computed so that a grid cell is exactly the inches
   its panel asked for.

Two supporting changes make the alignment *stable* rather than merely correct:

* **Panel margins are fitted to their content.** A renderer sizes its margins as
  a fraction of its canvas, so the same axis label reserved 0.394 in at 3.2 in
  wide and 0.519 in at 4.2 in - which moved the column's shared edge every time
  a panel was resized. Fitted margins are a measurement in inches and do not
  drift. They also give the plot the room: panel A's frame went from 2.378 in to
  2.732 in inside the same 3.2 in panel.
* **One type hierarchy per figure, scaled to the smallest panel.** Scaling each
  panel to its own canvas is what put 12 pt axis labels beside 10.2 pt ones.
  Taking the *median* panel instead made a single edit global - widening C
  restyled the figure, which grew C's own legend until it no longer fitted
  beside its plot, so widening C made C's plot narrower. The smallest panel is
  the one the type has to stay legible in, and using it means making a panel
  bigger never restyles anything.

## Second report: the block edge, not just the plot edge

Re-tested on `2ba687a` with a second package (`Figure_1_new`: box plot, bar
chart, clustered heatmap, Kaplan-Meier). Measured on the preview PNG, in pixels
of a 2159 px wide figure:

| | panel A (box plot) | panel C (heatmap) |
|---|---|---|
| plot frame left | x = 227 | x = 229 |
| leftmost ink (the y-axis label) | x = **77** | x = **41** |

So the frames were aligned to a pixel and the blocks were 36 px - about 3 mm on
a 180 mm figure - out of line, which reads as the heatmap sticking out past its
neighbour. Both can be true at once: a y-axis label is positioned by a pad
rather than by the data, so the narrower panel's label is pushed out until its
leading decoration measures the same as the column's widest. After the fix, on
the same package:

| | frame x0 | block x0 (leftmost ink) |
|---|---|---|
| A | 0.950 in | 0.234 in |
| C | 0.950 in | 0.234 in |
| B | 4.484 in | 4.054 in |
| D | 4.484 in | 4.055 in |

The panel letter now hangs off the block's top-left corner rather than the
plot's, with its offset taken against the column width, so the letters line up
down a column too (measured 1 px apart, which is the difference between the
antialiased apex of an `A` and the bowl of a `C`).

## Bottom alignment is now a control

Panels in a row are drawn the same height already; what differs is how much of
that height goes below the axes. In the reported figure, panel A (rotated
category labels) and panel B (a heatmap) differed by **1.52 in** of frame
height, which is why their bottoms could not be lined up. With **Match plot
heights across each row**:

| | A frame | B frame | C frame | D frame |
|---|---|---|---|---|
| off | 6.440 – 8.205 | 4.918 – 8.205 | 0.396 – 3.214 | 1.158 – 3.214 |
| on  | 5.048 – 8.335 | 5.048 – 8.335 | 0.434 – 3.253 | 0.434 – 3.253 |

Off by default, because it draws a panel at a height other than the one that was
asked for.

## Gates

| Gate | Result |
|------|--------|
| Full suite, serial (authoritative — CI runs serially) | **4023 passed**, 4 skipped, **0 failed** in 44 min, on `8b3f614` |
| Full suite, `-n 12` | 4022 passed, 4 skipped, 1 failure: `test_pop_out_panels` crashes an xdist worker (Qt) and passes serially |
| New permanent regression tests | `tests/test_figure_builder_alignment.py`, **20 tests**, all 10 reported defects |
| Gallery audit, 45 registered plot types | **45/45 clean**; render, publication render, PNG/SVG/PDF export, PlotSpec round-trip, package round-trip |
| Clipped text, all 45 | **0** (unchanged) |
| Overlapping text pairs, all 45 | **36 -> 34** (bland_altman_plot 3 -> 1) |
| Colour contract | 119 controls audited, 3 with no effect - the same three continuous-colormap plots as v1.2.1, unchanged |

## Cost

`build_figure` draws each panel twice and measures it, which is what it did
before (once to size the grid, once at the drawn size). Measured on the reported
figure, the two builders are the same speed:

| | 4 panels | 8 panels |
|---|---|---|
| before | 5.84 s | 11.13 s |
| after  | 5.84 s | 10.70 s |

So the live preview is no slower - but it is slow, at about 1.4 s per panel, and
that is a pre-existing cost rather than a new one. The preview now also caps the
panel raster DPI at 150 (it is displayed at 110), so a figure set to export at
600 DPI no longer rasterizes every panel at 600 for a preview nobody sees.

## Known, unchanged

* `confusion_matrix`, `enrichment_dotplot` and `spatial_feature_map` expose a
  categorical palette control that a continuous colormap cannot use. Recorded in
  `palette_contract.csv` in both v1.2.1 and here.
* `spatial_categorical_map`, `spatial_composition_map` and
  `neighborhood_enrichment_matrix` still overflow a pinned 4 x 2 in canvas
  vertically (`KNOWN_VERTICAL_OVERFLOW_AT_4X2`). Pre-existing, tripwired.
