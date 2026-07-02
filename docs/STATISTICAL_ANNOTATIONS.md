# Statistical annotations on figures

Make My Figure draws publication-style statistical annotations directly on
figures. A central layout engine
(`make_my_figure_core/plots/stats_overlay.py`) handles bracket placement so
every renderer produces consistent, non-overlapping annotations.

## The core guarantee

Every p-value, star, or statistic drawn on a figure is derived from a stored
`StatResult` (see [STATISTICS.md](STATISTICS.md)). Renderers never format a
p-value themselves and never draw a decorative, unbacked label. The chain is:

```
StatsSpec → run_statistics() → [StatResult, ...] → AnnotationItem → overlay engine → figure
```

The same results are exported in the `*.stats_spec.json` sidecar, so a label on
the figure and the reported number always agree.

## Bar / box / violin / grouped plots — significance brackets

- A bracket is drawn between each pair of compared groups.
- The bracket's baseline is placed automatically above the data (and above error
  bars for bar plots).
- Multiple brackets **auto-stack**: overlapping comparisons are assigned
  increasing levels so lines never cross labels.
- The y-axis is expanded automatically so nothing is clipped on export.
- Comparison modes:
  - **all pairs** — every pairwise comparison,
  - **compare to control** — each group vs a chosen reference,
  - **selected pairs** — only the pairs you specify,
  - **within each x category** — for grouped/dodged plots, compare subgroups
    inside each x level (e.g. VC vs OJ within each dose), with brackets placed at
    the correct dodged positions.

Labels can show stars, exact p-values, or both, and optionally the effect size.

## Scatter / regression

Correlation/regression statistics (r or ρ, p, R², slope) are placed in a
non-overlapping corner panel. With a color/group column, per-group statistics are
listed.

## Kaplan–Meier survival

The log-rank p-value is placed in a clean text box inside the axes; if a Cox
model is run, the hazard ratio and its 95% CI are shown too.

## Categorical / composition

Chi-square or Fisher's exact results (test name + p-value) are shown as a corner
panel on stacked composition plots.

## Volcano / forest

Volcano plots annotate thresholds and label significant genes using the
**supplied** p-values — no p-values are invented. Forest plots display the
provided estimates and confidence intervals.

## Formatting controls

Exposed in both apps: annotation display mode (stars / p / both), p-value
decimals, scientific-notation threshold, whether to show effect sizes, annotation
font size, and bracket line width/height/offset. Annotations respect the selected
style profile's fonts and colors and export cleanly to SVG, PDF, and PNG.

## Tips to avoid clutter

- Prefer **compare to control** or **selected pairs** over all-pairs when you
  have many groups.
- Use **stars** for dense figures and **exact p-values** for a small number of
  key comparisons.
- Turn off "show non-significant" brackets if you only want to mark significant
  differences (the results table still lists every comparison).
