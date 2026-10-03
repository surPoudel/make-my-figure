# Journal-family differences in measured style

Numeric fields: Kruskal-Wallis across families, effect = epsilon-squared (0.01 small, 0.06 medium, 0.14 large). 
Categorical fields: chi-square, effect = Cramer's V (0.1 small, 0.3 medium, 0.5 large). 
Absolute text and stroke sizes use only figures measured from typeset PDFs (observed scale); web-JPEG estimates are excluded. 
A field counts as *meaningfully different* only when p < 0.01 AND the effect is at least medium; 
everything else is treated as shared practice and the presets must NOT manufacture a difference there.

## all_quantitative

| field | kind | n | p | effect | meaningful | per-family value |
|---|---|---|---|---|---|---|
| typeset_width_mm | numeric | 401 |  |  | no | {"Cell": null, "Nature": 173.32, "Science": null} |
| smallest_cluster_pt | numeric | 398 |  |  | no | {"Cell": null, "Nature": 5.03, "Science": null} |
| dominant_cluster_pt | numeric | 398 |  |  | no | {"Cell": null, "Nature": 5.69, "Science": null} |
| largest_cluster_pt | numeric | 398 |  |  | no | {"Cell": null, "Nature": 6.53, "Science": null} |
| stroke_pt_inferred | numeric | 231 |  |  | no | {"Cell": null, "Nature": 2.88, "Science": null} |
| coloured_fraction | numeric | 1636 | 4.81e-25 | 0.07 | YES | {"Cell": 0.05, "Nature": 0.08, "Science": 0.04} |
| n_hue_clusters | numeric | 1636 | 0.00277 | 0.01 | no | {"Cell": 3.0, "Nature": 3.0, "Science": 3.0} |
| mean_saturation | numeric | 1636 | 1.67e-17 | 0.05 | no | {"Cell": 0.57, "Nature": 0.68, "Science": 0.59} |
| figure_aspect | numeric | 1636 | 5.87e-12 | 0.03 | no | {"Cell": 0.88, "Nature": 1.08, "Science": 0.9} |
| n_panels_detected | numeric | 1636 | 7.56e-11 | 0.03 | no | {"Cell": 6.0, "Nature": 6.0, "Science": 4.0} |
| legend_entries | numeric | 797 | 2.02e-05 | 0.02 | no | {"Cell": 2.0, "Nature": 3.0, "Science": 3.0} |
| n_categorical_colours | numeric | 1700 | 0.000905 | 0.01 | no | {"Cell": 2.0, "Nature": 2.0, "Science": 2.0} |
| spines | categorical | 1694 | 4.49e-06 | 0.11 | no | {"Cell": "LB", "Nature": "LB", "Science": "LB"} |
| tick_direction | categorical | 1523 | 2.86e-08 | 0.12 | no | {"Cell": "out", "Nature": "out", "Science": "out"} |
| grid | categorical | 1697 | 0.207 | 0.04 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| background | categorical | 1700 | 0.202 | 0.04 | no | {"Cell": "white", "Nature": "white", "Science": "white"} |
| error_bar_style | categorical | 1450 | 1.29e-20 | 0.20 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| points_overlaid | categorical | 784 | 4.48e-20 | 0.34 | YES | {"Cell": "yes", "Nature": "no", "Science": "yes"} |
| marker_fill | categorical | 995 | 0.0167 | 0.08 | no | {"Cell": "filled", "Nature": "filled", "Science": "filled"} |
| marker_size_class | categorical | 998 | 2.03e-07 | 0.14 | no | {"Cell": "small", "Nature": "small", "Science": "small"} |
| line_weight_class | categorical | 408 | 1.04e-06 | 0.20 | no | {"Cell": "regular", "Nature": "regular", "Science": "regular"} |
| axis_line_weight_class | categorical | 325 | 1.28e-08 | 0.26 | no | {"Cell": "regular", "Nature": "regular", "Science": "regular"} |
| legend_position | categorical | 1677 | 4.49e-10 | 0.14 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| legend_frame | categorical | 884 | 9.69e-06 | 0.16 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| palette_class | categorical | 1700 | 2.17e-20 | 0.19 | no | {"Cell": "saturated", "Nature": "saturated", "Science": "mixed"} |
| sequential_cmap_class | categorical | 210 | 0.0126 | 0.25 | no | {"Cell": "other", "Nature": "other", "Science": "other"} |
| colourbar_position | categorical | 213 | 0.00221 | 0.25 | no | {"Cell": "right", "Nature": "right", "Science": "right"} |
| panel_label_case | categorical | 1700 | 0 | 0.65 | YES | {"Cell": "upper", "Nature": "lower", "Science": "upper"} |
| panel_label_weight | categorical | 1675 | 1.69e-07 | 0.14 | no | {"Cell": "bold", "Nature": "bold", "Science": "bold"} |
| panel_label_size_class | categorical | 1675 | 2.27e-263 | 0.60 | YES | {"Cell": "larger", "Nature": "larger", "Science": "much_larger"} |
| font_class | categorical | 1700 | 0.0015 | 0.09 | no | {"Cell": "sans", "Nature": "sans", "Science": "sans"} |
| axis_label_weight | categorical | 1700 | 0.0892 | 0.05 | no | {"Cell": "regular", "Nature": "regular", "Science": "regular"} |
| title_present | categorical | 1700 | 6.67e-06 | 0.12 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| significance_style | categorical | 1512 | 8.77e-18 | 0.18 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| brackets | categorical | 1400 | 8.26e-15 | 0.22 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| n_stated_in_panel | categorical | 1700 | 0.065 | 0.06 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| tick_label_density | categorical | 1700 | 2.96e-18 | 0.16 | no | {"Cell": "normal", "Nature": "normal", "Science": "normal"} |
| x_tick_rotation | categorical | 1494 | 0.00751 | 0.07 | no | {"Cell": "0", "Nature": "0", "Science": "0"} |
| panel_aspect_class | categorical | 1700 | 0.0253 | 0.06 | no | {"Cell": "square", "Nature": "wide", "Science": "square"} |

