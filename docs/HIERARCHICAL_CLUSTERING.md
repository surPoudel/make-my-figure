# Hierarchical clustering (v0.5)

Make My Figure supports hierarchical clustering three ways, all sharing one
engine (`make_my_figure_core/clustering.py`):

1. **Clustered heatmap** (`heatmap_clustered_matrix`) — exploratory display with
   optional cluster color strips.
2. **Standalone dendrogram** (`hierarchical_dendrogram`) — the tree only.
3. **Hierarchical clustering result** (`hierarchical_clustering`) — clusters into
   *k* groups, shows the ordered matrix with a cluster color strip, and **exports
   a cluster-assignment table**.

> Clustering and the resulting groups are an **exploratory summary**. You are
> responsible for confirming the distance metric, linkage, scaling, and k are
> appropriate for your data and for interpreting biological meaning.

## Input
A features x samples matrix: the first column is the row label (e.g. `gene`);
every other column is a numeric sample. Missing values are imputed (row mean →
0) for distance computation and shown as blank cells.

## Options
| Option | Choices | Default | Notes |
|---|---|---|---|
| `cluster` | rows / columns | rows | which axis to cluster + assign |
| `k` | 2 … n | 3 | number of clusters (cut the tree) |
| `scale` | none / row_zscore / column_zscore / center_rows / log | row_zscore | applied before clustering + display |
| `distance_metric` | euclidean / correlation / cosine / cityblock | euclidean | |
| `linkage_method` | average / complete / single / ward | average | **ward requires euclidean** |
| `cluster_prefix` | text | Cluster | label prefix (Cluster 1, Cluster 2, …) |

For the **clustered heatmap**, the same `scale` / `distance_metric` /
`linkage_method` apply, plus `cluster_k_rows`, `cluster_k_columns` (0 = off),
`sort_by_cluster`, and highlighting (see HEATMAP_HIGHLIGHTING.md).

## k-cluster behavior
Selecting `k` cuts the dendrogram into k clusters and:
- adds a new **cluster assignment** per object (`Cluster 1…k`),
- draws a cluster **color strip** on the clustered axis with a legend,
- exports the **assignment table** in the render metadata
  (`cluster_assignment`; `row_assignment`/`column_assignment` on the heatmap),
- records a **cluster summary** (`cluster_summary` / `row_clusters` /
  `column_clusters`): number and size of clusters + the parameters used.

## Exporting cluster assignments
The `hierarchical_clustering` plot puts the full table on
`metadata["cluster_assignment"]` (records): `feature`/`sample`, `cluster`,
`cluster_id`, `dendrogram_order`, and `mean_value` (row clustering). The app can
save this alongside the figure.

## Validation / friendly errors
- A numeric matrix is required (label column + ≥1 numeric column).
- `k` must be an integer in `[2, n_objects]`.
- Ward linkage with a non-euclidean metric is rejected with a clear message.
- Constant rows and NaNs are handled (nudged / imputed) rather than crashing.

## Limitations / TODO
- Precomputed distance-matrix input is not yet supported (distances are computed
  from the matrix).
- On the result view, only the selected axis drives cluster assignment; the
  other axis is ordered by best-effort clustering for a clean display.

## Large matrices & RNA-seq count tables (v0.5.2)

Hierarchical clustering builds an O(n²) distance matrix, so clustering a huge
feature axis (e.g. a ~55,000-gene RSEM count table) can exhaust RAM. To stay
safe and readable:

- The clustered heatmap, dendrogram, and hierarchical-clustering plot **cap the
  feature (row) axis to the top-N most variable rows** (default **2,000**, set
  via `max_features`) before clustering, with a warning. Any `highlight_rows`
  you specify are always kept. Pre-filtering to your genes of interest is still
  the best practice for a readable figure.
- **Annotation columns** common in count matrices (`geneSymbol`, `bioType`,
  `annotationLevel`, …) are handled: non-numeric ones are dropped automatically,
  and you can drop numeric-looking ones with **`exclude_columns`** (e.g.
  `["annotationLevel"]`). The plot reports which columns it used as samples.
- **PCA** is memory-safe even at 55k genes and, when you supply a metadata table,
  uses only the columns whose names match the metadata's sample-id column — so
  annotation columns are never mistaken for samples. Log-transform raw counts
  (`scale: log`) for a more meaningful PCA/heatmap.
