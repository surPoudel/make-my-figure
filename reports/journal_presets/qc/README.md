# Experimental preset QC

12 presets x 39 plot types = 468 cells: PASS 293, WARN 69, FAIL 106.

FAIL = overlapping text, clipped annotation, or smallest text below the minimum at the target width. 
WARN = legend over data, exported width off target by more than 15 %, or publication score 'fail'. 
Nothing is auto-fixed; each non-PASS cell is listed for the preset author.

| preset | plot type | status | issues |
|---|---|---|---|
| full_174mm_C | grouped_barplot_with_error_bar | WARN | exported width 119.7 mm deviates -31% from target 174.0 mm |
| full_174mm_C | volcano_plot | WARN | exported width 120.3 mm deviates -31% from target 174.0 mm |
| full_174mm_C | scatterplot_with_regression | WARN | exported width 117.5 mm deviates -32% from target 174.0 mm |
| full_174mm_C | stacked_bar_composition | WARN | legend covers data (47% of legend box) |
| full_174mm_C | waterfall_plot | WARN | exported width 138.2 mm deviates -21% from target 174.0 mm |
| full_174mm_C | oncoprint_mutation_heatmap | WARN | legend covers data (90% of legend box); exported width 144.7 mm deviates -17% from target 174.0 mm |
| full_174mm_C | lollipop_mutation_plot | WARN | exported width 127.3 mm deviates -27% from target 174.0 mm |
| full_174mm_C | ma_plot | FAIL | 1 overlapping text pair(s); exported width 144.0 mm deviates -17% from target 174.0 mm |
| full_174mm_C | dose_response_curve | FAIL | 1 overlapping text pair(s); exported width 118.9 mm deviates -32% from target 174.0 mm |
| full_174mm_C | upset_plot | WARN | exported width 145.3 mm deviates -16% from target 174.0 mm |
| full_174mm_C | swimmer_plot | WARN | exported width 145.0 mm deviates -17% from target 174.0 mm |
| full_174mm_C | spider_plot | WARN | exported width 119.4 mm deviates -31% from target 174.0 mm |
| full_174mm_C | sankey_plot | WARN | exported width 139.5 mm deviates -20% from target 174.0 mm |
| full_174mm_C | embedding_scatter | WARN | exported width 118.1 mm deviates -32% from target 174.0 mm |
| full_174mm_C | hierarchical_clustering | WARN | legend covers data (100% of legend box) |
| full_174mm_C | network_graph | FAIL | 1 overlapping text pair(s); exported width 108.7 mm deviates -38% from target 174.0 mm |
| full_174mm_C | chord_diagram | FAIL | 1 overlapping text pair(s) |
| full_183mm_N | grouped_barplot_with_error_bar | WARN | exported width 124.5 mm deviates -32% from target 183.0 mm |
| full_183mm_N | volcano_plot | WARN | exported width 125.2 mm deviates -32% from target 183.0 mm |
| full_183mm_N | scatterplot_with_regression | WARN | exported width 122.6 mm deviates -33% from target 183.0 mm |
| full_183mm_N | stacked_bar_composition | WARN | legend covers data (39% of legend box) |
| full_183mm_N | waterfall_plot | WARN | exported width 151.9 mm deviates -17% from target 183.0 mm |
| full_183mm_N | oncoprint_mutation_heatmap | WARN | legend covers data (88% of legend box) |
| full_183mm_N | lollipop_mutation_plot | WARN | exported width 132.9 mm deviates -27% from target 183.0 mm |
| full_183mm_N | ma_plot | FAIL | 1 overlapping text pair(s); exported width 150.5 mm deviates -18% from target 183.0 mm |
| full_183mm_N | dose_response_curve | FAIL | 1 overlapping text pair(s); exported width 123.8 mm deviates -32% from target 183.0 mm |
| full_183mm_N | upset_plot | WARN | exported width 149.3 mm deviates -18% from target 183.0 mm |
| full_183mm_N | swimmer_plot | WARN | exported width 151.3 mm deviates -17% from target 183.0 mm |
| full_183mm_N | spider_plot | WARN | exported width 124.3 mm deviates -32% from target 183.0 mm |
| full_183mm_N | sankey_plot | WARN | exported width 139.5 mm deviates -24% from target 183.0 mm |
| full_183mm_N | embedding_scatter | WARN | exported width 123.2 mm deviates -33% from target 183.0 mm |
| full_183mm_N | hierarchical_clustering | WARN | legend covers data (100% of legend box) |
| full_183mm_N | network_graph | FAIL | 1 overlapping text pair(s); exported width 114.4 mm deviates -38% from target 183.0 mm |
| full_184mm_S | grouped_barplot_with_error_bar | WARN | exported width 125.9 mm deviates -32% from target 184.0 mm |
| full_184mm_S | volcano_plot | WARN | exported width 126.6 mm deviates -31% from target 184.0 mm |
| full_184mm_S | scatterplot_with_regression | WARN | exported width 123.8 mm deviates -33% from target 184.0 mm |
| full_184mm_S | stacked_bar_composition | WARN | legend covers data (44% of legend box) |
| full_184mm_S | waterfall_plot | WARN | exported width 148.0 mm deviates -20% from target 184.0 mm |
| full_184mm_S | oncoprint_mutation_heatmap | WARN | legend covers data (98% of legend box); exported width 154.7 mm deviates -16% from target 184.0 mm |
| full_184mm_S | lollipop_mutation_plot | WARN | exported width 134.1 mm deviates -27% from target 184.0 mm |
| full_184mm_S | ma_plot | FAIL | 1 overlapping text pair(s); exported width 151.8 mm deviates -18% from target 184.0 mm |
| full_184mm_S | dose_response_curve | FAIL | 1 overlapping text pair(s); exported width 125.2 mm deviates -32% from target 184.0 mm |
| full_184mm_S | upset_plot | WARN | exported width 152.5 mm deviates -17% from target 184.0 mm |
| full_184mm_S | swimmer_plot | WARN | exported width 152.8 mm deviates -17% from target 184.0 mm |
| full_184mm_S | spider_plot | WARN | exported width 125.6 mm deviates -32% from target 184.0 mm |
| full_184mm_S | sankey_plot | WARN | exported width 139.5 mm deviates -24% from target 184.0 mm |
| full_184mm_S | embedding_scatter | WARN | exported width 124.4 mm deviates -32% from target 184.0 mm |
| full_184mm_S | hierarchical_clustering | WARN | legend covers data (100% of legend box) |
| full_184mm_S | network_graph | FAIL | 1 overlapping text pair(s); exported width 115.0 mm deviates -38% from target 184.0 mm |
| full_184mm_S | chord_diagram | FAIL | 1 overlapping text pair(s) |
| gc_bar_points_jittered | volcano_plot | FAIL | 4 overlapping text pair(s) |
| gc_bar_points_jittered | scatterplot_with_regression | FAIL | 1 overlapping text pair(s) |
| gc_bar_points_jittered | lineplot_timecourse_with_error_band | WARN | legend covers data (21% of legend box) |
| gc_bar_points_jittered | stacked_bar_composition | FAIL | 29 overlapping text pair(s) |
| gc_bar_points_jittered | pca_scatter_from_matrix | FAIL | 1 overlapping text pair(s) |
| gc_bar_points_jittered | ma_plot | FAIL | 6 overlapping text pair(s); 2 clipped annotation(s) |
| gc_bar_points_jittered | manhattan_plot | WARN | legend covers data (21% of legend box) |
| gc_bar_points_jittered | bland_altman_plot | FAIL | 3 overlapping text pair(s) |
| gc_bar_points_jittered | dose_response_curve | FAIL | 1 overlapping text pair(s) |
| gc_bar_points_jittered | spider_plot | FAIL | 1 overlapping text pair(s) |
| gc_bar_points_jittered | chord_diagram | FAIL | 3 overlapping text pair(s) |
| gc_bar_points_open | volcano_plot | FAIL | 4 overlapping text pair(s) |
| gc_bar_points_open | scatterplot_with_regression | FAIL | 1 overlapping text pair(s) |
| gc_bar_points_open | lineplot_timecourse_with_error_band | WARN | legend covers data (21% of legend box) |
| gc_bar_points_open | stacked_bar_composition | FAIL | 29 overlapping text pair(s) |
| gc_bar_points_open | pca_scatter_from_matrix | FAIL | 1 overlapping text pair(s) |
| gc_bar_points_open | ma_plot | FAIL | 6 overlapping text pair(s); 2 clipped annotation(s) |
| gc_bar_points_open | manhattan_plot | WARN | legend covers data (21% of legend box) |
| gc_bar_points_open | bland_altman_plot | FAIL | 3 overlapping text pair(s) |
| gc_bar_points_open | dose_response_curve | FAIL | 1 overlapping text pair(s) |
| gc_bar_points_open | spider_plot | FAIL | 1 overlapping text pair(s) |
| gc_bar_points_open | network_graph | FAIL | 1 overlapping text pair(s) |
| gc_bar_points_open | chord_diagram | FAIL | 3 overlapping text pair(s) |
| gc_box_points_light | volcano_plot | FAIL | 4 overlapping text pair(s) |
| gc_box_points_light | scatterplot_with_regression | FAIL | 1 overlapping text pair(s) |
| gc_box_points_light | lineplot_timecourse_with_error_band | WARN | legend covers data (21% of legend box) |
| gc_box_points_light | stacked_bar_composition | FAIL | 29 overlapping text pair(s) |
| gc_box_points_light | pca_scatter_from_matrix | FAIL | 1 overlapping text pair(s) |
| gc_box_points_light | ma_plot | FAIL | 6 overlapping text pair(s); 2 clipped annotation(s) |
| gc_box_points_light | manhattan_plot | WARN | legend covers data (21% of legend box) |
| gc_box_points_light | bland_altman_plot | FAIL | 3 overlapping text pair(s) |
| gc_box_points_light | dose_response_curve | FAIL | 1 overlapping text pair(s) |
| gc_box_points_light | spider_plot | FAIL | 1 overlapping text pair(s) |
| gc_box_points_light | network_graph | FAIL | 1 overlapping text pair(s) |
| gc_box_points_light | chord_diagram | FAIL | 3 overlapping text pair(s) |
| gc_box_points_outline | volcano_plot | FAIL | 3 overlapping text pair(s) |
| gc_box_points_outline | scatterplot_with_regression | FAIL | 1 overlapping text pair(s) |
| gc_box_points_outline | lineplot_timecourse_with_error_band | WARN | legend covers data (21% of legend box) |
| gc_box_points_outline | stacked_bar_composition | FAIL | 29 overlapping text pair(s) |
| gc_box_points_outline | pca_scatter_from_matrix | FAIL | 1 overlapping text pair(s) |
| gc_box_points_outline | ma_plot | FAIL | 6 overlapping text pair(s); 2 clipped annotation(s) |
| gc_box_points_outline | manhattan_plot | WARN | legend covers data (21% of legend box) |
| gc_box_points_outline | bland_altman_plot | FAIL | 3 overlapping text pair(s) |
| gc_box_points_outline | dose_response_curve | FAIL | 1 overlapping text pair(s) |
| gc_box_points_outline | spider_plot | FAIL | 1 overlapping text pair(s) |
| gc_box_points_outline | network_graph | FAIL | 1 overlapping text pair(s) |
| gc_box_points_outline | chord_diagram | FAIL | 3 overlapping text pair(s) |
| gc_dense_groups | volcano_plot | FAIL | 4 overlapping text pair(s) |
| gc_dense_groups | scatterplot_with_regression | FAIL | 1 overlapping text pair(s) |
| gc_dense_groups | lineplot_timecourse_with_error_band | WARN | legend covers data (21% of legend box) |
| gc_dense_groups | stacked_bar_composition | FAIL | 29 overlapping text pair(s) |
| gc_dense_groups | pca_scatter_from_matrix | FAIL | 1 overlapping text pair(s) |
| gc_dense_groups | ma_plot | FAIL | 6 overlapping text pair(s); 2 clipped annotation(s) |
| gc_dense_groups | manhattan_plot | WARN | legend covers data (21% of legend box) |
| gc_dense_groups | bland_altman_plot | FAIL | 3 overlapping text pair(s) |
| gc_dense_groups | dose_response_curve | FAIL | 1 overlapping text pair(s) |
| gc_dense_groups | spider_plot | FAIL | 1 overlapping text pair(s) |
| gc_dense_groups | network_graph | FAIL | 1 overlapping text pair(s) |
| gc_dense_groups | chord_diagram | FAIL | 3 overlapping text pair(s) |
| gc_violin_points | volcano_plot | FAIL | 3 overlapping text pair(s) |
| gc_violin_points | scatterplot_with_regression | FAIL | 1 overlapping text pair(s) |
| gc_violin_points | lineplot_timecourse_with_error_band | WARN | legend covers data (21% of legend box) |
| gc_violin_points | stacked_bar_composition | FAIL | 29 overlapping text pair(s) |
| gc_violin_points | pca_scatter_from_matrix | FAIL | 1 overlapping text pair(s) |
| gc_violin_points | ma_plot | FAIL | 6 overlapping text pair(s); 2 clipped annotation(s) |
| gc_violin_points | manhattan_plot | WARN | legend covers data (21% of legend box) |
| gc_violin_points | bland_altman_plot | FAIL | 3 overlapping text pair(s) |
| gc_violin_points | dose_response_curve | FAIL | 1 overlapping text pair(s) |
| gc_violin_points | spider_plot | FAIL | 1 overlapping text pair(s) |
| gc_violin_points | network_graph | FAIL | 1 overlapping text pair(s) |
| gc_violin_points | chord_diagram | FAIL | 3 overlapping text pair(s) |
| single_57mm_S | barplot_with_error_bar | FAIL | 1 overlapping text pair(s) |
| single_57mm_S | grouped_barplot_with_error_bar | WARN | legend covers data (25% of legend box); exported width 45.1 mm deviates -21% from target 57.0 mm |
| single_57mm_S | heatmap_clustered_matrix | FAIL | 11 overlapping text pair(s) |
| single_57mm_S | volcano_plot | FAIL | 5 overlapping text pair(s); legend covers data (21% of legend box); smallest text 3.99 pt at 57.0 mm (minimum 5.0 pt; role tick); exported width 92.9 mm deviates +63% from target 57.0 mm |
| single_57mm_S | scatterplot_with_regression | FAIL | 1 overlapping text pair(s); legend covers data (17% of legend box); smallest text 4.83 pt at 57.0 mm (minimum 5.0 pt; role tick); exported width 76.7 mm deviates +35% from target 57.0 mm |
| single_57mm_S | lineplot_timecourse_with_error_band | WARN | legend covers data (42% of legend box) |
| single_57mm_S | enrichment_dotplot | FAIL | 6 overlapping text pair(s) |
| single_57mm_S | stacked_bar_composition | FAIL | 29 overlapping text pair(s); legend covers data (77% of legend box) |
| single_57mm_S | waterfall_plot | FAIL | 3 overlapping text pair(s); legend covers data (25% of legend box); exported width 28.2 mm deviates -50% from target 57.0 mm |
| single_57mm_S | oncoprint_mutation_heatmap | WARN | legend covers data (67% of legend box); exported width 35.2 mm deviates -38% from target 57.0 mm |
| single_57mm_S | lollipop_mutation_plot | FAIL | 6 overlapping text pair(s); legend covers data (46% of legend box) |
| single_57mm_S | hierarchical_dendrogram | FAIL | 23 overlapping text pair(s) |
| single_57mm_S | ma_plot | FAIL | 8 overlapping text pair(s); 3 clipped annotation(s); legend covers data (62% of legend box) |
| single_57mm_S | manhattan_plot | FAIL | 22 overlapping text pair(s); legend covers data (46% of legend box) |
| single_57mm_S | confusion_matrix | WARN | exported width 73.8 mm deviates +30% from target 57.0 mm |
| single_57mm_S | dose_response_curve | FAIL | 2 overlapping text pair(s); exported width 45.8 mm deviates -20% from target 57.0 mm |
| single_57mm_S | upset_plot | FAIL | smallest text 2.86 pt at 57.0 mm (minimum 5.0 pt; role tick); exported width 129.7 mm deviates +128% from target 57.0 mm |
| single_57mm_S | swimmer_plot | WARN | legend covers data (50% of legend box) |
| single_57mm_S | spider_plot | FAIL | 1 overlapping text pair(s); legend covers data (62% of legend box); exported width 46.3 mm deviates -19% from target 57.0 mm |
| single_57mm_S | sankey_plot | FAIL | smallest text 2.66 pt at 57.0 mm (minimum 5.0 pt; role tick); exported width 139.5 mm deviates +145% from target 57.0 mm |
| single_57mm_S | embedding_scatter | WARN | legend covers data (58% of legend box); exported width 45.3 mm deviates -20% from target 57.0 mm |
| single_57mm_S | hierarchical_clustering | FAIL | 18 overlapping text pair(s); legend covers data (100% of legend box); exported width 41.9 mm deviates -26% from target 57.0 mm |
| single_57mm_S | network_graph | FAIL | smallest text 4.49 pt at 57.0 mm (minimum 5.0 pt; role legend); exported width 82.5 mm deviates +45% from target 57.0 mm |
| single_85mm_C | grouped_barplot_with_error_bar | WARN | exported width 64.0 mm deviates -25% from target 85.0 mm |
| single_85mm_C | volcano_plot | FAIL | 2 overlapping text pair(s) |
| single_85mm_C | scatterplot_with_regression | FAIL | 1 overlapping text pair(s) |
| single_85mm_C | stacked_bar_composition | WARN | legend covers data (70% of legend box) |
| single_85mm_C | waterfall_plot | WARN | legend covers data (17% of legend box); exported width 50.6 mm deviates -40% from target 85.0 mm |
| single_85mm_C | oncoprint_mutation_heatmap | WARN | legend covers data (97% of legend box); exported width 55.7 mm deviates -34% from target 85.0 mm |
| single_85mm_C | lollipop_mutation_plot | FAIL | 5 overlapping text pair(s); legend covers data (33% of legend box); exported width 68.9 mm deviates -19% from target 85.0 mm |
| single_85mm_C | ma_plot | FAIL | 8 overlapping text pair(s); 2 clipped annotation(s); legend covers data (17% of legend box) |
| single_85mm_C | bland_altman_plot | FAIL | 1 overlapping text pair(s) |
| single_85mm_C | dose_response_curve | FAIL | 1 overlapping text pair(s); exported width 63.3 mm deviates -26% from target 85.0 mm |
| single_85mm_C | upset_plot | FAIL | smallest text 4.26 pt at 85.0 mm (minimum 5.0 pt; role tick); exported width 129.7 mm deviates +53% from target 85.0 mm |
| single_85mm_C | spider_plot | WARN | legend covers data (17% of legend box); exported width 63.8 mm deviates -25% from target 85.0 mm |
| single_85mm_C | sankey_plot | FAIL | smallest text 3.96 pt at 85.0 mm (minimum 5.0 pt; role tick); exported width 139.5 mm deviates +64% from target 85.0 mm |
| single_85mm_C | embedding_scatter | FAIL | 1 overlapping text pair(s); legend covers data (38% of legend box); exported width 62.5 mm deviates -26% from target 85.0 mm |
| single_85mm_C | hierarchical_clustering | WARN | legend covers data (100% of legend box) |
| single_85mm_C | chord_diagram | FAIL | 1 overlapping text pair(s) |
| single_89mm_N | grouped_barplot_with_error_bar | WARN | exported width 65.7 mm deviates -26% from target 89.0 mm |
| single_89mm_N | volcano_plot | FAIL | 3 overlapping text pair(s) |
| single_89mm_N | scatterplot_with_regression | FAIL | 1 overlapping text pair(s) |
| single_89mm_N | histogram_distribution | FAIL | 1 overlapping text pair(s) |
| single_89mm_N | stacked_bar_composition | WARN | legend covers data (65% of legend box) |
| single_89mm_N | waterfall_plot | WARN | exported width 59.3 mm deviates -33% from target 89.0 mm |
| single_89mm_N | oncoprint_mutation_heatmap | WARN | legend covers data (96% of legend box); exported width 64.1 mm deviates -28% from target 89.0 mm |
| single_89mm_N | lollipop_mutation_plot | FAIL | 1 overlapping text pair(s); exported width 73.0 mm deviates -18% from target 89.0 mm |
| single_89mm_N | ma_plot | FAIL | 3 overlapping text pair(s); 1 clipped annotation(s) |
| single_89mm_N | dose_response_curve | FAIL | 1 overlapping text pair(s); exported width 65.1 mm deviates -27% from target 89.0 mm |
| single_89mm_N | upset_plot | FAIL | smallest text 3.85 pt at 89.0 mm (minimum 5.0 pt; role tick); exported width 127.1 mm deviates +43% from target 89.0 mm |
| single_89mm_N | spider_plot | FAIL | 1 overlapping text pair(s); exported width 65.5 mm deviates -26% from target 89.0 mm |
| single_89mm_N | sankey_plot | FAIL | smallest text 3.51 pt at 89.0 mm (minimum 5.0 pt; role tick); exported width 139.5 mm deviates +57% from target 89.0 mm |
| single_89mm_N | embedding_scatter | WARN | legend covers data (21% of legend box); exported width 64.5 mm deviates -28% from target 89.0 mm |
| single_89mm_N | hierarchical_clustering | WARN | legend covers data (100% of legend box) |
