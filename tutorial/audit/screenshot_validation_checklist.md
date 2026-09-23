# Screenshot validation checklist

Applies to every PNG under `tutorial/screenshots/`. The driver produces them from the real
application with isolated settings and an empty preset library, which rules out several items
by construction; the rest are checked by eye per tutorial.

| check | how it is ensured | manual pass |
|---|---|---|
| no obsolete controls | captured from the current build (see `VERSION`); re-captured by `validate_tutorials.py` | per release |
| no old version number | the window title carries no version; About dialog is not captured | - |
| no old plot count | the plot-type list is read live; the text says "39 plot types" only in `getting_started.md`, regenerated from the registry count in the manifest | per release |
| no deprecated UI | same build for all captures | per release |
| no private manuscript data | only `tutorial/datasets/*.csv` (simulated) and bundled examples are opened | by construction |
| no OneDrive or personal paths | file dialogs are never shown (answered programmatically); status bar shows file names only; confirmation boxes show table names | checked: `03_package_confirmation.png` shows "group_comparison.csv (30 x 5)" only |
| no API keys / credentials | the application has none | - |
| no personal information | isolated settings: no recent files, no user presets | by construction |
| consistent window size / scale / theme | 1680 x 1000, Qt scale 1, 96 dpi, offscreen Fusion style on Linux; native style on Windows captures | by construction |
| cropping keeps context | widget-level captures (mapping, options, statistics) are used only next to a full-window capture of the same state | per tutorial |

Pilot check (2026-09-23): all captures under `screenshots/` for the nine pilot tutorials and
`getting_started` reviewed; one path appears in a message box text recorded in
`audit/validation/figure_package.json` ("Figure package saved ... <path>") but that box is not
captured as an image.
