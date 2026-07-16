# Preprocessing workflow examples (synthetic)

Deterministic, synthetic, license-safe fixtures — no private data.

- `raw_like_count_matrix.tsv` — 400 features x (annotation + 12 sample) columns, integer,
  right-skewed, with sample-total imbalance (count-like).
- `skewed_intensity_matrix.tsv` — continuous strongly right-skewed intensities.
- `internal_standard_matrix.tsv` — 5 stable `IS_*` internal-standard features + real features.
- `sample_metadata.csv` — 6 Ctrl + 6 Treatment (+ batch).
- `control_feature_list.txt` — feature ids used as controls/internal standards.
- `expected_preprocessing_recommendations.json` — QC-driven preprocessing suggestions.

The app diagnoses these matrices, RECOMMENDS preprocessing, and only applies it after
you confirm — the original matrix is never changed and every step is saved in a
PreprocessingSpec. See docs/PREPROCESSING_QC.md.
