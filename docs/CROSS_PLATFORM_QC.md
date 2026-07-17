# Cross-platform QC runbook

Run this on **each** target OS (Mac, native Windows, WSL/Linux, Linux) and compare
the generated reports. We do **not** compare pixels across platforms (fonts/backends
legitimately differ) — we compare render success, artifact presence, element counts,
statistics values, and the absence of forbidden style labels.

## Confirm you are running the pulled code

Every app shows a build banner (Streamlit sidebar; desktop status bar):

```
🔖 Make My Figure vX.Y.Z · <commit> · <platform> · <backend>
```

If the **commit** does not match your pulled `git rev-parse --short HEAD`, a stale
installed package is shadowing the repo. Fix with an editable install from the repo:

```bash
python -m pip uninstall make-my-figure        # remove any stale install
python -m pip install -e .                     # editable install of THIS checkout
```

## Commands

### macOS
```bash
python -m pytest -q
python scripts/run_cross_platform_qc.py --output reports/release_cross_platform_qc/mac
streamlit run apps/streamlit_app/streamlit_app.py --server.fileWatcherType none
python -m apps.desktop_app.main
```

### WSL / Linux
```bash
python -m pytest -q
QT_QPA_PLATFORM=offscreen python -m pytest -q      # if Qt GUI tests are present
python scripts/run_cross_platform_qc.py --output reports/release_cross_platform_qc/wsl
streamlit run apps/streamlit_app/streamlit_app.py --server.fileWatcherType none
```
> `python -m pytest -q` may fail to *collect* if the `pytest-qt` plugin can't load Qt
> (missing `libEGL.so.1`). Install the Qt runtime libs (`sudo apt-get install libegl1
> libxkbcommon0 libxcb-cursor0`) or run `python -m pytest -q -p "no:pytest-qt"
> --ignore=tests/test_desktop_gui.py`.

### Native Windows (PowerShell)
```powershell
python -m pytest -q
python scripts\run_cross_platform_qc.py --output reports\release_cross_platform_qc\windows
streamlit run apps\streamlit_app\streamlit_app.py --server.fileWatcherType none
python -m apps.desktop_app.main
```

## Comparing reports across platforms

Each run writes to its `--output` folder:
- `platform_manifest.json` — version, commit, package versions, backend, platform.
- `qc_summary.csv` — one row per plot type (render/export status, element counts, font).
- `qc_report.md` — human summary.
- `<plot_type>/` — PNG/PDF/SVG + PlotSpec sidecar (local only; not committed).

Compare `qc_summary.csv` between platforms: `render_status`, `export_*`, `n_axes`,
`n_legend_labels`, and `forbidden_style_label` should match. Small font differences
are expected (Arial vs fallback).

## Confirm only Publication style appears
```bash
python -c "from make_my_figure_core.styles.engine import list_profiles; print(list_profiles())"
# -> ['publication']  (plus only 'publication*' learned profiles, never journal names)
```

## Confirm network interaction_type colors
Map an edge table with an `interaction_type` column; edges should show multiple hues
with a legend of all categories. Auto-detected; override with `edge_color_by`.
See [NETWORK_GRAPH.md](NETWORK_GRAPH.md).

## Clear Streamlit cache / stale state
- In the app: the sidebar **Reset / Upload new data** clears session state.
- On disk: `streamlit cache clear`.
- Restart with `--server.fileWatcherType none` on synced folders (OneDrive/`/mnt/c`).

## Performance
`/mnt/c` and OneDrive are slow under WSL for file I/O. For active work, keep the repo
and data on the **Linux filesystem** (`~/…`). App-side, expensive diagnostics/stats
run behind explicit **Run/Generate** buttons and are cached by spec hash, so they do
not recompute on every widget change. See
[reports/release_cross_platform_qc/performance_report.md](../reports/release_cross_platform_qc/performance_report.md).
