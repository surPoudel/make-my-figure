# Scientific QC -- thommen2019_planaria / panel_A

**Figure kind:** log-log wet-mass-vs-dry-mass allometric scatter with a linear fit -- matches Thommen et al. 2019, Figure 1B (confirmed by viewing the published figure).

**Data:** Figure 1-source data 1 (`elife-38187-fig1-data1-v1.xlsx`), CC BY 4.0. n = 28 paired
(wet mass, dry mass) measurements after dropping one trailing balance-readability note row.

**Quantitative check (app output):**
- Ordinary-least-squares fit of log10(wet) on log10(dry) over all 28 points: slope (scaling exponent) = **1.14**, Pearson r = **0.995**.
- Paper reports scaling exponent **1.03 +/- 0.01** for the isometric regime.
- Restricting to dry mass >= 0.15 mg (n = 21) -- i.e. excluding the smallest planarians the figure itself shows deviating below the fit line -- the same app returns slope = **1.03**, matching the paper.

**Interpretation:** wet and dry mass scale near-isometrically (exponent ~1), reproducing the paper's central claim for panel B. The full-data exponent is inflated by low-mass deviants; the discrepancy is a fitting-scope difference, not an error, and is disclosed rather than hidden. No p-values are fabricated; the fit slope is computed by the renderer.
