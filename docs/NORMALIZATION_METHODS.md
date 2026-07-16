# Normalization methods

All Python‑only (`matrix_workflow/normalization.py`); each returns a **new** matrix and
a params/warnings record and never mutates the input. No method is universally
appropriate — the recommender surfaces suitability/risk text (`normalization_catalog()`).

| Method | What it does | Suitable for | Risks / not for |
|---|---|---|---|
| `total_sum` | divide each sample by its total, ×scale factor | count‑like, comparable libraries | dominated by a few big features; needs ≥0 |
| `median_scale` | equalize per‑sample medians | robust size correction | breaks if >50% features change |
| `upper_quartile` | scale by the 75th percentile | a few features dominate totals | very sparse data; needs ≥0 |
| `quantile` | force identical distributions | technical distribution differences | erases real global shifts |
| `row_zscore` / `column_zscore` / `global_zscore` | standardize feature/sample/all | heatmap contrast, comparability | loses absolute magnitude |
| `robust_scale` | per‑column median/IQR | skewed/outlier‑heavy data | changes units |
| `standard_scale` | per‑column mean 0 / unit variance | model inputs | changes units |
| `center` | subtract sample/feature/grand median or feature mean | centering for display | not a full normalization |
| `internal_standard_features` / `internal_standard_columns` | divide (or subtract, if log) by internal‑standard signal | targeted assays with spike‑ins | unstable IS propagates error |
| `control_features` | normalize by housekeeping/control features | assays with stable controls | poor if controls vary |
| `reference_sample` | express relative to a reference sample/group | fold‑relative views | reference must be representative |

**Scale awareness:** log transforms and ratio fold‑change require non‑negative values;
if negatives are present the app warns and recommends z‑score/centering for
visualization only. Every applied method is recorded in the `PreprocessingSpec`.
