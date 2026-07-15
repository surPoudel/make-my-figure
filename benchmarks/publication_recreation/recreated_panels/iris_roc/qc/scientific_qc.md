# Scientific QC — iris_roc

**Result: PASS**

Target panel: Fig: ROC for versicolor-vs-virginica classification.

Transforms: LogisticRegression (OvR, 5-fold cross_val_predict); positive=virginica.

- mapping[label]='true_label' traced to source column ✓
- mapping[score]='score_model_a' traced to source column ✓
- rows=100, cols=3
