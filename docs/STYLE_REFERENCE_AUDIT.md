# Style Reference Audit

_Generated 2026-07-01 by `scripts/build_learned_styles.py`._

> **How references are used.** Downloaded papers and figures are used as *local visual references* to derive aggregate publication plotting conventions. The app does **not** copy published figures, does **not** reproduce copyrighted datasets unless explicitly licensed, and does **not** claim official journal compliance. Only aggregate measurements (not individual figures) are stored in the repository; raw figure bitmaps remain local-only.

All reference papers are open access under CC BY. See each paper's `figure_library/<group>/<paper>/provenance.json` for title, DOI, journal, year, license, and URLs.

## Aggregate observations by journal family

| Family | Papers | Figures | Images measured | Median aspect (w/h) | Licenses |
|---|---|---|---|---|---|
| nature | 4 | 21 | 21 | 1.151 | CC BY |
| science | 2 | 12 | 12 | 1.255 | CC BY |
| cell | 4 | 15 | 15 | 0.9 | CC BY |

## Conventions encoded into the learned profiles

These are *curated, aggregate* conventions informed by the references (not pixel-measurements of any single figure), encoded in `style_profiles/learned/*.json`:

- **Aspect ratios** — default panel aspect per family (see each profile's `layout`).
- **Panel label style** — bold; consistent case across panels.
- **Typography** — small sans-serif (Arial/Helvetica fallback), ~7 pt base / 8 pt title.
- **Axis / spine line width** — thin (0.5–0.6 pt); top/right spines hidden; no grid.
- **Tick style** — short, outward ticks.
- **Legend placement** — frameless, auto-placed.
- **Color palette** — colorblind-aware (Okabe–Ito-derived) categorical palettes.
- **Markers / error bars** — small markers; SEM error bars with small caps.
- **Heatmap colorbar** — thin right-side colorbar; diverging map (RdBu_r / PuOr_r).
- **Volcano thresholds/labels** — |log2FC| ≥ 1, p ≤ 0.05, top-N labeled.
- **Multi-panel spacing / export size** — one/two-column widths in mm; 300 dpi raster.

## What is NOT extracted

Exact fonts, precise point sizes, and line widths cannot be reliably recovered from rasterized multi-panel figures and are therefore **not** claimed as measurements; the learned profiles use curated defaults for those. Only image aspect ratios and paper/figure counts are measured programmatically.
