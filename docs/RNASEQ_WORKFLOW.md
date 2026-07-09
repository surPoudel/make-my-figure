# RNA-seq workflow

Make My Figure supports three RNA-seq input modes, all reachable from the
**RNA-seq** section (desktop: the "🧬 RNA-seq…" button; Streamlit: the "RNA-seq"
data-source option). It never fabricates differential-expression statistics.

> **Caution.** RNA-seq differential expression depends on experimental design,
> normalization, model specification, covariates, and multiple-testing
> correction. Make My Figure reports the analysis method and design, but users
> remain responsible for confirming that the model matches their study design.
> RNA-seq DE must **not** be replaced by a simple t-test — count data are
> over-dispersed and require count-based models (edgeR/limma-voom).

## The three modes

| Mode | Upload | Produces | Needs R? |
|------|--------|----------|----------|
| **A. Precomputed DE result** | a DE table (e.g. `Ctrl_vs_Treatment_DE.txt`) | volcano plot, filtered/significant tables | no |
| **B. Normalized matrix** | a normalized matrix (e.g. `voom_norm_annot.txt`) | heatmap, PCA, sample correlation, gene plots | no |
| **C. Raw counts + metadata** | count matrix + sample metadata (+ optional config) | reproducible DE (edgeR + limma-voom) → volcano/heatmap | **yes** |

The app auto-detects the mode on upload (and you can override it). Detection
recognizes R `write.table` output where the gene ID is an unnamed row-name
column, and promotes it to a `gene_id` column automatically.

## Mode A — precomputed DE table → volcano

See [VOLCANO_FROM_DE_RESULTS.md](VOLCANO_FROM_DE_RESULTS.md). Column roles
(gene id, symbol, logFC, p-value, adjusted p, average expression, statistic) are
auto-detected from common aliases and are editable. Genes are classified
Up / Down / Not significant from your thresholds; p-values come straight from the
table.

## Mode B — normalized matrix → heatmap

See [HEATMAP_FROM_EXPRESSION_MATRIX.md](HEATMAP_FROM_EXPRESSION_MATRIX.md). The
leading annotation columns (gene id/symbol/biotype/...) are separated from the
sample columns automatically. Do **not** run raw-count DE on a normalized matrix.

## Mode C — raw counts + metadata → DE

See [RNASEQ_RAW_COUNTS_TO_VOLCANO.md](RNASEQ_RAW_COUNTS_TO_VOLCANO.md).

**Required metadata columns:** a sample-ID column (e.g. `SampleID`) matching the
count-matrix columns, and a condition/group column (e.g. `Group`). Optional:
batch, covariates (e.g. `Age`), replicate/subject.

**Comparisons** are defined as `{group1, group2}` pairs (treatment vs control),
either chosen in the GUI or read from a `config.json`.

**Method (accurately labeled):** the pipeline is **edgeR (TMM normalization +
CPM filtering) with limma-voom and an empirical Bayes moderated t-test** — the
same design as the reference script
`test_matrix/pipeline_cab_rnaseq_de_finalized_050924_cov_rep_fixed.R`. The app
reports the exact design formula and contrasts, and the statistic is the
moderated *t* with Benjamini-Hochberg FDR. It is not labeled "edgeR only".

## DE methods

Mode C offers two count-appropriate methods (choose per analysis):

- **edgeR + limma-voom** — TMM normalization + CPM filtering, voom, and an
  empirical Bayes **moderated t-test** (the reference pipeline). DE columns:
  `logFC, AveExpr, t, P.Value, adj.P.Val, B`.
- **DESeq2** — median-of-ratios size factors, a negative-binomial GLM, and a
  **Wald test**; a VST-normalized matrix is written for heatmaps/PCA. DESeq2
  requires integer counts (values are rounded). Output columns are normalized to
  the same schema (`logFC` = log2FoldChange, `t` = Wald stat, `adj.P.Val` = padj)
  so the volcano/heatmap code is method-agnostic.

Neither is "better" universally — report whichever you use, with its design.

## Installing R — one click, or manual

**Easiest (recommended):** in the RNA-seq workflow, click **"Set up R for
RNA-seq"**. The app downloads a self-contained R environment (via micromamba)
into the per-user app-data directory and auto-uses its `Rscript`. Platform
detail: on **Linux/macOS** it pulls prebuilt conda-forge/bioconda binaries; on
**Windows** (where Bioconda has no builds) it installs `r-base` from conda-forge
and then uses **BiocManager** to fetch Bioconductor's precompiled Windows
binaries for edgeR/limma/DESeq2. Either way there's no separate R install and no
compiler. Needs internet once (~1 GB); a locked-down/offline machine may block
it.

**Manual alternative:** install R from https://www.r-project.org/, then:

```r
if (!requireNamespace("BiocManager", quietly=TRUE)) install.packages("BiocManager")
BiocManager::install(c("edgeR", "limma", "DESeq2"))
install.packages("jsonlite")
```

`Rscript` resolution order: `MAKE_MY_FIGURE_RSCRIPT` env var → the app-managed
environment → your system PATH. If R or a required package is missing, the app
says so, disables **Run DE**, and still makes volcano plots from precomputed DE
tables.

## Reproducibility — RnaSeqSpec

Every RNA-seq analysis can export an `*.rnaseq_spec.json` recording input files
(+ checksums), the detected mode, condition/reference/comparison, covariates,
batch, the **design formula and contrasts**, filtering, normalization, the DE
method label, R + package versions, output paths, thresholds, and warnings —
alongside the PlotSpec and a Markdown method report. See
[VOLCANO_FROM_DE_RESULTS.md](VOLCANO_FROM_DE_RESULTS.md) and the caution above.

## What the app does not do

- It does not choose your model for you or verify that covariates/batch capture
  the real confounders.
- It does not run gene-set / pathway enrichment, isoform, or single-cell
  analyses.
- It does not recompute DE statistics from a normalized matrix (that needs the
  raw counts and the R pipeline).
