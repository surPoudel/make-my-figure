# v0.6 Publication Recreation Report

Make My Figure recreates representative **publication-style** panels from **real, permissively-licensed public data**, through the app's normal render path (`registry.render` + the built-in `publication` style). These are **publication-grade, scientifically-traceable recreations — not exact copies** of any published figure image (no figure images are downloaded or stored).

## Executive summary

- Benchmark panels attempted: **13**
- Panels PASSING (scientific QC + visual QC + non-empty PNG/SVG/PDF, ≥2 iterations): **13**
- Distinct plot types covered: **10** — boxplot_or_violin_with_points, calibration_plot, confusion_matrix, forest_plot, heatmap_clustered_matrix, network_graph, pca_scatter_from_matrix, precision_recall_curve, roc_curve, scatterplot_with_regression
- Datasets used: **6** real public datasets (Palmer Penguins CC0, Zachary Karate Club public-domain, Iris/Wine/Diabetes public/BSD via scikit-learn, Gapminder CC BY 4.0).

## Licensing / provenance

| dataset | license | verified |
|---|---|---|
| Ecological sexual dimorphism ... Pygoscelis peng | CC0-1.0 | palmerpenguins package states data released CC0 (with Palmer LTER attr |
| An Information Flow Model for Conflict and Fissi | Public-Domain | Classic public-domain network; bundled in NetworkX (BSD-3). |
| The use of multiple measurements in taxonomic pr | Public-Domain (CC BY 4.0 at UCI) | UCI ML Repository (CC BY 4.0); bundled in scikit-learn (BSD-3). |
| Wine recognition data (UCI) | CC BY 4.0 (UCI) | UCI ML Repository (CC BY 4.0); bundled in scikit-learn (BSD-3). |
| Least Angle Regression (diabetes data) | Public / BSD-3 (scikit-learn) | Standard public regression dataset bundled in scikit-learn (BSD-3). |
| Gapminder (life expectancy, GDP per capita, popu | CC-BY-4.0 | Gapminder data released under CC BY 4.0 (gapminder.org free material). |

## Passing panels

| benchmark | plot type | sci QC | vis QC | iters | DOI/URL |
|---|---|---|---|---|---|
| penguins_scatter | scatterplot_with_regression | PASS | PASS | 2 | 10.1371/journal.pone.0090081 |
| penguins_box | boxplot_or_violin_with_points | PASS | PASS | 2 | 10.1371/journal.pone.0090081 |
| penguins_pca | pca_scatter_from_matrix | PASS | PASS | 2 | 10.1371/journal.pone.0090081 |
| penguins_heatmap | heatmap_clustered_matrix | PASS | PASS | 2 | 10.1371/journal.pone.0090081 |
| penguins_forest | forest_plot | PASS | PASS | 2 | 10.1371/journal.pone.0090081 |
| karate_network | network_graph | PASS | PASS | 2 | 10.1086/jar.33.4.3629752 |
| iris_roc | roc_curve | PASS | PASS | 2 | 10.1111/j.1469-1809.1936.tb02137.x |
| iris_pr | precision_recall_curve | PASS | PASS | 2 | 10.1111/j.1469-1809.1936.tb02137.x |
| iris_confusion | confusion_matrix | PASS | PASS | 2 | 10.1111/j.1469-1809.1936.tb02137.x |
| iris_calibration | calibration_plot | PASS | PASS | 2 | 10.1111/j.1469-1809.1936.tb02137.x |
| wine_pca | pca_scatter_from_matrix | PASS | PASS | 2 | 10.24432/C5PC7J |
| diabetes_scatter | scatterplot_with_regression | PASS | PASS | 2 | 10.1214/009053604000000067 |
| gapminder_scatter | scatterplot_with_regression | PASS | PASS | 2 | https://www.gapminder.org/data/ |

## Scientific QC

Every value/threshold drawn is traced to a source column or a documented computation (see each `recreated_panels/<id>/qc/scientific_qc.md`). Statistical annotations (penguins box plot) come from a stored `StatsReport` (Kruskal–Wallis + Dunn, BH-corrected); model-performance panels (iris ROC/PR/confusion/calibration) use documented 5-fold cross-validated logistic-regression predictions.

## Visual QC

Each panel exports non-empty PNG+SVG+PDF and clears the advisory publication-readiness check (no clipping/overlap). See `recreated_panels/<id>/qc/visual_qc.md`.

## General style improvements

Iteration 2 applies publication polish via **PlotSpec-level** style overrides (legend placement, higher export DPI) — no per-panel or shared-token hacks. See `docs/V0_6_PUBLICATION_STYLE_LESSONS.md`.

## Reference images

**No published figure images are stored** (to avoid figure-copyright risk). Targets are textual panel descriptions; QC is checklist-based (no image-similarity).

## Regenerate

```
python benchmarks/publication_recreation/scripts/download_benchmark_assets.py
python benchmarks/publication_recreation/scripts/curate_benchmark_data.py
python benchmarks/publication_recreation/scripts/recreate_panels.py
python benchmarks/publication_recreation/scripts/evaluate_recreations.py
python benchmarks/publication_recreation/scripts/generate_contact_sheets.py
```

## Limitations

- Recreations use the associated public datasets, not the exact per-figure source tables of arbitrary paywalled papers; targets are described, not image-matched.
- Model-performance panels recompute predictions with a standard documented method (the app plots the resulting tables; it does not claim to reproduce a paper's model).
- Offline runs skip network datasets gracefully (penguins/gapminder cached after first download).
