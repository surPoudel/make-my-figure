# Presets used in the showcases

Each preset was loaded from its file and applied with `presets.apply_preset`, exactly as the application's Preview & apply does. All are EXPERIMENTAL evidence-derived presets; the letters (S), (C), (N) name the evidence set, not an approval.

## `gc_box_points_outline` - Box + observations (outline)

File: `style_profiles/experimental_publication_presets/gc_box_points_outline.mmfpreset.json`; mode style; plot type boxplot_or_violin_with_points; universal False; applied 12 setting(s), skipped 0.

```json
{
 "style": {
  "marker_alpha": 0.9
 },
 "options": {
  "points": true,
  "point_arrangement": "jitter",
  "point_fill": "filled",
  "point_edge": "dark",
  "point_edge_width": 0.4,
  "point_size": 0.0,
  "point_alpha": 0.0,
  "kind": "box",
  "box_fill": "outline",
  "box_width": 0.5,
  "show_outliers": false
 },
 "layout": {}
}
```

## `gc_violin_points` - Violin + observations

File: `style_profiles/experimental_publication_presets/gc_violin_points.mmfpreset.json`; mode style; plot type boxplot_or_violin_with_points; universal False; applied 10 setting(s), skipped 0.

```json
{
 "style": {
  "marker_alpha": 0.9
 },
 "options": {
  "points": true,
  "point_arrangement": "jitter",
  "point_fill": "filled",
  "point_edge": "dark",
  "point_edge_width": 0.4,
  "point_size": 0.0,
  "point_alpha": 0.0,
  "kind": "violin",
  "show_outliers": false
 },
 "layout": {}
}
```

## `gc_bar_points_jittered` - Bar + observations (jittered)

File: `style_profiles/experimental_publication_presets/gc_bar_points_jittered.mmfpreset.json`; mode style; plot type barplot_with_error_bar; universal False; applied 12 setting(s), skipped 0.

```json
{
 "style": {
  "marker_alpha": 0.9
 },
 "options": {
  "points": true,
  "point_arrangement": "jitter",
  "point_fill": "filled",
  "point_edge": "dark",
  "point_edge_width": 0.4,
  "point_size": 0.0,
  "point_alpha": 0.0,
  "bar_width": 0.6,
  "bar_fill": "filled",
  "error_cap": true,
  "show_n": "none"
 },
 "layout": {}
}
```

## `gc_box_points_light` - Box + observations (light fill)

File: `style_profiles/experimental_publication_presets/gc_box_points_light.mmfpreset.json`; mode style; plot type boxplot_or_violin_with_points; universal False; applied 12 setting(s), skipped 0.

```json
{
 "style": {
  "marker_alpha": 0.9
 },
 "options": {
  "points": true,
  "point_arrangement": "jitter",
  "point_fill": "filled",
  "point_edge": "dark",
  "point_edge_width": 0.4,
  "point_size": 0.0,
  "point_alpha": 0.0,
  "kind": "box",
  "box_fill": "light",
  "box_width": 0.5,
  "show_outliers": false
 },
 "layout": {}
}
```

## `single_89mm_N` - Single column 89 mm (N)

File: `style_profiles/experimental_publication_presets/single_89mm_N.mmfpreset.json`; mode style; plot type boxplot_or_violin_with_points; universal True; applied 38 setting(s), skipped 0.

```json
{
 "style": {
  "show_top_spine": false,
  "show_right_spine": false,
  "tick_direction": "out",
  "grid": false,
  "legend_frameon": false,
  "font_weight": "normal",
  "palette_name": "publication",
  "text_color": "#000000",
  "tick_label_pt": 5.5,
  "axis_font_pt": 6.5,
  "legend_pt": 5.5,
  "annotation_pt": 5.5,
  "legend_title_pt": 6.5,
  "title_font_pt": 6.5,
  "base_font_pt": 5.5,
  "panel_label_pt": 8.0,
  "font_family": "Arial",
  "spine_width_pt": 0.5,
  "line_width_pt": 0.75,
  "tick_width": 0.5,
  "tick_length": 2.5,
  "errorbar_line_width": 0.5,
  "bar_edge_width": 0.5,
  "marker_edge_width": 0.4,
  "regression_line_width": 0.75,
  "grid_width": 0.4,
  "marker_size": 20.0,
  "marker_alpha": 0.9,
  "errorbar_capsize": 1.5,
  "legend_loc": "best",
  "legend_outside": false,
  "legend_ncol": 1
 },
 "options": {},
 "layout": {
  "column_width": "89mm",
  "legend_location": "best"
 }
}
```
