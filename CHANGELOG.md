# Changelog

All notable changes to Make My Figure are recorded here. This project uses a
single, evolving `Publication` style — it does not target or claim compliance
with any journal.

## Unreleased

### Fixed — Figure Builder panels line up on their plots, not their pictures

Reported from real use of v1.2.1: four unmodified example plots added as panels
A–D of a 2×2 figure, then panel C widened. Every measurement below is of that
figure, taken from the composite in inches.

- **Widening one panel no longer moves its neighbours.** A panel is a picture of
  a plot wrapped in its own y-axis label, tick numbers, legend and colourbar, and
  those are a different width in every panel — so laying the *pictures* out in a
  tidy grid left the *plots* inside them crooked. A↔C measured **0.408 in out of
  line** at C = 4.2 in, and widening C moved A's plot sideways. Panels are now
  drawn, measured, and placed by their plotting frame: one shared left edge down
  each column, one shared top edge across each row, **0.000 in** at every width.
- **A panel is the size you type.** The grid sat inside Matplotlib's default
  subplot margins, so a panel asked for 3.2 in was drawn 2.684 in — the "comes
  out around 0.85× the number here" the help text had to apologise for. A cell is
  now exactly the inches its panel asked for.
- **Panel margins are fitted to their content**, which both gives the plot the
  room its own margin was holding (panel A: 2.378 in → 2.732 in of frame inside
  the same 3.2 in panel) and stops the column's shared edge drifting when a panel
  is resized. The leftover white space is a control: **Panel padding**, in mm.
- **One type hierarchy per figure.** Scaling each panel to its own canvas put
  12 pt axis labels beside 10.2 pt ones in the same figure. The hierarchy is now
  scaled once, to the smallest panel — so making a panel smaller still pulls the
  type down, and making one bigger never restyles the figure.
- **Plot heights can be matched across a row.** Panels in a row are drawn the
  same height already; what differs is how much of that height goes below the
  axes — rotated category labels take more room than a heatmap's sample names —
  so the plots ended at different places and the bottoms could not be lined up.
  **Match plot heights across each row** re-draws the shorter panels taller so
  every frame in the row shares a top *and* a bottom edge. Off by default: it
  draws a panel at a height other than the one that was asked for.
- **Panel letters sit on one line.** They were hung off each panel's picture, and
  the pictures in a row start at different heights, so A and B were at different
  heights on the page.
- **Fonts for every feature, defaulting to what you pushed in.** The override had
  five boxes for seven sizes — the panel title, the statistics and the legend
  heading could not be reached at all. All seven are now there, and the boxes open
  filled with the sizes the panels are *actually drawn with*, so switching the
  override on changes nothing until a number is moved.

### Fixed — text that no longer covers the plot it belongs to

- **An axis label is not cropped.** "measurement (mean ± SEM)" came back as
  "measurement (mean ± SE". Matplotlib deliberately leaves the along-axis extent
  of an axis label out of every tight bounding box it computes, so no layout pass
  could see it; this one looks at the label directly, and wraps or shrinks it.
- **Regression statistics annotate the plot instead of replacing it.** Six lines
  of statistics for a two-group fit measured 209 px against a 210 px axes, which
  passed the old "narrower than the axes" test while covering the scatter it
  described. The box now takes at most 65% of the axes width and 28% of its area.
- **An outside legend that costs more than a third of the figure goes inside** —
  but only where the plot has a corner to spare. A volcano that labels its own
  points keeps the width it paid for, because those labels are still being
  repelled apart when the legend is placed.
- **A count line wraps onto balanced lines.** The volcano's "Up 16 · Down 8 · NS
  476 (P < 0.05, |log₂FC| ≥ 1)" went onto three lines with "1)" alone on the last
  one: the wrap width was guessed from the character count, which is half as wide
  as the measured overflow called for, and an 8.5 pt floor kept the line larger
  than the axis labels on any panel-sized canvas.
- **A heatmap too small for its row labels shows fewer of them, legibly, and says
  so.** Thirty gene names in a panel 2.2 in tall have about 4 pt of row each;
  shrinking stops at the publication minimum, and past it the labels were printed
  on top of each other. Now 1 in every *n* is shown, with a warning naming *n*.

## [1.2.1] — Corrective release: Figure Builder, style state, palettes, spatial ROI, PCA grouping, margins

A patch release fixing regressions reported from real use of v1.2.0. No new
scientific capability; every item below is a defect corrected.

### Fixed — Figure Builder no longer restyles a finished plot

- **A panel keeps the typography it was finalized with.** The builder's font
  boxes always held a value, so the documented "keep each panel's own size"
  setting was unreachable and every panel was restyled on insertion whether or
  not it was asked for. Measured at identical physical size, the title grew 50%,
  the axis labels shrank 37.5% and the statistics grew 50%, inverting the type
  hierarchy by 2.4× — which is why text collided and the plot had to be formatted
  again. The override is now a checkbox, **off by default**, and when it is used
  it replaces the whole hierarchy rather than four of nine tokens.
- **Statistics text is sized by its own control.** "Annotation font pt" did
  nothing for the corner statistics panel: 6 pt and 20 pt both drew 7.83 pt. The
  bracket engine honoured the setting; the corner panel did not.
- **Statistics text is no longer cut off.** `p < 0.` was not a formatting fault —
  the formatter is correct — it was a correctly formatted string running past the
  edge of the canvas, with as little as 26% of it visible on a three-up panel.
  The panel is now fitted to the figure.
- **A p value that is not zero can no longer print as zero.** At one decimal
  digit, `p = 0.049` was reported as `p = 0.0`; it now reads `p < 0.1`.

### Fixed — a new plot starts clean

- Styling from the previous figure carried into the next one: title, axis labels,
  fonts, palette, margins, figure size, picked labels and statistics settings —
  21 settings in all — so a box plot of different data arrived titled with the
  previous figure's title in its fonts. There was no plot-state object at all;
  every setting lived in long-lived widgets that nothing ever cleared.
