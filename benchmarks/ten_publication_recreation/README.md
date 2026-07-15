# Publication figure recreation benchmark

Each panel reproduces the **kind of figure its source paper actually shows** —
**confirmed by viewing the published figure** — recreated through Make My Figure
(Publication style) from the paper's **public data**. The real published figure is
stored as a reference **only where the article license clearly permits** (CC BY /
CC0 / public domain), with attribution + `license.txt`. Recreations are the same
*kind*, **not pixel-identical**, and are never labelled "exact reproduction".

## Hard rule (why this is small)
Do **not** assume a paper contains a figure because a dataset is famous. For every
entry the paper's actual figures were downloaded and **viewed** to confirm the kind
before claiming a match. Entries whose plotted kind could not be visually confirmed
in the manuscript were removed (`reports/rejected_candidates.md`).

Worked trap: the "penguin bill length-vs-depth scatter" everyone associates with
this dataset is **`palmerpenguins` teaching art, not a figure in Gorman et al.
2014**. That paper's five figures are a study map, a sampling map + sea-ice bar
charts, and **δ¹³C-vs-δ¹⁵N stable-isotope biplots** (Figs 3–5). So the only
app-reproducible match is the **isotope biplot**.

## Verified entries

| id | paper | article license | plot kind (confirmed in paper) | real figure stored |
|---|---|---|---|---|
| gorman2014_penguins | Gorman et al. 2014, *PLoS ONE* | **CC BY 4.0** | δ¹³C-vs-δ¹⁵N stable-isotope scatter (Figs 3–5) | **yes** — Fig 3 + `side_by_side/gorman2014_penguins.png` |

Only Gorman 2014 is open-access, so only its figure could be legally stored.

## Expanding
Scaling to ~10 verified figure-matches requires sourcing more **modern
open-access (CC BY/CC0)** papers whose figures (a) can be downloaded + viewed,
(b) map to an app plot type, and (c) are reproducible from public data — verifying
article/figure/data licenses per paper. This was intentionally **not padded** with
plots the papers don't contain; entries are added one verified paper at a time.

## Reproduce
```
python -m pytest tests/test_ten_publication_recreation.py -q -p no:pytest-qt
```
