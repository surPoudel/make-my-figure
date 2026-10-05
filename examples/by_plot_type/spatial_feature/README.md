# Spatial map (continuous value)

**Real published data** — same CODEX image as the categorical example, coloured by measured marker intensity (CD8, CD68, Ki67, CD4 columns available).

Schürch CM, et al. Coordinated cellular neighborhood orchestrates antitumoral immunity at the colorectal cancer invasive front. Cell 2020. doi:10.1016/j.cell.2020.07.005. Dataset: doi:10.17632/mpjzbtfgfr.1 (Mendeley Data, CC BY 4.0).

Redistributed under CC BY 4.0.

The bundled spec uses `transform='log1p'` because raw CODEX intensities are strongly right-skewed **and contain exact zeros** — `log2`/`log10` are refused outright rather than nudged. The colourbar is labelled `log(1 + CD8 intensity)` so the transform is visible in the figure, not buried in a spec file.
