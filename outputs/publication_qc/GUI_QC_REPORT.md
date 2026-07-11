# GUI QC report

## Desktop (PySide6) — ⚠️ unverified in this environment
The sandbox has no Qt system libraries (`libxkbcommon`/`libEGL`) and no sudo, so
the desktop app cannot launch headless here. What IS verified:
- Non-GUI controller logic (`DesktopController`) renders every example for all 37
  plot types (`test_desktop_controller`).
- Pop-out/dock manager logic has Qt-guarded tests (`test_pop_out_panels`:
  register / pop-out / dock / dock-all / reset / QSettings persistence) that run
  in a real Qt environment; they skip cleanly here.
- The pop-out integration in `main.py` is additive and guarded (a failure cannot
  block app startup); all edited files byte-compile.

**Manual checks required before release** (run `python -m apps.desktop_app.main`):
launch; Home / Upload New Data; replace example with uploaded data without
restart; no stale figure after a validation error; figure toolbar works;
View → Pop Out Figure / Data / Controls and dock back (toolbar still works, state
preserved); Reset Layout; export uses the current figure.

## Streamlit — ⚠️ skipped in this sandbox (streamlit not installed)
`test_app_smoke` skips without streamlit. Where streamlit is installed it drives
the app in-process across all plot types. New v0.5 plot types + options appear
automatically (the GUIs read `ui_hints`). No native pop-out is claimed in
Streamlit (documented as desktop-only).

## Recommendation
Desktop pop-out and both app launches should be smoke-tested by a human on a
machine with Qt + streamlit installed before publishing. Everything that can be
verified headlessly passes.
