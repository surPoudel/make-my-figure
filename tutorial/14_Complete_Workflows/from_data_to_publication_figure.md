# From data to publication figure - the complete path

This is the written companion of the master video (`video_scripts/master_from_data_to_figure.md`).
It strings together steps that the topic tutorials explain in detail; each step names the
tutorial to read for more. Every step was executed against the application (validation
records `mapping_ambiguous`, `group_comparison_box`, `figure_preset`, `figure_package`,
`figure_builder`).

1. **Launch** and look at the start screen - [getting started](../00_Getting_Started/getting_started.md).
2. **Open an arbitrary table**: `datasets/ambiguous_columns.csv`. Read the detected column
   types under the Data preview and the recommendation cards - [column mapping](../01_Data_and_Column_Mapping/your_table_does_not_need_perfect_column_names.md).
3. **Choose a plot type** (Box / violin plot with points). Accept or change the proposed roles
   under **2. Map columns**; make a second plot (Scatter plot) from the same table by re-mapping.
4. **Open `group_comparison.csv`**, same plot type; refine under **3. Options** and
   **4. Labels & size** - [styling](../09_Styling_and_Annotations/styling.md).
5. **Run statistics**: tick the **6. Statistics** title box and *Enable statistics*; Welch's
   t-test, all pairs, Holm-Bonferroni, P-value only; **Run statistics**; export the table and the
   method report - [statistics](../06_Statistics/statistics.md).
6. **Check readability** with **Publication QC**.
7. **Save a Figure Preset** (style only) - [presets](../10_Figure_Presets/figure_presets.md).
8. **Export** PDF (and PNG for slides) - [export](../13_Export/export.md).
9. **Save a Figure Package**; go **Home**, reopen the package from the start screen and
   confirm the figure and its statistics return - [reproducibility](../11_Reproducibility/plotspec_and_figure_package.md).
10. **Build a composite**: save the box plot as a panel, open `relationship_data.csv`, make a
    scatter, save it as a panel, **Open Figure Builder...**, save the figure and its package -
    [Figure Builder](../12_Figure_Builder/figure_builder.md).

What the path demonstrates: the application proposes (figures, roles, tests) and records
(PlotSpec, StatsSpec, Figure Package); the researcher decides (mapping, test, look) and keeps
the evidence.

A second complete workflow, [from expression matrix to visualization](matrix_workflow.md), is
planned after the pilot review.
