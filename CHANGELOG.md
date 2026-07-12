# Changelog

All notable changes to Make My Figure are recorded here.

## [0.5.3] — grouped heatmaps + cleaner "Define groups"

### Fixed
- **"Define groups" listed non-sample columns.** The wide-matrix group assignment
  showed every non-id column (including RNA-seq annotation columns like
  `geneSymbol` / `bioType` / `annotationLevel`) and auto-assigned each a group.
  Now only **numeric** columns are offered as samples (text annotation columns are
  dropped), groups start **blank** (assign only your real samples; anything left
  blank — e.g. a numeric annotation column — is excluded), and "Auto-guess from
  names" is opt-in.
- **Heatmap showed nothing after grouping.** Grouping only reshaped to *long*,
  which collapses a heatmap to a single "value" column. The Define-groups dialog
  now has an output choice: **long** (bar/box/violin) or **wide** (heatmap/PCA).
  Wide keeps the matrix (assigned samples only) and adds a **group color strip**,
  so a grouped heatmap actually renders. Verified end-to-end on a real 12-sample /
  55k-gene RSEM matrix + metadata.

### Added
- `grouping.numeric_sample_columns()` and `grouping.wide_grouped_matrix()`
  (returns the wide matrix + a column-annotation group strip); controller
  `group_from_matrix_wide()` / `numeric_sample_columns()`.

## [0.5.2] — memory guards for large matrices + RNA-seq parsing

### Fixed
- **Out-of-memory on large matrices.** Hierarchical clustering builds an O(n²)
  distance matrix, so a big feature axis (e.g. a ~55k-gene RSEM count table)
  exhausted RAM and crashed the app. The clustered heatmap, standalone
  dendrogram, and hierarchical-clustering plot now **cap the feature (row) axis
  to the top-N most variable rows** (default 2,000, configurable via
  `max_features`) before clustering/display, with a clear warning. Highlighted
  rows are always kept. PCA is unaffected (it SVDs the small samples×features
  orientation — no O(n²) — and was already memory-safe).
- **RNA-seq matrices with annotation columns.** Count matrices commonly carry
  columns like `geneSymbol` / `bioType` / `annotationLevel` before the samples.
  The heatmap/dendrogram/hierarchical-clustering now drop non-numeric annotation
  columns automatically and accept an `exclude_columns` list for numeric-looking
  ones; they also report exactly which columns were used as samples. PCA now
  restricts to the columns present in the metadata's sample-id column, so
  annotation columns are no longer mistaken for samples.

### Notes
- Defaults preserve prior output for normal-sized matrices. For a readable
  publication heatmap, subsetting to top-variable genes was already best practice;
  this just makes it automatic and memory-safe instead of crashing.

## [0.5.1] — click to identify / label points

### Added
- **Click-to-identify / click-to-label** on the desktop live canvas for **volcano**
  and **scatter** plots: enable *"Click a point to identify / label it"* (Labels &
  size), then click near a point to see its gene/sample name + coordinates in the
  status bar and toggle a label on it. Added labels are stored in the PlotSpec
  (`mapping.selected_labels`) so they persist on export/reload; click again to
  remove. Picks are kept per plot type and reset on new data.
- Core (GUI-independent) helpers: `build_pickable_points`, `nearest_pickable`,
  `choose_label_column`, `resolve_point_labels`; renderers emit
  `metadata['pickable_points']` + `pick_label_column`. Scatter now honors
  `selected_labels` (label only the chosen points).

### Notes
- Interactive desktop feature — exports remain static; only the labels you add
  persist. Covers volcano + scatter (other plot types label by name). No
  drag-to-reposition. The Qt click handler is additive/guarded but should be
  smoke-tested in the desktop app.

## [0.5.0] — networks, annotations, docking & clustering

Builds on v0.4 (37 plot types total). Focus: publication-ready, refine-in-app
figures. No breaking changes — existing plots, statistics annotations, exports,
PlotSpec, desktop app, and Streamlit app are unchanged.

### Added — plot types
- **Network graph** (`network_graph`): edge-list / adjacency-matrix /
  correlation-network inputs; spring/kamada-kawai/circular/shell/spectral/
  multipartite/fixed layouts (reproducible via a stored seed); filtering
  (weight, |r|, p/FDR, top-N edges/nodes, min degree, remove isolates); node
  metrics (degree, betweenness/closeness/eigenvector centrality) and a network
  summary; exportable filtered edge + node-metric tables. NetworkX-based.
- **Hierarchical clustering** (`hierarchical_clustering`): cut the tree into `k`
  clusters, cluster color strip, exported cluster-assignment table + summary;
  scaling (row/col z-score, center, log) and distance/linkage options.

