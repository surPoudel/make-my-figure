# CNTools 2024 — spatial validation benchmark

Reproduces **Fig 3A (CRC, CC\*)** of Tao et al. 2024, *PLOS Computational Biology*
20(8):e1012344, doi:10.1371/journal.pcbi.1012344 — both channels of the panel:
the CT-CN enrichment score (colour) and the per-neighbourhood cell-type frequency
(point size).

## Result

**Exact numerical reproduction.** 504 / 504 comparisons agree to floating point:

| Channel | Pearson r | max abs diff | median abs diff |
|---|---|---|---|
| Enrichment score | 1.0 | 7.8e-14 | 1.8e-15 |
| Frequency per CN | 1.0 | 8.5e-16 | 6.5e-18 |

Audit table: `validation/fig3a_audit.csv` (one row per published value).
Summary: `validation/fig3a_summary.json`.

## What this does and does not establish

It validates **the CT-CN enrichment calculation** — an independent group's
published numbers fall out of our implementation of the published formula
exactly.

It does **not** validate our CC neighbourhood implementation. The reproduction
uses the *published* neighbourhood labels, not labels our clustering produced.
Those are separate claims and are kept separate.

## Reading CC\* correctly

The Fig 3 legend defines CC\* as *"the original CC results"* — the neighbourhood
assignments from the original publication, deposited in the CRC table as
`neighborhood10`. It is **not** a fresh CNTools CC run.

This distinction decides the outcome. Treating CC\* as a fresh CC run gives
r = 0.17 and looks like a failed reproduction; reading it as the legend defines
it gives r = 1.0. The tell was that our own pipeline is seed-stable at
r = 0.9998–1.0000, so a gap that large could not be clustering noise.

The Methods add that the original had ten CNs "with one 'dirt' enriched CN
removed". `neighborhood10` CN 1 is 70.4 % dirt; every other CN is ≤ 3.75 %, so
CN 1 is the removed one. Dropping it and the remaining dirt cells leaves
**249,678 cells, 9 neighbourhoods, 28 cell types** — matching the published
matrix shape exactly.

## Running it

```bash
scripts/download.sh                 # fetches both sources, verifies SHA-256
python scripts/reproduce_fig3a.py   # writes validation/ and derived/
```

## Sources and licensing

| Source | Licence | Committed? |
|---|---|---|
| CNTools S1 Data (`.xlsx`, 80,689 B) | PLOS **CC BY 4.0** | derived tidy table only |
| CRC CODEX cells (`.csv`, 223 MB) | terms not confirmed | **no** — fetched by script |

`derived/neighborhood_enrichment_cntools.csv` holds the published Fig 3A values
in tidy form. It is redistributable under CC BY 4.0 with attribution to Tao et al.

Checksums for both inputs are in `source_manifest.json` and re-verified on every run.
