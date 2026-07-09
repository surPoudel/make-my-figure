# Volcano plots from precomputed DE results

Upload a differential-expression result table (e.g. a limma/edgeR `topTable`
such as `test_matrix/Ctrl_vs_Treatment_DE.txt`) and get a publication-grade
volcano. **P-values are read from your table — never recomputed.**

## Column auto-detection

These roles are detected from common aliases (case-insensitive) and are editable
in the mapping UI:

| Role | Recognized names |
|------|------------------|
| gene id | `gene`, `gene_id`, `GeneID`, `feature_id`, `Ensembl`, or the unnamed row-name column |
| gene symbol | `geneSymbol`, `symbol`, `gene_name`, `external_gene_name` |
| log fold change | `logFC`, `log2FoldChange`, `log2FC`, `LFC` |
| p-value | `P.Value`, `PValue`, `pvalue`, `p_value` |
| adjusted p | `adj.P.Val`, `FDR`, `padj`, `qvalue`, `adj_p_value` |
| average expression | `AveExpr`, `logCPM`, `baseMean`, `mean_expression` |
| statistic | `t`, `F`, `LR`, `stat`, `WaldStatistic` |

## Thresholds and classification

Genes are classified **Up / Down / Not significant** from:

- absolute log2 fold-change cutoff (default 1.0),
- adjusted-p (FDR) or raw-p cutoff (default 0.05),
- whether to threshold on the adjusted p-value (recommended) or the raw p-value.

The volcano is drawn from this classification, so the figure matches the DE
result's own thresholds exactly. The subtitle auto-summarizes:
`Up: N | Down: N | FDR < 0.05, |log2FC| >= 1`.

> Real datasets can have **0** genes at |log2FC|≥1 & FDR<0.05 when effects are
> subtle. That is honest, not a bug — loosen the cutoffs (or threshold on raw p)
> if appropriate for your study, and say so in the methods.

## Labels

- top-N most significant genes, and/or an explicit list of selected genes,
- label by gene symbol or gene id,
- label only significant genes (default) or all,
- overlap avoidance via `adjustText` when installed, otherwise a distance-based
  fallback. Labels never clip on SVG/PDF/PNG export.

## Exports

Volcano SVG/PDF/PNG, the filtered DE table, the significant-gene table, the
PlotSpec, an `*.rnaseq_spec.json` (thresholds + detected columns), and a method
report. The y-axis label follows your choice: `-log10 adjusted p-value` or
`-log10 p-value`.
