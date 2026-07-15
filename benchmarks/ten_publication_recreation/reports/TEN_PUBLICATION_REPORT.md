# Publication figure recreation — report

**Rule:** reproduce only figure *kinds* confirmed by viewing each paper's actual
figures; store the real figure only under a permissive license; never claim
"exact reproduction". Padding with plots the papers don't contain is not allowed.

## Verified: 4 papers (fully figure-matched, real figure stored)

### gorman2014_penguins — Gorman et al. 2014, *PLoS ONE* 9(3):e90081 (CC BY 4.0)
- **Paper's actual figures (viewed):** Fig 1 study-site map; Fig 2 sampling map +
  sea-ice area/duration **bar** charts by year; **Figs 3–5 δ¹³C-vs-δ¹⁵N stable-isotope
  biplots** (mean±error) by sex per year, one per species.
- **Reproduced:** the isotope biplot kind — `scatterplot_with_regression`,
  x=δ¹³C, y=δ¹⁵N, coloured by species — from `penguins_raw.csv` (which carries the
  "Delta 15 N"/"Delta 13 C" columns; the tidy `penguins.csv` does not).
- **Real figure stored:** PLoS Fig 3 (`pone.0090081.g003`, CC BY 4.0, attributed in
  `reference_figures/gorman2014_penguins/license.txt`) + `side_by_side/gorman2014_penguins.png`.
- **Classification:** publication-grade recreation (same kind, not pixel-identical;
  the paper facets by year and shows per-sex mean±SE per species, here individual
  birds coloured by species).

### thommen2019_planaria — Thommen et al. 2019, *eLife* 8:e38187 (CC BY 4.0)
- **Paper's actual figures (viewed):** Fig 1 = planarian size series photo (A) +
  **log–log wet-vs-dry mass scatter with linear fit, exponent 1.03±0.01 (B)** +
  metabolic-rate-vs-wet-mass scatter (C) + cross-species Kleiber scatter (D).
- **Reproduced:** panel B's kind — `scatterplot_with_regression`, x=log₁₀ dry mass,
  y=log₁₀ wet mass, with the app's default OLS fit — from **Figure 1-source data 1**
  (`elife-38187-fig1-data1-v1.xlsx`, CC BY 4.0; n=28 after dropping one note row).
- **Real figure stored:** eLife Fig 1B (cropped, CC BY 4.0, attributed in
  `reference_figures/thommen2019_planaria/license.txt`) +
  `side_by_side/thommen2019_planaria.png`.
- **Classification:** publication-grade recreation (same kind, not pixel-identical).
  **Quantitative honesty:** the app's default OLS over all 28 points gives exponent
  **1.14** (r=0.995); the paper reports **1.03±0.01** for the isometric regime.
  Restricting to the same range (dry ≥ 0.15 mg, n=21 — excluding the smallest
  planarians the figure itself shows below the line) the app reproduces **1.03**.
  Disclosed in `differences_from_published.md`, not hidden.

### guo2019_melanoma_methylation — Guo et al. 2019, *eLife* 8:e44310 (CC BY 4.0)
- **Paper's actual figures (viewed):** Fig 2 = ROC curves (A training, B validation,
  D GEO) + **Kaplan–Meier survival curve, low-risk vs high-risk, GEO GSE51547
  cohort, P=3.09E-2 (C)**.
- **Reproduced:** panel C's kind — `kaplan_meier_survival_curve`, time=days,
  event=status, group=low/high-risk — from **Figure 2-source data 3**
  (`elife-44310-fig2-data3-v1.xlsx`, CC BY 4.0; n=47).
- **Real figure stored:** eLife Fig 2C (cropped, CC BY 4.0, attributed in
  `reference_figures/guo2019_melanoma_methylation/license.txt`) +
  `side_by_side/guo2019_melanoma_methylation.png`.
- **Classification:** publication-grade recreation (same kind, not pixel-identical).
  **Quantitative honesty:** per-group sizes/events match the legend **exactly**
  (low-risk 17/14, high-risk 30/28) and the KM step curves reproduce the published
  shape; the app's native log-rank p is **0.051** vs the paper's **P=3.09E-2** — a
  log-rank variant/tie-handling difference (the curves are identical). Disclosed in
  `differences_from_published.md`.

### kume2024_psoriasis_semaphorin — Kume et al. 2024, *eLife* 13:RP97654 (CC BY 4.0)
- **Paper's actual figures (viewed):** Fig 5 = **volcano plot of psoriatic
  non-lesional vs control keratinocyte RNA-seq (A)** + GO bar chart (B) + per-marker
  expression strip plots (C) + mouse epidermis strip plots (D–F). Panel A confirmed
  by downloading and viewing the figure — caption: "The volcano plot (A) …
  changes in gene expression in psoriatic NL compared to Ctl."
- **Reproduced:** panel A's kind — `volcano_plot`, x=log₂ fold-change,
  y=−log₁₀ padj, red genes labelled — from **Figure 5-source data 1**
  (`elife-97654-fig5-data1-v1.xlsx`, sheet "Figure 5A", CC BY 4.0; 9,999 genes).
- **Real figure stored:** eLife Fig 5A (cropped, CC BY 4.0, attributed in
  `reference_figures/kume2024_psoriasis_semaphorin/license.txt`) +
  `side_by_side/kume2024_psoriasis_semaphorin.png`.
- **Classification:** publication-grade recreation (same kind, not pixel-identical).
  **Quantitative honesty:** every plotted value is the paper's own; p-values are
  **read verbatim** — `padj = 10^(−neglog10_padj)` is the exact lossless inverse of
  the published column, never recomputed (the app runs no DE). Landmark genes match:
  SPRR2F at the apex (log₂FC 4.99, −log₁₀ padj 21.5), SEMA4A at the origin
  (unchanged in NL, matching the paper's thesis). The app adds significance colours,
  dashed thresholds, a legend and count subtitle (53 up / 135 down); the paper draws
  black points with red labels only, and 3 of 16 near-origin labels are de-duped for
  overlap. Disclosed in `differences_from_published.md`.

## Removed
See `reports/rejected_candidates.md` — entries removed (kind not confirmed in the
paper and/or paper not open-access). Notably the famous penguin "bill" scatter is
`palmerpenguins` teaching art, not a Gorman-2014 figure. The R Journal
palmerpenguins paper (RJ-2022-020) was **rejected** because its content license is
"© The R Foundation", not clearly CC BY.

## Honest limitation
4 papers are fully verified here, now spanning scatter/regression, Kaplan–Meier,
and a DE volcano. Reaching ~10 needs sourcing more modern open-access papers whose
figures can be downloaded/viewed, map to an app plot type, and are reproducible
from public data — added one verified paper at a time, not padded.
