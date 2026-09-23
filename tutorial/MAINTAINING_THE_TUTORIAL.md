# Maintaining the tutorial

The tutorial is generated against the live application, so it can be checked and extended by
script. This is the loop to run when the application changes and when a plot type is added.

## When a plot type is added

1. **Registry audit detects it.** `python tutorial/automation/build_inventory.py` reads the
   plot registry; the new plot appears in `audit/plot_tutorial_inventory.csv` with
   `tutorial_status = MISSING` and `video_status = MISSING`. `build_manifest.py` lists it under
   `plot_tutorials_missing`.
2. **Deterministic example.** Add the columns the plot needs to one of the existing
   `datasets/*.csv` generators in `datasets/make_tutorial_datasets.py` (fixed seed) rather than a
   new file, unless the shape is genuinely new. Re-run the generator.
3. **Action script.** Copy `automation/tutorials/scatter_regression.py`, rename to the plot id,
   set `TITLE`, `DATASETS`, the plot type and the roles. Capture the standard checkpoints:
   `01_open_data`, `02_mapping`, `03_initial_plot`, `04_customization`, `05_statistics` (if any),
   `06_final_plot`, plus exports. Record facts (`ctx.fact`) for anything the Markdown will quote.
4. **Run it.** `python tutorial/automation/run_tutorial.py <plot_id>`; fix until PASS.
5. **Write the tutorial** from `plots/_TEMPLATE.md` into `plots/<plot_id>.md`, quoting the
   recorded facts (proposed roles, option names, messages). Every UI label in backticks must be
   the label the application shows.
6. **Video script**: `video_scripts/<plot_id>.md` from `video_scripts/_TEMPLATE.md`; add the
   id to `videos/video_links.json` with a `VIDEO_URL_...` placeholder.
7. **Gallery and manifest**: `build_gallery.py`, `build_inventory.py`, `build_manifest.py`,
   `build_html.py`.
8. **Validate**: `python tutorial/automation/validate_tutorials.py` and check
   `audit/validation_report.md`; run the screenshot checklist (`audit/screenshot_validation_checklist.md`).

## When the application changes

Run `validate_tutorials.py`. A renamed control, a removed option or a changed proposal fails
the corresponding check or changes a recorded fact; the report names the tutorial and the step.
Update the action script and the Markdown together, re-capture, re-validate.

## Versioning

`VERSION` and `tutorial_manifest.json` record the software version, commit, plot count,
tutorial count, video count and generation date. Do not write version numbers into the
tutorial text.

## Environment notes

* Screenshots: offscreen Qt, 1680 x 1000, control column 600 px, Qt scale 1, 96 dpi, empty
  presets and settings (the driver sets all of this).
* Linux without root needs the Qt system libraries unpacked locally (`automation/README.md`).
* Windows captures (native widget style) are produced with the same scripts under a Windows
  Python that has PySide6; the on-screen mode there is also what the videos are recorded from.

## Integration with the MakeMyFigure Developer agent

The agent's plot-type checklist (in the agent's own branch) should include the eight steps
above; the inventory CSV is the hand-over point - anything MISSING there is tutorial work.
