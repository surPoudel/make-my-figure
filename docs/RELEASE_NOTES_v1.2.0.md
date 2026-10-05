# Make My Figure v1.2.0 — release notes

Released from `main` at `420344b`, tagged `v1.2.0`, on 2026-10-05. Six new plot types, one typography system shared by
every renderer, and a figure width that no layer is allowed to overrule.

The registry count below is read from the live registry at release time, not maintained by hand:
**45 plot types** (39 in v1.1.1) and **18 statistical procedures**.

### Added — spatial plot types (39 → 45)

Six renderers for spatial tissue data, on a shared spatial core: neighbour graphs, local
composition, cellular-neighbourhood clustering and enrichment.

- **`spatial_categorical_map`** — a categorical cell or region map, with a scale bar per facet.
- **`spatial_composition_map`** — local neighbourhood composition.
- **`spatial_feature_map`** — a continuous feature on tissue coordinates, with a colour scale that
  states its own limits rather than implying precision it does not have.
- **`spatial_roi_map`** — region-of-interest map.
- **`spatial_transcript_map`** — transcript or gene positions.
- **`neighborhood_enrichment_matrix`** — cell-type neighbourhood enrichment.

Example data for all six is built from published colorectal-carcinoma tissue and bundled, so each
opens from the Examples menu with no download. Spatial figures round-trip through a
`.mmfpackage`, including the background image.

**Independent validation.** The spatial engine was checked against published results rather than
against itself: an exact numerical reproduction of CNTools Fig 3A (CRC, CC*), plus a second
hand-check that imports no project code; and for Janesick 2023, Xenium Fig 3l reproduced and the
Visium Fig 2c normalisation recovered.

### Added — figure size and typography

- **One typography system, shared by every renderer.** Title, axis label, tick, legend and
  annotation sizes come from a single scale with fixed ratios, and that scale adapts to the canvas
  instead of each renderer applying a floor of its own. A figure that is shrunk or enlarged keeps
  its hierarchy, and nothing is scaled past legibility.
- **One font setting produces one size on the page, in every panel.** In a multi-panel figure each
  panel was scaled independently — four panels of one figure came out at 69%, 71%, 98% and 66% of
  the requested size. Composite figures now lay out once at their drawn size.
- **Figure size is a real control on every plot type:** explicit width and height, in their own
  section, with working margins. A dimension too small to lay out is refused with an explanation
  instead of producing an unusable figure.
- **A requested width is final.** A single column, a double column or a measurement such as
  `174mm` now produces exactly that width on all 45 plot types — 225 of 225 plot-type × width
  combinations exact. Three layers used to overrule it: the layout pass grew the canvas to rescue
  an outside legend, the spatial maps widened themselves for their key beforehand, and a
  renderer's own legibility floor outranked a measurement it did not recognise, so
  `network_graph` returned 132 mm whatever was picked and `confusion_matrix` returned 79 mm when
  asked for 57 mm. Where the content genuinely cannot fit, the plot area gives up the room and the
  render says so — it never silently returns a different size.

### Added — statistics

- **Error-bar statistics with explicit choices:** standard error, standard deviation, 95%
  confidence interval (normal and t-based), and interquartile range. A whisker that does not
  describe its bar — an IQR around a mean, say — is corrected, and the correction is reported
  rather than drawn as though it were intended.
- Group-comparison renderers for summary-plus-observations figures, with controls for jitter
  arrangement and width, marker shape, size, fill, edge and transparency.

### Added — experimental publication presets (opt-in, off by default)

A bundled, read-only library of style presets whose values were measured in a corpus of published
open-access figures and cross-checked against publishers' stated artwork requirements. They appear
under an **Experimental** heading, **off by default**, and always through a preview-before-apply
flow that lists every setting a preset will change.

A preset here is **style only** — typography, line and marker weights, palette, legend and axis
geometry, and a target width. The loader refuses a preset file that tries to change data, column
roles, statistics, P values, transformations, normalisation, feature selection or thresholds.

These are **not journal templates.** No preset claims compliance with, approval by, endorsement by
or acceptance at any journal, and none reproduces any published figure; they encode aggregate
visual conventions under neutral names. See *Known limitations*.

### Added — controls

- **Cluster bars on the clustered heatmap get the same class of controls the colourbar has:**
  thickness, padding, side, label size, palette and legend placement.
- **Separators between cluster groups,** with their own colour, width and style.
- **Row and column labels can go on either side,** independently of the cluster bars.
- **The Figure Builder works at a normal window size.** Its panel list scrolls, its action bar is
  pinned, and panels reorder by dragging or with Alt+↑/↓. Its minimum height went from 902 px —
  taller than many laptop screens, so the window had to be maximised to reach the controls — to
  136 px.

