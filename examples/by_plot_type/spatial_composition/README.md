# Spatial composition glyphs

**Real published data, aggregated.** The same CODEX image (reg052_B) binned into a 9x7 grid; each bin is drawn as a pie of its cell-type mixture.

Schürch CM, et al. Coordinated cellular neighborhood orchestrates antitumoral immunity at the colorectal cancer invasive front. Cell 2020. doi:10.1016/j.cell.2020.07.005. Dataset: doi:10.17632/mpjzbtfgfr.1 (Mendeley Data, CC BY 4.0).

Redistributed under CC BY 4.0. Changes made: cells aggregated into square bins, bins with fewer than 12 cells dropped, and cell types outside the seven most common pooled as `other`. Counts are exact — nothing was rescaled.

The spec sets `normalize='fraction'` because the table holds raw counts. With `normalize='as_given'` the values are drawn exactly as supplied and a short sum is reported rather than silently rescaled.
