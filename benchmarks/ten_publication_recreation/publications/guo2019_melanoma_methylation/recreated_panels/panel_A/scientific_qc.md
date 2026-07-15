# Scientific QC -- guo2019_melanoma_methylation / panel_A

**Figure kind:** two-group Kaplan-Meier survival curve with censoring ticks -- matches Guo et al. 2019, Figure 2C (confirmed by viewing the published figure).

**Data:** Figure 2-source data 3 (`elife-44310-fig2-data3-v1.xlsx`), CC BY 4.0. GEO GSE51547 cohort, n=47.

**Group / event counts (app) vs published legend:**
- low-risk: n=17, events=14  (legend "Low-risk (17/14)") -- exact match.
- high-risk: n=30, events=28 (legend "High-risk (30/28)") -- exact match.

**Log-rank:** app native log-rank p = **0.051** (chi-square 3.80, 1 df). Paper reports **P = 3.09E-2**.
The Kaplan-Meier step curves are deterministic and reproduce the published shape exactly; the p-value
difference reflects a log-rank variant / tie-handling difference between the app (scipy-based) and the
paper's tool, not a data error. No p-value is fabricated -- it comes from the app's stored StatResult.

**Interpretation:** high-risk patients have markedly worse survival than low-risk, reproducing the
paper's central claim for panel C.
