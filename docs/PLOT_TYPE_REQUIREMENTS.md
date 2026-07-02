# Plot Type Requirements

> **Published papers and figures are used only as visual style references** for layout, typography, panel structure, legends, annotations, spacing, and journal-like formatting. The bundled example datasets are **synthetic** unless explicitly marked otherwise. Synthetic examples are not copied from published papers and must not be cited as real biological findings.

Required and optional columns for every supported plot type. Column order does not matter — the app validates by name and type.

### Bar plot with error bars  (`barplot_with_error_bar`)

Compare a mean readout across experimental conditions with replicate error bars.

- **Required columns:**
  - `condition`
  - `replicate`
  - `measurement`
- **Optional columns:**
  - `unit`
  - `experiment_batch`
- **Recommended styles:** nature_like, science_like, cell_like

### Grouped bar plot with error bars  (`grouped_barplot_with_error_bar`)

Two-factor comparison (e.g. genotype x treatment) with grouped bars and error bars.

- **Required columns:**
  - `genotype`
  - `treatment`
  - `replicate`
  - `expression`
- **Optional columns:**
  - `gene`
  - `unit`
- **Recommended styles:** nature_like, science_like, cell_like

### Box / violin plot with points  (`boxplot_or_violin_with_points`)

Show full distributions per group as box or violin plots with overlaid points.

- **Required columns:**
  - `sample_id`
  - `group`
  - `value`
- **Optional columns:**
  - `batch`
  - `sex`
- **Recommended styles:** nature_like, science_like, cell_like

### Scatter plot  (`scatterplot_with_regression`)

Relationship between two continuous variables, colored by group, optional fit line.

- **Required columns:**
  - `sample_id`
  - `x_marker`
  - `y_response`
- **Optional columns:**
  - `group`
  - `label`
- **Recommended styles:** nature_like, science_like, cell_like

### Line / time-course with error band  (`lineplot_timecourse_with_error_band`)

Mean response over time per treatment, with a shaded SEM/CI error band.

- **Required columns:**
  - `time_hours`
  - `treatment`
  - `replicate`
  - `signal`
- **Optional columns:**
  - `unit`
- **Recommended styles:** nature_like, science_like, cell_like

### Clustered heatmap  (`heatmap_clustered_matrix`)

Gene-by-sample expression matrix with optional row/column clustering.

- **Required columns:**
  - `gene`
  - `<sample columns>`
- **Optional columns:**
  - (none)
- **Recommended styles:** nature_like, science_like, cell_like

### Volcano plot  (`volcano_plot`)

Differential expression: log2 fold change vs significance, highlighting hits.

- **Required columns:**
  - `gene`
  - `log2_fold_change`
  - `p_value`
- **Optional columns:**
  - `adjusted_p_value`
  - `gene_class`
  - `label`
- **Recommended styles:** nature_like, science_like, cell_like

### Enrichment dot plot  (`enrichment_dotplot`)

Pathway/term enrichment: dot size = gene count, color = significance.

- **Required columns:**
  - `term`
  - `gene_ratio`
  - `fdr`
- **Optional columns:**
  - `category`
  - `gene_count`
  - `neg_log10_fdr`
- **Recommended styles:** nature_like, science_like, cell_like

### Kaplan-Meier survival curve  (`kaplan_meier_survival_curve`)

Survival probability over time by group, with censoring marks.

- **Required columns:**
  - `sample_id`
  - `group`
  - `time_months`
  - `event`
- **Optional columns:**
  - `censor_reason`
- **Recommended styles:** nature_like, science_like, cell_like

### Stacked composition bar plot  (`stacked_bar_composition`)

Cell-type (or category) composition per sample as stacked fractions.

- **Required columns:**
  - `sample_id`
  - `cell_type`
  - `fraction`
- **Optional columns:**
  - `group`
- **Recommended styles:** nature_like, science_like, cell_like

### Waterfall plot  (`waterfall_plot`)

Best percent change per patient (oncology response), sorted into a waterfall.

- **Required columns:**
  - `patient_id`
  - `best_percent_change`
- **Optional columns:**
  - `treatment_arm`
  - `response_category`
  - `duration_months`
- **Recommended styles:** nature_like, science_like, cell_like

### PCA scatter (matrix + metadata)  (`pca_scatter_from_matrix`)

PCA of an expression matrix; samples colored by group and shaped by batch.

- **Required columns:**
  - `gene`
  - `<sample columns>`
- **Optional columns:**
  - (none)
- **Auxiliary table:** `metadata` (see README)
- **Recommended styles:** nature_like, science_like, cell_like

### Oncoprint mutation heatmap  (`oncoprint_mutation_heatmap`)

Gene-by-sample alteration grid (oncoprint) colored by alteration type.

- **Required columns:**
  - `patient_id`
  - `gene`
  - `alteration_type`
- **Optional columns:**
  - `variant_annotation`
  - `variant_allele_fraction`
- **Recommended styles:** nature_like, science_like, cell_like

### Lollipop mutation plot  (`lollipop_mutation_plot`)

Mutation counts along a protein, as lollipops colored by mutation type.

- **Required columns:**
  - `gene`
  - `protein_position`
  - `sample_count`
- **Optional columns:**
  - `amino_acid_change`
  - `mutation_type`
  - `domain`
- **Recommended styles:** nature_like, science_like, cell_like

### ROC curve  (`roc_curve`)

ROC curves with AUC comparing one or two classifier scores.

- **Required columns:**
  - `sample_id`
  - `true_label`
  - `score_model_a`
- **Optional columns:**
  - `score_model_b`
  - `cohort`
- **Recommended styles:** nature_like, science_like, cell_like

### Forest plot  (`forest_plot`)

Subgroup effect sizes (hazard/odds ratios) with confidence intervals.

- **Required columns:**
  - `subgroup`
  - `hazard_ratio`
  - `ci_low`
  - `ci_high`
- **Optional columns:**
  - `study`
  - `p_value`
  - `n`
- **Recommended styles:** nature_like, science_like, cell_like

### Ridge / density plot  (`ridge_or_density_plot`)

Stacked density (ridgeline) distributions of a value per condition.

- **Required columns:**
  - `cell_id`
  - `condition`
  - `pseudotime`
- **Optional columns:**
  - `sample_id`
  - `score`
- **Recommended styles:** nature_like, science_like, cell_like

## Statistics per plot type

Statistics are optional and configured via the app's Statistics panel (or the
`statistics` block of a PlotSpec). Applicable tests by plot type:

| Plot type | Applicable statistics |
|-----------|-----------------------|
| Bar / Box / Violin | t-tests, Mann–Whitney, paired t / Wilcoxon (with subject ID), one-way ANOVA, Kruskal–Wallis |
| Grouped bar | two-way ANOVA, or pairwise tests within each x category |
| Line / time-course | pairwise tests per timepoint; repeated-measures needs a subject ID |
| Kaplan–Meier | log-rank; Cox hazard ratio |
| Stacked / composition, Oncoprint | chi-square, Fisher's exact |
| Scatter | Pearson, Spearman, linear regression (per group if colored) |
| Volcano | uses supplied p-values; not recomputed |
| Heatmap, PCA, Lollipop, Forest | no automatic tests (descriptive / input statistics) |

See [STATISTICS.md](STATISTICS.md) for required columns and test selection, and
`examples/statistics/` for a worked example of each workflow.
