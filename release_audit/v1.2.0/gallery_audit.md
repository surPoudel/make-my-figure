# v1.2.0 gallery audit (Phases 5-6)

45 registered plot types, read from the live registry.

Per plot type: default render, publication-style render, layout QC (clipped text, overlapping text, legend over data, minimum font), PNG/SVG/PDF export, PlotSpec round-trip and Figure Package round-trip re-rendered from the frozen data.

**Result: 39 of 45 clean; 6 with failures.**

## Failures

- **bland_altman_plot**
  - `overlap`: FAIL 3 pairs
- **dose_response_curve**
  - `overlap`: FAIL 1 pairs
- **ma_plot**
  - `overlap`: FAIL 1 pairs
- **pca_scatter_from_matrix**
  - `overlap`: FAIL 1 pairs
- **stacked_bar_composition**
  - `overlap`: FAIL 29 pairs
- **volcano_plot**
  - `overlap`: FAIL 1 pairs

## Reported, not gating: legend drawn over data

A key placed inside the axes can sit on the data; on a dense plot that is a judgement call, so it is recorded rather than failed.

- lineplot_timecourse_with_error_band
- manhattan_plot

## Reported, not gating: a drawn scale with no name

These axes draw tick labels but carry no axis label. Whether that is a defect depends on the plot type, so it is recorded rather than failed.

- enrichment_dotplot (ax0.y)
- forest_plot (ax0.y)
- oncoprint_mutation_heatmap (ax0.y)
- upset_plot (ax1.y,ax2.y)

Full per-plot measurements: `gallery_audit.csv`.

## Adjudication of the six remaining overlaps (release lead, 2026-10-05)

Whether these are regressions was settled by measurement, not judgement: v1.1.1's
renderers were rendered in a `v1.1.1` worktree and measured with **this** release's
instrument, so the only variable is the renderer vintage.

| plot | v1.1.1 | v1.2.0 | verdict |
|---|---|---|---|
| `stacked_bar_composition` | 29 pairs | 29 pairs | pre-existing, unchanged |
| `bland_altman_plot` | 3 pairs | 3 pairs | pre-existing, unchanged |
| `dose_response_curve` | 1 pair | 1 pair | pre-existing, unchanged |
| `pca_scatter_from_matrix` | 1 pair | 1 pair | pre-existing, unchanged |
| `ma_plot` | 6 pairs + **2 clipped** | 1 pair, 0 clipped | **improved** |
| `volcano_plot` | 4 pairs | 1 pair | **improved** |
| `lollipop_mutation_plot` | 0 pairs | 0 pairs | regressed to 1 in this line; **fixed** |
| `network_graph` | 1 pair | 0 pairs | regressed to 2 in this line; **fixed, now better than v1.1.1** |

Nothing ships with more overlapping text than v1.1.1 had, and two plot types ship
with materially less.

### Why the six are not being fixed in v1.2.0

Five of them (`bland_altman` ×3, `dose_response`, `pca_scatter`, `ma_plot`,
`volcano`) are one shared situation: the leftmost x tick label meets the lowest y
tick label at the corner of the axes, overlapping by 3-8 px. Clearing it means
changing tick selection or axis padding on all 45 plot types, which moves every
render fingerprint in the suite. That is not a change to make late in a release
for a pre-existing few pixels.

`stacked_bar_composition` is different and worth stating precisely: 30 category
labels are drawn in an axes **240 px wide on a 476 px canvas**, because the
outside legend takes the other half at a pinned single-column width. The labels
have 7.3 px of room and need 15 px at 10 pt; fitting them would mean about
**4.9 pt type**, below any legibility floor. The figure is over-constrained rather
than mislaid out - 30 samples, a 12-entry key and 110 mm do not coexist. The
honest fixes are a wider figure, fewer categories, or a legend inside the axes,
all of which are the author's choice and none of which a renderer should make
silently. Recorded in the v1.2.0 release notes under *Known limitations*.

### Instrument corrections made during this audit

- `check_text_layout` measured tick labels and axis labels belonging to an axes
  whose axis is switched off. matplotlib skips the whole axis at draw time rather
  than hiding each label, so the `Text` objects still report `get_visible() is
  True`; the chord diagram was credited with three overlapping pairs of labels
  that are never drawn. Real findings were being buried under phantom ones.
- This harness required every plot to label both axes, which failed all seven
  plot types that deliberately present no axis - a network graph clears both tick
  sets, a tissue map gives a scale bar instead of coordinates in microns. The
  check cannot tell that from a defect, so it now reports only the narrower claim
  it can defend ("this axes draws a scale and does not name it") and does not gate.
