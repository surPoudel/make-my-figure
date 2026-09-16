# Style measurement protocol (defined before measurement; 2026-09-16)

This protocol fixes *what* is measured on each published figure, *how*, and how confident each
value is, before any figure in the corpus is opened for measurement. It applies to every row of
`style_measurements.csv`. Publisher images are read from `PRIVATE_REFERENCE_ONLY/` (never
redistributed); only aggregate measurements leave that folder.

## Evidence classes (every value carries one)

| Class | Meaning | Example |
|---|---|---|
| `OBSERVED` | Read directly from the artefact with a known scale, or a categorical fact visible in the image | legend outside the axes; spines: left+bottom only; error bars present; typeset figure width from the article PDF image box |
| `INFERRED` | Derived from observed quantities by a stated formula with a known scale | tick-label point size from glyph height in px when the typeset width of the figure is known from the PDF |
| `ESTIMATED` | Derived under an assumption stated in `assumption` | tick-label point size from glyph height in px assuming the figure is typeset at the publisher's stated double-column width |
| `UNKNOWN` | Could not be determined from the material | font family beyond "sans-serif"; exact line width |

Rule: absolute point sizes and line widths in **millimetres/points** are never `OBSERVED` from a web
JPEG alone. They are `INFERRED` only when the physical figure width is known (PDF image box), and
`ESTIMATED` otherwise, with the assumed typeset width recorded. Relative measures (text height as a
fraction of figure width, line width in px relative to figure width) are `OBSERVED`.

## Unit of measurement

One row per **panel** when panels can be separated, otherwise one row per figure with
`panel = all`. Panels are identified by the printed panel letter. Only quantitative data panels
are measured (schematics, micrographs, gels, blots and photographs are recorded with
`plot_family = non-quantitative` and no style values).

## Fields of `style_measurements.csv`

Identification: `paper_id, journal, journal_family, year, figure_number, panel, plot_family,
image_path, image_width_px, image_height_px, typeset_width_mm, typeset_width_source`.

Typography (per panel, from the tick labels unless stated):
`tick_label_height_px` (median cap/x-height of tick-label glyph components),
`tick_label_rel_height` (= height_px / image_width_px, OBSERVED),
`tick_label_pt` (INFERRED/ESTIMATED; formula below), `axis_label_pt`, `panel_label_pt`,
`panel_label_case` (upper/lower), `panel_label_weight` (bold/regular), `font_class`
(sans/serif/UNKNOWN), `title_present` (yes/no).

Axes: `spines` (LB = left+bottom only; box = all four; none; other), `tick_direction`
(out/in/UNKNOWN), `grid` (none/major/minor), `axis_line_rel_width` (px / image_width_px),
`axis_line_weight_class` (hairline/regular/heavy, relative to text stroke).

Marks: `error_bar_style` (none/bars/bars+caps/band), `error_bar_caps` (yes/no/na),
`marker_fill` (filled/open/mixed/na), `marker_size_class` (small/medium/large), `points_shown_on_bars_or_boxes` (yes/no/na),
`line_weight_class`, `bar_edge` (none/dark/same-colour).

Legend: `legend_position` (inside/outside-right/outside-top/below/none/in-title),
`legend_frame` (yes/no/na), `legend_entries` (count).

Colour: `n_categorical_colours` (distinct hues used for groups), `palette_class`
(qualitative-saturated / qualitative-muted / monochrome-black / greys / diverging / sequential),
`background` (white/grey/other), `sequential_cmap_class` (viridis-like/blue-red/other/na).

Statistics display: `significance_style` (stars/P-values/both/none/na), `brackets` (yes/no/na),
`n_stated_in_panel` (yes/no).

Layout: `panel_aspect` (w/h), `figure_aspect`, `n_panels_in_figure`, `panel_grid_regular` (yes/no).

Provenance: `evidence_class_typography`, `evidence_class_lines`, `assumption`, `measured_by`
(auto/visual/both), `notes`.

## Formulas

Point size from glyph height. For Arial/Helvetica the cap height is ~0.716 em and the x-height
~0.519 em. Measured `tick_label_height_px` is the median height of connected components in the
tick-label strip, which for mixed digits/lowercase text approximates the digit height (= cap
height, digits in Arial are 0.716 em). Therefore

    em_px = height_px / 0.716
    pt    = em_px * (typeset_width_mm / image_width_px) / 25.4 * 72

`typeset_width_mm` is OBSERVED when read from the PDF image box; otherwise the publisher's stated
column width for the nearest class (single, or double when the figure aspect is wider than 1.25 or
the caption/XML marks it as a full-width figure) is assumed and the value is ESTIMATED.

## Sampling of panels within a paper

Measure every quantitative panel of the first three main figures with at least one quantitative
panel; if a paper has fewer, measure all. This caps the per-paper contribution and avoids
over-weighting long papers.

## Automated vs visual

The script `tools/measure_figure.py` produces the image-level and colour metrics and proposes a
panel segmentation. A reviewer (an agent viewing the image) records the categorical fields and
corrects the segmentation. Both are recorded in `measured_by`. Disagreements are resolved in
favour of the visual reading, with a note.

## Outliers

A panel whose value lies outside 1.5 x IQR of its family-and-plot-family group for any numeric
field is listed in `outliers.md` with a one-line reason (e.g. "tiny inset", "poster-style
tick labels") and is kept in the raw data but excluded from the central estimate.
