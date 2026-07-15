# Ten-publication recreation — report

**10 publications, 10 distinct plot types.** All render through Make My Figure (Publication style) and pass per-panel scientific + visual QC. No copyrighted figure images are stored; no panel claims exact reproduction.

| # | publication | year | plot type | data license | sci | vis | classification |
|---|---|---|---|---|---|---|---|
| 1 | Cascading classifiers (Optical Recogniti (Alpaydin E, Kayn) | 1998 | calibration_plot | public domain (UCI); sciki | PASS | PASS | publication-grade visualization from associated data (Brie |
| 2 | Covariance analysis of heart transplant  (Crowley J, Hu M) | 1977 | kaplan_meier_survival_curve | public dataset; statsmodel | PASS | PASS | publication-grade visualization from associated data (surv |
| 3 | Least angle regression (diabetes data) (Efron B, Hastie ) | 2004 | scatterplot_with_regression | public benchmark; scikit-l | PASS | PASS | publication-grade visualization from associated data |
| 4 | The use of multiple measurements in taxo (Fisher RA) | 1936 | confusion_matrix | public domain (UCI); sciki | PASS | PASS | publication-grade visualization from associated data (the  |
| 5 | PARVUS: extendable package for data expl (Forina M, et al.) | 1991 | pca_scatter_from_matrix | public domain (UCI); sciki | PASS | PASS | publication-grade visualization from associated data |
| 6 | Ecological sexual dimorphism ... Antarct (Gorman KB, Willi) | 2014 | ridge_or_density_plot | CC0 1.0 | PASS | PASS | publication-grade recreation (distribution of a real measu |
| 7 | Smoking and lung cancer in China (8-city (Liu Z, et al.) | 1992 | forest_plot | published 2x2 counts; stat | PASS | PASS | scientific reproduction (per-city odds ratios computed fro |
| 8 | Nuclear feature extraction for breast tu (Street WN, Wolbe) | 1993 | roc_curve | public domain (UCI); sciki | PASS | PASS | publication-grade visualization from associated data (ROC  |
| 9 | Linnerud exercise physiology dataset (Tenenhaus M (ref) | 1998 | heatmap_clustered_matrix | public benchmark; scikit-l | PASS | PASS | publication-grade visualization from associated data |
| 10 | An information flow model for conflict a (Zachary WW) | 1977 | network_graph | public domain (classic net | PASS | PASS | scientific reproduction (exact node/edge set from the publ |

## Provenance & licensing
- **alpaydin1998_digits** — https://archive.ics.uci.edu/dataset/80/optical+recognition+of+handwritten+digits · article: publisher · data: public domain (UCI); scikit-learn BSD-3 · verified: UCI public-domain dataset; bundled in scikit-learn (BSD-3)
- **crowley1977_heart** — https://doi.org/10.1080/01621459.1977.10479903 · article: publisher · data: public dataset; statsmodels (BSD-3) · verified: classic public survival dataset; bundled in statsmodels (BSD-3)
- **efron2004_diabetes** — https://doi.org/10.1214/009053604000000067 · article: publisher · data: public benchmark; scikit-learn BSD-3 · verified: bundled in scikit-learn (BSD-3); standard public benchmark from the LARS paper
- **fisher1936_iris** — https://doi.org/10.1111/j.1469-1809.1936.tb02137.x · article: public domain (1936; Wiley shows public access) · data: public domain (UCI); scikit-learn BSD-3 · verified: UCI public-domain dataset; bundled in scikit-learn (BSD-3)
- **forina_wine** — https://archive.ics.uci.edu/dataset/109/wine · article: dataset donation · data: public domain (UCI); scikit-learn BSD-3 · verified: UCI public-domain dataset; bundled in scikit-learn (BSD-3)
- **gorman2014_penguins** — https://doi.org/10.1371/journal.pone.0090081 · article: CC BY 4.0 · data: CC0 1.0 · verified: PLoS ONE article CC BY 4.0; palmerpenguins data released CC0 (documented in package)
- **liu1992_china_smoking** — https://doi.org/10.1093/ije/21.2.197 · article: publisher · data: published 2x2 counts; statsmodels (BSD-3) · verified: aggregate 2x2 counts bundled in statsmodels (BSD-3)
- **street1993_wdbc** — https://doi.org/10.1117/12.148698 · article: publisher; data public domain · data: public domain (UCI); scikit-learn BSD-3 · verified: UCI public-domain dataset; bundled in scikit-learn (BSD-3)
- **tenenhaus_linnerud** — https://scikit-learn.org/stable/datasets/toy_dataset.html#linnerrud-dataset · article: publisher · data: public benchmark; scikit-learn BSD-3 · verified: bundled in scikit-learn (BSD-3); classic public multivariate dataset
- **zachary1977_karate** — https://doi.org/10.1086/jar.33.4.3629752 · article: publisher · data: public domain (classic network; bundled in NetworkX, BSD) · verified: canonical public-domain network; ships in NetworkX (BSD-3)

## Reference images
None stored (all reference_image_stored=false); textual targets only, no image-similarity.

## Known differences / honesty
- Classic datasets (Iris, Wine, Digits, Diabetes, WDBC, Linnerud): publication-grade visualizations from the associated data; ROC/confusion/calibration postdate the source papers (new visualizations of the datasets, documented per panel).
- Model-performance panels use documented cross-validated predictions (method in each scientific_qc.md); values trace to those computations.
- Scientific reproductions: Zachary karate (exact published node/edge set); Liu 1992 (per-city odds ratios from the published 2x2 counts).
- Colours/limits are Publication defaults, not any paper exact styling.

## Deferred (license-restricted, not included)
TCGA / cBioPortal / GDSC / MSK-IMPACT — data-use terms do not clearly permit redistribution; not committed. See rejected_candidates.md.

## Reproduce
    python -m pytest tests/test_ten_publication_recreation.py -q -p no:pytest-qt

## Honest conclusion
Publication-grade recreation across 10 distinct plot types — scientifically traceable to real public data and visually publication-grade, not pixel-identical to any published figure. Two panels reach scientific reproduction (karate network, Liu odds ratios).