## bars

| field | kind | n | p | effect | meaningful | per-family value |
|---|---|---|---|---|---|---|
| typeset_width_mm | numeric | 100 |  |  | no | {"Cell": null, "Nature": 174.21, "Science": null} |
| smallest_cluster_pt | numeric | 100 |  |  | no | {"Cell": null, "Nature": 5.36, "Science": null} |
| dominant_cluster_pt | numeric | 100 |  |  | no | {"Cell": null, "Nature": 5.53, "Science": null} |
| largest_cluster_pt | numeric | 100 |  |  | no | {"Cell": null, "Nature": 6.03, "Science": null} |
| stroke_pt_inferred | numeric | 52 |  |  | no | {"Cell": null, "Nature": 2.76, "Science": null} |
| coloured_fraction | numeric | 491 | 1.72e-06 | 0.05 | no | {"Cell": 0.04, "Nature": 0.08, "Science": 0.05} |
| n_hue_clusters | numeric | 491 | 0.681 | -0.00 | no | {"Cell": 3.0, "Nature": 3.0, "Science": 3.0} |
| mean_saturation | numeric | 491 | 0.000782 | 0.03 | no | {"Cell": 0.61, "Nature": 0.69, "Science": 0.58} |
| figure_aspect | numeric | 491 | 1.87e-09 | 0.08 | YES | {"Cell": 0.81, "Nature": 1.18, "Science": 1.01} |
| n_panels_detected | numeric | 491 | 4.38e-10 | 0.08 | YES | {"Cell": 8.0, "Nature": 7.0, "Science": 4.0} |
| legend_entries | numeric | 237 | 0.0147 | 0.03 | no | {"Cell": 2.0, "Nature": 2.0, "Science": 3.0} |
| n_categorical_colours | numeric | 530 | 0.000398 | 0.03 | no | {"Cell": 2.0, "Nature": 2.0, "Science": 3.0} |
| spines | categorical | 527 | 0.0399 | 0.12 | no | {"Cell": "LB", "Nature": "LB", "Science": "LB"} |
| tick_direction | categorical | 479 | 0.00306 | 0.13 | no | {"Cell": "out", "Nature": "out", "Science": "out"} |
| grid | categorical | 530 | 0.126 | 0.09 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| background | categorical | 530 | 0.217 | 0.08 | no | {"Cell": "white", "Nature": "white", "Science": "white"} |
| error_bar_style | categorical | 522 | 1.26e-12 | 0.25 | no | {"Cell": "bars_caps", "Nature": "bars_caps", "Science": "bars_caps"} |
| points_overlaid | categorical | 506 | 1.2e-05 | 0.21 | no | {"Cell": "yes", "Nature": "no", "Science": "yes"} |
| marker_fill | categorical | 338 | 6.72e-05 | 0.19 | no | {"Cell": "filled", "Nature": "filled", "Science": "filled"} |
| marker_size_class | categorical | 341 | 1.74e-09 | 0.34 | YES | {"Cell": "small", "Nature": "small", "Science": "small"} |
| line_weight_class | categorical | 17 |  |  | no | {"Cell": "hairline", "Nature": null, "Science": null} |
| axis_line_weight_class | categorical | 128 | 0.000182 | 0.29 | no | {"Cell": "regular", "Nature": "regular", "Science": "regular"} |
| legend_position | categorical | 528 | 3.77e-12 | 0.27 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| legend_frame | categorical | 255 | 0.0257 | 0.17 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| palette_class | categorical | 530 | 8.86e-05 | 0.20 | no | {"Cell": "saturated", "Nature": "saturated", "Science": "mixed"} |
| sequential_cmap_class | categorical | 5 |  |  | no | {"Cell": "other", "Nature": "yellow_red", "Science": "blue_red"} |
| colourbar_position | categorical | 9 |  |  | no | {"Cell": "none", "Nature": "right", "Science": "top"} |
| panel_label_case | categorical | 530 | 7.54e-100 | 0.66 | YES | {"Cell": "upper", "Nature": "lower", "Science": "upper"} |
| panel_label_weight | categorical | 522 | 0.00145 | 0.16 | no | {"Cell": "bold", "Nature": "bold", "Science": "bold"} |
| panel_label_size_class | categorical | 522 | 4.22e-98 | 0.93 | YES | {"Cell": "larger", "Nature": "larger", "Science": "much_larger"} |
| font_class | categorical | 530 |  |  | no | {"Cell": "sans", "Nature": "sans", "Science": "sans"} |
| axis_label_weight | categorical | 530 | 0.0116 | 0.13 | no | {"Cell": "regular", "Nature": "regular", "Science": "regular"} |
| title_present | categorical | 530 | 0.131 | 0.09 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| significance_style | categorical | 523 | 1.53e-14 | 0.28 | no | {"Cell": "stars", "Nature": "none", "Science": "stars"} |
| brackets | categorical | 526 | 1.77e-10 | 0.29 | no | {"Cell": "no", "Nature": "no", "Science": "yes"} |
| n_stated_in_panel | categorical | 530 | 1.46e-07 | 0.24 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| tick_label_density | categorical | 530 | 7.77e-13 | 0.24 | no | {"Cell": "normal", "Nature": "normal", "Science": "normal"} |
| x_tick_rotation | categorical | 480 | 0.000138 | 0.15 | no | {"Cell": "0", "Nature": "0", "Science": "0"} |
| panel_aspect_class | categorical | 530 | 0.00057 | 0.14 | no | {"Cell": "square", "Nature": "wide", "Science": "tall"} |

