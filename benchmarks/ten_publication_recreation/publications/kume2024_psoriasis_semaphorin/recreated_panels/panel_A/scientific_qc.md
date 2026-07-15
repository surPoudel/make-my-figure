# Scientific QC — Kume 2024 Figure 5A volcano recreation

**Data traceability.** Every plotted value comes from eLife Figure 5-source data 1,
sheet "Figure 5A" (`elife-97654-fig5-data1-v1.xlsx`): gene symbol, log2 fold-change,
-log10 padj — 9,999 genes. The processed table adds `padj = 10**(-neglog10_padj)`,
the **exact lossless inverse** of the published column; no DE statistics were
recomputed (the app never runs DE — p-values are read verbatim).

**Landmark checks against the published panel (viewed):**

| Gene | log2FC | -log10 padj | padj | matches published position |
|------|-------:|------------:|------|----------------------------|
| SPRR2F | 4.99 | 21.47 | 3.4e-22 | top point, top-right — yes |
| DEFB4B | 5.69 | 14.58 | 2.6e-15 | far right, high — yes |
| SERPINB4 | 4.82 | 15.98 | 1.1e-16 | upper right — yes |
| KRT16 | 1.73 | 2.74 | 1.8e-3 | mid, just right of origin — yes |
| SEMA4A | -0.17 | 0.63 | 0.23 | near origin, ~unchanged — yes |

- Axis ranges: log2FC ∈ [-4.21, 6.01], max -log10 padj = 21.47 — consistent with
  the published axes (x roughly -5..6, y 0..~22).
- Significant counts at |log2FC|≥1 & padj<0.05: **53 up, 135 down** (9,811 n.s.).
  The published panel does not print counts; these follow from the source values
  at the conventional thresholds and are shown transparently in the subtitle.

**Invariant honoured:** no fabricated statistics; SEMA4A (the paper's subject
gene) correctly sits at the origin, i.e. essentially unchanged in NL — matching
the paper's narrative that its downregulation is a *lesional* feature.
