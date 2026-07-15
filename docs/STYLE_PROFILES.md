# Style Profiles & Publication-Ready Defaults

Make My Figure produces **publication-style figures by default** — the first plot
you get is already readable and clean, without manual tweaking. Formatting
controls are for *refinement*, not for fixing bad defaults.

> **Publication style, not an official template.** Make My Figure uses a single
> `publication` style — a general manuscript-ready visual style. It does **not**
> provide official journal templates or guarantee compliance with, or acceptance
> by, any journal. (Older saved files that named a removed profile are migrated to
> Publication automatically.)

## The shared style engine

All renderers (desktop **and** Streamlit) consume one style model —
`make_my_figure_core/styles/engine.py` (`StyleProfile`). This guarantees the two
apps never diverge. A profile carries tokens for:

- **Typography** — font family (Arial → Helvetica → DejaVu Sans → sans-serif),
  axis-label / tick / legend / legend-title / annotation / title / panel-label
  sizes, weight, text color.
- **Axes** — spine width, tick width/length/direction, top/right spine visibility,
  grid on/off + width/alpha.
- **Data marks** — scatter marker size, marker edge width, marker alpha, line
  width, regression line width, error-bar line width + cap size, bar edge width.
- **Legend** — frame on/off, location, outside-plot flag, number of columns.
- **Colors** — categorical palette, sequential + diverging colormaps.
- **Sizing / export** — width presets (`default`, `single`, `onehalf`, `double`),
  export DPI, preferred formats.

### Default values (publication)

| Token | Default |
|---|---|
| Axis label | 12 pt |
| Tick label | 10 pt |
| Legend / legend title | 10 / 11 pt |
| Annotation | 9.5 pt |
| Title | 13 pt |
| Axis/spine width | 1.1 pt · Tick width 1.0 pt · length 4.5 pt |
| Scatter marker | s = 45, white edge |
| Regression line | 2.0 pt · Error bar 1.1 pt, cap 3.5 |
| Bar edge | 0.9 pt |
| Palette | colorblind-aware, high-contrast (Okabe–Ito-derived) |

Colors avoid Matplotlib's default cycle; the palette is colorblind-aware and
high-contrast. Alternative named palettes: `publication`, `colorblind_safe`,
`high_contrast`, `grayscale`.

## Adjusting the style

- **Desktop app** — the **"5. Style (publication defaults)"** panel: palette,
  axis/tick/legend/annotation sizes, marker size, line width, axis/spine width,
  legend-outside, grid, and **Reset to publication defaults**. Figure width is in
  "Labels & size".
- **Streamlit app** — the **"6. Formatting → Publication style controls"**
  expander exposes the same options.

Both write a `spec["style"]` override dict that
`StyleProfile.with_overrides(...)` applies on top of the chosen profile, so a
tweak never permanently changes the profile.

## Learned profiles

`*_learned` profiles encode *aggregate* visual conventions derived from a local
open-access reference library — see
[STYLE_REFERENCE_AUDIT.md](STYLE_REFERENCE_AUDIT.md). No figures or datasets are
copied.

## Publication-readiness check

After each render the app runs a lightweight check (`make_my_figure_core/qa/`)
that flags small text, legend overlap, likely clipping, missing labels, dense
tick labels, weak contrast, and small figures. It is advisory and never blocks
export. Regenerate a full visual QA gallery with
`python scripts/generate_style_qa_gallery.py`.