- **Opening a PlotSpec or a Figure Package now restores that spec and nothing
  else.** Loading was additive and cleared nothing, so a spec carrying only
  margins came back with the previous figure's palette, font and resolution.
- **File ▸ New plot** added; the action did not exist.

### Fixed — colour

- **The palette chooser offered the same palette twice.** `publication` and
  `colorblind_safe` differed at exactly one of their eight entries, so any figure
  with six categories or fewer was pixel-identical between them — 40 of the 45
  plot types. The first colour across the four palettes was blue, blue, black,
  black. `colorblind_safe` is now a distinct colourblind-safe scheme; old specs
  naming `nature_like` still resolve to the previous palette.
- **Three groups draw three colours** on the beeswarm and dot/strip plots. They
  rejected a colour column that named the x column — asking to colour by the
  grouping variable, the obvious action — and then fell back to a single colour
  for every group.
- **Spatial ROI regions are visible.** With no ROI category mapped, every outline
  fell back to the text colour and the fill defaulted to transparent, so an ROI
  table drew as a near-black wireframe. Outline colour, fill opacity and outline
  width are now adjustable; they existed in the renderer but could not be set
  from either frontend. The one control that was shown there did nothing and has
  been removed.
- **Colour pickers for plots that use a single colour**, in the style the volcano
  already used for its significance classes: calibration (curve, points, outline),
  Bland-Altman (points, mean-difference line, confidence band), Q-Q (points,
  outline), forest (estimate marker, confidence interval) and dendrogram
  (branches). Plots that cannot use a categorical palette now say so with a
  reason instead of offering a control that does almost nothing.

### Fixed — Matrix Workflow PCA

- **A PCA started from the Matrix Workflow uses the sample groups you confirmed**,
  with a legend, by default. Which of two PCA entries you picked decided whether
  grouping applied, and the obvious one ignored it — and shipped no metadata, so
  the grouping could not be restored by hand either.
- **Supplying metadata no longer changes the analysis.** Samples were restricted
  to those listed in the metadata *before* the decomposition, so an incomplete
  metadata table silently removed samples and moved every score — dropping one
  sample of six moved PC1 by about 20%, and four missing raised an error about
  too few columns. Unlisted samples are kept, drawn as `Unassigned`, and counted.
  Duplicate sample identifiers no longer raise an unhandled error.

### Fixed — figure margins

- **One change to a margin now does one visible thing.** The controls offered
  blank space while the layout engine expected edge positions, so nudging the
  right or top margin produced a value the engine rejected: five clicks did
  nothing and the sixth collapsed the plot. A saved figure also no longer changes
  when it is reopened, which that mismatch caused.
- **The title and axis-label boxes and the style-profile menu now redraw.** They
  were connected to nothing, so typing a title drew no figure until some other
  control happened to trigger one.

### Validation

- 22 permanent regression tests, one per defect, each failing on v1.2.0.
- Full suite: 3979 passed, 3 skipped (v1.2.0: 3957 passed, 3 skipped).

## [1.2.0] — Spatial analysis, one typography system, and a width that is final

### Added — plot types (39 → 45)

Six spatial renderers, built on a shared spatial core (neighbour graphs, local composition,
cellular-neighbourhood clustering and enrichment). The registry count is read from the live
registry, not maintained by hand.

- **`spatial_categorical_map`** — categorical cell or region map, with a scale bar per facet.
- **`spatial_composition_map`** — local neighbourhood composition.
- **`spatial_feature_map`** — a continuous feature on tissue coordinates, with a colour scale that
  states its own limits rather than implying precision it does not have.
- **`spatial_roi_map`** — region-of-interest map.
- **`spatial_transcript_map`** — transcript or gene positions.
- **`neighborhood_enrichment_matrix`** — cell-type neighbourhood enrichment.

Example data for all six is built from published colorectal-carcinoma tissue and bundled, so every
one opens from the Examples menu with no download. Spatial plots round-trip through a Figure
Package, including the background image.

### Added — figure size and typography

- **One typography system, shared by every renderer.** Title, axis label, tick, legend and
  annotation sizes come from one scale with fixed ratios, and that scale adapts to the canvas
  instead of each renderer inventing its own floor. A figure shrunk or enlarged keeps its
  hierarchy; nothing is scaled past legibility.
- **One font setting produces one size on the page, in every panel.** In a multi-panel figure each
  panel was scaled independently — four panels of one figure came out at 69%, 71%, 98% and 66% of
  the requested size. Composite figures now opt out of per-panel scaling and are laid out once at
  their drawn size.
- **Figure size is a real control on every plot type.** Explicit width and height in millimetres or
  inches, in their own section, with working margins. A dimension too small to lay out is refused
  with an explanation rather than producing an unusable figure.
- **A requested width is final.** Asking for a single column, a double column or a measurement such
  as `174mm` now produces exactly that width on all 45 plot types (225 of 225 plot-type × width
  combinations exact). Three separate layers used to overrule it: the layout pass grew the canvas
  to rescue an outside legend, the spatial maps widened themselves for their key beforehand, and a
  renderer's own legibility floor outranked a measurement it did not recognise — `network_graph`
  returned 132 mm whatever was picked, and `confusion_matrix` returned 79 mm when asked for 57 mm.
  Where the content genuinely cannot fit the requested width, the plot area gives up the room and
  the render says so; it never silently returns a different size.

### Added — statistics

- **Error-bar statistics with explicit choices:** standard error, standard deviation, 95%
  confidence interval (normal and t-based) and interquartile range. A whisker that does not
  describe its bar — an IQR around a mean, say — is corrected and the correction is reported rather
  than drawn as though it were intended.
- Group-comparison renderers for summary-plus-observations figures.

### Added — experimental publication presets (opt-in, off by default)

A bundled, read-only library of style presets whose values were measured in a corpus of published
open-access figures and cross-checked against publishers' stated artwork requirements. They are
shown under an "Experimental" heading, **off by default**, and always through a
preview-before-apply flow that lists every setting a preset will change.

