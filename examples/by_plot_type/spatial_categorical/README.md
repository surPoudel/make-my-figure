# Spatial map (categories)

**Real published data.** One CODEX image (reg052_B, 2,192 cells, 16 annotated cell types) from the colorectal-cancer dataset of Schürch et al., *Cell* 2020.

Schürch CM, et al. Coordinated cellular neighborhood orchestrates antitumoral immunity at the colorectal cancer invasive front. Cell 2020. doi:10.1016/j.cell.2020.07.005. Dataset: doi:10.17632/mpjzbtfgfr.1 (Mendeley Data, CC BY 4.0).

Redistributed under CC BY 4.0. Changes made: one image selected, columns subset and renamed; no measured value was altered.

Coordinates are **image pixels**, so the example declares `coordinate_units='pixel'` and `orientation='y_down'` — imaging y runs downward, and the renderer flips only when told to. No physical scale bar is drawn, because pixels carry no stated physical length.

`neighborhood` holds the published cellular-neighbourhood assignment, so the same table also renders as a neighbourhood map by pointing `category` at it.
