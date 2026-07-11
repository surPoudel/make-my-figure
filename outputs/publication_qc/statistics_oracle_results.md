# Statistics oracle validation

Independent recomputation via **scipy** / **statsmodels**, compared to the app's `StatResult` fields.

**62/62 checks passed.**

| test | field | app | reference | tolerance | pass | note |
|---|---|---|---|---|:--:|---|
| Student's t | statistic | -2.87172 | -2.87172 | rtol=1e-06 | ✅ |  |
| Student's t | p_value | 0.00578726 | 0.00578726 | rtol=1e-06 | ✅ |  |
| Student's t | df | 55 | 55 | rtol=1e-06 | ✅ |  |
| Student's t | Cohen's d | -0.761793 | -0.761793 | rtol=1e-06 | ✅ |  |
| Student's t | CI low | -1.54115 | -1.54115 | rtol=1e-05 | ✅ |  |
| Student's t | CI high | -0.274258 | -0.274258 | rtol=1e-05 | ✅ |  |
| Welch's t | statistic | -2.81534 | -2.81534 | rtol=1e-06 | ✅ |  |
| Welch's t | p_value | 0.00720208 | 0.00720208 | rtol=1e-06 | ✅ |  |
| Mann-Whitney U | statistic | 244 | 244 | rtol=1e-06 | ✅ |  |
| Mann-Whitney U | p_value | 0.0103138 | 0.0103138 | rtol=1e-06 | ✅ |  |
| Paired t | statistic | -5.87982 | -5.87982 | rtol=1e-06 | ✅ |  |
| Paired t | p_value | 1.1599e-05 | 1.1599e-05 | rtol=1e-06 | ✅ |  |
| Paired t | Cohen's dz | -1.31477 | -1.31477 | rtol=1e-06 | ✅ |  |
| Wilcoxon | statistic | 6 | 6 | rtol=1e-06 | ✅ |  |
| Wilcoxon | p_value | 2.67029e-05 | 2.67029e-05 | rtol=1e-06 | ✅ |  |
| One-way ANOVA | F | 17.0308 | 17.0308 | rtol=1e-06 | ✅ |  |
| One-way ANOVA | p_value | 9.73771e-07 | 9.73771e-07 | rtol=1e-06 | ✅ |  |
| One-way ANOVA | df1 | 2 | 2 | rtol=1e-06 | ✅ |  |
| One-way ANOVA | df2 | 69 | 69 | rtol=1e-06 | ✅ |  |
| One-way ANOVA | eta^2 | 0.330497 | 0.330497 | rtol=1e-06 | ✅ |  |
| Kruskal-Wallis | H | 24.4233 | 24.4233 | rtol=1e-06 | ✅ |  |
| Kruskal-Wallis | p_value | 4.97209e-06 | 4.97209e-06 | rtol=1e-06 | ✅ |  |
| Two-way ANOVA [A] | F | 2.13426 | 2.13426 | rtol=0.0001 | ✅ |  |
| Two-way ANOVA [A] | p_value | 0.155172 | 0.155172 | rtol=0.0001 | ✅ |  |
| Two-way ANOVA [B] | F | 1.70493 | 1.70493 | rtol=0.0001 | ✅ |  |
| Two-way ANOVA [B] | p_value | 0.202272 | 0.202272 | rtol=0.0001 | ✅ |  |
| Two-way ANOVA [A x B] | F | 0.0029338 | 0.0029338 | rtol=0.0001 | ✅ |  |
| Two-way ANOVA [A x B] | p_value | 0.957189 | 0.957189 | rtol=0.0001 | ✅ |  |
| Chi-square | statistic | 14.4862 | 14.4862 | rtol=1e-06 | ✅ |  |
| Chi-square | p_value | 0.000141189 | 0.000141189 | rtol=1e-06 | ✅ |  |
| Chi-square | df | 1 | 1 | rtol=1e-06 | ✅ |  |
| Chi-square | Cramer's V | 0.425532 | 0.425532 | rtol=1e-06 | ✅ |  |
| Fisher's exact | odds ratio | 7 | 7 | rtol=1e-06 | ✅ |  |
| Fisher's exact | p_value | 0.000111681 | 0.000111681 | rtol=1e-06 | ✅ |  |
| Log-rank | chi2 | 10.3439 | 10.3439 | rtol=0.0001 | ✅ |  |
| Log-rank | p_value | 0.00129904 | 0.00129904 | rtol=0.0001 | ✅ |  |
| Pearson | r | 0.74338 | 0.74338 | rtol=1e-06 | ✅ |  |
| Pearson | p_value | 3.91322e-08 | 3.91322e-08 | rtol=1e-06 | ✅ |  |
| Spearman | rho | 0.688555 | 0.688555 | rtol=1e-06 | ✅ |  |
| Spearman | p_value | 9.05609e-07 | 9.05609e-07 | rtol=1e-06 | ✅ |  |
| Linear regression | slope | 0.732385 | 0.732385 | rtol=1e-06 | ✅ |  |
| Linear regression | p_value | 3.91322e-08 | 3.91322e-08 | rtol=1e-06 | ✅ |  |
| Linear regression | R^2 | 0.552614 | 0.552614 | rtol=1e-06 | ✅ |  |
| Correction [bonferroni] | p_adj[0] | 0.006 | 0.006 | rtol=1e-09 | ✅ |  |
| Correction [bonferroni] | p_adj[1] | 0.06 | 0.06 | rtol=1e-09 | ✅ |  |
| Correction [bonferroni] | p_adj[2] | 0.12 | 0.12 | rtol=1e-09 | ✅ |  |
| Correction [bonferroni] | p_adj[3] | 0.18 | 0.18 | rtol=1e-09 | ✅ |  |
| Correction [bonferroni] | p_adj[4] | 1 | 1 | rtol=1e-09 | ✅ |  |
| Correction [bonferroni] | p_adj[5] | 1 | 1 | rtol=1e-09 | ✅ |  |
| Correction [holm] | p_adj[0] | 0.006 | 0.006 | rtol=1e-09 | ✅ |  |
| Correction [holm] | p_adj[1] | 0.05 | 0.05 | rtol=1e-09 | ✅ |  |
| Correction [holm] | p_adj[2] | 0.08 | 0.08 | rtol=1e-09 | ✅ |  |
| Correction [holm] | p_adj[3] | 0.09 | 0.09 | rtol=1e-09 | ✅ |  |
| Correction [holm] | p_adj[4] | 0.4 | 0.4 | rtol=1e-09 | ✅ |  |
| Correction [holm] | p_adj[5] | 0.5 | 0.5 | rtol=1e-09 | ✅ |  |
| Correction [benjamini_hochberg] | p_adj[0] | 0.006 | 0.006 | rtol=1e-09 | ✅ |  |
| Correction [benjamini_hochberg] | p_adj[1] | 0.03 | 0.03 | rtol=1e-09 | ✅ |  |
| Correction [benjamini_hochberg] | p_adj[2] | 0.04 | 0.04 | rtol=1e-09 | ✅ |  |
| Correction [benjamini_hochberg] | p_adj[3] | 0.045 | 0.045 | rtol=1e-09 | ✅ |  |
| Correction [benjamini_hochberg] | p_adj[4] | 0.24 | 0.24 | rtol=1e-09 | ✅ |  |
| Correction [benjamini_hochberg] | p_adj[5] | 0.5 | 0.5 | rtol=1e-09 | ✅ |  |
| Hedges g | g | -0.751357 | -0.751357 | rtol=1e-06 | ✅ |  |

Reference libraries: scipy scipy, statsmodels. Log-rank oracle: `statsmodels.duration.survfunc.survdiff`. Cox HR uses statsmodels PHReg (same engine; PH assumption not auto-checked — see method sentence).
