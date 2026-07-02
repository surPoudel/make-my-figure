# Statistics example: grouped_within_dose

Grouped design (like the classic ToothGrowth data): dose (0.5/1.0/2.0) x supplement (VC/OJ), 10 per cell.

Design: compare the two supplements WITHIN each dose. Default: Welch's t-test per dose, Benjamini-Hochberg corrected across the 3 comparisons; each dose gets its own bracket. Two-way ANOVA is also available.

Required columns: `dose` (x), `supplement` (subgroup), `tooth_length` (numeric).

All data are SYNTHETIC (fixed seed) and not real measurements.
