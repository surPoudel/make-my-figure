# Expected method report: grouped_within_dose

Statistical analyses were performed with Python (scipy 1.17.1, statsmodels 0.14.6, numpy 2.1.2). Tests used: Welch's t-test. P-values were adjusted across 3 comparisons using Benjamini-Hochberg FDR correction. Exact p-values are reported unless otherwise noted. Non-finite values were removed listwise before testing. Users are responsible for confirming that each test is appropriate for their experimental design.

- 'VC' vs 'OJ' were compared with a two-sided unpaired Welch's t-test (t(17.3557) = -3.15, p = 0.009, adjusted, Benjamini-Hochberg FDR correction, Hedges' g = -1.35, 95% CI for difference in means (group_a - group_b) [-5.83, -1.16]).
- 'VC' vs 'OJ' were compared with a two-sided unpaired Welch's t-test (t(15.7283) = -8.26, p < 0.001, adjusted, Benjamini-Hochberg FDR correction, Hedges' g = -3.54, 95% CI for difference in means (group_a - group_b) [-8.77, -5.19]).
- 'VC' vs 'OJ' were compared with a two-sided unpaired Welch's t-test (t(13.1787) = -1.27, p = 0.226, adjusted, Benjamini-Hochberg FDR correction, Hedges' g = -0.544, 95% CI for difference in means (group_a - group_b) [-3.31, 0.856]).
