# Figure presets: style travels, data stay

TITLE: Figure presets - reuse a look on new data
TARGET LENGTH: 3:00
DATASETS: tutorial/datasets/group_comparison.csv, tutorial/datasets/one_table_many_plots.csv
START STATE: start screen; empty preset library.
ACTION SCRIPT: `python tutorial/automation/run_tutorial.py figure_preset --onscreen --pause 1.5`

| time | screen | action | narration |
|---|---|---|---|
| 0:00-0:10 | start screen | - | "A Figure Preset stores how a figure looks, so the next figure can look the same." |
| 0:10-0:45 | workspace | open `group_comparison.csv`, box / violin, Kind violin, Point size 14, y label, Figure width single | "Make a figure and refine it: violins, larger points, a y label, single-column width." |
| 0:45-1:20 | Figure preset panel, Save Figure Preset dialog | **Save preset...**, name, Figure style only, **Save** | "Save preset. Two kinds: Figure style only - fonts, colours, layout, legend, export - or Full figure configuration, which also stores column roles, thresholds and statistics settings. Neither contains your data." |
| 1:20-1:50 | start screen, workspace | open `one_table_many_plots.csv`, box / violin, x = treatment, y = response | "An unrelated table, same plot type, default look." |
| 1:50-2:25 | Figure preset panel | select the preset, **Apply** | "Apply. Nine settings transfer: the violins, the points, the width, the label. The groups and their values are the new table's own." |
| 2:25-3:00 | preview | - | "A preset is not a PlotSpec. A PlotSpec describes one figure and needs its data; a preset describes a look and works on any table of that plot type." |

FINAL STATE: violin plot of the second dataset in the saved style.
EXPORT: `preset_applied.png`; preset file `Tutorial_violin_style.mmfpreset.json`.
KEY MESSAGE: Figure Preset is not PlotSpec: appearance transfers, values do not.
