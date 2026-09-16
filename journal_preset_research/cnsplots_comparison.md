# cnsplots as prior art for journal-style figure presets

Source studied: https://github.com/faridrashidi/cnsplots (v0.7.0, BSD-3-Clause, Python, ~670 stars,
created 2023-01, last push 2026-09-13). Files read: README.md, LICENSE.md, pyproject.toml,
docs/{index,getting_started,installation,settings,api}.md, src/cnsplots/{_settings,_setup,_sizing,
_palettes,_svg,_multipanels,_utils}.py, src/cnsplots/_agent_skill/cnsplots/SKILL.md,
examples/{figure_setup,settings,palettes}.py, and the overview showcase image.

Compared against MakeMyFigure (this worktree): `make_my_figure_core/presets.py`,
`make_my_figure_core/styles/engine.py`, `make_my_figure_core/styles/publication_style_engine.py`,
plus `style_profiles/starter_journal_style_profiles.json` for context. Read-only; no code was copied.

## Summary

cnsplots is a matplotlib/seaborn wrapper that ships roughly 30 plot functions (box, violin, volcano,
Kaplan-Meier, ROC, heatmap, Sankey, UpSet, etc.), built-in statistical annotation (statannotations,
scipy, lifelines), a multipanel layout manager with automatic A/B/C labels, and an SVG export path that
round-trips through PDF and MuPDF `mutool` so text stays editable in Adobe Illustrator.

Despite the name ("CNS" = Cell/Nature/Science) and the README tagline "Publication-Ready Scientific
Plots for Cell, Nature, and Science Journals", **cnsplots has no per-journal presets**. There is a
single global house style (`cns.settings`, applied through `setup_matplotlib()`), and "Cell",
"Nature" and "Science" exist only as names of qualitative colour palettes. The house style is
small-type, thin-line, open-spine matplotlib: Helvetica, 8 pt titles/axis labels, 7 pt ticks/legend,
0.5 pt spines, 2 pt ticks, no grid, no legend frame, transparent tight-bbox export at 288 dpi.
Figure sizes are specified in points (default 150x150 pt single figure, 540 pt multipanel width)
with `unit="mm"|"in"` conversion.

Its main value as prior art is therefore not the journal encoding (there is none) but: (a) a
validated, settings-object approach with `reset()` and `context()`; (b) sizing in physical units at
canvas level with a clear DPI-vs-physical-size separation; (c) the multipanel API; (d) the Illustrator
SVG pipeline; (e) integrated p-value annotation defaults; (f) a rich palette registry including
`OkabeIto`, `TolBright`, `TolMuted`; (g) an emitted ggplot2 theme string for Python/R consistency.

MakeMyFigure already goes further on the preset side (a JSON preset format with a data/style scope
split, style-vs-full modes, layout presets, a preset store, plot-type capability gating) and on
honesty (the codebase explicitly refuses journal-named styles and documents them as "*-like" only).

## Targets and encoding

| Question | cnsplots | Notes |
|---|---|---|
| Journals named | Cell, Nature, Science (README, SKILL.md, docstrings); Lancet, NEJM, JAMA, JCO (palette names only) | Names appear in marketing text and palette registry, nowhere as style presets |
| Per-journal presets? | **No** | One global style; no `theme_nature()`-style functions, no width tables per journal |
| Encoding mechanism | `cns.settings` (a validated attribute container, ~85 keys) rendered to `matplotlib.rcParams` by `setup_matplotlib()`; `setup_ax(ax)` re-applies to a foreign axes; `settings.context(**kw)` scoped override wrapping `mpl.rc_context()` | Not ggplot2; pure matplotlib. `setup_ggplot()` returns an R `theme()` source string for parity |
| Palettes | Registry of ~28 qualitative + 7 continuous entries; lazy factories; `register_palette()`; `available_palettes(kind)` | Journal-named palettes hard-coded as hex lists |
| Sizing | Points at canvas level, `unit` in {"pt","in","mm"}; display dpi 144, export dpi 288, physical size independent of both | Column widths only appear as comments in one example (89, 120, 178, 183 mm) with "check the target journal's current guidelines" |
| Multipanel | `multipanel(max_width=540)` + `panel("A", width, height)`; wraps rows automatically; bold uppercase labels at `title_fontsize` | Panel size = axes area, margins in points, label pads in display pixels |
| Export | `savefig()` -> SVG via PDF+mutool (editable text), PDF fonttype 42, svg.fonttype none, transparent, tight bbox, 0.01 in pad | Falls back to plain matplotlib SVG with a RuntimeWarning if mutool absent |
| Stats | `pairs=`, `test=`, `p_adjust=` on categorical plots; `pvalue_format` in {star, threshold, full}; prints a methods sentence | Statistical tests are integrated into the plot call |

