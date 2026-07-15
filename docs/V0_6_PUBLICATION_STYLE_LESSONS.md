# v0.6 Publication style lessons (from real-data benchmark recreations)

These lessons come from recreating **13 panels across 6 real, permissively-licensed
public datasets and 10 distinct plot types** through Make My Figure's single
**Publication** style (see `benchmarks/publication_recreation/`). They describe
**general, aggregate** publication design defaults — not per-panel hacks, and not
any claim of official journal compliance.

## What held up (no change needed)

Across all 13 panels the built-in Publication style cleared the advisory
publication-readiness check (`qa/publication_check.py`) with **no clipping,
overlap, tiny-font, or dense-tick warnings**. So no shared style tokens were
changed for this benchmark — the readable Publication defaults (title > axis >
tick > annotation font hierarchy, ~1.1pt spines, hidden top/right spines,
colorblind-aware categorical palette, editable vector export) were already
publication-grade on real data. This is the intended outcome of a single, opinionated
default style.

## General polish applied (via PlotSpec, not per-panel hacks)

Iteration 2 of every recreation applies **PlotSpec-level** overrides only:

- **Legend placement:** `style.legend_outside = True` for multi-series panels
  (scatter colored by species/continent, PCA colored by group) so the legend never
  competes with the data. Applied generally by category, not per figure.
- **Export resolution:** raise export DPI to 400 for the final pass — vector
  (SVG/PDF) remains the primary publication artifact; the raster is a high-DPI
  preview.
- **Physical size:** wide layouts (network, heatmap, PCA, confusion matrix) use the
  double-column width; others single-column — a general size heuristic by plot type.

## Observations worth carrying into the style engine (general, future)

- Keep an **axis-unit nudge**: several real panels have units in the data (mm, g,
  years, US$) that belong in axis labels — a general "did you set units?" advisory is
  useful (already an advisory in the readiness check).
- **Legend-outside by series count** is a good general rule (≥4 series → outside);
  encode it once rather than per plot type.
- **Heatmap colorbars** read best slim with few ticks; **network** layouts benefit
  from a fixed seed for reproducibility (used: `seed=42`).

## Limitations

- These panels use canonical public datasets; they exercise the renderers broadly
  but do not cover every plot type (survival, volcano/MA from a precomputed DE table,
  Manhattan/Q-Q, dose-response, enrichment, oncoprint/lollipop, swimmer/spider) —
  those await a license-verified real dataset (see
  `benchmarks/publication_recreation/reports/failed_or_rejected_candidates.md`).
- No published figure image is stored, so lessons are from our own recreations vs
  described targets, not pixel comparison.
