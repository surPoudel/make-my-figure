# Janesick et al. 2023 — spatial validation benchmark

Reproduces panels from Janesick A, *et al.*, "High resolution mapping of the tumor
microenvironment using integrated single-cell, spatial and in situ analysis",
*Nature Communications* 14:8353 (2023), doi:10.1038/s41467-023-43458-x.

## Results

| Target | Classification | Checks |
|---|---|---|
| **Fig. 3l** — Xenium cell-type spatial map | **exact reproduction of the published annotation** | 28/28 |
| **Fig. 2c** — Visium marker expression | **expression reproduced; normalisation verified against deposited values** | 12/12 |
| **Fig. 2c** — Visium cluster panel | **not reproduced** — see below | — |

### Fig. 3l — why this is a reproduction, not a recreation

Every cell's type is the authors' own **deposited supervised annotation**
(`GSM7780153_Xenium_R1_Fig1-5_supervised.csv.gz`, the labels used for Figures 1–5),
and every coordinate is a deposited cell centroid. Nothing is re-clustered,
re-annotated or re-normalised — the figure is redrawn from the authors' numbers.

167,780 cells, 20 cell types, 100 % join on `cell_id`. The audit checks the count of
every individual population survives the join, so a lost or duplicated group would fail.

### Fig. 2c — the normalisation was recovered, not assumed

The paper says only that markers are shown as "log2(normalized UMI counts)" and does
not define the normalisation. That would normally force a "recreation" label. It does
not here, because the normalisation can be **checked against deposited values**:

`spatial/spatial_enrichment.csv` carries a per-gene "Median Normalized Average Counts"
column produced by the same pipeline that made the figure. Scaling each spot to the
median total UMI count (median = 13,532) reproduces that column:

| | |
|---|---|
| Genes compared | **18,056** |
| Worst relative difference | **8.6e-13** |
| Correlation | 1.0000000000 |

So the normalisation is established by evidence. **One documented assumption remains**:
the paper writes "log2", and zero counts are present, so `log2(1 + x)` is used —
`log2(x)` is undefined at zero. That affects the colour scale only, and is recorded in
the figure's metadata and colourbar label.

### What is *not* reproduced, and why

The **Fig. 2c cluster panel**. Space Ranger's graph-based cluster assignments are
deposited only inside the proprietary `.cloupe` file (909 MB); no cluster table is
published. Re-clustering would produce different labels and would not be a
reproduction of the published figure, so it is not attempted. This is a limitation of
what was deposited, not of the software.

Styling is MakeMyFigure's Publication style throughout. **No claim is made that the
artwork matches the published figures** — the claim is about the data drawn.

## Running it

```bash
scripts/download.sh                              # fetches sources, verifies SHA-256
python scripts/reproduce_xenium_celltypes.py     # Fig. 3l
python scripts/reproduce_visium_expression.py    # Fig. 2c markers
```

Both write an audit table to `validation/` with one row per compared quantity
(published value, our value, absolute and relative difference, pass/fail).

## Downloading without downloading everything

The series tar is **31.78 GB** and the Xenium output bundle is **9.18 GB**. Neither is
fetched in full. `scripts/zip_member.py` reads a remote ZIP's central directory with
HTTP range requests and pulls out only the wanted member — **7.9 MB instead of 9.18 GB**
for the cell table. Visium files are fetched per sample rather than from the series tar.

## Sources and licensing

Data are deposited under **GEO GSE243280**. Raw and derived data are **not committed**:
`raw/` is fetched by script, and the derived tables (14 MB) and rendered figures (16 MB)
regenerate from them. The audit tables and PlotSpecs *are* committed, so the result
stays auditable without the bulk.

No 10x Genomics software or restricted companion code is copied or vendored. Every
operation here is implemented independently from the deposited data, which is the
licensing posture the paper's terms require.

Checksums for every input are in `source_manifest.json` and re-verified on each run.
