# Tutorial automation

Everything in this folder operates the **real** desktop application (`apps/desktop_app/main.py`).
No tutorial code is added to the application; the driver reaches into the running `MainWindow`
and uses its widgets exactly as a user would.

| file | purpose |
|---|---|
| `mmf_driver.py` | `MMFDriver`: launch the real window (offscreen or on screen), open files, choose the plot type, set rows of *2. Map columns*, *3. Options*, *4. Labels & size*, the *Statistics* panel, presets, exports, figure packages, the Figure Builder; grab any widget to PNG; record PASS / FAIL checks |
| `run_tutorial.py` | run one tutorial action script (`tutorials/<id>.py`) - screenshots + validation record, or on-screen for recording |
| `tutorials/` | one action script per tutorial: `TITLE`, `DATASETS`, `run(drv, ctx)` |
| `build_inventory.py` | `tutorial/audit/plot_tutorial_inventory.csv` from the live plot registry |
| `build_gallery.py` | `tutorial/PLOT_GALLERY.md` with a real render of every registered plot type |
| `build_manifest.py` | `tutorial/VERSION` and `tutorial/tutorial_manifest.json` |
| `build_html.py` | browsable HTML copy of the tutorial (Python-Markdown, no framework) |
| `validate_tutorials.py` | run every action script offscreen and write `tutorial/audit/validation_report.md` |

## Screenshots (offscreen, deterministic)

```
python tutorial/datasets/make_tutorial_datasets.py      # once
python tutorial/automation/run_tutorial.py --list
python tutorial/automation/run_tutorial.py mapping_ambiguous
python tutorial/automation/run_tutorial.py all
```

Screenshots land in `tutorial/screenshots/<tutorial_id>/`, exported files in
`tutorial/automation/_outputs/<tutorial_id>/` (git-ignored) and the validation record in
`tutorial/audit/validation/<tutorial_id>.json`. Window size is 1680 x 1000, the control column is
600 px wide, Qt scale factor 1, 96 dpi fonts, an empty preset library and empty settings, so the
captures do not depend on the machine they were made on.

### Linux without root

PySide6 needs `libxkbcommon.so.0` and `libEGL.so.1`. Without `sudo` they can be unpacked from the
Ubuntu packages into a folder and exported:

```
mkdir -p /tmp/qtdeb && cd /tmp/qtdeb
apt-get download libxkbcommon0 libegl1 libgl1 libglvnd0 libglx0 libegl-mesa0 libgbm1 libopengl0
for f in *.deb; do dpkg -x "$f" root; done
export LD_LIBRARY_PATH=/tmp/qtdeb/root/usr/lib/x86_64-linux-gnu
```

## On-screen runs for video recording

```
python tutorial/automation/run_tutorial.py volcano_manual_mapping --onscreen --pause 1.5
```

The real window opens on the desktop and the driver performs each step with a pause, so the
viewer (and the recorder) can follow. Start the recorder first; see `tutorial/videos/RECORDING.md`
for the per-platform capture commands. Automation and recording are deliberately separate.

## Writing a new action script

```python
TITLE = "Waterfall plot"
DATASETS = ["one_table_many_plots.csv"]

def run(drv, ctx):
    drv.open_file(ctx.dataset("one_table_many_plots.csv"))
    drv.select_plot("waterfall_plot")          # plot id or display name
    drv.set_mapping("x", "sample_id")          # rows of "2. Map columns"
    drv.set_mapping("y", "response")
    drv.update_preview()                       # asserts that a figure rendered
    drv.capture("03_initial_plot", "window")   # window | mapping | options | stats | figure | ...
    drv.export("png", ctx.out("waterfall.png"))
    ctx.fact("proposed_mapping", drv.current_mapping())   # recorded for the written tutorial
```

Every `drv.*` call that changes state adds a step to the log; `drv.log.check(...)` calls become
the PASS / FAIL rows of the validation report. `ctx.fact(...)` records what the live application
showed (proposed roles, recommendation text, option choices) so the Markdown tutorial can quote
it and the validation run can catch drift when the application changes.
