# Changelog

All notable changes to Make My Figure are recorded here.

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
