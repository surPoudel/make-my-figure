# Milestone 2 Summary — Make My Figure

Date: 2026-06-30

## What was built

Added the remaining 12 manuscript plot types from `plot_schema_manifest.json`,
bringing the app to **all 17 plot types** in the manifest. Each was implemented
one at a time: renderer → registry/schema wiring → default mapping → Streamlit
UI controls → SVG/PNG/PDF + PlotSpec export → tests → run/fix.

### New renderers (`make_my_figure/plots/`)
| File | plot_type | Notes |
|---|---|---|
| `box_violin.py` | boxplot_or_violin_with_points | box or violin + deterministic jittered points |
| `lineplot.py` | lineplot_timecourse_with_error_band | mean line + SEM/SD/CI band per series |
| `ridge.py` | ridge_or_density_plot | SciPy gaussian_kde ridgelines, adjustable overlap |
| `enrichment.py` | enrichment_dotplot | size=count, color=-log10(FDR), size legend + colorbar |
| `survival.py` | kaplan_meier_survival_curve | KM estimator from scratch (no lifelines), censor ticks |
| `stacked.py` | stacked_bar_composition | pivot to stacked fractions, optional sort-by group |
| `waterfall.py` | waterfall_plot | sorted bars, RECIST reference lines, color by response |
| `pca.py` | pca_scatter_from_matrix | NumPy SVD PCA; matrix + aux metadata; color/shape |
| `oncoprint.py` | oncoprint_mutation_heatmap | gene×sample grid, freq-ordered genes, memo-sorted samples |
| `lollipop.py` | lollipop_mutation_plot | stems + markers sized by count, colored by mutation type |
| `roc.py` | roc_curve | ROC/AUC from scratch, 1–2 models |
| `forest.py` | forest_plot | point estimate + asymmetric CI, log axis, reference line |

### Architecture additions
- **Auxiliary-table support**: `render(..., aux=...)` and `render_to_files(..., aux=...)`
  pass a secondary table (e.g. PCA sample metadata) only to renderers that declare an
  `aux` parameter (detected via `inspect.signature`). Existing renderers are untouched.
- Registry extended: `_RENDERERS`, `_DEFAULT_MAPPINGS`, `_DISPLAY_NAMES` now cover 17 types.
- Streamlit app: all 17 in the sample picker and column-mapping (`COLUMN_FIELDS`),
  per-plot option widgets (kind, overlap, top-N, sort, reference, log axis, error band),
  and a PCA metadata uploader / auto-loaded bundled metadata.

### No third-party heavy deps added
KM, ROC/AUC, and PCA are implemented with NumPy/SciPy already in the stack — no
scikit-learn or lifelines required. Fixed a NumPy 2.0 incompatibility (`np.trapz` →
`np.trapezoid`) in the ROC AUC computation.

## How it was tested

`pytest -q` → **91 passed** (was 42 in Milestone 1).
- The parametrized `plot_case` fixture now renders **all 17 types × 3 styles**, exports
  SVG/PNG/PDF + sidecar, and checks the no-silent-mutation contract.
- `test_renderers_m2.py`: 14 renderer-specific assertions (box/violin kinds, KM
  group/event counts, oncoprint frequency ordering, ROC AUC sanity, PCA explained
  variance + with/without metadata, waterfall sort counts, forest reference, etc.).
- `test_app_smoke.py`: Streamlit `AppTest` now drives the dashboard through **every**
  sample plot type (incl. PCA with bundled metadata) with no exception.
- All 17 example figures regenerated via `scripts/generate_examples.py` and
  spot-checked visually (KM curves, oncoprint grid, ROC with 2 models, PCA group/batch
  separation, forest log-axis, etc.).

## Constraints honored
- No paper harvesting started (per instruction — core app finished first).
- No papers/DOIs/figures/journal rules fabricated; only bundled synthetic mock data.
- Style profiles remain explicitly "*-like" with the disclaimer in metadata and UI.

## Known limitations / Milestone 3 candidates
- Dense point labels can still overlap (volcano, lollipop); a non-overlap label placer
  is the main remaining cosmetic item.
- No multi-panel composition / panel labels (A/B/C) yet; no significance brackets.
- TIFF/EPS are supported by the export layer but only SVG/PNG/PDF are surfaced as
  dashboard download buttons.
- No CLI (`makefig …`) or CI workflow yet; GitHub Pages docs site not built.
- Paper/figure/data **curation pipeline (Phases 4+) intentionally not started.**
