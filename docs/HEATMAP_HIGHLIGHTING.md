# Heatmap annotation & gene highlighting (v0.5)

The clustered heatmap (`heatmap_clustered_matrix`) supports highlighting and
cluster annotation without leaving the app:

- **Highlight a gene/row list:** set `highlight_rows` to a list of row labels
  (paste a gene list). Highlighted rows are labeled in **bold red** even when
  row labels are otherwise hidden for legibility. `highlight_columns` does the
  same for samples.
- **Show/hide labels:** `show_row_labels` / `show_col_labels` (true/false)
  override the automatic hide-when-crowded behavior.
- **Cluster color strips:** `cluster_k_rows` / `cluster_k_columns` add a
  categorical cluster color strip + legend and export the assignment (see
  HIERARCHICAL_CLUSTERING.md).
- **Sample metadata strips:** `column_annotations` (existing) draws categorical
  tracks above the columns.

If you request many highlighted rows a warning is added; prefer a focused list
or a larger figure size for legibility. Highlight lists match row/column labels
by exact (case-insensitive) name.
