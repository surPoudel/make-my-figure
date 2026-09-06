## Part V — Column mapping

### 21. How mapping works

Every plot type declares its **column roles** in one registry (`ui_hints.py`), and both apps build their mapping controls from it — a combo box per single-column role, a multi-select list per multi-column role. When a table loads, a role is prefilled only if a column with the expected name exists (bundled examples), or, for a volcano plot, if a DE-style header is recognised (`logFC` / `log2FoldChange`, `P.Value` / `pvalue`, `adj.P.Val` / `padj`, gene symbol). Everything else you set yourself, and everything prefilled you can change.

**Note:** Make My Figure does not infer biological meaning. A column called `time` is not a survival time until you map it to *time*; a numeric column in a matrix is not a measurement until it is a selected value column.

### 22. Roles by plot family

| Role | Meaning | Plots |
|---|---|---|
| `x`, `y` | category / value, or numeric axes | bar, grouped bar, box/violin, strip, beeswarm, raincloud, scatter, line, waterfall, lollipop, MA, embedding |
| `group`, `color`, `stack`, `shape` | series colour, stacking, marker shape | grouped bar, line, ridge, histogram, dose-response, swimmer, spider, stacked bar, PCA (metadata) |
| `label`, `id_col` | point labels / feature identity (duplicate-safe) | volcano, MA, scatter, lollipop, embedding, Bland-Altman |
| `p`, `x` (effect) | p-value / log fold change | volcano, MA, Manhattan (`p`), Q-Q (`p`) |
| `chrom`, `pos`, `snp` | chromosome, position, variant id | Manhattan |
| `time`, `event`, `group`; `survival_columns` | subject-level survival; or precomputed S(t) columns | Kaplan-Meier |
| `subject`, `condition`, `value` | paired measurements | paired slopegraph |
| `subject`, `start`, `end`, `duration`, `event` | timelines | swimmer |
| `subject`, `time`, `value` | longitudinal change | spider |
| `label`, `score`, `score2` | truth label and one or two scores | ROC, precision-recall |
| `true`, `predicted` | confusion matrix | confusion matrix |
| `label`, `prob` | calibration | calibration |
| `label`, `estimate`, `lower`, `upper` | forest plot rows | forest |
| `dose`, `response`, `group` | dose-response | dose-response |
| `method_a`, `method_b` | two measurements of the same thing | Bland-Altman |
| `source`, `target`, `value` / `weight`, `interaction_type` | flows and edges | Sankey, network |
| `row_id`, `matrix_row_id`, `value_columns` | matrix feature id and measurement columns | heatmap, clustering, dendrogram, PCA |
| `sample`, `row`, `fill` | oncoprint long form | oncoprint |
| `sets` | 0/1 membership columns | UpSet |
| `y`, `x`, `size`, `color` | term, enrichment, count, significance | enrichment dot plot |

Multi-column roles (`value_columns`, `survival_columns`) are lists: tick every column that belongs — a single choice would silently plot one series.

### 23. Statistics columns

The Statistics panel has its own **Group column**, **Subgroup column**, **Subject/pair ID** and **Control group** selectors. When left at *(none)* they follow the plot mapping (x as the group, y as the value); set them explicitly for paired tests (subject id), two-way designs (subgroup) and comparisons against a control.

## Part VI — Data-aware recommendations

### 24. What the engine does

On load, `recommend_for_table` profiles the table — column kinds, identifier columns, binary columns, missingness, p-value-like ranges, matrix shape, correlation/adjacency structure — and assigns a **schema**: `precomputed_differential`, `survival`, `gwas`, `classification`, `dose_response`, `network_edge_list`, `mutation_matrix`, `enrichment`, `correlation_matrix`, `expression_like_matrix`, `numeric_matrix`, `matrix_plus_metadata`, `paired`, `generic_long`, or `unknown`. Rules per schema propose plots with a **confidence score**, a **reason**, the **suggested mapping**, missing mappings, suggested statistics and thresholds.

