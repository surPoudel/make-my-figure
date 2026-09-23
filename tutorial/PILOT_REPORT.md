# Pilot report - Make My Figure desktop tutorial

Prepared 2026-09-22 on branch `feature/desktop-tutorial` (worktree `make_my_plot_tutorial`),
from `main` at 84458dd. Nothing merged, tagged, released, published or pushed.

## CURRENT APPLICATION

| item | value (read from the code the application imports) |
|---|---|
| version | 1.1.1 (`make_my_figure_core/version.py`) |
| registered plots | 39 (`registry.available_plot_types()`) |
| desktop entry point | `python -m apps.desktop_app.main` (`apps/desktop_app/main.py`, `MainWindow`; controller in `controller.py`) |
| statistics | 19 tests in `statistics/test_registry.py` |
| example datasets | 39 bundled synthetic examples (`examples/by_plot_type/`, manifest seed 42) |
| architecture facts used | control column of group boxes 1-6, Recommended figures panel, Data preview / Messages tabs, checkable Statistics panel, Figure preset panel, Figure Builder dialog, Define groups dialog, Matrix workflow wizard |

## TUTORIAL STRUCTURE

Directories created under `tutorial/`: `00_Getting_Started`, `01_Data_and_Column_Mapping`,
`06_Statistics`, `09_Styling_and_Annotations`, `10_Figure_Presets`, `11_Reproducibility`,
`12_Figure_Builder`, `13_Export`, `14_Complete_Workflows`, `plots`, `datasets`, `screenshots`,
`videos`, `video_scripts`, `automation`, `audit`, `slides`, `html` (generated). The section
folders `02_Basic_Plots`, `03_Group_Comparisons`, `04_Relationships_and_Regression`,
`05_Matrix_and_Omics`, `07_Survival_and_Effect_Plots`, `08_Advanced_Plots` exist as families in
the inventory and gallery; their per-plot pages go into `plots/` after review.

Datasets (`datasets/make_tutorial_datasets.py`, seed 20260922, all marked simulated):
general_long_table, group_comparison, relationship_data, time_course, rnaseq_results,
rnaseq_results_renamed, feature_sample_matrix, sample_metadata, survival, mutation_matrix,
network, effect_estimates, paired_data, categorical_data, **ambiguous_columns**,
**one_table_many_plots** (16 files, `datasets_manifest.json`).

## COLUMN-MAPPING TUTORIAL

`01_Data_and_Column_Mapping/your_table_does_not_need_perfect_column_names.md`, validated by
`mapping_ambiguous`:

* standard mapping - the application's proposal for a box plot (`x = condition_code`,
  `y = measurement_2`) and for a scatter (first two numeric columns), quoted from the live run;
* ambiguous mapping - `ambiguous_columns.csv` with `col_A`, `measurement_2`, `condition_code`,
  `thing`, `score_final`, `id_value`; the detected-types line and the recommendation cards as
  shown;
* manual correction - `y` changed to `score_final`; scatter roles `x`, `y`, `color`, `label`
  assigned by hand; volcano tutorial shows the (none) / missing-roles state and the fix;
* one-table-many-plots - box, scatter with per-group regression and bar with SEM from the same
  file; `one_table_many_plots.csv` also used in the preset tutorial.

## PILOT PLOTS

| tutorial | written | screenshots | video script | validation |
|---|---|---|---|---|
| Scatter / regression (`plots/scatterplot_with_regression.md`) | yes | 8 | yes | PASS |
| Box / violin with statistics (`plots/boxplot_or_violin_with_points.md`) | yes | 8 | yes | PASS |
| Volcano with manual mapping (`plots/volcano_plot.md`) | yes | 10 | yes | PASS |
| Clustered heatmap (`plots/heatmap_clustered_matrix.md`) | yes | 6 | yes | PASS |
| Kaplan-Meier (`plots/kaplan_meier_survival_curve.md`) | yes | 7 | yes | PASS |
| Ambiguous columns (mapping master) | yes | 11 | yes | PASS |
| Figure Preset (`10_Figure_Presets/figure_presets.md`) | yes | 6 | yes | PASS |
| Figure Package (`11_Reproducibility/plotspec_and_figure_package.md`) | yes | 7 | yes | PASS |
| Figure Builder (`12_Figure_Builder/figure_builder.md`) | yes | 3 | yes | PASS |
| Getting started | yes | 6 | (part of master) | PASS |