## Parameters controlled (table)

Defaults of the single cnsplots house style, grouped as in `docs/settings.md`. "MMF" column shows
the closest MakeMyFigure `StyleProfile` token or preset key (from `engine.py` / `presets.py`).

| Group | cnsplots setting | Default | Maps to matplotlib | MMF equivalent |
|---|---|---|---|---|
| Typography | `font_family` | sans-serif | font.family | `font_family` (concrete list) |
| | `font_sans_serif` | Helvetica, Helvetica Neue, Arial, Nimbus Sans, Liberation Sans, DejaVu Sans | font.sans-serif | `_FONT_STACK` Arial, Helvetica, DejaVu Sans |
| | `mathtext_fontset` | custom | mathtext.fontset | none |
| | `title_fontsize` | 8 | font.size, axes.titlesize, axes.labelsize, legend.title_fontsize | `title_font_pt` 13, `axis_font_pt` 12, `base_font_pt` 11 |
| | `title_fontweight` | bold | axes.titleweight | `title_font_weight` bold |
| | `legend_fontsize` | 7 (None -> inherit title) | legend.fontsize, xtick/ytick.labelsize | `legend_pt` 10, `tick_label_pt` 10 |
| | `legend_title_fontsize` | None (inherit) | legend.title_fontsize | `legend_title_pt` 11 |
| | `pvalue_fontsize` | "small" | annotation text | `annotation_pt` 9.5 |
| | `panel_label_fontname` / `panel_label_fontweight` | None / bold | text artist | `panel_label_pt` 13 (weight not separate) |
| Axes | `axes_linewidth` | 0.5 | axes.linewidth | `spine_width_pt` 1.1 |
| | `axes_spines_top` / `axes_spines_right` | False / False | axes.spines.* | `show_top_spine` / `show_right_spine` False |
| | `axes_edgecolor` / `axes_labelcolor` | black / black | axes.edgecolor, axes.labelcolor | `text_color` #1a1a1a |
| | `axes_grid` | False | axes.grid | `grid` False (+ `grid_width`, `grid_alpha`) |
| | `axes_titlelocation` | center | axes.titlelocation | none |
| | `axes_labelpad` / `axes_titlepad` | 2 / 4 | axes.labelpad, axes.titlepad | layout `x_label_pad`, `y_label_pad`, `title_pad` |
| | `axes_xmargin` / `axes_ymargin` | 0.05 / 0.05 | axes.xmargin/ymargin | none |
| Ticks | `xtick_major_size` / `ytick_major_size` | 2 / 2 | *tick.major.size | `tick_length` 4.5 |
| | `xtick_major_width` / `ytick_major_width` | 0.6 / 0.6 | *tick.major.width | `tick_width` 1.0 |
| | `xtick_major_pad` / `ytick_major_pad` | 1 / 1 | *tick.major.pad | layout `x_tick_pad`, `y_tick_pad` |
| | `xtick_bottom` / `ytick_left` | True / True | xtick.bottom, ytick.left | none |
| | `xtick_color` / `ytick_color` | black | *tick.color | `text_color` |
| | `xtick_alignment` / `ytick_alignment` | center / center_baseline | *tick.alignment | layout `x_tick_horizontal_alignment`, `x_tick_vertical_alignment` |
| | `xtick_labelrotation` / `ytick_labelrotation` | 0 / 0 | setup_ax only | layout `x_tick_rotation`, `y_tick_rotation` |
| | tick direction | (matplotlib default, out) | not exposed | `tick_direction` |
| Legend | `legend_frameon` | False | legend.frameon | `legend_frameon` False |
| | `legend_markerscale` | 0.5 | legend.markerscale | none |
| | `legend_handlelength` / `legend_handleheight` | 0.7 / 0.7 | legend.handle* | none |
| | `legend_handletextpad` | 0.3 | legend.handletextpad | none |
| | `legend_out_loc` / `legend_out_bbox_to_anchor` / `legend_out_markerscale` | upper left / (1, 1.02) / 1 | `take_legend_out()` helper | `legend_outside`, `legend_loc`, `legend_ncol`, layout `legend_location` |
| Data marks | (not exposed as settings) | matplotlib defaults | lines.linewidth etc. | `line_width_pt` 1.8, `marker_size` 45, `marker_edge_width`, `marker_alpha`, `regression_line_width`, `errorbar_line_width`, `errorbar_capsize`, `bar_edge_width` |
| Palettes | `palette_qual` | Ecotyper1 | axes.prop_cycle | `palette_name` / `palette` (publication, colorblind_safe, high_contrast, grayscale) |
| | `palette_seq` | gnuplot | image.cmap | `sequential_cmap` viridis, `diverging_cmap` RdBu_r |
| | registry | Set1-3, Pastel1-2, Paired, Dark2, Accent, Tableau, Bold, BlueRed, ECharts, Ecotyper1-6, Cell, Nature, Science, Lancet, NEJM, JAMA, JCO, OkabeIto, TolBright, TolMuted; continuous parula, gnuplot, hot, BuRd_custom, WhYlOrRd_custom, OrBu_custom, YlGnBu_custom | registered as colormaps | 4 user palettes + hidden legacy aliases |
| Figure size | `figure_width` / `figure_height` | 150 / 150 pt (canvas) | figure(figsize) | `WIDTH_PRESETS_MM` single 110, onehalf 140, double 180, default 130; `aspect`; output `width_mm`/`height_mm` |
| | `figure_dpi` | 144 (display) | figure.dpi | figure.dpi 110 |
| | `unit` argument | pt / in / mm | conversion | mm throughout |
| Multipanel | `multipanel_max_width` | 540 pt (190.5 mm) | figure width | layout preset (`.mmflayout.json`), `subplot_wspace/hspace`, margins |
| | `panel_width` / `panel_height` | 150 / 150 pt (axes area) | axes size | per-panel in MultiPanelFigure |
| | `panel_margin_top/bottom/left/right` | 0 / 10 / 0 / 10 pt | layout | `margin_*` layout keys |
| | `panel_pad_left` / `panel_pad_top` | 0 / 0 px | label offset | none |
| | `multipanel_title_loc` / `_height_min` / `_height_pad` | center / 12 / 4 | title band | none |
| Export | `savefig_dpi` | 288 | savefig.dpi | `export_dpi` 300, output `dpi` |
| | `savefig_bbox` / `savefig_pad_inches` | tight / 0.01 | savefig.bbox, savefig.pad_inches | savefig.bbox tight |
| | `savefig_transparent` | True | savefig.transparent | none (opaque) |
| | `svg_fonttype` / `pdf_fonttype` | none / 42 | svg.fonttype, pdf.fonttype | none / 42 / ps 42 |
| | SVG post-processing | PDF -> mutool -> cleaned SVG | `_svg.py` | none |
| | `preferred_exports` | (not a setting) | | `preferred_exports` svg, pdf, png |
| Stats display | `pvalue_format` | star | annotation | statistics `annotation` block |
| | `pvalue_loc` | inside | annotation | none |
| | `annotation_auto_contrast` | True | white/black text by luminance | none |
| | `setup_ax_colorbar_label` | "FDR q-val" | colorbar | `colorbar_label` (capability-gated) |
| Integration | `scanpy_*`, `ggplot_*` | see source | scanpy.set_figure_params, R theme string | none |

