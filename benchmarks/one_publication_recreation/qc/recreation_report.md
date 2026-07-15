# One-publication recreation report

**Publication:** Gorman KB, Williams TD, Fraser WR (2014). Ecological Sexual Dimorphism and Environmental Variability within a Community of Antarctic Penguins (Genus Pygoscelis). PLoS ONE 9(3):e90081.
**DOI:** 10.1371/journal.pone.0090081
**Article license:** CC BY 4.0 · **Data license:** CC0 (Palmer Station LTER, tidied release via palmerpenguins).

## Panels recreated (through Make My Figure, Publication style)
- **3/3 panels pass** scientific + visual QC (>=3 QC iterations each).

| panel | plot type | rows | iters | sci QC | vis QC |
|---|---|---|---|---|---|
| A | scatterplot_with_regression | 342 | 3 | PASS | PASS |
| B | boxplot_or_violin_with_points | 342 | 3 | PASS | PASS |
| C | pca_scatter_from_matrix | 4 | 3 | PASS | PASS |

## Data sources & provenance
- Raw (CC0): palmerpenguins `penguins.csv`, `penguins_raw.csv` (SHA-256 in `raw_data/checksums.json`). Measurements are Gorman et al. 2014 (Palmer LTER).
- Processed: reproducible via `scripts/curate_data.py` (see `processed_data/curation_log.json`). Raw files are never modified.

## Statistics verified
- Panel B body-mass comparison: pairwise Mann-Whitney U (BH-corrected), every value drawn from a stored `StatResult` via `run_statistics`. Adelie vs Chinstrap n.s.; both vs Gentoo highly significant (Gentoo is the heavy species).

## Figure Builder
- Panels A/B/C assembled via `make_my_figure_core.panels.build_figure` into a labelled 2x2 layout; exported PNG/SVG/PDF + `figure_builder/figure_spec.json`.

## Reference images
- **None stored.** Article is CC BY but we keep only citation + figure number + textual target descriptions (see `source/figure_targets.md`); no image-similarity was computed.

## Known differences / limitations
- Panel B uses a standard nonparametric pairwise test, not the paper's linear models (documented per-panel). PCA sign/rotation is arbitrary. Colours/limits are Publication defaults, not the paper's exact styling. See each panel's `differences_from_published.md`.

## Honest conclusion
**Publication-grade recreation** — scientifically traceable to the associated CC0 data and visually publication-grade, but not pixel-identical (no reference image; some analyses are standard equivalents of the paper's models).

## Reproduce
```
python benchmarks/one_publication_recreation/scripts/download_data.py
python benchmarks/one_publication_recreation/scripts/curate_data.py
python benchmarks/one_publication_recreation/scripts/recreate_panels.py
python benchmarks/one_publication_recreation/scripts/assemble_figure_builder.py
python benchmarks/one_publication_recreation/scripts/evaluate_recreation.py
python -m pytest tests/test_one_publication_recreation.py -q -p no:pytest-qt
```