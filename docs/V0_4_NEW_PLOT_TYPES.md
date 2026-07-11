# v0.4 — new manuscript plot types

v0.4 adds **18 new plot types** aimed at a much broader range of publication
figures (distributions, omics, genomics, model performance, clinical timelines,
set overlap/flow, and method comparison). They plug into the existing engine:
the same PlotSpec validation, style profiles, publication-readiness check, and
export path (SVG/PDF/PNG + reproducibility sidecar). Every new type has a
bundled synthetic example dataset (**Use example data →** in either app).

> As with the existing types, the app **never fabricates statistics**. P-values,
> AUPRC, accuracy, Brier score, IC50/EC50, and inflation λ are computed only from
> valid inputs and are otherwise omitted with a warning — never invented.

## Suggested UI grouping (by manuscript use case)

- **Group comparison & distributions:** dot / strip · beeswarm · paired dot / slopegraph · raincloud
- **Relationships & trends:** dose-response · spider
- **High-dimensional / omics:** hierarchical dendrogram · MA plot · UMAP/t-SNE embedding
- **Genomics & variants:** Manhattan · Q-Q
- **Clinical & survival:** swimmer
- **Model performance:** precision-recall · confusion matrix · calibration
- **Set overlap & flow:** UpSet · Sankey / alluvial
- **Method comparison / QC:** Bland-Altman

## Plot types

| Plot type (`id`) | Use case | Required columns | Optional columns | Notes / limitations |
|---|---|---|---|---|
| Dot / strip plot (`dot_strip_plot`) | Every observation per group; readable alternative to bar plots | `x` (group), `y` (value) | `color`; `summary` (none/mean/median/ci/sd/sem), `jitter` | Summary overlay drawn over jittered points |
| Beeswarm plot (`beeswarm_plot`) | Distribution per group, points spread to avoid overprinting | `x` (group), `y` (value) | `color`; `summary` | Quasi-beeswarm (value-binned spread), **not** force-directed; very large n/group can still crowd |
| Paired dot / slopegraph (`paired_slopegraph`) | Within-subject change across matched conditions/timepoints | `subject`, `condition`, `value` | `color` (group) | Duplicate subject/condition cells are averaged; conditions ordered by first appearance |
| Raincloud plot (`raincloud_plot`) | Distribution shape + box summary + raw points in one panel | `x` (group), `y` (value) | — | Reuses matplotlib violin/box; reads best with ≤6 groups |
| Hierarchical clustering dendrogram (`hierarchical_dendrogram`) | Cluster genes/samples and show the tree (standalone) | label column + numeric sample columns | `method`, `metric`, `cluster` (rows/columns), `orientation` | Reuses shared clustering; `ward` forces euclidean; >40 leaves hides labels. TODO: accept precomputed linkage |
| MA plot (`ma_plot`) | RNA-seq/proteomics DE overview (abundance vs fold change) | average expression + log fold change | p-value/FDR (for coloring), gene label; `p_cutoff`, `label_top_n` | Flexible column auto-detection (AveExpr/baseMean/logCPM; logFC/log2FoldChange; padj/FDR/pvalue); p read **verbatim**; no LOESS trend in v0.4; top labels de-overlapped |
| Manhattan plot (`manhattan_plot`) | GWAS genome-wide significance | `chrom`, `pos`, `p` | `snp` (label) | Natural chromosome order (1–22, X, Y, MT); alternating colors; genome-wide (5e-8) + suggestive (1e-5) lines; out-of-range p clipped with a warning |
| Q-Q plot (`qq_plot`) | GWAS calibration / distribution check | `p` (pvalue mode) **or** `observed` (quantile mode) | `mode` | pvalue mode reports genomic inflation λ; quantile mode vs normal; y=x reference |
| Bland-Altman (`bland_altman_plot`) | Agreement between two measurement methods (QC) | `method_a`, `method_b` (numeric) | `label`, `show_ci` | Mean vs difference; bias + 1.96·SD limits of agreement; assumes paired rows |
| Precision-recall curve (`precision_recall_curve`) | Classifier performance on imbalanced data (complements ROC) | `label` (0/1) + `score` **or** precomputed `recall`+`precision` | `score2` (2nd model) | AUPRC = average precision; baseline = positive prevalence; never faked |
| Confusion matrix (`confusion_matrix`) | Classification results (binary or multiclass) | `true` + `predicted` **or** a precomputed matrix table | `normalize` (none/row/column/total) | Accuracy reported only when built from labels; auto-contrast cell text |
| Calibration plot (`calibration_plot`) | Clinical prediction / risk-model reliability | `label` (0/1) + `prob` **or** precomputed `predicted`+`observed` | `n_bins` | Equal-width binning; Brier score in metadata only; no ECE/over-claiming |
| Dose-response curve (`dose_response_curve`) | Drug screens; IC50/EC50 estimation | `dose` (>0), `response` | `group`, `fit` | Log-x; per-group 4PL fit via SciPy; EC50 in `metadata['fits']`; non-converging fits skipped honestly (never faked) |
| UpSet plot (`upset_plot`) | Set intersections (scalable alternative to Venn) | ≥2 binary 0/1 set columns (`mapping['sets']`) or element+set (long) | element id | Static; top 20 intersections shown |
| Swimmer plot (`swimmer_plot`) | Clinical timelines per patient (time on treatment, events) | `subject`, `end` (or `duration`) | `start`, `event`, `group` | One horizontal bar per patient; sorted by group then duration; one event marker at bar end |
| Spider plot (`spider_plot`) | Per-patient longitudinal trajectories (tumor burden / biomarker) | `subject`, `time`, `value` | `group`, `reference` | One line per subject; dashed reference (default 0%); **not** a radar chart; per-subject legend suppressed >10 subjects without a group |
| Sankey / alluvial (`sankey_plot`) | Flow between two category stages | `source`, `target`, `value` | — | Two-stage only; multi-stage alluvial is a documented TODO |
| UMAP / t-SNE embedding (`embedding_scatter`) | Cluster/label single-cell or sample embeddings | `x`, `y` coordinate columns (auto-detects UMAP_1/UMAP_2, tSNE_1/tSNE_2) | `color`, `shape`, `label` | **Precomputed coordinates only.** Direct `.h5ad`/AnnData ingestion is planned for a future version. Categorical vs continuous color auto-detected |

## Known limitations / TODOs (v0.4)

- **Beeswarm** is a dependency-free quasi-beeswarm (value binning), not a true force-directed layout.
- **Dendrogram** computes linkage from the matrix; a precomputed-linkage input is a TODO.
- **Sankey** supports two stages (source → target); multi-stage alluvial is a TODO.
- **Embedding** plots precomputed coordinates only; `.h5ad`/AnnData ingestion is deferred.
- **UpSet** is static and caps the display at the top 20 intersections by size.
- **Dose-response** IC50 vs EC50 naming is left to the user (reported as `ec50`); fits that don't converge show points only.

All 18 render through the standard export path (editable-text SVG/PDF, 300-dpi
PNG) and write the usual `*.plot_spec.json` reproducibility sidecar. A visual QA
gallery can be regenerated with `python scripts/generate_v04_qa_gallery.py`
(outputs under `reports/v04_qa/`).
