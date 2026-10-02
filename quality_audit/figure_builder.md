# The Multi-panel Figure Builder

Reported from the running app, with screenshots: the panel size controls "seem to
be too difficult to use", setting a panel's height "did not work", there is a
band of white space under a short panel, and the window cannot be scrolled so it
has to be maximised to reach the save buttons.

All four were real. Three are fixed; the fourth is measured and open.

## 1. The window could not be made short enough to fit the screen

Not "no scrollbar" - worse. The dialog's `minimumSize()` was **532 x 902 px**, so
it could not be shrunk below 902 px tall. On a 1366x768 laptop (710 px usable)
the bottom **192 px is below the edge of the display**, and maximising cannot
make a screen taller. It misses a 1440x900 MacBook Air by 62 px. Stranded down
there: the legend and panel-letter font spinners, and all three of
*Save figure… / Save Figure Package… / Close*.

Worth recording because it defeats the obvious test: **no widget was unreachable
*inside* the dialog**. Qt grew the window rather than clipping its contents, so
an audit that walked widget rectangles would have found nothing and called the
report unreproducible. The number that matters is `minimumSize().height()`.

| | before | after |
|---|---|---|
| dialog minimum | 532 x **902** | 570 x **136** |
| 1366x768 laptop | 192 px off-screen | fits |
| 1440x900 MacBook Air | 62 px off-screen | fits |
| widgets below their own minimum | 13 | 0 |
| blocking findings (`figure_builder_ux.py`) | 53 | 0 |

The left column is now a `QScrollArea` with ~374 px of real scroll - which is
precisely the height that used to be squeezed out of the form rows, flattening
every combo and spinner 21-26% below its minimum (17 px against 22). That
squeezing is what the screenshots show as overlapping, half-clipped text. The
action buttons are pinned outside the scroll area, and the default size is
1240x900 clamped to the available screen instead of a fixed 980x640.

## 2. Setting a panel's height did nothing

Measured on the reported 2x2 (A volcano, B bar, C heatmap, D lineplot):

| D `height_in` | D drawn | D's cell empty |
|---|---|---|
| auto | 2.97 x 2.06 in | 53.8% |
| 3.5 | 2.97 x 2.06 in - **identical** | 53.8% |
| 6.0 | 2.97 x 2.06 in - **identical** | 59.4% - *worse* |

`height_in` only fed `row_h = max(panel heights in the row)`. The panel image was
then fitted to the cell's **width** at its own aspect, so the drawn height was
always `cell_width x aspect` whatever was typed. Raising it past the heatmap's
height only made the row - and the dead space - bigger.

**The fix is to honour the request where it can be honoured: at render time.** A
finished raster can only be scaled, and scaling returns the shape it already had.
But a panel still carries its PlotSpec, so it is re-rendered on a canvas of the
requested size. The axes grow; the data is not stretched.

One more step was needed on top of that. `_figure_to_image` rasterised with
`bbox_inches="tight"`, which crops straight back to the content - a panel
rendered on a 3.2 x 4.5 in canvas came back as an image of aspect 0.77 instead of
1.41, so "4.5 inches tall" still drew 2.46. The trim is now off for panels whose
size was explicitly asked for; the whitespace kept is the plot's own margin at
the size requested, which is what the user is buying.

Result on the reported figure - D's cell goes from **54.0% empty to 0.9%**:

| | D drawn | D's cell empty |
|---|---|---|
| auto | 2.68 x 1.86 in | 54.0% |
| height 5 in | 2.68 x 4.19 in | **0.9%** |
| **Fill the cell** | 2.63 x 4.04 in | **1.9%** |

`fill_cell` is the new one-click answer: the panel is re-rendered at its cell's
true size, so it fills the space with square pixels. Off by default - keeping a
panel's proportions stays the default everywhere, because a stretched scientific
figure is a distorted one. A panel that *cannot* be re-drawn (an imported image)
is stretched only if explicitly told to, and says so; a height it cannot reach is
capped with a warning instead of inflating the row into more white space.

Sizes remain **approximate**: the drawn panel is about 0.85x the number typed,
because the composite's figure size and the gridspec margins double-count. The
ratio is exact - double the request, double the draw - and the help text now says
so. Making inches literal would resize every existing composite by ~19%.

## 3. Still open, and measured: type is not uniform across panels

Each panel is rendered once and then scaled to fit its cell **by a different
factor**, so the "Fonts (points, applied to all panels)" controls set the same
point size in every render and the compositor then scales them apart.

Per-panel image scale on the reported 2x2 (higher = more downscaled = smaller
drawn text):

| | A, B, C, D | spread |
|---|---|---|
| auto | 1.84, 1.56, 1.56, 1.56 | 1.18x |
| D height 5 in | 1.84, 1.56, 1.56, 1.19 | 1.54x |
| D fill cell | 1.84, 1.56, 1.56, 0.97 | **1.90x** |

So a 10 pt label in panel D is drawn nearly twice the size of the same 10 pt
label in panel A. It is visible in `reports/figure_builder/2x2_D_fill_cell.png`.
This is **pre-existing** - the spread is already 1.18x with nothing set - but the
new size controls widen it, because changing one panel's size changes only that
panel's scale.

The fix is a second render pass: once the grid is known, re-render every
resizable panel at its final drawn size, so every scale is 1.0 and the font
controls mean what they say. It costs one extra render per panel on a preview
that redraws on every edit, and it changes the look of every existing composite,
so it is written down here rather than slipped in.

## Instrument

`quality_audit/figure_builder_ux.py` opens the dialog headlessly at several
window sizes and reports unreachable, compressed, clipped and overlapping
widgets, plus whether the dialog fits on common screens. It exits non-zero on a
blocking finding, and refuses to report at all if its own self-test does not fire
every check - a zero from a dead instrument is worthless. Five check designs were
tried and discarded as unreliable before it settled; they are listed in
`figure_builder_ux.md`, including one that produced 19 false "unreachable"
findings against a working scroll area because Qt's `ensureWidgetVisible` scrolls
to a spin box's text-cursor rectangle rather than to the widget.
