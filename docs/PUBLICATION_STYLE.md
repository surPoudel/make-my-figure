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

## Publication controls layout (Streamlit)

The Streamlit sidebar groups the Publication controls into clear sections: **①
Figure** (width preset, DPI, margins, auto-fix layout), **② Typography** (palette,
title/axis/tick/annotation sizes, marker size, line & spine width, grid), **③ Axes &
labels** (title, x/y labels, x/y tick angle, label & title padding), **④ Legend**
(location incl. inside/outside positions, size, outside toggle), and **⑤ Colorbar**
(location/padding/size — heatmap, clustered heatmap, confusion matrix, enrichment dot).
Plot-specific controls stay in the mapping section, and per-label annotation
positioning lives in the plot's "Label points" expander. Controls that don't apply to
the active plot are flagged, not silently ignored. (The desktop app shares the same
engine; grouping its Qt panel identically is a follow-up.)
