# Plot gallery - Make My Figure 1.1.1

39 registered plot types, rendered from the bundled synthetic examples with the same renderer the desktop application uses. Column roles are the rows of **2. Map columns** for that plot type. Tutorials appear as they are written; video links are filled from `videos/video_links.json`.

## Basic plots and distributions

| | plot | purpose | column roles | tutorial | video |
|---|---|---|---|---|---|
| <img src="screenshots/gallery/lineplot_timecourse_with_error_band.png" width="160"> | **Line / time-course with error band**<br>`lineplot_timecourse_with_error_band` | Mean response over time per treatment, with a shaded SEM/CI error band | x, y, color, style_by | not yet written | - |
| <img src="screenshots/gallery/ridge_or_density_plot.png" width="160"> | **Ridge / density plot**<br>`ridge_or_density_plot` | Stacked density (ridgeline) distributions of a value per condition | x, group | not yet written | - |
| <img src="screenshots/gallery/histogram_distribution.png" width="160"> | **Histogram (binned distribution)**<br>`histogram_distribution` | Binned counts of one measurement, as separate panels per group or overlaid - shows the distribution's actual shape (modes, gaps, tails) rather than a smoothed curve | x, group, value_columns | not yet written | - |
| <img src="screenshots/gallery/stacked_bar_composition.png" width="160"> | **Stacked composition bar plot**<br>`stacked_bar_composition` | Cell-type (or category) composition per sample as stacked fractions | x, stack, y, facet_or_sort_by | not yet written | - |
| <img src="screenshots/gallery/waterfall_plot.png" width="160"> | **Waterfall plot**<br>`waterfall_plot` | Best percent change per patient (oncology response), sorted into a waterfall | x, y, color | not yet written | - |

## Group comparisons