## distributions

| field | kind | n | p | effect | meaningful | per-family value |
|---|---|---|---|---|---|---|
| typeset_width_mm | numeric | 54 |  |  | no | {"Cell": null, "Nature": 168.78, "Science": null} |
| smallest_cluster_pt | numeric | 53 |  |  | no | {"Cell": null, "Nature": 5.36, "Science": null} |
| dominant_cluster_pt | numeric | 53 |  |  | no | {"Cell": null, "Nature": 5.53, "Science": null} |
| largest_cluster_pt | numeric | 53 |  |  | no | {"Cell": null, "Nature": 6.7, "Science": null} |
| stroke_pt_inferred | numeric | 27 |  |  | no | {"Cell": null, "Nature": 3.36, "Science": null} |
| coloured_fraction | numeric | 230 | 0.000466 | 0.06 | no | {"Cell": 0.05, "Nature": 0.07, "Science": 0.04} |
| n_hue_clusters | numeric | 230 | 0.0966 | 0.01 | no | {"Cell": 4.0, "Nature": 3.0, "Science": 3.0} |
| mean_saturation | numeric | 230 | 3.65e-06 | 0.10 | YES | {"Cell": 0.57, "Nature": 0.69, "Science": 0.64} |
| figure_aspect | numeric | 230 | 0.0105 | 0.03 | no | {"Cell": 0.95, "Nature": 1.03, "Science": 0.86} |
| n_panels_detected | numeric | 230 | 0.0465 | 0.02 | no | {"Cell": 7.0, "Nature": 5.0, "Science": 6.0} |
| legend_entries | numeric | 82 | 0.00349 | 0.12 | YES | {"Cell": 2.0, "Nature": 4.0, "Science": 3.0} |
| n_categorical_colours | numeric | 270 | 0.0788 | 0.01 | no | {"Cell": 2.0, "Nature": 3.0, "Science": 2.0} |
| spines | categorical | 270 | 0.0616 | 0.17 | no | {"Cell": "LB", "Nature": "LB", "Science": "LB"} |
| tick_direction | categorical | 248 | 0.267 | 0.10 | no | {"Cell": "out", "Nature": "out", "Science": "out"} |
| grid | categorical | 268 | 0.16 | 0.11 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| background | categorical | 270 | 0.46 | 0.08 | no | {"Cell": "white", "Nature": "white", "Science": "white"} |
| error_bar_style | categorical | 266 | 3.05e-08 | 0.29 | no | {"Cell": "box_whisker", "Nature": "none", "Science": "none"} |
| points_overlaid | categorical | 158 | 0.000943 | 0.30 | no | {"Cell": "yes", "Nature": "yes", "Science": "yes"} |
| marker_fill | categorical | 204 | 0.00398 | 0.19 | no | {"Cell": "filled", "Nature": "filled", "Science": "filled"} |
| marker_size_class | categorical | 204 | 9.45e-09 | 0.33 | YES | {"Cell": "small", "Nature": "small", "Science": "medium"} |
| line_weight_class | categorical | 39 | 0.0193 | 0.45 | no | {"Cell": "hairline", "Nature": "regular", "Science": "hairline"} |
| axis_line_weight_class | categorical | 47 | 1.41e-07 | 0.82 | YES | {"Cell": "heavy", "Nature": "regular", "Science": "regular"} |
| legend_position | categorical | 269 | 0.178 | 0.15 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| legend_frame | categorical | 85 | 0.00358 | 0.36 | YES | {"Cell": "no", "Nature": "no", "Science": "no"} |
| palette_class | categorical | 270 | 1.47e-09 | 0.36 | YES | {"Cell": "mixed", "Nature": "saturated", "Science": "mixed"} |
| sequential_cmap_class | categorical | 1 |  |  | no | {"Cell": "greys", "Nature": null, "Science": null} |
| colourbar_position | categorical | 2 |  |  | no | {"Cell": "inside", "Nature": "none", "Science": null} |
| panel_label_case | categorical | 270 | 1.18e-51 | 0.67 | YES | {"Cell": "upper", "Nature": "lower", "Science": "upper"} |
| panel_label_weight | categorical | 261 | 0.0271 | 0.17 | no | {"Cell": "bold", "Nature": "bold", "Science": "bold"} |
| panel_label_size_class | categorical | 261 | 5.73e-49 | 0.92 | YES | {"Cell": "larger", "Nature": "larger", "Science": "much_larger"} |
| font_class | categorical | 270 |  |  | no | {"Cell": "sans", "Nature": "sans", "Science": "sans"} |
| axis_label_weight | categorical | 270 | 0.0453 | 0.15 | no | {"Cell": "regular", "Nature": "regular", "Science": "regular"} |
| title_present | categorical | 270 | 0.00305 | 0.21 | no | {"Cell": "yes", "Nature": "no", "Science": "yes"} |
| significance_style | categorical | 261 | 8.65e-05 | 0.25 | no | {"Cell": "stars", "Nature": "p_values", "Science": "stars"} |
| brackets | categorical | 256 | 0.000234 | 0.26 | no | {"Cell": "yes", "Nature": "no", "Science": "yes"} |
| n_stated_in_panel | categorical | 270 | 0.431 | 0.08 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| tick_label_density | categorical | 270 | 8.04e-05 | 0.21 | no | {"Cell": "normal", "Nature": "normal", "Science": "normal"} |
| x_tick_rotation | categorical | 253 | 0.258 | 0.10 | no | {"Cell": "0", "Nature": "0", "Science": "0"} |
| panel_aspect_class | categorical | 270 | 0.0836 | 0.12 | no | {"Cell": "square", "Nature": "wide", "Science": "wide"} |

