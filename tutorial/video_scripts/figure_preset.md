# Presets: your own, and the experimental publication presets

TITLE: Figure presets - preview on your data, apply, keep adjusting
TARGET LENGTH: 3:30
DATASETS: tutorial/datasets/showcase_group_comparison.csv (publication presets); tutorial/datasets/group_comparison.csv and one_table_many_plots.csv (a user preset on a second dataset)
START STATE: start screen; empty preset library.
ACTION SCRIPTS: `run_tutorial.py publication_presets --onscreen --pause 1.5`, then `run_tutorial.py figure_preset --onscreen --pause 1.5`

| time | screen | action | narration |
|---|---|---|---|
| 0:00-0:10 | start screen | - | "Two kinds of preset: the ones you save, and an experimental library derived from published figures." |
| 0:10-0:35 | workspace | open `showcase_group_comparison.csv`, box / violin, statistics on | "A box plot with every observation and three comparisons." |
| 0:35-0:55 | Figure preset panel | tick **Show experimental presets** | "Tick Show experimental presets. Ten presets apply to this plot type; each name says what it does or which evidence set its width and typography came from. They require a preview." |
| 0:55-1:35 | preview dialog | select **Violin + observations**, **Preview & apply...** | "Before and after on your own data. The list says exactly what would change - kind, markers, edges. The green line confirms: no data, column role, test or threshold changes. Cancel leaves everything untouched." |
| 1:35-1:55 | figure | **Preview & apply...** again, **Apply** | "Apply. Violins now; the statistics table is unchanged." |
| 1:55-2:20 | preview dialog, figure | **Single column 89 mm (N)**, preview, **Apply** | "A width preset on top: figure width, typography and line weights measured in that evidence set. Thirty-eight settings, none of them data." |
| 2:20-2:45 | 3. Options | **Point size** 30, **Point fill** open, **Point edge** same | "Presets are a starting configuration, not a locked template. Keep adjusting." |
| 2:45-3:15 | Save Figure Preset dialog, second dataset | **Save preset...** (Figure style only); open `one_table_many_plots.csv`, same plot type, **Apply** | "Save your own preset - style only or full configuration; neither contains data. Apply it to an unrelated table: the look transfers, the values are the new table's own." |
| 3:15-3:30 | figure | - | "Figure Preset is not PlotSpec: a preset describes a look; a PlotSpec describes one figure." |

FINAL STATE: second dataset drawn in the saved style.
EXPORT: `preset_final.pdf`, `preset_final.png`, `preset_applied.png`.
KEY MESSAGE: Presets are previewed on your data, change presentation only, and stay editable.
