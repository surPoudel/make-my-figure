# Statistics in Make My Figure

Make My Figure can compute common statistical tests, annotate figures with the
results, and export a transparent method report and a machine-readable
`StatsSpec` sidecar.

> **Important.** Make My Figure can compute common statistical tests, but **users
> are responsible for choosing tests appropriate to their experimental design.**
> The app reports methods transparently and flags common design issues, but it
> does **not** replace statistical review.

The engine never fabricates a p-value. Every number shown on a figure comes from
a stored result that records the exact test, the groups compared, the sample
size, pairing, the p-value, the adjusted p-value, the correction method, the
effect size, and (where applicable) a confidence interval.

## Contents

- [Supported tests](#supported-tests)
- [When to use each test](#when-to-use-each-test)
- [Assumption checks](#assumption-checks)
- [Model diagnostics (residual plots)](#model-diagnostics-residual-plots)
- [R-style statistics report](#r-style-statistics-report)
- [Required columns](#required-columns)
- [Paired vs unpaired](#paired-vs-unpaired)
- [Multiple-testing correction](#multiple-testing-correction)
- [Effect sizes](#effect-sizes)
- [Confidence intervals](#confidence-intervals)
- [Survival statistics](#survival-statistics)
- [How p-values are displayed](#how-p-values-are-displayed)
- [Method sentences](#method-sentences)
- [Using it in the apps](#using-it-in-the-apps)
- [The StatsSpec sidecar](#the-statsspec-sidecar)
- [Limitations and warnings](#limitations-and-warnings)

## Supported tests

| Test | Family | Effect size | CI | Library |
|------|--------|-------------|----|---------|
| Student's t-test | two-group, parametric | Cohen's d | mean diff | scipy |
| Welch's t-test | two-group, unequal variance | Hedges' g | mean diff | scipy |
| Mann–Whitney U | two-group, nonparametric | rank-biserial | – | scipy |
| Paired t-test | paired, parametric | Cohen's dz | mean of diffs | scipy |
| Wilcoxon signed-rank | paired, nonparametric | rank-biserial | – | scipy |
| One-way ANOVA | ≥3 groups, one factor | η² (and ω²) | – | scipy |
| Two-way ANOVA | two factors + interaction | partial η² per term | – | statsmodels |
| Factorial ANOVA / ANCOVA | 1–3 factors (+ covariates), Type II or III, estimability checked | partial η² per term | coefficient CIs | statsmodels |
| Repeated-measures ANOVA | within-subject | – | – | statsmodels |
| Kruskal–Wallis | ≥3 groups, nonparametric | ε² | – | scipy |
| Dunn's test (post-hoc) | pairwise after Kruskal | rank-biserial | – | native |
| Chi-square | categorical (r×c) | Cramér's V | – | scipy |
| Fisher's exact | categorical (2×2; r×c on scipy ≥1.15) | odds ratio | – | scipy |
| Log-rank | survival, ≥2 groups | – | – | native |
| Cox proportional hazards | survival, HR | hazard ratio | HR 95% CI | statsmodels |
| Pearson correlation | bivariate, linear | R² | Fisher-z on r | scipy |
| Spearman correlation | bivariate, monotonic | ρ | – | scipy |
| Linear regression | slope test | R² | slope | scipy |

The log-rank test and Dunn's test are implemented natively (verified against
`statsmodels.duration.survdiff` and standard formulas) so the project does not
depend on lifelines or scikit-posthocs.

## When to use each test

**Two groups, one numeric outcome (bar / box / violin):**
- roughly normal, similar spread → **Student's t-test**
- roughly normal, unequal spread → **Welch's t-test** (a safe default)
- skewed / ordinal / small n → **Mann–Whitney U**

**Two groups measured on the same subjects (before/after, matched):**
- **Paired t-test** (normal differences) or **Wilcoxon signed-rank** (otherwise).
  A subject/pair ID column is **required**.

**Three or more groups, one factor:**
- **One-way ANOVA** (parametric) or **Kruskal–Wallis** (nonparametric), optionally
  with post-hoc pairwise comparisons and multiple-testing correction.

**Two factors (e.g. genotype × treatment):**
- **Two-way ANOVA** for main effects + interaction, or pairwise tests *within*
  each level of one factor (comparison mode "within each x category").

**Repeated measures (subject measured at several timepoints):**
- **Repeated-measures ANOVA** — requires a subject ID and a complete, balanced
  design (one row per subject per level). If the structure is invalid the app
  reports a clear error rather than guessing.

**Survival (time-to-event):**
- **Log-rank** to compare curves; **Cox** for a hazard ratio.

**Categorical / composition:**
- **Chi-square** for larger tables; **Fisher's exact** for 2×2 or small expected
  counts.

**Scatter:**
- **Pearson** (linear), **Spearman** (monotonic), or **linear regression**
  (slope, R², CI). Computed per group if a color/group column is set.

**Volcano:** p-values come from the input; the app does **not** recompute
differential statistics. Only thresholds and labels are annotated.

## Assumption checks

A parametric test is checked **before** it runs, and the checks are listed with the
results (table rows *Shapiro-Wilk - normality* / *Levene (median-centred) - equal
variances*, verdict **met** / **NOT met** / *not tested*), in the method sentence, and
as a warning when one fails. What is checked is what the test assumes:

| test | normality (Shapiro-Wilk) | equal variances (Levene, median-centred) | alternative when normality fails |
|---|---|---|---|
| Student's t | each group compared | yes | Mann-Whitney U (Welch's t when only variances fail) |
| Welch's t | each group compared | not assumed | Mann-Whitney U |
| paired t | the paired differences | — | Wilcoxon signed-rank |
| one-way ANOVA | residuals (value − group mean) | across groups | Kruskal-Wallis (+ Dunn post-hoc) |
| two-way / factorial ANOVA, ANCOVA | **model residuals** | across factor combinations | none: reported with a recommendation (log / square-root transform in *Prepare table*) |
| Pearson | each variable | — | Spearman |

An ANOVA assumes normal **errors**, so its residuals are tested, not the pooled raw
values (a factor with a large effect makes those bimodal however normal each group
is). Levene's test is the median-centred (Brown-Forsythe) form, the default of
`car::leveneTest`. Both use α = 0.05 (`statistics.assumption_alpha`). Fewer than three
observations cannot be tested and say so; above 5000 the Shapiro-Wilk P is
approximate and even negligible departures are significant (judge from a Q-Q plot).
With many groups, about 5 % of Shapiro-Wilk tests fail by chance alone.

**If assumptions fail** (Statistics panel, both apps) decides what happens:
*Report it and keep the chosen test* (default; nothing is switched) or *Use the
non-parametric alternative* (`statistics.assumption_action = "switch"`), which runs the
alternative above and says so in the method sentence. On a facet grid the checks run
in every panel; the method sentence says in how many panels they were met and names
the others, and the whole-grid model has its own check.

Validated against base R 4.5.3 (`quality_audit/assumption_checks/validate_assumptions.R`:
`shapiro.test`, Levene from its definition): 11 checks, worst relative difference
8.7 × 10⁻⁹ (`tests/test_assumption_checks.py`).

## Model diagnostics (residual plots)

**Model diagnostics (residual plots)…** (Statistics panel; browser: the **🔍 Model
diagnostics** expander) draws R's four `plot(lm)` panels for the model behind the
statistics - the ANOVA / ANCOVA's factors and covariates, the group means behind a
t-test or Kruskal-Wallis comparison (both grouping columns on a grouped plot), `y ~ x`
for a correlation or regression:

| panel | look for | what a problem looks like |
|---|---|---|
| Residuals vs Fitted (+ lowess) | no pattern, an even band about 0 | a curve (a missing term), a funnel |
| Normal Q-Q (standardized residuals) | points on the quartile line | S-shape or heavy tails (non-normal errors) |
| Scale-Location (√\|standardized residuals\| + lowess) | a flat line | a rising line: the variance grows with the mean (heteroscedasticity) |
| Residuals vs Leverage (Cook's distance 0.5, 1) | no point beyond the dashed lines | an influential observation |

When every observation has the same leverage (any balanced ANOVA) the last panel is
**Constant Leverage: Residuals vs Factor Levels**, as in R. The three most extreme
points are numbered with their row in the table (R's `id.n = 3`). Below the plots:
the Shapiro-Wilk and Levene results for the same model and the largest Cook's
distance. **Panel** picks a facet panel or the whole grid; **Response** redraws the
model on another column - a transformed one from *Prepare table* - to see whether it
helps. **Save figure…** (PNG / PDF / SVG, 300 dpi) and **Save values (CSV)** (fitted,
residual, standardized residual, leverage, Cook's distance per row).

On the mock plant data (Young panel, `Growth_cm ~ Month * Nitrogen`) the Scale-Location
line rises by 0.63 and Levene's test fails (P = 9.5 × 10⁻⁵): growth spreads as plants
grow. With `log10(Growth_cm)` the line is flat (−0.02) and Levene's P is 0.96.

Computed as R computes them (`rstandard`, `hatvalues`, `cooks.distance`, `lowess(f =
2/3, iter = 3)`, `qqnorm`'s `ppoints`); validated against base R 4.5.3
(`quality_audit/assumption_checks/validate_diagnostics.R`): every per-observation value
to 1e-9 relative, the smoothers to 1e-8 (`tests/test_model_diagnostics.py`).

## R-style statistics report

**Statistics report (R-style summary(aov), TukeyHSD)…** (Statistics panel; browser:
*Show the statistics report* in the 🔍 Model diagnostics expander) prints, for the
model behind the figure, what R prints for

```r
model <- aov(Growth_cm ~ Species * Treatment, data = plant)
summary(model)
TukeyHSD(model)
```

- the same rows, columns, factor-level order (sorted; numbers numerically), pair
  order, significance codes and number formatting - **identical to R 4.5.3's console
  text, line for line**, on five models (one-, two- and three-way, balanced and
  unbalanced; `tests/test_anova_report.py`);
- then the assumption checks on the same model (Shapiro-Wilk on `residuals(model)`,
  Levene), notes (rows left out, unequal group sizes) and the software versions.

`summary(aov)` is a **Type I (sequential)** table: with unequal group sizes the order
of the factors changes the sums of squares, and the report says so. The figure's
ANOVA uses the *Sums of squares* setting (Type II by default); with equal group sizes
the two are identical, otherwise the report notes the difference (choose Type I to
match R). `TukeyHSD` compares the means of every term, which with unequal group sizes
are the model's adjusted means (`model.tables(model, "means")`), as in R. The
studentized range distribution is a port of R's own `ptukey` / `qtukey`
(`statistics/_tukey_dist.py`; quantiles agree to 1e-12, tail probabilities to 1e-13).

**Copy report** / **Save report (.txt)** in the desktop window, a download in the
browser. Models with covariates (ANCOVA) and correlation / regression tests are not
`aov` tables and say so; their results are in the statistics table and *Prepare
table ▸ Factorial analysis*.

## Required columns

| Workflow | Columns |
|----------|---------|
| Two-group / multi-group | a grouping column + a numeric value column |
| Paired / repeated | + a subject/pair ID column |
| Two-way ANOVA | value + two categorical factor columns |
| Survival | time (numeric) + event (1/0) + group |
| Categorical | two categorical columns (row, column) |
| Correlation / regression | two numeric columns (x, y) |

## Paired vs unpaired

An **unpaired** test treats the two groups as independent samples. A **paired**
test matches each observation in one condition to its partner in the other via a
subject/pair ID. Paired tests require exactly one measurement per subject per
condition; duplicate or unmatched IDs raise a validation error. Using a paired
test on unmatched data (or an unpaired test on repeated measures) is a common
design error — the app warns when it can detect it, but cannot detect all cases.

## Multiple-testing correction

When several comparisons form a family (e.g. all pairwise comparisons, or one
comparison per dose), raw p-values overstate significance. Available methods:

- **Benjamini–Hochberg FDR** (default) — controls the false discovery rate.
- **Bonferroni** — controls the family-wise error rate (conservative).
- **Holm–Bonferroni** — uniformly more powerful than Bonferroni.
- **None** — no adjustment.

The adjusted p-value is what the significance decision and the on-figure star
use. Omnibus tests (ANOVA F, Kruskal H) are single tests and are not folded into
the pairwise family.

## Factorial designs

`factorial_anova` fits 1–3 factors (with optional covariates) only after a design
check. Confounded factors, empty factor combinations, zero residual df, a constant
response, or repeated rows from one subject are explained and not computed. It is
validated against base R (509 of 509 quantities agree; the largest relative
difference is 6.5 × 10⁻¹³). Conventions and limits: [STATISTICS_FACTORIAL.md](STATISTICS_FACTORIAL.md).

## Effect sizes

Effect sizes quantify magnitude independent of sample size (see the table above).
Cohen's d/dz, Hedges' g, rank-biserial, η²/ω²/ε², Cramér's V, odds ratio, and
hazard ratio are reported where applicable. An effect size is shown as `NaN`
(and omitted from the figure) when it is undefined for the data.

## Confidence intervals

CIs are reported where they are standard and reliable: the difference in means
(t-tests, from the t-distribution), the mean of paired differences, the
regression slope, the Pearson r (Fisher-z transform, needs n ≥ 4), and the
hazard ratio (Wald, on the log scale). When a CI is not available it is stated
explicitly rather than approximated.

## Survival statistics

- **Log-rank**: a χ² statistic with df = (#groups − 1), plus observed and
  expected events per group. Verified against `statsmodels.duration.survdiff`.
- **Cox proportional hazards**: HR = exp(coef), a Wald 95% CI, and p-value per
  non-reference level. **The proportional-hazards assumption is not checked**;
  every Cox result carries a warning to verify it before reporting.

## How p-values are displayed

- **Stars**: `****` p<0.0001, `***` p<0.001, `**` p<0.01, `*` p<0.05, `ns`
  otherwise (applied to the *displayed* p-value — adjusted when a correction was
  used, so a star always matches the reported p-value).
- **Exact**: e.g. `p = 0.023`, or `p = 1.2e-05` for very small values, or
  `p < 0.001` below the chosen decimal resolution.
- **Both**: star + exact p.

You control decimals, the scientific-notation threshold, and whether to also
show the effect size on the figure.

## Method sentences

For every analysis the app generates a per-comparison method sentence, an
overall methods paragraph (with library versions and the correction method), and
a figure-legend sentence. Example:

> Pairwise comparisons between treatment groups within each dose were performed
> using Welch's t-test with Benjamini–Hochberg correction. P-values were adjusted
> across 3 comparisons.

Method reports export as Markdown, JSON, or a CSV/TSV results table.

## Using it in the apps

**Desktop:** open the **"6. Statistics"** panel → *Enable statistics* → choose a
test (or *Auto-suggest*), a comparison mode, and a correction → *Run statistics*.
Results appear in the table and the figure; export the table, copy the method
sentence, or export the method report.

**Streamlit:** the **"7. Statistics"** sidebar expander exposes the same controls
and shows a results table, method sentence, and a StatsSpec JSON download.

Worked examples for every workflow live in `examples/statistics/` (each with
data, a PlotSpec, a StatsSpec, a README describing the design, and the expected
method report).

## The StatsSpec sidecar

Exports include a `*.stats_spec.json` sidecar containing the configuration, the
full results, the method paragraph, the correction method, warnings, and library
versions — so any figure's statistics are fully reproducible. The StatsSpec is
also embedded inside the PlotSpec under `statistics`.

A figure package (`.mmfpackage`) stores the StatsSpec with its results next to the frozen data; on reopening, the statistics are recomputed from the frozen data and compared with the stored results, and any difference is reported (see `FIGURE_PACKAGES.md`).

## Limitations and warnings

- Test *selection* is advisory. The app cannot know your design; you must confirm
  the test is appropriate.
- Normality and equal-variance assumptions are **not** formally tested; they are
  listed as assumptions and the app warns on very small samples.
- Repeated-measures ANOVA assumes sphericity (no Greenhouse–Geisser correction).
- Cox proportional-hazards assumptions are not checked.
- Chi-square warns, but does not block, when expected counts are < 5.
- Non-finite values are dropped listwise before testing.
- See also [STATISTICAL_ANNOTATIONS.md](STATISTICAL_ANNOTATIONS.md) and
  [MULTI_PANEL_FIGURES.md](MULTI_PANEL_FIGURES.md).