A preset here is **style only** — typography, line and marker weights, palette, legend and axis
geometry, and a target width. The loader refuses a preset file that tries to change data, column
roles, statistics, P values, transformations, normalisation, feature selection or thresholds.

These are **not** journal templates. No preset claims compliance with, approval by, endorsement by
or acceptance at any journal, and none reproduces any published figure — they encode aggregate
visual conventions under neutral names. See *Known limitations* below.

### Added — controls

- **Cluster bars get the same class of controls the colourbar has** on the clustered heatmap:
  thickness, padding, side, label size, palette and legend placement.
- **Separators between cluster groups**, with their own colour, width and style.
- **Row and column labels can be placed on either side**, independently of the cluster bars.
- **The Figure Builder is usable at a normal window size.** Its panel list scrolls, its action bar
  is pinned, and panels can be reordered by dragging or with Alt+↑/↓. Its minimum height went from
  902 px — taller than many laptop screens, so the window had to be maximised to reach the controls
  — to 136 px.

### Changed

- Linux AppImages are built with `appimagetool` from `AppImage/appimagetool`, which embeds the
  current `type2-runtime`, instead of the retired AppImageKit build whose older runtime required
  the host's `libfuse2`.
- **Desktop Help → Plot types** now lists the required/optional columns, description, example file
  and replacement note for every registered plot type. It read only the legacy 18-dataset manifest,
  so the 21 plot types added since v0.3 showed "Required columns: —" and "Example file: None"; it now
  reads `examples/example_data_manifest.json` with the legacy manifest as fallback. Regression test
  `tests/test_help_content.py`.
- The desktop plot-type dropdown scrolls, so every registered type is reachable.

### Fixed

- **Every legend now fits inside its canvas.** Eleven of the 45 plot types clipped an outside
  legend in their default output. The legend is placed relative to the axes, so a long entry hung
  off the edge; exporting with a tight bounding box hid it, which is why it survived — the saved
  file looked right and the on-screen preview and any fixed-size export did not.
- **No plot type draws outside a pinned canvas.** At a pinned 4 × 2 in panel size, content — most
  often the axis label — fell off the edge on several plot types. The list of known offenders is now
  empty and the pinned-size test runs on every plot type instead of skipping the exceptions.
- **Every render is reproducible.** Three plot types (volcano, network graph, lollipop) drew a
  different figure on each run from identical input. The label-overlap solver was given a
  one-second wall-clock budget by default and iterated until the timer expired, so the result
  depended on machine speed and load. No seed fixes that; it now gets a fixed iteration budget,
  which is both reproducible and faster than the second it used to spend.
- **Picked point labels no longer pile up.** Selecting several nearby points annotated each one at a
  fixed offset, so close points always collided. They now repel each other, are re-separated after
  the layout pass moves the axes, and step down in size when a narrow column leaves no room —
  fourteen labels separate cleanly at 180 mm, 110 mm and 57 mm.
- **Dead controls.** Every control on every plot type was exercised by measuring the rendered
  output, and the ones that changed nothing were fixed. Among them: cluster-bar padding was dead
  whenever both bars were shown (two layout dividers overwrote each other), colourbar padding was
  computed against the figure width instead of the axes width and came out ~40% short, and three
  renderers silently dropped a new option because of a duplicate dictionary key.
- **The error statistic no longer travels inside a style.** Choosing a style could change which
  error statistic a figure reported.
- **Renderers draw the same figure on every supported pandas version.** Every `sort_values` in the
  plot renderers now uses a stable sort, so rows that tie on the sort key keep their table order
  instead of an arbitrary order that differed between pandas 2 (`object` columns) and pandas 3
  (default `str` columns). Found by the whole-library render fingerprint: stacked composition bars
  ordered by a grouping column were drawn as S01, S14, S13, … on pandas 2 and S01, S02, S03, … on
  pandas 3 for the same data. Also affects tie-breaking in the oncoprint gene order, lollipop draw
  order and top-n labels, volcano / MA label ranking, enrichment and network top-n selection, and
  the waterfall, calibration, precision-recall, Manhattan and spider sorts; values, counts and
  statistics are unchanged. Regression tests: `tests/test_renderer_sort_stability.py`.
- **Library-version compatibility:** box/violin orientation on matplotlib < 3.10, and pandas 3
  read-only views and default `str` dtype.
- **The Linux app runs on Ubuntu 22.04 again.** The bundled CPython links against the build
  machine's glibc, and glibc is forward- but not backward-compatible, so the builder sets the
  oldest system the app can run on. GitHub's `ubuntu-latest` label moved from 22.04 to 24.04,
  which raised the floor from glibc 2.35 to 2.38 with no code change and made the rebuilt v1.1.1
  Linux assets fail to start on 22.04 (supported to 2027) with
  `libpython3.11.so.1.0: version 'GLIBC_2.38' not found`. The Linux build is pinned to
  `ubuntu-22.04`, and the build log reports the bundled CPython's glibc requirement so a future
  runner-image migration is visible instead of silent.
