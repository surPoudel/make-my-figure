# Legend and colour behaviour, per plot type

Generated from the capability registry and `styling_audit.csv`. A dash means
the plot type does not have that kind of colour or does not draw a legend, so
the control is hidden rather than shown and ignored.

| plot type | legend | categorical palette | per-category override | continuous map | semantic classes |
|---|---|---|---|---|---|
| `barplot_with_error_bar` | no legend in example | yes | yes | — | — |
| `beeswarm_plot` | no legend in example | yes | yes | — | — |
| `bland_altman_plot` | — | yes | — | — | above / within / below LoA |
| `boxplot_or_violin_with_points` | no legend in example | yes | yes | — | — |
| `calibration_plot` | offset exact | yes | — | — | curve / points / reference |
| `chord_diagram` | offset exact | yes | yes | — | — |
| `confusion_matrix` | — | yes | — | yes | — |
| `dose_response_curve` | offset exact | yes | yes | — | — |
| `dot_strip_plot` | no legend in example | yes | yes | — | — |
| `embedding_scatter` | offset exact | yes | yes | yes | — |
| `enrichment_dotplot` | offset exact | yes | — | yes | — |
| `forest_plot` | — | yes | — | — | — |
| `grouped_barplot_with_error_bar` | offset exact | yes | yes | — | — |
| `heatmap_clustered_matrix` | no legend in example | yes | — | yes | — |
| `hierarchical_clustering` | offset exact | yes | — | yes | — |
| `hierarchical_dendrogram` | — | yes | — | — | — |
| `histogram_distribution` | no legend in example | yes | yes | — | — |
| `kaplan_meier_survival_curve` | offset exact | yes | yes | — | — |
| `lineplot_timecourse_with_error_band` | offset exact | yes | yes | — | — |
| `lollipop_mutation_plot` | offset exact | yes | yes | — | — |
| `ma_plot` | offset exact | yes | yes | — | up / down / n.s. |
| `manhattan_plot` | offset exact | yes | yes | — | alternating chromosomes |
| `neighborhood_enrichment_matrix` | no legend in example | yes | — | yes | — |
| `network_graph` | offset exact | yes | yes | yes | — |
| `oncoprint_mutation_heatmap` | offset exact | yes | yes | — | — |
| `paired_slopegraph` | no legend in example | yes | yes | — | — |
| `pca_scatter_from_matrix` | offset exact | yes | yes | — | — |
| `precision_recall_curve` | offset exact | yes | yes | — | — |
| `qq_plot` | — | yes | — | — | — |
| `raincloud_plot` | — | yes | yes | — | — |
| `ridge_or_density_plot` | no legend in example | yes | yes | — | — |
| `roc_curve` | offset exact | yes | yes | — | — |
| `sankey_plot` | — | yes | yes | — | — |
| `scatterplot_with_regression` | offset exact | yes | yes | — | — |
| `spatial_categorical_map` | offset exact | yes | yes | — | — |
| `spatial_composition_map` | offset exact | yes | yes | — | — |
| `spatial_feature_map` | — | yes | — | yes | — |
| `spatial_roi_map` | offset exact | yes | yes | — | — |
| `spatial_transcript_map` | offset exact | yes | yes | — | — |
| `spider_plot` | offset exact | yes | yes | — | — |
| `stacked_bar_composition` | offset exact | yes | yes | — | — |
| `swimmer_plot` | offset exact | yes | yes | — | — |
| `upset_plot` | — | yes | yes | — | set / intersection bars |
| `volcano_plot` | offset exact | — | — | — | up / down / n.s. |
| `waterfall_plot` | offset exact | yes | yes | — | — |