## heatmaps

| field | kind | n | p | effect | meaningful | per-family value |
|---|---|---|---|---|---|---|
| typeset_width_mm | numeric | 49 |  |  | no | {"Cell": null, "Nature": 173.32, "Science": null} |
| smallest_cluster_pt | numeric | 48 |  |  | no | {"Cell": null, "Nature": 4.48, "Science": null} |
| dominant_cluster_pt | numeric | 48 |  |  | no | {"Cell": null, "Nature": 5.45, "Science": null} |
| largest_cluster_pt | numeric | 48 |  |  | no | {"Cell": null, "Nature": 6.53, "Science": null} |
| stroke_pt_inferred | numeric | 31 |  |  | no | {"Cell": null, "Nature": 3.84, "Science": null} |
| coloured_fraction | numeric | 116 | 0.262 | 0.01 | no | {"Cell": 0.11, "Nature": 0.12, "Science": 0.1} |
| n_hue_clusters | numeric | 116 | 0.0115 | 0.06 | no | {"Cell": 3.0, "Nature": 3.0, "Science": 2.0} |
| mean_saturation | numeric | 116 | 0.0271 | 0.05 | no | {"Cell": 0.58, "Nature": 0.62, "Science": 0.55} |
| figure_aspect | numeric | 116 | 0.406 | -0.00 | no | {"Cell": 1.07, "Nature": 1.02, "Science": 0.89} |
| n_panels_detected | numeric | 116 | 0.00024 | 0.13 | YES | {"Cell": 3.0, "Nature": 8.0, "Science": 2.0} |
| legend_entries | numeric | 14 |  |  | no | {"Cell": 2.5, "Nature": 2.0, "Science": 4.0} |
| n_categorical_colours | numeric | 121 | 0.161 | 0.01 | no | {"Cell": 0.0, "Nature": 0.0, "Science": 0.0} |
| spines | categorical | 120 | 0.556 | 0.11 | no | {"Cell": "box", "Nature": "none", "Science": "none"} |
| tick_direction | categorical | 100 | 0.68 | 0.09 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| grid | categorical | 121 | 0.0832 | 0.20 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| background | categorical | 121 | 0.00234 | 0.26 | no | {"Cell": "white", "Nature": "white", "Science": "white"} |
| error_bar_style | categorical | 19 |  |  | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| points_overlaid | categorical | 0 |  |  | no | {"Cell": null, "Nature": null, "Science": null} |
| marker_fill | categorical | 0 |  |  | no | {"Cell": null, "Nature": null, "Science": null} |
| marker_size_class | categorical | 0 |  |  | no | {"Cell": null, "Nature": null, "Science": null} |
| line_weight_class | categorical | 3 |  |  | no | {"Cell": "heavy", "Nature": "regular", "Science": null} |
| axis_line_weight_class | categorical | 1 |  |  | no | {"Cell": null, "Nature": null, "Science": "regular"} |
| legend_position | categorical | 104 | 0.0325 | 0.28 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| legend_frame | categorical | 56 | 0.125 | 0.27 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| palette_class | categorical | 121 | 0.0156 | 0.28 | no | {"Cell": "diverging", "Nature": "sequential", "Science": "sequential"} |
| sequential_cmap_class | categorical | 117 | 0.0255 | 0.32 | no | {"Cell": "other", "Nature": "other", "Science": "other"} |
| colourbar_position | categorical | 117 | 0.00668 | 0.32 | YES | {"Cell": "right", "Nature": "right", "Science": "right"} |
| panel_label_case | categorical | 121 | 9.95e-24 | 0.94 | YES | {"Cell": "upper", "Nature": "lower", "Science": "upper"} |
| panel_label_weight | categorical | 121 | 0.578 | 0.10 | no | {"Cell": "bold", "Nature": "bold", "Science": "bold"} |
| panel_label_size_class | categorical | 121 | 1.96e-16 | 0.57 | YES | {"Cell": "larger", "Nature": "larger", "Science": "much_larger"} |
| font_class | categorical | 121 |  |  | no | {"Cell": "sans", "Nature": "sans", "Science": "sans"} |
| axis_label_weight | categorical | 121 | 0.821 | 0.06 | no | {"Cell": "regular", "Nature": "regular", "Science": "regular"} |
| title_present | categorical | 121 | 0.969 | 0.02 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| significance_style | categorical | 68 | 0.346 | 0.18 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| brackets | categorical | 64 |  |  | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| n_stated_in_panel | categorical | 121 | 0.399 | 0.12 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| tick_label_density | categorical | 121 | 0.358 | 0.13 | no | {"Cell": "normal", "Nature": "normal", "Science": "dense"} |
| x_tick_rotation | categorical | 105 | 0.00504 | 0.27 | no | {"Cell": "0", "Nature": "0", "Science": "0"} |
| panel_aspect_class | categorical | 121 | 0.0956 | 0.18 | no | {"Cell": "wide", "Nature": "square", "Science": "square"} |