- **The Linux app starts on a desktop that does not already have Qt's X11 libraries.** The v1.1.1
  AppImage and Linux tarball bundled Qt's `xcb` platform plugin but not the nine libraries it
  links against. On a machine without them the app exited before drawing a window with "Could not
  load the Qt platform plugin xcb … even though it was found." `scripts/build_linux.sh` now copies
  the plugin's libraries into the bundle — before the tarball is packed, so both artifacts get them
  — sets `LD_LIBRARY_PATH` in `AppRun`, and **fails the build** if any is still absent. The GL
  stack, core X11/XCB and glibc are still taken from the host, as AppImage convention requires.
  Reported by the AppImage catalog test (AppImage/appimage.github.io#6693).

### Validation

- **CNTools (cellular neighbourhoods):** exact numerical reproduction of Fig 3A (CRC, CC*), plus an
  independent hand-check that imports no project code.
- **Janesick 2023:** Xenium Fig 3l reproduced; Visium Fig 2c normalisation recovered.
- Performance benchmarks for the spatial workflow.
- Karate-network QC figures recorded now that the output is stable.

### Documentation

- Spatial v2 audit findings, with the published methods transcribed and the scope stated.
- The plot capability matrix is generated from the live registry rather than maintained by hand.

### Packaging

- **The test suite runs in CI.** It had no automation at all: it ran only when someone remembered
  to run it locally, so nothing would have caught a regression before a release.
  `.github/workflows/tests.yml` runs the full suite headless (`QT_QPA_PLATFORM=offscreen`,
  `MPLBACKEND=Agg`) on every pull request and on pushes to `main`, on `ubuntu-22.04` — the same
  image the released Linux app is built on.
- **CI exercises the `xcb` plugin.** The build smoke test ran only with
  `QT_QPA_PLATFORM=offscreen`, which loads `libqoffscreen.so` and never touches `libqxcb.so`, so a
  build that could not start on any real Linux desktop passed cleanly. A second smoke test now runs
  under `xvfb` with `QT_QPA_PLATFORM=xcb`.
- **`scikit-learn` is declared.** The publication-recreation benchmarks load the
  iris/wine/diabetes built-ins from scikit-learn, but it appeared in no requirements file, so a
  clean environment built from `requirements-lock.txt` failed `test_curation_is_deterministic` with
  `ModuleNotFoundError: No module named 'sklearn'`. It is now a `benchmarks` extra, pinned in the
  lock file, and the test skips cleanly when it is genuinely absent rather than erroring.

### Known limitations

- **The experimental publication presets have had no user testing.** They are merged and shipped,
  opt-in and off by default, but `MANUAL_PRESET_ACCEPTANCE.md` is not signed off. Treat them as
  what their heading says. No number measured during that work should be quoted until it has been
  regenerated on this released build.
- **Some text still ignores the figure-wide type scale.** Twenty-one places across twelve renderers
  derive a size from the style and then clamp it to a fixed floor, which the shared scale cannot
  reach. On a small figure this shows as mixed sizes within one panel — a 60 × 45 mm volcano draws
  its subtitle at 9 pt beside 5.8 pt body text. Eight plot types are affected. The sizes are
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
- **Interactive Windows and macOS validation for this release was automated, not manual.** Each
  platform's app was built and smoke-tested on its own runner (`--selftest`, plus an `xcb` check
  under `xvfb` on Linux). A human did not click through the Windows or macOS build before
  publication.

## [1.1.1] — Reproducible figure packages, Circos chord diagram, compatibility fixes

Prepared on `main` on 2026-09-20. The `v1.1.1` tag, installers and GitHub release follow after the author's final check.

### Added — plot types

- **Circos-style chord diagram** (`chord_diagram`, `make_my_figure_core/plots/chord_diagram.py`):
  flows between categories that share one set, from an edge list with one row per link
  (`source`, `target`, optional numeric `value`, optional `group`). Segments are sized by total
  flow, ribbons by link value; options with explicit scopes for segment order, gap, start angle,
  ribbon colouring (source / target / group), transparency, labels (radial / tangential), total
  tick marks and the group legend (style), and for the minimum link value, directed reading
  (ribbons narrow toward the target) and self-links (config). No statistics: a chord diagram
  summarises flows. Bundled synthetic example (six cell types, compartment group), catalogue
  entry and figure, focused tests (`tests/test_chord_diagram.py`), and a low-confidence
  recommendation (0.55) alongside the network graph for `source`/`target` edge lists. Genomic
  multi-track Circos (ideogram coordinates, heatmap or histogram rings) is out of scope for
  this version; the ring geometry leaves room for tracks.

### Added — reproducible figure packages
- **Reproducible figure packages (`.mmfpackage`)** — one portable file that reopens a figure on
  another computer without the original data files: the PlotSpec (or FigureSpec + every panel's
  PlotSpec/StatsSpec), a frozen lossless copy of the exact table(s) the plot used (`mmftable`
  JSON: doubles bit-exact incl. NaN/±Inf/−0.0, missing values, strings, categories, dates), the
  original CSV/TSV/XLSX when available, the StatsSpec with results, the MatrixSpec /
  SampleMetadataSpec / PreprocessingSpec with both the original and the derived matrix, imported
  panel images, PNG/SVG/PDF previews, the software environment, and `manifest.json` (format
  version 1, JSON Schema `schemas/figure_package_manifest.schema.json`) with a SHA-256 for every
  file. Core: `make_my_figure_core.package` (writer, reader, assembly helpers, security scan).
