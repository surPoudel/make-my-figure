# Publication figure recreation — report

**Rule:** reproduce only figure *kinds* confirmed by viewing each paper's actual
figures; store the real figure only under a permissive license; never claim
"exact reproduction". Padding with plots the papers don't contain is not allowed.

## Verified: 1 paper (fully figure-matched, real figure stored)

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

## Removed
See `reports/rejected_candidates.md` — 9 entries removed (kind not confirmed in the
paper and/or paper not open-access). Notably the famous penguin "bill" scatter is
`palmerpenguins` teaching art, not a Gorman-2014 figure.

## Honest limitation
Only 1 paper is fully verified here. Reaching ~10 needs sourcing more modern
open-access papers whose figures can be downloaded/viewed, map to an app plot type,
and are reproducible from public data — added one verified paper at a time, not
padded.
