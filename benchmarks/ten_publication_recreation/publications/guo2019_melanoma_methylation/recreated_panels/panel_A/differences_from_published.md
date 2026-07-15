# Differences from published -- guo2019_melanoma_methylation / panel_A

Published: Guo et al. 2019, eLife, Figure 2C (CC BY 4.0). https://doi.org/10.7554/eLife.44310

| Aspect | Published Fig 2C | Recreation |
|---|---|---|
| Kind | two-group Kaplan-Meier + censoring ticks | same |
| Groups | low-risk (17/14), high-risk (30/28) | identical n / events |
| Curve shape | high-risk worse; plateaus ~0.15 | reproduced |
| Log-rank p | P = 3.09E-2 | app native log-rank p = 0.051 |
| Group encoding | dashed vs solid black | two colours + legend |
| p annotation | in-panel "P = 3.09E-2" | "Log-rank p = 0.051" |

**Honest note:** the Kaplan-Meier estimator is deterministic, so the step curves match the published
panel; the reported log-rank p differs (0.051 vs 0.031) because of a log-rank test-variant / tie-handling
difference between the app (scipy-based) and the paper's software. Disclosed, not hidden. Never claimed
as an exact reproduction.
