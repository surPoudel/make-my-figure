# Tutorial validation report

Generated 2026-10-05 11:41 by `tutorial/automation/validate_tutorials.py`. Each row is one action script run against the real desktop application (offscreen). Checks are recorded by the driver as the script performs the tutorial's own steps.

| tutorial | status | checks | failed | captures | seconds | datasets | detail |
|---|---|---|---|---|---|---|---|
| `figure_builder` | **PASS** | 8 | 0 | 3 | 44.6 | group_comparison.csv, relationship_data.csv |  |
| `figure_package` | **PASS** | 9 | 0 | 7 | 28.7 | group_comparison.csv |  |
| `figure_preset` | **PASS** | 8 | 0 | 6 | 30.1 | group_comparison.csv, one_table_many_plots.csv |  |
| `getting_started` | **PASS** | 0 | 0 | 6 | 12.1 |  |  |
| `group_comparison_box` | **PASS** | 8 | 0 | 8 | 32.7 | group_comparison.csv |  |
| `heatmap_clustered` | **PASS** | 5 | 0 | 6 | 22.6 | feature_sample_matrix.csv |  |
| `kaplan_meier` | **PASS** | 6 | 0 | 7 | 25.9 | survival.csv |  |
| `mapping_ambiguous` | **PASS** | 7 | 0 | 11 | 34.9 | ambiguous_columns.csv |  |
| `master_capabilities` | **PASS** | 48 | 0 | 27 | 172.7 | ambiguous_columns.csv, showcase_group_comparison.csv, rnaseq_results.csv, rnaseq_results_renamed.csv, feature_sample_matrix.csv, survival.csv, relationship_data.csv |  |
| `observations_jitter` | **PASS** | 20 | 0 | 17 | 58.9 | showcase_group_comparison.csv |  |
| `publication_presets` | **PASS** | 13 | 0 | 9 | 39.5 | showcase_group_comparison.csv |  |
| `scatter_regression` | **PASS** | 6 | 0 | 8 | 30.5 | relationship_data.csv |  |
| `volcano_manual_mapping` | **PASS** | 8 | 0 | 10 | 34.9 | rnaseq_results.csv, rnaseq_results_renamed.csv |  |

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
- PASS: preset applied - Applied preset “Tutorial violin style”: 26 setting(s).
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
- PASS: export png - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/mapping_ambiguous/ambiguous_scatter.png
- PASS: export svg - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/mapping_ambiguous/ambiguous_scatter.svg

### `master_capabilities` - Master replay: from an ordinary table to a reproducible multi-panel figure (PASS)

- PASS: data loaded - ambiguous_columns.csv
- PASS: figure rendered
- PASS: figure rendered
- PASS: data loaded - showcase_group_comparison.csv
- PASS: figure rendered
- PASS: figure rendered
- PASS: figure rendered
- PASS: figure rendered
- PASS: figure rendered
- PASS: figure rendered
- PASS: figure rendered
- PASS: figure rendered
- PASS: figure rendered
- PASS: figure rendered
- PASS: statistics ran - 6 comparison row(s)
- PASS: stats table exported - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/master_capabilities/master_stats_table.csv
- PASS: method report exported - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/master_capabilities/master_methods.md
- PASS: experimental presets listed - 11 entries
- PASS: preset preview opened - Preview preset: Box + observations (outline)
- PASS: preset applied from preview - Applied preset “Box + observations (outline)” after preview: 12 setting(s).
- PASS: figure rendered
- PASS: figure rendered
- PASS: export pdf - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/master_capabilities/master_box.pdf
- PASS: export svg - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/master_capabilities/master_box.svg
- PASS: export png - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/master_capabilities/master_box.png
- PASS: export json - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/master_capabilities/master_box.plot_spec.json
- PASS: figure package saved - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/master_capabilities/master_box.mmfpackage
- PASS: returned to start screen
- PASS: package opened and rendered
- PASS: data loaded - rnaseq_results.csv
- PASS: data loaded - rnaseq_results_renamed.csv
- PASS: figure rendered
- PASS: export pdf - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/master_capabilities/master_volcano.pdf
- PASS: data loaded - feature_sample_matrix.csv
- PASS: figure rendered
- PASS: figure rendered
- PASS: data loaded - survival.csv
- PASS: figure rendered
- PASS: statistics ran - 1 comparison row(s)
- PASS: panel saved - 1 panel(s)
- PASS: data loaded - showcase_group_comparison.csv
- PASS: statistics ran - 6 comparison row(s)
- PASS: panel saved - 2 panel(s)
- PASS: data loaded - relationship_data.csv
- PASS: figure rendered
- PASS: panel saved - 3 panel(s)
- PASS: composite figure saved - master_composite.png, master_composite.pdf, master_composite.svg
- PASS: composite package saved - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/master_capabilities/master_composite.mmfpackage

### `observations_jitter` - Showing individual observations and controlling jitter (PASS)

- PASS: data loaded - showcase_group_comparison.csv
- PASS: figure rendered
- PASS: figure rendered
- PASS: figure rendered
- PASS: figure rendered
- PASS: figure rendered
- PASS: figure rendered
- PASS: figure rendered
- PASS: figure rendered
- PASS: figure rendered
- PASS: figure rendered
- PASS: statistics ran - 6 comparison row(s)
- PASS: experimental presets listed - 11 entries
- PASS: preset preview opened - Preview preset: Box + observations (outline)
- PASS: preset applied from preview - Applied preset “Box + observations (outline)” after preview: 12 setting(s).
- PASS: figure rendered
- PASS: figure rendered
- PASS: export pdf - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/observations_jitter/observations.pdf
- PASS: export svg - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/observations_jitter/observations.svg
- PASS: export png - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/observations_jitter/observations.png

### `publication_presets` - Publication presets: preview, apply, keep adjusting (PASS)

- PASS: data loaded - showcase_group_comparison.csv
- PASS: statistics ran - 6 comparison row(s)
- PASS: experimental presets listed - 11 entries
- PASS: preset preview opened - Preview preset: Violin + observations
- PASS: preset preview opened - Preview preset: Violin + observations
- PASS: preset applied from preview - Applied preset “Violin + observations” after preview: 10 setting(s).
- PASS: figure rendered
- PASS: preset preview opened - Preview preset: Single column 89 mm (N)
- PASS: preset applied from preview - Applied preset “Single column 89 mm (N)” after preview: 38 setting(s).
- PASS: figure rendered
- PASS: figure rendered
- PASS: export pdf - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/publication_presets/preset_final.pdf
- PASS: export png - /mnt/c/Users/spoudel1/OneDrive - St. Jude Children's Research Hospital/make_my_plot_tutorial/tutorial/automation/_outputs/publication_presets/preset_final.png

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
