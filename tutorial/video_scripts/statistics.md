# Statistics on the figure

TITLE: Statistics - choose the test, read the result, export the method
TARGET LENGTH: 3:30
DATASET: tutorial/datasets/group_comparison.csv
START STATE: box / violin plot of `group_comparison.csv` on screen (end state of the group comparison video).
ACTION SCRIPT: `python tutorial/automation/run_tutorial.py group_comparison_box --onscreen --pause 1.5` (statistics segment)

| time | screen | action | narration |
|---|---|---|---|
| 0:00-0:15 | 6. Statistics (grey) | - | "The statistics panel is off until the box in its title is ticked; inside, Enable statistics is the second switch." |
| 0:15-0:45 | Test list | open the Test list | "Nineteen tests: t-tests, Mann-Whitney, paired tests, ANOVA, Kruskal-Wallis, Dunn, chi-square, Fisher, log-rank, Cox, correlations, regression. Auto-suggest picks from the data; the suggestion is printed under the buttons." |
| 0:45-1:15 | Comparison, Group column, Control group | choose Compare all groups (pairwise) | "Comparison family: all pairs, against a control, within each x category, selected pairs, or the omnibus test only. Group column is the column that defines the groups." |
| 1:15-1:35 | Correction | Holm-Bonferroni | "Multiple-testing correction: Benjamini-Hochberg, Bonferroni, Holm, or none." |
| 1:35-2:00 | Annotation shows / placement | P-value only, bracket | "What appears on the figure: stars, P, adjusted P, statistic, effect size, a custom template; and where." |
| 2:00-2:40 | Run statistics, table | **Run statistics** | "Run. Brackets on the figure; a table with test, P, adjusted P, effect size and n per comparison; the method sentence." |
| 2:40-3:10 | Export buttons | **Export stats table**, **Export method report**, **Copy method sentence** | "Export the table as CSV, the method report as Markdown or JSON, or copy the sentence." |
| 3:10-3:30 | figure | - | "The settings and results are a StatsSpec, stored with the PlotSpec and inside a Figure Package. The application does not decide whether a test fits your design - the researcher does." |

FINAL STATE: figure with brackets, table filled.
EXPORT: `box_stats_table.csv`, `box_methods.md`.
KEY MESSAGE: MakeMyFigure runs and documents the test you choose; choosing it is your job.
