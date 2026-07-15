# Scientific QC — alpaydin1998_digits

**Result: PASS**

Publication: Cascading classifiers (Optical Recognition of Handwritten Digits) (Alpaydin E, Kaynak C, 1998). https://archive.ics.uci.edu/dataset/80/optical+recognition+of+handwritten+digits
Data license: public domain (UCI); scikit-learn BSD-3 — UCI public-domain dataset; bundled in scikit-learn (BSD-3)

Plot type: `calibration_plot` · rows used: 1797

Curation / traceability:
- n_samples: 1797
- task: one-vs-rest: is digit 0
- method: 5-fold CV P(digit==0); StandardScaler+LogReg
- n_positive: 178
- brier: 0.0026713398948047576

Every displayed quantity traces to a source column or the documented computation above (no fabricated values).
