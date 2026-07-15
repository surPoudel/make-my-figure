# Curation report: iris

Raw acquired from `builtin:iris` (license Public-Domain (CC BY 4.0 at UCI)); raw kept unchanged under `raw/`.

Processed CSVs written to `processed/` by `curate_benchmark_data.py`.

## iris_roc
Transforms: LogisticRegression (OvR, 5-fold cross_val_predict); positive=virginica.
Mapping: `{'label': 'true_label', 'score': 'score_model_a'}`
## iris_pr
Transforms: Same prediction table as iris_roc.
Mapping: `{'label': 'true_label', 'score': 'score_model_a'}`
## iris_confusion
Transforms: Row-normalized; labels are species names.
Mapping: `{'true': 'true_label', 'predicted': 'predicted_label', 'normalize': 'true'}`
## iris_calibration
Transforms: Predicted virginica probability vs observed fraction.
Mapping: `{'label': 'true_label', 'prob': 'predicted_prob', 'n_bins': 8}`
