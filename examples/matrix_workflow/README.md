# Matrix workflow examples (synthetic)

Deterministic, synthetic fixtures — no private or sensitive data.

- `normalized_feature_matrix.tsv` — 300 features x (2 annotation + 12 sample) columns.
  Columns: `feature_id`, `feature_name`, `bioType`, `annotationLevel` (a numeric
  ANNOTATION coded 1/2/3, **not** a measurement), then 12 sample value columns
  (`SAMPLE_01`..`SAMPLE_12`). Values are log-normalized (may be negative).
- `sample_metadata.csv` — `sample_id`, `group` (6 Ctrl + 6 Treatment), `batch`.
- `precomputed_differential_table.tsv` — a supplied differential table
  (`feature_id`, `feature_name`, `logFC`, `AveExpr`, `P.Value`, `adj.P.Val`).
- `feature_list.txt` — feature ids to highlight.
- `expected_recommendations.json` — plots recommended for the confirmed mapping.

The app never guesses silently: you confirm the feature id / annotation / value
columns and the sample->group assignment before anything is plotted or tested.
This is a generic feature matrix (not an RNA-seq pipeline); statistics are generic
feature-level comparisons on normalized values, and precomputed tables are supported.
