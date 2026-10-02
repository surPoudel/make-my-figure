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

## 3. Type is now uniform across panels

Each panel was rendered once and then scaled to fit its cell **by a different
factor**, so the "Fonts (points, applied to all panels)" controls set one point
size in every render and the compositor scaled them apart. A 10 pt label in one
panel was drawn nearly twice the size of the same 10 pt label in another.

Per-panel image scale (higher = more downscaled = smaller drawn text):

| | A, B, C, D | spread |
|---|---|---|
| before, auto | 1.84, 1.56, 1.56, 1.56 | 1.18x |
| before, D height 5 in | 1.84, 1.56, 1.56, 1.19 | 1.54x |
| before, D fill cell | 1.84, 1.56, 1.56, 0.97 | 1.90x |
| **after** | 1.00, 1.00, 1.00, 1.00 | **1.001x** |

Three steps were needed, and the middle one is the reason this is written down.

**A second render pass.** Once the grid is known, every panel that still carries
its PlotSpec is re-drawn at the exact box it is about to occupy, so the image is
placed 1:1 and a point of type in a panel is a point on the page.

**That alone made the figure worse.** The first render after the change came back
with panel A's title wrapped onto three lines, panel B's y-label clipped to
"measurement (mean ± SE" and panel C's sample names overlapping. The build
warnings said why: the canvas-responsive type scaling - correct for a standalone
figure, and the right answer to a 2 x 1 in panel - is **per panel**, and it had
scaled each panel's type by a different amount: **69% / 71% / 98% / 66%**. That
is the same defect by another route, and it would have shipped as a fix. A
composite sets one size for the whole figure, so composite panels now opt out
(`layout["scale_typography"] = False`) and their points are literal. A standalone
figure still scales to its canvas, pinned by a test.

**The defaults had to come down.** 11/12/10/10 pt were the right numbers when
every panel was silently shrunk ~1.56x - 10 pt arrived as about 6.4 pt. Now the
number is the number on the page, and a three-inch journal panel wants 6-8 pt, so
the defaults are text 7.0 / axis 7.5 / tick 6.5 / legend 6.5. The panel letter
stays at 14 pt: it is drawn on the composite, so it was never scaled.

**Migration, deliberately not automatic.** A composite saved before this recorded
`base_font_pt=11` and will now render that as a literal 11 pt - visibly larger.
Lowering the numbers to around 7 restores the old look. Old values are *not*
silently multiplied by 0.64: a magic rescale buried in a loader is far harder to
reason about later than a one-time adjustment the author makes on purpose.

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
