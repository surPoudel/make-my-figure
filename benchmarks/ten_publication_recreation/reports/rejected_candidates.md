# Rejected / removed candidates

Removed because the plotted kind could **not be confirmed by viewing the source
paper's figures**, and/or the paper is not open-access so the real figure cannot be
obtained/redistributed. Per the benchmark rule, no panel is kept unless its figure
kind is visually verified in the manuscript.

- **zachary1977_karate** (network graph) — Zachary 1977 (J. Anthropological Research)
  is not open-access; its figure could not be downloaded/viewed to confirm. Dropped
  (no assuming from fame).
- **fisher1936_iris** (confusion matrix) — the 1936 paper predates and does not contain
  a confusion matrix.
- **alpaydin1998_digits** (calibration plot) — not a figure in the source paper.
- **efron2004_diabetes** (scatter) — the LARS paper's figures are coefficient-path
  plots, not this scatter.
- **tenenhaus_linnerud** (heatmap) — not a figure in the source.
- **forina_wine** (PCA) — plot kind not confirmed in the source; non-open.
- **street1993_wdbc** (ROC) — plot kind not confirmed in the source; non-open.
- **crowley1977_heart** (Kaplan–Meier) — plausible for a survival paper, but the 1977
  article's figure could not be obtained/viewed to confirm. Dropped.
- **liu1992_china_smoking** (forest) — plot kind not confirmed in the source; non-open.
- **horst2022_palmerpenguins** (R Journal RJ-2022-020) — a natural candidate for a
  penguin figure with a clearly-viewable manuscript, but **rejected on license**: the
  R Journal states its content is "© The R Foundation", not clearly CC BY/CC0, so its
  figures cannot be redistributed here. (Verified by fetching journal.r-project.org.)

These datasets remain scientifically usable, but as *dataset illustrations*, not
reproductions of the papers' figures — so they do not belong in a figure-recreation
benchmark.

## Batch 4 rejections (enrichment / grouped-bar / dose-response search)

- **eLife 69433 (Marcotti et al.) Fig 3** — synapses/IHC vs frequency, WT vs
  Tmc mutants. REJECTED (kind mismatch): the panel is a grouped **dot plot with
  mean ± SD markers**, not a bar chart. The app's `grouped_barplot_with_error_bar`
  draws bars; representing a dot-with-mean±SD figure as bars would misrepresent the
  mark, and the app has no two-level (frequency × genotype) grouped dot/strip plot.
  License CC BY 4.0 (would have qualified), but recreated faithfully it is not the
  same visual kind.
- **eLife 80165 (Kaur et al.) Fig 6** — LPM marker TPM, WT vs CEP83−/− over D0/D7/D25.
  REJECTED (same kind mismatch): dot + mean±SD panels, not bar charts.
- **eLife 103073 Fig 3A/B** — GO enrichment dot plot (up/down DEGs). REJECTED
  (cannot reproduce from real data): the only attached source data (sheet "Fig.3F+G")
  holds PDGFRA expression for panels F/G, **not** the enrichment table (term /
  GeneRatio / count / adjusted p) behind the dot plot, so the dots' values are not
  available to plot verbatim.
- **eLife 92990 / 98221 (antimalarial)** — screened for a clean sigmoidal
  dose–response curve with tidy concentration/response data + a reported EC50/IC50.
  REJECTED (deferred): the figures with source data are thermal-proteome / LiP-MS
  volcano/isobologram/index panels, not single dose–response curves with raw
  concentration–response points — no clean 4PL landmark to reproduce.

Net: eLife molecular-biology figures overwhelmingly use dot-with-mean±SD rather
than true bar charts, and enrichment/dose-response numeric tables are frequently not
in machine-readable source data. Added **1** rigorous new kind this batch (violin,
Liu 2018) rather than pad with a forced or unverifiable match.
