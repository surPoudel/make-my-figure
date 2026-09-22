## Part I — Introduction

### 1. About Make My Figure

Make My Figure (package `make_my_figure_core`, version 1.1.1) turns tabular scientific data — CSV/TSV/TXT files and Excel workbooks — into manuscript-style figures, and records how each figure was made. One engine serves two interfaces: a **desktop application** built with Qt (PySide6) and a **browser application** built with Streamlit. Both run entirely on your own computer.

### 2. Intended users

Bench and computational scientists who have a table of results and need a clean, consistent, reproducible figure: a bar or box plot of replicate measurements, a volcano from a differential-expression table, a heatmap or PCA from a normalised matrix, a Kaplan–Meier curve, a network, a multi-panel composite for a manuscript. No programming is required; the PlotSpec files it writes are plain JSON if you want to look inside.

### 3. Design principles

- **You confirm the mapping.** Columns are assigned to roles (x, y, group, p-value, time, event…) by you. Auto-detection only prefills a suggestion — for a differential-expression table it recognises edgeR/limma/DESeq2 headers, for a matrix it proposes value columns — and you accept or change it.
- **No silent guessing.** A numeric annotation column is not treated as a measurement until you tick it; a value scale (raw, normalised, log) is declared, not inferred; a survival curve that is already computed is refused as a 0/1 event column instead of being drawn wrong.
- **Every number drawn is stored.** A p-value or effect size on a figure always comes from a stored statistical result that is exported alongside the figure. Renderers never format p-values themselves.
- **Controls that do not apply are reported**, never ignored quietly.
- **One style.** The **Publication** style is a general manuscript-ready visual style — readable fonts, colour-blind-aware palettes, tidy axes. It is not a journal template and the app says so in its exported metadata.
- **Original data are never modified.** Preprocessing creates a new, derived table with its steps recorded; the source stays as loaded.

### 4. What Make My Figure does

- Loads delimited text and Excel (including every worksheet of a multi-sheet workbook, stacked and merged headers).
- Profiles a table and **recommends** plots, with a reason and a match score.
- Renders **38 plot types** from a single registry.
- Runs **18 statistical methods** with multiple-testing correction and effect sizes, and annotates figures from stored results.
- Guides a **Matrix Workflow** (feature × sample matrices): mapping, groups/metadata, preprocessing, QC, differential summary, plot generation.
- Offers **Publication controls** (typography, palette, axes, legend, colorbar, margins) with capability-aware honesty.
- Supports **annotations** (click-to-label points, duplicate-label policies, a manual annotation layer in the PlotSpec).
- Saves and applies **Figure presets** (style-only or full configuration) across datasets.
- Assembles **multi-panel figures** from generated and imported panels.
- Exports **SVG, PDF, EPS, PNG, TIFF** with a **PlotSpec** (and StatsSpec / FigureSpec) record, and saves **figure packages** (`.mmfpackage`) that carry the specification together with the frozen data.

### 5. What Make My Figure does not do

- It does **not** perform differential-expression inference (no DESeq2, edgeR or limma). It plots a DE table you already have and reads its p-values verbatim. (A separate, opt-in `count-de` extra exists for a Python-only count model; it is not part of the standard install and is not covered by this manual.)
- It does **not** choose a statistical test for you. Suggestions are advisory.
- It does **not** guarantee journal acceptance or compliance with any journal's author guidelines.
- It does **not** upload data, collect telemetry, or need a network connection to run.
- It does **not** implement Dunnett's test; comparisons against a control use the pairwise test you choose with a multiple-testing correction.

### 6. Reproducibility and provenance model

**Export PlotSpec JSON**, **Export all as ZIP** and the browser downloads write a **PlotSpec** (`name.plot_spec.json`): the plot type, the table name, the column roles, every option, the style tokens, the layout, statistics settings, manual annotations, worksheet provenance, a content digest of the table, and the render metadata (including the software versions used for statistics). The single-format desktop buttons (SVG/PNG/PDF) write the figure file only. When statistics ran, **Export all as ZIP** and the browser also write a **StatsSpec** (`name.stats_spec.json`) with every result. The Figure Builder writes a **FigureSpec** referencing each panel's PlotSpec. A PlotSpec or FigureSpec records the *identity* of its tables, not their values, so it needs the data to reopen. The Matrix Workflow's **MatrixSpec**, **SampleMetadataSpec** and **PreprocessingSpec** reach an export only through the figure package.

