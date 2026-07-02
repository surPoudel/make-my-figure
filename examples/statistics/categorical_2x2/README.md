# Statistics example: categorical_2x2

A 2x2 table: treatment arm (A/B) x response (Responder/Non-responder).

Design: categorical association, 2x2. Default: Fisher's exact test (odds ratio + p). Chi-square is available for larger tables / large counts.

Required columns: `treatment_arm`, `response` (both categorical).

All data are SYNTHETIC (fixed seed) and not real measurements.
