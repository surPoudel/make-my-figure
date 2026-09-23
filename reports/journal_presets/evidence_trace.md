# Evidence trace for the experimental publication presets

Generated 2026-09-16 by journal_preset_research/tools/derive_presets.py from journal_preset_research/analysis and journal_preset_research/analysis/group_comparison_summary.json. Evidence classes: OFFICIAL (publisher statement), INFERRED (typeset-PDF measurement with observed scale), OBSERVED (corpus convention, share of coded panels), ESTIMATED (stated assumption), SHARED (no meaningful family difference; applied to every preset).

Papers per evidence family: {'Nature': 63, 'Science': 50, 'Cell': 51}

## Single column 89 mm (N)  (`single_89mm_N.mmfpreset.json`)

Style measured from open-access research figures in evidence set N and the publisher's stated artwork requirements, at the stated single-column width of 89 mm. Changes typography, line weights, palette, legend and axis geometry only. Not an official template.

| value | setting | evidence |
|---|---|---|
| style.show_top_spine | False | SHARED:Nature LB 60%/Science LB 72%/Cell LB 62% |
| style.show_right_spine | False | SHARED:Nature LB 60%/Science LB 72%/Cell LB 62% |
| style.tick_direction | 'out' | SHARED:Nature out 70%/Science out 85%/Cell out 80% |
| style.grid | False | SHARED:Nature no grid 96%/Science no grid 94%/Cell no grid 96% |
| style.legend_frameon | False | SHARED:Nature unframed 96%/Science unframed 86%/Cell unframed 95% |
| style.font_weight | 'normal' | SHARED:Nature regular 90%/Science regular 93%/Cell regular 93% |
| style.palette_name | 'publication' | SHARED:colour-blind-aware categorical palette; corpus modes Nature saturated 39%/Science mixed 40%/Cell saturated 32%; OFFICIAL: Nature figure guide requires an accessible palette |
| style.text_color | '#000000' | OBSERVED:axis and tick text black in the reviewed panels; publishers require standard fonts in black |
| style.tick_label_pt | 5.5 | INFERRED:398 typeset figures, dominant text size median 5.69 pt (IQR 5.36-6.03), clamped to official 5.0-7.0 pt |
| style.axis_font_pt | 6.5 | INFERRED:398 typeset figures, largest text cluster median 6.53 pt, clamped to official 5.0-7.0 pt |
| style.legend_pt | 5.5 | SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus) |
| style.annotation_pt | 5.5 | SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus) |
| style.legend_title_pt | 6.5 | SHARED:set equal to the axis-label size |
| style.title_font_pt | 6.5 | SHARED:set equal to the axis-label size |
| style.base_font_pt | 5.5 | SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus) |
| style.panel_label_pt | 8.0 | OFFICIAL:8.0 pt bold panel letters |
| style.font_family | 'Arial' | OFFICIAL:Arial (Nature figure guide / final-submission artwork page (research-figure-guide.nature.com; nature.com/nature/for-authors/final-submission), Nature Methods AIP page) |
| style.spine_width_pt | 0.5 | INFERRED:vector stroke widths in typeset figures - modes 0.5 pt (15%), 0.18 pt (11%), 0.19 pt (10%); official minimum 0.25 pt; 0.5 pt floor for raster export |
| style.line_width_pt | 0.75 | INFERRED:heaviest common stroke 0.5 pt in typeset figures, kept within official 0.25-1.0 pt |
| style.tick_width | 0.5 | SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes) |
| style.tick_length | 2.5 | ESTIMATED:2.5 pt, about half the tick-label height |
| style.errorbar_line_width | 0.5 | SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes) |
| style.bar_edge_width | 0.5 | SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes) |
| style.marker_edge_width | 0.4 | ESTIMATED:0.4 pt - a visible but light edge; marker edges were 'dark' or 'none' in similar shares |
| style.regression_line_width | 0.75 | SHARED:same as data lines |
| style.grid_width | 0.4 | SHARED:grid is off; width kept light if a user turns it on |
| style.marker_size | 20.0 | ESTIMATED:corpus marker class 'small' (74% of coded panels) -> diameter about 0.8 x tick-label height -> 20.0 pt^2 |
| style.marker_alpha | 0.9 | ESTIMATED:0.9 so overlapping observations remain distinguishable |
| style.errorbar_capsize | 1.5 | OBSERVED:modal error-bar style 'none'; short caps kept for legibility |
| style.legend_loc | 'best' | OBSERVED:legends are most often absent or inside the axes (mode 'none') |
| style.legend_outside | False | OBSERVED:legends outside the axes are the minority; users move them per figure |
| style.legend_ncol | 1 | SHARED:one column |
| layout.column_width | '89mm' | OFFICIAL:89.0 mm stated single width |
| layout.legend_location | 'best' | OBSERVED:see legend_loc |
| output.formats | ['pdf', 'svg', 'png'] | OFFICIAL:vector (PDF/EPS/AI) preferred by every publisher; PNG for review copies |
| output.width_mm | 89.0 | OFFICIAL:same as column_width |
| output.dpi | 450 | OFFICIAL:450 dpi (recommended) |