The **figure package** (`name.mmfpackage`) is the portable record: one file with the PlotSpec (or FigureSpec), a frozen lossless copy of the exact table(s) the plot used, the original source file when available, the StatsSpec results, the MatrixSpec / SampleMetadataSpec / PreprocessingSpec where they apply, imported images, PNG/SVG/PDF previews, the software environment and a manifest with a SHA-256 for every file. **Open Figure Package** verifies every checksum and reopens the figure from the frozen data on any computer (Part XV).

A figure is therefore **reconstructable under a recorded software environment**: open the figure package (or the PlotSpec with its data) with the same code, and the same figure is rebuilt. Byte-identical output across different machines is not promised — fonts, Matplotlib versions and platform text rendering differ slightly.

### 7. Local, open-source architecture

Python, pandas, NumPy, SciPy, statsmodels, Matplotlib, openpyxl, networkx. The desktop app adds PySide6; the browser app adds Streamlit. Data flow: **loader → PlotSpec (validated against a JSON schema) → renderer → RenderResult → export + sidecar**. Source: `https://github.com/surPoudel/make-my-figure`.

## Part II — Installation and startup

### 8. Which installation is for you

| You want to… | Use |
|---|---|
| Run the desktop app without installing Python | **Packaged installer** (Windows `.exe`/`.zip`, macOS `.dmg`, Linux `.AppImage`/`.tar.gz`) |
| Run the newest code, the browser app, or develop | **Source install** with Python 3.10–3.12 |
| Use Make My Figure from your own scripts | `pip install` the core wheel (`make_my_figure_core-*.whl`) — no GUI included |

The installers attached to release **v1.1.1** (`MakeMyFigure-1.1.1.dmg`, `MakeMyFigure-1.1.1-Setup.exe` / `MakeMyFigure-1.1.1-windows.zip`, `MakeMyFigure-1.1.1.AppImage` / `MakeMyFigure-1.1.1-linux.tar.gz`) are built from the tagged v1.1.1 source on native macOS, Windows and Linux runners and contain everything this manual documents (Figure presets, the histogram plot, survival-curve and merged-header fixes, the R-validated statistical corrections). Download them from the project's GitHub *Releases* page and check the file's SHA-256 against `SHA256SUMS.txt` if you want to verify the download.

### 9. macOS

**Packaged:** open `MakeMyFigure-1.1.1.dmg`, drag *Make My Figure* to *Applications*. The bundle is not notarised: on first launch right-click → **Open**, or allow it in *System Settings → Privacy & Security*.

**Source:**

```bash
git clone https://github.com/surPoudel/make-my-figure.git
cd make-my-figure
# use a modern interpreter (Homebrew python@3.11/3.12 or a conda base python):
python3.11 -m venv .venv_mac
source .venv_mac/bin/activate
python -m pip install --upgrade pip
python -m pip install --no-compile -r requirements.txt
python -m pip install --no-compile -e ".[desktop]"
python -c "from make_my_figure_core.version import build_banner; print(build_banner())"
python -m apps.desktop_app.main
```

Common macOS startup errors:

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'pandas'` while the prompt shows `(.venv)` | a stale venv label; the folder was moved or the wrong `python` is first on PATH | `deactivate; conda deactivate`, then re-create the venv in the project folder and `source` it again |
| `numpy.dtype size changed … Expected 96 from C header, got 88` | two environments stacked (`(base)` + a venv) so pandas came from one and NumPy from another | deactivate everything, create one fresh venv, install into it |
| pip crashes with `SyntaxError … {% for module in qt_modules %}` while installing PySide6 | Apple's Python 3.9 byte-compiling a Jinja template inside PySide6 | use Python 3.10+ and `pip install --no-compile` |

### 10. Windows

**Packaged:** run `MakeMyFigure-1.1.1-Setup.exe` (Inno Setup installer) or unzip `MakeMyFigure-1.1.1-windows.zip` and start `MakeMyFigure\MakeMyFigure.exe`. Windows Defender may show a SmartScreen prompt for an unsigned binary; choose *More info → Run anyway* if you trust the source.

**Source (PowerShell):**

```powershell
git clone https://github.com/surPoudel/make-my-figure.git
cd make-my-figure
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1        # if blocked: Set-ExecutionPolicy -Scope Process RemoteSigned
python -m pip install --upgrade pip
python -m pip install --no-compile -r requirements.txt
python -m pip install --no-compile -e ".[desktop]"
python -m apps.desktop_app.main
```

First launch of the packaged app can take 10–20 s while Windows unpacks and scans the bundle; later launches are faster. Rendering runs in background workers so the window stays responsive.

### 11. Linux

**Packaged:** `chmod +x MakeMyFigure-1.1.1.AppImage && ./MakeMyFigure-1.1.1.AppImage`, or unpack `MakeMyFigure-1.1.1-linux.tar.gz` and run `MakeMyFigure/MakeMyFigure`.

**Source:** as for macOS, using the distribution's `python3` (3.10+). The Qt binding needs system libraries that server and container images usually lack:

```bash
sudo apt install -y libxkbcommon0 libxkbcommon-x11-0 libgl1 libegl1 libxcb-cursor0 \
    libxcb-xinerama0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
    libxcb-icccm4 libxcb-image0 libxcb-xfixes0 libdbus-1-3