The desktop **Recommended figures** group shows cards (*Generate*, *Add to Figure Builder*, *Dismiss*); the browser shows the **🔮 Recommended figures** expander. **Generate** switches the plot type and applies the suggested mapping; you still confirm it in *Map columns*.

![Recommendation cards for a grouped-observation table.](../../assets/screenshots/desktop_09_plot_recommendations.png)

![Browser: the Recommended figures expander for a matrix.](../../assets/screenshots/streamlit_09_recommended_figures.png)

### 25. Typical recommendations (from the bundled examples, this commit)

| Table shape (schema) | Suggested plots (score) |
|---|---|
| grouping column + numeric value (`generic_long`) | box/violin with points (0.72), ridge/density (0.62), bar with error bars (0.60), grouped bar (0.55) |
| logFC + p-value (+ FDR) per feature (`precomputed_differential`) | volcano (0.92); heatmap of the values (0.55) |
| feature × sample numeric matrix (`expression_like_matrix`) | clustered heatmap (0.85), PCA (0.70) |
| time + 0/1 event + group (`survival`) | Kaplan-Meier (0.88) |
| source/target(/weight) (`network_edge_list`) | network graph (0.80) |
| chromosome + position + p (`gwas`) | Manhattan (0.82), Q-Q (0.70) |
| subject × two conditions (`paired`) | paired slopegraph (0.75), box/violin (0.70) |
| term + enrichment + count (`enrichment`) | enrichment dot plot (0.80) |

An embedding table (UMAP/t-SNE coordinates) is recognised as a numeric matrix and gets matrix suggestions; choose *UMAP / t-SNE embedding scatter* yourself.

### 26. Limitations

Scores are rule-based heuristics about the table's shape, not probabilities and not a judgement of scientific appropriateness. A wrong column-name convention lowers a score; an unusual but valid design may get no recommendation. Treat every suggestion as a starting point to confirm in *Map columns*.

## Part VII — Matrix Workflow

![The Matrix Workflow: five confirmed steps from mapping to the plot editor; the original matrix is never modified.](../../assets/diagrams/matrix_workflow.png)

### 27. Opening it

Load the matrix (any file or worksheet), then **🧮 Matrix workflow…** (desktop) or **Workflow → Matrix workflow (guided)** (browser). The desktop dialog has five tabs; later tabs stay disabled until the earlier step is confirmed. The browser shows the same steps as expanders.

![Browser: Matrix workflow (guided), step ① Map columns — feature ID, optional display column, value columns, annotation columns, and the value scale with a hint.](../../assets/screenshots/streamlit_06_matrix_workflow.png)

### 28. ① Map columns

![Step ①: feature ID column, feature display column, value scale, and the value-column list.](../../assets/screenshots/desktop_06_matrix_workflow_mapping.png)

- **Feature ID column** — the identifier (gene, protein, feature).
- **Feature display column** — optional friendlier name for labels.
- **Value scale (you confirm)** — `normalized`, `log_normalized`, `raw_numeric`, or `unknown_user_confirmed`. Preprocessing is offered only for raw-like data.
- **Value columns** — every measurement column; numeric annotation columns (e.g. a 1/2/3 level code) are unselected by default and stay out unless you tick them.
- The browser adds an explicit **Annotation columns** selector and shows a hint when the values look log-scaled (*"If so, choose log_normalized"*) — a hint, never a decision.
- **Confirm mapping** writes the **MatrixSpec** (source file/sheet, feature column, annotation columns, value columns, excluded columns, value type, missing-value and duplicate-feature policies, confirmation flag).

### 29. ② Define groups

![Step ②: one group per sample column, typed or uploaded.](../../assets/screenshots/desktop_07_matrix_workflow_groups.png)

Three sources, in order of preference: **⬆ Upload metadata file…** (CSV/TSV/XLSX with a sample column and a group column), a metadata **worksheet** of the same workbook (browser), or the in-app table — type a group per sample column, or select rows and **Apply to selected rows**; leave a cell blank to exclude that column. **Confirm groups** writes the **SampleMetadataSpec** and reports **sample matching** (columns in the matrix without metadata and vice versa).

### 30. ③ Preprocess (raw-like)

