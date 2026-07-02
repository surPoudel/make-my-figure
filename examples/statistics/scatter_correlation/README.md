# Statistics example: scatter_correlation

Continuous x-y data (biomarker vs outcome), n=50.

Design: bivariate association. Default: Pearson correlation (r, p, R², with a Fisher-z 95% CI). Alternatives: Spearman (monotonic) or linear regression (slope + CI). Per-group stats are computed if a color/group column is set.

Required columns: `biomarker`, `outcome` (both numeric).

All data are SYNTHETIC (fixed seed) and not real measurements.
