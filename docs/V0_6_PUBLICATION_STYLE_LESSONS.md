# Publication style lessons from the benchmark work

These are general design lessons distilled from running
[the publication-recreation benchmark suite](PUBLICATION_BENCHMARKS.md) and its
[Publication QC](PUBLICATION_QC.md) scores across all 17 plot types. They
describe defaults for the **single Publication style**
(`make_my_figure_core/styles/engine.py`) — general manuscript-ready design
choices, applied uniformly, never a per-dataset or per-panel hack.

> **No official journal-compliance claim.** These are general Publication
> defaults informed by aggregate visual conventions, not a specific journal's
> requirements. Make My Figure does not provide official journal templates or
> claim compliance with any journal's formatting requirements.

Source material: `benchmarks/publication_recreation/style_notes/` (
`aggregate_publication_defaults.md`, `qc_observations.md`) and the "Aggregate
style lessons" / "What matched well vs. differed" sections of
`benchmarks/publication_recreation/V0_6_BENCHMARK_RECREATION_REPORT.md`.

## Font hierarchy

Keep a clear size ordering — title > axis label > tick label > annotation —
with readable minimums: axis label ≥ 11 pt, tick label ≥ 9 pt (the Publication
defaults are higher still; see [docs/STYLE_PROFILES.md](STYLE_PROFILES.md)).
Use a sans-serif stack (Arial → Helvetica → DejaVu Sans → generic sans-serif)
so the figure renders consistently across machines without the exact font
installed.

## Axis labeling and units

The recurring finding across the benchmark run was the same low-confidence
advisory: an axis label that looks like it needs a unit but doesn't have one
(`time_months`, `pseudotime`, `bill_length_mm`). This never failed QC, but it
is common enough to call out explicitly: prefer `Label (unit)` on axes
wherever a unit applies, and let Publication QC's `missing_units` check nudge
you when one looks absent.

## Legend placement

For four or more series, or any panel where the legend risks sitting over the
data, place the legend **outside** the plotting area with the frame off. The
Publication style already exposes this as `legend_outside`; Publication QC's
`legend_overlap` check exists specifically to catch the cases where this
wasn't applied, and its `legend_outside` auto-fix applies it directly.

## Margins and panel spacing

A touch more outer margin than Matplotlib's tight defaults reads as more
manuscript-like, and multi-panel figures benefit from slightly larger
inter-panel spacing plus bold vector panel labels (A, B, C, …) so panels don't
feel cramped against each other or the figure edge.

## Colorbar readability

Keep heatmap colorbars **slim**, explicitly labeled, with a modest number of
ticks, and sized to match the height of the axes they annotate — a colorbar
that dwarfs the plot or has an unlabeled, dense tick ladder reads as
unfinished.

## Volcano labeling and thresholds

Draw significance thresholds as light, unobtrusive guide lines rather than
heavy reference lines. Cap the number of drawn point labels (Publication QC's
`label_crowding` check flags a volcano with more than 40 annotated points) and
prefer non-overlapping label placement over letting labels stack on top of
each other or the data.

## Export defaults

Every recreated panel in the benchmark suite exported cleanly to **editable**
SVG and PDF (`svg.fonttype: none`, `pdf.fonttype: 42`) alongside PNG, plus a
reproducible `.plot_spec.json` sidecar — confirming the existing export path
(`make_my_figure_core/plots/registry.py::export_figure`) is already
publication-ready. Publication QC additionally checks that the chosen
`output.dpi` is adequate at the intended physical size (≥300 DPI recommended,
<150 DPI is a fail) — keep DPI explicit in the PlotSpec rather than relying on
a renderer default.

## What this suite did not need to fix

No panel in the benchmark run triggered a QC `fail`: axis labels, legible
fonts, non-overlapping legends, and adequate export DPI were already present
by default across all 17 plot types (12 of 15 recreated panels scored a clean
pass; the other 3 only drew the units advisory above). The lessons above are
refinements on an already-solid baseline, not fixes for broken defaults.

## See also

- [docs/PUBLICATION_QC.md](PUBLICATION_QC.md) — the checks referenced throughout this page.
- [docs/PUBLICATION_BENCHMARKS.md](PUBLICATION_BENCHMARKS.md) — how these lessons were derived and how to re-run the suite.
- [docs/STYLE_PROFILES.md](STYLE_PROFILES.md) — the Publication style's token defaults these lessons feed into.
- [docs/STYLE_REFERENCE_AUDIT.md](STYLE_REFERENCE_AUDIT.md) — the earlier, broader open-access style reference audit.