## lines

| field | kind | n | p | effect | meaningful | per-family value |
|---|---|---|---|---|---|---|
| typeset_width_mm | numeric | 99 |  |  | no | {"Cell": null, "Nature": 172.63, "Science": null} |
| smallest_cluster_pt | numeric | 99 |  |  | no | {"Cell": null, "Nature": 5.36, "Science": null} |
| dominant_cluster_pt | numeric | 99 |  |  | no | {"Cell": null, "Nature": 6.03, "Science": null} |
| largest_cluster_pt | numeric | 99 |  |  | no | {"Cell": null, "Nature": 6.37, "Science": null} |
| stroke_pt_inferred | numeric | 54 |  |  | no | {"Cell": null, "Nature": 4.08, "Science": null} |
| coloured_fraction | numeric | 374 | 4.22e-07 | 0.07 | YES | {"Cell": 0.05, "Nature": 0.08, "Science": 0.04} |
| n_hue_clusters | numeric | 374 | 0.0265 | 0.01 | no | {"Cell": 3.0, "Nature": 3.0, "Science": 3.0} |
| mean_saturation | numeric | 374 | 3.65e-05 | 0.05 | no | {"Cell": 0.57, "Nature": 0.69, "Science": 0.63} |
| figure_aspect | numeric | 374 | 0.00727 | 0.02 | no | {"Cell": 0.88, "Nature": 1.09, "Science": 0.9} |
| n_panels_detected | numeric | 374 | 0.167 | 0.00 | no | {"Cell": 5.0, "Nature": 4.5, "Science": 4.0} |
| legend_entries | numeric | 278 | 0.0247 | 0.02 | no | {"Cell": 3.0, "Nature": 3.0, "Science": 3.0} |
| n_categorical_colours | numeric | 399 | 0.0107 | 0.02 | no | {"Cell": 2.0, "Nature": 2.0, "Science": 3.0} |
| spines | categorical | 398 | 0.00657 | 0.16 | no | {"Cell": "LB", "Nature": "LB", "Science": "LB"} |
| tick_direction | categorical | 352 | 1.39e-08 | 0.25 | no | {"Cell": "out", "Nature": "out", "Science": "out"} |
| grid | categorical | 399 | 0.0196 | 0.14 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| background | categorical | 399 |  |  | no | {"Cell": "white", "Nature": "white", "Science": "white"} |
| error_bar_style | categorical | 397 | 1.68e-06 | 0.23 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| points_overlaid | categorical | 113 | 2.93e-06 | 0.47 | YES | {"Cell": "no", "Nature": "no", "Science": "yes"} |
| marker_fill | categorical | 163 | 0.227 | 0.13 | no | {"Cell": "filled", "Nature": "filled", "Science": "filled"} |
| marker_size_class | categorical | 163 | 9.21e-10 | 0.38 | YES | {"Cell": "medium", "Nature": "small", "Science": "small"} |
| line_weight_class | categorical | 289 | 0.0852 | 0.12 | no | {"Cell": "regular", "Nature": "regular", "Science": "regular"} |
| axis_line_weight_class | categorical | 98 | 0.00466 | 0.33 | YES | {"Cell": "regular", "Nature": "regular", "Science": "regular"} |
| legend_position | categorical | 398 | 5.14e-05 | 0.22 | no | {"Cell": "inside", "Nature": "inside", "Science": "inside"} |
| legend_frame | categorical | 281 | 0.00156 | 0.21 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| palette_class | categorical | 399 | 1.97e-12 | 0.31 | YES | {"Cell": "saturated", "Nature": "saturated", "Science": "mixed"} |
| sequential_cmap_class | categorical | 4 |  |  | no | {"Cell": null, "Nature": "other", "Science": "other"} |
| colourbar_position | categorical | 6 |  |  | no | {"Cell": "none", "Nature": "right", "Science": "right"} |
| panel_label_case | categorical | 399 | 2.74e-68 | 0.63 | YES | {"Cell": "upper", "Nature": "lower", "Science": "upper"} |
| panel_label_weight | categorical | 395 |  |  | no | {"Cell": "bold", "Nature": "bold", "Science": "bold"} |
| panel_label_size_class | categorical | 395 | 5.21e-45 | 0.52 | YES | {"Cell": "larger", "Nature": "larger", "Science": "much_larger"} |
| font_class | categorical | 399 | 0.00295 | 0.17 | no | {"Cell": "sans", "Nature": "sans", "Science": "sans"} |
| axis_label_weight | categorical | 399 | 0.0011 | 0.18 | no | {"Cell": "regular", "Nature": "regular", "Science": "regular"} |
| title_present | categorical | 399 | 0.125 | 0.10 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| significance_style | categorical | 372 | 0.000132 | 0.20 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| brackets | categorical | 301 | 0.0135 | 0.17 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| n_stated_in_panel | categorical | 399 | 0.0566 | 0.12 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| tick_label_density | categorical | 399 | 1.36e-07 | 0.22 | no | {"Cell": "normal", "Nature": "normal", "Science": "normal"} |
| x_tick_rotation | categorical | 390 | 0.000531 | 0.16 | no | {"Cell": "0", "Nature": "0", "Science": "0"} |
| panel_aspect_class | categorical | 399 | 0.000175 | 0.17 | no | {"Cell": "wide", "Nature": "wide", "Science": "wide"} |

