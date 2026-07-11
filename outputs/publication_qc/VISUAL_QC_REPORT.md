# Visual QC report

Automated publication-readiness checks (`qa/publication_check.py`) run on every
render and are asserted for all 37 plot types across every style profile
(`test_publication_style`). Checks: font sizes (≥9pt labels / ≥8pt ticks),
tight-bbox clipping, missing axis labels, dense unrotated ticks, and inside-axes
legend overlap. Galleries were rendered and visually inspected.

| area | source | status | residual limitation |
|---|---|---|---|
| 37 plot types | `test_publication_style` (all profiles) | pass | — |
| v0.4 gallery (18 types) | `reports/v04_qa/_contact_sheet.png` | pass | — |
| v0.5 gallery (networks, clustering, volcano, annotations) | `outputs/style_qa_gallery/v0_5/_contact_sheet.png` | pass | dense force networks crowd labels (warned + thinned) |
| volcano label modes | v0.5 gallery | pass | very crowded requests warn + cap; adjustText best-effort |
| heatmap cluster strips + highlight | v0.5 gallery | pass | many highlighted rows warn |
| manual annotations (region/callout/panel label) | v0.5 gallery | pass | — |
| export non-empty + vector text | `test_reproducibility_export_qc` | pass | — |

Regenerate: `python scripts/generate_v05_qa_gallery.py` (and
`python scripts/generate_v04_qa_gallery.py`).

No clipped labels/legends, tiny text, blank exports, or stale-figure cases were
found in the generated galleries. Dense-network label crowding is the only
residual visual limitation and is mitigated by a warning + top-N label thinning.