Also written: statistics, styling, export, reshaping / derived columns, complete workflow,
master video script, statistics video script, matrix-workflow outline. Report:
`audit/validation_report.md`; records with the facts quoted by the tutorials:
`audit/validation/*.json`.

Application findings recorded during validation (for the author): the group titles
"1. Plot type & style" and "4. Labels & size" display with the ampersand consumed as a
mnemonic; the statistics panel needs two switches (title box and *Enable statistics*); the
scatter statistics table labels both per-group Spearman rows with the x column name rather than
the group name.

## VIDEO

* capture approach - recorder separate from automation; `videos/RECORDING.md`; wrapper
  `automation/record_screen.py` (ffmpeg gdigrab / avfoundation / x11grab, cursor drawn);
  `imageio-ffmpeg` gives a bundled ffmpeg where none is installed;
* automation approach - `run_tutorial.py <id> --onscreen --pause 1.5` performs the tutorial in a
  visible window of the real application; the same script produces the screenshots offscreen;
* Windows support - demonstrated: the action script ran the real window on the Windows desktop
  through a Windows Python with PySide6 (`_onscreen_test/`), PASS;
* macOS support - same script; QuickTime or ffmpeg avfoundation for capture (not yet exercised);
* Linux support - offscreen screenshots demonstrated here (system libraries unpacked without
  root); on-screen needs a display (x11grab) or the desktop's Wayland recorder;
* limitations - no video has been recorded yet; narration is scripted, not voiced; pointer
  highlighting depends on the recorder; the Fusion widget style of the Linux offscreen captures
  differs slightly from the native Windows / macOS look (Windows-native captures can be produced
  with the same scripts, as demonstrated).

## GALLERY

`PLOT_GALLERY.md` - 39 entries, 39 thumbnails, each a real render of the bundled example with
the application's renderer; tutorial links for the five written plot pages; video placeholders
from `videos/video_links.json`.

## AUTOMATION

Can be automated (done): opening files and examples, choosing plot types, setting every row of
2. Map columns (including Value columns lists and multi-column roles), options, labels and size,
the statistics panel (all combos, run, exports), presets (save with the real dialog, apply),
exports, figure packages (save with the real confirmation, reopen), PlotSpec export / open,
Home, panels and the Figure Builder (open, inspect, save figure and package), widget and dialog
captures, PASS / FAIL checks, fact recording.

Should remain manual: video recording and narration; reviewing screenshots against the
checklist; choosing the video platform; judging tutorial language and pacing; deciding which
option each plot tutorial should feature.

## AUTHOR REVIEW - files to inspect

1. `tutorial/README.md` and `tutorial/01_Data_and_Column_Mapping/your_table_does_not_need_perfect_column_names.md` (language, level of detail)
2. `tutorial/plots/volcano_plot.md` and `tutorial/screenshots/volcano_manual_mapping/` (the manual-mapping story)
3. `tutorial/plots/boxplot_or_violin_with_points.md` and `tutorial/06_Statistics/statistics.md` (statistics wording)
4. `tutorial/video_scripts/master_from_data_to_figure.md` (pacing, narration style)
5. `tutorial/screenshots/getting_started/05_controls_full.png` (visual style, window size)
6. `tutorial/PLOT_GALLERY.md`, `tutorial/audit/plot_tutorial_inventory.csv`
7. `tutorial/audit/validation_report.md`
8. `tutorial/slides/MakeMyFigure_Tutorial_Seminar.pptx` (Arial deck from the author's template; rendered previews in `slides/_render/`)

The pilot MakeMyFigure desktop tutorial is ready for author review. The tutorial demonstrates
both guided recommendations and manual column mapping, including creation of different plots
from the same table. No tutorial materials have been pushed or released.
