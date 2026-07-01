# Make My Figure — Desktop App

A zero-command desktop application for non-technical scientists. Download an
installer, double-click, and create publication-style figures from your data —
no Python, no terminal required.

> **Journal-like, not official.** “Nature-like”, “Science-like”, and “Cell-like”
> are aesthetic style profiles only. They are **not** official journal templates
> and do **not** guarantee compliance with or acceptance by any publisher.

> **Privacy.** The desktop app runs entirely on your computer. Your data, figures,
> and settings never leave the machine. There is no telemetry and no cloud upload.

## Features

- **Welcome screen** — “Open data file”, “Use example data”, “Recent files”, “Help”.
- **Data import** — `.xlsx`, `.csv`, `.tsv`; drag-and-drop onto the window; table
  preview with detected column types; friendly error messages for malformed files.
- **Plot workflow** — choose plot type and style (Nature-/Science-/Cell-like), map
  required columns with dropdowns, set key options, and see a **live preview**.
  Validation warnings appear before you export.
- **Interactive figure toolbar** — the preview is a live Matplotlib canvas with the
  standard Qt navigation toolbar: **Home** (reset view), **Back/Forward** (view
  history), **Pan** (drag), **Zoom** (box-zoom), **Configure subplots**, and **Save**.
  The toolbar always controls the currently displayed figure — switching plot types
  rebuilds the canvas and toolbar together, with no stale plot left behind.
- **RStudio-like resizable panels** — drag the divider between the left controls and
  the right preview, and the horizontal divider between the top data/messages tabs
  and the bottom figure area. The figure canvas grows/shrinks with the window and the
  splitters. **Your panel layout and window size are remembered between sessions**
  (stored via `QSettings`).
- **Export** — SVG, PNG, PDF, PlotSpec JSON, or **all as a ZIP bundle**.
- **Examples & templates** — every supported plot type has a bundled example
  (File → Open example). “Save template” exports an example table so you can
  replace the rows with your own data while keeping the column names.
- **Help** — in-app Help window explaining each plot type, required columns, how to
  format your data, and the journal-like disclaimer.
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

## Journal-like style profiles (starter + learned)

The style selector offers six profiles: **Nature-like**, **Science-like**,
**Cell-like**, and their **(learned)** variants. The learned profiles are derived
from a *local* reference library of open-access (CC BY) papers by
`scripts/build_learned_styles.py`, which extracts only **aggregate** visual
conventions (e.g. median figure aspect ratio, panel-label style, typography and
line-width defaults) into `style_profiles/learned/*.json`.

> **How references are used.** Downloaded papers and figures are used only as local
> visual references to derive aggregate journal-like plotting conventions. The app
> does **not** copy published figures, does **not** reproduce copyrighted datasets
> unless explicitly licensed, and does **not** claim official journal compliance.
> Only aggregate measurements are stored in the repo; raw figure bitmaps stay
> local-only. See **[STYLE_REFERENCE_AUDIT.md](STYLE_REFERENCE_AUDIT.md)**.

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
