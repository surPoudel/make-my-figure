# Independent R validation of MakeMyFigure — VALIDATION REPORT

Repository commit `ac49ff8a01bd7fba715a52ec7b8a92354662e80b` (`make_my_figure_core` 1.0.0), validated
2026-09-04. Python 3.11.8 / numpy 2.1.2 / scipy 1.17.1 / pandas 2.2.3 / statsmodels 0.14.6; R 4.3.3 with
limma 3.58.1, edgeR 4.0.16, DESeq2 1.42.0, survival 3.8-3, car 3.1-3, rstatix 0.7.2, effectsize 1.0.1, MASS
7.3-60, dunn.test 1.3.6, pROC 1.19.0.1 (`results/R_sessionInfo.txt`, `results/python_environment.txt`,
`benchmark_manifest.json` with SHA-256 of all 486 input/output files). All work is local; nothing was
pushed, merged, tagged, released or published.

## 1. Executive summary

* **2,625 individual comparisons** across nine components; after matching documented conventions,
  **0 FAIL, 0 NEEDS_REVIEW.** 2,491 are EXACT (≤ 1e-12) or NUMERICALLY_EQUIVALENT (≤ 1e-10 abs /
  1e-8 rel); 53 are documented ACCEPTABLE_IMPLEMENTATION_DIFFERENCE rows; 43 are UPSTREAM_INPUT_DIFFERENCE
  rows (voom-based inputs that inherit the TMM tie-boundary difference; the same components are EXACT on the
  shared log-CPM input); 4 QC rows are categorical rules not compared numerically.
* **Five defects were found, confirmed, fixed minimally and pinned with regression tests**
  (`tests/test_r_validation_regressions.py`, 6 tests): non-reproducible r × c Fisher p-values; row-order-
  dependent ROC AUC / average precision under tied scores; quantile normalization breaking ties
  arbitrarily; `voom` not implementing limma's voom definition; inverted Mann–Whitney effect-size sign in the
  feature-level summary. A sixth numerical fragility (last-bit near-ties of log-CPM zero counts in rank
  tests, giving p = 0.28 for an all-zero gene) was fixed by canonicalising values for rank tests.
* **Class B (scientific concordance):** the app's per-gene Welch-t screen on log-CPM correlates with
  limma-voom / edgeR-QL / DESeq2 log₂FC at Pearson 0.95–0.9999 and Spearman 0.995–0.9999 on the real
  RSEM matrix, with direction agreement 0.90–0.996, but shares only 39–52 % of the top-100 genes by p-value
  and Jaccard 0.55–0.80 at FDR 0.05 — it is *not* a substitute for a count model, exactly as the app's UI
  text states.
* The recommendation engine's numerical inputs are exact; its **wording mislabels fractional RSEM
  expected counts as "intensity-like"**, and its top-1 plot suggestion matches the intended plot for 29 % of
  the bundled example tables (`reports/RECOMMENDATION_AUDIT.md`).

## 2. Scope and inventories

`statistical_inventory.csv` (32 statistical procedures: 18 tests, 3 corrections, 2 differential engines,
9 plot-derived statistics, PCA, clustering, network metrics), `transformation_inventory.csv` (24
normalization / transform / QC entries) and `recommendation_inventory.csv` (12 rule sets) enumerate every
implementation (file::function), the exact scipy/statsmodels/numpy call or formula, its conventions and
defaults, the R reference used, and the validation class. Every entry except `network_metrics` (no igraph
in the R environment) was exercised.

## 3. Final validation matrix (`FINAL_VALIDATION_MATRIX.csv`, `results/validation_summary_table.csv`)

| Component | n | EXACT | NUM. EQUIV. | ACCEPTABLE | UPSTREAM | FAIL | NEEDS REVIEW | Verdict |
|---|---|---|---|---|---|---|---|---|
| statistics (18 tests × 26 datasets + 11 bundled examples) | 1039 | 1000 | 16 | 23 | 0 | 0 | 0 | PASS with documented convention differences |
| multiple testing (BH / Holm / Bonferroni, with NA) | 1176 | 1176 | 0 | 0 | 0 | 0 | 0 | PASS (exact) |
| transformations / normalizations (88 matrices, factors, filters) | 88 | 77 | 4 | 7 | 0 | 0 | 0 | PASS with documented convention differences |
| matrix QC metrics | 112 | 101 | 7 | 0 | 0 | 0 | 0 (+4 rule labels not compared) | PASS |
| PCA (scores sign-aligned, explained variance) | 15 | 10 | 0 | 0 | 5 | 0 | 0 | PASS on shared input; voom-based rows upstream |
| hierarchical clustering (cophenetic + merge heights) | 31 | 24 | 0 | 0 | 7 | 0 | 0 | PASS on shared input; voom-based rows upstream |
| differential screens (exact equivalence) | 100 | 47 | 6 | 16 | 31 | 0 | 0 | PASS on shared input |
| plot-derived statistics | 35 | 27 | 1 | 7 | 0 | 0 | 0 | PASS (4PL fit: optimizer tolerance) |
| RSEM characterisation | 29 | 29 | 0 | 0 | 0 | 0 | 0 | PASS |

