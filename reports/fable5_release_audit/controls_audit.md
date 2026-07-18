# Legend / tick / colorbar control audit — all 37 plot types

Method: render every registered plot from its bundled example, measure whether the
shared controls take effect, and cross-check the capability registry. Data:
`controls_audit.csv`.

## X tick rotation (layout.x_tick_rotation)
- 37 plot types; 33 render x tick labels.
- **33/33 now honor x_tick_rotation** (0 failures) after applying the shared
  `apply_publication_layout` centrally in `registry.render()` on the primary axes.
- The 4 without x tick labels (network_graph, sankey, and the two colorbar-only
  matrices when labels are hidden) correctly report n/a.

## Legend placement (layout.legend_location)
- Applied centrally: when `legend_location` is set, `registry.render()` re-places the
  primary-axes legend at any inside/outside position and reserves margin for outside
  legends. Verified moving-outside for grouped bar, volcano, scatter, ROC, PR,
  Kaplan–Meier, Manhattan, line, dose-response, calibration, PCA (custom-handle
  legends handled via a fallback that reads the existing legend's handles).
- Plots whose example has no grouping draw no legend (expected) but still *support*
  it — capability `supports_legend` reflects capability, not the example.

## Colorbar placement (mapping.colorbar_location / _pad / _fraction / _shrink)
- Colorbar-capable plots: heatmap_clustered_matrix, hierarchical_clustering,
  confusion_matrix, enrichment_dotplot (+ network_graph when color_by=value).
- All now accept `colorbar_location` (right/left/top/bottom) + pad/fraction/shrink and
  render OK. `enrichment_dotplot` capability corrected to `supports_colorbar=True`.
- upset_plot has multiple axes but no colorbar (correctly `supports_colorbar=False`).

## Result
- x tick rotation: consistent across all axis plots. ✓
- legend location: consistent across all primary-axes-legend plots. ✓
- colorbar location: available on all colorbar plots. ✓
- No renderer exposes a control that silently does nothing for these three families
  (unsupported style controls are still reported via `warn_ignored_style_controls`).

## Remaining (not in this audit's scope)
Interactive click-drag annotation UI; a dedicated clipping/overlap QC engine; the
Publication-tab reorganization in the GUIs; per-plot y-tick-rotation where meaningful.

## Y tick rotation (layout.y_tick_rotation) — follow-up audit
- 37 plot types; 36 render y tick labels.
- **36/36 honor y_tick_rotation** (0 failures) via the same central
  `apply_publication_layout`. Data: `y_tick_rotation_audit.csv`.
- Reachability: the shared layout controls (x/y tick rotation, legend location,
  margins, label padding, auto-fix) are now surfaced in the **Streamlit** sidebar
  "Axes & layout" expander. Surfacing the same set in the **desktop** style panel is a
  parallel Qt task (not done in this session — engine support already exists, so a
  PlotSpec with these keys works in the desktop app today).
