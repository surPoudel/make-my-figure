# Known documentation limitations

Version documented: **1.1.0** (release branch `release/v1.1.0-integration`; initial run 2026-09-03 at commit `ac49ff8`, re-verified and screenshots recaptured 2026-09-06). Everything below is a boundary of *this documentation run*, stated so that a reader knows what was and was not verified.

## Environment used for verification

- All screenshots and workflow validations were produced on **Linux (WSL 2)**. The desktop app was driven on Qt's **offscreen** platform (no window manager, default Fusion-like widget style) and the browser app in **headless Chromium**. On macOS and Windows the widgets are drawn by the native style, so spacing, fonts and control shapes differ from the screenshots; the labels and layout are the same.
- No screenshot was taken on macOS or Windows, and no packaged installer (`.dmg`, `.exe`, `.AppImage`) was run. Installer instructions come from the build scripts and the CI build logs of the v1.1.0 installers (which pass their `--selftest` on the macOS, Windows and Linux runners); the installation-error table for macOS reflects errors reported by a collaborator and reproduced by reasoning, not by running on a Mac here.
- Emoji glyphs in a few button labels depend on an installed emoji font; on the capture machine one had to be installed. They are decoration only.

## Observed UI defects that the manuals describe rather than hide

- Desktop group titles that contain an ampersand — **1. Plot type & style**, **4. Labels & size**, **③ Axes & labels**, **⑤ Recommend & generate** — render with a Qt mnemonic artefact (the `&` is consumed and the next letter is underlined/shown as `_`). Visible in several screenshots. Cosmetic; not fixed in this documentation pass.
- **Help → About** reports `commit unknown` while the status-bar banner and the browser sidebar show the real commit; they use different lookup paths. The manuals direct users to the banner.
- The browser app always submits every style token, so plot types without markers, lines or legends (e.g. a bar plot) show several informational "style control … was ignored" notices under the figure even at default settings. Documented as informational.

## What was validated, and how

- **22 documented workflows** were executed headlessly (`docs/manuals/audit/manual_instruction_validation.csv`): core API, desktop controller, offscreen `MainWindow`, and Streamlit `AppTest`. "Click X" instructions were executed through the same code path the button calls, not by simulating a mouse.
- **34 screenshots** were captured from the running apps on bundled synthetic data; **13** were opened and inspected individually (the ones the text describes in detail); the rest were captured by the same driver and referenced with generic captions (`screenshot_inventory.csv`, column `ui_match`).
- The **plot catalogue** (Part X) is generated from the registry, the option registry and the capability scan; its prose "Purpose / When to use / Known limitations" lines are hand-written and reviewed, not generated.

## Not documented or not verifiable here

- The optional `count-de` extra (PyDESeq2) and the `import-panels` extra (PyMuPDF/cairosvg vector import) were not exercised; the manual states what they are and how to install them only.
- Pop-out panel behaviour on multiple monitors was not exercised (offscreen has one virtual screen).
- No performance numbers were measured; Part XX gives qualitative guidance only.
- Drag-and-drop of files onto the desktop window was read from code (`dropEvent`), not exercised.
- Preset library paths for macOS and Windows follow the code's platform branches and were not created on those systems.

## Documentation build

- DOCX is produced by pandoc; PDF by PyMuPDF's Story engine (no LaTeX/HTML-to-PDF engine is available). The PDF has a title page, a contents section with page references counted from the first body page, page numbers, figure numbers and an outline; typography is deliberately plain.
- Screenshots are downscaled inside the PDF to fit a page; the full-resolution PNGs are in `docs/manuals/assets/screenshots/`.
- The Quick Start is 14 PDF pages with 14 figures; the User Manual is about 80 PDF pages with 72 figures at this commit (exact counts are printed by `scripts/build_manuals.py`).

## Rebuilding

```bash
python scripts/manual_capture_desktop.py        # QT_QPA_PLATFORM=offscreen; needs PySide6
python scripts/manual_capture_streamlit.py      # needs a running streamlit on :8501 and Playwright Chromium
python scripts/build_plot_catalog_part.py       # Part X from the registry
python scripts/manual_validate_instructions.py  # manual_instruction_validation.csv
python scripts/manual_screenshot_inventory.py   # screenshot_inventory.csv
python scripts/build_manuals.py                 # Markdown -> DOCX + PDF
```

Nothing in `docs/manuals/` was committed, pushed, tagged or released by the documentation run.
