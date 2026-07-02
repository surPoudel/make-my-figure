# Statistics example: contingency_large

A 3x3 contingency table: tumor subtype x grade.

Design: categorical association, larger than 2x2. Default: chi-square test of independence (with Cramer's V). The app warns if any expected cell count < 5.

Required columns: `subtype`, `grade` (both categorical).

All data are SYNTHETIC (fixed seed) and not real measurements.
