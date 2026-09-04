# Discrepancy report

Every Python-vs-R difference that survived the tolerance test (`abs 1e-10 / rel 1e-8`) is listed here with
its **cause**, its **class**, its **magnitude**, and what was done. Nothing was tuned to make numbers
agree: where the R reference had to match a documented MakeMyFigure convention, R's default is reported
next to it (`results/comparisons/statistics_R_convention_context.csv`). Tables referenced:
`results/statistics_python_vs_R.csv`, `results/transformation_python_vs_R.csv`,
`results/comparisons/*.csv`, `FINAL_VALIDATION_MATRIX.csv`.

## 1. Confirmed defects (fixed, with regression tests) — bug-fixing protocol applied

For each: input frozen → before/after saved → regression test added → minimal fix → full re-run.

| # | Component | Defect | Evidence (before) | Fix | After | Test |
|---|---|---|---|---|---|---|
| D1 | `statistics/categorical.py::fishers_exact` (r × c tables) | scipy ≥ 1.15 computes the r × c p-value by **unseeded Monte Carlo**; the app returned a *different* p-value on every call and labelled it "Fisher's exact". | P (3×4): 0.0483, 0.0464, 0.0446, 0.0466, 0.0438 on five calls; R `fisher.test` exact = 0.046215 (`results/comparisons/bugfix_fisher_rxc_before_after.json`) | Pass `MonteCarloMethod(n_resamples=200000, rng=default_rng(20240901))`; record method/seed/n in `extra`; add a warning saying the value is an approximation. | 0.0460248 on every call (0.29 s); Monte Carlo error vs exact ≈ 2e-4 | `test_fisher_rxc_is_reproducible`, `test_fisher_2x2_path_unchanged` |
| D2 | `plots/roc.py::_roc`, `plots/precision_recall.py::_pr_from_scores` | Tied scores were split by numpy's unstable `argsort`, so the ROC/PR curves, **AUC and average precision depended on the row order** of the input table. | 200-row table with integer scores: AUC 0.7337 / 0.7130 / 0.7067 / 0.7117 / 0.7265 over five shuffles; tie-corrected Mann–Whitney AUC and pROC = 0.725442; AP 0.6574 … 0.6313 (`results/comparisons/adversarial_roc_ties.json`) | Stable sort + one operating point per distinct score (ties move together). | AUC 0.7254 for every shuffle (= pROC); AP 0.5872 for every shuffle | `test_roc_auc_and_ap_do_not_depend_on_row_order_with_tied_scores` |
| D3 | `matrix_workflow/normalization.py::quantile_normalize` | Tie handling by `argsort(argsort())` (unstable): **identical input values received different normalized values**, order-dependent; not the Bolstad/limma algorithm. | W count matrix vs limma `normalizeQuantiles`: 3,225 / 4,800 cells differ (max 28.1); vs an ordinal-tie reference 2,847 cells still differ (max 56.2) → tie order was implementation-defined. Z: 90 cells (max 1.0). Y (no ties): exact. | limma's algorithm: reference = row means of column-sorted values (NA columns interpolated onto the full grid), each value mapped at its **average rank**. | W, Y, Z cell-wise EXACT vs limma (0 cells differ); X (4 % NA) within 1e-10 | `test_quantile_normalization_ties_get_equal_values_and_match_bolstad` |
| D4 | `matrix_workflow/normalization.py::voom` | Labelled "voom (Law et al. 2014)" but computed edgeR-style log-CPM with a **library-size-scaled** prior; limma's voom uses `log2((count + 0.5)/(lib·nf + 1)·1e6)` (unscaled prior). | W: max \|Δ\| vs `limma::voom()$E` = 0.746 log2 units; RSEM: 0.626 (low counts in libraries far from the mean library size); the limma formula reproduces R to 5.7e-14 | Use limma's definition (unscaled prior; `lib + 2·prior`). | matches `limma::voom()$E` up to the TMM factor difference (§3) | `test_voom_matches_limma_definition` |
| D5 | `matrix_workflow/differential_summary.py::_two_group_record` (Mann–Whitney) | Effect size used `1 − 2U/(n_a n_b)`: **sign inverted** relative to `statistics.effect_sizes.rank_biserial_from_u` (`2U/(n_a n_b) − 1`) and to the table's own mean difference / fold change. | Toy A > B: summary −0.92, statistics engine +0.92, mean difference > 0 | `2U/(n_a n_b) − 1` | consistent sign | `test_feature_summary_mann_whitney_effect_sign_matches_rank_biserial` |

Side observation while testing D5: `feature_differential_summary(correction="none")` raises `KeyError`
(only BH/Bonferroni/Holm are mapped), whereas the statistics engine accepts `"none"`. Not changed
(interface decision), recorded here.

## 2. Method mismatches (Class B by design — documented, not "fixed")

| # | Component | Nature | Magnitude / evidence |
|---|---|---|---|
| M1 | `differential.py::differential_screen`, `feature_differential_summary` vs limma-voom / edgeR-QL / DESeq2 | Per-feature Welch *t* on log-CPM + BH is **not** a count model: no empirical-Bayes variance moderation, no dispersion estimation, no precision weights. | See `results/rnaseq_method_concordance.csv` (Pearson/Spearman of log₂FC, direction agreement, top-N overlap, Jaccard at FDR 0.05) — reported as concordance only. The app's UI text already says so ("not a count-based model"). |
| M2 | `normalization.voom_weights` | Per-feature weights from a lowess of √SD vs mean (no design, raw SD); limma's weights are per observation from the fitted mean–variance trend. | Not used by any workflow; flagged so the name is not read as "limma weights". |
| M3 | `dose_response` 4PL fit | `scipy.optimize.curve_fit` (bounded TRF) vs `nls`: same model, different optimizer; local optimum depends on start values. | Not compared numerically (no `drc` in the R env); listed as optimizer-dependent. |

