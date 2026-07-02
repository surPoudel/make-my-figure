# Expected method report: two_group_paired

Statistical analyses were performed with Python (scipy 1.17.1, statsmodels 0.14.6, numpy 2.1.2). Tests used: Paired t-test. Exact p-values are reported unless otherwise noted. Non-finite values were removed listwise before testing. Users are responsible for confirming that each test is appropriate for their experimental design.

- 'Pre' vs 'Post' were compared with a two-sided paired Paired t-test (t(14) = -7.63, p < 0.001, Cohen's dz = -1.97, 95% CI for mean of paired differences (a - b) [-1.19, -0.667]).