### Fixed

- **Every legend fits inside its canvas.** Eleven of the 45 plot types clipped an outside legend in
  their default output. The legend is placed relative to the axes, so a long entry hung off the
  edge; exporting with a tight bounding box hid it, which is why it survived — the saved file
  looked right and the preview and any fixed-size export did not.
- **No plot type draws outside a pinned canvas.** At a pinned 4 × 2 in panel size, content — most
  often the axis label — fell off the edge on several plot types. The list of known offenders is
  empty, and the pinned-size test now runs on every plot type instead of skipping the exceptions.
- **Every render is reproducible.** Three plot types (volcano, network graph, lollipop) drew a
  different figure on each run from identical input: the label-overlap solver was given a
  one-second wall-clock budget by default and iterated until the timer expired, so the result
  depended on machine speed and load. No seed fixes that; it now gets a fixed iteration budget,
  which is both reproducible and faster than the second it used to spend.
- **Picked point labels no longer pile up.** Selecting several nearby points annotated each at a
  fixed offset, so close points always collided. They repel each other, are re-separated after the
  layout pass moves the axes, and step down in size when a narrow column leaves no room — fourteen
  labels separate cleanly at 180 mm, 110 mm and 57 mm.
- **Dead controls.** Every control on every plot type was exercised by measuring rendered output,
  and the ones that changed nothing were fixed. Among them: cluster-bar padding was dead whenever
  both bars were shown (two layout dividers overwrote each other), colourbar padding was computed
  against the figure width instead of the axes width and came out about 40% short, and three
  renderers silently dropped a new option because of a duplicate dictionary key.
- **The error statistic no longer travels inside a style**, so choosing a style cannot change which
  error statistic a figure reports.
- **Renderers draw the same figure on every supported pandas version.** Every `sort_values` in the
  renderers now uses a stable sort, so rows that tie keep their table order instead of an order
  that differed between pandas 2 and pandas 3. Values, counts and statistics are unchanged.
- **Library compatibility:** box/violin orientation on matplotlib < 3.10; pandas 3 read-only views
  and default `str` dtype.
- **The Linux app runs on Ubuntu 22.04 again,** and **starts on a desktop that does not already
  have Qt's X11 libraries** — the v1.1.1 AppImage and tarball bundled Qt's `xcb` plugin but not the
  nine libraries it links against, so the app exited before drawing a window. CI now exercises the
  `xcb` plugin under `xvfb`, which is the check that would have caught it.

### Validation

- Full test suite: **3956 passed, 4 skipped, 0 failed** on the release commit, locally and in CI
  on `ubuntu-22.04` — the same image the released Linux app is built on.
- The test suite now runs automatically on every pull request and every push to `main`. Before
  this release it ran only when someone remembered to run it.

## Known limitations

- **The experimental publication presets have had no user testing.** They ship opt-in and off by
  default, and `MANUAL_PRESET_ACCEPTANCE.md` is not signed off. No number measured during that work
  should be quoted until it has been regenerated on this released build.
- **Some text still ignores the figure-wide type scale.** Twenty-one places across twelve
  renderers derive a size from the style and then clamp it to a fixed floor the shared scale
  cannot reach. On a small figure this shows as mixed sizes within one panel — a 60 × 45 mm volcano
  draws its subtitle at 9 pt beside 5.8 pt body text. Eight plot types are affected. The sizes are
  legible; they are not uniform.
- **Dense category labels can still overlap, and one bundled example shows it.**
  `stacked_bar_composition` with 30 samples at a single-column width draws its
  category labels in a plot area 240 px wide on a 476 px canvas, because the
  outside key takes the other half. The labels have 7.3 px of room and need 15 px
  at 10 pt, so fitting them would mean about 4.9 pt type — below legibility. The
  figure is over-constrained rather than mislaid out: 30 samples, a 12-entry key
  and 110 mm do not coexist. Widen the figure, reduce the categories, or move the
  key inside the axes. Five other plot types have a 3–8 px overlap where the
  leftmost x tick label meets the lowest y tick label; both conditions are
  unchanged from v1.1.1, measured with the same instrument.
- **Windows and macOS validation for this release was automated, not manual.** Each platform's app
  was built and smoke-tested on its own GitHub Actions runner (`MakeMyFigure --selftest`, plus an
  `xcb` check under `xvfb` on Linux), all three from this one commit. A person did not click
  through the Windows or macOS build before publication.
- Genomic multi-track Circos (ideogram coordinates, heatmap or histogram rings) remains out of
  scope; the ring geometry leaves room for tracks.
