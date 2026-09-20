# Make My Figure — Desktop App

A zero-command desktop application for non-technical scientists. Download an
installer, double-click, and create publication-style figures from your data —
no Python, no terminal required.

> **Publication style, not an official template.** Make My Figure uses a single
> Publication style — a general manuscript-ready visual style. It is **not** an
> official journal template and does **not** guarantee compliance with or
> acceptance by any publisher.

> **Privacy.** The desktop app runs entirely on your computer. Your data, figures,
> and settings never leave the machine. There is no telemetry and no cloud upload.

## Features

- **Pop-out / pop-in panels (v0.5)** — detach the Figure, Data & Messages, or
  Plot Controls panels into floating windows (usable on a second monitor) via the
  **View** menu, and dock them back with state preserved. See
  [POP_OUT_PANELS.md](POP_OUT_PANELS.md).
- **Welcome screen** — “Open data file”, “Use example data”, “Recent files”, “Help”.
- **Data import** — `.xlsx`, `.csv`, `.tsv`; drag-and-drop onto the window; table
  preview with detected column types; friendly error messages for malformed files.
- **Plot workflow** — choose plot type (the Publication style is applied), map
  required columns with dropdowns, set key options, and see a **live preview**.
  Validation warnings appear before you export.
- **Interactive figure toolbar** — the preview is a live `FigureCanvasQTAgg` with the
  standard `NavigationToolbar2QT`: **Home** (reset view), **Back/Forward** (view
  history), **Pan** (drag), **Zoom** (box-zoom), **Configure subplots**, and **Save**.
  The home view is seeded on every render, so **Home works immediately** (before any
  pan/zoom). The toolbar always controls the currently displayed figure — switching
  plot types rebuilds the canvas and toolbar together, with no stale plot left behind.
  If a button ever seems inert, use **Help → Diagnose toolbar** (below) or run with
  `--debug` to log each action and canvas event.

- **Toolbar diagnostics** — **Help → Diagnose toolbar** runs a live in-app self-test
  (Home resets the view, Pan/Zoom modes engage, Save writes a file) and reports
  whether the toolbar is functionally connected to the current canvas, plus the exact
  running source file + commit (so you can confirm you're not on a stale synced copy).
  `python -m apps.desktop_app.main --debug` prints the same diagnostics and logs every
  toolbar action and canvas mouse event to the terminal.
- **RStudio-like resizable panels** — drag the divider between the left controls and
  the right preview, and the horizontal divider between the top data/messages tabs
  and the bottom figure area. The figure canvas grows/shrinks with the window and the
  splitters. **Your panel layout and window size are remembered between sessions**
  (stored via `QSettings`).
- **Export** — SVG, PNG, PDF, PlotSpec JSON (specification only), **Save Figure Package (.mmfpackage)** — one portable file with the specification, the frozen data and all records — or **all as a ZIP bundle** (figures + specs + package). **Open Figure Package** on the landing page / File menu reopens a package with its frozen data after verifying every checksum (see `FIGURE_PACKAGES.md`).
- **Examples & templates** — every supported plot type has a bundled example
  (File → Open example). “Save template” exports an example table so you can
  replace the rows with your own data while keeping the column names.
- **Help** — in-app Help window explaining each plot type, required columns, how to
  format your data, and the Publication-style disclaimer.
- **About / debug info** — About shows the version, git commit, and the exact file
  paths of the loaded desktop app and core package (so you can confirm which source
  is running). **Help → Copy debug info** copies it to the clipboard, and running with
  `--debug` prints it (plus a canvas/toolbar diagnostic and widget-tree dump) to the
  terminal. The status bar shows the version, commit, and source path at startup.
- **View menu** — **Reset Layout**, **Maximize Figure Panel**, and **Show/Hide Data
  Preview**.

## Running from source & OneDrive/iCloud/Dropbox warning

> **Run from a plain local folder.** Cloud-synced folders (OneDrive, iCloud Drive,
> Dropbox, Google Drive) can serve **stale copies** of source files or hold file
> **locks** during development, so you may end up running an old version of the app
> even after editing/pulling. If the app doesn't reflect your latest changes (e.g. a
> fix "doesn't apply"), that's the usual cause.
>
> Recommended: clone/run from a local path such as `~/Developer/make-my-figure`.
> The app flags this for you: if it detects a cloud-synced source path, the status
> bar and About dialog show a warning, and `Help → Copy debug info` includes the exact
> loaded file paths so you can verify you're on the current source.