![Step ③: Run diagnostics, a QC-plot preview, and the recommended preprocessing recipes (you choose; nothing is applied automatically).](../../assets/screenshots/desktop_08_preprocessing_qc.png)

Optional, for raw-like / unnormalised / skewed matrices; skip it if the matrix is already normalised.

1. **Run diagnostics** — reports the *suspected data type* (e.g. `log_like_or_normalized`), features × samples, overall skew, zero and negative fractions, the value range, and warnings such as *"Negative values present — log transforms and ratio fold-change are not valid without an explicit, justified offset"* or *"Values may already be log-transformed/normalized — avoid re-logging"*.
2. **QC plot** — choose one of the nine QC plots (Part VIII §36) and **Preview** it for the current matrix.
3. **Recommended preprocessing (you choose; not applied automatically)** — a list of recipes derived from the diagnostics, each a short chain of steps with its reasoning and assumptions:

| Recipe | Steps | Offered when |
|---|---|---|
| Center/scale only (looks already log/normalized) | `row_zscore` | values look log-like / normalised — do **not** log again |
| Total-sum normalize → log2 → z-score | `total_sum` (scale 1e6) → `log2` (pseudocount 1) → `row_zscore` | sample totals differ, values non-negative/skewed |
| Median-scale → log2 | `median_scale` → `log2` (pseudocount 1) | robust alternative when a few features dominate totals |
| log2(x + 1) → z-score | `log2` (pseudocount 1) → `row_zscore` | strong right skew, non-negative values |
| arcsinh (intensity-like) → z-score | `arcsinh` (cofactor 5) → `row_zscore` | intensity-like skew with zeros |
| Filter sparse features → log2 | `filter` (max zero fraction 0.5, drop constant) → `log2` | high zero fraction |
| Z-score for visualization only (negatives present) | `row_zscore` | negative values — no log, no ratio fold change |
| Internal-standard normalization | `internal_standard_features` / `_columns` | you have internal-standard features or columns |

The selected recipe's steps and note are shown under the list. **Apply preprocessing → use processed matrix** applies them; the derived matrix becomes the working table and every step is recorded as a **PreprocessingStep** in the **PreprocessingSpec** (method, parameters, input/output matrix ids, QC before/after, confirmation). **Save before/after QC report…** writes a contact sheet (PDF + PNG) and one vector file per QC plot. **↩ Revert to raw matrix** returns to the source.

### 31. ④ Validation

![Step ④: the validation report for the confirmed mapping and groups.](../../assets/screenshots/desktop_08b_matrix_validation.png)

A read-only report of the confirmed MatrixSpec and metadata: features, samples (value columns), annotation columns, groups with their sizes, missing values, duplicate feature ids and the declared value scale, followed by **ERRORS**, **Warnings** (⚠) — for example sample columns without a group or non-numeric value columns — or *✓ Validation passed*.

### 32. ⑤ Recommend & generate

![Step ⑤: the optional feature-level differential summary, the recommended plots, and the preview / hand-off buttons.](../../assets/screenshots/desktop_08c_matrix_recommend_generate.png)

- **Feature-level differential summary (optional — enables volcano / MA / ranked effect):** choose **Test** (Welch's t, Student's t, Mann-Whitney, paired t, Wilcoxon; ANOVA or Kruskal-Wallis for more groups), **Correction** (Benjamini-Hochberg, Bonferroni, Holm), **Group A** and **Group B**, then **Compute differential summary** (runs in the background; **Cancel** is available). The result is a per-feature table (log2 fold change, p, adjusted p, effect size) that can be saved and that enables volcano and MA recommendations. It is a screen, not DESeq2/edgeR/limma (Part VIII §36).
- **Recommended plots:** a dropdown (Heatmap, PCA, box/violin of selected features, volcano/MA when a summary exists) with a one-line rationale; **Volcano y-axis** → *Adjusted p-value (FDR)* or *Raw p-value*.
- **Open in plot editor** hands the (processed) table, mapping, metadata and provenance to the ordinary editor with full controls; **Quick preview** renders in the dialog.

### 33. Provenance

