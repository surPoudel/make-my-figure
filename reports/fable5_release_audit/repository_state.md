# Repository state audit (independent review)

## Position
- Branch: `main`
- HEAD at audit start: `ccd117f` (pushed)
- Latest RC tag: `v1.0.0-rc1` at `dc49b8e` (not moved by this audit)

## Interrupted-session work found (uncommitted on main)
Modified (all parse-clean, no conflict markers, no debug leftovers):
- make_my_figure_core/plots/base.py — shared `apply_publication_layout`,
  `resolve_legend_location`, `LEGEND_LOCATIONS`, enhanced `place_legend`,
  and (added in this audit) rotated-tick vertical-alignment fix.
- plots/pca.py — marker size now honors style (was hard-coded s=30).
- plots/stacked.py — centered ticks, flexible legend, shared layout.
- plots/manhattan.py — optional/editable cutoff line + tick rotation.
- plots/paired_slope.py — independent line/point colors.
- plots/upset.py — adaptive + adjustable left margin.
- plots/swimmer.py — right-side headroom + adjustable right margin.
- plots/ma_plot.py — click-identify + selected labels + per-label offsets.
- plots/volcano.py — per-label manual offsets (leader lines).
- ui_hints.py — exposes new controls (manhattan cutoff, paired colors, swimmer pad).

Untracked (new):
- tests/test_layout_and_annotations.py — layout + per-plot fix tests.
- scripts/generate_figure_qc_gallery.py — focused QC gallery.
- reports/figure_qc_release_candidate/ — generated QC artifacts (images local-only).

## Complete vs incomplete
- Complete + verified this audit: shared layout helper, flexible legend locations,
  PCA marker size, stacked tick centering + rotated-label position, Manhattan cutoff
  controls, paired-dot colors, UpSet/swimmer margins, MA click-identify, volcano/MA
  per-label offsets.
- Defect found + fixed by audit: rotated x tick labels overlapped the plot (labels
  extended up into the bars). Root cause: 90° + anchor rotation mode + default va.
  Fixed with va="top" and default rotation mode for 90°; regression test added.
- Not yet done (release blockers remaining, see final report): clustered/hierarchical
  heatmap label↔colorbar overlap deep-fix; lollipop leader alignment/movement;
  interactive click-drag in the GUIs; global colorbar-position controls; full plot
  registry QC table; statistics numeric re-validation table.

## Must not commit (protected)
GREEN-*.txt, voom_norm_annot*, meta_info_detail.csv, outputs/, clauderesume, the
unrelated modified benchmarks/.../karate_network/qc/visual_qc.md, and large QC images.
