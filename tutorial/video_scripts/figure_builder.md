# Figure Builder: a two-panel composite

TITLE: Figure Builder - assembling a multi-panel figure
TARGET LENGTH: 3:00
DATASETS: tutorial/datasets/group_comparison.csv, tutorial/datasets/relationship_data.csv
START STATE: start screen, no data, no saved panels.
ACTION SCRIPT: `python tutorial/automation/run_tutorial.py figure_builder --onscreen --pause 1.5`

| time | screen | action | narration |
|---|---|---|---|
| 0:00-0:10 | start screen | - | "Two plots from two tables become one figure with panel letters." |
| 0:10-0:40 | workspace, 6. Multi-panel figure | box / violin from `group_comparison.csv`, title, **Save current plot as panel** | "Make the first plot, give it a title, and save it as a panel. The panel keeps its own copy of the data." |
| 0:40-1:10 | workspace | scatter from `relationship_data.csv`, title, **Save current plot as panel** | "Second table, second plot, second panel. Two panels saved." |
| 1:10-2:00 | Figure Builder | **Open Figure Builder...** | "The builder: figure name, columns and rows, width in millimetres, gutters, panel letters, export DPI, a layout preset library. The panel list sets the order A, B, C. Selected panel size scales a panel without distorting it. Fonts apply to all panels. A draft legend is generated - a starting point to rewrite." |
| 2:00-2:30 | Figure Builder | **Save figure...** | "Save figure writes PNG, PDF and SVG of the composite." |
| 2:30-3:00 | Figure Builder | **Save Figure Package...**, **Close** | "Save Figure Package keeps every panel with its specification and its table in one file; reopening it restores the composite in the builder." |

FINAL STATE: builder preview with panels A and B.
EXPORT: `composite.png`, `composite.pdf`, `composite.svg`, `composite.mmfpackage`.
KEY MESSAGE: Panels carry their own data; the builder arranges, letters and exports.
