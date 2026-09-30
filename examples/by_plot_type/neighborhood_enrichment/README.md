# Cellular-neighbourhood enrichment matrix

**Real published data.** These are the Fig 3A (CRC, CC*) values from CNTools — Tao et al. 2024, *PLOS Computational Biology* 20(8):e1012344, doi:10.1371/journal.pcbi.1012344 — redistributed under CC BY 4.0.

9 neighbourhoods x 28 cell types. Colour is the enrichment score, point area the cell type's frequency within the neighbourhood.

Cell types are shown as `CT_00`..`CT_27` because the published spreadsheet does not label its columns. `benchmarks/spatial_validation/cntools_2024` reproduces these values from the deposited CRC data to a maximum absolute difference of 7.8e-14.
