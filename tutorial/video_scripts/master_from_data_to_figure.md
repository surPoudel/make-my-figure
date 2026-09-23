# MakeMyFigure Desktop: From Data to Publication Figure

TITLE: Make My Figure desktop - from data to publication figure
TARGET LENGTH: 10:00 (8-12 min)
DATASETS: tutorial/datasets/ambiguous_columns.csv, tutorial/datasets/group_comparison.csv, tutorial/datasets/relationship_data.csv
START STATE: application open on the start screen; datasets in a neutral folder (`~/tutorial_data`); no presets saved.
ACTION SCRIPT: the master run chains four scripts with a pause: `run_tutorial.py mapping_ambiguous group_comparison_box figure_preset figure_package figure_builder --onscreen --pause 1.5` (record in one take or in five and cut).
RECORDING: tutorial/videos/RECORDING.md

| time | screen | action | narration |
|---|---|---|---|
| 0:00-0:20 | start screen | - | "Make My Figure turns an ordinary data table into a publication-style figure, on your computer, without code. This video follows one path from opening a file to a two-panel figure. The steps are the same for every plot type." |
| 0:20-0:45 | start screen | click **Open data file**, choose `ambiguous_columns.csv` | "Start with a table whose column names mean nothing to anyone else: col_A, measurement_2, condition_code. The application opens CSV, TSV and Excel files." |
| 0:45-1:20 | workspace, Data preview | point at the detected-types line and the Recommended figures cards | "Under the table the application lists what it detected: which columns are text, which are numeric. On the left it recommends figures for this shape of table. These are suggestions. Nothing has been drawn yet." |
| 1:20-2:00 | plot type list, 2. Map columns | choose **Box / violin plot with points** | "Choose a plot type. The application proposes roles: condition_code as x, measurement_2 as y, and draws the figure. Every row under Map columns is a drop-down of your own columns." |
| 2:00-2:30 | 2. Map columns, preview | change **y** to `score_final` | "If the proposal is not what you want, change it. The figure follows. The row label is the role; the drop-down is your column." |
| 2:30-3:15 | plot type list, mapping | choose **Scatter plot**; set x, y, color, label | "The same table can answer a different question. A scatter plot of the two readouts, coloured by condition, labelled by the text column. The data do not belong to one plot." |
| 3:15-3:45 | Home, Open data file | **Home / Upload New Data**, open `group_comparison.csv`, choose box / violin | "Now a real comparison: three groups of unequal size." |
| 3:45-4:15 | 3. Options, 4. Labels & size | Kind violin then box, point size, y label | "Options are the plot's own controls; labels and size set the axis text and the column width." |
| 4:15-5:30 | 6. Statistics | tick the title box, Enable statistics, Welch's t-test, Compare all groups, Holm-Bonferroni, P-value only, **Run statistics** | "The statistics panel is switched on with the box in its title. The panel suggests a test from the data; the choice is yours. Welch's t-test for all pairs, Holm correction, exact P values. Run. Brackets appear on the figure, the table lists every comparison with effect size and n, and the method sentence is ready to paste." |
| 5:30-6:00 | Publication QC, preview | click **Publication QC** | "Publication QC checks readability: text size, overlaps, legend placement." |
| 6:00-6:45 | Figure preset | **Save preset...**, name, Figure style only, Save | "Save the look as a Figure Preset. A style preset carries fonts, colours, layout and legend - never your data." |
| 6:45-7:15 | 5. Export | **Export PDF** | "Export as PDF, SVG or PNG. The file is the preview as you see it." |
| 7:15-8:00 | 5. Export, confirmation | **Save Figure Package (.mmfpackage)**, read the confirmation, Save | "A Figure Package is one file with the specification, a frozen copy of the table, the statistics results and previews. It is the file to keep with a manuscript." |
| 8:00-8:40 | Home, start screen, Open Figure Package | Home, Clear and continue; **Open Figure Package**, choose the file | "Close everything, reopen the package: integrity verified, the figure and its statistics return without the original CSV." |
| 8:40-9:30 | 6. Multi-panel figure, Figure Builder | **Save current plot as panel**; open `relationship_data.csv`, scatter, save panel; **Open Figure Builder...** | "Save plots as panels and open the Figure Builder: panel letters, a common width, common fonts, a draft legend. Save figure writes the composite; Save Figure Package keeps every panel with its data." |
| 9:30-10:00 | Figure Builder preview | - | "That is the whole path: open any table, decide what each column means, choose the figure, add the test, keep the look, keep the evidence. The application suggests; you decide." |

FINAL STATE: Figure Builder showing panels A and B.
EXPORT: `box_stats.pdf`, `box.mmfpackage`, `composite.png/.pdf/.svg`, `composite.mmfpackage`.
KEY MESSAGE: Recommendations and proposed column roles are conveniences; the researcher controls the mapping, the test and the record.
