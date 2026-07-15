# Selected panels

13 panels across 6 real public datasets and 10 distinct plot types. Each is generated through Make My Figure (Publication style) and passes scientific + visual QC (>=2 iterations).

| benchmark | dataset | plot type | target panel |
|---|---|---|---|
| penguins_scatter | penguins | scatterplot_with_regression | Fig: bill length vs bill depth by species (Simpson's paradox). |
| penguins_box | penguins | boxplot_or_violin_with_points | Fig: body mass distribution by species with group comparison. |
| penguins_pca | penguins | pca_scatter_from_matrix | Fig: PCA of morphometrics separating species. |
| penguins_heatmap | penguins | heatmap_clustered_matrix | Fig: z-scored morphometric means by species (clustered heatmap). |
| penguins_forest | penguins | forest_plot | Fig: mean body mass by species with 95% CI (forest). |
| karate_network | karate | network_graph | Fig: Zachary karate club social network. |
| iris_roc | iris | roc_curve | Fig: ROC for versicolor-vs-virginica classification. |
| iris_pr | iris | precision_recall_curve | Fig: precision-recall for versicolor-vs-virginica. |
| iris_confusion | iris | confusion_matrix | Fig: 3-class confusion matrix. |
| iris_calibration | iris | calibration_plot | Fig: reliability curve for the virginica probability. |
| wine_pca | wine | pca_scatter_from_matrix | Fig: PCA of wine chemistry separating cultivars. |
| diabetes_scatter | diabetes | scatterplot_with_regression | Fig: disease progression vs BMI. |
| gapminder_scatter | gapminder | scatterplot_with_regression | Fig: life expectancy vs income (2007), by continent. |

See `reports/failed_or_rejected_candidates.md` for categories deferred because a license-clean real dataset was not verified in scope (KM survival, volcano/MA from a precomputed DE table, Manhattan/Q-Q, dose-response, enrichment, oncoprint/lollipop, swimmer/spider). The app supports these plot types; they were not counted here only for lack of a verified-license real dataset.