## other

| field | kind | n | p | effect | meaningful | per-family value |
|---|---|---|---|---|---|---|
| typeset_width_mm | numeric | 27 |  |  | no | {"Cell": null, "Nature": 178.37, "Science": null} |
| smallest_cluster_pt | numeric | 26 |  |  | no | {"Cell": null, "Nature": 5.03, "Science": null} |
| dominant_cluster_pt | numeric | 26 |  |  | no | {"Cell": null, "Nature": 6.03, "Science": null} |
| largest_cluster_pt | numeric | 26 |  |  | no | {"Cell": null, "Nature": 6.03, "Science": null} |
| stroke_pt_inferred | numeric | 21 |  |  | no | {"Cell": null, "Nature": 2.88, "Science": null} |
| coloured_fraction | numeric | 181 | 0.0154 | 0.04 | no | {"Cell": 0.05, "Nature": 0.08, "Science": 0.06} |
| n_hue_clusters | numeric | 181 | 0.124 | 0.01 | no | {"Cell": 3.0, "Nature": 3.0, "Science": 3.0} |
| mean_saturation | numeric | 181 | 0.00637 | 0.05 | no | {"Cell": 0.52, "Nature": 0.64, "Science": 0.53} |
| figure_aspect | numeric | 181 | 0.0718 | 0.02 | no | {"Cell": 0.99, "Nature": 1.21, "Science": 1.01} |
| n_panels_detected | numeric | 181 | 0.0012 | 0.06 | YES | {"Cell": 1.0, "Nature": 5.0, "Science": 1.0} |
| legend_entries | numeric | 38 | 0.586 | -0.03 | no | {"Cell": 3.0, "Nature": 4.0, "Science": 4.0} |
| n_categorical_colours | numeric | 121 | 0.795 | -0.01 | no | {"Cell": 3.0, "Nature": 3.0, "Science": 2.0} |
| spines | categorical | 120 | 0.02 | 0.28 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| tick_direction | categorical | 109 | 0.309 | 0.15 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| grid | categorical | 120 | 0.379 | 0.13 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| background | categorical | 121 | 0.567 | 0.11 | no | {"Cell": "white", "Nature": "white", "Science": "white"} |
| error_bar_style | categorical | 51 | 0.209 | 0.29 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| points_overlaid | categorical | 4 |  |  | no | {"Cell": "no", "Nature": "no", "Science": null} |
| marker_fill | categorical | 31 | 0.283 | 0.29 | no | {"Cell": "filled", "Nature": "filled", "Science": "filled"} |
| marker_size_class | categorical | 31 | 0.129 | 0.36 | no | {"Cell": "medium", "Nature": "small", "Science": "small"} |
| line_weight_class | categorical | 26 | 0.538 | 0.25 | no | {"Cell": "hairline", "Nature": "hairline", "Science": "hairline"} |
| axis_line_weight_class | categorical | 9 |  |  | no | {"Cell": null, "Nature": "regular", "Science": "regular"} |
| legend_position | categorical | 120 | 0.558 | 0.17 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| legend_frame | categorical | 45 | 0.0496 | 0.37 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| palette_class | categorical | 121 | 0.000512 | 0.40 | YES | {"Cell": "saturated", "Nature": "saturated", "Science": "mixed"} |
| sequential_cmap_class | categorical | 25 | 0.0046 | 0.61 | YES | {"Cell": "other", "Nature": "other", "Science": "rainbow"} |
| colourbar_position | categorical | 20 | 0.351 | 0.41 | no | {"Cell": "right", "Nature": "right", "Science": "right"} |
| panel_label_case | categorical | 121 | 8.02e-26 | 0.98 | YES | {"Cell": "upper", "Nature": "lower", "Science": "upper"} |
| panel_label_weight | categorical | 121 | 0.0397 | 0.23 | no | {"Cell": "bold", "Nature": "bold", "Science": "bold"} |
| panel_label_size_class | categorical | 121 | 2.58e-20 | 0.64 | YES | {"Cell": "larger", "Nature": "larger", "Science": "much_larger"} |
| font_class | categorical | 121 |  |  | no | {"Cell": "sans", "Nature": "sans", "Science": "sans"} |
| axis_label_weight | categorical | 121 | 0.501 | 0.11 | no | {"Cell": "regular", "Nature": "regular", "Science": "regular"} |
| title_present | categorical | 121 | 0.00698 | 0.29 | no | {"Cell": "no", "Nature": "no", "Science": "yes"} |
| significance_style | categorical | 98 | 0.327 | 0.15 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| brackets | categorical | 86 |  |  | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| n_stated_in_panel | categorical | 121 | 0.0724 | 0.21 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| tick_label_density | categorical | 121 | 0.0562 | 0.20 | no | {"Cell": "sparse", "Nature": "sparse", "Science": "sparse"} |
| x_tick_rotation | categorical | 42 | 0.0558 | 0.33 | no | {"Cell": "0", "Nature": "0", "Science": "0"} |
| panel_aspect_class | categorical | 121 | 0.327 | 0.14 | no | {"Cell": "square", "Nature": "wide", "Science": "wide"} |