## Full width 183 mm (N)  (`full_183mm_N.mmfpreset.json`)

Style measured from open-access research figures in evidence set N and the publisher's stated artwork requirements, at the stated full-page width of 183 mm. Changes typography, line weights, palette, legend and axis geometry only. Not an official template.

| value | setting | evidence |
|---|---|---|
| style.show_top_spine | False | SHARED:Nature LB 60%/Science LB 72%/Cell LB 62% |
| style.show_right_spine | False | SHARED:Nature LB 60%/Science LB 72%/Cell LB 62% |
| style.tick_direction | 'out' | SHARED:Nature out 70%/Science out 85%/Cell out 80% |
| style.grid | False | SHARED:Nature no grid 96%/Science no grid 94%/Cell no grid 96% |
| style.legend_frameon | False | SHARED:Nature unframed 96%/Science unframed 86%/Cell unframed 95% |
| style.font_weight | 'normal' | SHARED:Nature regular 90%/Science regular 93%/Cell regular 93% |
| style.palette_name | 'publication' | SHARED:colour-blind-aware categorical palette; corpus modes Nature saturated 39%/Science mixed 40%/Cell saturated 32%; OFFICIAL: Nature figure guide requires an accessible palette |
| style.text_color | '#000000' | OBSERVED:axis and tick text black in the reviewed panels; publishers require standard fonts in black |
| style.tick_label_pt | 5.5 | INFERRED:398 typeset figures, dominant text size median 5.69 pt (IQR 5.36-6.03), clamped to official 5.0-7.0 pt |
| style.axis_font_pt | 6.5 | INFERRED:398 typeset figures, largest text cluster median 6.53 pt, clamped to official 5.0-7.0 pt |
| style.legend_pt | 5.5 | SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus) |
| style.annotation_pt | 5.5 | SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus) |
| style.legend_title_pt | 6.5 | SHARED:set equal to the axis-label size |
| style.title_font_pt | 6.5 | SHARED:set equal to the axis-label size |
| style.base_font_pt | 5.5 | SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus) |
| style.panel_label_pt | 8.0 | OFFICIAL:8.0 pt bold panel letters |
| style.font_family | 'Arial' | OFFICIAL:Arial (Nature figure guide / final-submission artwork page (research-figure-guide.nature.com; nature.com/nature/for-authors/final-submission), Nature Methods AIP page) |
| style.spine_width_pt | 0.5 | INFERRED:vector stroke widths in typeset figures - modes 0.5 pt (15%), 0.18 pt (11%), 0.19 pt (10%); official minimum 0.25 pt; 0.5 pt floor for raster export |
| style.line_width_pt | 0.75 | INFERRED:heaviest common stroke 0.5 pt in typeset figures, kept within official 0.25-1.0 pt |
| style.tick_width | 0.5 | SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes) |
| style.tick_length | 2.5 | ESTIMATED:2.5 pt, about half the tick-label height |
| style.errorbar_line_width | 0.5 | SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes) |
| style.bar_edge_width | 0.5 | SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes) |
| style.marker_edge_width | 0.4 | ESTIMATED:0.4 pt - a visible but light edge; marker edges were 'dark' or 'none' in similar shares |
| style.regression_line_width | 0.75 | SHARED:same as data lines |
| style.grid_width | 0.4 | SHARED:grid is off; width kept light if a user turns it on |
| style.marker_size | 20.0 | ESTIMATED:corpus marker class 'small' (74% of coded panels) -> diameter about 0.8 x tick-label height -> 20.0 pt^2 |
| style.marker_alpha | 0.9 | ESTIMATED:0.9 so overlapping observations remain distinguishable |
| style.errorbar_capsize | 1.5 | OBSERVED:modal error-bar style 'none'; short caps kept for legibility |
| style.legend_loc | 'best' | OBSERVED:legends are most often absent or inside the axes (mode 'none') |
| style.legend_outside | False | OBSERVED:legends outside the axes are the minority; users move them per figure |
| style.legend_ncol | 1 | SHARED:one column |
| layout.column_width | '183mm' | OFFICIAL:183.0 mm stated full width |
| layout.legend_location | 'best' | OBSERVED:see legend_loc |
| output.formats | ['pdf', 'svg', 'png'] | OFFICIAL:vector (PDF/EPS/AI) preferred by every publisher; PNG for review copies |
| output.width_mm | 183.0 | OFFICIAL:same as column_width |
| output.dpi | 450 | OFFICIAL:450 dpi (recommended) |

