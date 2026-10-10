# Make My Figure v1.3.0 — release notes

Two things: a Figure Builder whose panels line up, and style controls that do
what they say. It also carries everything that was prepared for v1.2.1, which was
withdrawn before release when the Figure Builder defects below were reported —
those fixes ship here.

Every number in these notes is a measurement, not an estimate.

## The Figure Builder lines panels up on their plots

A panel is a picture of a plot wrapped in its own y-axis label, tick numbers,
legend and colourbar, and those are a different width in every panel. Laying the
*pictures* out in a tidy grid therefore leaves the *plots* inside them crooked.
Measured on a reported 2×2 figure: the bar chart and the heatmap below it were
**0.408 in out of line**, and widening one panel dragged its neighbour's plot
sideways.

Panels are now drawn, measured and placed by their **plotting frame**: one shared
left edge down each column, one shared top edge across each row — 0.000 in at
every panel width. The panel *block* lines up too, so a heatmap's long row labels
no longer hang out past the chart above it, and the panel letter sits just
outside the block's corner.

Also in the builder:

- **A panel is the size you type.** The grid sat inside Matplotlib's default
  margins, so a panel asked for 3.2 in was drawn 2.684 in.
- **Match plot heights across each row** — optional, for when the bottoms should
  line up as well as the tops.
- **Panel padding** in millimetres: panel margins are fitted to their content, so
  that white space is yours to spend.
- **Fonts for every feature**, pre-filled with the sizes the panels are actually
  drawn with, so switching the override on changes nothing until you move one.
- An axis label is no longer cropped: "measurement (mean ± SEM)" came back as
  "measurement (mean ± SE" because Matplotlib leaves the along-axis extent of an
  axis label out of every tight bounding box it computes.
- A heatmap too small for its row labels shows fewer of them, legibly, and says
  how many.

## Legend positioning

Seven controls — offset X/Y and gap to the plot in **points**, plus inner
padding, row spacing, handle length and column spacing. They apply to every plot
type that draws a legend, through the shared legend path.

Geometry is **not** relocation: nudging a legend leaves it where its plot type
put it, so a volcano's outside key stays outside. Measured: an 18 pt offset moves
a legend 18.0 pt on every plot type tested.

**Legend outside** now works. It was dead on 25 of the 27 plots that draw a
legend, because sixteen renderers build their legend with a direct call that
never saw the flag.

## Colour that matches the plot

- **Palettes grouped by what they are for** — qualitative for categories,
  sequential for ordered magnitudes, diverging for signed values, grayscale. A
  sequential map is never offered for nominal categories.
- **Any number of groups.** Ten groups on an eight-colour palette used to give
  two different groups the same colour, silently. You now get a warning that
  names palettes which actually fit, checked against their real capacity.
- **Individual colours** by position or by group name, in any Matplotlib colour
  including HEX.
- **MA plot** gains Up / Down / Not-significant colours, like the volcano.
- **Bland–Altman** gains independent colours for the two limits of agreement, and
  can colour observations by agreement category — labelled as agreement limits,
  never as significance.
- **UpSet** can tell its set-size and intersection-size bars apart.

## Controls are offered only where they can act

A sweep of **45 plot types × 15 style controls** — change it, re-render, check
the figure changed — found 111 visible controls that did nothing. That is now 24,
and the 24 are all one honest category: the plot draws nothing of that kind (no
grid, no spines, no markers).

The colormap choosers were the clearest case. Which of the two governs a figure
depends on the **data**, not the plot type: a matrix that is centred or z-scored
is drawn with the diverging map and the sequential one does nothing to it. The
render now reports which one it used and the panel shows that one. Across all 45
plot types the reported role matches which control actually changes the figure,
with zero disagreements.

X/Y tick labels and X/Y axis names also gained show/hide boxes, on every plot
type at once. Hiding tick labels hides their tick marks too.

## Compatibility

Defaults are unchanged throughout. A figure, PlotSpec, style preset or Figure
Package made with v1.2.0 renders the same in v1.3.0; every new control is
opt-in, and a control left alone writes nothing into the spec.

## Verification

- Full test suite: **4211 tests**, serial run green.
- Capability audit, all 45 registered plot types: render, legend offset, palette,
  per-category override, PlotSpec round trip, export and two-exports-identical —
  **45/45 clean**, with every numeric field of the render metadata identical
  under styling.
- Visual QC sheets in `quality_audit/v1.2.2/visual_qc/`.
