# Pop-out / pop-in panels (v0.5, desktop app)

The desktop app lets you **detach** major workbench panels into floating windows
— move them to a second monitor, resize them — and **dock** them back to their
original position without losing any state (data, PlotSpec, StatsSpec,
annotations). The *same* widget instances are reparented, never recreated, so
the live Matplotlib canvas (and its toolbar/export) keeps working when detached.

## Panels you can pop out
- **Figure** — the live canvas + toolbar.
- **Data & Messages** — the data preview and validation/warning tabs.
- **Plot Controls** — the mapping/options/style/statistics column.

(The statistics and annotation controls live inside the Plot Controls column, so
they travel with it. The RNA-seq workflow panel is not present in this
figure-first build.)

## How to use
**View menu:**
- **Pop Out Figure**, **Pop Out Data Table**, **Pop Out Controls** — toggle a
  panel between docked and floating.
- **Dock All Panels** — return every floating panel.
- **Reset Layout** — dock everything and restore default splitter sizes.

Each floating window has a **⮊ Dock back** button; **closing** a floating window
also docks its panel back (state preserved).

## Multiple monitors & persistence
Floating panels are ordinary OS windows (movable across monitors, resizable, not
always-on-top). Their size/position is remembered via `QSettings`
(`panel_geo/<key>`), and which panels were floating is saved on exit
(`panel_floating`). On quit, any floating panels are docked back so no orphan
windows are left.

## Implementation notes
This is an **additive** manager (`apps/desktop_app/panels_dock.py`,
`PanelManager`) that reparents widgets between their home `QSplitter` slot and a
floating `QWidget` window; it does **not** convert the workbench to
`QDockWidget`s, so it cannot disturb the existing splitter layout. Registration
and the View actions are guarded — if anything fails, the app still starts with
pop-out simply unavailable.

## Limitations
- Statistics/annotation panels are not *individually* detachable in v0.5 (they
  pop out with the Controls column).
- Streamlit (the web app) cannot open native OS windows; use the desktop app for
  the full multi-monitor pop-out workflow. In Streamlit, use the browser's own
  new-tab / full-width view for a larger figure.
