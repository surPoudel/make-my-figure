# Annotations: manual layer, point labels, statistical overlays, geometry

Written 2026-09-17 against `main` (bb45c12). Three separate systems share the
word "annotation"; keep them apart:

1. the universal manual annotation layer (`spec["annotations"]`),
2. point labels on feature plots (volcano / MA / lollipop / network / scatter),
3. statistical annotations (brackets, above-bar labels, corner panels) derived
   from `StatResult`s.

Pointers: `docs/ANNOTATIONS.md` (manual layer), `docs/VOLCANO_ANNOTATIONS.md`
(point labels, duplicate policy, click-to-label), `docs/STATISTICAL_ANNOTATIONS.md`
(bracket engine, per-plot behaviour), `docs/STATISTICAL_ANNOTATION_FORMATTING.md`
(content modes and tokens). See statistics.md for the engine itself.

## 1. Universal manual annotation layer

Code: `make_my_figure_core/annotations.py` (`Annotation` dataclass,
`parse_annotations`, `apply_annotations`). Applied by `registry.render` to
`figure.axes[0]` of ANY plot type, inside `style.apply()` so text takes the
profile font, before the QA checks (so annotation-induced clipping is flagged).
Count stored in `metadata["n_manual_annotations"]`; errors never break a render.

- Kinds (`_KINDS`): `text`, `arrow`, `callout` (text at `xy2` pointing to `xy`),
  `box`, `region` (translucent fill, alpha x 0.18), `bracket`, `hline`, `vline`.
- Fields: `kind`, `annotation_id`, `text`, `xy`, `xy2`, `coords`
  (`data` | `axes` | `figure`), `color`, `font_size`, `font_weight`, `box`,
  `arrow`, `arrow_style`, `line_width`, `alpha`, `layer` (z-order, drawn in
  ascending order), `visible`, `created_by`
  (user | statistics | volcano | heatmap | clustering), `target` (semantic record).
- Defaults come from the style: `text_color`, `annotation_pt`, `line_width_pt`.
- Drawn as vector artists (`ax.text`, `ax.annotate`, `Rectangle`, `axhline`),
  so SVG/PDF stay editable. `hline`/`vline` are dashed by default.
