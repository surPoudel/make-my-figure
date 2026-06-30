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
- **Export** — SVG, PNG, PDF, PlotSpec JSON, or **all as a ZIP bundle**.
- **Examples & templates** — every supported plot type has a bundled example
  (File → Open example). “Save template” exports an example table so you can
  replace the rows with your own data while keeping the column names.
- **Help** — in-app Help window explaining each plot type, required columns, how to
  format your data, and the journal-like disclaimer.
- **About** — shows the app version (single-sourced from the package).

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
