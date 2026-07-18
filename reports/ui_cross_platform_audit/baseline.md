# Cross-platform UI audit — baseline & findings

## Environment (this session)
- Repo on WSL/Linux (/mnt/c). Qt cannot load headless here (libEGL/libxkbcommon
  absent) — the desktop GUI, offscreen Qt, and screenshots could NOT be run/produced
  in this session. Fixes are code-level, verified by parse + GUI-free controller
  import + static source checks; **live macOS/Windows verification is required.**
- App version 1.0.0rc1; audited from commit 1470d47.

## Root causes (from the macOS screenshot)
1. "Matrix workflow…" clipped: three top-nav buttons in a horizontal row inside a
   control pane hard-capped at `setMaximumWidth(480)` — the third button clipped.
2. Left pane too narrow / recommendation card truncated: same 480px cap, plus the
   recommendations panel's nested QScrollArea had no minimum height, so cards were cut
   mid-sentence.
3. Data preview very wide columns / truncated headers: no per-column width cap and no
   header tooltips.
4. Windows "defaults to Bar": the Streamlit app set `default_plot_type =
   available_plot_types()[0]` on upload and had no placeholder option — it auto-selected
   and rendered the first (bar) plot. The desktop already reset to a placeholder on
   every upload, so the two frontends disagreed.

## Fixes
- Nav buttons stacked vertically (full labels at any width/DPI).
- Removed the 480px max-width cap; left pane min 340, width driven by the splitter
  (proportional [400,820] default) with stale-size validation on restore.
- Recommendation nested scroll given a 240px minimum height.
- Preview: header tooltips (full name), user-resizable columns, per-column width caps
  (first columns wider, sample columns narrower).
- Streamlit: placeholder "— Choose a plot type… —" prepended + default; render gated
  until a real plot is chosen (no auto-bar). Shared placeholder/style/action strings
  moved to make_my_figure_core/ui_strings.py used by both frontends.

## Not done / needs live verification
- No screenshots or offscreen Qt run possible here — the visual result on macOS
  Retina / Windows scaling must be confirmed on-device.
- The desktop Qt geometry test harness (Phase 10) requires a working Qt; added
  source-level guardrail tests instead (tests/test_ui_consistency.py).
