# Scatter plot with regression line

TITLE: Scatter plot with regression - relationships between two readouts
TARGET LENGTH: 2:30
DATASET: tutorial/datasets/relationship_data.csv
START STATE: start screen, no data.
ACTION SCRIPT: `python tutorial/automation/run_tutorial.py scatter_regression --onscreen --pause 1.5`

| time | screen | action | narration |
|---|---|---|---|
| 0:00-0:08 | start screen | - | "A scatter plot with a regression line, from a table of sixty samples." |
| 0:08-0:25 | Data preview | **Open data file**, `relationship_data.csv` | "Six columns: an identifier, a cell line, a dose, viability and two expression readouts. The application detects a dose-response shape; we want the two expression columns instead." |
| 0:25-0:55 | 2. Map columns | **Scatter plot**; x = expression_a, y = expression_b, color = cell_line | "The proposal uses the first two numeric columns. Set x and y to the expression readouts and colour by cell line. One regression line per line, with slope, R-squared and P in the box." |
| 0:55-1:25 | 3. Options, 4. Labels & size | show_r, show_n on; Stats box location upper left; axis labels | "Options add Pearson r and n to the box and move it. Axis labels are set under Labels and size." |
| 1:25-2:05 | 6. Statistics | title box, Enable statistics, Spearman correlation, **Run statistics** | "For a formal test, switch the statistics panel on and choose Spearman correlation. The test runs per colour group; the table shows rho, P and n for each line, and the method sentence is ready to copy." |
| 2:05-2:30 | 5. Export | **Export PDF**, **Export PNG** | "Export as PDF for the journal, PNG for a slide." |

FINAL STATE: scatter with two regression lines and stats box top left.
EXPORT: `scatter.pdf`, `scatter.png`.
KEY MESSAGE: With a colour role, regression and correlation are computed per group.
