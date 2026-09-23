# Export

Everything you can write out is under **5. Export** in the control column (and in the File
menu). The buttons, top to bottom, as the application shows them:

| button | writes |
|---|---|
| **Export SVG** | vector figure, text kept as text |
| **Export PNG** | raster figure at the *Raster DPI* set under 4. Labels & size (300 by default) |
| **Export PDF** | vector figure with embedded fonts |
| **Export PlotSpec JSON (specification only)** | the specification and render metadata; no data |
| **Save Figure Package (.mmfpackage)** | specification + frozen data + statistics + previews |
| **Export all as ZIP** | SVG, PNG and PDF, the PlotSpec, and the figure package in one archive |
| **Save template (example table)** | an empty table with the columns this plot type expects, to fill in |

Each button opens a file dialog whose proposed name is built from the table name and the plot
type (and the worksheet name for Excel workbooks). The exported figure is the preview as it
stands, including statistics annotations.

Figure size: **Figure width** under 4. Labels & size offers *default*, *single*, *onehalf* and
*double* column widths; the preview keeps that aspect. The **Publication QC** button (above
5. Export) lists readability issues such as small text or overlapping labels before you export,
with one-click fixes where they exist.

From the Figure Builder, **Save figure...** writes the composite in PNG, PDF and SVG at the
builder's *Export DPI*, and **Save Figure Package...** writes the composite package.

## Common mistakes

* Exporting PNG for a journal that asks for vector: use PDF or SVG.
* Changing the DPI after exporting and expecting the earlier file to change.
* Sending a PlotSpec when the recipient needs the figure: send the PDF, or a figure package.
