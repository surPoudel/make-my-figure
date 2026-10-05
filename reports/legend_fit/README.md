# Legend fitting — before and after

Four of the eleven plot types that clipped a legend in their **default** output.
No unusual request involved: this is what opening the example produced.

`__before` is rendered with the fitting pass stubbed out, `__after` with it live.

In `scatterplot_with_regression__before.png`: the key reads "Respon…" and
"Non_res…", the fit-statistics box is cut off on the left, and the x-axis label
`x_marker` is missing off the bottom. All three are back in the `after`, and the
plot area is the same size — the canvas grew rather than the data area shrinking
to pay for the key.

## Why it lasted

The legend is positioned relative to the axes, not the figure, so a long label
runs past the canvas edge. Exporting with a tight bounding box crops to the
content and looks correct, which is exactly what hides it. The preview, and any
export at a declared size, is where it shows.

## What the fix does

`fit_content_to_canvas` in `plots/base.py`, applied once in `registry.render`
after every other layout pass:

- **nothing pinned** → grow the canvas, holding the axes at their original inches;
- **a size pinned** → pull the subplot area in instead, because a figure fitted to
  a journal column cannot be widened and a slightly smaller plot beats a cropped
  key;
- **neither is enough** → say so, naming how much still falls outside, rather than
  cropping in silence.

Four plot types still cannot fit an eight-entry key beside a 4 x 2 in panel. They
report it; they are listed as `NO_ROOM_AT_4X2` in
`tests/test_legend_fits_the_canvas.py`.
