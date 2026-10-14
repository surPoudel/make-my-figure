# Axis scaling — log axes and tick notation (display only)

A log axis changes how values are **drawn**, never the values. On a log10 axis,
1, 10, 100 and 1000 sit at equal spacing, but the plotted data, every statistic,
every exported table and the Figure Package still hold 1, 10, 100, 1000. To analyse
log values instead, **transform** the data ([GENERAL_TABULAR_DATA.md](GENERAL_TABULAR_DATA.md)),
which adds a derived column. The two are deliberately separate:

| | Data transformation | Axis scale |
|---|---|---|
| What changes | the numbers (a new column) | how the axis is drawn |
| 1, 10, 100, 1000 become | 0, 1, 2, 3 | 1, 10, 100, 1000 at equal spacing |
| Statistics use | the transformed values | the original values |
| A mean marker shows | mean of the logs (= log of the geometric mean) | arithmetic mean of the raw values |
| Where | Data ▸ Prepare table | Style ▸ Axis scale & range |

## Controls

Desktop: **Axis scale & range (display only)** in the style panel. Browser:
**③ Axes & labels**. Spec keys in `layout` (a control left alone writes nothing):

| Key | Values |
|---|---|
| `x_scale`, `y_scale` | `linear` · `log10` · `log2` · `ln` (`log` = `log10`, `symlog` kept for old specs) |
| `x_tick_format`, `y_tick_format` | `auto` · `plain` (1, 10, 1,000) · `power` (10⁰, 10¹; log axes) · `scientific` (×10ⁿ at the end of a linear axis) |
| `x_minor_ticks`, `y_minor_ticks` | `true` · `false` |
| `x_min`, `x_max`, `y_min`, `y_max` | explicit range; blank = automatic |

**Scientific notation is not a log scale.** On a linear axis, `scientific` writes
1, 2, 3 with ×10⁶ at the axis end, and the spacing stays linear. `power` labels need
a log axis, and asking for them on a linear axis is reported.

Across several decades, ticks sit on powers of the base. Across less than about
1.5 decades (most measured responses), powers of the base would give one tick or
none, so ticks go at 1, 2, 5 × 10ᵏ instead, each labelled. A log axis looks the same
whatever its base; the base decides only where the ticks go.

## Refusals — reported, never silent

* A plotted value ≤ 0 (a log axis cannot show it). Keep a linear axis, or transform
  with an offset you can justify.
* A column that already holds log values (`log10(x)`, `log2FC`, `-log10 P`): a log
  axis would apply the logarithm twice.
* A minimum ≤ 0 on a log axis, a maximum not above the minimum, or a range that would
  hide a plotted value (a truncated axis overstates differences).
* A plot whose axis carries no magnitude (below).
* **Bars on a log axis** are drawn, with a note: a bar's length then depends on where
  the axis starts rather than on zero, so compare bar tops, or use a dot, strip or box
  plot.

Without a range set, a log axis refits its limits to the plotted values, including
error bars and statistics brackets, and then widens the range until significance stars
and other labels anchored to the data sit inside the axes. A bar chart's linear limits
start at 0, which a log axis cannot show.

A **linear** range on a bar chart still counts the bars' base: a minimum above it would
truncate the bars and overstate the differences, so it is refused.

Specs written before these controls existed may set `y_scale: "log"` or `"symlog"`
on any plot type. Those keep drawing exactly as they did then.

Axis limits are typed with a point for decimals (`1.5`), whatever the system locale.
On a comma-decimal system, `1,5` is refused rather than read as 15.

## Which plots

Generated from `styles/capabilities.py` (`AXIS_SCALE_AXES`, `AXIS_SCALE_REASONS`),
the single source the GUI and the render path both read.

| Plot | x axis | y axis |
|---|---|---|
| Bar plot with error bars | — | yes |
| Grouped bar plot with error bars | — | yes |
| Scatter plot | yes | yes |
| Box / violin plot with points | — | yes |
| Line / time-course with error band | yes | yes |
| Dot / strip plot | — | yes |
| Paired dot plot / slopegraph | — | yes |

