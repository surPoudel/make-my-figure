# Statistics example: repeated_measures

Repeated measures: 12 subjects each measured at 3 timepoints (T0/T1/T2).

Design: within-subject factor `time`, subject ID `subject`. Default: repeated-measures ANOVA (requires a complete, balanced design - one row per subject per timepoint). Sphericity is assumed and not corrected.

Required columns: `subject` (ID), `time` (within factor), `signal` (numeric).

All data are SYNTHETIC (fixed seed) and not real measurements.
