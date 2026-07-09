# Heatmaps from an expression matrix

Upload a normalized expression matrix (e.g. `voom_norm_annot.txt`) or a raw count
matrix and build a clustered, publication-grade heatmap.

## Matrix layout

Leading **annotation columns** (gene id, gene symbol, biotype, annotation level)
are separated automatically from the trailing **sample columns**. The gene ID
(often an unnamed R row-name column) is detected and promoted to `gene_id`. Row
labels use the gene symbol when available (falling back to the id), de-duplicated.

## Transforms

| Transform | Meaning | Use for |
|-----------|---------|---------|
| `none` | values as supplied | already-normalized matrices (e.g. voom) |
| `log2p1` | log2(x + 1) | raw counts, quick view |
| `cpm` / `log2cpm` | counts per million / log2(CPM+1) | raw counts |
| `zscore` | per-gene z-score (row standardization) | comparing gene patterns (default) |

Z-score uses a diverging colormap centered at 0; other transforms use a
sequential colormap. The colorbar is labeled accordingly.

## Gene selection

- **all genes** (row labels auto-hidden when too many),
- **top variable genes** (highest across-sample variance; default),
- **selected genes** (by symbol or id),
- **top-N significant DE genes** when a DE result is available.

## Sample annotations

Provide sample metadata and choose annotation columns (e.g. `Group`, `Sex`) to
draw colorblind-aware category strips above the heatmap, each with a compact
legend. Missing samples are shown light grey.

## Publication defaults

- Row/column clustering on by default (toggleable).
- Figure height grows with the number of labeled rows so gene labels stay
  legible and unclipped; labels auto-hide past a legibility limit.
- Readable colorbar, larger default fonts, editable vector text on export
  (SVG/PDF), high-DPI PNG/TIFF.

## Do not

Do not run raw-count differential expression on a normalized matrix — use Mode C
(raw counts + metadata) for DE. Heatmaps here are descriptive visualizations, not
statistical tests.
