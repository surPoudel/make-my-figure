# Scientific QC - guo2019_melanoma_roc

**Result: PASS**

Publication: Guo W, et al. (2019). eLife 8:e44310. https://doi.org/10.7554/eLife.44310
Data license: CC BY 4.0 (eLife Figure 2-source data 1, training cohort).

Plot type: `roc_curve` - rows used: 205 (92 positive = died within 5 y, 113 negative).

Traceability:
- Predictor = the paper's own 'Four-DNA methylation' risk score column (read verbatim from source data 1).
- Outcome = 'died within 5 years' (time_days <= 1825 and status == 1), derived from the source-data survival columns.
- The app computes AUC = 0.8223, which rounds to the published **AUC = 0.822** (Figure 2A) exactly - a hard numeric landmark match.
- No p-value is drawn and nothing is fabricated; the AUC is derived by the app's ROC integrator from stored values.
