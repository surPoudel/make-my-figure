# Statistics example: two_group_paired

Paired measurements (Pre vs Post) on the same 15 subjects.

Design: paired (matched on `subject`), two-sided. Default test: paired t-test. Alternative: Wilcoxon signed-rank. A subject/pair ID is REQUIRED.

Required columns: `subject` (pair ID), `timepoint` (Pre/Post), `value` (numeric).

All data are SYNTHETIC (fixed seed) and not real measurements.
