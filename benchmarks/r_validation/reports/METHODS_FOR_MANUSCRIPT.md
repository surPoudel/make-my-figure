# Methods text — independent validation against R (manuscript-ready draft)

**Validation of statistical and preprocessing components.** All numerical components of Make My Figure
(hypothesis tests, effect sizes, multiple-testing corrections, matrix normalization and transformation
methods, matrix quality-control metrics, principal-component analysis, hierarchical clustering and the
feature-level differential screen) were validated against independent reference implementations in R
(R 4.3.3; `stats`, `survival` 3.8-3, `car` 3.1-3, `rstatix` 0.7.2, `effectsize` 1.0.1, `MASS` 7.3-60,
`dunn.test` 1.3.6, `limma` 3.58.1, `edgeR` 4.0.16, `DESeq2` 1.42.0). R was used only as a reference;
the application itself has no R dependency. Twenty-six synthetic datasets (fixed seed 20250904) were
designed to cover the regimes in which implementations typically diverge — equal and unequal variances,
tied and small-sample rank tests, zero paired differences, unbalanced factorial designs, tied censoring
times, tables with small expected counts, p-value vectors with missing entries, count matrices with
library-size spread, intensity matrices with missing values, log-scale matrices with negatives, and
small-integer matrices with heavy ties — and every bundled example dataset shipped with the software
was analysed in addition. Python outputs were produced exclusively through the public
`make_my_figure_core` API; the R scripts read only the shared input files and never any Python result.
Comparisons were classified as *exact* (absolute difference ≤ 1 × 10⁻¹²), *numerically equivalent*
(≤ 1 × 10⁻¹⁰ absolute or ≤ 1 × 10⁻⁸ relative), *acceptable implementation difference* (same method;
documented numerical or convention cause), *method mismatch* (different method by design), or *fail*.
Where a documented convention had to be matched (for example scipy's rule for switching between the
exact and asymptotic Mann–Whitney distributions, Breslow tie handling in the Cox model, population
standard deviations in z-scores), the R reference applied the same convention and R's default result was
recorded alongside. Principal-component scores were compared after sign alignment; hierarchical
clusterings were compared through cophenetic distance matrices and merge heights.

**RNA-seq reference workflows.** The RSEM expected-count matrix deposited with GEO series GSE299655
(16 RAW264.7 libraries: Parental, ORP5/8 KD, ATP11A/C KD and CDC50A KD, four replicates each; byte-
identical to the file used here, SHA-256 37922f56…) was used as a real-data benchmark. Expected counts
are real-valued (4.6 % of cells are non-integer); the source matrix was never rounded or altered.
Genes with counts-per-million > 1 in at least four libraries were retained (11,646 genes). Make My
Figure's log-CPM (prior count 0.5), TMM, and voom-style log-CPM were compared cell-wise with
`edgeR::cpm`, `edgeR::calcNormFactors` and `limma::voom`. The application's feature-level differential
screen (per-gene Welch *t* on log-CPM, log₂ fold change as difference of group means, Benjamini–Hochberg
adjustment) was checked for exact equivalence against the same procedure in R and for scientific
concordance against limma-voom, edgeR quasi-likelihood and DESeq2 (the latter on rounded counts, as
DESeq2 requires integers), reporting Pearson and Spearman correlation of log₂ fold changes, direction
agreement, top-100/top-500 overlap and the Jaccard index of genes at FDR < 0.05.

**Results summary (numbers in `manuscript_validation_table.csv` and `FINAL_VALIDATION_MATRIX.csv`).**
Of 2,625 comparisons, 2,491 were exact or numerically equivalent and the remainder were documented
convention differences (e.g. rank tie handling at the TMM trim boundary, IRLS standard-error evaluation,
Monte Carlo approximation of the r × c Fisher p-value) or upstream-input differences; no comparison failed.
The benchmark identified and corrected five defects (non-reproducible r × c Fisher p-values; row-order-
dependent ROC AUC and average precision under tied scores; order-dependent tie handling in quantile
normalization; a voom implementation that did not follow limma's definition; an inverted Mann–Whitney
effect-size sign in the feature-level summary), each now covered by a regression test. On the GSE299655
matrix the application's log-CPM Welch screen reproduced limma-voom log₂ fold changes with Pearson r ≥ 0.999
and direction agreement ≥ 0.99 per contrast, while top-100 overlap by p-value (0.42–0.52) and Jaccard at
FDR 0.05 (0.57–0.80) show that it ranks evidence differently from moderated count models and should be
described as a screening tool, not as differential-expression inference.

**Reproducibility.** Inputs, outputs and their SHA-256 checksums, software versions, operating system
and the random seed are recorded in `benchmarks/r_validation/benchmark_manifest.json`; `sessionInfo()`
is in `results/R_sessionInfo.txt`.