## Single column 57 mm (S)  (`single_57mm_S.mmfpreset.json`)

Style measured from open-access research figures in evidence set S and the publisher's stated artwork requirements, at the stated single-column width of 57 mm. Changes typography, line weights, palette, legend and axis geometry only. Not an official template.

| value | setting | evidence |
|---|---|---|
| style.show_top_spine | False | SHARED:Nature LB 60%/Science LB 72%/Cell LB 62% |
| style.show_right_spine | False | SHARED:Nature LB 60%/Science LB 72%/Cell LB 62% |
| style.tick_direction | 'out' | SHARED:Nature out 70%/Science out 85%/Cell out 80% |
| style.grid | False | SHARED:Nature no grid 96%/Science no grid 94%/Cell no grid 96% |
| style.legend_frameon | False | SHARED:Nature unframed 96%/Science unframed 86%/Cell unframed 95% |
| style.font_weight | 'normal' | SHARED:Nature regular 90%/Science regular 93%/Cell regular 93% |
| style.palette_name | 'publication' | SHARED:colour-blind-aware categorical palette; corpus modes Nature saturated 39%/Science mixed 40%/Cell saturated 32%; OFFICIAL: Nature figure guide requires an accessible palette |
| style.text_color | '#000000' | OBSERVED:axis and tick text black in the reviewed panels; publishers require standard fonts in black |
| style.tick_label_pt | 6.5 | OFFICIAL:Science instructions for preparing initial/revised manuscripts (science.org, Wayback captures 2025-08-10 / 2025-03-30): 5.7 / 12.1 / 18.4 cm widths, Helvetica preferred, not smaller than 5 pt and about 7 pt after reduction, lines >= 0.5 pt, 10 pt bold capital panel letters, >= 300 dpi; accessed 2026-09-16 (no typeset-scale measurement available for this family; web images give relative sizes only) |
| style.axis_font_pt | 7.5 | OFFICIAL:Science instructions for preparing initial/revised manuscripts (science.org, Wayback captures 2025-08-10 / 2025-03-30): 5.7 / 12.1 / 18.4 cm widths, Helvetica preferred, not smaller than 5 pt and about 7 pt after reduction, lines >= 0.5 pt, 10 pt bold capital panel letters, >= 300 dpi; accessed 2026-09-16 (no typeset-scale measurement available for this family; web images give relative sizes only) |
| style.legend_pt | 6.5 | SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus) |
| style.annotation_pt | 6.5 | SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus) |
| style.legend_title_pt | 7.5 | SHARED:set equal to the axis-label size |
| style.title_font_pt | 7.5 | SHARED:set equal to the axis-label size |
| style.base_font_pt | 6.5 | SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus) |
| style.panel_label_pt | 10.0 | OFFICIAL:10.0 pt bold panel letters |
| style.font_family | 'Helvetica' | OFFICIAL:Helvetica (Science instructions for preparing initial/revised manuscripts (science.org, Wayback captures 2025-08-10 / 2025-03-30)) |
| style.spine_width_pt | 0.5 | OFFICIAL:minimum line weight 0.5 pt (Science instructions for preparing initial/revised manuscripts (science.org, Wayback captures 2025-08-10 / 2025-03-30)); no typeset-scale measurement for this family |
| style.line_width_pt | 0.75 | ESTIMATED:data lines drawn 0.25 pt heavier than axes, within the official range |
| style.tick_width | 0.5 | SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes) |
| style.tick_length | 2.5 | ESTIMATED:2.5 pt, about half the tick-label height |
| style.errorbar_line_width | 0.5 | SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes) |
| style.bar_edge_width | 0.5 | SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes) |
| style.marker_edge_width | 0.4 | ESTIMATED:0.4 pt - a visible but light edge; marker edges were 'dark' or 'none' in similar shares |
| style.regression_line_width | 0.75 | SHARED:same as data lines |
| style.grid_width | 0.4 | SHARED:grid is off; width kept light if a user turns it on |
| style.marker_size | 20.0 | ESTIMATED:corpus marker class 'small' (81% of coded panels) -> diameter about 0.8 x tick-label height -> 20.0 pt^2 |
| style.marker_alpha | 0.9 | ESTIMATED:0.9 so overlapping observations remain distinguishable |
| style.errorbar_capsize | 1.5 | OBSERVED:modal error-bar style 'none'; short caps kept for legibility |
| style.legend_loc | 'best' | OBSERVED:legends are most often absent or inside the axes (mode 'none') |
| style.legend_outside | False | OBSERVED:legends outside the axes are the minority; users move them per figure |
| style.legend_ncol | 1 | SHARED:one column |
| layout.column_width | '57mm' | OFFICIAL:57.0 mm stated single width |
| layout.legend_location | 'best' | OBSERVED:see legend_loc |
| output.formats | ['pdf', 'svg', 'png'] | OFFICIAL:vector (PDF/EPS/AI) preferred by every publisher; PNG for review copies |
| output.width_mm | 57.0 | OFFICIAL:same as column_width |
| output.dpi | 300 | OFFICIAL:300 dpi (minimum) |

