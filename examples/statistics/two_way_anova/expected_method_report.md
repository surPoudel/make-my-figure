# Expected method report: two_way_anova

Statistical analyses were performed with Python (scipy 1.17.1, statsmodels 0.14.6, numpy 2.1.2). Tests used: Two-way ANOVA. Exact p-values are reported unless otherwise noted. Non-finite values were removed listwise before testing. Users are responsible for confirming that each test is appropriate for their experimental design.

- A Two-way ANOVA was performed on expression across genotype x treatment (genotype) (F(1, 28) = 91.4, p < 0.001, partial eta-squared (approx, eta-sq of total SS) = 0.363).
- A Two-way ANOVA was performed on expression across genotype x treatment (treatment) (F(1, 28) = 104, p < 0.001, partial eta-squared (approx, eta-sq of total SS) = 0.413).
- A Two-way ANOVA was performed on expression across genotype x treatment (genotype x treatment) (F(1, 28) = 28.1, p < 0.001, partial eta-squared (approx, eta-sq of total SS) = 0.112).
