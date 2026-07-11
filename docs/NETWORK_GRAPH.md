# Network graph (v0.5)

Node-link diagram of an interaction, co-expression, or correlation network,
built with NetworkX and exported as vector-safe SVG/PDF/PNG.

> A **correlation network** encodes statistical association, **not** a
> mechanistic interaction — the figure caption says so automatically.
> Network visualizations are exploratory summaries; you are responsible for
> confirming thresholds/filters and interpreting biological meaning.

## Input modes

| Mode | `mapping.mode` | Required | Optional |
|---|---|---|---|
| Edge list (default) | `edge_list` | `source`, `target` | `weight`, `interaction_type`, `sign`, `p_value`/`adjusted_p_value`, `group` |
| Adjacency matrix | `adjacency` | first column = node labels; remaining numeric columns = weights | `min_weight` threshold |
| Correlation network | `correlation` | `source`, `target`, `correlation` | `corr_cutoff`, `sign_filter` (both/positive/negative), `p_value` |

### Node attributes (optional)
Provide a second table (`nodes.csv`, exposed to the app as an auxiliary table)
with columns `node` + any of `group`/`module`/`community`, `value`/`size`,
`color_value`. Nodes are **sized** by degree (default) or a numeric column, and
**colored** by group (categorical palette + legend) or a continuous value
(sequential colormap + colorbar).

## Layouts
`spring` (default, force-directed), `kamada_kawai`, `circular`, `shell`,
`spectral`, `multipartite` (needs a group/layer column), `fixed` (node `x`/`y`
columns), `random` (fallback). Randomized layouts use `mapping.seed` (default
42) and the seed is recorded in the PlotSpec + metadata, so layouts are
reproducible.

## Filtering
`min_weight`, `corr_cutoff` (|r|), `p_cutoff` (p/FDR), `top_n_edges`,
`min_degree`, `top_n_nodes`, `remove_isolates`. The app warns when a network is
very dense (>300 nodes, >1500 edges, or density > 0.5) and thins node labels to
the top-N by degree so the figure stays readable.

## Metrics & export
Computed and exported: node/edge counts, density, connected components, largest
component size; per-node degree, weighted degree, and (for ≤500 nodes)
betweenness/closeness/eigenvector centrality. Optional community detection
(`detect_communities`) uses greedy modularity (**heuristic**). Exports: the
filtered edge table, a node-metrics table, and a `network_summary` in the
PlotSpec sidecar.

## Styling defaults
Clean white background, colorblind-safe palette, high-contrast node outlines,
subtle alpha edges (width ∝ weight), node size ∝ degree/value, legend outside
the plot, no clipped labels, vector-safe export.

## Limitations
Static (non-interactive) rendering; two-node edges only (no hyperedges);
community detection is heuristic; centrality is skipped above 500 nodes for cost.
