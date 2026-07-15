# Differences from the published panel

| Aspect | Published (Kume 2024 Fig 5A) | This recreation |
|--------|------------------------------|-----------------|
| Plot kind | Volcano | Volcano (same) |
| x / y | log2 FC / -log10 padj | identical (same source values) |
| Point colour | all black | up=red, down=blue, n.s.=grey by threshold |
| Thresholds | none drawn | dashed |log2FC|=1 and padj=0.05 guides |
| Legend / counts | none | up/down legend + count subtitle |
| Gene labels | 16 red labels | 13 drawn (3 near-origin labels de-duped for overlap) |
| p-value origin | RaNA-seq padj | **read verbatim** (lossless inverse of published -log10 padj) |

None of these change the science: the same values are plotted and the labelled
genes land in the same places. The added colour/thresholds/legend are the app's
default publication styling and are transparent. Not a pixel-for-pixel copy;
never described as an "exact reproduction".
