# Author test checklist - <plot_type> (<display name>)

Fill the placeholders, hand it to the author with the acceptance report, and stop.

Build/launch: `<path to local build>` or `python -m apps.desktop_app.main` in `<checkout>` (commit `<sha>`).

| # | step | how | expected | result |
|---|---|---|---|---|
| 1 | Load normal data | Home -> Upload `<your file>` (or Open example -> <display name>) | Detected data type shown; plot type listed as "<display name>" | |
| 2 | Map columns | Set `<role>` = `<column>`, ... | Roles accepted; missing required role gives a clear message | |
| 3 | Render | Generate | Figure appears; warnings (if any) are understandable | |
| 4 | Customise | Change `<option 1>`, `<option 2>`, palette, font size, figure width | Only appearance changes; numbers unchanged | |
| 5 | Statistics (if applicable) | Enable statistics, test = auto | Brackets/labels above the data; sidecar lists test, n, P | |
| 6 | Save PlotSpec | Export -> `.plot_spec.json` | File written next to the figure | |
| 7 | Reload | Open PlotSpec + the same data | Same figure, same numbers | |
| 8 | Save preset | Figure preset -> Save preset... | Listed under your presets | |
| 9 | Apply preset to other data | Load `<other file>`, apply | Look transfers; roles the new table lacks are reported, never guessed | |
| 10 | Figure Package (if available in this build) | Save package; move it; reopen without the original folder | Reopens, integrity verified, identical numbers | |
| 11 | Figure Builder | Add as panel with one other plot; resize; export | Panel label, aspect kept, no clipping | |
| 12 | Exports | SVG, PDF, PNG (300 dpi), TIFF | Text editable in SVG/PDF; physical width as set | |
| 13 | Edge data | `<small n / many groups / long labels file>` | Readable; no overlap; warnings where relevant | |

Known limitations to confirm or reject: <list>.
