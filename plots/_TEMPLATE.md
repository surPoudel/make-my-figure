# <Plot display name>

<!-- Copy this file to tutorial/plots/<plot_id>.md. Keep every heading; delete a section only
     when it does not apply (say so in one line rather than leaving it empty). Every UI label in
     backticks must be the label the application shows today; the validation run checks the
     dataset, the plot type, each column role, the options used and every export. -->

## What this plot shows

Two to four plain sentences.

## Example question

One realistic question a scientist would ask.

## Required data

| column | role in this tutorial | example values |
|---|---|---|
| ... | ... | ... |

Dataset: `tutorial/datasets/<file>.csv` (simulated; no biological meaning).

## Open the data

1. Start Make My Figure. On the start screen click **Open data file** (or use *File > Open data file...*, or drop the file onto the window).
2. Choose `<file>.csv`. The **Data preview** tab shows the table; the line under it lists the detected type of every column.

## Map the columns

Under **2. Map columns** the application proposes roles. Check them; change any row.

| column | role |
|---|---|
| `<column>` | **<role row>** |

## Create the plot

Under **1. Plot type & style** choose **<display name>** and click **Update preview** (the preview also updates on its own after each change).

## Customize

Only the controls that matter for this plot.

## Statistics

Which tests apply, which settings were used in the tutorial, what appears on the figure. If none applies, one sentence saying so.

## Annotation

If applicable.

## Figure Preset

Whether a style preset transfers to this plot type and what it carries.

## Save / reproduce

`Export PlotSpec JSON` for the specification, **Save Figure Package (.mmfpackage)** for specification plus frozen data.

## Export

Formats used in the tutorial and where the buttons are.

## Common mistakes

Two to five real pitfalls seen with this plot.

## Result

![final](../screenshots/<tutorial_id>/06_final_plot.png)

Video: see `tutorial/videos/video_links.json` (`VIDEO_URL_<ID>`).
