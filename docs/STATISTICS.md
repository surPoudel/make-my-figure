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
| Two-way ANOVA | two factors + interaction | η² per term | – | statsmodels |
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