## Full width 184 mm (S)  (`full_184mm_S.mmfpreset.json`)

Style measured from open-access research figures in evidence set S and the publisher's stated artwork requirements, at the stated full-page width of 184 mm. Changes typography, line weights, palette, legend and axis geometry only. Not an official template.

| value | setting | evidence |
|---|---|---|
| style.show_top_spine | False | SHARED:Nature LB 60%/Science LB 72%/Cell LB 62% |
| style.show_right_spine | False | SHARED:Nature LB 60%/Science LB 72%/Cell LB 62% |
| style.tick_direction | 'out' | SHARED:Nature out 70%/Science out 85%/Cell out 80% |
| style.grid | False | SHARED:Nature no grid 96%/Science no grid 94%/Cell no grid 96% |
| style.legend_frameon | False | SHARED:Nature unframed 96%/Science unframed 86%/Cell unframed 95% |
| style.font_weight | 'normal' | SHARED:Nature regular 90%/Science regular 93%/Cell regular 93% |
| style.palette_name | 'publication' | SHARED:colour-blind-aware categorical palette; corpus modes Nature saturated 39%/Science mixed 40%/Cell saturated 32%; OFFICIAL: Nature figure guide requires an accessible palette |
| style.text_color | '#000000' | OBSERVED:axis and tick text black in the reviewed panels; publishers require standard fonts in black |
| style.tick_label_pt | 6.5 | OFFICIAL:Science instructions for preparing initial/revised manuscripts (science.org, Wayback captures 2025-08-10 / 2025-03-30): 5.7 / 12.1 / 18.4 cm widths, Helvetica preferred, not smaller than 5 pt and about 7 pt after reduction, lines >= 0.5 pt, 10 pt bold capital panel letters, >= 300 dpi; accessed 2026-09-16 (no typeset-scale measurement available for this family; web images give relative sizes only) |
| style.axis_font_pt | 7.5 | OFFICIAL:Science instructions for preparing initial/revised manuscripts (science.org, Wayback captures 2025-08-10 / 2025-03-30): 5.7 / 12.1 / 18.4 cm widths, Helvetica preferred, not smaller than 5 pt and about 7 pt after reduction, lines >= 0.5 pt, 10 pt bold capital panel letters, >= 300 dpi; accessed 2026-09-16 (no typeset-scale measurement available for this family; web images give relative sizes only) |
| style.legend_pt | 6.5 | SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus) |
| style.annotation_pt | 6.5 | SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus) |
| style.legend_title_pt | 7.5 | SHARED:set equal to the axis-label size |
| style.title_font_pt | 7.5 | SHARED:set equal to the axis-label size |
| style.base_font_pt | 6.5 | SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus) |
| style.panel_label_pt | 10.0 | OFFICIAL:10.0 pt bold panel letters |
| style.font_family | 'Helvetica' | OFFICIAL:Helvetica (Science instructions for preparing initial/revised manuscripts (science.org, Wayback captures 2025-08-10 / 2025-03-30)) |
| style.spine_width_pt | 0.5 | OFFICIAL:minimum line weight 0.5 pt (Science instructions for preparing initial/revised manuscripts (science.org, Wayback captures 2025-08-10 / 2025-03-30)); no typeset-scale measurement for this family |
| style.line_width_pt | 0.75 | ESTIMATED:data lines drawn 0.25 pt heavier than axes, within the official range |
| style.tick_width | 0.5 | SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes) |
| style.tick_length | 2.5 | ESTIMATED:2.5 pt, about half the tick-label height |
| style.errorbar_line_width | 0.5 | SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes) |
| style.bar_edge_width | 0.5 | SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes) |
| style.marker_edge_width | 0.4 | ESTIMATED:0.4 pt - a visible but light edge; marker edges were 'dark' or 'none' in similar shares |
| style.regression_line_width | 0.75 | SHARED:same as data lines |
| style.grid_width | 0.4 | SHARED:grid is off; width kept light if a user turns it on |
| style.marker_size | 20.0 | ESTIMATED:corpus marker class 'small' (81% of coded panels) -> diameter about 0.8 x tick-label height -> 20.0 pt^2 |
| style.marker_alpha | 0.9 | ESTIMATED:0.9 so overlapping observations remain distinguishable |
| style.errorbar_capsize | 1.5 | OBSERVED:modal error-bar style 'none'; short caps kept for legibility |
| style.legend_loc | 'best' | OBSERVED:legends are most often absent or inside the axes (mode 'none') |
| style.legend_outside | False | OBSERVED:legends outside the axes are the minority; users move them per figure |
| style.legend_ncol | 1 | SHARED:one column |
| layout.column_width | '184mm' | OFFICIAL:184.0 mm stated full width |
| layout.legend_location | 'best' | OBSERVED:see legend_loc |
| output.formats | ['pdf', 'svg', 'png'] | OFFICIAL:vector (PDF/EPS/AI) preferred by every publisher; PNG for review copies |
| output.width_mm | 184.0 | OFFICIAL:same as column_width |
| output.dpi | 300 | OFFICIAL:300 dpi (minimum) |