- **Desktop:** *Open Figure Package* on the landing page and File menu (Ctrl+Shift+P), *Save
  Reproducible Figure Package…* (Ctrl+Shift+S) and *Save Figure Package (.mmfpackage)* in the
  Export group with a privacy notice ("Figure packages include the data required to reproduce the
  figure"), content list and size estimate; packages open from drag-and-drop and *Recent files*
  (📦); composite packages reopen in the Figure Builder with their layout and frozen panel data;
  Figure Builder *Save Figure Package…*; Help tab *Files & reproducibility*.
- **Browser:** *Data source → Open Figure Package* and a *Figure Package* download.
- On opening a package the statistics are recomputed from the frozen data and compared with the
  stored StatsSpec, and a recorded preprocessing chain is replayed on the frozen source and
  compared with the frozen derived matrix; differences are reported, frozen values are never
  replaced.
- Exported PlotSpecs carry `source.source_table_sha256`, a content digest of the plotted table;
  *Open PlotSpec* warns when the data it finds differ from the recorded table.
- `PreprocessingStep.user_parameters` records the requested parameters so a chain can be replayed
  exactly (older records are replayed by signature filtering).

### Changed
- **Export all as ZIP** now contains the publication files, `name.plot_spec.json`,
  `name.stats_spec.json` (when statistics ran), **`name.mmfpackage`** and a README.
- Desktop wording makes the three artifacts unmistakable: *Export PlotSpec JSON (specification
  only)*, *Open PlotSpec… (specification only; needs the data file)*, Figure preset (no data),
  Figure package (frozen data + specifications).
- *Open PlotSpec* accepts the `{"plot_spec": …, "render_metadata": …}` sidecar written by *Export
  PlotSpec JSON* (previously only the bare spec from *Save PlotSpec* reopened).

### Security
- Packages are untrusted input: member names are checked (no `..`, absolute paths, drive letters,
  backslashes, control characters), symbolic links and device entries are rejected, entry count,
  entry size, total size and compression ratio are capped, unlisted or altered files fail the
  integrity check, nothing is unpickled or executed.

### Documentation
- `docs/FIGURE_PACKAGES.md`; Quick Start and User Manual (Parts I §6, XV §61–63a, XVI §68, XVII
  §70, XXIII, XXIV, glossary) describe PlotSpec vs Figure preset vs Figure package and the
  eight-step "Sharing a reproducible figure" workflow; `reports/portable_package_current_state.md`
  (live-code audit of v1.1.0), `reports/v1.1.1_manuscript_claim_audit.md`,
  `reports/v1.1.1_manual_acceptance_test.md`.

### Fixed — library compatibility
- Figure-package tables written with pandas 3 (default `str` dtype) reopen with their dtype
  intact; on pandas 2 they reopen as `object`, which is what that pandas infers itself
  (`make_my_figure_core/package/tabledata.py`, test in `tests/test_figure_package_integrity.py`).
- The figure-preset QC script no longer writes into read-only pandas 3 array views.

### Packaging
- Packaging: the MIT `LICENSE`, `README.md` and `CHANGELOG.md` are bundled at the top level of the
  desktop builds (Windows zip and installer, macOS app, Linux tar.gz/AppImage); the installer shows
  the licence; `pyproject.toml` declares the licence and classifiers.
- Dependencies: bounded ranges (next major excluded) in `pyproject.toml` and `requirements.txt`, and
  a new `requirements-lock.txt` with the exact versions the release was tested with.

## [1.1.0] — Figure presets, validated statistics, export and packaging fixes

### Added
- **Figure presets for every plot type** (`presets.py`; desktop *Figure preset* panel and
  browser expander: Apply, Save preset…, Import, Export, Delete, Reset). A preset is the
  reusable part of a PlotSpec — **style** mode (typography, palette, geometry, legend and
  colorbar placement, export size, visual plot options) or **full** mode (adds column roles,
  thresholds, labels, statistics test). It never contains the table, its name, values or
  worksheet provenance; roles a new table cannot satisfy are reported, never substituted.
  Every option now declares a scope (`Option.scope`), and a registry-wide QC matrix
  (`reports/figure_preset_qc/`) pins save → apply → export → round-trip for all 38 types.
  Figure Builder **Layout presets** (`.mmflayout.json`) carry grid, panel sizes, gutters and
  label style without panel content.
- **Histogram plot type** (`histogram_distribution`): long or wide input (declared, not
  guessed), one panel per group or overlaid, bars and/or frequency polygon, counts /
  frequency / percent / density, cumulative option, mean/median markers, axis-range and tick
  controls. Complements the ridge/density plot, which smooths.
- **Survival curves:** explicit `precomputed` input form for already-computed S(t) columns
  (multi-column role), validated 0/1 event indicator with a two-level recoding message,
  `y_scale` fraction/percent, reference line, group labels, curve style; a log-rank test is
  refused on a precomputed curve with an explanation.
- **Axis-range and tick overrides** (`x_min`, `x_max`, `y_ticks`, `ends_and_midpoint`) for
  survival, histogram and forest plots. A range that would hide plotted data is refused
  rather than clipped silently. Layout `x_scale` / `y_scale` (`linear` | `log` | `symlog`)
  for line plots; a log axis is skipped for non-positive data.
- **Line / time-course bands:** `iqr` and `range` (median-centred) in addition to SEM / SD /
  CI95; `style_by` mapping varies line style and marker by a second category while colour
  follows the first.
- **Oncoprint:** `order` (frequency | input) and `show_sample_labels` options.
- **Box/violin:** `point_size`; **volcano:** `show_legend`; **MA plot:** optional
  `lfc_cutoff` so significance can follow a published definition; **heatmap:** an explicit
  layout `aspect` overrides the row-count height heuristic; `title_font_weight` style token
  honoured by every renderer that draws a title.
- **Multi-column roles** (`value_columns`, `survival_columns`) render as multi-select lists in
  both frontends; optional numeric options can be left blank ("(auto)") in the desktop app.
- **Independent R validation benchmark** (`benchmarks/r_validation/`): every statistical test,
  correction, normalisation/transform, QC metric, PCA, clustering and differential screen
  compared with independent R implementations (base R, survival, car, rstatix, effectsize,
  MASS, dunn.test, limma, edgeR, DESeq2) on 26 seeded synthetic datasets, the bundled examples
  and a public RSEM count matrix; 2,625 comparisons, no failures; classes EXACT /
  NUMERICALLY_EQUIVALENT / ACCEPTABLE_IMPLEMENTATION_DIFFERENCE / UPSTREAM_INPUT_DIFFERENCE /
  METHOD_MISMATCH kept apart; the feature-level screen is compared with limma-voom, edgeR and
  DESeq2 as concordance only. Regression tests in `tests/test_r_validation_regressions.py`.
- **User Manual and Quick Start** (`docs/manuals/`, generated Markdown, DOCX and PDF with
  screenshots from bundled example data) and a plot catalogue generated from the registry.

### Changed
- The browser app reads column roles and options from the shared `ui_hints` registry (its
  own copy had drifted: 19 plot types had no mapping controls).
- Tick density follows the style's tick font even when a figure is drawn outside the style
  context (Figure Builder rasterisation); rotated multi-line category labels are joined on
  one line.
- Exports use a tight bounding box that includes axis labels and titles, so a long axis label
  is no longer clipped.
- Streamlit single-plot exports keep text as text (editable SVG/PDF).

### Fixed
- **Six numerical defects found by the R validation:** r × c Fisher's exact test used an
  unseeded Monte Carlo p-value (now seeded, 200,000 resamples, method recorded); ROC AUC and
  average precision depended on input row order for tied scores (ties collapsed to one
  operating point); quantile normalisation broke ties by sort order (now Bolstad/limma
  average-rank algorithm); `voom` used a library-size-scaled prior (now the voom definition);
  the Mann–Whitney effect size in the feature-level summary had the wrong sign; last-bit
  near-ties in rank tests are treated as ties.
- Delimited-text floats are parsed correctly rounded (`float_precision="round_trip"`), so a
  CSV and an XLSX of the same table load to the same doubles.
- The Publication font stack (Arial → Helvetica → DejaVu Sans) is written as a concrete,
  installed family list, so exports, Figure Builder letters/titles, re-placed legends and
  manual annotations keep the profile font instead of falling back to DejaVu Sans.
- Style presets transfer the palette in order to plots with new categories (regression test).
- Installed wheels ship the bundled resources (schemas, style profiles, mock data, examples)
  inside the package; `pip install` of a wheel could previously not render anything.
- Five stale tests repaired: browser smoke test picker index; AppTest session-state proxy; the
  desktop grouping-dialog test used a 3-row toy matrix whose columns are (correctly) classified
  as annotations and expected groups to be guessed without pressing *Guess groups*, so it
  blocked on a modal warning offscreen; the PlotSpec round-trip test hard-coded a plot type
  that the benchmark had since corrected.
- Desktop About dialog shows the real licence and repository instead of placeholders.

### Validation
- Full test suite on Linux (Qt offscreen where available); R benchmark re-run against the
  release candidate (see `docs/releases/v1.1.0/release_v1.1.0_audit.md`).

### Documentation
- README rewritten for v1.1.0 (native installers first; plot and statistics counts from code).
- `docs/manuals/`: Quick Start and User Manual regenerated for v1.1.0.

### Packaging
- `setup.py` + `MANIFEST.in` stage resources into the wheel; `pyproject.toml` build extra.
- Native installers (macOS DMG, Windows Setup.exe, Linux AppImage/tar.gz) are built on the
  GitHub Actions native runners when a version tag is pushed, with a `--selftest` smoke test.

## [1.0.0] — First stable release

Supersedes `1.0.0-rc1`, adding the release-candidate fixes plus first-class
multi-sheet Excel support, duplicate feature-label handling, and a unified Matrix
Workflow. One user-facing **Publication** style; reproducible PlotSpec/StatsSpec
sidecars; no R dependency and no fabricated statistics.

### Added
- **Multi-sheet Excel workbook browser** (Desktop + Streamlit): every worksheet is
  selectable (documentation/empty/hidden included), advisory sheet classification,
  worksheet-aware output names, and workbook/sheet provenance on the PlotSpec. See
  [docs/MULTI_SHEET_EXCEL.md](docs/MULTI_SHEET_EXCEL.md).
- **Duplicate feature labels for Volcano & MA**: per-point identity with all /
  unique / count label policies and deterministic representative selection, so rows
  sharing a gene symbol stay independently labelable. See
  [docs/VOLCANO_ANNOTATIONS.md](docs/VOLCANO_ANNOTATIONS.md).

### Changed
- **Unified Matrix Workflow.** The Matrix Workflow now prepares data + recommendations
  and hands off to the *same* full plot editor as the normal workflow (one canonical
  PlotSpec, full controls, annotations, export, and Figure Builder) — no second reduced
  plot UI. Matrix/metadata/preprocessing/statistics/workbook provenance travels into
  the exported PlotSpec. See [docs/MATRIX_WORKFLOW.md](docs/MATRIX_WORKFLOW.md).

## [1.0.0-rc1] — Responsive cross-platform UI and deterministic defaults

### Fixed
- **Clipped desktop controls (macOS/Windows).** The top-nav buttons were laid out
  in a fixed-width horizontal row inside a control pane hard-capped at 480px, which
  clipped the **"Matrix workflow…"** button. Buttons are now stacked vertically and
  the pane's max-width cap is removed, so full labels stay visible at any pane
  width, DPI, or OS font metric.
- **Truncated recommendation cards.** The nested scroll area in the Recommended
  Figures panel could collapse to a sliver and cut cards mid-sentence; it now has a
  minimum height so at least a full card is readable.
- **Over-wide / truncated data-preview columns.** Preview columns are now
  user-resizable, width-capped, and carry header tooltips showing the full column
  name.
- **Stale persisted splitter sizes.** Degenerate/outdated saved splitter geometry is
  validated on restore and falls back to a proportional default instead of leaving
  the control pane unusably narrow.
- **Streamlit silently defaulted to a bar plot.** On upload the app auto-selected
  the first plot type and rendered it; it now shows a **"— Choose a plot type… —"**
  placeholder and renders nothing until a real plot is chosen — matching the desktop
  app's existing behavior.

### Changed
- Placeholder text, the visible style name, and top-level workflow action labels now
  live in a shared `make_my_figure_core/ui_strings.py` so the Streamlit and desktop
  frontends stay in lockstep.

### Notes
- Cross-platform UI QC runbook added (`docs/CROSS_PLATFORM_UI_QC.md`). The visual
  fixes are covered by source-level guardrail tests; on-device verification on macOS
  (Retina) and Windows (125/150/200% scaling) is still recommended before release.

## [0.6.1] — Open PlotSpec, transform-aware recommendations, in-app differential screen

### Added
- **Open PlotSpec** (desktop File menu + Streamlit data source): reopen a saved
  `*.plot_spec.json` (+ its data) and reproduce the exact figure — restores plot
  type, mappings, style, and statistics.
- **Transform-aware recommendations**: plots reachable by reshaping the data
  (wide→long ridge/box, correlation heatmap, category-frequency bar). On Generate
  the app reshapes the data, **saves the new CSV**, and plots it.
- **Guidance recommendations** (informational): e.g. volcano/MA from a matrix
  explain that a precomputed fold-change + p-value/FDR table is required and that
  Make My Figure does not compute or fabricate those statistics.
- **In-app differential screen** (Define groups → "Differential screen"): a basic
  per-feature two-group test (Welch/Student's t or Mann–Whitney — the app's
  existing two-group tests) + Benjamini–Hochberg FDR + log2 fold-change on a
  **normalized** matrix, writing a results table (log2FC/p/FDR/AveExpr) that then
  drives volcano/MA/top-feature recommendations. It is transparently labeled as a
  basic screen — **NOT** a count-based model (DESeq2/edgeR/limma-voom) and **not**
  RNA-seq-from-raw-counts; normalize before running.
- **Heatmap `log_zscore` scale** (log then per-row z-score) + a nudge when a raw-
  count-like matrix is left unscaled.

### Fixed
- Recommendation engine now detects unnamed categorical group columns (e.g.
  `species`) so group/value tables get box/violin/ridge/bar suggestions; manually
  picking a distribution plot auto-prefills x/y/group.
- **Revert to original data**: reshaping the data (a transform recommendation,
  grouping, or the differential screen) no longer traps you on the transformed
  table. A "↩ Revert to original data" button appears and restores the pre-reshape
  data and its own recommendations (the saved reshaped CSV is kept on disk).

## [0.6.0] — Publication style, recommendations, QC, benchmarks, performance

Focus: fast, polished, intelligent, publication-ready — not more plot types.

### Added
- **Intelligent figure recommendations** (`make_my_figure_core/recommendations/`):
  profiles an uploaded table and suggests appropriate figures (from the existing
  37 plot types) with confidence, reason, detected mappings, suggested statistics,
  and a one-click PlotSpec draft. Surfaced as a **Recommended Figures** panel
  (desktop) and expander (Streamlit); expensive suggestions require confirmation.
- **Publication QC** (`make_my_figure_core/qc/`): scored pass/warn/fail readiness
  check with suggested and one-click auto-fixes. Desktop **Publication QC** button
  + Streamlit expander.
- **License-safe publication benchmark recreation** (`benchmarks/publication_recreation/`,
  branch `benchmarks/publication-recreation`): recreates real-data publication-style
  panels through the app with scientific + visual QC and full provenance.
- **Performance:** `apps/desktop_app/workers.py` (QThreadPool background layer),
  debounced rendering for continuous controls, `scripts/benchmark_performance.py`.

### Changed
- **Single `Publication` style identity.** Journal-named profiles (Nature-/Science-/
  Cell-like and their "learned" variants) are removed from the UI and docs; advanced
  appearance controls remain under Publication. Old PlotSpecs referencing removed
  profile names are migrated to `Publication` on load, with a non-intrusive notice.

### Notes
- Make My Figure does not run RNA-seq differential expression (no R/edgeR/limma/
  voom). It plots generic matrices (→ heatmap/PCA/clustering) and precomputed
  differential results tables (→ volcano/MA). Users confirm that recommended
  figures/tests match their design. The Publication style is a general
  manuscript-ready visual style, not an official journal template.

## [0.5.3] — grouped heatmaps + cleaner "Define groups"

### Fixed
- **"Define groups" listed non-sample columns.** The wide-matrix group assignment
  showed every non-id column (including RNA-seq annotation columns like
  `geneSymbol` / `bioType` / `annotationLevel`) and auto-assigned each a group.
  Now only **numeric** columns are offered as samples (text annotation columns are
  dropped), groups start **blank** (assign only your real samples; anything left
  blank — e.g. a numeric annotation column — is excluded), and "Auto-guess from
  names" is opt-in.
- **Heatmap showed nothing after grouping.** Grouping only reshaped to *long*,
  which collapses a heatmap to a single "value" column. The Define-groups dialog
  now has an output choice: **long** (bar/box/violin) or **wide** (heatmap/PCA).
  Wide keeps the matrix (assigned samples only) and adds a **group color strip**,
  so a grouped heatmap actually renders. Verified end-to-end on a real 12-sample /
  55k-gene RSEM matrix + metadata.

### Added
- `grouping.numeric_sample_columns()` and `grouping.wide_grouped_matrix()`
  (returns the wide matrix + a column-annotation group strip); controller
  `group_from_matrix_wide()` / `numeric_sample_columns()`.

## [0.5.2] — memory guards for large matrices + RNA-seq parsing

### Fixed
- **Out-of-memory on large matrices.** Hierarchical clustering builds an O(n²)
  distance matrix, so a big feature axis (e.g. a ~55k-gene RSEM count table)
  exhausted RAM and crashed the app. The clustered heatmap, standalone
  dendrogram, and hierarchical-clustering plot now **cap the feature (row) axis
  to the top-N most variable rows** (default 2,000, configurable via
  `max_features`) before clustering/display, with a clear warning. Highlighted
  rows are always kept. PCA is unaffected (it SVDs the small samples×features
  orientation — no O(n²) — and was already memory-safe).
- **RNA-seq matrices with annotation columns.** Count matrices commonly carry
  columns like `geneSymbol` / `bioType` / `annotationLevel` before the samples.
  The heatmap/dendrogram/hierarchical-clustering now drop non-numeric annotation
  columns automatically and accept an `exclude_columns` list for numeric-looking
  ones; they also report exactly which columns were used as samples. PCA now
  restricts to the columns present in the metadata's sample-id column, so
  annotation columns are no longer mistaken for samples.

### Notes
- Defaults preserve prior output for normal-sized matrices. For a readable
  publication heatmap, subsetting to top-variable genes was already best practice;
  this just makes it automatic and memory-safe instead of crashing.

## [0.5.1] — click to identify / label points

### Added
- **Click-to-identify / click-to-label** on the desktop live canvas for **volcano**
  and **scatter** plots: enable *"Click a point to identify / label it"* (Labels &
  size), then click near a point to see its gene/sample name + coordinates in the
  status bar and toggle a label on it. Added labels are stored in the PlotSpec
  (`mapping.selected_labels`) so they persist on export/reload; click again to
  remove. Picks are kept per plot type and reset on new data.
- Core (GUI-independent) helpers: `build_pickable_points`, `nearest_pickable`,
  `choose_label_column`, `resolve_point_labels`; renderers emit
  `metadata['pickable_points']` + `pick_label_column`. Scatter now honors
  `selected_labels` (label only the chosen points).

### Notes
- Interactive desktop feature — exports remain static; only the labels you add
  persist. Covers volcano + scatter (other plot types label by name). No
  drag-to-reposition. The Qt click handler is additive/guarded but should be
  smoke-tested in the desktop app.

## [0.5.0] — networks, annotations, docking & clustering

Builds on v0.4 (37 plot types total). Focus: publication-ready, refine-in-app
figures. No breaking changes — existing plots, statistics annotations, exports,
PlotSpec, desktop app, and Streamlit app are unchanged.

### Added — plot types
- **Network graph** (`network_graph`): edge-list / adjacency-matrix /
  correlation-network inputs; spring/kamada-kawai/circular/shell/spectral/
  multipartite/fixed layouts (reproducible via a stored seed); filtering
  (weight, |r|, p/FDR, top-N edges/nodes, min degree, remove isolates); node
  metrics (degree, betweenness/closeness/eigenvector centrality) and a network
  summary; exportable filtered edge + node-metric tables. NetworkX-based.
- **Hierarchical clustering** (`hierarchical_clustering`): cut the tree into `k`
  clusters, cluster color strip, exported cluster-assignment table + summary;
  scaling (row/col z-score, center, log) and distance/linkage options.

### Added — annotations
- **Universal manual annotation layer** (`spec['annotations']`,
  `make_my_figure_core/annotations.py`): text, arrow, callout, box, region,
  bracket, and reference lines in data/axes/figure coordinates, drawn as vector
  artists and applied to every plot type through the central render path.

### Changed — annotations & clustering on existing plots
- **Volcano**: labels on/off, six label modes (top-FDR / top-|log2FC| / top
  up+down / selected / pasted list / all-significant), displaced-label arrows,
  label boxes/colors/size, auto `Up/Down/FDR` subtitle, and a max-labels warning.
- **Heatmap**: scaling + distance/linkage options, `cluster_k_rows` /
  `cluster_k_columns` color strips with exported assignments, `sort_by_cluster`,
  and gene/sample highlighting via a pasted list (bold labels when others hidden).

### Added — desktop
- **Pop-out / pop-in panels** (`apps/desktop_app/panels_dock.py`): detach the
  Figure, Data & Messages, or Plot Controls panels to floating (multi-monitor)
  windows and dock them back with state preserved; View-menu actions + Dock All;
  layout persisted via `QSettings`. Additive (reparenting, not `QDockWidget`).

### Added — supporting
- Shared `make_my_figure_core/clustering.py` (scaling, metric/linkage validation,
  k-cut, assignment table, color mapping, summary).
- `networkx` and `adjustText` added as dependencies.
- Docs: `V0_5_NEW_FEATURES.md`, `NETWORK_GRAPH.md`, `ANNOTATIONS.md`,
  `VOLCANO_ANNOTATIONS.md`, `HEATMAP_HIGHLIGHTING.md`, `HIERARCHICAL_CLUSTERING.md`,
  `POP_OUT_PANELS.md`; example data for the new types (incl. edge-list /
  adjacency / correlation network files); v0.5 visual QA gallery.

## [0.4.0] — manuscript plot-type expansion

Adds **18 new plot types** (17 → 35) covering a much broader range of
publication figures, wired through the existing registry, validation, style,
publication-readiness check, and export/sidecar systems. No breaking changes:
all existing plot types, statistics annotations, exports, and app navigation are
unchanged.

### Added — new plot types
- **Group comparison & distributions:** dot / strip plot, beeswarm plot, paired
  dot plot / slopegraph, raincloud plot.
- **Relationships & trends:** dose-response curve (4PL fit + EC50/IC50), spider
  plot (longitudinal per-patient change).
- **High-dimensional / omics:** hierarchical clustering dendrogram, MA plot,
  UMAP / t-SNE embedding scatter (precomputed coordinates).
- **Genomics & variants:** Manhattan plot (genome-wide + suggestive lines),
  Q-Q plot (p-value with genomic inflation λ, or quantile mode).
- **Clinical & survival:** swimmer plot.
- **Model performance:** precision-recall curve (AUPRC), confusion matrix
  (counts / row / column / total normalization), calibration plot (Brier score).
- **Set overlap & flow:** UpSet plot, Sankey / alluvial (two-stage).
- **Method comparison / QC:** Bland-Altman plot.

### Added — supporting
- `make_my_figure_core/plots/_v04_shared.py`: shared helpers (matrix parsing,
  hierarchical linkage, jitter / quasi-beeswarm, summary overlays, flexible
  column detection, −log10(p)); numpy/scipy only — no new dependencies.
- A bundled synthetic example dataset + PlotSpec for every new plot type
  (regenerate via `scripts/generate_example_data.py`).
- `scripts/generate_v04_qa_gallery.py`: renders each new plot and a contact
  sheet to `reports/v04_qa/` for visual QA.
- `docs/V0_4_NEW_PLOT_TYPES.md`: use cases, required/optional columns, and
  documented limitations for every new type.
- `tests/test_v04_plots.py`: per-type render, export, no-mutation, validator,
  and publication-readiness tests, plus metadata-correctness checks.

### Integrity
- No fabricated statistics: AUPRC, accuracy, Brier score, IC50/EC50, and genomic
  inflation λ are computed only from valid inputs and otherwise omitted with a
  warning. Differential-expression p-values are read verbatim, never recomputed.
- Documented limitations: quasi-beeswarm (not force-directed); two-stage Sankey
  only; embedding takes precomputed coordinates (no `.h5ad`/AnnData yet);
  dendrogram computes linkage from the matrix (no precomputed-linkage input yet);
  UpSet shows the top 20 intersections.

## [0.3.0]
- Multi-panel Figure Builder: live preview, per-panel size (inches), figure-wide
  font controls, and undistorted (letterboxed) panel scaling; per-panel titles
  off by default.

## [0.2.0]
- Figure-first workflow; in-app grouping; volcano from a DE-result table with
  confirmable columns.

## [0.1.0]
- First desktop release.
