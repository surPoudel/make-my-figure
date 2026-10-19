# Make My Figure v1.3.2 — release notes

This release adds what an ecology or field-experiment analysis needs between the data
and the figure:
- facet grids (small multiples) on the box/violin and line plots;
- wide tables reshaped to long form, with the wide file left untouched;
- assumption checks before every parametric test, and R's residual plots;
- a statistics report that reads exactly as R's `summary(aov)` and `TukeyHSD`.

It also fixes ANOVA annotations that ignored the statistics controls. Every number in
these notes is a measurement, not an estimate.

## Facet grids

Map **facet row** and/or **facet column** on the box/violin or line plot to draw one
panel per level, as ggplot's `facet_grid(Age ~ Species)`: a 2 species × 2 ages × 3
nitrogen levels × 4 months design reads as one grid, nitrogen as colour and months
along x.

- Every panel shares the category order, the colour per level and one value axis
  (or its own, with **Facets share the value axis** off). Strips read `Species:
  Species_A` or just the value.
- The title, axis labels and legend belong to the grid, so the existing legend, axis,
  palette, colour-override, typography, log-axis and axis-range controls act on it.
- Statistics run within each panel; **Also test across the whole grid** fits one
  ANOVA with the facet variables as factors (`Growth ~ Month × Age × Species`).
- The line plot can draw mean ± SE as capped **error bars** as well as a band.
- A figure without facets renders exactly as before: all 48 default renders are
  byte-identical to v1.3.1.

## Wide tables to long form

A table with one row per plant and one column per sampling month (`Month_4 …
Month_10`) is reshaped with **↕ Wide → long…**. When columns share a name with a
number after it the button says *(suggested)* and the dialog opens filled in. Every
other column (Species, Age, Nitrogen, Replicate) is repeated on each row: the 60-row
wide plant table becomes exactly the 240-row long table. The wide file is never
changed. The long table is saved beside it as `<name>_long.csv` with a record of the
reshape (never overwriting), **Revert to original data** goes back, and a Figure
Package keeps both tables and replays the reshape to verify it.

Before this, the only reshape on offer turned that table into 300 rows of `[column,
value]`, gathering Replicate as a measurement and dropping Species, Age and Nitrogen.

## Assumption checks before the test

No assumption was tested before v1.3.2. Each result listed "approximately normal
residuals" and "equal variances" as text only. Now, before a parametric test:

- **Normality, Shapiro-Wilk** on each group (t-tests), on the paired differences
  (paired t-test), or on the **model residuals** (one-way, two-way, factorial ANOVA).
- **Equal variances, Levene's test** (median-centred) where the test assumes them.
- Listed in the statistics table (**met** / **NOT met**), the method sentence, the
  exported table and the statistics file; a failed check is a warning naming the
  alternative.
- **If assumptions fail**: keep the test and report it (default), or use the
  non-parametric alternative (Mann-Whitney, Wilcoxon, Kruskal-Wallis with Dunn,
  Spearman). A factorial ANOVA has no rank-based equivalent here and is never
  replaced; the warning recommends a log or square-root transformation.

The checks agree with base R 4.5.3 to 8.7 × 10⁻⁹. On the mock plant data the residuals
are normal (Shapiro-Wilk P = 0.249) but the variances differ within each age (Levene
P = 9.5 × 10⁻⁵): growth spreads as plants grow.

## Residual plots

**Model diagnostics (residual plots)…** draws R's four `plot(lm)` panels for the model
behind the test: Residuals vs Fitted, Normal Q-Q, Scale-Location and Residuals vs
Leverage with Cook's distance, the three most extreme rows numbered. Pick a facet panel
or the whole grid, and another response to compare a transformation. With
`log10(Growth_cm)` the plant data's Scale-Location line flattens (rise 0.63 → −0.02)
and Levene's P rises from 9.5 × 10⁻⁵ to 0.96. Every plotted value matches R to 10⁻⁹.

## A statistics report in R's format

**Statistics report (R-style summary(aov), TukeyHSD)…** prints the model's ANOVA table
and Tukey HSD comparisons exactly as R's console prints them: identical text, line
for line, on five reference models from R 4.5.3, from a one-way ANOVA to a 48-mean
three-way interaction, balanced and unbalanced. Then come the assumption checks and the
software versions. Copy it or save it as text. Like R's `summary(aov)` the table uses
Type I (sequential) sums of squares; with unequal group sizes the report says when
that differs from the figure's ANOVA.

## ANOVA statistics on the figure

- The ANOVA box on a facet panel stays inside its panel; it ran 233 px into the next
  one.
- **Annotation shows**, **Show effect size** and **Hide non-significant** now act on
  ANOVA terms. The default, *Stars only*, keeps "F = 77.9, p < 0.001" so saved figures
  do not change; **ANOVA terms as stars too** gives "Month: ****".
- **Post-hoc pairwise after omnibus** now runs after a two-way or factorial ANOVA, not
  only a one-way ANOVA.
- **Sums of squares** can be chosen for a factorial ANOVA: Type II (default), Type I
  (sequential, R's `anova(lm)`) or Type III. Type I agrees with R to 10⁻¹².

## Checks

- Full test suite at the released code: 4639 passed, 13 skipped, 0 failed
  (`test_pop_out_panels` run serially, as it must be on Qt).
- All 48 default renders byte-identical to v1.3.1.
- The packaged app's self-test renders all 45 plot types, the statistics and a facet
  grid, and measures the bundled Qt binding.
