# Visual QC — Kume 2024 Figure 5A volcano recreation

Compared side-by-side with the stored published panel
(`../../reference_figures/kume2024_psoriasis_semaphorin/reference_panel.png`,
CC BY 4.0). See `../../side_by_side/kume2024_psoriasis_semaphorin.png`.

**Matches the published panel (kind + content):**
- Same plot kind (volcano), same axes (log2 fold-change vs -log10 padj) and
  the same overall point cloud shape.
- The genes labelled red in the paper appear at the same locations here:
  SPRR2F at the apex, then SERPINB4 / DEFB4B / S100A7A / CXCL8 / PI3 / SPRR2A /
  S100A8 / S100A7 / DEFB4A up-right, KRT16 / KRT5 / KRT10 low near the centre.

**Deliberate stylistic differences (recreation, not pixel copy):**
- The paper colours all points black and marks only the red gene *labels*; the
  app colours points by significance (up = red, down = blue, n.s. = grey), adds
  dashed |log2FC|=1 / padj=0.05 threshold guides, a legend with up/down counts,
  and an EnhancedVolcano-style count subtitle.
- 13 of the 16 red-labelled genes are drawn; SEMA4A, S100A9 and KRT14 sit in the
  crowded near-origin region and were dropped by the overlap-avoidance de-duper
  (they remain in the data and are recoverable by raising the label cap). This is
  disclosed, not hidden.
- Vector text preserved (SVG/PDF exported); 300 dpi PNG.

**Verdict:** publication-grade recreation of the KIND of figure in Kume et al.
2024 Figure 5A, faithful to the source values. Not pixel-identical; never claimed
as an exact reproduction.