## Single column 85 mm (C)  (`single_85mm_C.mmfpreset.json`)

Style measured from open-access research figures in evidence set C and the publisher's stated artwork requirements, at the stated single-column width of 85 mm. Changes typography, line weights, palette, legend and axis geometry only. Not an official template.

| value | setting | evidence |
|---|---|---|
| style.show_top_spine | False | SHARED:Nature LB 60%/Science LB 72%/Cell LB 62% |
| style.show_right_spine | False | SHARED:Nature LB 60%/Science LB 72%/Cell LB 62% |
| style.tick_direction | 'out' | SHARED:Nature out 70%/Science out 85%/Cell out 80% |
| style.grid | False | SHARED:Nature no grid 96%/Science no grid 94%/Cell no grid 96% |
| style.legend_frameon | False | SHARED:Nature unframed 96%/Science unframed 86%/Cell unframed 95% |
| style.font_weight | 'normal' | SHARED:Nature regular 90%/Science regular 93%/Cell regular 93% |
| style.palette_name | 'publication' | SHARED:colour-blind-aware categorical palette; corpus modes Nature saturated 39%/Science mixed 40%/Cell saturated 32%; OFFICIAL: Nature figure guide requires an accessible palette |
| style.text_color | '#000000' | OBSERVED:axis and tick text black in the reviewed panels; publishers require standard fonts in black |
| style.tick_label_pt | 6.5 | OFFICIAL:Cell Press figure guidelines (cell.com/figureguidelines, Wayback capture 2025-09-11): 85 / 114 / 174 mm widths, Arial only, about 6-8 pt text, 0.5-1.5 pt lines, capital panel letters, >= 300 dpi colour, RGB; accessed 2026-09-16 (no typeset-scale measurement available for this family; web images give relative sizes only) |
| style.axis_font_pt | 7.5 | OFFICIAL:Cell Press figure guidelines (cell.com/figureguidelines, Wayback capture 2025-09-11): 85 / 114 / 174 mm widths, Arial only, about 6-8 pt text, 0.5-1.5 pt lines, capital panel letters, >= 300 dpi colour, RGB; accessed 2026-09-16 (no typeset-scale measurement available for this family; web images give relative sizes only) |
| style.legend_pt | 6.5 | SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus) |
| style.annotation_pt | 6.5 | SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus) |
| style.legend_title_pt | 7.5 | SHARED:set equal to the axis-label size |
| style.title_font_pt | 7.5 | SHARED:set equal to the axis-label size |
| style.base_font_pt | 6.5 | SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus) |
| style.panel_label_pt | 8.0 | ESTIMATED:8 pt - publisher states capital bold letters without a size; corpus panel letters are 'larger' than axis text |
| style.font_family | 'Arial' | OFFICIAL:Arial (Cell Press figure guidelines (cell.com/figureguidelines, Wayback capture 2025-09-11)) |
| style.spine_width_pt | 0.5 | OFFICIAL:minimum line weight 0.5 pt (Cell Press figure guidelines (cell.com/figureguidelines, Wayback capture 2025-09-11)); no typeset-scale measurement for this family |
| style.line_width_pt | 0.75 | ESTIMATED:data lines drawn 0.25 pt heavier than axes, within the official range |
| style.tick_width | 0.5 | SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes) |
| style.tick_length | 2.5 | ESTIMATED:2.5 pt, about half the tick-label height |
| style.errorbar_line_width | 0.5 | SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes) |
| style.bar_edge_width | 0.5 | SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes) |
| style.marker_edge_width | 0.4 | ESTIMATED:0.4 pt - a visible but light edge; marker edges were 'dark' or 'none' in similar shares |
| style.regression_line_width | 0.75 | SHARED:same as data lines |
| style.grid_width | 0.4 | SHARED:grid is off; width kept light if a user turns it on |
| style.marker_size | 20.0 | ESTIMATED:corpus marker class 'small' (68% of coded panels) -> diameter about 0.8 x tick-label height -> 20.0 pt^2 |
| style.marker_alpha | 0.9 | ESTIMATED:0.9 so overlapping observations remain distinguishable |
| style.errorbar_capsize | 1.5 | OBSERVED:modal error-bar style 'none'; short caps kept for legibility |
| style.legend_loc | 'best' | OBSERVED:legends are most often absent or inside the axes (mode 'none') |
| style.legend_outside | False | OBSERVED:legends outside the axes are the minority; users move them per figure |
| style.legend_ncol | 1 | SHARED:one column |
| layout.column_width | '85mm' | OFFICIAL:85.0 mm stated single width |
| layout.legend_location | 'best' | OBSERVED:see legend_loc |
| output.formats | ['pdf', 'svg', 'png'] | OFFICIAL:vector (PDF/EPS/AI) preferred by every publisher; PNG for review copies |
| output.width_mm | 85.0 | OFFICIAL:same as column_width |
| output.dpi | 300 | OFFICIAL:300 dpi (minimum) |