## 3. Acceptable implementation / convention differences (Class A after matching conventions)

| # | Where | Cause | Magnitude |
|---|---|---|---|
| A1 | TMM factors (`tmm_norm_factors` vs `edgeR::calcNormFactors`) | Rank-based trimming is discontinuous. MakeMyFigure ranks M/A ordinally (ties broken by row order); edgeR uses average ranks; and last-ulp differences in `log2` change which A-values tie. Verified gene-by-gene: on W sample A_2 one gene (row 357) whose A-value is tied with four others exactly at the 5 % trim boundary has average rank 17 (< loS = 19, dropped by edgeR) but ordinal rank 19 (kept by MakeMyFigure). Reference sample, trims and weights are identical. | max Δfactor 6.8e-4 (W, 400 genes), 2.5e-7–4.4e-6 (RSEM, 11,646 genes); propagates to TMM-CPM (≤ 50 CPM units at CPM ≈ 1e5 on W; 3e-3 on RSEM) and voom log-CPM (≤ 1e-3 log2 units). Optional alignment: use average ranks (`scipy.stats.rankdata`) — not applied (it is a convention, not an error; and cross-language ulp ties would still leave rare differences). |
| A2 | GLM Wald statistics / p / CI (Poisson, Gamma) | R `summary.glm` standard errors use the working weights of the final IRLS iteration evaluated at the *previous* iterate; statsmodels evaluates the information at the converged coefficients. With `glm.control(epsilon = 1e-14)` R's coefficients agree with statsmodels to ≤ 1e-10; with R's default `epsilon = 1e-8` the Gamma fit stops two iterations early (Δβ ≈ 7e-6). | rel ≤ 7.5e-8 on z / p / CI after tightening R; R default reported as `R_default.*` |
| A3 | Cox HR (Breslow) | `coxph` default `eps = 1e-9` vs PHReg; with `eps = 1e-12` identical to ≤ 1e-9 rel. | ≤ 1e-9 |
| A4 | Mann–Whitney p (small n / ties) | scipy `method='auto'`: exact only if both n ≤ 8 and no ties, else normal approximation with continuity correction; R: exact if n < 50 and no ties. Same statistic U. | Like-for-like exact; R default differs for A (n = 12/15, no ties: R exact vs scipy asymptotic) — see context table. |
| A5 | Wilcoxon signed-rank | scipy: `zero_method='wilcox'`, no continuity correction, statistic = min(W⁺, W⁻); R: `correct = TRUE`, V = W⁺. | Like-for-like exact; conventions recorded. |
| A6 | Spearman p | scipy: t-approximation; R: exact/AS 89 for n < 1290 without ties. ρ identical. | p differs at the 3rd–4th decimal for n = 35–40; both valid. |
| A7 | Fisher 2 × 2 odds ratio | scipy: sample OR ad/bc; R: conditional MLE. p identical. | OR differs (e.g. 0.318 vs 0.331); documented in the result label. |
| A8 | Quantile normalization with missing values (X) | Both interpolate the reference for columns with NA; MakeMyFigure now follows limma's scheme exactly (after D3). | see final table |
| A9 | PCA explained variance | Metadata stores ratios rounded to 4 dp. Scores agree to 1e-14 after sign alignment. | ≤ 5e-5 (rounding) |
| A10 | Skewness | scipy biased g1 = R computed from definition; MAD outlier rule uses raw MAD (no 1.4826). | exact |
| A11 | Degenerate two-group input (E: one group constant) | scipy emits catastrophic-cancellation warnings and a t/p from a zero variance; R errors. Both flag it; not comparable. | NEEDS_REVIEW → documented |

## 4. Items that were R-side/benchmark artefacts (not MakeMyFigure issues)

* V dataset: quoted empty strings were skipped as blank lines by `read.csv`; fixed by writing `NA`
  explicitly. `adjust_pvalues` aligns missing p-values correctly (1,176/1,176 exact after the fix).
* R statistic-name conventions (Pearson `statistic` = r not t, `linear_regression` `statistic` = slope,
  Spearman = ρ; omnibus comparison label `all`) had to be mirrored on the R side.
* `preprocessCore::normalize.quantiles` could not start threads in the sandbox; `limma::normalizeQuantiles`
  (pure R, same algorithm) is the canonical reference instead.

## 5. Residual `FAIL` / `NEEDS_REVIEW` rows after the final run

After the final run: **0 FAIL, 0 NEEDS_REVIEW** in all nine components (2,625 comparisons). Residual
non-exact rows are exactly the curated items above: 23 statistics rows (A2 GLM SEs, D1 Monte Carlo p),
7 TMM-derived transformation rows (A1), 16 differential rows (all-zero gene0044: Python t = 0 / p = 1 vs R
NA, shifting BH m by one), 43 UPSTREAM_INPUT_DIFFERENCE rows (voom-based inputs inheriting A1), 7 dose-
response 4PL parameters (optimizer tolerance), and 4 categorical QC labels that are not numeric.
