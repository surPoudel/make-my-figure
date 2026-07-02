# Expected method report: one_way_anova

Statistical analyses were performed with Python (scipy 1.17.1, statsmodels 0.14.6, numpy 2.1.2). Tests used: One-way ANOVA; Welch's t-test. P-values were adjusted across 3 comparisons using Benjamini-Hochberg FDR correction. Exact p-values are reported unless otherwise noted. Non-finite values were removed listwise before testing. Users are responsible for confirming that each test is appropriate for their experimental design.

- A One-way ANOVA was performed on measurement across dose_group (F(2, 45) = 37.1, p < 0.001, eta-squared = 0.623).
- 'Low' vs 'Medium' were compared with a two-sided unpaired Welch's t-test (t(29.9972) = -2.18, p = 0.037, adjusted, Benjamini-Hochberg FDR correction, Hedges' g = -0.752, 95% CI for difference in means (group_a - group_b) [-1.31, -0.0432]).
- 'Low' vs 'High' were compared with a two-sided unpaired Welch's t-test (t(29.6093) = -8.52, p < 0.001, adjusted, Benjamini-Hochberg FDR correction, Hedges' g = -2.94, 95% CI for difference in means (group_a - group_b) [-3.09, -1.9]).
- 'Medium' vs 'High' were compared with a two-sided unpaired Welch's t-test (t(29.5424) = -6.17, p < 0.001, adjusted, Benjamini-Hochberg FDR correction, Hedges' g = -2.13, 95% CI for difference in means (group_a - group_b) [-2.42, -1.21]).
