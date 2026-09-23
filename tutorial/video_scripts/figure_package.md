# Reproducibility: PlotSpec and Figure Package

TITLE: Reproducibility - PlotSpec versus Figure Package
TARGET LENGTH: 3:30
DATASET: tutorial/datasets/group_comparison.csv
START STATE: start screen, no data.
ACTION SCRIPT: `python tutorial/automation/run_tutorial.py figure_package --onscreen --pause 1.5`

| time | screen | action | narration |
|---|---|---|---|
| 0:00-0:10 | start screen | - | "Two files can carry a figure: the PlotSpec, which is the specification alone, and the Figure Package, which adds the data." |
| 0:10-0:40 | workspace | open `group_comparison.csv`, box / violin, run Welch's t-test all pairs | "A box plot with statistics - something worth keeping exactly." |
| 0:40-1:00 | 5. Export | **Export PlotSpec JSON (specification only)** | "Export PlotSpec JSON. It records plot type, roles, options, statistics settings and a fingerprint of the table. It does not contain the table." |
| 1:00-1:40 | 5. Export, confirmation | **Save Figure Package (.mmfpackage)**, read, **Save** | "Save Figure Package. The confirmation lists what goes in: the source table with the original file, the PlotSpec, the StatsSpec with results, previews. It also reminds you that the package contains your data." |
| 1:40-2:10 | Home question, start screen | **Home / Upload New Data**, *Clear and continue* | "Clear the session. Imagine the package was emailed to a colleague." |
| 2:10-2:45 | start screen, workspace | **Open Figure Package**, choose the copied file | "Open Figure Package. The status bar reports the integrity check and the date the data were frozen. The table, the mapping, the brackets - all back, without the CSV." |
| 2:45-3:20 | File menu, dialogs | *Open PlotSpec...*, choose the JSON, then choose the data file | "Opening a PlotSpec instead asks for the data file, because the specification cannot draw itself. If the table changed since, the application warns you." |
| 3:20-3:30 | workspace | - | "PlotSpec for the recipe, Figure Package for recipe plus ingredients." |

FINAL STATE: figure rebuilt from PlotSpec plus data.
EXPORT: `box.plot_spec.json`, `box.mmfpackage` (and its copy).
KEY MESSAGE: A PlotSpec needs its data; a Figure Package is self-contained and verified.
