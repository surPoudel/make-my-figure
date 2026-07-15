# Differences from published -- thommen2019_planaria / panel_A

Published: Thommen et al. 2019, eLife, Figure 1B (CC BY 4.0). https://doi.org/10.7554/eLife.38187

| Aspect | Published Fig 1B | Recreation |
|---|---|---|
| Kind | log-log wet-vs-dry mass scatter + linear fit | same |
| Axes | log-scaled (decade ticks) | log10-transformed values, linear ticks |
| Fit scope | isometric regime, exponent 1.03 +/- 0.01 | app default OLS over all 28 points, exponent 1.14 (r=0.995) |
| Exponent reproducibility | -- | restricting to dry >= 0.15 mg (n=21) reproduces 1.03 |
| In-panel text | "Scaling exponent: 1.03 +/- 0.01" | title only |
| Colour | open black circles | filled accent circles (Publication palette) |

**Honest note:** the app's default fit uses all points, so its headline exponent (1.14) is steeper than
the paper's (1.03). This is a difference in fitting scope, not a data or code error: the paper fits the
isometric regime and the figure visibly shows the smallest planarians falling below the line. Feeding the
same isometric subset to the app reproduces 1.03. Never claimed as an exact reproduction.
