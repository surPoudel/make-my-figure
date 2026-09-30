# Cellular-neighbourhood enrichment matrix

**Real published data.** The Fig 3A (CRC, CC*) values from CNTools — 9 neighbourhoods x 28 cell types.

Tao Y, et al. CNTools: a computational toolbox for cellular neighborhood analysis from multiplexed images. PLOS Comput Biol 2024;20(8):e1012344. doi:10.1371/journal.pcbi.1012344 (S1 Data, CC BY 4.0).

Redistributed under CC BY 4.0.

Colour is the enrichment score, point area the cell type's frequency within that neighbourhood. Cell types appear as `CT_00`..`CT_27` because the published spreadsheet does not label its columns.

`benchmarks/spatial_validation/cntools_2024` reproduces these values from the deposited CRC data to a maximum absolute difference of 7.8e-14.

The spec pins `vmin`/`vmax` to +/-6: zero-count cells sit at a pseudocount floor near -15, and letting them set the range washes every real signal to white. Values outside the range are drawn at the end colours and the colourbar says so.