```

If PySide6 cannot load, the desktop app prints this exact list and exits cleanly; the browser app is unaffected.

### 12. WSL2 (Linux running under Windows)

WSL2 is Linux running inside Windows; it is not native Windows and the Windows installer does not apply to it. The source install works in WSL 2. The desktop app needs a display: WSLg (Windows 11) provides one automatically; otherwise use the browser app, which needs no display — `streamlit run apps/streamlit_app/streamlit_app.py --server.headless true` and open the printed URL in a Windows browser. Install the Linux Qt libraries above if you want the desktop app.

### 13. Launching, verifying the version, updating, uninstalling

- **Desktop:** `python -m apps.desktop_app.main` (source) or the installed application. The status bar shows the build banner on launch (`Make My Figure v1.1.1 · <commit> · <platform> · <backend>`); **Help → About** shows the version.
- **Browser:** `streamlit run apps/streamlit_app/streamlit_app.py`; the banner is in the sidebar, with a **🔧 Diagnostics** expander listing the module path and backend. If the commit there does not match your pulled HEAD, an older installed package is shadowing the checkout — run `python -m pip install -e .`.
- **Update a source install:** `git pull`, then re-run the two `pip install` lines.
- **Uninstall:** delete the project folder and the venv; packaged apps uninstall like any application. User presets live in a separate folder (Part XIV) and are not removed with the app.

## Part III — The application interface

### 14. Desktop layout

![The desktop workspace with numbered regions.](../../assets/screenshots/desktop_02_data_loaded_workspace.png)

Left column (scrollable, "Plot Controls"): **Home / Upload New Data**, **Define groups…**, **Matrix workflow…**; **1. Plot type & style**; **Recommended figures**; **2. Map columns**; **3. Options**; **4. Labels & size** (title, axis labels, figure width, raster DPI, point picking); **Figure preset**; **5. Publication style** (checkable; ② Typography, ③ Axes & labels, ④ Legend, ⑤ Colorbar, ① Figure margins); **6. Statistics**; **5. Export**; **6. Multi-panel figure**.

Right: **Data preview** (editable — edits re-render the figure) and **Messages** tabs above the **figure** with the Matplotlib toolbar (home/zoom/pan/save). The status bar shows the build banner, loaded-file messages and statistics results.

![The controls column: plot type, recommended figures, column mapping, options and labels.](../../assets/screenshots/desktop_03_plot_selector_and_mapping.png)

**Menus.** *File:* Home / Upload New Data, Open data file…, Open Figure Package…, Open PlotSpec… (specification only), Save Reproducible Figure Package…, Open example ▸ (all 38), Recent files (packages marked 📦), Save template…, Figure preset ▸ (Apply, Save, Import, Export, Delete, Reset), Quit. *View:* Reset Layout, Maximize Figure Panel, Show Data Preview, Dock All Panels. *Help:* Help…, About, Copy debug info, Diagnose toolbar.

**Pop-out panels.** *Plot Controls*, *Data & Messages* and the *Figure* can each be popped out into their own window (for a second monitor) and docked back with **⮊ Dock back** or **View → Dock All Panels**; the arrangement persists between sessions.

**Home / Upload New Data** clears the data, spec, results and statistics and returns to the welcome page without restarting. The Matplotlib toolbar's own *home* only resets zoom/pan.

**Help.** *Help → Help…* opens a dialog with tabs **Plot types** (one entry per registered type, from the example manifest), **Format your data**, **Privacy** (everything runs locally, no telemetry) and **Publication style disclaimer**.

![The Help dialog.](../../assets/screenshots/desktop_18_help.png)

### 15. Browser layout

![Browser app before data is chosen: data source, workflow, plot type and style in the sidebar.](../../assets/screenshots/streamlit_01_home.png)

Sidebar: **1. Data** (Bundled sample / Upload file / Open PlotSpec / Open Figure Package; Worksheet + Header row for workbooks; **Workflow**: Quick plot or Matrix workflow (guided)); **2. Plot type**; **3. Style**; **4. Column mapping** (plus the plot's own options); **Figure preset**; **5. Publication style** (five expanders); **6. Statistics**. Main column: the editable table with row/column counts, **🗂 Define groups**, **🔮 Recommended figures**, **Figure preview** with warnings and the publication check, **✅ Publication QC**, **Render metadata**, and **Export** (SVG / PNG / PDF / PlotSpec JSON / Figure Package downloads). **🏠 Reset / Upload new data** clears the session.

### 16. Functional equivalence and differences

| Capability | Desktop | Browser |
|---|---|---|
| Header-row choice for uploads | first row only | first / chosen / two stacked / none, plus forward fill |
| Font family control | yes | no |
| Click-to-label | click on the canvas | pick from a list + numeric offsets |
| Figure Builder | full (grid, sizes, imports, layout presets) | columns-only composer inside the Matrix workflow |
| Export EPS/TIFF | via **Export all as ZIP** | not offered (SVG/PNG/PDF) |
| Statistics export | stats table, method report, copy sentence | shown in-page |
| Preset library | shared folder | shared folder |

## Part IV — Data input

### 17. Supported files

| Type | Extensions | Notes |
|---|---|---|
| Delimited text | `.csv`, `.tsv`, `.txt`, `.tab` | delimiter is sniffed; an unknown extension is parsed as text with a warning |
| Excel | `.xlsx`, `.xlsm`, `.xls` | every worksheet is selectable; merged header cells are recovered for `.xlsx`/`.xlsm` (`.xls` has no merge map) |

Text encoding should be UTF-8. Column names should be in the first row (desktop) or the row you choose (browser).

### 18. Headers, missing values, types

- **Header row** (browser): *First row*, *Choose row…* (skips title/report rows above the header), *Two rows (stacked)* (outer group + inner replicate labels become `Group | Replicate` column names), *No header* (positional names `column_1`, `column_2`…). Excel merged cells spanning a block of replicate columns are expanded to every column of the block. For labels typed once **without** merging, tick **Carry a group label across blank cells**.
- **Duplicate column names** are disambiguated (`event`, `event.1`, `event.2`) and kept as separate columns — row-level identity is preserved, nothing is collapsed by label.
- **Missing values** (blank, `NA`, `NaN`) are reported per column in Messages; renderers drop them where a statistic or geometry needs a value and say so.
- **Numeric detection** is by content; a column mixing text and numbers stays text — the preview lists *Detected types*.
- **Empty or documentation worksheets** load (you may plot nothing from them) and are labelled as such.
- **Hidden worksheets** in a workbook are listed and marked hidden.

### 19. Shapes of data

- **Long table** — one row per observation with a grouping column (bar, box, violin, strip, beeswarm, raincloud, histogram long form).
- **Wide table** — one column per group of unequal length (histogram *wide* form: `Input form → wide`, tick the columns), or a feature × sample **matrix** (heatmap, clustering, PCA, Matrix Workflow).
- **Precomputed differential results** — one row per feature with logFC, p, adjusted p (volcano, MA).
- **Survival** — one row per subject with time, 0/1 event and group; or a *precomputed* curve with one S(t) column per group.
- **Edge list** — source, target, weight (network). **Set membership** — one 0/1 column per set (UpSet). **Coordinates** — x, y, colour (embedding scatter).
- **Metadata** — one row per sample with group/batch columns (PCA colour/shape, Matrix Workflow groups).

### 20. In-app grouping without a metadata file

**🗂 Define groups…** (desktop) / **🗂 Define groups (no metadata file needed)** (browser):

- *Assign sample groups (wide matrix)*: choose the **Feature id column**, then type a group for each sample column (leave blank to exclude). **Auto-guess groups from names** (desktop) or the prefilled table (browser) uses shared name tokens (`Ctrl_1`, `Ctrl_2` → `Ctrl`). **Create grouped table** produces a long table `feature / sample / group / value` that flows into any plot.
- *Group by column values*: map the values of an existing column to group labels in a new column.

![Browser: the Define groups expander for a wide matrix.](../../assets/screenshots/streamlit_07_define_groups.png)

The grouped table is a new table; **↩ Revert to original data** restores the source.
