# Facet grids — QC record

Branch `feat/faceted-plots`. Request: the plant-growth design (2 species × 2 ages ×
3 nitrogen levels × 4 months, n = 5 per cell, 240 rows; `new_task_ravi/`) drawn as a
faceted box plot and a faceted mean ± SE line plot, as ggplot's
`facet_grid(Age ~ Species)`, with every existing control carried over.

Implementation: `facet_row` / `facet_col` column roles on `boxplot_or_violin_with_points`
and `lineplot_timecourse_with_error_band`, one shared grid module
(`make_my_figure_core/plots/facets.py`); not two new plot types, so the 45 plot types
and their options, statistics, presets, packages and Builder behaviour apply unchanged.

## Method

Two independent visual reviewers rendered the grids through the real pipeline
(`DesktopController.render` + `figure_to_bytes`), looked at every image, and measured
geometry in points; a third agent swept every visible control. Each defect was
reproduced with a script before fixing and re-measured after
(`recheck_round1.py`, `recheck_round2.py`, `contact_sheet.py`). Default renders of all
45 plot types (+3 variants) were digested before any change and compared after every
change (`default_render_digests.py`): **48 of 48 unchanged** at every step.

## Defects found and fixed (all measured)

| # | Defect | Before | After |
|---|---|---|---|
| 1 | inside legend hidden behind the panels (host z-order −10) | invisible | visible; anchored to the panel area, 0 overlap with strips |
| 2 | horizontal grid + free scales shared the wrong axis | 19 / 240 points outside limits | 0 |
| 3 | free scales had tick labels on the left column only | unreadable | labels on every panel |
| 4 | outside-left legend over the shared y label | −12 pt | +9.9 pt gap |
| 5 | outside-bottom legend over the x label (default / big fonts / 80-char title) | −4.6 / −15.7 / −50 pt | +10.2 / +11.8 / +10.2 pt |
| 6 | strip text overflowing the strip | 37.6 pt (120 mm), 207–223 pt (long names) | 0 px; wrapped, then shrunk to ≥ 70 %, then "…" |
| 7 | squashed panels not reported | silent | note quotes the measured panel size (0.95 in at 120 mm; 0.77 in at 8 columns) |
| 8 | automatic width unbounded | 26.9 in at 8 columns | capped at 10.0 in |
| 9 | colour override by name missed the SE band / error bars / legend swatch | palette colour | all #d62728 (plain and faceted) |
| 10 | default grid always "widened to fit"; tight_layout UserWarning | 1 warning + stderr | none |
| 11 | line grid: facet variable = x not warned | silent | warned |
| 12 | hue = facet variable: box off its tick | centres 1, 3 for ticks 1, 2 | centred |
| 13 | line x ticks 4 … 10 for sampled 4/6/8/10 | 5, 7, 9 shown | 4, 6, 8, 10 |
| 14 | bracket stacks compounding on the shared axis | y top 115 | 107 (= the tallest panel's own need) |
| 15 | long title at 18 pt squeezed the panels | 1.0 in panels | 3.0 in |
| 16 | one-row grid + bottom legend below the canvas | 17–22 pt outside | 0 |
| 17 | publication check "axes are missing x/y labels" on every grid | false warning | reads the shared labels |
| 18 | grid title clipped in the desktop preview | 0.007 in margin | 0.10 in |
| 19 | mid-word strip wrapping ("A / rabidopsi…") | | whole words at a smaller size first |
| 20 | `y_max` on a shared axis checked against the first panel only | points above 40 cut off panels 2 and 4, silently | refused, quoting the range of every panel |

## Controls sweep

A third agent set every visible control to a non-default value on the faceted box
and line plots - 195 controls (`controls_sweep.csv`: per-plot options, style
overrides, layout keys, legend geometry, axis scale and range, typography, figure
size) - and compared the render with the baseline grid and with the same control on
the plain plot. Every pure styling control left the plotted values and the
statistics unchanged; every control that acts on the plain plot acts on the grid,
except two that are the grid's defaults already (`legend_outside`, `outside right`)
and `auto_fix_layout`, which finds nothing to fix. The sweep found #20 above and the
legend-swatch half of #9. Pre-existing, not facet-specific, and left as found:
`violin_alpha` is shown while `kind = box`; the desktop Colorbar group and the line
plot's Marker size row are visible but inert on these two plot types.

## Statistics on grids

Within each panel: pairwise tests (48 results on the 2 × 2 grid), one-way ANOVA (4),
two-way ANOVA (12 terms), factorial ANOVA (12), Kruskal–Wallis + Dunn (28), each
result tagged with its panel; P values adjusted within the panel. **Also test across
the whole grid**: `Growth ~ Month * Age * Species` fitted once through the
R-validated factorial engine; the 7 terms equal `factorial_anova` run directly on the
table (F to 1e-12, P to 1e-9); four factors (x, hue, row, col) is explained, not
computed; a pairwise test at grid scope pools the panels (6 comparisons, n = 120 each).

## Known limits (reported to the user, not hidden)

- A stack of all-pairs brackets takes more of a short panel's range than of a
  single plot (107 vs 74 for the same six brackets): prefer `within_x`, or a taller figure.
- At most 12 levels per facet direction; panels narrower than 1.3 in are reported.
- Level names that cannot fit even at 70 % size are truncated with "…" and reported.

## Tests

`tests/test_facet_grids.py` (29), `tests/test_desktop_facets_and_builder.py` (5),
browser tests in `tests/test_streamlit_table_tools_and_axis_scale.py` (2). Packaged
`--selftest` renders a grid (SELFTEST OK). Full suite on the final code, 2026-10-17:
serial (authoritative) **4552 passed, 13 skipped, 0 failed** in 1 h 03 min; parallel
4548 passed, 13 skipped, 0 failed. Default renders of the 45 plot types (+3 variants):
48 of 48 byte-identical to the pre-change baseline.