## Full width 174 mm (C)  (`full_174mm_C.mmfpreset.json`)

Style measured from open-access research figures in evidence set C and the publisher's stated artwork requirements, at the stated full-page width of 174 mm. Changes typography, line weights, palette, legend and axis geometry only. Not an official template.

| value | setting | evidence |
|---|---|---|
| style.show_top_spine | False | SHARED:Nature LB 60%/Science LB 72%/Cell LB 62% |
| style.show_right_spine | False | SHARED:Nature LB 60%/Science LB 72%/Cell LB 62% |
| style.tick_direction | 'out' | SHARED:Nature out 70%/Science out 85%/Cell out 80% |
| style.grid | False | SHARED:Nature no grid 96%/Science no grid 94%/Cell no grid 96% |
| style.legend_frameon | False | SHARED:Nature unframed 96%/Science unframed 86%/Cell unframed 95% |
| style.font_weight | 'normal' | SHARED:Nature regular 90%/Science regular 93%/Cell regular 93% |
| style.palette_name | 'publication' | SHARED:colour-blind-aware categorical palette; corpus modes Nature saturated 39%/Science mixed 40%/Cell saturated 32%; OFFICIAL: Nature figure guide requires an accessible palette |
| style.text_color | '#000000' | OBSERVED:axis and tick text black in the reviewed panels; publishers require standard fonts in black |
| style.tick_label_pt | 6.5 | OFFICIAL:Cell Press figure guidelines (cell.com/figureguidelines, Wayback capture 2025-09-11): 85 / 114 / 174 mm widths, Arial only, about 6-8 pt text, 0.5-1.5 pt lines, capital panel letters, >= 300 dpi colour, RGB; accessed 2026-09-16 (no typeset-scale measurement available for this family; web images give relative sizes only) |
| style.axis_font_pt | 7.5 | OFFICIAL:Cell Press figure guidelines (cell.com/figureguidelines, Wayback capture 2025-09-11): 85 / 114 / 174 mm widths, Arial only, about 6-8 pt text, 0.5-1.5 pt lines, capital panel letters, >= 300 dpi colour, RGB; accessed 2026-09-16 (no typeset-scale measurement available for this family; web images give relative sizes only) |
| style.legend_pt | 6.5 | SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus) |
| style.annotation_pt | 6.5 | SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus) |
| style.legend_title_pt | 7.5 | SHARED:set equal to the axis-label size |
| style.title_font_pt | 7.5 | SHARED:set equal to the axis-label size |
| style.base_font_pt | 6.5 | SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus) |
| style.panel_label_pt | 8.0 | ESTIMATED:8 pt - publisher states capital bold letters without a size; corpus panel letters are 'larger' than axis text |
| style.font_family | 'Arial' | OFFICIAL:Arial (Cell Press figure guidelines (cell.com/figureguidelines, Wayback capture 2025-09-11)) |
| style.spine_width_pt | 0.5 | OFFICIAL:minimum line weight 0.5 pt (Cell Press figure guidelines (cell.com/figureguidelines, Wayback capture 2025-09-11)); no typeset-scale measurement for this family |
| style.line_width_pt | 0.75 | ESTIMATED:data lines drawn 0.25 pt heavier than axes, within the official range |
| style.tick_width | 0.5 | SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes) |
| style.tick_length | 2.5 | ESTIMATED:2.5 pt, about half the tick-label height |
| style.errorbar_line_width | 0.5 | SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes) |
| style.bar_edge_width | 0.5 | SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes) |
| style.marker_edge_width | 0.4 | ESTIMATED:0.4 pt - a visible but light edge; marker edges were 'dark' or 'none' in similar shares |
| style.regression_line_width | 0.75 | SHARED:same as data lines |
| style.grid_width | 0.4 | SHARED:grid is off; width kept light if a user turns it on |
| style.marker_size | 20.0 | ESTIMATED:corpus marker class 'small' (68% of coded panels) -> diameter about 0.8 x tick-label height -> 20.0 pt^2 |
| style.marker_alpha | 0.9 | ESTIMATED:0.9 so overlapping observations remain distinguishable |
| style.errorbar_capsize | 1.5 | OBSERVED:modal error-bar style 'none'; short caps kept for legibility |
| style.legend_loc | 'best' | OBSERVED:legends are most often absent or inside the axes (mode 'none') |
| style.legend_outside | False | OBSERVED:legends outside the axes are the minority; users move them per figure |
| style.legend_ncol | 1 | SHARED:one column |
| layout.column_width | '174mm' | OFFICIAL:174.0 mm stated full width |
| layout.legend_location | 'best' | OBSERVED:see legend_loc |
| output.formats | ['pdf', 'svg', 'png'] | OFFICIAL:vector (PDF/EPS/AI) preferred by every publisher; PNG for review copies |
| output.width_mm | 174.0 | OFFICIAL:same as column_width |
| output.dpi | 300 | OFFICIAL:300 dpi (minimum) |