## scatter

| field | kind | n | p | effect | meaningful | per-family value |
|---|---|---|---|---|---|---|
| typeset_width_mm | numeric | 72 |  |  | no | {"Cell": null, "Nature": 173.22, "Science": null} |
| smallest_cluster_pt | numeric | 72 |  |  | no | {"Cell": null, "Nature": 5.02, "Science": null} |
| dominant_cluster_pt | numeric | 72 |  |  | no | {"Cell": null, "Nature": 5.69, "Science": null} |
| largest_cluster_pt | numeric | 72 |  |  | no | {"Cell": null, "Nature": 6.7, "Science": null} |
| stroke_pt_inferred | numeric | 46 |  |  | no | {"Cell": null, "Nature": 2.52, "Science": null} |
| coloured_fraction | numeric | 244 | 1.13e-08 | 0.14 | YES | {"Cell": 0.05, "Nature": 0.09, "Science": 0.04} |
| n_hue_clusters | numeric | 244 | 0.0702 | 0.01 | no | {"Cell": 3.0, "Nature": 3.0, "Science": 3.0} |
| mean_saturation | numeric | 244 | 5.05e-05 | 0.07 | YES | {"Cell": 0.54, "Nature": 0.64, "Science": 0.58} |
| figure_aspect | numeric | 244 | 0.00315 | 0.04 | no | {"Cell": 0.86, "Nature": 1.03, "Science": 0.86} |
| n_panels_detected | numeric | 244 | 6.24e-05 | 0.07 | YES | {"Cell": 7.0, "Nature": 7.0, "Science": 4.0} |
| legend_entries | numeric | 148 | 0.332 | 0.00 | no | {"Cell": 3.5, "Nature": 4.0, "Science": 4.0} |
| n_categorical_colours | numeric | 259 | 0.876 | -0.01 | no | {"Cell": 2.0, "Nature": 3.0, "Science": 2.0} |
| spines | categorical | 259 | 0.00211 | 0.22 | no | {"Cell": "LB", "Nature": "LB", "Science": "LB"} |
| tick_direction | categorical | 235 | 0.00226 | 0.19 | no | {"Cell": "out", "Nature": "out", "Science": "out"} |
| grid | categorical | 259 | 0.0108 | 0.19 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| background | categorical | 259 | 0.438 | 0.08 | no | {"Cell": "white", "Nature": "white", "Science": "white"} |
| error_bar_style | categorical | 195 | 0.089 | 0.19 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| points_overlaid | categorical | 3 |  |  | no | {"Cell": "no", "Nature": "no", "Science": null} |
| marker_fill | categorical | 259 | 0.182 | 0.11 | no | {"Cell": "filled", "Nature": "filled", "Science": "filled"} |
| marker_size_class | categorical | 259 | 0.212 | 0.11 | no | {"Cell": "small", "Nature": "small", "Science": "small"} |
| line_weight_class | categorical | 34 | 0.0566 | 0.41 | no | {"Cell": "regular", "Nature": "regular", "Science": "regular"} |
| axis_line_weight_class | categorical | 42 | 0.00163 | 0.55 | YES | {"Cell": "regular", "Nature": "heavy", "Science": "regular"} |
| legend_position | categorical | 258 | 0.00971 | 0.20 | no | {"Cell": "none", "Nature": "none", "Science": "inside"} |
| legend_frame | categorical | 162 | 0.246 | 0.13 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| palette_class | categorical | 259 | 0.239 | 0.18 | no | {"Cell": "mixed", "Nature": "saturated", "Science": "mixed"} |
| sequential_cmap_class | categorical | 58 | 0.0177 | 0.43 | no | {"Cell": "other", "Nature": "viridis_like", "Science": "other"} |
| colourbar_position | categorical | 59 | 0.138 | 0.35 | no | {"Cell": "right", "Nature": "right", "Science": "right"} |
| panel_label_case | categorical | 259 | 1.63e-47 | 0.66 | YES | {"Cell": "upper", "Nature": "lower", "Science": "upper"} |
| panel_label_weight | categorical | 255 | 0.0455 | 0.16 | no | {"Cell": "bold", "Nature": "bold", "Science": "bold"} |
| panel_label_size_class | categorical | 255 | 1.28e-37 | 0.82 | YES | {"Cell": "larger", "Nature": "larger", "Science": "much_larger"} |
| font_class | categorical | 259 |  |  | no | {"Cell": "sans", "Nature": "sans", "Science": "sans"} |
| axis_label_weight | categorical | 259 | 0.555 | 0.07 | no | {"Cell": "regular", "Nature": "regular", "Science": "regular"} |
| title_present | categorical | 259 | 6.37e-06 | 0.30 | YES | {"Cell": "yes", "Nature": "no", "Science": "no"} |
| significance_style | categorical | 190 | 0.00924 | 0.19 | no | {"Cell": "none", "Nature": "none", "Science": "none"} |
| brackets | categorical | 167 | 0.711 | 0.06 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| n_stated_in_panel | categorical | 259 | 0.913 | 0.03 | no | {"Cell": "no", "Nature": "no", "Science": "no"} |
| tick_label_density | categorical | 259 | 0.188 | 0.11 | no | {"Cell": "normal", "Nature": "normal", "Science": "normal"} |
| x_tick_rotation | categorical | 224 | 0.0238 | 0.16 | no | {"Cell": "0", "Nature": "0", "Science": "0"} |
| panel_aspect_class | categorical | 259 | 0.556 | 0.08 | no | {"Cell": "square", "Nature": "square", "Science": "square"} |
