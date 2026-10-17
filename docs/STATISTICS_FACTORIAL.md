# Factorial ANOVA / ANCOVA — and when it cannot be run

`make_my_figure_core.statistics.factorial` (`check_design`, `factorial_anova`,
`model_coefficients`). Desktop: **Prepare table ▸ 3 Factorial analysis**. Browser:
**📋 Prepare table ▸ Factorial design check**. Plot statistics: test
`factorial_anova` (factors default to the plot's x and group columns).

## A table with three categorical columns does not license a three-way ANOVA

`response ~ A * B * C` can be fitted only if all of the following hold:

* every combination of levels was observed (otherwise the interactions do not exist);
* no factor is a relabelling of another (otherwise their effects cannot be separated);
* the design matrix has full rank;
* observations remain to estimate the error variance (residual df > 0);
* the response varies;
* the rows are independent experimental units.

`check_design` tests each of these and says, in words, which ones fail.
`factorial_anova` refuses to run unless all of them pass. On the four-row bee
workbook, for `total quantity ~ treatment * social setting * time`:

```
This analysis cannot be estimated from these data:
• 'total quantity' has the same value (100) in every row; there is no variation to analyse.
• 'treatment' and 'time' are completely confounded: each level of 'treatment' occurs
  with exactly one level of 'time', so their effects cannot be separated.
• 12 of 16 factor combinations have no observations, so the interaction terms cannot
  be estimated. Collect data for the empty combinations, or fit main effects only.
• No residual degrees of freedom: 4 observations for 4 identifiable parameters. The
  error variance cannot be estimated, so F statistics and P values do not exist.
```

A rank-deficient design is refused even under "main effects only". Examples are a
factor nested in another (each level of B occurs within one level of A) and a covariate
that is a relabelling of a factor; fitting them would silently drop parameters and
misreport F and P. A response is "constant" only if every value is exactly equal, so a
response measured in nanomoles is analysed normally.

Warnings that do not block the analysis: few residual df (< 5), single-observation
cells, unequal cell sizes (Type II and III then differ), and the parallel-slopes
assumption when there are covariates. Rows with a missing value in any used column
are left out (listwise deletion), and the number is reported.

## Repeated measurements and random effects

If a **subject / colony** column is given and any unit contributes more than one row,
the design is refused. Repeated observations of one unit are not independent
replicates, and they need a mixed-effects model with the unit as a random effect.
MakeMyFigure does **not** fit mixed models (it has no validated implementation), so
it says so instead of pretending the rows are independent. The options are to
average to one value per unit and condition, or to analyse the full data in
dedicated software (e.g. R `lme4`). The one-way repeated-measures ANOVA (`rm_anova`)
remains available for a complete, balanced within-subject design.

## Conventions

| | |
|---|---|
| Model | ordinary least squares (statsmodels `ols`); factors as categorical terms |
| Default sums of squares | **Type II**: each term adjusted for every term that does not contain it (the default of `car::Anova`) |
| Type III | on request, **always with sum-to-zero contrasts**; Type III with treatment contrasts tests reference-level-dependent hypotheses and is not offered |
| Type I | on request: **sequential** (R's `anova(lm)`); each term adjusted only for the terms before it, in R's order (factors as listed, then covariates, then interactions by degree), so the factor order changes the answer when cell sizes differ |
| Coefficients | sum-to-zero (deviation) coding: level *i* of a factor is its deviation from the grand mean; the last level is minus the sum of the others |
| Covariates | main effects only (ANCOVA with parallel slopes) |
| Effect size | partial η² = SS_term / (SS_term + SS_residual) |
| Interactions | `full` (all) or `main` (main effects only) |
| Factors | 1–3 |

### Which sums of squares

With the **same number of observations in every combination** (a balanced design,
such as the plant-growth example: n = 5 in each of 48 cells) Types I, II and III
give identical sums of squares, F and P. The choice matters only when cell sizes
differ, for example after lost samples:

| | tests | use when |
|---|---|---|
| **Type II** (default) | each main effect adjusted for the other main effects; the interaction adjusted for both | the usual choice, and the more powerful one for main effects when the interaction is negligible (`car::Anova` default) |
| **Type I** | sequential: the first factor unadjusted, the second adjusted for the first, … | the factors have a natural order (a blocking factor or covariate first); R's `anova(lm)`. Reordering the factors changes the answer |
| **Type III** | every term adjusted for every other, interactions included | the interaction is real and main effects must still be reported (SPSS / SAS default); always with sum-to-zero contrasts here |

Report which type was used; the method sentence and the statistics table record it.

### Correction in this release: the two-way ANOVA effect size

Up to v1.3.0, `two_way_anova` reported SS_term / SS_total under the name "partial
eta-squared". On the unbalanced validation case B3 that gave 0.549 / 0.164 / 0.110
for treatment / time / interaction; the true partial η² is 0.756 / 0.480 / 0.384. It
is now the partial η² that R's sums of squares give. `two_way_anova` also runs the
design check, so a confounded or empty-cell design is refused rather than reported
with `NaN`.

## Independent validation against R

The reference is base R 4.5.3 (`quality_audit/general_tabular_workflow/r_validation/validate_factorial.R`),
which shares no code with the Python implementation:

* Type II SS from nested-model comparisons computed explicitly;
* Type I SS from `anova(fit)` (cases F1–F6: 27 terms, 81 quantities, worst relative
  difference 1e-12);
* Type III SS from `drop1(fit, . ~ ., test = "F")` under `contr.sum`;
* coefficients, standard errors, t, P and 95 % CIs from `summary(lm)` and `confint`;
* estimability from aliased coefficients, residual df, constant response, complete
  confounding and repeated colonies.

The datasets are **synthetic** (`tests/fixtures/factorial/generate.py`, fixed seeds),
shaped like an insect experiment but not real observations. They cover balanced
designs with and without interaction, unbalanced designs, different group sizes,
missing observations, ANCOVA, Type II and III, a missing factor combination,
complete confounding, zero residual df, a constant response, and repeated colonies.

Prespecified tolerances (`tests/test_factorial_anova_matches_r.py`, not to be
loosened): relative 1e-9 for SS, F, estimates, SE, t and CI limits; P values
relative 1e-7 (absolute 1e-15 below 1e-8); degrees of freedom exactly equal.

**Result: 509 of 509 compared quantities agree. The largest relative difference is
6.5 × 10⁻¹³.** All six non-estimable designs are refused, each where R shows the
reason. Per-quantity table: `quality_audit/general_tabular_workflow/factorial_statistics_validation.csv`.

The **coefficient table** (desktop: Factorial analysis ▸ Coefficients; browser:
under the ANOVA table; API: `model_coefficients`) has readable names
(`treatment = control`, `bee body size_mm (slope)`, `treatment = control × time = 2`)
and an explanation of each. These names map one-to-one onto R's `contr.sum`
coefficients (`treatment1`, …), and the estimates agree within the tolerances above
on all 13 estimable designs.

Not validated here, and therefore not offered: post-hoc comparisons after a factorial
model, estimated marginal means, mixed models, and sphericity corrections.
