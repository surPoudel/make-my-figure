# Recommendation audit

Scope: the data-recommendation engine (`recommendations/`: profiler → schema → plot / transform /
statistics suggestions), the matrix QC "suspected data type" rule and its warnings
(`matrix_workflow/qc_diagnostics.py`), the preprocessing recommendations
(`matrix_workflow/transform_recommendations.py`) and the statistical-test recommender
(`statistics/test_registry.py::recommend_tests`). Numerical inputs to every rule (skewness, zero fraction,
totals, MAD outliers, integer-likeness) were validated against R in `results/comparisons/qc_python_vs_R.csv`
(all EXACT / NUMERICALLY_EQUIVALENT). This document audits the **rules and their wording**, which have no
R equivalent.

## 1. Rules exercised and their outcomes

| Input | QC suspected type | Preprocessing recommendations (ranked) | Assessment |
|---|---|---|---|
| RSEM expected counts (GSE299655; 4.6 % fractional cells, skew 42.8, 71 % zeros, totals 24–42 M) | `intensity_like_skewed` | log2(x+1)→z; arcsinh→z; filter sparse→log2; (always) internal-standard; quantile | **Mislabels the data type.** `integer_like` is `False` because RSEM expected counts are fractional, so the `count_like` branch (which requires integer-likeness) is skipped and the matrix is called *intensity-like*. The recommendations themselves (log transform, filter sparse features) are reasonable for counts, but the sentence "Values look intensity-like and skewed" is wrong for this file. The data profiler (`_classify_matrix`, 95 % integral threshold) *does* call the same file `count_like` — the two rules disagree on the same input. |
| W (NB counts, integer) | `count_like` | log2(x+1)→z; arcsinh→z; … | Correct; note that the library-size rule ("totals differ > 3×") did not fire (max/min = 2.1), so no CPM/total-sum workflow was proposed although `cpm`/`tmm` exist in the catalogue. |
| X (intensities, 4 % NA, skew 23.5) | `intensity_like_skewed` | log2(x+1)→z; arcsinh→z; … | Correct; the missing-value warning fires. |
| Y (centred log-like, negatives) | `log_like_or_normalized` | centre/scale only | Correct; the engine explicitly refuses to re-log. |
| Z (small integers 0–5, ties) | `possibly_log_or_normalized` | centre/scale only | Defensible (max < 40, |skew| < 1) but a 0–5 integer matrix is more likely ordinal/count data; the label hedges ("possibly"). |

`recommend_tests` was exercised through the bundled statistics examples (11 workflows): the suggested
primary test agreed with the example's intended test for every two-group, multi-group, paired,
correlation, categorical and survival example (`statistics_R_07_examples.csv` compares the executed tests).

## 2. Plot recommendations on the 38 bundled example tables

`results/comparisons/recommendation_examples_audit.csv` (generated from `recommend_for_table` on each
`examples/by_plot_type/*/data.csv`): the intended plot type is the **top-1 recommendation for 11/38
tables (29 %)**, within the top 3 for 17/38 (45 %), and absent from the list for 20/38. Schema detection
is correct for the role-based schemas (volcano/MA, survival, GWAS, classification, dose–response, network,
enrichment, mutation, matrices) and these get the right top plot. Misses fall in three groups:

* *Generic long tables* (bar, beeswarm, dot-strip, raincloud, ridge, line time-course, stacked, waterfall,
  spider, sankey, scatter): all map to `generic_long` and receive box/violin first. This is by design
  (the recommender is distribution-first) but the intended plot is often not offered at all (beeswarm,
  dot-strip, raincloud, waterfall, sankey, spider, stacked, line time-course).
* *Schema false positives*: `grouped_bar` and `histogram` are detected as **paired** (a subject-like id
  column plus two levels) and receive `paired_slopegraph`; `forest`, `embedding` and `dendrogram` inputs are
  detected as **expression-like matrices** and receive a clustered heatmap; `swimmer` is detected as
  survival. These are wrong for the data's purpose.
* *No schema*: `qq` (p-value column only) yields no recommendation; `confusion_matrix` and `upset` fall to
  a value-count transform.

None of this affects numerical correctness — recommendations are advisory and every one carries a "why"
sentence — but the confidence numbers (0.4–0.92) are heuristics, not calibrated probabilities, and should
not be described as such in a manuscript.

## 3. Wording audit (over-claiming / under-claiming)

| Where | Text | Verdict |
|---|---|---|
| `qc_diagnostics._warnings` | "Values look count-like (non-negative, integer, right-skewed)." | Accurate when it fires; **never fires for RSEM/salmon/kallisto expected counts** because of the strict integer test. Recommend: treat ≥ 95 % integer cells as integer-like (as the profiler does) or add an "expected-count-like (fractional counts)" branch. |
| `qc_diagnostics._warnings` | "Values look intensity-like and skewed." | Over-claims for fractional count matrices (see above). |
| `qc_diagnostics._warnings` | "Strongly right-skewed values — consider a log/arcsinh transform (the choice depends on your data type)." | Appropriately hedged. |
| `transform_recommendations` | "Values look already log-transformed or normalized — do NOT log again." | Appropriately assertive; the rule (negatives or max < 40) is documented. |
| `transform_recommendations` catalogue | "Quantile normalization (forces identical distributions) … Inappropriate when distribution shifts are biologically real." | Good. |
| `normalization.voom` (docstring / method name) | "voom-style log2 CPM on TMM-effective library sizes (Law et al. 2014)" | **Before this validation the output was edgeR-style log-CPM with a library-scaled prior, not limma's voom E** (up to 0.75 log2 units apart at low counts). Fixed to limma's definition (see DISCREPANCY_REPORT §2). The name still implies precision weights are used downstream; they are not (`voom_weights` is per-feature and not part of any workflow). Recommend renaming the user-facing label to "log2-CPM (TMM, limma voom definition)". |
| `differential.py` / GUIs | "This screen expects a NORMALIZED matrix … not a count-based model (DESeq2/edgeR/limma-voom)" | Correct and important; keep. |
| `plot_recommender` confidences | e.g. "0.92" for volcano | Heuristic ranks; not probabilities. Label as "rank score" in any text. |
| `recommend_tests` notes | "Cox reports hazard ratios (proportional-hazards assumption is not auto-checked)." | Correct disclosure. |
| `categorical.fishers_exact` (r × c) | none before | **Now** states that the p-value is a seeded Monte Carlo approximation (fix, see DISCREPANCY_REPORT §1). |
| Recommendation "Count how many rows fall in each 'geneSymbol' category and show a frequency bar." (RSEM) | | Harmless but useless for a gene matrix (120 duplicated symbols); the value-count transform should skip high-cardinality id-like columns. |

## 4. Recommendations for the maintainers (not applied — product decisions)

1. Make `integer_like` tolerant (fraction of integer cells ≥ 0.95, as the profiler already does) or add an
   explicit "expected counts (fractional)" type so RSEM/salmon/kallisto matrices are described correctly.
2. Reconcile `_classify_matrix` (profiler) and `_suspect_type` (QC) so one input gets one label.
3. For the `generic_long` schema, add the intended plot families (beeswarm/dot-strip/raincloud, line
   time-course when an ordered x is detected, waterfall when a signed percent-change column is detected).
4. Tighten the *paired* detector (currently any id column with two group levels) and the matrix detector
   (forest/embedding tables are wide numeric but not feature × sample matrices).
5. Present confidence values as ranks, not probabilities.
