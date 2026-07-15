# Curation report: diabetes

Raw acquired from `builtin:diabetes` (license Public / BSD-3 (scikit-learn)); raw kept unchanged under `raw/`.

Processed CSVs written to `processed/` by `curate_benchmark_data.py`.

## diabetes_scatter
Transforms: scikit-learn diabetes; BMI vs target.
Mapping: `{'x': 'bmi', 'y': 'disease_progression', 'fit_line': True}`
