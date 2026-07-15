# Scientific QC — penguins_pca

**Result: PASS**

Target panel: Fig: PCA of morphometrics separating species.

Transforms: Features x samples matrix from 4 morphometrics; metadata=species/island.

- mapping[matrix_row_id]='feature' traced to source column ✓
- mapping[metadata_key]='sample_id' is matrix/metadata key ✓
- mapping[color]='group' optional/derived (not a plain column)
- mapping[shape]='batch' optional/derived (not a plain column)
- rows=4, cols=343