Largest absolute difference among agreeing statistics rows: 2.2e-8 (a GLM Wald statistic; rel 1e-9).
Largest absolute difference among agreeing transformation cells: 1.0e-10 (CPM values ~1e5, rel 1e-15).

## 4. Design, independence and tolerance rules

Synthetic datasets A–Z (26 files, seed 20250904, `data/synthetic/MANIFEST.csv`) plus the adversarial
tied-score set `AA_roc_tied_scores.csv`; every bundled example (`examples/statistics/*`, 38
`examples/by_plot_type/*`) and the RSEM matrix. Python results come only from the public core API
(`python/export_make_my_figure_reference.py`); R scripts `R/00`–`R/16` read only the shared inputs
(asserted in `00_setup.R`); `python/compare_outputs.py` is the only code that reads both trees.
Classes: EXACT ≤ 1e-12; NUMERICALLY_EQUIVALENT ≤ 1e-10 abs or ≤ 1e-8 rel; ACCEPTABLE_IMPLEMENTATION_
DIFFERENCE / METHOD_MISMATCH / UPSTREAM_INPUT_DIFFERENCE only from a curated list with a written cause
(audited in `reports/DISCREPANCY_REPORT.md`); otherwise FAIL; one-sided values NEEDS_REVIEW. For
p-values below 1e-10 only absolute agreement is claimed (e.g. 1.9e-12 vs 1.0e-14 counts as equivalent).

## 5. Statistical tests (Class A)

