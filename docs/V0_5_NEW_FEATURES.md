# v0.5 — networks, annotations, docking & clustering

v0.5 builds on the v0.4 plot-type expansion (37 plot types total) and focuses on
**making figures publication-ready and interactive to refine**: a network graph,
a universal manual annotation layer, richer volcano/heatmap labelling, full
hierarchical clustering with k-cluster assignment, and pop-out desktop panels.

> Clustering and network visualizations are **exploratory summaries**. Users are
> responsible for interpreting biological meaning and confirming that chosen
> distance metrics, thresholds, and filters are appropriate.

## New plot types (2)

| Plot type (`id`) | Category | Required | Optional | Notes |
|---|---|---|---|---|
| Network graph (`network_graph`) | Set overlap, flow, and networks | edge list `source`, `target` (or adjacency matrix, or correlation `source`/`target`/`correlation`) | `weight`, `interaction_type`, node table (`node`, `group`, `value`); layout/filter options | NetworkX layouts, filtering, centrality metrics + exportable edge/node tables. See [NETWORK_GRAPH.md](NETWORK_GRAPH.md) |
| Hierarchical clustering (`hierarchical_clustering`) | High-dimensional / omics | label column + numeric sample columns | `cluster`, `k`, `scale`, `distance_metric`, `linkage_method` | Cuts the tree into k clusters, draws a cluster color strip, exports the assignment table. See [HIERARCHICAL_CLUSTERING.md](HIERARCHICAL_CLUSTERING.md) |

*(The other 18 manuscript plot types shipped in v0.4 — see [V0_4_NEW_PLOT_TYPES.md](V0_4_NEW_PLOT_TYPES.md).)*

## Universal manual annotations
A reproducible annotation layer (`spec['annotations']`) that works on any plot:
free text, arrows, callouts, highlight boxes / regions, brackets, and reference
lines, anchored in data / axes / figure coordinates and drawn as editable vector
artists. See [ANNOTATIONS.md](ANNOTATIONS.md).

## Volcano annotation controls
Labels on/off, six label modes (top-FDR, top-|log2FC|, top up+down, selected,
pasted gene list, all-significant), arrows from displaced labels, label boxes,
colors, and an automatic `Up: N | Down: N | FDR < c, |log2FC| >= c` subtitle.
See [VOLCANO_ANNOTATIONS.md](VOLCANO_ANNOTATIONS.md).

## Heatmap highlighting & clustering
Highlight a pasted gene/sample list (bold labels even when others are hidden),
show/hide labels, cluster color strips with k selection, scaling and
distance/linkage options. See [HEATMAP_HIGHLIGHTING.md](HEATMAP_HIGHLIGHTING.md)
and [HIERARCHICAL_CLUSTERING.md](HIERARCHICAL_CLUSTERING.md).

## Hierarchical clustering suite
Clustered heatmap + standalone dendrogram + a clustering-result view that cuts
into `k` clusters, adds a cluster assignment column, color strips, and exports
the assignment table and a cluster summary.

## Pop-out / pop-in desktop panels
Detach the Figure, Data & Messages, or Plot Controls panels into floating
windows (multi-monitor), dock them back with state preserved, and persist the
layout via `QSettings`. See [POP_OUT_PANELS.md](POP_OUT_PANELS.md).

## Integrity & limitations
- No fabricated statistics: p-values are read verbatim; network centrality /
  clustering are computed with SciPy/NetworkX and clearly labelled exploratory.
- Correlation networks are labelled as association, not mechanistic interaction.
- Network rendering is static; community detection is a documented heuristic;
  centrality is skipped above 500 nodes.
- Precomputed distance-matrix clustering input and multi-stage alluvial are
  future work; embedding takes precomputed coordinates only.
- Desktop pop-out is additive (reparenting, not `QDockWidget`); statistics /
  annotation controls pop out with the Controls column.
