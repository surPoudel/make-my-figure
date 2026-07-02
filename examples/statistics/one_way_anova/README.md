# Statistics example: one_way_anova

Three groups (Low/Medium/High), 16 samples each.

Design: one categorical factor, >2 groups. Default: one-way ANOVA (omnibus) with post-hoc pairwise Welch t-tests, Benjamini-Hochberg corrected. Nonparametric alternative: Kruskal-Wallis + Dunn.

Required columns: `dose_group` (categorical), `measurement` (numeric).

All data are SYNTHETIC (fixed seed) and not real measurements.