## Bar + observations (jittered)  (`gc_bar_points_jittered.mmfpreset.json`)

The most common group-comparison display in the corpus: a summary bar with every observation jittered over it, error bar with caps, medium bar width.

| value | setting | evidence |
|---|---|---|
| style.marker_alpha | 0.9 | ESTIMATED:0.9 |
| options.points | True | OBSERVED:individual observations visible in 78% of group-comparison panels |
| options.point_arrangement | 'jitter' | OBSERVED:jitter 56%, centred 20%, beeswarm 3% |
| options.point_fill | 'filled' | OBSERVED:filled 53% vs open 19% |
| options.point_edge | 'dark' | OBSERVED:dark edge 31%, none 37%, same colour 12% |
| options.point_edge_width | 0.4 | ESTIMATED:0.4 pt light edge |
| options.point_size | 0.0 | SHARED:0 = adaptive - the renderer scales markers by the number of observations within fixed bounds (never hides points) |
| options.point_alpha | 0.0 | SHARED:0 = adaptive opacity by group size |
| options.bar_width | 0.6 | OBSERVED:medium bar width 57% |
| options.bar_fill | 'filled' | OBSERVED:filled bars dominate; outline-only 4% |
| options.error_cap | True | OBSERVED:capped error bars are the modal style in bar panels |
| options.show_n | 'none' | OBSERVED:n printed in the panel in only 7% of panels; usually in the caption |

## Bar + observations (open circles)  (`gc_bar_points_open.mmfpreset.json`)

Summary bar with open-circle observations in the bar's colour - the second most common marker treatment; keeps the bar fill readable through the points.

| value | setting | evidence |
|---|---|---|
| style.marker_alpha | 0.9 | ESTIMATED:0.9 |
| options.points | True | OBSERVED:individual observations visible in 78% of group-comparison panels |
| options.point_arrangement | 'jitter' | OBSERVED:jitter 56%, centred 20%, beeswarm 3% |
| options.point_fill | 'open' | OBSERVED:open markers 19% of coded panels (second most common) |
| options.point_edge | 'same' | OBSERVED:open markers take the group colour as their edge |
| options.point_edge_width | 0.6 | ESTIMATED:0.6 pt so open circles stay visible when small |
| options.point_size | 0.0 | SHARED:0 = adaptive - the renderer scales markers by the number of observations within fixed bounds (never hides points) |
| options.point_alpha | 0.0 | SHARED:0 = adaptive opacity by group size |
| options.bar_width | 0.6 | OBSERVED:medium bar width 57% |
| options.bar_fill | 'filled' | OBSERVED:filled bars dominate |
| options.error_cap | True | OBSERVED:capped error bars are the modal style |

## Box + observations (outline)  (`gc_box_points_outline.mmfpreset.json`)

Outline box (no fill) with the observations on top - the common minimal box style; whiskers and median in the axis colour.