### Added — annotations
- **Universal manual annotation layer** (`spec['annotations']`,
  `make_my_figure_core/annotations.py`): text, arrow, callout, box, region,
  bracket, and reference lines in data/axes/figure coordinates, drawn as vector
  artists and applied to every plot type through the central render path.

### Changed — annotations & clustering on existing plots
- **Volcano**: labels on/off, six label modes (top-FDR / top-|log2FC| / top
  up+down / selected / pasted list / all-significant), displaced-label arrows,
  label boxes/colors/size, auto `Up/Down/FDR` subtitle, and a max-labels warning.
- **Heatmap**: scaling + distance/linkage options, `cluster_k_rows` /
  `cluster_k_columns` color strips with exported assignments, `sort_by_cluster`,
  and gene/sample highlighting via a pasted list (bold labels when others hidden).

### Added — desktop
- **Pop-out / pop-in panels** (`apps/desktop_app/panels_dock.py`): detach the
  Figure, Data & Messages, or Plot Controls panels to floating (multi-monitor)
  windows and dock them back with state preserved; View-menu actions + Dock All;
  layout persisted via `QSettings`. Additive (reparenting, not `QDockWidget`).

### Added — supporting
- Shared `make_my_figure_core/clustering.py` (scaling, metric/linkage validation,
  k-cut, assignment table, color mapping, summary).
- `networkx` and `adjustText` added as dependencies.
- Docs: `V0_5_NEW_FEATURES.md`, `NETWORK_GRAPH.md`, `ANNOTATIONS.md`,
  `VOLCANO_ANNOTATIONS.md`, `HEATMAP_HIGHLIGHTING.md`, `HIERARCHICAL_CLUSTERING.md`,
  `POP_OUT_PANELS.md`; example data for the new types (incl. edge-list /
  adjacency / correlation network files); v0.5 visual QA gallery.

## [0.4.0] — manuscript plot-type expansion

Adds **18 new plot types** (17 → 35) covering a much broader range of
publication figures, wired through the existing registry, validation, style,
publication-readiness check, and export/sidecar systems. No breaking changes:
all existing plot types, statistics annotations, exports, and app navigation are
unchanged.

### Added — new plot types
- **Group comparison & distributions:** dot / strip plot, beeswarm plot, paired
  dot plot / slopegraph, raincloud plot.
- **Relationships & trends:** dose-response curve (4PL fit + EC50/IC50), spider
  plot (longitudinal per-patient change).
- **High-dimensional / omics:** hierarchical clustering dendrogram, MA plot,
  UMAP / t-SNE embedding scatter (precomputed coordinates).
- **Genomics & variants:** Manhattan plot (genome-wide + suggestive lines),
  Q-Q plot (p-value with genomic inflation λ, or quantile mode).
- **Clinical & survival:** swimmer plot.
- **Model performance:** precision-recall curve (AUPRC), confusion matrix
  (counts / row / column / total normalization), calibration plot (Brier score).
- **Set overlap & flow:** UpSet plot, Sankey / alluvial (two-stage).
- **Method comparison / QC:** Bland-Altman plot.

### Added — supporting
- `make_my_figure_core/plots/_v04_shared.py`: shared helpers (matrix parsing,
  hierarchical linkage, jitter / quasi-beeswarm, summary overlays, flexible
  column detection, −log10(p)); numpy/scipy only — no new dependencies.
- A bundled synthetic example dataset + PlotSpec for every new plot type
  (regenerate via `scripts/generate_example_data.py`).
- `scripts/generate_v04_qa_gallery.py`: renders each new plot and a contact
  sheet to `reports/v04_qa/` for visual QA.
- `docs/V0_4_NEW_PLOT_TYPES.md`: use cases, required/optional columns, and
  documented limitations for every new type.
- `tests/test_v04_plots.py`: per-type render, export, no-mutation, validator,
  and publication-readiness tests, plus metadata-correctness checks.

### Integrity
- No fabricated statistics: AUPRC, accuracy, Brier score, IC50/EC50, and genomic
  inflation λ are computed only from valid inputs and otherwise omitted with a
  warning. Differential-expression p-values are read verbatim, never recomputed.
- Documented limitations: quasi-beeswarm (not force-directed); two-stage Sankey
  only; embedding takes precomputed coordinates (no `.h5ad`/AnnData yet);
  dendrogram computes linkage from the matrix (no precomputed-linkage input yet);
  UpSet shows the top 20 intersections.

## [0.3.0]
- Multi-panel Figure Builder: live preview, per-panel size (inches), figure-wide
  font controls, and undistorted (letterboxed) panel scaling; per-panel titles
  off by default.

## [0.2.0]
- Figure-first workflow; in-app grouping; volcano from a DE-result table with
  confirmable columns.

## [0.1.0]
- First desktop release.