- Stored in the PlotSpec, declared in `schemas/plot_spec.schema.json` as an
  array; full presets carry them (with a "positions were chosen for the
  original data" warning), style presets do not.

Reuse this for any user-placed text, arrows, ROI boxes or reference lines a
new renderer wants to offer: do not add a renderer-specific free-text mechanism.

## 2. Point labels on feature plots

Code: `plots/label_policy.py` (pure pandas), `plots/annotation_state.py`
(frontend-agnostic selection/move state), `plots/volcano.py::_repel_labels`,
plus per-renderer use in `ma_plot.py`, `lollipop.py`, `network_graph.py`.

- `label_policy.build_label_points(work, ranked_idx, label_series=, text_fn=,
  x_col=, y_col=, id_col=, policy=, representative_rule=, show_count=,
  rep_columns=, limit=, total_counts=) -> List[LabelPoint]`. Policies
  (`duplicate_label_policy`): `all` (default), `unique`, `count` (suffix
  `(n=k)`); representative rules: `pvalue`, `padj`, `effect`, `statistic`,
  `first`. `LabelPoint` carries a stable `point_id` (feature id or `row_<pos>`,
  matching `base.build_pickable_points`), never keyed by text, so duplicate
  gene symbols stay independently selectable.
- Mapping keys the renderers consume: `annotate`, `label_mode` (`top_fdr`,
  `top_lfc`, `top_up_down`, `selected`, `pasted`, `significant_all`), `top_n`,
  `selected_labels`, `label_list`, `max_labels_warn`, `point_offsets`
  (`{point_id: [dx, dy]}` in points, preferred), `label_offsets` (legacy,
  keyed by text), `label_color`, `label_font_size`, `label_box`,
  `show_arrows`, `repel_strength`, `duplicate_label_*`. Offsets are excluded
  from presets (`presets.MAPPING_DATA_KEYS`).
- `AnnotationState` (add/toggle/select/move/set_offset/reset/delete) serialises
  to `selected_labels` + `label_offsets` via `to_mapping`/`from_mapping`; both
  GUIs use it for click-to-label (desktop identify mode uses
  `base.nearest_pickable` on the renderer's `pickable_points`).
- adjustText: dependency pinned `adjustText>=1.0,<2` (`pyproject.toml`,
  `requirements.txt`). `volcano._repel_labels` creates `ax.text` artists then
  calls `adjust_text(texts, ax=ax, arrowprops=..., force_text=(repel, repel))`;
  on any failure it removes them and falls back to `ax.annotate` with a fixed
  `(4, 4)` offset in points. Lollipop and network use
  `adjust_text(..., only_move={"text": "xy"})`. Manually moved labels bypass
  adjustText and are drawn with `ax.annotate(..., xytext=(dx, dy),
  textcoords="offset points")` plus a thin grey leader line.
- Headroom: volcano expands `ylim` to 1.30 x max when labels are drawn (1.18
  otherwise) so repelled labels are not clipped; `n_labeled` is recorded in
  metadata and the renderer warns when identical labels stack on one anchor.

New feature-labelled renderers should call `build_label_points`, honour
`point_offsets`/`label_offsets`, reuse `_repel_labels`-style placement (move
it to a shared module rather than copying if a third caller appears), and
publish `pickable_points` through `base.build_pickable_points`.

## 3. Statistical annotations

Chain: StatsSpec -> `run_statistics` -> `StatResult` ->
`statistics.annotations.build_pairwise_annotations` -> `AnnotationItem` ->
`plots/stats_overlay` -> figure. Renderers call
`plots/stats_integration.run_and_annotate` and never format text.

Text: `method_reporting.render_annotation(result, cfg)` builds the label from
`annotation.content` (`stars`, `p`, `p_adj`, `p_stars`, `stat`, `effect`,
`p_stat`, `p_effect`, `full`, `flags`, `custom` with `{p} {p_adj} {stars}
{stat_symbol} {stat} {effect_symbol} {effect} {ci} {test_short} {n}
{comparison}` tokens from `annotation_tokens`). Formatting keys: `digits`,
`sci_threshold`, `stat_digits`, `effect_digits`, `p_less_than_style`,
`use_ns`, `show_*` flags, `hide_nonsignificant` / legacy `show_nonsignificant`.
Stars from `stars_for_p` (`STAR_THRESHOLDS`). Hidden values remain in the
sidecar (`tests/test_annotation_formatting.py::test_statsspec_retains_all_values_when_hidden`).

Placement and geometry (all fractions of the current y-range unless noted):

- `annotation.placement`: `bracket` (default) or `above_bar`; anything else
  raises `StatsError`.
- Bracket engine `stats_overlay.annotate_pairwise(ax, items, position_lookup,
  style=, cfg=, top_lookup=)`: `bracket_height_frac` 0.03 (tick height),
  `gap_frac` 0.06 (between stacked levels), `top_margin_frac` 0.10 (headroom),
  `font_size` (None -> `style.annotation_pt`), `line_width` (None ->
  `style.spine_width_pt`), colour `style.text_color`. It measures real label
  widths with the canvas renderer, widens each bracket's effective span to the
  label width (x1.12 + 3 % x-range pad), greedily assigns levels narrowest
  first so nothing on one level overlaps, expands `ylim` before drawing, then
  stacks levels a gap above the tallest measured label. Returns
  `{"n_brackets", "levels", "top"}` (stored as `report.config["_annotation_info"]`).
- `annotate_above(ax, items, positions, tops, style=, cfg=, reference=)`:
  one label above each compared bar for comparisons sharing one reference
  (`infer_reference_group` when not restated); `above_bar_pad_frac` 0.02;
  pairs without the reference are returned as `unplaced` and
  `run_and_annotate` draws them as brackets.
- `annotate_corner(ax, lines, style=, loc=)`: axes-fraction positions
  (`upper left` = (0.03, 0.97), etc.), white rounded bbox, alpha 0.75. Used for
  correlation/regression, categorical, survival and omnibus panels;
  `run_and_annotate` reserves `0.085 * n_lines + 0.04` of y-range headroom for
  omnibus panels.
- `annotate_text_below_legend` exists but has no caller on main.
- Omnibus/two-way results are never bracketed; `stat_text_panel` renders them
  (a compact multi-line Two-way ANOVA block).

Tests to keep green: `tests/test_stats_annotations.py` (brackets for bar/box,
ylim expansion, level stacking, within-x, wide-label stagger),
`tests/test_above_bar_annotation.py`, `tests/test_annotation_formatting.py`.

## 4. Other annotation-like elements and what to reuse

- Reference / threshold lines: volcano draws dashed `axvline`/`axhline` at the
  cutoffs (grey "0.5", threshold line options in `ui_hints`); forest draws
  `axvline(reference)` with `style.spine_width_pt`; spider draws a reference
  level; manhattan has cutoff colour/width/style options
  (`tests/test_layout_and_annotations.py::test_manhattan_cutoff_*`). There is
  no shared "reference line" helper on main beyond the manual `hline`/`vline`
  kinds; use `style.spine_width_pt` and a neutral grey for consistency.
- n labels: no shared n-label helper exists. Scatter's fit box can include `n`
  via `show_n`; statistical labels include `{n}` through `annotation_tokens`.
  Kaplan-Meier has no number-at-risk table on main.
- Legend placement: `base.place_legend` / `LEGEND_LOCATIONS` (inside and
  outside positions that reserve figure margin).
- Axis-scoped text sizing: `style.annotation_pt` for any label the user reads
  as an annotation; QA floors are 9 pt for labels and 8 pt for ticks
  (`qa/publication_check.py`).

## 5. Geometry conventions

- Data coordinates: bracket x positions, bar tops, manual annotations with
  `coords="data"`, volcano label anchors.
- Axes fractions (0-1, `transAxes`): corner panels, manual `coords="axes"`,
  legend `bbox_to_anchor` (1.02, 0.5) for outside placement, `FigureLayout.label_dx/dy`.
- Figure fractions: `coords="figure"`, `subplots_adjust` margins
  (`layout.margin_*`).
- Points (1/72 in): label offsets (`point_offsets`, `label_offsets`,
  `xytext` with `textcoords="offset points"`), font sizes, line widths, tick
  pads (`x_tick_pad`, `y_tick_pad`, `x_label_pad`, `y_label_pad`, `title_pad`).
- Fractions of the y-range: every `*_frac` key in `annotation`.
- Millimetres: only `WIDTH_PRESETS_MM`, `output.width_mm/height_mm`,
  `FigureLayout.fig_width_mm`.

## Verify this is still current

```bash
cd "<repo>" && grep -n "^_KINDS\|^_COORDS\|^def " make_my_figure_core/annotations.py
grep -n "def annotate_pairwise\|def annotate_above\|def annotate_corner\|def annotate_text_below_legend\|_frac" make_my_figure_core/plots/stats_overlay.py make_my_figure_core/statistics/schemas.py
grep -rn "adjust_text(" make_my_figure_core/plots/*.py && grep -n adjustText pyproject.toml
grep -n "def build_label_points\|DUPLICATE_POLICIES\|REPRESENTATIVE_RULES" make_my_figure_core/plots/label_policy.py
```