All 18 tests agree exactly with R on every dataset once conventions are matched: Student/Welch *t* (CI,
Cohen's d / Hedges' g with J = 1 − 3/(4n − 9)), Mann–Whitney U (scipy's exact/asymptotic rule mirrored,
R's default reported), paired *t* / Wilcoxon (zeros dropped, no continuity correction, min(W⁺, W⁻)),
one-way ANOVA (η², ω²), Kruskal–Wallis (ε²), Dunn (shared tie correction, Cliff's δ as effect), two-way
type II ANOVA (`car::Anova`), repeated-measures ANOVA (`aov` + `Error(subject/w)`), Pearson (Fisher-z
CI), Spearman (ρ; scipy's t-approximation p reproduced, R's exact/AS89 p reported), OLS, five GLM
families, χ² (Yates for 2 × 2 only, Cramér's V), Fisher exact (2 × 2 exact; r × c seeded Monte Carlo after
the fix), log-rank (2 and 3 groups, tied times), Cox (Breslow ties = statsmodels default; Efron reported).
Within-x pairwise families, vs-control/all-pairs families and the BH/Holm/Bonferroni family corrections
through the runner are exact (351 rows). The 23 ACCEPTABLE rows are: 22 GLM Wald SE rows (Poisson,
negative-binomial: IRLS final-iteration weights in R vs converged information in statsmodels, rel ≤ 1e-7;
NB dispersion fixed at 1 in statsmodels — like-for-like reproduced) and the 3 × 4 Fisher p (Monte Carlo
approximation 0.04602 vs exact 0.04622).

## 6. Multiple-testing corrections

1,176 adjusted p-values (196 p-values × 3 methods × 2 datasets, one with three missing entries) are
bit-identical to `p.adjust` (max |Δ| 1e-15). Missing p-values are excluded from m and stay missing.

## 7. Transformations, normalizations, filters

77/88 cell-wise EXACT: total-sum, median, upper-quartile, CPM, log-CPM (prior 0.5 and 2), log2/ln/log10
(+1), arcsinh, sqrt, winsorize, z-scores (row/column/global, ddof 0/1), standard/robust scaling, four
centering modes, internal-standard (features / columns), control features, reference sample, imputation
(3 strategies), filters (4 rules + top-variance), heatmap scaling modes, quantile normalization (after the
fix: identical to `limma::normalizeQuantiles` on W, Y, Z; X with 4 % NA to 1e-10). The 7 ACCEPTABLE rows
are all TMM-derived (factors, TMM-CPM, TMM-log-CPM, voom): max factor difference 6.8e-4 (W) / 4.4e-6
(RSEM) from tie handling at the trim boundary (`DISCREPANCY_REPORT` A1).

## 8. QC metrics and recommendation inputs

108/108 numeric QC quantities agree (missing, zero/negative fractions, min/max/mean/median, integer-
likeness, per-feature variance, sample totals/medians, biased skewness, raw-MAD outlier lists).
`looks_log_scale` agrees. The four `suspected_data_type` labels are rules, audited in
`RECOMMENDATION_AUDIT.md`.

## 9. Discrepancy analysis

See `reports/DISCREPANCY_REPORT.md`: 5 fixed defects (§1), 3 method mismatches by design (§2), 11
convention/implementation differences with causes and magnitudes (§3), benchmark-side artefacts (§4).
No residual FAIL or NEEDS_REVIEW rows remain.

## 10. PCA and clustering

On the shared inputs (Y; W and RSEM log-CPM) PC1/PC2 scores agree to ≤ 3e-13 after sign alignment and
explained-variance ratios agree at the 4-decimal precision the app stores. Cophenetic distances and merge
heights agree to ≤ 1.1e-13 for average/complete/single/ward (= `ward.D2`) with euclidean, correlation,
cosine and cityblock metrics (24 EXACT). The voom-based rows (5 PCA, 7 clustering) differ only because the
input matrices inherit the TMM factor difference.

## 11. RSEM matrix (GSE299655) — characterisation

Byte-identical to the GEO deposit (SHA-256 `37922f56…`; `source_publication_audit.md`). 55,665 genes ×
16 libraries; 4.63 % of cells non-integer (RSEM expected counts); 70.9 % zeros; library sizes 24.0–41.5 M;
0 duplicated `geneID`, 120 duplicated `geneSymbol`. All 29 characterisation quantities agree between
Python and R. Sample → group mapping is taken from the GEO `Sample_description` fields (Parental,
ORP5/8 KD, ATP11A/C KD, CDC50A KD; `data/metadata/geo_sample_map.csv`). No biological claim is made or
tested; the groups are technical contrasts. The source matrix was never altered; each derived
representation is a separate file.

## 12. RSEM normalization and QC

Shared filter (CPM > 1 in ≥ 4 libraries): 11,646 genes on both sides (identical lists). CPM, log-CPM,
total-sum, upper-quartile, median scaling, log2(x + 1): EXACT. TMM factors within 4.4e-6 of edgeR; TMM-CPM
within 3e-3; voom log-CPM within 3.4e-7 of `limma::voom()$E` after the definition fix. QC: `integer_like`
= False, skew 42.8, zero fraction 0.71, `suspected_data_type = intensity_like_skewed` (see audit).

## 13. RNA-seq differential expression — exact equivalence and scientific concordance

Exact (Class A): the app's differential screen (Welch t on log-CPM, log₂FC = mean difference, BH) is
identical to the same procedure in R for all three knock-down contrasts (11,646 genes; log₂FC, t, p, BH
padj all EXACT/NUM. EQUIV.); on the voom input it is identical up to the TMM factor difference.
Concordance (Class B, `results/rnaseq_method_concordance.csv`, `figures/rnaseq_concordance.*`):

| Contrast (voom + Welch vs …) | Pearson log₂FC | Spearman log₂FC | direction agreement | top-100 overlap | Jaccard FDR < 0.05 |
|---|---|---|---|---|---|
| ORP5/8 KD: limma-voom / edgeR-QL / DESeq2 | 0.9999 / 0.987 / 0.947 | 0.9999 / 0.998 / 0.998 | 0.996 / 0.995 / 0.994 | 0.42 / 0.43 / 0.43 | 0.79 / 0.79 / 0.78 |
| ATP11A/C KD | 0.9998 / 0.989 / 0.989 | 0.9995 / 0.998 / 0.998 | 0.993 / 0.992 / 0.975 | 0.50 / 0.52 / 0.50 | 0.57 / 0.57 / 0.55 |
| CDC50A KD | 0.9994 / 0.993 / 0.993 | 0.9994 / 0.999 / 0.999 | 0.993 / 0.994 / 0.985 | 0.42 / 0.43 / 0.43 | 0.80 / 0.80 / 0.80 |

Effect sizes are essentially the limma-voom effect sizes (same log-CPM scale); the *ranking by evidence*
differs because the app's per-gene Welch t has 6 residual df and no variance moderation, so top-N
overlap by p-value is ~40–50 %. On the synthetic W matrix (80 true DE of 400): Pearson 0.97–0.9996,
Jaccard 0.40–0.49. DESeq2 was run on rounded counts (documented derived representation).

## 14. Plot-derived statistics

ROC AUC (after the tie fix, = pROC), average precision, Brier score, accuracy, Bland–Altman bias / SD /
LoA, genomic-inflation λ, per-group regression (slope, intercept, r, R², p, SEs) and the drawn Kaplan–Meier
step curves (S(t) at all 113 plotted points vs `survfit`) are EXACT. 4PL dose–response parameters agree
with `nls(port)` to ≤ 1e-6 (EC50) and ≤ 3e-4 relative (asymptotes) — optimizer tolerance.

## 15. Recommendation validation

`reports/RECOMMENDATION_AUDIT.md`: numerical inputs exact; wording defects (fractional-count matrices
called intensity-like; profiler and QC disagree on the same input); top-1 plot recommendation matches the
intended plot for 11/38 bundled tables, top-3 for 17/38; schema false positives for `grouped_bar`,
`histogram` (→ paired), `forest`, `embedding`, `dendrogram` (→ matrix), `swimmer` (→ survival).

## 16. Adversarial edge cases

Zero-variance group (E): scipy returns t/p with cancellation warnings, R errors — both flag; documented.
Ties in rank tests (C, I, G): exact after convention matching. Zero paired differences (G): handled
identically. Small n (D): exact-distribution regime reproduced. Missing p-values (V): exact. Tied ROC
scores (AA): defect found and fixed. Constant / all-zero features: MWU p now 1 (was 0.28). Fractional
counts: integer check correctly refuses the count model; QC label wrong (audit). Unequal variances and
unbalanced designs: exact. Correlation/cosine clustering with zero-variance rows: exact.

## 17. Bugs fixed (before/after evidence in `results/comparisons/bugfix_*.json`, `adversarial_roc_ties.json`)

| Fix | File | Before → after | Test |
|---|---|---|---|
| r × c Fisher reproducible (seeded MC, labelled approximate) | `statistics/categorical.py` | 5 different p per 5 calls → 0.0460248 every call | `test_fisher_rxc_is_reproducible` |
| ROC / PR tie collapsing | `plots/roc.py`, `plots/precision_recall.py` | AUC 0.707–0.734 by row order → 0.7254 (= pROC) | `test_roc_auc_and_ap_do_not_depend_on_row_order_with_tied_scores` |
| Quantile normalization (limma algorithm) | `matrix_workflow/normalization.py` | 3,225 cells ≠ limma → 0 | `test_quantile_normalization_ties_get_equal_values_and_match_bolstad` |
| voom = limma definition | `matrix_workflow/normalization.py` | max Δ 0.746 → 9.9e-4 (TMM residual) | `test_voom_matches_limma_definition` |
| MWU effect sign | `matrix_workflow/differential_summary.py` | −0.92 vs +0.92 → consistent | `test_feature_summary_mann_whitney_effect_sign_matches_rank_biserial` |
| Near-tie canonicalisation for rank tests | `differential.py`, `differential_summary.py` | all-zero gene p 0.28 → 1 | `test_rank_tests_treat_last_bit_near_ties_as_ties` |

Existing suites touching these modules pass (`test_normalization_methods`, `test_matrix_qc_polish`,
`test_preprocessing_transforms`, `test_matrix_transformations`, `test_differential`,
`test_feature_differential_summary`, `test_processed_matrix_differential_summary`, `test_statistics_core`,
`test_renderers -k roc/precision`).

## 18. What was NOT validated / limitations

Network metrics (no igraph in R); `voom_weights` (method mismatch, unused by workflows); GUI code paths
(tested elsewhere, not numerical); the optional PyDESeq2 extra (not installed); multi-predictor GLM
beyond two covariates; statistics on the Streamlit/desktop UI layers (the same core is called). R was run
in a micromamba environment on Linux/WSL2; R's default settings sometimes differ from the like-for-like
settings used (all such cases are listed with R's default alongside). Confidence intervals for the
Mann–Whitney/Wilcoxon are not produced by the app and therefore not compared.

## 19. Reproducibility

`benchmark_manifest.json` (commit, versions, OS, UTC timestamp, seed, tolerances, SHA-256 of 486
files), `results/R_sessionInfo.txt`, `results/python_environment.txt`, `data/synthetic/MANIFEST.csv`.
Re-run commands in `README.md`.

## 20. Conclusion

Within its declared scope, every statistic, correction, transformation, QC metric, PCA, clustering and
differential-screen value that MakeMyFigure produces is reproduced by an independent R implementation to
machine precision, or differs for a documented and audited reason. Five defects — all affecting
reproducibility or labelling rather than the core formulas — were found by the benchmark and fixed with
regression tests. Claims for the manuscript should be limited to Class A equivalence for the listed
components and to *concordance* (not equivalence) for RNA-seq differential expression, using the numbers
in §13.