## Run it from source (developers)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[desktop]"
python -m apps.desktop_app.main
# or:  python apps/desktop_app/main.py
```

The desktop app is a thin GUI over `make_my_figure_core`; it shares the exact
same plotting/validation/export engine as the Streamlit web app
(`apps/streamlit_app/streamlit_app.py`).

## Build installers

See **[BUILD_INSTALLERS.md](BUILD_INSTALLERS.md)**. In short:

```bash
pip install -e ".[desktop,build]"
python scripts/build_desktop.py        # app folder / .app under dist/
# then the per-OS wrapper:  scripts/build_windows.ps1 | build_macos.sh | build_linux.sh
```

## Publication style

Make My Figure uses a single **Publication** style — a polished, manuscript-ready
visual identity. Advanced controls (fonts, palette, line/marker sizes, legend,
figure size, DPI) adjust it without switching profiles. Aggregate design defaults
may be informed by a *local* reference library of open-access (CC BY) papers via
`scripts/build_learned_styles.py`, which extracts only **aggregate** visual
conventions (e.g. median figure aspect ratio, panel-label style, typography and
line-width defaults) — never individual figures.

> **How references are used.** Downloaded papers and figures are used only as local
> visual references to derive aggregate publication plotting conventions. The app
> does **not** copy published figures, does **not** reproduce copyrighted datasets
> unless explicitly licensed, and does **not** claim official journal compliance.
> Only aggregate measurements are stored in the repo; raw figure bitmaps stay
> local-only. See **[STYLE_REFERENCE_AUDIT.md](STYLE_REFERENCE_AUDIT.md)**.

## Lollipop mutation plot options

The lollipop renderer is tuned for publication-style output: wide aspect, thin
stems, marker size scaled by mutation/sample count, the mutation-type legend placed
**outside** the axes, and top-N mutation labels drawn above markers with a vertical
margin and staggering so they never touch markers or clip at the top. Options
(in the desktop **Options** panel and via PlotSpec `mapping`):

- **Show mutation labels** (`show_labels`)
- **Label top N mutations** (`label_top_n`, default 6) — labels only the highest-count
  positions rather than every point.
- **Legend position** (`legend_loc`: `right` default, or `bottom`).
- **Marker scale** (`marker_scale`) — marker area per unit count.
- **Top y-margin** (`y_margin`) — extra headroom above the tallest lollipop.

## Recommended export formats for publication

- **SVG or PDF** for vector figures with **editable text** (fonts are embedded as
  text, not outlines — `svg.fonttype=none`, `pdf.fonttype=42`), so you can tweak
  labels in Illustrator/Inkscape.
- **PNG at 300–600 DPI** for raster use (slides, previews). The desktop **Raster DPI**
  control sets PNG/TIFF resolution.
- **PlotSpec JSON** sidecar (the recipe; source data required) and **figure packages** (`.mmfpackage`, recipe + frozen data; see `FIGURE_PACKAGES.md`).
- Exports use tight bounding boxes so an outside legend is always fully included.

## Architecture

```
make_my_figure_core/      reusable engine (loaders, validation, styles,
                          renderers, export, provenance, mock-data + ui hints)
apps/streamlit_app/       web/developer frontend (unchanged)
apps/desktop_app/         PySide6 desktop frontend
  controller.py           GUI-free logic (load/build-spec/render/export)
  main.py                 Qt windows & widgets
  help_content.py         help text (plot descriptions from the manifest)
```

No plotting logic lives in the GUI — `main.py` only builds widgets and calls the
controller, which calls the core.
