# Make My Figure v1.2.1 — release notes

A corrective release. Everything below is a defect found in real use of v1.2.0
and fixed; there is no new scientific capability, and v1.2.0 remains available
unchanged.

Built from the v1.2.0 tag plus these fixes only — no unreleased development work
is included.

## Figure Builder no longer restyles a finished plot

A plot added to the Figure Builder kept its data but not its appearance. Measured
at identical physical dimensions, the title grew 50%, the axis labels shrank
37.5% and the statistics text grew 50% — inverting the type hierarchy by 2.4×,
which is why text collided and the figure had to be formatted a second time.

The builder's figure-wide font boxes always held a value, so the setting that was
supposed to mean "keep each panel's own typography" could never be selected. That
override is now a checkbox, **off by default**. When it is switched on it
replaces the whole type hierarchy rather than four of its nine sizes — a partial
override was what inverted the hierarchy.

At equal dimensions a panel now reproduces the standalone figure exactly.

## Statistics text

- The "Annotation font pt" control did nothing for the corner statistics panel:
  6 pt and 20 pt both drew 7.83 pt. It now sizes that panel.
- `p < 0.` was **not** a formatting fault. The formatter is correct; that was a
  correctly formatted string running past the edge of the canvas, with as little
  as 26% of it visible on a three-up panel. The panel is now fitted to the figure.
- At one decimal digit a significant result could be reported as `p = 0.0`. It now
  reads `p < 0.1`, which is true at any precision.

## A new plot starts from a clean state

Styling carried from one figure to the next — title, axis labels, fonts, palette,
margins, figure size, picked labels and statistics settings, 21 settings in all.
A box plot of unrelated data would arrive carrying the previous figure's title in
its fonts and palette.

The cause was structural: there was no plot-state object, only long-lived
controls that nothing ever cleared. Opening a PlotSpec or a Figure Package now
restores that specification **and nothing else** — loading used to add to
whatever was already on screen, so a specification carrying only margins came
back with the previous figure's palette, font and resolution. **File ▸ New plot**
has been added; it did not exist.

## Colour

- **The palette chooser offered the same palette twice.** `publication` and
  `colorblind_safe` differed at exactly one of eight entries, so any figure with
  six categories or fewer was identical between them — 40 of the 45 plot types.
  The first colour across the four palettes was blue, blue, black, black, which
  is why only black or blue appeared to work. `colorblind_safe` is now a distinct
  colourblind-safe scheme. Figures saved with the previous palette names still
  open unchanged.
- **Three groups now draw three colours** on the beeswarm and dot/strip plots.
  Colouring by the grouping column — the obvious request — was refused, and the
  fallback drew every group in one colour.
- **Spatial ROI regions are visible.** Without an ROI category column every
  outline fell back to the text colour and the fill defaulted to transparent, so
  an ROI table drew as a near-black wireframe. Outline colour, fill opacity and
  outline width can now be set; they existed but were unreachable from the
  interface.
- **Colour pickers for plots that use a single colour**, following the volcano's
  existing pattern: calibration, Bland-Altman, Q-Q, forest and dendrogram each
  expose a colour for every element they actually draw. Plots that cannot use a
  categorical palette now explain why instead of showing a control that does
  almost nothing.

## Matrix Workflow PCA

A PCA started from the Matrix Workflow now colours by the sample groups you
confirmed, with a legend, without asking again. Whether grouping applied used to
depend on which of two PCA entries was chosen, and the obvious one ignored it.

More seriously: supplying metadata could **change the analysis**. Samples were
restricted to those listed in the metadata before the decomposition, so an
incomplete metadata table silently removed samples and moved every score —
dropping one sample of six moved PC1 by about 20%, and four missing produced an
error about too few columns. Samples are now kept and drawn as `Unassigned`, the
count is reported, and the principal components no longer depend on the grouping.

## Figure margins

One change to a margin now produces one visible change. The controls offered
blank space while the layout engine expected edge positions, so nudging the right
or top margin produced a value the engine rejected — five clicks did nothing and
the sixth collapsed the plot. The same mismatch altered a saved figure when it
was reopened.

The title and axis-label boxes and the style-profile menu now redraw the figure.
They were connected to nothing, so typing a title produced no change until some
unrelated control triggered a redraw.

## Validation

- 22 permanent regression tests, one per defect, each failing on v1.2.0.
- Full suite: **3979 passed, 3 skipped** (v1.2.0: 3957 passed, 3 skipped).
- All 45 registered plot types audited for rendering, publication styling,
  PNG/SVG/PDF export, PlotSpec round-trip and Figure Package round-trip.

## Known limitations

- Windows and macOS builds were produced and smoke-tested automatically on their
  own runners; a person did not click through them before publication.
- The experimental publication presets are unchanged from v1.2.0 and still have
  had no user testing.