| value | setting | evidence |
|---|---|---|
| style.marker_alpha | 0.9 | ESTIMATED:0.9 |
| options.points | True | OBSERVED:individual observations visible in 78% of group-comparison panels |
| options.point_arrangement | 'jitter' | OBSERVED:jitter 56%, centred 20%, beeswarm 3% |
| options.point_fill | 'filled' | OBSERVED:filled 53% vs open 19% |
| options.point_edge | 'dark' | OBSERVED:dark edge 31%, none 37%, same colour 12% |
| options.point_edge_width | 0.4 | ESTIMATED:0.4 pt light edge |
| options.point_size | 0.0 | SHARED:0 = adaptive - the renderer scales markers by the number of observations within fixed bounds (never hides points) |
| options.point_alpha | 0.0 | SHARED:0 = adaptive opacity by group size |
| options.kind | 'box' | OBSERVED:box+points 9% of panels |
| options.box_fill | 'outline' | OBSERVED:outline boxes are the common minimal treatment |
| options.box_width | 0.5 | OBSERVED:medium box width 12% of box panels |
| options.show_outliers | False | SHARED:outliers are already drawn as observations |

## Box + observations (light fill)  (`gc_box_points_light.mmfpreset.json`)

Lightly filled box in the group colour with the observations on top.

| value | setting | evidence |
|---|---|---|
| style.marker_alpha | 0.9 | ESTIMATED:0.9 |
| options.points | True | OBSERVED:individual observations visible in 78% of group-comparison panels |
| options.point_arrangement | 'jitter' | OBSERVED:jitter 56%, centred 20%, beeswarm 3% |
| options.point_fill | 'filled' | OBSERVED:filled 53% vs open 19% |
| options.point_edge | 'dark' | OBSERVED:dark edge 31%, none 37%, same colour 12% |
| options.point_edge_width | 0.4 | ESTIMATED:0.4 pt light edge |
| options.point_size | 0.0 | SHARED:0 = adaptive - the renderer scales markers by the number of observations within fixed bounds (never hides points) |
| options.point_alpha | 0.0 | SHARED:0 = adaptive opacity by group size |
| options.kind | 'box' | OBSERVED:box+points 9% of panels |
| options.box_fill | 'light' | OBSERVED:filled boxes in the group colour are the other common treatment |
| options.box_width | 0.5 | OBSERVED:medium box width |
| options.show_outliers | False | SHARED:outliers are already drawn as observations |

## Violin + observations  (`gc_violin_points.mmfpreset.json`)

Violin body with the observations on top; used for larger groups where the distribution shape matters.

| value | setting | evidence |
|---|---|---|
| style.marker_alpha | 0.9 | ESTIMATED:0.9 |
| options.points | True | OBSERVED:individual observations visible in 78% of group-comparison panels |
| options.point_arrangement | 'jitter' | OBSERVED:jitter 56%, centred 20%, beeswarm 3% |
| options.point_fill | 'filled' | OBSERVED:filled 53% vs open 19% |
| options.point_edge | 'dark' | OBSERVED:dark edge 31%, none 37%, same colour 12% |
| options.point_edge_width | 0.4 | ESTIMATED:0.4 pt light edge |
| options.point_size | 0.0 | SHARED:0 = adaptive - the renderer scales markers by the number of observations within fixed bounds (never hides points) |
| options.point_alpha | 0.0 | SHARED:0 = adaptive opacity by group size |
| options.kind | 'violin' | OBSERVED:violin+points 3% of panels (most common at large n) |
| options.show_outliers | False | SHARED:not applicable to violins |

## Many observations per group  (`gc_dense_groups.mmfpreset.json`)

For large groups: small, semi-transparent centred observations over a box so the distribution stays legible; the renderer still draws every point.

| value | setting | evidence |
|---|---|---|
| style.marker_alpha | 0.9 | ESTIMATED:0.9 |
| options.points | True | OBSERVED:individual observations visible in 78% of group-comparison panels |
| options.point_arrangement | 'jitter' | OBSERVED:jitter 56%, centred 20%, beeswarm 3% |
| options.point_fill | 'filled' | OBSERVED:filled 53% vs open 19% |
| options.point_edge | 'none' | ESTIMATED:no edge at high density |
| options.point_edge_width | 0.4 | ESTIMATED:0.4 pt light edge |
| options.point_size | 0.0 | SHARED:0 = adaptive - the renderer scales markers by the number of observations within fixed bounds (never hides points) |
| options.point_alpha | 0.5 | ESTIMATED:0.5 opacity for dense groups |
| options.kind | 'box' | OBSERVED:box+points preferred over bars at large n in the corpus (see group_comparison_summary.md, large-n table) |
| options.box_fill | 'outline' | OBSERVED:outline box |
| options.point_jitter_width | 0.5 | ESTIMATED:wider spread for dense groups |

