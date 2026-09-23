# Tutorial validation report

Generated 2026-09-22 20:15 by `tutorial/automation/validate_tutorials.py`. Each row is one action script run against the real desktop application (offscreen). Checks are recorded by the driver as the script performs the tutorial's own steps.

| tutorial | status | checks | failed | captures | seconds | datasets | detail |
|---|---|---|---|---|---|---|---|
| `figure_builder` | **PASS** | 8 | 0 | 3 | 46.2 | group_comparison.csv, relationship_data.csv |  |
| `figure_package` | **PASS** | 9 | 0 | 7 | 41.6 | group_comparison.csv |  |
| `figure_preset` | **PASS** | 8 | 0 | 6 | 34.6 | group_comparison.csv, one_table_many_plots.csv |  |
| `getting_started` | **PASS** | 0 | 0 | 6 | 21.6 |  |  |
| `group_comparison_box` | **PASS** | 8 | 0 | 8 | 36.3 | group_comparison.csv |  |
| `heatmap_clustered` | **PASS** | 5 | 0 | 6 | 30.0 | feature_sample_matrix.csv |  |
| `kaplan_meier` | **PASS** | 6 | 0 | 7 | 33.6 | survival.csv |  |
| `mapping_ambiguous` | **PASS** | 7 | 0 | 11 | 45.0 | ambiguous_columns.csv |  |
| `scatter_regression` | **PASS** | 6 | 0 | 8 | 36.6 | relationship_data.csv |  |
| `volcano_manual_mapping` | **PASS** | 8 | 0 | 10 | 41.3 | rnaseq_results.csv, rnaseq_results_renamed.csv |  |

## Checks per tutorial

### `figure_builder` - Figure Builder: a two-panel composite (PASS)

- PASS: data loaded - group_comparison.csv
- PASS: figure rendered
- PASS: panel saved - 1 panel(s)
- PASS: data loaded - relationship_data.csv
- PASS: figure rendered
- PASS: panel saved - 2 panel(s)
- PASS: composite figure saved - composite.png, composite.pdf, composite.svg
- PASS: composite package saved - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/figure_builder/composite.mmfpackage

### `figure_package` - Reproducibility: PlotSpec and Figure Package (PASS)

- PASS: data loaded - group_comparison.csv
- PASS: statistics ran - 3 comparison row(s)
- PASS: figure rendered
- PASS: export json - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/figure_package/box.plot_spec.json
- PASS: figure package saved - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/figure_package/box.mmfpackage
- PASS: returned to start screen
- PASS: package opened and rendered
- PASS: returned to start screen
- PASS: plotspec opened and rendered

### `figure_preset` - Figure presets: style travels, data stays (PASS)

- PASS: data loaded - group_comparison.csv
- PASS: figure rendered
- PASS: preset saved - Tutorial_violin_style.mmfpreset.json
- PASS: data loaded - one_table_many_plots.csv
- PASS: figure rendered
- PASS: preset applied - Applied preset “Tutorial violin style”: 9 setting(s).
- PASS: figure rendered
- PASS: export png - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/figure_preset/preset_applied.png

### `getting_started` - Getting started with the desktop application (PASS)


### `group_comparison_box` - Box / violin plot with points and statistics (PASS)

- PASS: data loaded - group_comparison.csv
- PASS: figure rendered
- PASS: figure rendered
- PASS: statistics ran - 3 comparison row(s)
- PASS: export png - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/group_comparison_box/box_stats.png
- PASS: export svg - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/group_comparison_box/box_stats.svg
- PASS: stats table exported - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/group_comparison_box/box_stats_table.csv
- PASS: method report exported - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/group_comparison_box/box_methods.md

### `heatmap_clustered` - Clustered heatmap from a feature-by-sample matrix (PASS)

- PASS: data loaded - feature_sample_matrix.csv
- PASS: figure rendered
- PASS: figure rendered
- PASS: export png - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/heatmap_clustered/heatmap.png
- PASS: export pdf - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/heatmap_clustered/heatmap.pdf

### `kaplan_meier` - Kaplan-Meier survival curve (PASS)

- PASS: data loaded - survival.csv
- PASS: figure rendered
- PASS: figure rendered
- PASS: statistics ran - 1 comparison row(s)
- PASS: export pdf - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/kaplan_meier/km.pdf
- PASS: export png - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/kaplan_meier/km.png

### `mapping_ambiguous` - Column mapping with ambiguous column names (PASS)

- PASS: data loaded - ambiguous_columns.csv
- PASS: figure rendered
- PASS: figure rendered
- PASS: figure rendered
- PASS: figure rendered
- PASS: export png - C:\Users\spoudel1\OneDrive - St. Jude Children's Research Hospital\make_my_plot_tutorial\tutorial\automation\_outputs\mapping_ambiguous\ambiguous_scatter.png
- PASS: export svg - C:\Users\spoudel1\OneDrive - St. Jude Children's Research Hospital\make_my_plot_tutorial\tutorial\automation\_outputs\mapping_ambiguous\ambiguous_scatter.svg

### `scatter_regression` - Scatter plot with regression line (PASS)

- PASS: data loaded - relationship_data.csv
- PASS: figure rendered
- PASS: figure rendered
- PASS: statistics ran - 2 comparison row(s)
- PASS: export pdf - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/scatter_regression/scatter.pdf
- PASS: export png - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/scatter_regression/scatter.png

### `volcano_manual_mapping` - Volcano plot: automatic detection and manual role mapping (PASS)

- PASS: data loaded - rnaseq_results.csv
- PASS: figure rendered
- PASS: data loaded - rnaseq_results_renamed.csv
- PASS: figure rendered
- PASS: figure rendered
- PASS: export png - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/volcano_manual_mapping/volcano.png
- PASS: export pdf - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/volcano_manual_mapping/volcano.pdf
- PASS: export json - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/volcano_manual_mapping/volcano.plot_spec.json
