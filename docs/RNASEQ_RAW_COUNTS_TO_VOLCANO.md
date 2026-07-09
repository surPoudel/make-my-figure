# Raw counts → DE → volcano (edgeR + limma-voom)

This is Mode C: upload a raw count matrix and sample metadata, choose the design
and comparison, run a reproducible DE analysis in R, then plot the volcano.

> RNA-seq DE is **not** a t-test. Counts are over-dispersed; this workflow uses
> the count-appropriate **edgeR + limma-voom** pipeline. If R is unavailable the
> app tells you what to install and will not silently fall back to a t-test.

## Inputs

- **Count matrix**: genes as rows, samples as columns. A leading `geneID` column
  plus optional annotation columns (`geneSymbol`, `bioType`, `annotationLevel`)
  are recognized and carried through to the normalized-matrix output. **RSEM
  "expected counts" are often fractional** (multi-mapping reads) — for the
  edgeR/limma-voom path they are kept as-is (edgeR/voom accept non-integer
  counts, exactly like the reference pipeline); only DESeq2 rounds them (it
  requires integers). **ERCC spike-in rows (`^ERCC`) are removed** before
  modeling.
- **Sample metadata** (CSV/TSV/XLSX): one row per sample. **Required:** a
  sample-ID column matching the count columns, and a condition/group column.
  **Optional:** batch, covariates (e.g. `Age`), replicate/subject.
- **Optional config JSON** with `comparisons` (`{group1, group2}` list),
  `covariates`, and a reference group.

## Validation (before any analysis)

The app checks: counts are nonnegative and (near-)integer, no missing values,
duplicated gene ids handled, sample IDs match between counts and metadata, groups
have ≥2 replicates, and estimates how many low-count genes will be filtered. Clear
errors/warnings are shown; you fix inputs before running.

## The pipeline (method, accurately labeled)

Faithful to the reference script
`test_matrix/pipeline_cab_rnaseq_de_finalized_050924_cov_rep_fixed.R`:

1. **edgeR** `DGEList`; filter genes with `CPM > 1` in ≥ (smallest group size)
   samples; **TMM normalization** (`calcNormFactors`).
2. Design `~ [batch +] [covariates +] Group`, with `Group` releveled so the
   **reference group is the baseline**. The exact formula is reported.
3. **limma-voom** (`voom`) → `lmFit` → `contrasts.fit` → **`eBayes`**
   (empirical Bayes **moderated t-test**).
4. `topTable` per contrast (BH-adjusted), plus the voom-normalized matrix.

Reported method label: *"edgeR (TMM normalization + filtering) with limma-voom
and empirical Bayes moderated t-test."* The DE table columns are `logFC`,
`AveExpr`, `t`, `P.Value`, `adj.P.Val`, `B`.

## How it runs (robust + reproducible)

- Inputs are written to a temporary working directory; the R script is called
  via a subprocess **argument list** (not a shell string), so spaces and OneDrive
  paths are safe.
- stdout/stderr and an analysis log are captured; R and package versions are
  recorded; the design formula and contrasts are saved.
- Outputs: DE table(s), voom matrix, `method.json`, `versions.json`, log, and a
  populated `RnaSeqSpec`.

## Installing R

```r
if (!requireNamespace("BiocManager", quietly=TRUE)) install.packages("BiocManager")
BiocManager::install(c("edgeR", "limma"))
install.packages("jsonlite")
```

Set `MAKE_MY_FIGURE_RSCRIPT` to a specific `Rscript` if it is not on PATH. After
DE completes, the app auto-loads the DE table and draws a volcano (Mode A), and
**"Send normalized matrix to figure workspace"** loads the DE-produced normalized
(voom) matrix into the main window so you can make heatmaps, PCA, sample
correlation, and gene-level plots from it. DE tables, the normalized matrix, the
RnaSeqSpec, and the method report are all written to your chosen output folder.

## Reproducibility note

Validated against a real RSEM dataset: the normalized matrix reproduces the
reference voom output to machine precision and logFC is essentially identical.
Exact DE **p-values / FDR-significant-gene counts depend on the edgeR/limma
version** (the moderated-t statistic's empirical-Bayes/voom weights change
between releases) — so re-running with a different limma version gives
highly-concordant, not bit-identical, p-values. The app records the R and package
versions in the RnaSeqSpec so any run is reproducible against itself.
