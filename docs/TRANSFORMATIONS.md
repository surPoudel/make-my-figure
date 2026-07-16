# Matrix transformations

`make_my_figure_core.matrix_workflow.transformations` — reproducible, named
transformations over a confirmed `MatrixSpec`. Each returns a **new** derived
frame plus a `TransformationSpec` (`transformation_type`, `parameters`,
`warnings`, `reversible`, `user_confirmed`); none mutate the input, and none are
applied silently — the UI shows the derived dataset before plotting.

| Function | Output | Key parameters |
|---|---|---|
| `wide_to_long` | long: `feature_id`, `feature_label`, annotations, `sample_id`, `value`, `group` | uses metadata groups |
| `row_zscore` / `column_zscore` | standardized matrix | `ddof`; zero-variance rows → 0 (warned) |
| `top_variable_features` | most-variable feature subset | `top_n`, `method` (`variance`/`iqr`/`mad`) |
| `group_means` | per-feature group means ± error | `stat` (mean/median), `error` (sd/sem/ci95) |
| `sample_correlation` | sample×sample correlation | `method` (pearson/spearman) |
| `feature_correlation` | feature×feature correlation | `method`, `max_features` (capped, warned) |
| `distance_matrix` | sample×sample distance | `metric` (euclidean/correlation/cosine/cityblock) |
| `compute_pca` | scores (`sample_id`, `PC1…`); variance + loadings in spec | `n_components`, `scale` |
| `hierarchical_clustering` | matrix + optional `cluster` column; row/col order in spec | `metric`, `method`, `k`, cluster flags |

Fold-change / differential summary is documented separately in
[FEATURE_LEVEL_STATISTICS.md](FEATURE_LEVEL_STATISTICS.md).

The raw uploaded data is always preserved; a derived dataset is a named artifact
you can inspect, export, and reproduce from its `TransformationSpec`.
