# Windows performance notes

Make My Figure's desktop app (PySide6) runs identically on Windows, macOS, and
Linux, but Windows users most often notice startup lag and preview stutter.
This page explains why, what v0.6 does about it, and how to measure it on your
own machine.

## Why Windows can feel slower

- **OneDrive / cloud-synced working directories.** If the repo or your data
  files live under a OneDrive (or Dropbox/iCloud) folder, the first read of a
  file can block on cloud "hydration" — the file has to be fetched from the
  cloud before the OS can open it. File dialogs opened inside a synced folder
  can also feel slower for the same reason. This is outside the app's control;
  moving working data to a local, non-synced folder avoids it.
- **PyInstaller cold start.** The first launch of a frozen Windows build pays
  for: a Defender/SmartScreen scan of the new executable, cold DLL/plugin
  loading, and Matplotlib's one-time font-cache build. Subsequent launches are
  faster because the OS and Matplotlib cache the results.
- **Synchronous GUI-thread work.** Before v0.6, rendering, statistics, and
  export all ran on the Qt GUI thread — while a plot rendered, the window
  could not repaint or respond to input, which reads as a freeze (most visible
  on Windows where users are more likely to interact with the window while
  waiting).

## What v0.6 does

- **Background workers.** `apps/desktop_app/workers.py` wraps Qt's
  `QThreadPool`/`QRunnable` (`Task`, `run_in_background`, `global_pool`) so a
  long callable — statistics, clustering, layout, export, or figure
  *construction* — can run off the GUI thread and report back via signals
  (`finished`, `error`, and an optional `progress`). A Matplotlib `Figure` can
  be built inside a worker (the Agg backend is fine off-thread); the
  interactive **canvas** is still attached to it on the GUI thread in the
  `on_done` callback, because Qt widgets are not thread-safe.
- **Debounced rendering.** Continuous controls (sliders, spinboxes) delay their
  re-render until input settles instead of re-rendering on every intermediate
  value, cutting down redundant renders while dragging a control.
- **Lazy scipy import.** Statistics (which pulls in scipy) is imported only
  when statistics are actually used, not at app startup, shortening cold
  import time.

## Known remaining limitation

The desktop preview **canvas is still rebuilt on every render** rather than
updated in place — this is the main remaining source of preview flicker/lag
and is documented as a limitation rather than fixed in v0.6 (canvas reuse is a
larger change to the render/preview path).

## Measuring it yourself

```bash
python scripts/benchmark_performance.py --quick
python scripts/benchmark_performance.py --out outputs/performance/v0_6_performance_report.md
```

The script measures, with the headless Agg backend and no network access:

- **Cold import** — a fresh interpreter importing `make_my_figure_core` and
  `apps.desktop_app.controller` (subprocess-timed, so it reflects real
  first-import cost).
- **Example load** — `controller.load_example(plot_type)` for the common plot
  types (`barplot_with_error_bar`, `scatterplot_with_regression`,
  `boxplot_or_violin_with_points`, `volcano_plot`) and the heavier ones
  (`heatmap_clustered_matrix`, `pca_scatter_from_matrix`).
- **Render** — build + render each of those plot types.
- **Export** — one figure exported to SVG + PNG + PDF at 300 DPI.
- **Recommendation** — `recommend_for_table` timing on a common example.

`--quick` runs a smaller subset for a fast check; `--repeats N` (default 3)
controls how many times each timing is repeated (best + median are reported).
`--out PATH` writes the Markdown report; without it the report just prints to
stdout. All timings are **local and relative** — compare before/after on the
same machine, don't compare across machines.

### Expected first-launch delay

The first launch of a packaged Windows build after installation or an update
can take noticeably longer than subsequent launches (Defender/SmartScreen scan
+ cold DLL load + font-cache build, as above). This is a one-time cost per
build/update, not a sign of an ongoing performance problem — if every launch is
slow, that points at something else (e.g. a OneDrive-synced install location).

## Remaining limitations

- Timings vary widely by machine, antivirus configuration, and whether the
  working directory is cloud-synced; re-run locally rather than trusting a
  number from a different machine.
- Background rendering builds figures off-thread, but canvas updates must still
  happen on the GUI thread (a Matplotlib/Qt requirement) — heavy background
  work still ends with one GUI-thread canvas swap.
- First-launch delay on frozen Windows builds is largely outside the app's
  control.

## See also

- [docs/V0_6_NEW_FEATURES.md](V0_6_NEW_FEATURES.md)
- [docs/BUILD_INSTALLERS.md](BUILD_INSTALLERS.md) / [docs/DESKTOP_APP.md](DESKTOP_APP.md) — packaging context for the cold-start costs described above.
