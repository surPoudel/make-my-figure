# Expected method report: repeated_measures

Statistical analyses were performed with Python (scipy 1.17.1, statsmodels 0.14.6, numpy 2.1.2). Tests used: Repeated-measures ANOVA. Exact p-values are reported unless otherwise noted. Non-finite values were removed listwise before testing. Users are responsible for confirming that each test is appropriate for their experimental design.

- A Repeated-measures ANOVA was performed on signal across time (F(2, 22) = 71.5, p < 0.001).

Warnings:
- Sphericity is assumed and not corrected (no Greenhouse-Geisser).
