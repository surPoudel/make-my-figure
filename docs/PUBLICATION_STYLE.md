# Publication style

Make My Figure has **one visible style identity: Publication** — a general,
manuscript-ready visual style. It is *not* a journal template and never claims to
guarantee compliance with any journal's requirements. Legacy journal-named profiles
(`nature_like` / `science_like` / `cell_like` and their `*_learned` variants) migrate
to `publication` on load.

## Fonts

Arial-first stack with safe fallbacks (`Arial → Helvetica → DejaVu Sans →
sans-serif`); a single family name entered in the UI is expanded into that stack so
Matplotlib resolves it (and degrades gracefully if Arial isn't installed). **No font
files are committed.**

## Palettes

Selectable palettes include `publication`, `colorblind_safe`, `high_contrast`, and
`grayscale` (a fully monochrome **black-and-white** option many publications use).
Grayscale/colorblind palettes also drive heatmap colormaps and — as of the plot-aware
fix — **network group node colors**.

## Plot-aware controls

Style controls are applied where they make sense and flagged where they don't — see
[PLOT_STYLE_CONTROLS.md](PLOT_STYLE_CONTROLS.md). Every control either affects the
active plot or is reported as not applicable; there are no silent no-op controls.

## Reproducibility & export

All style choices are stored in the PlotSpec (`spec["style"]`) and plot-specific color
choices in the mapping, so they round-trip and are reproduced on re-render. SVG/PDF
text stays editable (vector); PNG/PDF/SVG exports honor the selected colors and should
match the on-screen preview.
