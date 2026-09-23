# Styling and annotations

Appearance is controlled in three places, all in the control column.

## 4. Labels & size

*Title*, *X label*, *Y label* (free text; empty means the column name is used), *Figure width*
(default / single / onehalf / double), *Raster DPI*, and *Point picking* - the checkbox
**Click a point to identify / label it**. With it ticked, clicking a point in the preview
labels it with the plot's **label** column; labels can then be dragged.

## 5. Publication style

Five groups: **① Figure margins**, **② Typography** (font sizes for title, axis labels, ticks,
legend, annotations), **③ Axes & labels** (spines, ticks, grid, label rotation), **④ Legend**
(position, frame), **⑤ Colorbar (heatmaps etc.)**. **Reset to publication defaults** restores
the single Publication style. The application ships one style and does not claim compliance
with any journal (Help > Publication style disclaimer).

## 3. Options

Plot-specific appearance and semantics: kind, point size, colours by class, cutoffs, label
counts, colormap, clustering, curve style ... The set depends on the plot type; the plot
tutorials list the ones that matter.

## Annotations

* Statistics annotations (brackets, stars, P values, text) come from **6. Statistics**.
* Point labels come from the **label** role plus *Show labels* / *Top N labels* options where the
  plot has them (volcano, MA, lollipop, scatter), or from point picking.
* Group colour strips for heatmaps come from **Define groups...**.

## Publication QC

The **Publication QC** button scores the current figure for readability (minimum text size,
overlapping labels, legend over data, exported width) and lists suggested fixes; the status bar
shows *Publication check: passed* when nothing is flagged.

## Save the look

Once the figure looks right, **Figure preset > Save preset...** (style only) captures ①-⑤,
the labels-and-size choices and legend/export settings for reuse on other data
(see [figure presets](../10_Figure_Presets/figure_presets.md)).
