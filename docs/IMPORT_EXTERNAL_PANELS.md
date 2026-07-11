# Import external panels into the Figure Builder (v0.5)

You can assemble a publication multi-panel figure from **existing figures on your
computer** — exports from R, Python, GraphPad Prism, Illustrator, BioRender,
microscopy/flow/sequencing software — placed alongside plots generated inside
Make My Figure. Each imported file becomes a panel (A, B, C, D, …).

## How to import (desktop app)
1. Open the **Multi-panel Figure Builder** (save at least one plot as a panel, or
   start empty).
2. Click **“Import panel from file…”** and pick a file.
3. The imported panel is added to the list with a live preview; set its label,
   title, approximate size, crop/fit, border, and annotations like any panel.
4. Reorder / mix it with generated panels, then **Save figure…**.

> The Figure Builder (including imported panels) is a **desktop-app** feature.
> The Streamlit app focuses on single-plot workflows.

## Supported formats
| Format | Support | Notes |
|---|---|---|
| PNG, JPG/JPEG, TIFF/TIF, WEBP, BMP | ✅ always | loaded via Pillow |
| PDF | ✅ if **PyMuPDF** (`pip install pymupdf`) is installed | first page by default; page selectable; **rasterized** at a chosen DPI |
| SVG | ✅ if **cairosvg** (`pip install cairosvg`) is installed | otherwise a friendly message asks you to export PNG/PDF; **rasterized** when supported |
| EPS | ❌ not enabled | no reliable dependency-free converter; export to PDF/PNG instead |

Unsupported or unreadable files never crash the app — they return a clear message.

## Vector vs raster — read this
The multi-panel composite embeds **every** panel (including Make My Figure's own
plots) as a raster image at the panel DPI; only panel **labels and manual
annotations** stay vector. So imported **PDF/SVG panels are rasterized** at a high
DPI (default 300) and this is recorded in the FigureSpec. If you need a fully
vector panel, keep that panel as a separate vector file and assemble in
Illustrator/Inkscape. This is stated honestly rather than implying vector is
always preserved.

## Layout & edit controls (imported panels)
- **Panel label / title**, approximate **size** (inches).
- **Fit mode:** `contain` (preserve aspect, default), `fill`, `crop`, `stretch`
  (distorts — you get a warning).
- **Crop margins** (top/bottom/left/right fractions) and **auto-trim** white margins.
- **Rotate** 90/180/270, **flip** horizontal/vertical.
- **Background** white or transparent; **border** on/off + width.
- Works with automatic grid, custom rows/columns, width/height ratios, and A/B/C/D
  labels — the same as generated panels.

## Publication-readiness warnings
The builder warns when an imported panel is likely to look bad in print, e.g.:
- “Imported image is 900 px wide. At 3 in that is ~300 DPI; at 6 in that is 150 DPI.”
- “PDF/SVG rasterized at 300 DPI (vector not preserved in the composite).”
- “Panel is being stretched non-proportionally; this may distort the figure.”
Aim for imported rasters that give **≥300 DPI** at your target panel width.

## Annotations on imported panels
The universal annotation layer works on imported panels using **normalized panel
coordinates** (x, y from 0 to 1), so annotations reproduce at any panel size: add
text, arrows, callouts, boxes/regions, and brackets. They are stored in the
FigureSpec and exported as vector text/shapes.

## Assets & reproducibility
On import, the file is **copied into a managed assets folder**
(`figure_builder_assets/`) so the panel survives you moving/deleting the original.
The FigureSpec stores, per imported panel: original filename, stored asset
**basename** (never a private absolute path), file type, **SHA-256**, original
width/height, DPI, PDF page, rasterization DPI, crop/fit/rotate settings, panel
label/title, and any warnings. On **Save**, the assets are copied next to the
exported figure. **Keep the `figure_builder_assets/` folder with the FigureSpec
JSON** — reloading the FigureSpec restores imported panels from those assets.

## Export
The composite exports to **SVG / PDF / PNG** plus the **FigureSpec JSON**. Panel
labels and annotations stay vector/editable; imported raster/rasterized-vector
content appears at its resolution. Nothing is clipped (tight bounding box).

## Limitations
- Imported PDF/SVG are rasterized in the composite (see above).
- SVG/PDF import needs an optional converter (cairosvg / PyMuPDF); without it you
  get a clear message, not a crash.
- EPS is not enabled.
- Full crop/edit controls are in the desktop app; Streamlit has no Figure Builder.