Every other plot type, and why it has no axis scale:

| Plot | Reason |
|---|---|
| Clustered heatmap | a heatmap has no numeric axes; transform the values instead |
| Volcano plot | its axes are already log2 fold change and -log10 P; a log axis would log them twice |
| MA plot (differential expression) | its axes are already log-scale quantities; a log axis would log them twice |
| Manhattan plot (GWAS) | its y axis is already -log10 P |
| Q-Q plot (p-value / quantile) | its axes are already -log10 P quantiles |
| Enrichment dot plot | its x axis is already a ratio or -log10 P and its y axis lists terms |
| Kaplan-Meier survival curve | survival probability and follow-up time keep their linear meaning |
| Stacked composition bar plot | composition bars are proportions of a whole |
| Waterfall plot | waterfall bars are signed changes around zero |
| PCA scatter (matrix + metadata) | principal-component scores are signed coordinates |
| UMAP / t-SNE embedding scatter | embedding coordinates are positions, not magnitudes |
| Oncoprint mutation heatmap | an oncoprint has no numeric axes |
| Lollipop mutation plot | its axes are protein positions and counts per position |
| ROC curve | ROC axes are rates on [0, 1] |
| Precision-recall curve | precision and recall are rates on [0, 1] |
| Calibration plot | calibration axes are probabilities on [0, 1] |
| Confusion matrix | a confusion matrix has no numeric axes |
| Forest plot | use the forest plot's own 'Logarithmic axis' option (for ratio estimates) |
| Histogram (binned distribution) | use the histogram's own 'Logarithmic Y axis' option; a log x axis needs log-spaced bins — transform the values instead |
| Ridge / density plot | densities are estimated on the linear scale — transform the values instead |
| Raincloud plot | the density cloud is estimated on the linear scale — transform the values instead |
| Beeswarm plot | points are spread apart on the linear scale — transform the values instead |
| Dose-response curve | dose is already on a log axis and the fitted curve is defined on a linear response |
| Bland-Altman (method agreement) | differences between methods are signed values around zero |
| Hierarchical clustering dendrogram | dendrogram heights are merge distances, not magnitudes |
| Hierarchical clustering (heatmap + clusters) | clustering axes are not magnitudes |
| UpSet plot (set intersections) | an UpSet plot shows set intersections |
| Swimmer plot | swimmer bars are durations from a common start |
| Spider plot (longitudinal change) | spider plots show signed change from baseline |
| Sankey / alluvial flow (two-stage) | a Sankey diagram has no numeric axes |
| Network graph | a network diagram has no axes |
| Circos-style chord diagram | a chord diagram has no axes |
| Spatial map (categories) | spatial coordinates must keep their geometry |
| Spatial map (continuous value) | spatial coordinates must keep their geometry |
| Spatial transcript map | spatial coordinates must keep their geometry |
| Spatial ROI / region outlines | spatial coordinates must keep their geometry |
| Spatial composition glyphs | spatial coordinates must keep their geometry |
| Cellular-neighbourhood enrichment matrix | an enrichment matrix has no numeric axes |

## Presets, Figure Builder, packages

* **Style preset:** carries tick notation and minor ticks, which are appearance. It
  does **not** carry the axis scale or range, because those are choices about one
  dataset; a log axis must not ride a style preset onto the next figure. A **full**
  preset carries both.
* **Figure Builder:** a panel is re-rendered from its PlotSpec, so it keeps its log
  axis, notation and range (`tests/test_axis_scale_presets_and_builder.py`).
* **PlotSpec / Figure Package:** the keys round-trip through JSON, and two renders
  are byte-identical (`tests/test_axis_display_scaling.py`).

Implementation: `make_my_figure_core/plots/axis_scale.py`, applied once, centrally,
right after the renderer draws and before the label and canvas fitting passes, so
wider log tick labels are fitted like any other text.
