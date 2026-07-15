# Curation report: penguins

Raw acquired from `https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins.csv` (license CC0-1.0); raw kept unchanged under `raw/`.

Processed CSVs written to `processed/` by `curate_benchmark_data.py`.

## penguins_scatter
Transforms: Drop rows with missing bill/species; keep morphometric columns.
Mapping: `{'x': 'bill_length_mm', 'y': 'bill_depth_mm', 'color': 'species', 'fit_line': True}`
## penguins_box
Transforms: Drop missing body_mass; order species Adelie<Chinstrap<Gentoo.
Mapping: `{'x': 'species', 'y': 'body_mass_g', 'kind': 'box', 'points': True}`
Statistics: `{'enabled': True, 'test': 'kruskal_wallis', 'comparison_mode': 'all_pairs', 'correction': 'bh'}`
## penguins_pca
Transforms: Features x samples matrix from 4 morphometrics; metadata=species/island.
Mapping: `{'matrix_row_id': 'feature', 'metadata_key': 'sample_id', 'color': 'group', 'shape': 'batch'}`
## penguins_heatmap
Transforms: Per-species feature means, z-scored across species per feature.
Mapping: `{'row_id': 'feature', 'cluster_rows': True, 'cluster_columns': True, 'color_scale': 'diverging'}`
## penguins_forest
Transforms: Per-species mean +/- 1.96*SE (normal 95% CI); reference=overall mean.
Mapping: `{'label': 'subgroup', 'estimate': 'mean_body_mass_g', 'lower': 'ci_low', 'upper': 'ci_high', 'reference': 4200.0}`
