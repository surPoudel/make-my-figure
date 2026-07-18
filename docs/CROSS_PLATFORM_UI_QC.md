# Cross-platform UI QC runbook

Qt GUI behavior must be verified on each OS (it can't be exercised headless). Confirm
the build banner shows the pulled commit first (Streamlit sidebar / desktop status bar).

## Commands
### macOS / native Windows
```
python -m pip install -e ".[desktop]"
python -m pytest -q
python -m apps.desktop_app.main
```
### Linux / WSL
```
python -m pip install -e ".[desktop]"
QT_QPA_PLATFORM=offscreen python -m pytest -q
# WSL desktop also needs Qt system libs (see docs/CROSS_PLATFORM_QC.md).
```
Streamlit (any OS): `streamlit run apps/streamlit_app/streamlit_app.py --server.fileWatcherType none`

## Manual checklist (per OS)
- [ ] build banner shows the pulled commit
- [ ] plot type defaults to "— Choose a plot type… —" (no auto Bar)
- [ ] Style shows only "Publication"
- [ ] "Matrix workflow…" button label fully visible (not clipped)
- [ ] recommendation cards are readable / scroll, not truncated
- [ ] left control pane scrolls vertically; labels not clipped
- [ ] splitter resizes; sizes persist and stale sizes reset sensibly
- [ ] data preview: headers show full name on hover, columns resizable, not over-wide
- [ ] Home / new dataset returns to the placeholder (clean) state
- [ ] no clipped text at 100% / 125% / 150% / 200% scaling and on Retina