Fixed (not user-settable) in cnsplots: tick direction, line/marker widths, panel label letter case
(always the string passed), legend location per plot, colour of significance bars.

## Evidence used

Essentially none is cited. The only statements connecting the style to journals are:

- README: "Pre-configured styles matching Cell, Nature, and Science journal requirements" and
  "Inspired by the visualization standards of Cell, Nature, and Science journals."
- `setup_matplotlib` docstring: "This configuration follows journal guidelines for Cell, Nature, and
  Science."
- `examples/figure_setup.py`: a comment block listing 89 mm (~252 pt), 120 mm, 183 mm (~519 pt),
  178 mm (~505 pt) as "Example publication widths (check the target journal's current guidelines)",
  and noting the 540 pt multipanel default equals 190.5 mm.
- Palette docstrings: "Custom Cell-inspired journal palette", "Nature Reviews Cancer-inspired
  palette", "Science-inspired journal palette".

No URLs to author guidelines, no per-journal minimum font sizes, no colour-vision statements
beyond including OkabeIto/Tol palettes, no documentation of why 8/7 pt or 0.5 pt were chosen. The
89/183 mm values match Nature's commonly published single/double column widths; 120 mm and
178 mm are unattributed. The `Nature`, `Science`, `Lancet`, `NEJM`, `JAMA`, `JCO` hex lists appear
identical to the corresponding palettes in the R package ggsci (npg, aaas, lancet, nejm, jama, jco),
which is GPL-3 licensed and is not credited by cnsplots.

