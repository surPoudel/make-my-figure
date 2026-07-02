# Expected method report: two_group_unpaired

Statistical analyses were performed with Python (scipy 1.17.1, statsmodels 0.14.6, numpy 2.1.2). Tests used: Welch's t-test. Exact p-values are reported unless otherwise noted. Non-finite values were removed listwise before testing. Users are responsible for confirming that each test is appropriate for their experimental design.

- 'Control' vs 'Treated' were compared with a two-sided unpaired Welch's t-test (t(33.2018) = -3.29, p = 0.002, Hedges' g = -1.07, 95% CI for difference in means (group_a - group_b) [-1.76, -0.415]).