The exported PlotSpec of a figure generated from the workflow carries the workbook/sheet, the MatrixSpec, the PreprocessingSpec and the metadata assignment under `source`, and the statistics block echoes it, so the figure is traceable to the matrix and the steps that produced it.

## Part VIII — Preprocessing and QC

### 34. Principles

No preprocessing is applied silently. A step is applied only when you add it, and the original matrix is preserved; the output is a new matrix with a new id. Each method below is what its name says; parameters (pseudocount, percentile, reference features…) appear as fields on the step when the method takes any. **No method is universally correct** — the normalisation catalogue lists assumptions and risks for that reason.

### 35. Implemented methods (`available_methods()`)

| Method | What it does | Typical use | Caveats |
|---|---|---|---|
| `log2`, `log10`, `ln`, `log` | logarithm of the values | compress dynamic range of positive intensities | needs positive values (pseudocount parameter) |
| `sqrt`, `arcsinh` | variance-stabilising transforms | counts with zeros (arcsinh tolerates 0) | changes scale, not just spread |
| `cpm` | counts per million per sample; optional log2-CPM with a prior count | count-like data | library-size differences only |
| `total_sum` | divide by each sample's total, rescale | comparable total signal per sample | distorted by dominant features |
| `median_scale` | scale samples so medians match | robust size correction | breaks if most features change |
| `upper_quartile` | scale by the 75th percentile | data with a few dominant features | sensitive to sparsity |
| `quantile` | force identical distributions | technical distribution differences | erases real global shifts |
| `tmm` | TMM-CPM: counts per million using TMM-adjusted effective library sizes (optionally log2) | non-negative count-like data | scaling only; **not** differential inference |
| `voom` | limma-style log-CPM transform of the matrix | preparing counts for linear-model-style summaries | transform only; no DE fitting |
| `internal_standard_features`, `internal_standard_columns`, `control_features`, `reference_sample` | normalise to spike-ins / stable features / control set / a reference sample | targeted assays | an unstable standard propagates error |
| `row_zscore`, `column_zscore`, `zscore`, `global_zscore`, `center`, `standard_scale`, `robust_scale` | centring/scaling by feature, sample or globally | heatmap contrast, PCA input | loses absolute magnitude |
| `filter`, `winsorize`, `impute` | drop low features, clip extremes, fill missing (missing-value policies: keep, drop features, zero, mean impute) | before scaling | alters n or values — recorded |

The **normalisation recommendation catalogue** (total sum, median scale, upper quartile, quantile, row z-score, internal-standard features) states for each: assumptions, risks, suitable/unsuitable data, output scale. Recommendations are advisory and require confirmation.

### 36. QC plots and the differential summary

QC plots: per-sample total signal, per-sample median, per-sample distribution (box), value density, zero fraction, missing fraction, sample-correlation heatmap, PCA of samples, mean–variance trend. All are ordinary figures (exportable) and appear in the before/after report.

**Differential summary** (two groups: Welch's t, Student's t, Mann-Whitney, paired t, Wilcoxon; more groups: ANOVA, Kruskal-Wallis; correction: Benjamini-Hochberg, Bonferroni, Holm) yields per-feature log2 fold change, p, adjusted p and effect size for a *normalised* matrix. **It is a screen, not a count model** — it is not DESeq2, edgeR or limma, and the app labels it so.

## Part IX — Statistics

**Note:** Make My Figure performs calculations; the researcher remains responsible for choosing a scientifically appropriate method. Every method is pinned against SciPy/statsmodels in the test suite; the method sentence names the versions used.

### 37. Where statistics live

Desktop **6. Statistics** (a checkable group) and browser **Statistical tests & annotations**: **Test** (Auto-suggest or one of the 18), **Comparison**, **Group / Subgroup / Subject** columns, **Control group**, **Correction**, **Annotation shows**, **Annotation placement**, **Custom template**, effect-size toggle, hide non-significant, post-hoc after omnibus, p-value decimals, annotation font. **Run statistics** fills the results table (comparison, test, p, adjusted p, effect, n) and the **method sentence**; **Export stats table**, **Export method report**, **Copy method sentence**. Results are written to `name.stats_spec.json` on export.