## License and attribution implications

cnsplots is released under the BSD 3-Clause License (LICENSE.md, "Copyright (c) 2023-2026, Farid
Rashidi"). Operative terms, quoted:

> Redistribution and use in source and binary forms, with or without modification, are permitted
> provided that the following conditions are met:
>
> 1. Redistributions of source code must retain the above copyright notice, this list of conditions
>    and the following disclaimer.
>
> 2. Redistributions in binary form must reproduce the above copyright notice, this list of
>    conditions and the following disclaimer in the documentation and/or other materials provided
>    with the distribution.
>
> 3. Neither the name of the copyright holder nor the names of its contributors may be used to
>    endorse or promote products derived from this software without specific prior written
>    permission.
>
> THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR
> IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
> FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. [...]

Implications for MakeMyFigure:

- **Ideas, defaults, and API shapes are not covered by copyright.** Adopting a settings-context
  pattern, a `unit=` argument, or the numeric defaults (8 pt / 7 pt / 0.5 pt) requires no attribution.
- **Copying code (or close paraphrase) does.** If any cnsplots source were copied or adapted, the
  file would need to retain the copyright notice, the conditions and the disclaimer, and the
  distributed documentation would need the same. This document deliberately copies no code and this
  research does not create that obligation.
- **Hex palettes:** the Cell/Ecotyper lists are cnsplots' own creation; if we ever reused them
  verbatim, treat them as BSD-3 content (notice retention). The Nature/Science/Lancet/NEJM/JAMA/JCO
  lists appear to originate from ggsci (GPL-3), so reusing them via cnsplots would not launder the
  licence; avoid them entirely (MakeMyFigure already uses Okabe-Ito and its own palettes).
- **Clause 3:** we may not use "cnsplots" or "Farid Rashidi" to promote MakeMyFigure. Citing it as
  prior art in internal research documents is fine.
- The README's citation request (BibTeX) is a courtesy request, not a licence condition.

## Features useful to MakeMyFigure

1. **Scoped style context with rcParams restore.** `settings.context(...)` wraps `mpl.rc_context()`
   so temporary overrides are undone even on exception, and existing artists keep their properties.
   MakeMyFigure has `StyleProfile.apply()` returning an `rc_context`; a preset-level context that
   also restores the active preset would make "preview this preset" safe in the GUI.
2. **Physical units at the canvas with an explicit `unit` argument** and the documented separation
   of display dpi, export dpi and physical size. MakeMyFigure is mm-only; exposing pt and in for
   users porting from other tools costs little.
3. **Tiny, validated settings object with self-documenting `repr`.** Every setting has a validator
   and a docstring, and unknown attributes fail loudly (`__setattr__` guard). MakeMyFigure's
   `STYLE_TOKEN_KEYS` drops unknown keys with a note; a per-token validator (type, range) would
   catch e.g. negative font sizes at preset-load time.
4. **`setup_ax(ax)` to restyle a foreign axes** (seaborn, scanpy, gseapy output). Relevant to the
   figure-import path (`figure_import.py`): apply Publication tokens to an axes we did not create.
5. **Multipanel wrapping by width** with per-panel axes-area sizing and automatic label placement.
   MakeMyFigure's layout presets store geometry; a `max_width` wrap mode for many small panels is a
   plausible addition.
6. **Editable-text SVG pipeline** (PDF -> mutool -> SVG, fonttype 42 so glyphs keep Unicode). Our
   `svg.fonttype = none` already keeps text editable; the cnsplots note that Type 3 fonts lose the
   Unicode map for symbols such as the superscript minus is a useful test case for our PDF export.
7. **P-value formatting policy as a style token** (`star` / `threshold` / `full`, inside/outside,
   auto-contrast text). Our statistics block has `annotation`; making the format a named enum in the
   style preset improves portability across labs.
8. **Methods sentence emitted with the plot** ("P-values were determined by two-sided Welch's
   t-test."). MakeMyFigure has reports and QA; emitting the exact methods sentence into the figure
   package is a natural extension.
9. **Palette registry with `register_palette` and kind-filtered discovery**, plus Tol Bright/Muted
   alongside Okabe-Ito.
10. **An agent skill shipped in the package** (`cnsplots skill install`) documenting the workflow and
    statistical-integrity rules; a similar `SKILL.md` for MakeMyFigure would help Claude Code users.
11. **ggplot2 theme emission** so R users get a matching theme; low cost, useful for mixed labs.

## Features MakeMyFigure already supports

- rcParams-backed style tokens (`StyleProfile.rc_params()`), including tick direction, grid
  width/alpha, line/marker/errorbar/bar widths that cnsplots does not expose.
- Concrete font family list with installed-font filtering (cnsplots relies on the generic
  `sans-serif` family plus a fallback list; MakeMyFigure documents why the concrete list is needed
  for exports outside the rc context).
- Physical column-width presets in mm (single/onehalf/double/default) and `aspect`.
- Editable-text export (`svg.fonttype none`, `pdf.fonttype 42`, `ps.fonttype 42`), 300 dpi default.
- Colour-blind-aware default palettes, palette-driven continuous colormaps, grayscale variant.
- Open top/right spines, no grid, frameless legend, bold titles.
- Legend-outside heuristic keyed on series count (`recommended_overrides`).
- A serialised preset format (`.mmfpreset.json`) with `style` vs `full` modes, registry-driven scope
  classification, `apply_preset` reporting unsatisfied column roles, layout presets
  (`.mmflayout.json`), a preset store and safe filenames. cnsplots has no persisted preset at all;
  settings live only in the Python process.
- Plot-type capability gating with warnings for ignored controls (`capabilities.py`); cnsplots
  applies rcParams globally with no per-plot awareness.
- Explicit "*-like, not a template" language and legacy-alias migration of journal names to
  `publication`.

## Features MakeMyFigure can improve upon

- **Honest journal encoding.** cnsplots shows the failure mode to avoid: journal names in the
  title, one style underneath. If journal presets are added, each must carry a provenance block
  (guideline URL, retrieved date, which values are verbatim from the guideline vs. house choices).
  `starter_journal_style_profiles.json` already has a `notice`; extend it per value.
- **Two type scales.** cnsplots' 8/7 pt is a print scale; MakeMyFigure's 11-13 pt is a screen scale
  (`_parse_profile` deliberately ignores the ~7 pt starter values). A preset could carry both a
  "print at column width" scale and a "screen/slide" scale with an explicit switch, instead of
  clamping learned values upward.
- **Physical-size fidelity on export.** cnsplots documents that `bbox_inches="tight"` changes the
  saved size and offers `bbox_inches=None` to keep the requested canvas. MakeMyFigure always uses
  tight bbox; journal presets that promise "89 mm wide" need the fixed-canvas option.
- **Legend geometry tokens** (marker scale, handle length/height, handle-text pad) are missing from
  `StyleProfile`; they matter at small print sizes.
- **Axes margins** (`axes.xmargin/ymargin`) and title location are absent.
- **Panel label controls**: MakeMyFigure has `panel_label_pt` but no weight/case/offset tokens;
  cnsplots exposes weight, font name and pixel offsets.
- **Validation at token level** (see item 3 above).
- **`setup_ax`-style re-styling of imported figures.**

## Ideas deliberately NOT copied (and why)

- **Journal-named palettes (`Cell`, `Nature`, `Science`, `Lancet`, `NEJM`, `JAMA`, `JCO`).** They
  imply endorsement or house colours that the journals do not prescribe, several appear to be
  ggsci (GPL-3) values, and MakeMyFigure has already removed journal names from the UI
  (`USER_PALETTES`, `list_profiles` forbidden-token filter).
- **Claiming a single style "follows journal guidelines for Cell, Nature, and Science".** No
  guideline is cited; the three journals differ in column width and figure format requirements.
  MakeMyFigure's docstrings state the opposite and should keep doing so.
- **Global mutable `settings` singleton as the source of truth.** Convenient in notebooks, but it
  is process-local, unserialisable and order-dependent. MakeMyFigure's file-based presets with
  scope classification are the better model for reproducibility.
- **Points as the default unit.** Journals publish widths in mm; keep mm primary and add pt/in as
  conversions only.
- **Transparent background by default.** Fine for Illustrator compositing, surprising for PNG
  previews in slides and for reviewers; keep opaque default with an export toggle.
- **`gnuplot` as default sequential colormap** and `Ecotyper1` (a red/blue/green cycle that is not
  colour-blind-safe) as default qualitative palette; MakeMyFigure's Okabe-Ito-derived defaults are
  more defensible.
- **Bundling statistics with plotting functions.** MakeMyFigure keeps tests in the `statistics`
  block of the PlotSpec so the analysis is declared, versioned and reportable, not a keyword
  argument on a draw call.
- **Hard dependency on an external binary (mutool) for the headline export feature.**
- **Heavy mandatory dependency set** (scanpy, lifelines, gseapy, comprisk, pycomplexheatmap, etc.).

## Risks (trademark/endorsement wording it uses)

cnsplots uses journal names prominently and without qualification:

- Repository description: "Toolkit for generating publication-quality plots for Cell, Nature and
  Science journals".
- README H2: "Publication-Ready Scientific Plots for Cell, Nature, and Science Journals";
  "Pre-configured styles matching Cell, Nature, and Science journal requirements"; "Figures styled
  for Cell, Nature, and Science journals".
- Docstring: "This configuration follows journal guidelines for Cell, Nature, and Science."
- SKILL.md trigger: "Cell/Nature/Science-style visualization".
- Palette identifiers `Cell`, `Nature`, `Science`, `Lancet`, `NEJM`, `JAMA`, `JCO` exposed as public
  API strings and registered as matplotlib colormap names (global namespace).
- Only hedge present: "Inspired by the visualization standards of Cell, Nature, and Science
  journals" in Acknowledgments, and "-inspired" in palette docstrings.

The package name itself ("cns") leans on the journals' collective nickname. These are journal
trademarks (Cell Press/Elsevier, Springer Nature, AAAS) used to describe compatibility, which is
generally tolerated as nominative use, but "matching ... requirements" and "follows journal
guidelines" are compliance claims with no evidence behind them. For MakeMyFigure:

- Keep the existing "*-like aesthetics only ... NOT official ... must not be presented as
  guaranteeing submission compliance" language (engine.py module docstring) in any user-visible
  preset description.
- If journal presets are introduced, name them by measurable property or by guideline reference
  ("89 mm single column, 7 pt minimum type") rather than by brand, or use "for submission to X" with
  a dated guideline link and a disclaimer that the journal has not reviewed or endorsed the preset.
- Do not register journal names as global matplotlib colormap or palette identifiers.
- Do not reuse the cnsplots journal palettes; their licensing chain is unclear and their naming is
  the very pattern we are avoiding.
- Under cnsplots' BSD clause 3, do not cite cnsplots or its author in promotional material for
  MakeMyFigure; citing it in research notes such as this one is acceptable.
