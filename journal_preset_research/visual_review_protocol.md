# Visual review protocol for corpus figures (fixed before review; 2026-09-16)

The automated pass (`tools/run_auto_measurements.py`) measures sizes and colours. The visual
review records the categorical style facts a human (or an agent viewing the image) can read
directly. Reviewers follow this protocol exactly and never infer what they cannot see.

## Which figures

For each paper, the first three **main** figures that contain at least one quantitative data
panel (a plot of numbers: axes, bars, points, lines, heat cells, curves). Figures that are entirely
schematics, micrographs, gels, blots, photographs, sequence logos or structures are recorded with a
single row `plot_family = non-quantitative` and no style values, and do not count toward the
three.

## One row per quantitative panel

`panel` is the printed panel letter (`a`, `B`, ...). If panels are not lettered, use `p1`, `p2`, ...
in reading order. If a figure has more than eight quantitative panels, review the first eight in
reading order and set `notes = "more panels not reviewed"`.

## Fields and allowed values

| Field | Allowed values | How to read it |
|---|---|---|
| `plot_family` | `bar`, `grouped_bar`, `stacked_bar`, `box`, `violin`, `dot_strip`, `scatter`, `scatter_regression`, `line`, `line_band`, `survival`, `volcano`, `ma`, `heatmap`, `heatmap_clustered`, `pca_umap`, `forest`, `dot_bubble`, `histogram_density`, `roc_pr`, `oncoprint`, `network`, `sankey`, `pie_donut`, `other_quant`, `non-quantitative` | dominant mark type of the panel |
| `spines` | `LB` (left+bottom only), `box` (all four), `L` (left only), `B` (bottom only), `none`, `UNKNOWN` | which axis lines are drawn |
| `tick_direction` | `out`, `in`, `none`, `UNKNOWN` | tick marks point away from or into the plotting area |
| `grid` | `none`, `major`, `major_minor`, `UNKNOWN` | grid lines behind the data |
| `background` | `white`, `grey`, `other` | plotting-area fill |
| `error_bar_style` | `none`, `bars`, `bars_caps`, `band`, `box_whisker`, `na` | how dispersion is drawn |
| `points_overlaid` | `yes`, `no`, `na` | individual data points drawn on bars/boxes/violins |
| `marker_fill` | `filled`, `open`, `mixed`, `na` | scatter/point markers |
| `marker_size_class` | `small`, `medium`, `large`, `na` | relative to tick-label height: small < 1x, medium 1-2x, large > 2x |
| `line_weight_class` | `hairline`, `regular`, `heavy`, `na` | data lines relative to the axis line: hairline thinner, regular similar, heavy clearly thicker |
| `axis_line_weight_class` | `hairline`, `regular`, `heavy`, `UNKNOWN` | axis line relative to the stroke of tick-label glyphs: hairline thinner, regular similar, heavy thicker |
| `legend_position` | `inside`, `outside_right`, `outside_top`, `below`, `in_title_or_caption`, `none`, `na` | where the key is |
| `legend_frame` | `yes`, `no`, `na` | box drawn around the legend |
| `legend_entries` | integer or `na` | number of entries |
| `n_categorical_colours` | integer (0 for monochrome) | distinct group colours in the panel |
| `palette_class` | `saturated`, `muted`, `pastel`, `monochrome_black`, `greys`, `sequential`, `diverging`, `mixed` | overall colour impression of the data marks |
| `sequential_cmap_class` | `viridis_like`, `blue_red`, `blue_white_red`, `yellow_red`, `greys`, `rainbow`, `other`, `na` | heatmap colour map |
| `colourbar_position` | `right`, `top`, `bottom`, `left`, `inside`, `none`, `na` | |
| `panel_label_case` | `upper`, `lower`, `none`, `UNKNOWN` | printed panel letter |
| `panel_label_weight` | `bold`, `regular`, `UNKNOWN` | |
| `panel_label_size_class` | `same_as_axis_label`, `larger`, `much_larger`, `UNKNOWN` | relative to axis-label text |
| `font_class` | `sans`, `serif`, `mixed`, `UNKNOWN` | |
| `axis_label_weight` | `regular`, `bold`, `UNKNOWN` | |
| `title_present` | `yes`, `no` | a title above the panel (not the panel letter) |
| `significance_style` | `stars`, `p_values`, `both`, `ns_marks`, `none`, `na` | |
| `brackets` | `yes`, `no`, `na` | comparison brackets/lines between groups |
| `n_stated_in_panel` | `yes`, `no` | sample size printed inside the panel |
| `tick_label_density` | `sparse`, `normal`, `dense` | dense = labels nearly touching |
| `x_tick_rotation` | `0`, `45`, `90`, `other`, `na` | |
| `panel_aspect_class` | `wide`, `square`, `tall` | wide > 1.3, tall < 0.77 |
| `confidence` | `high`, `medium`, `low` | your confidence in this row overall |
| `notes` | free text | anything unusual; state "UNKNOWN because ..." where a field could not be read |

`UNKNOWN` is always preferable to a guess. Web-resolution images (about 700 px wide) are too
small to judge line weights reliably: use `UNKNOWN` unless the difference is obvious.

## Output

`visual_review_<family>_<batch>.csv` with columns exactly:
`paper_id, journal, journal_family, figure_number, panel, plot_family, spines, tick_direction,
grid, background, error_bar_style, points_overlaid, marker_fill, marker_size_class,
line_weight_class, axis_line_weight_class, legend_position, legend_frame, legend_entries,
n_categorical_colours, palette_class, sequential_cmap_class, colourbar_position,
panel_label_case, panel_label_weight, panel_label_size_class, font_class, axis_label_weight,
title_present, significance_style, brackets, n_stated_in_panel, tick_label_density,
x_tick_rotation, panel_aspect_class, confidence, notes, image_path, reviewer`

`reviewer` is the agent's batch label. Rows are appended as each figure is reviewed so partial
work survives.
