# Plot recommendations

> **Recommendation → full plot editor.** Selecting a recommendation opens it in the
> **same** plot editor as the normal workflow (via a canonical
> `PlotEditorHandoff` — `make_my_figure_core/plots/handoff.py`), with the plot type
> and column mappings pre-populated and every standard control available. The Matrix
> Workflow only prepares the plot-ready data + mappings; it owns no separate plot
> controls. See [MATRIX_WORKFLOW.md](MATRIX_WORKFLOW.md).

`make_my_figure_core.matrix_workflow.recommend_plots(matrix_spec, metadata,
has_differential_summary=..., n_features=...)` returns a ranked list of
`RecommendedPlot` entries for a confirmed matrix. Nothing is auto-generated — the
UI shows the list and you pick one to configure and generate.

Each `RecommendedPlot` carries: `plot_type`, `label`, `reason`,
`required_data_shape`, `required_transformations`, `required_user_inputs`,
`readiness_status`, and scientific/visual warnings.

## Readiness statuses

- `ready` — can generate now.
- `needs_feature_selection` — confirm the matrix mapping first.
- `needs_group_selection` — needs confirmed groups (e.g. group comparisons).
- `needs_transformation` — needs a transform first (e.g. a differential summary
  before a volcano).
- `unavailable` — not applicable to this data.

Entries are ordered ready-first.

## What gets recommended

- **After matrix confirmation:** heatmap, clustered (row z-score) heatmap,
  hierarchical clustering, dendrogram, sample-correlation heatmap, PCA,
  feature-correlation heatmap (manageable feature counts), top-variable-feature
  heatmap. Large matrices carry a visual warning to default to top-variable features.
- **After groups confirmed:** selected-feature box/violin/raincloud/bar by group,
  PCA colored by group (each lists the transform it needs, e.g. `wide_to_long`).
- **After a differential summary:** volcano, MA plot, ranked-effect (waterfall).
  Before one exists these show `needs_transformation` (or `needs_group_selection`)
  and list `feature_differential_summary` as required.

## Precomputed differential tables

`recommend_from_differential_table(has_average_abundance, has_matrix)` covers the
case where you upload a ready-made differential table: volcano, MA plot (if an
average-abundance column exists), ranked-effect, and — when a matrix is also
present — a top-feature heatmap.