| | plot | purpose | column roles | tutorial | video |
|---|---|---|---|---|---|
| <img src="screenshots/gallery/barplot_with_error_bar.png" width="160"> | **Bar plot with error bars**<br>`barplot_with_error_bar` | Compare a mean readout across experimental conditions with replicate error bars | x, y, color | not yet written | - |
| <img src="screenshots/gallery/grouped_barplot_with_error_bar.png" width="160"> | **Grouped bar plot with error bars**<br>`grouped_barplot_with_error_bar` | Two-factor comparison (e.g | x, group, y | not yet written | - |
| <img src="screenshots/gallery/boxplot_or_violin_with_points.png" width="160"> | **Box / violin plot with points**<br>`boxplot_or_violin_with_points` | Show full distributions per group as box or violin plots with overlaid points | x, y, hue | [tutorial](plots/boxplot_or_violin_with_points.md) | - |
| <img src="screenshots/gallery/dot_strip_plot.png" width="160"> | **Dot / strip plot**<br>`dot_strip_plot` | Show every observation per group with an optional mean/median summary — a readable alternative to a bar plot | x, y, color | not yet written | - |
| <img src="screenshots/gallery/beeswarm_plot.png" width="160"> | **Beeswarm plot**<br>`beeswarm_plot` | Show every observation per group with a collision-avoiding layout — a readable alternative to a bar plot | x, y, color | not yet written | - |
| <img src="screenshots/gallery/paired_slopegraph.png" width="160"> | **Paired dot plot / slopegraph**<br>`paired_slopegraph` | Connect matched observations across conditions/timepoints (before/after, repeated measures) | subject, condition, value, color | not yet written | - |
| <img src="screenshots/gallery/raincloud_plot.png" width="160"> | **Raincloud plot**<br>`raincloud_plot` | Full distribution per group as a half-violin cloud + box summary + raw points | x, y | not yet written | - |

## Relationships, regression and classifier curves

| | plot | purpose | column roles | tutorial | video |
|---|---|---|---|---|---|
| <img src="screenshots/gallery/scatterplot_with_regression.png" width="160"> | **Scatter plot**<br>`scatterplot_with_regression` | Relationship between two continuous variables, colored by group, optional fit line | x, y, color, label | [tutorial](plots/scatterplot_with_regression.md) | - |
| <img src="screenshots/gallery/roc_curve.png" width="160"> | **ROC curve**<br>`roc_curve` | ROC curves with AUC comparing one or two classifier scores | label, score, score2 | not yet written | - |
| <img src="screenshots/gallery/bland_altman_plot.png" width="160"> | **Bland-Altman (method agreement)**<br>`bland_altman_plot` | Agreement between two measurement methods (bias and limits of agreement) | method_a, method_b, label | not yet written | - |
| <img src="screenshots/gallery/precision_recall_curve.png" width="160"> | **Precision-recall curve**<br>`precision_recall_curve` | Precision vs recall for one or two classifiers on an imbalanced outcome, with average precision (AUPRC) | label, score, score2 | not yet written | - |
| <img src="screenshots/gallery/confusion_matrix.png" width="160"> | **Confusion matrix**<br>`confusion_matrix` | Classification confusion matrix (binary or multiclass) with optional row/column/total normalization | true, predicted | not yet written | - |
| <img src="screenshots/gallery/calibration_plot.png" width="160"> | **Calibration plot**<br>`calibration_plot` | Reliability of a clinical risk model: predicted vs observed probability, binned, with a perfect-calibration diagonal | label, prob | not yet written | - |
| <img src="screenshots/gallery/dose_response_curve.png" width="160"> | **Dose-response curve**<br>`dose_response_curve` | Drug dose-response with a 4-parameter logistic fit and EC50/IC50 per group | dose, response, group | not yet written | - |

## Matrices, dimension reduction and differential results

| | plot | purpose | column roles | tutorial | video |
|---|---|---|---|---|---|
| <img src="screenshots/gallery/heatmap_clustered_matrix.png" width="160"> | **Clustered heatmap**<br>`heatmap_clustered_matrix` | Gene-by-sample expression matrix with optional row/column clustering | row_id | [tutorial](plots/heatmap_clustered_matrix.md) | - |
| <img src="screenshots/gallery/volcano_plot.png" width="160"> | **Volcano plot**<br>`volcano_plot` | Differential expression: log2 fold change vs significance, highlighting hits | x, p, label, id_col | [tutorial](plots/volcano_plot.md) | - |
| <img src="screenshots/gallery/enrichment_dotplot.png" width="160"> | **Enrichment dot plot**<br>`enrichment_dotplot` | Pathway/term enrichment: dot size = gene count, color = significance | y, x, size, color | not yet written | - |
| <img src="screenshots/gallery/pca_scatter_from_matrix.png" width="160"> | **PCA scatter (matrix + metadata)**<br>`pca_scatter_from_matrix` | PCA of an expression matrix; samples colored by group and shaped by batch | matrix_row_id | not yet written | - |
| <img src="screenshots/gallery/hierarchical_dendrogram.png" width="160"> | **Hierarchical clustering dendrogram**<br>`hierarchical_dendrogram` | Hierarchical clustering of a feature-by-sample matrix as a standalone dendrogram | row_id | not yet written | - |
| <img src="screenshots/gallery/ma_plot.png" width="160"> | **MA plot (differential expression)**<br>`ma_plot` | Differential expression: average abundance (A) vs log fold change (M), colored by significance | x, y, p, label, id_col | not yet written | - |
| <img src="screenshots/gallery/manhattan_plot.png" width="160"> | **Manhattan plot (GWAS)**<br>`manhattan_plot` | Genome-wide association -log10(p) across chromosomes with significance thresholds | chrom, pos, p, snp | not yet written | - |
| <img src="screenshots/gallery/qq_plot.png" width="160"> | **Q-Q plot (p-value / quantile)**<br>`qq_plot` | Observed vs expected -log10(p) Q-Q plot with genomic inflation (lambda) | p | not yet written | - |
| <img src="screenshots/gallery/embedding_scatter.png" width="160"> | **UMAP / t-SNE embedding scatter**<br>`embedding_scatter` | Single-cell / sample embedding (UMAP or t-SNE) colored by cluster or metadata | x, y, color, shape, label | not yet written | - |
| <img src="screenshots/gallery/hierarchical_clustering.png" width="160"> | **Hierarchical clustering (heatmap + clusters)**<br>`hierarchical_clustering` | Cluster a feature-by-sample matrix into k groups and export the cluster assignment table | row_id | not yet written | - |

## Survival, effect estimates and clinical timelines

| | plot | purpose | column roles | tutorial | video |
|---|---|---|---|---|---|
| <img src="screenshots/gallery/kaplan_meier_survival_curve.png" width="160"> | **Kaplan-Meier survival curve**<br>`kaplan_meier_survival_curve` | Survival probability over time by group, with censoring marks | time, event, group, survival_columns | [tutorial](plots/kaplan_meier_survival_curve.md) | - |
| <img src="screenshots/gallery/forest_plot.png" width="160"> | **Forest plot**<br>`forest_plot` | Subgroup effect sizes (hazard/odds ratios) with confidence intervals | label, estimate, lower, upper | not yet written | - |
| <img src="screenshots/gallery/swimmer_plot.png" width="160"> | **Swimmer plot**<br>`swimmer_plot` | Per-patient treatment/follow-up timelines (oncology), colored by response with event markers | subject, start, end, duration, event, group | not yet written | - |
| <img src="screenshots/gallery/spider_plot.png" width="160"> | **Spider plot (longitudinal change)**<br>`spider_plot` | Longitudinal per-patient change over time (e.g | subject, time, value, group | not yet written | - |

## Specialised plots

| | plot | purpose | column roles | tutorial | video |
|---|---|---|---|---|---|
| <img src="screenshots/gallery/oncoprint_mutation_heatmap.png" width="160"> | **Oncoprint mutation heatmap**<br>`oncoprint_mutation_heatmap` | Gene-by-sample alteration grid (oncoprint) colored by alteration type | sample, row, fill | not yet written | - |
| <img src="screenshots/gallery/lollipop_mutation_plot.png" width="160"> | **Lollipop mutation plot**<br>`lollipop_mutation_plot` | Mutation counts along a protein, as lollipops colored by mutation type | x, y, color, label | not yet written | - |
| <img src="screenshots/gallery/upset_plot.png" width="160"> | **UpSet plot (set intersections)**<br>`upset_plot` | Intersections among many sets (a scalable alternative to Venn diagrams) | chosen in Map columns | not yet written | - |
| <img src="screenshots/gallery/sankey_plot.png" width="160"> | **Sankey / alluvial flow (two-stage)**<br>`sankey_plot` | Flow between two sets of categories (e.g | source, target, value | not yet written | - |
| <img src="screenshots/gallery/network_graph.png" width="160"> | **Network graph**<br>`network_graph` | Interaction / co-expression network: nodes are genes/features, edges are interactions or correlations, colored by module and sized by degree | source, target, weight, interaction_type | not yet written | - |
| <img src="screenshots/gallery/chord_diagram.png" width="160"> | **Circos-style chord diagram**<br>`chord_diagram` | Ligand-receptor interaction counts between cell types drawn as a Circos-style chord diagram: one segment per cell type sized by its total interactions, ribbons sized by the count of each pair, and a compartment band on the outside | source, target, value, group | not yet written | - |
