# Box / violin plot with points and statistics

TITLE: Comparing groups - box or violin with points and a test
TARGET LENGTH: 3:30
DATASET: tutorial/datasets/group_comparison.csv
START STATE: start screen, no data.
ACTION SCRIPT: `python tutorial/automation/run_tutorial.py group_comparison_box --onscreen --pause 1.5`

| time | screen | action | narration |
|---|---|---|---|
| 0:00-0:08 | start screen | - | "Three groups of unequal size, one readout: the most common comparison figure." |
| 0:08-0:30 | Data preview, Recommended figures | **Open data file**, `group_comparison.csv` | "Thirty rows, a group column, a response. The first recommendation is the box / violin plot with points." |
| 0:30-0:50 | 2. Map columns | **Box / violin plot with points** | "The proposal is group on x, response on y. Every observation is a point over its box." |
| 0:50-1:20 | 3. Options | Kind violin, Point size 12; back to box | "Kind switches between box and violin. Point size and overlay points are here too." |
| 1:20-2:30 | 6. Statistics | title box, Enable statistics, Welch's t-test, Compare all groups (pairwise), Group column group, Holm-Bonferroni, P-value only, **Run statistics** | "The statistics panel has two switches: the box in its title and Enable statistics. It suggests a test from the number of groups; the choice remains yours. Welch's t-test for every pair, Holm correction, exact P values on the figure. Run. Brackets appear; the table lists each comparison with the adjusted P, Hedges' g and n." |
| 2:30-3:00 | statistics table, method sentence | **Export stats table**, **Export method report** | "Export the table and the method report. The sentence under the table is the one for your methods section; it also says that you are responsible for choosing an appropriate test." |
| 3:00-3:30 | 5. Export | **Export PNG**, **Export SVG** | "Export the figure. The brackets are part of it." |

FINAL STATE: box plot with three P-value brackets.
EXPORT: `box_stats.png`, `box_stats.svg`, `box_stats_table.csv`, `box_methods.md`.
KEY MESSAGE: The application runs the test you choose and writes it up; it does not choose for you.
