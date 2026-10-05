# Phase 2 visual check — typography across canvas sizes

Eight plot types rendered at three canvas sizes, to be looked at rather than measured.
See `quality_audit/typography.md` for the system itself.

| file suffix | canvas | what to look for |
|---|---|---|
| `__default` | the style's own 5.12 × 3.69 in | must be identical to v1.1.1 — scaling does not engage here |
| `__4x2in` | pinned 4 × 2 in | the panel size in the brief; type scaled to 84% |
| `__4x4in` | pinned 4 × 4 in | square panel |

## Why these images exist

The automated width check passed on `volcano_plot__4x2in` while the image showed the
title clipped at both ends. A title is centred on its **axes**, not the figure, and the
axes are inset for the y-label and the outside legend — so a title 91% as wide as the
canvas still hung off both edges. Only looking at the render caught it.

Known and still visible in these images, tripwired in
`tests/test_typography_system.py` but not fixed in this phase:

- **outside legends are cut off at the default size** on 11 of 45 plot types. Look at
  `scatterplot_with_regression__default.png` (loses most of `Non_responder`) and
  `spatial_composition_map__default.png` (loses the end of `CD68+CD163+ macrophages`).
  No custom figure size is involved — this is the out-of-the-box output.
- at a pinned 4 × 2 in, the same thing on 12 plot types, plus **the x-axis label
  falling off the bottom** on 14.

All of it is legend and colourbar placement assuming the figure can be widened to make
room, which it cannot be once the size is pinned — and which it was not doing correctly
even at the default size. Layout work, not typography.

What this phase did fix, visible here: compare
`spatial_composition_map__default.png` with the figure described in
`quality_audit/typography.md` — the title's leading `C` was clipped and is now whole,
wrapped onto two lines. And `volcano_plot__4x2in.png`, whose title was cut off at both
ends and is now complete.
