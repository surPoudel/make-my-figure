# One-publication recreation report

> **This benchmark demonstrates publication-grade recreation from associated data, not pixel-identical reproduction.**

**Publication:** Gorman KB, Williams TD, Fraser WR (2014). Ecological Sexual Dimorphism and Environmental Variability within a Community of Antarctic Penguins (Genus Pygoscelis). PLoS ONE 9(3):e90081.
**DOI:** 10.1371/journal.pone.0090081
**Article license:** CC BY 4.0 · **Data license:** CC0 (Palmer Station LTER, tidied release via palmerpenguins).

## Panels (through Make My Figure, Publication style)
- **3/3 panels pass** scientific + visual QC (>=3 QC iterations each).
- No panel is labelled *exact reproduction*; each is classified honestly below.

| panel | plot type | rows | iters | sci QC | vis QC | classification |
|---|---|---|---|---|---|---|
| A | scatterplot_with_regression | 342 | 3 | PASS | PASS | publication-grade recreation |
| B | boxplot_or_violin_with_points | 342 | 3 | PASS | PASS | publication-grade visualization from the same dataset (not a statistical reproduction) |
| C | pca_scatter_from_matrix | 4 | 3 | PASS | PASS | new visualization from associated data |

## Method-matching table
| panel | published method | app method | same/different | acceptable | reason |
|---|---|---|---|---|---|
| A | culmen (bill) length & depth described by species (morphometric description; no per-panel inferential test) | scatter with per-species OLS trend line (no test) | different | yes | descriptive visualization of the same variables; no statistical claim is made, so the method difference does not misrepresent the paper |
| B | linear models of body mass (species/sex + environmental covariates, e.g. stable-isotope terms) | distribution box + points only; NO statistical brackets | different | yes | the paper's linear-model analysis is not reproduced; brackets were removed and the panel is labelled a visualization, not a statistical reproduction |
| C | no canonical PCA panel of these four morphometrics in the article | PCA of four z-scored morphometrics | n/a (new visualization) | yes | explicitly labelled a new visualization from the associated data, not a recreation of a published panel |

## Visual target table
| panel | reference image stored | textual target | image similarity possible | comparison method |
|---|---|---|---|---|
| A | no | yes | no | checklist against the figure legend / textual target (axes, variables, group order, scale, legend) — no pixel or image-similarity comparison |
| B | no | yes | no | checklist against the figure legend / textual target (axes, variables, group order, scale, legend) — no pixel or image-similarity comparison |
| C | no | yes | no | checklist against the figure legend / textual target (axes, variables, group order, scale, legend) — no pixel or image-similarity comparison |

_Reference-image note:_ PLoS ONE is CC BY 4.0 and would permit storing a cropped, attributed reference panel; we deliberately store description-only to avoid figure-copyright ambiguity and because no image-similarity is claimed.

## Data sources & provenance
- Raw (CC0): palmerpenguins `penguins.csv`, `penguins_raw.csv` (SHA-256 in `raw_data/checksums.json`). Measurements are Gorman et al. 2014 (Palmer LTER).
- Processed: reproducible via `scripts/curate_data.py` (see `processed_data/curation_log.json`). Raw files are never modified.

## Statistics
- **No statistical test from the paper is reproduced.** The paper analyses body mass with linear models (species/sex + environmental covariates); we do not fit that model. Panel B therefore shows only the body-mass distribution with **no** significance brackets/p-values, and is labelled a visualization, not a statistical reproduction. Box summaries (medians/quartiles) trace directly to the data.

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