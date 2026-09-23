# Your table does not need perfect column names

TITLE: Column mapping - your table does not need perfect column names
TARGET LENGTH: 3:30
DATASET: tutorial/datasets/ambiguous_columns.csv
START STATE: start screen, no data.
ACTION SCRIPT: `python tutorial/automation/run_tutorial.py mapping_ambiguous --onscreen --pause 1.5`

| time | screen | action | narration |
|---|---|---|---|
| 0:00-0:10 | start screen | - | "Most tables were not made for a plotting program. This one has columns called col_A, measurement_2, condition_code and thing." |
| 0:10-0:35 | Data preview | **Open data file**, `ambiguous_columns.csv` | "The application shows the table and what it detected: two numeric columns, four text columns. id_value is treated as text because it looks like an identifier." |
| 0:35-0:55 | Recommended figures | scroll the cards | "It recommends figures for this shape - box plot, ridge, bar - with a match score. Suggestions, not decisions." |
| 0:55-1:25 | plot type, 2. Map columns | choose **Box / violin plot with points** | "Choose the box plot. The application proposes condition_code as x and measurement_2 as y and draws it." |
| 1:25-1:50 | 2. Map columns | y = score_final | "Suppose score_final is the readout you care about. Change y. The figure follows; nothing else changes." |
| 1:50-2:40 | plot type, 2. Map columns | **Scatter plot**; x = measurement_2, y = score_final, color = condition_code, label = thing | "Same table, different question: how do the two readouts relate? A scatter plot with one regression line per condition, each point labelled." |
| 2:40-3:05 | plot type, 2. Map columns | **Bar plot with error bars**; x = condition_code, y = measurement_2 | "And a bar plot with standard error, from the same file." |
| 3:05-3:30 | 5. Export | back to the scatter; **Export PNG**, **Export SVG** | "Export. Three figures from one table, with the columns you chose. The application proposes; you decide." |

FINAL STATE: scatter plot with regression lines.
EXPORT: `ambiguous_scatter.png`, `ambiguous_scatter.svg`.
KEY MESSAGE: The row label is the role, the drop-down is your column; the data do not belong to one plot.
