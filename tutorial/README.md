# Make My Figure - desktop tutorial

A step-by-step course for the **desktop application**, from opening the program to building a
multi-panel figure, written against the application as it is today (see `VERSION`). Every
screenshot is a capture of the real application driven by the scripts in `automation/`; every
instruction was executed against the application and recorded as PASS in
`audit/validation_report.md`.

## The one idea to take away

Your table does not have to be arranged or named the way the application expects. Open it,
look at the **Data preview**, choose a plot, and assign your columns to roles under
**2. Map columns**. The application proposes roles and recommends figures; those proposals are
conveniences, and the assignment stays yours. The same table can produce several different
figures - the data do not belong to one plot.

## Start here

| step | read | do |
|---|---|---|
| 1 | [00_Getting_Started/getting_started.md](00_Getting_Started/getting_started.md) | launch, start screen, layout |
| 2 | [01_Data_and_Column_Mapping/your_table_does_not_need_perfect_column_names.md](01_Data_and_Column_Mapping/your_table_does_not_need_perfect_column_names.md) | the mapping master tutorial |
| 3 | [01_Data_and_Column_Mapping/reshaping_and_derived_columns.md](01_Data_and_Column_Mapping/reshaping_and_derived_columns.md) | what the app can restructure for you |
| 4 | [PLOT_GALLERY.md](PLOT_GALLERY.md) | pick a plot, follow its tutorial |
| 5 | [03_Group_Comparisons/showing_individual_observations_and_jitter.md](03_Group_Comparisons/showing_individual_observations_and_jitter.md) | summary + every observation: size, jitter, markers, statistics |
| 6 | [06_Statistics/statistics.md](06_Statistics/statistics.md), [09_Styling_and_Annotations/styling.md](09_Styling_and_Annotations/styling.md) | tests on the figure, appearance |
| 7 | [10_Figure_Presets/publication_presets.md](10_Figure_Presets/publication_presets.md), [10_Figure_Presets/figure_presets.md](10_Figure_Presets/figure_presets.md), [11_Reproducibility/plotspec_and_figure_package.md](11_Reproducibility/plotspec_and_figure_package.md) | publication presets with preview; your own presets; reproduce a figure |
| 8 | [12_Figure_Builder/figure_builder.md](12_Figure_Builder/figure_builder.md), [13_Export/export.md](13_Export/export.md) | composite figures, files for the journal |
| 9 | [14_Complete_Workflows/from_data_to_publication_figure.md](14_Complete_Workflows/from_data_to_publication_figure.md) | the whole path in one sitting (master video) |

## Folders

| folder | content |
|---|---|
| `00_Getting_Started/` ... `14_Complete_Workflows/` | topic tutorials in reading order |
| `plots/` | one tutorial per registered plot type (same template for all: `plots/_TEMPLATE.md`) |
| `datasets/` | small simulated tables that support many plots; `make_tutorial_datasets.py` regenerates them with fixed seeds |
| `screenshots/<tutorial_id>/` | real captures produced by `automation/run_tutorial.py` |
| `video_scripts/` | timed scripts (screen, action, narration) for each video |
| `videos/` | recording guide, link mapping (`video_links.json`), raw/final videos (not committed) |
| `showcase/` | same-data / different-presentation renders (five showcases, `build_showcase.py`), presets used |
| `automation/` | the driver that operates the real application, action scripts, gallery / inventory / manifest / HTML builders, validation |
| `audit/` | plot inventory, validation records, screenshot and video checklists |
| `html/` | browsable copy (`automation/build_html.py`) |

## Status

Visual review (2026-09-23): the pilot was re-evaluated as a visual demonstration
(`audit/TUTORIAL_VISUAL_REVIEW.md`, `../presentation/audit/SLIDE_VISUAL_REVIEW.md`); the tutorial
branch now includes the presets branch so that individual observations, jitter and the experimental
publication presets can be shown from the real application (`audit/MISSING_SHOWCASE_CAPABILITIES.md`).

Pilot: nine tutorials (scatter / regression, box-violin with statistics, volcano with manual
mapping, clustered heatmap, Kaplan-Meier, the ambiguous-columns mapping tutorial, figure presets,
figure packages, Figure Builder) plus getting started, written, captured and validated. The
remaining plot types are inventoried in `audit/plot_tutorial_inventory.csv` and marked MISSING
until their tutorials are written after author review. `MAINTAINING_THE_TUTORIAL.md` describes
the update loop.

All datasets are **simulated**; they carry no biological meaning and must not be cited as
findings.
