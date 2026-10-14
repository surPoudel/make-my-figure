# Make My Figure v1.3.1 — release notes

This release does three things:
- fixes the macOS crash in v1.3.0;
- fixes a desktop title box that lost the keyboard while you typed;
- adds a workflow for ordinary experimental tables (ecology, entomology,
  agriculture, physiology), with recorded transformations, logarithmic axes and a
  factorial ANOVA that refuses designs it cannot estimate.

Every number in these notes is a measurement, not an estimate.

## macOS: the app no longer quits unexpectedly

v1.3.0 could quit on macOS with `EXC_BAD_ACCESS` inside a Qt callback. The cause was
the Qt binding bundled into the installers, not MakeMyFigure's own code. The release
build installs the newest PySide6 its version range allows. For v1.3.0 that was
**6.12.0** (v1.2.x had 6.11.2). PySide6 6.12.0 releases one reference too many each
time a signal reaches Python (−1.000 per call) and each time a timer fires
(−1.005), against 0.000 on 6.11.2, until Python frees an object that is still in
use.

This release pins the working binding. Every installer's built-in self-test now
measures the binding it bundles, so a defective release fails the build instead of
reaching you. A build with the fix was checked on the reporter's Mac, and the app no
longer quit.

## Desktop: typing a title no longer loses the keyboard

Each pause while typing redraws the preview. The redraw briefly turned the old
toolbar into a window of its own and then gave the new figure the keyboard, so a
half-typed title stopped accepting characters. This is fixed on all 45 plot types.

## Ordinary experimental tables

For a table with one row per observation (treatment, social setting, time, colony,
body size, a measured quantity) under any column names. Click **📋 Prepare table**.

- **Column roles.** Say which column is the response, which are factors, covariates,
  time, and the experimental unit (subject or colony). Suggestions show their reason,
  and your choice always wins. Such a table is no longer mistaken for an expression
  matrix: the 4-row bee workbook used to be offered a clustered heatmap and PCA.
- **Transformations with a preview.** log10, log2, ln, square root and z-score each
  **add a new column** beside the original, and the original table never changes. The
  offset is 0 unless you set one: no silent "+1". Zeros and negatives are counted
  before anything is applied, and refused unless you choose to record them as missing.
  A column that is already a log is not logged again.
- **Saved and exported.** *Export table with derived columns* writes the transformed
  values themselves, plus a record of how each column was made (source checksum,
  sheet, method, base, offset). A Figure Package holds the raw table, the derived
  table and that record. It reopens after the source file is deleted or edited, and
  detects any change to its data.

## Logarithmic axes, without changing the data

On bar, grouped bar, scatter, box/violin, line, dot/strip and paired plots:
- **Scales:** log10, log2 or natural-log axes.
- **Tick labels:** plain numbers (100,000 · 1,000,000), powers (10⁵, 10⁶) or
  scientific notation (×10⁶).
- **Also:** minor ticks, and an explicit axis range.

The values, the statistics and the exports stay the original numbers. Audited on all
45 plot types: 81 of 81 scale and tick-label combinations draw identical values and
round-trip byte-identically through a PlotSpec and a Figure Package. The other 38
plot types say why they have no log axis (volcano axes are already logs, spatial
coordinates must keep their geometry, and so on).

A log axis is refused, with a message, if a plotted value is 0 or negative or the
column already holds log values. A log axis also keeps significance stars inside
the plot and keeps the regression-statistics box off the data.

## Factorial ANOVA that knows when it cannot answer

- **The design is checked first.** Up to three factors, with optional covariates. If
  factors are confounded, combinations are empty, a factor is nested in another,
  nothing is left to estimate the error, the response is constant, or one colony
  contributes several rows, the app explains why in plain words and computes nothing.
  On the 4-row bee workbook, a three-way ANOVA reports all four of its reasons.
- **What it reports when the design is estimable:**
  - Type II (default) or Type III (sum-to-zero contrasts) sums of squares;
  - partial η² for each term;
  - a **coefficient table** (estimate, SE, t, P and 95 % CI, with readable names).
- **Checked against R.** Base R 4.5.3 on simulated designs: **509 of 509** numbers
  agree, with the largest relative difference **6.5 × 10⁻¹³**.

**Corrected:** the existing two-way ANOVA reported its effect size as SS/SS_total
under the name "partial η²" (0.549 where the partial η² is 0.756). It now reports
partial η², and refuses designs it cannot estimate.

## Also

- **Browser app:** the same transformations, design check, coefficient table and
  axis controls.
- **New guides:** `docs/GENERAL_TABULAR_DATA.md`, `docs/AXIS_SCALING.md` and
  `docs/STATISTICS_FACTORIAL.md`.
- **New tutorial:** `tutorial/general_tabular_data/`, with screenshots and a
  simulated replicated dataset.

**Not included:** mixed-effects models, post-hoc tests after a factorial model, and
more than three factors. The app says so instead of guessing.

Tests: 4518 passed, 13 skipped, 0 failed (full serial suite).