![Statistics panel with results for the box/violin example.](../../assets/screenshots/desktop_05_statistics.png)

![The box/violin figure after Run statistics: brackets with stars from the stored results.](../../assets/screenshots/desktop_05b_statistics_figure.png)

![Browser: the Statistical tests & annotations expander.](../../assets/screenshots/streamlit_05_statistics.png)

### 38. Methods

**Two-group (unpaired)**

| Method | Input | Assumptions | Output | Effect size |
|---|---|---|---|---|
| Student's t-test | numeric value, two groups | normality, equal variances | t, df, p, CI of the mean difference | Cohen's d |
| Welch's t-test | as above | normality; variances may differ | t, df (Welch), p, CI | Hedges' g |
| Mann-Whitney U | numeric/ordinal, two groups | independent samples | U, p | rank-biserial / Cliff's delta |

**Two-group (paired)** — require **Subject/pair ID**

| Method | Assumptions | Output | Effect size |
|---|---|---|---|
| Paired t-test | normal paired differences | t, df, p, CI of mean difference | Cohen's d_z |
| Wilcoxon signed-rank | symmetric differences | W, p | rank-biserial |

**Multi-group (omnibus)** — three or more groups (two-way / repeated-measures from two)

| Method | Design | Output | Effect size |
|---|---|---|---|
| One-way ANOVA | one factor | F, df, p | eta-squared |
| Two-way ANOVA | group × subgroup | F per term, p | partial eta-squared (approx.) |
| Repeated-measures ANOVA | subject × condition | F, p | partial eta-squared (approx.) |
| Kruskal-Wallis | one factor, non-parametric | H, p | epsilon-squared |
| Dunn's test (post-hoc) | after Kruskal-Wallis | pairwise z, p (corrected) | — |

After an omnibus test, tick **Post-hoc pairwise after omnibus** to add pairwise comparisons with correction.

**Categorical** — two categorical columns (stacked composition, oncoprint)

| Method | Output | Effect size |
|---|---|---|
| Chi-square test | chi², df, p (Yates' continuity correction on 2 × 2 tables) | Cramér's V |
| Fisher's exact test (2 × 2) | p | odds ratio |

**Correlation / regression** — scatter plot

| Method | Output | Effect size |
|---|---|---|
| Pearson correlation | r, p, CI (Fisher z) | r / R² |
| Spearman correlation | rho, p | rho |
| Linear regression | slope, intercept, R², p | R² (fit statistics box on the plot) |
| GLM regression (multi-predictor) | coefficients, p per term | — |

**Survival** — Kaplan-Meier (subject-level input only)

| Method | Output | Effect size |
|---|---|---|
| Log-rank test | chi², p | — |
| Cox proportional hazards | HR, CI, p | hazard ratio |

A log-rank test **cannot** be computed from a precomputed curve (no numbers at risk); the app refuses with a message rather than inventing one.

### 39. Multiple testing

Corrections apply across the family of pairwise comparisons in one run: **Benjamini-Hochberg FDR**, **Bonferroni**, **Holm-Bonferroni**, or **None**. Both raw and adjusted p are stored and either can be shown.

### 40. Annotation on figures

Supported on: bar plot, grouped bar plot (within-x brackets), box/violin (brackets or above-bar), scatter (fit-statistics box), Kaplan-Meier and stacked composition (corner panel). **Not** supported on the line/time-course plot and other types. Content modes: stars, p, adjusted p, p + stars, statistic, effect size, p + statistic, full, flags, or a **custom template** with tokens such as `{p}`, `{p_adj}`, `{stars}` and `{stat_symbol}` (the Custom template field lists the tokens available for the chosen test). Placement: **bracket** between compared categories (auto-stacked) or **above each bar** (comparisons against a control; the control bar stays unmarked). Star thresholds: `*` p < 0.05, `**` p < 0.01, `***` p < 0.001, `****` p < 0.0001; `n.s.` optional. Hiding a value on the figure never removes it from the exported StatsSpec.
