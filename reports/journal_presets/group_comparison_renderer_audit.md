# Group-comparison renderers - capability audit

Read-only audit of the worktree `make_my_plot_journal_presets/` (2026-09-16). All paths are
relative to `make_my_figure_core/` unless stated; line numbers refer to the files as they are in
this worktree. Source was not modified.

Renderers audited (all registered in `plots/registry.py:68-90`, default mappings `:111-143`,
display names `:174-197`):

| plot_type | file | render entry |
|---|---|---|
| `boxplot_or_violin_with_points` | `plots/box_violin.py` | `render` `:25` |
| `barplot_with_error_bar` | `plots/barplot.py` | `render` `:25` |
| `grouped_barplot_with_error_bar` | `plots/grouped_barplot.py` | `render` `:27` |
| `dot_strip_plot` | `plots/dot_strip.py` | `render` `:36` |
| `beeswarm_plot` | `plots/beeswarm.py` | `render` `:41` |
| `raincloud_plot` | `plots/raincloud.py` | `render` `:32` |
| `paired_slopegraph` | `plots/paired_slope.py` | `render` `:32` |

Shared code: `plots/base.py` (`get_mapping :52`, `summarize_error :71-96`, `figure_size :127`,
`style_axes :261`, `autorotate_xticklabels :281`, `place_legend :353`, `apply_publication_layout
:427`, `base_metadata :640`), `plots/_v04_shared.py` (`jitter :168`, `beeswarm_offsets :176`,
`summary_stat :212`, `ordered_unique :245`), `plots/stats_integration.py`, `plots/stats_overlay.py`,
`statistics/annotations.py`, `statistics/schemas.py`, `statistics/runner.py`,
`statistics/test_registry.py`, `statistics/method_reporting.py`, `ui_hints.py`,
`styles/engine.py`, `styles/capabilities.py`, `recommendations/*`.

How options reach a renderer: every non-column option is a key in `spec["mapping"]` read with
`get_mapping` (`base.py:52-58`). Scope (`style` vs `config`) is declared per option in
`ui_hints.Option.scope` (`ui_hints.py:60-84`) and consumed by the preset system
(`presets.py:136-163`). The PlotSpec JSON schema allows arbitrary mapping keys
(`schemas/plot_spec.schema.json:19-30`), so an undeclared key is silently ignored by the renderer
rather than rejected. `StyleProfile` tokens come from `spec["style"]` via `with_overrides`
(`styles/engine.py:293-322`); `styles/capabilities.py` records which controls each plot type
honours and warns about the rest (`registry.py:311-320`).

Status legend: **yes** = user-controllable option exists; **partial** = behaviour exists but is
hard-coded, coupled to another option, or only partly configurable; **no** = not found.

---

## 1. `boxplot_or_violin_with_points` (`plots/box_violin.py`)

| capability | status | option key / scope / default | evidence | gap note |
|---|---|---|---|---|
| show individual observations | yes | `points` / style / `True` | `box_violin.py:29,71-77`; `ui_hints.py:203` | |
| jitter style | partial | none | `:73` uniform `rng.uniform(-0.12, 0.12)` | only uniform; no option |
| jitter seed | partial | none | `:41` `default_rng(42)` fixed | deterministic but not exposed |
| jitter width | no | none | `:73` hard-coded 0.12 | |
| beeswarm-like spacing | no | not found | - | separate `beeswarm_plot` only |
| marker size | yes | `point_size` / style / `8.0` (pt2, 1-80) | `:75`; `ui_hints.py:201` | ignores `style.marker_size` (`capabilities.py:100-102` declares `supports_marker_size=False`) |
| marker shape | no | not found | `:74` `ax.scatter` default `o` | |
| marker fill (filled vs open) | no | not found | `:76` `color=` always filled | |
| marker edge colour | no | hard-coded `black` | `:76` | |
| marker edge width | no | hard-coded `0.2` | `:77` | does not use `style.marker_edge_width` |
| marker alpha | no | hard-coded `0.8` | `:77` | does not use `style.marker_alpha` |
| box width | no | hard-coded `widths=0.5` | `:58` | |
| box fill vs outline-only | no | always `patch_artist=True`, facecolor palette, alpha 0.5 | `:58,61-63` | no outline-only mode |
| box outline colour | no | hard-coded `black` | `:64` | |
| box line width | partial | token `style.spine_width_pt` (1.1) | `:65` | not a per-plot option |
| median line width / colour | partial | `style.line_width_pt` (1.8) / hard-coded `black` | `:60` | |
| whisker style / width | partial | matplotlib default (1.5 IQR), width `style.spine_width_pt`, colour black | `:66-69` | no whisker-range option (e.g. min-max, 5-95 %) |
| cap width | no | matplotlib default | `:58` | no `capwidths` |
| show/hide outliers separately from points | no | `showfliers=not show_points` | `:59` | outliers only appear when points are hidden; no independent toggle |
| violin styling | partial | `kind="violin"`; body alpha 0.45, edge black, `spine_width_pt`; medians only, no extrema | `:45-55` | no bandwidth / inner / split options |
| group spacing | no | positions `1..n` | `:37` | fixed |
| category order | partial | first-seen order | `:35` | no `order` option (grep `category_order|group_order` in `ui_hints.py` and the renderers: not found) |
| orientation (vertical/horizontal) | no | not found | all `ax.boxplot(... positions=)` vertical | |
| one grouping variable | yes | `x` (column field) | `:26`; `ui_hints.py:18` | |
| primary x + secondary grouping | no | `COLUMN_FIELDS` = `["x","y"]` only | `ui_hints.py:18` | no dodged/hue box plot |
| bar summary statistic (mean/median) | n/a | median drawn by box; no mean marker | `:60` | no mean overlay option |
| error choice | n/a | - | - | |
| PlotSpec/metadata records summary + error | partial | `meta["kind"]`, `meta["groups"]`, `meta["group_n"]` | `:99-101` | no explicit "centre = median, whiskers = 1.5 IQR" record |
| raw-observation overlay | yes (jittered only) | `points` | `:71-77` | |
| adaptive small-n / large-n rules | no | not found | - | same size/alpha at n=3 and n=300 |
| n labels (below/above / legend) | no | not found (n only in metadata `group_n :101`) | - | |
| statistics integration | yes | `spec["statistics"]` -> `run_and_annotate(mode="bracket")`, tops = per-group max | `:90-96` | brackets clear the max observation of the two compared groups |
| axis policy | partial | no forced zero (matplotlib autoscale); brackets expand ylim | `stats_overlay.py:154-155,197-198` | `apply_axis_overrides` not called -> `y_min/y_max/y_ticks` ignored (grep `apply_axis_overrides` in `plots/*.py`: only forest/histogram/survival) |
| legend | no | `supports_legend=False` | `capabilities.py:100-102` | nothing to legend without a second grouping |
| x tick rotation | yes | `x_tick_rotation` / style / `auto` | `:81`; `ui_hints.py:106-107,204` | |

## 2. `barplot_with_error_bar` (`plots/barplot.py`)

| capability | status | option key / scope / default | evidence | gap note |
|---|---|---|---|---|
| show individual observations | no | not found | whole render `:49-90`, only `ax.bar` | manuscript-style "bar + dots" impossible |
| jitter / beeswarm | no | not found | - | |
| marker size/shape/fill/edge/alpha | no | not found | - | |
| bar width | no | hard-coded `width=0.68` | `:60` | |
| bar fill vs outline | no | palette fill, edge `#222222` hard-coded | `:57-58` | no open-bar / hatch mode |
| bar edge width | partial | token `style.bar_edge_width` (0.9) | `:59` | |
| group spacing | no | positions `range(n)` | `:51` | |
| category order | partial | first-seen | `:36` | no `order` option |
| orientation | no | not found | `ax.bar` only | no `barh` |
| one grouping variable | yes | `x` | `:26`; `ui_hints.py:13` | |
| secondary grouping | partial | `color` column field declared (`ui_hints.py:13`, default `"condition"` `registry.py:112`) | `:29,92` | `color_by` is read and echoed to metadata only; bars are coloured by category index `:52` -> the option has no visual effect |
| bar summary statistic selection | no | centre is always the mean | `base.py:71-75` "Center is always the mean"; `:41` | median bars not possible; "bar = mean" is assumed and written into the y label `:70-71` |
| error choice | yes | `error` / style / `sem`; choices `sem, sd, ci95, none` | `:28`; `ui_hints.py:97,124`; `base.py:79-96` | CI is normal-approx `1.96*SEM` (`base.py:93-95`), not t-based; label `mean ± CI95` |
| metadata records summary + error | partial | `meta["error_method"]`, `meta["centers"]`, `meta["categories"]` | `:93-95` | summary statistic ("mean") is not recorded as a field; CI method not recorded |
| raw-observation overlay on bars | no | not found | - | |
| adaptive small-n / large-n | partial | warning only when a category has n<2 | `:46-47` | no visual adaptation |
| n labels | no | not found | - | |
| statistics | yes | `run_and_annotate(mode="bracket")`, tops = mean + error | `:82-90` | `above_bar` placement available via `statistics.annotation.placement` |
| zero baseline | partial (implicit) | matplotlib bar sticky edge at 0 + `ax.margins(y=0.08)` | `:73` | not an explicit policy; no option to start elsewhere |
| legend | no | `supports_legend=False` | `capabilities.py:76-81` | |
| x tick rotation | yes | `x_tick_rotation` / style / `auto` | `:67`; `ui_hints.py:125` | |

## 3. `grouped_barplot_with_error_bar` (`plots/grouped_barplot.py`)

| capability | status | option key / scope / default | evidence | gap note |
|---|---|---|---|---|
| show individual observations | no | not found | `:50-77` | |
| jitter / beeswarm / marker styling | no | not found | - | |
| bar width / cluster width | no | `total_width=0.8`, `bar_width=0.8/n_groups` | `:41-42` | |
| bar fill / edge | no | palette per subgroup, edge `#222222`, width `style.bar_edge_width` | `:71-73` | |
| group spacing | no | `x_idx = arange` | `:43` | |
| category order | partial | first-seen for both factors | `:37-38` | |
| orientation | no | not found | - | |
| one grouping variable | n/a | requires `group` | `:29` | cannot be used for a single factor |
| primary x + secondary grouping | yes | `x`, `group` (column fields) | `:28-29`; `ui_hints.py:14` | drawn as dodged bars within each x cluster `:59-77`; legend title = group column `:104` |
| bar summary statistic | no | mean only | `:56` via `summarize_error` | |
| error choice | yes | `error` / style / `sem` | `:31`; `ui_hints.py:126` | y label `mean ± ERR` `:94-95` |
| metadata records summary + error | partial | `error_method`, `x_levels`, `groups` | `:112-114` | no centres, no per-cell n, no "mean" field |
| raw-observation overlay | no | not found | - | |
| adaptive n rules | no | not found; no n<2 warning here either | - | |
| n labels | no | not found | - | |
| statistics | yes | positions keyed `(x_level, group)` and `x_level` (cluster centre) | `:61-64,82-87`; `stats_integration.py:62-81` | with `test="auto"` the recommender's primary is `two_way_anova` (`test_registry.py:81-83`, primary = first `:117`) -> omnibus corner panel, no brackets unless a pairwise test is chosen; then `auto` mode = within-x pairs (`runner.py:270-272`) |
| zero baseline | partial (implicit) | sticky edge + `ax.margins(y=0.08)` | `:97` | |
| legend | yes (forced) | `place_legend(force_outside=True)` | `:104` | `style.legend_loc` ignored; `layout.legend_location` re-places it (`registry.py:365-388`) |
| x tick rotation | yes | `x_tick_rotation` / style / `auto` | `:91` | |

## 4. `dot_strip_plot` (`plots/dot_strip.py`)

| capability | status | option key / scope / default | evidence | gap note |
|---|---|---|---|---|
| show individual observations | yes (always) | - | `:69-76` | cannot hide |
| jitter on/off | yes | `jitter` / style / `True` | `:40,63`; `ui_hints.py:291` | |
| jitter style / width / seed | partial | uniform, width 0.18 hard-coded, seed `gi+1` | `:63`; `_v04_shared.py:168-173` | |
| beeswarm spacing | no | use `beeswarm_plot` | - | |
| marker size | partial | token `style.marker_size` (45) | `:70,74` | no per-plot option; `capabilities.py` has no entry -> default caps advertise `marker_size` as supported (`:181-186`) |
| marker shape / fill | no | not found | `ax.scatter` default | |
| marker edge colour | no | hard-coded `white` | `:71,75` | |
| marker edge width | partial | `style.marker_edge_width` (0.6) | `:71,75` | |
| marker alpha | partial | `style.marker_alpha` (0.9) | `:72,76` | |
| point colour per group | partial | all groups use `color_for(0)` unless `color` set | `:74` | groups are not palette-cycled |
| group spacing | no | `gi` integer positions, xlim `(-0.6, n-0.4)` | `:69,93` | |
| category order | partial | first-seen (`ordered_unique`) | `:49` | |
| orientation | no | not found | - | |
| one grouping variable | yes | `x` | `:37` | |
| secondary grouping | partial | `color` column: colours points within the same cloud, legend outside | `:39,50-51,64-72,99-100`; `ui_hints.py:35` | not dodged; summary overlay ignores colour groups (one summary per x) `:78-86` |
| summary statistic selection | yes | `summary` / style / `mean`; `none, mean, median, ci, sd, sem` | `:41-43`; `ui_hints.py:290` | `mean` silently means mean ± SEM (`_v04_shared.py:234`); `median` = line only `:224` |
| error choice | yes (coupled) | same `summary` key | as above | centre and error are one choice; "median ± IQR" impossible |
| metadata records summary + error | partial | `meta["summary"]`, `meta["jitter"]` | `:107-108` | does not say `mean` implies SEM |
| raw overlay | yes | always | | |
| adaptive n rules | no | not found | - | |
| n labels | no | not found | - | |
| statistics | no | `run_and_annotate` not called | whole file | no brackets possible |
| axis policy | partial | no forced zero; `ax.margins(y=0.08)` | `:94` | no `apply_axis_overrides` |
| legend | yes when `color` set | `place_legend(force_outside=True)` | `:99-100` | |
| publication layout | yes | `apply_publication_layout` | `:103` | (also applied by registry `:342-348`) |

## 5. `beeswarm_plot` (`plots/beeswarm.py`)

| capability | status | option key / scope / default | evidence | gap note |
|---|---|---|---|---|
| show individual observations | yes (always) | - | `:73-80` | |
| beeswarm-like spacing | partial | value-binned symmetric spread, width 0.32, seed `gi+1` | `:67`; `_v04_shared.py:176-209` | documented "quasi-beeswarm" (`:1-9`, `meta["layout_algorithm"] :110`); bins use `max(10, min(60, 4*sqrt(n)))` `:192`; no cross-bin collision check, no marker-size awareness |
| jitter option | no | not found | - | |
| marker size / edge / alpha | partial | `style.marker_size`, edge `white`, `style.marker_edge_width`, `style.marker_alpha` | `:73-80` | as dot_strip |
| marker shape / fill | no | not found | - | |
| point colour | partial | `color_for(0)` for all groups unless `color` | `:78` | |
| group spacing / order / orientation | no / partial / no | as dot_strip | `:53,91-96` | |
| secondary grouping | partial | `color` column (same swarm, legend) | `:44,54-55,68-76` | |
| summary / error | yes (coupled) | `summary` / style / `mean` | `:45-47`; `ui_hints.py:295` | |
| metadata | partial | `summary`, `layout_algorithm`, `n_groups` | `:108-110` | |
| adaptive n rules | partial | bin count scales with sqrt(n) only | `_v04_shared.py:192` | marker size/alpha constant |
| n labels | no | not found | - | |
| statistics | no | `run_and_annotate` not called | whole file | |
| axis policy | partial | no forced zero; margins 0.08 | `:97` | |
| legend | yes when `color` | forced outside | `:102-103` | |

## 6. `raincloud_plot` (`plots/raincloud.py`)

| capability | status | option key / scope / default | evidence | gap note |
|---|---|---|---|---|
| show individual observations | yes (always) | - | `:80-83` | |
| jitter | partial | uniform width 0.07, offset `gi-0.28`, seed `gi+1` | `:80-81` | |
| marker size / edge / alpha | partial | `max(8, style.marker_size*0.5)`, edge `white`, `marker_edge_width*0.7`, `marker_alpha` | `:81-83` | |
| half-violin | partial | `widths=0.9`, alpha 0.35, right half, at `gi+0.05`; skipped when n<=1 or zero range | `:57-66` | no bandwidth option |
| box width | no | `widths=0.14` at `gi-0.12` | `:68` | |
| box fill vs outline | partial (fixed) | white fill, palette edge | `:71-74` | opposite convention to box_violin; not selectable |
| box line width / median | partial | `spine_width_pt`; median `text_color`, `line_width_pt` | `:69-78` | |
| whiskers / caps | partial | palette colour, `spine_width_pt`; default 1.5 IQR | `:75-78` | |
| outliers | no | `showfliers=False` always | `:69` | |
| category order / spacing / orientation | partial / no / no | first-seen; xlim `(-0.6, n-0.15)` | `:40,88` | horizontal rainclouds (common in papers) not possible |
| secondary grouping | no | `COLUMN_FIELDS` = `["x","y"]` | `ui_hints.py:38` | |
| summary selection | no | median via box only | - | |
| metadata | partial | `n_groups`, `components` | `:99-100` | |
| adaptive n | partial | warning when >6 groups | `:42-43` | nothing for n per group |
| n labels | no | not found | - | |
| statistics | no | not called | whole file | |
| legend | no | `supports_legend=False` | `capabilities.py:133-134` | |
| options exposed | minimal | only `x_tick_rotation` | `ui_hints.py:299` | |

## 7. `paired_slopegraph` (`plots/paired_slope.py`)

| capability | status | option key / scope / default | evidence | gap note |
|---|---|---|---|---|
| show individual observations | yes (always) | one line + markers per subject | `:52-88` | |
| jitter / beeswarm | no | not found | - | |
| marker size | yes | `point_size` / style / `6.0` (ui) ; renderer fallback `max(3, sqrt(marker_size))` | `:84-85`; `ui_hints.py:406` | ui default and code fallback differ |
| marker shape | no | hard-coded `o` | `:87` | |
| marker fill / colour | yes | `point_color` / style / `(group)` | `:78,80,87`; `ui_hints.py:402-403` | |
| marker edge colour / width | partial | `white` / `style.marker_edge_width` | `:88` | |
| line colour / width / alpha | yes | `line_color` `(group)`, `line_width` 1.5, `line_alpha` 0.7 (ui); code fallbacks `style.line_width_pt`, 0.55/0.75 | `:77-83`; `ui_hints.py:404-408` | |
| duplicates per subject/condition | partial | averaged silently | `:54-61` | no warning |
| category order / spacing / orientation | partial / no / no | first-seen; xlim `(-0.35, n-0.65)` | `:42,92` | |
| secondary grouping | yes | `color` column colours lines; legend outside | `:36,45-46,66-71,100-101`; `ui_hints.py:37` | |
| summary overlay (group mean line) | no | not found | - | |
| n labels | no | not found; `meta["n_subjects"]` only | `:106` | |
| statistics | no | `run_and_annotate` not called; paired tests exist in the engine (`schemas.py:19`, `runner.py:97-107`) but only reachable from box/bar renderers | whole file | |
| axis policy | partial | no forced zero; margins 0.08 | `:95` | |
| legend | yes when `color` | forced outside | `:100-101` | |

---

## 8. Shared statistics-annotation system

Files: `plots/stats_integration.py`, `plots/stats_overlay.py`, `statistics/annotations.py`,
`statistics/schemas.py`, `statistics/runner.py`, `statistics/test_registry.py`,
`statistics/method_reporting.py`.

| capability | status | key / default | evidence | gap note |
|---|---|---|---|---|
| Enabling | yes | `statistics.enabled` default `False` | `schemas.py:85` | |
| Renderers wired to it | partial | box_violin, barplot, grouped_barplot only | `box_violin.py:95`, `barplot.py:89`, `grouped_barplot.py:108` | dot_strip, beeswarm, raincloud, paired_slopegraph: not wired |
| Comparison modes | yes | `comparison_mode` in `auto, all_pairs, vs_control, selected_pairs, within_x, omnibus`, default `auto` | `schemas.py:24,87`; `runner.py:69-81,280-303` | `selected_pairs` = list of `[a, b]` pairs `:73-79`; `vs_control` needs `reference_group` `:71-72` |
| `auto` mode resolution | partial | `vs_control` if `reference_group` set else `all_pairs`; `within_x` when a subgroup column exists | `runner.py:285-286,270-272` | |
| Tests (two-group) | yes | `students_t, welch_t, mann_whitney, paired_t, wilcoxon` | `schemas.py:19`; `runner.py:85-111` | paired tests need `subject_column` `:93-95` |
| Tests (omnibus) | yes | `one_way_anova, kruskal_wallis, two_way_anova, rm_anova`; post-hoc via `posthoc=True`, `posthoc_test="welch_t"` (Dunn for KW) | `runner.py:231-260`; `schemas.py:91-92` | |
| `test="auto"` | partial | primary = first suggestion: 2 groups -> `welch_t`; >=3 -> `one_way_anova` (omnibus only, `posthoc` default False); grouped bar -> `two_way_anova` | `test_registry.py:80-93,117`; `runner.py:136-141` | with 3+ groups the default figure gets a corner ANOVA panel and no brackets |
| Minimum n per group | yes | 2 finite values | `validators.py:53-63` | unequal n handled; `n_by_group` recorded (`pairwise.py:34`) |
| Correction | yes | `correction` default `benjamini_hochberg`; applied across two-group family only | `schemas.py:88`; `runner.py:167-176` | |
| Annotation forms | yes | `annotation.content` in `stars, p, p_adj, p_stars, stat, effect, p_stat, p_effect, full, flags, custom`; legacy `mode` `stars/p/both` | `schemas.py:25-39,47-49`; `method_reporting.py:279-348` | stars thresholds `method_reporting.py:19` applied to `display_p` (adjusted when present, `models.py:89-91`) |
| P-value formatting | yes | `digits` 3, `sci_threshold` 1e-3, `p_less_than_style` True, `use_ns` True | `schemas.py:51-56` | |
| Hide non-significant | yes | `hide_nonsignificant` False / `show_nonsignificant` True | `schemas.py:66-67`; `annotations.py:45,54-55` | |
| Placement | yes | `placement` in `bracket` (default), `above_bar` | `schemas.py:72`; `stats_integration.py:83-106` | `above_bar` only for comparisons sharing one reference (`stats_overlay.py:202-247`); others fall back to brackets `:97-103` |
| Bracket tick height | yes | `bracket_height_frac` 0.03 of y-range | `schemas.py:77`; `stats_overlay.py:61` | fraction of y-range, not points/mm |
| Gap above data | yes | `gap_frac` 0.06 of y-range | `schemas.py:78`; `stats_overlay.py:62,173` | start = `max(tops of the two compared groups)` per item (`:76-81`) but the first level uses the *global* max across all items (`:153,173`) so every level-0 bracket starts at the same height |
| Bracket line width / font | yes | `line_width` None -> `style.spine_width_pt`; `font_size` None -> `style.annotation_pt` | `stats_overlay.py:64-65` | |
| Stacking of multiple comparisons | yes | greedy leveling on effective x-span (bracket span or measured label width + 3 % pad) | `stats_overlay.py:101-147` | |
| Collision avoidance | partial | bracket-vs-bracket and label-vs-bracket only | `:133-147,169-195` | a group *between* the compared groups that is taller than both is not checked (start uses only the two compared tops `:80-81`); brackets do not avoid the omnibus corner panel |
| Inclusion in axis limits | yes | ylim expanded before and after drawing; artists `clip_on=False` | `:149-155,182,185,197-198`; corner panel headroom `stats_integration.py:116-118` | |
| Manual y coordinates | not needed | no user y-coordinate input exists | `stats_overlay.py` | (manual annotation layer `annotations.py` is separate) |
| Top margin | yes | `top_margin_frac` 0.10 | `schemas.py:79` | |
| `n` in annotation text | partial | `content="flags"` + `show_n=True` appends `n = a, b` to the label | `method_reporting.py:345-346`; `schemas.py:65` | only inside a comparison label; no per-category n |
| Provenance | yes | every label from a `StatResult` (`annotations.py:34-69`); `meta["statistics_report"]`; `_annotation_info` in `report.config`; sidecar | `stats_integration.py:107-108`; `schemas.py:159-174` | |
| Omnibus display | yes | corner panel upper-left with reserved headroom | `stats_integration.py:112-119`; `stats_overlay.py:288-307` | location not configurable in bracket mode |

## 9. Recommendation engine (`recommendations/`)

Schema detection: a categorical column matching the `group` aliases (`data_profiler.py:28,188,203`)
plus >=1 numeric column -> `generic_long` (`schema_detector.py:82-83`); `paired` when a subject id
and a 2-level group with >=2 rows per subject are present (`:70-79`).

| situation | recommendations (confidence) | evidence | note |
|---|---|---|---|
| few groups + continuous outcome (`generic_long`) | 1. `boxplot_or_violin_with_points` 0.72 with suggested stats; 2. `ridge_or_density_plot` 0.62; 3. `barplot_with_error_bar` 0.60 ("Compare group means with error bars"); 4. `grouped_barplot_with_error_bar` 0.55 if a second categorical exists; 5. scatter 0.50 if >=2 numerics | `plot_recommender.py:209-236` | box wins over bar; violin is the same rec (`kind` default `box`, `registry.py:119`); bar draft carries `color` = group column but the renderer ignores it |
| raw observations present | no rule | not found | the engine never inspects n per group or replicate structure; `dot_strip_plot`, `beeswarm_plot`, `raincloud_plot` are never recommended (grep in `plot_recommender.py`: not found) |
| small n (3-10) | no rule | not found | no "show all points / avoid bars" logic |
| `paired` | `paired_slopegraph` 0.75; `boxplot_or_violin_with_points` 0.70 with paired-test hint | `plot_recommender.py:194-206` | the slopegraph renderer cannot run the paired test itself |
| after statistics run | `boxplot_or_violin_with_points` promoted to 0.85 | `recommendation_runner.py:69-81` | |
| wide numeric block | transform -> box/violin (`tf_box_columns`) | `transform_recommender.py:60-65` | |
| categorical only | count bar (`tf_count_bar`) via `barplot_with_error_bar` | `transform_recommender.py:87-98` | |
| suggested tests | delegated to `statistics.recommend_tests` | `stat_recommender.py:15-30`; `test_registry.py:60-118` | |

## 10. StyleProfile tokens honoured (`styles/engine.py:159-217`)

Applied to all seven renderers through `style.apply()` / `rc_params()` (`engine.py:238-291`):
`font_family`, `base_font_pt`, `axis_font_pt`, `tick_label_pt`, `legend_pt`, `legend_title_pt`,
`title_font_pt`, `title_font_weight`, `font_weight`, `text_color`, `spine_width_pt`
(axes.linewidth), `line_width_pt` (lines.linewidth), `tick_width`, `tick_length`,
`tick_direction`, `show_top_spine`, `show_right_spine`, `grid`, `grid_width`, `grid_alpha`,
`legend_frameon`, `export_dpi`; plus `single_column_width_mm`, `double_column_width_mm`,
`default_width_mm` via `figure_size` (`base.py:127-142`, `engine.py:219-232`) and the tick
tokens again via `style_axes` (`base.py:261-280`).

Read directly by renderer:

| token | box_violin | barplot | grouped_barplot | dot_strip | beeswarm | raincloud | paired_slope | stats overlay |
|---|---|---|---|---|---|---|---|---|
| `palette` / `color_for` | `:49,62,76` | `:52` | `:71` | `:69,74` | `:73,78` | `:55` | `:69,73` | - |
| `spine_width_pt` | `:52,65,69` | - | - | - | - | `:74,78` | - | `stats_overlay.py:65` |
| `line_width_pt` | `:55,60` | - | - | `:82` | `:85` | `:70` | `:81` | - |
| `marker_size` | - (uses `point_size`) | - | - | `:70,74` | `:74,78` | `:81` | `:85` | - |
| `marker_edge_width` | - (0.2 fixed) | - | - | `:71,75` | `:75,79` | `:82` | `:88` | - |
| `marker_alpha` | - (0.8 fixed) | - | - | `:72,76` | `:76,80` | `:83` | - | - |
| `text_color` | - | - | - | `:81,84` | `:84,87` | `:69` | - | `stats_overlay.py:66,251` |
| `bar_edge_width` | - | `:59` | `:73` | - | - | - | - | - |
| `errorbar_line_width` | - | `:62-63` | `:75-76` | `:85` | `:88` | - | - | - |
| `errorbar_capsize` | - | `:61` | `:74` | `:85` | `:88` | - | - | - |
| `annotation_pt` | - | - | - | - | - | - | - | `stats_overlay.py:64,250,293` |
| `legend_frameon`, `legend_ncol`, `legend_outside` | - | - | `:104` via `place_legend` (`base.py:363-364,389`) | `:100` | `:103` | - | `:101` | - |

Tokens defined but not honoured by any of these renderers: `regression_line_width`,
`sequential_cmap`, `diverging_cmap`, `panel_label_pt`, `legend_loc` (all legends here are
`force_outside=True`, so `legend_loc` is only reachable through `layout.legend_location`,
`registry.py:365-388`). `capabilities.py` has no entries for `dot_strip_plot`, `beeswarm_plot`
or `paired_slopegraph`, so they receive the all-true default (`:181-186`); `box_violin` is
declared `supports_marker_size=False` (`:100-102`) because it reads `point_size` instead.

---

## 11. Prioritised gap list

Ordered by what blocks a journal-style "few groups, all observations shown, bracketed P" figure.

1. **Raw observations on bars (P0).** `barplot_with_error_bar` and `grouped_barplot_with_error_bar`
   draw no points (`barplot.py:49-90`, `grouped_barplot.py:50-77`). Needed: `points`
   (none/jitter/centred/beeswarm), reusing `_v04_shared.jitter` / `beeswarm_offsets`, with the
   stats `tops` raised to `max(mean+err, max observation)` so brackets clear the dots.
2. **Explicit summary + error recording (P0).** Bars always mean (`base.py:73-75`); CI is
   `1.96*SEM` (`:93-95`); dot/beeswarm `summary="mean"` silently implies SEM (`_v04_shared.py:234`).
   Needed: a `summary` option (`mean|median`) on bars, a separate `error` option on dot/beeswarm
   (`sd|sem|ci95|iqr|none`), t-based CI, and `meta["summary"]`, `meta["error"]`,
   `meta["error_definition"]`, per-group `n` written by every renderer (only box_violin records
   `group_n`, `box_violin.py:101`).
3. **Statistics wiring for the point-based renderers (P0).** `dot_strip`, `beeswarm`, `raincloud`,
   `paired_slopegraph` never call `run_and_annotate`; the paired tests in the engine
   (`runner.py:93-107`) are unreachable from the paired plot. Needed: positions/tops maps and the
   `run_and_annotate(... mode="bracket")` call in each, matching `box_violin.py:90-96`.
4. **Bracket auto-placement defaults (P1).** Geometry exists (`stats_overlay.py:39-199`) but:
   (a) `test="auto"` with >=3 groups yields an omnibus panel and no brackets because `posthoc`
   defaults to `False` (`test_registry.py:91-93`, `runner.py:248-252`); (b) the level-0 start is
   the global max rather than per-pair (`:153,173`); (c) intermediate taller groups are not
   checked (`:76-81`); (d) tick height / gap are fractions of y-range, not points. Needed: default
   `posthoc=True` (or auto pairwise) for the group-comparison plot types, per-pair local starts
   with an "everything spanned" check, and point-based geometry.
5. **Secondary grouping for box/violin/dot/beeswarm/raincloud (P1).** Only `grouped_barplot`
   dodges a second factor (`grouped_barplot.py:59-77`); `dot_strip`/`beeswarm` only recolour
   within one cloud (`dot_strip.py:64-72`); `box_violin`/`raincloud` accept `x`,`y` only
   (`ui_hints.py:18,38`); `barplot.color` is inert (`barplot.py:29,52,92`). Needed: a `group`
   (hue) role with dodge offsets, `(x_level, group)` position keys (the stats bridge already
   accepts them, `stats_integration.py:62-81`), and a legend.
6. **n labels (P1).** Not found in any renderer; only inside a comparison label via
   `annotation.content="flags"` + `show_n` (`method_reporting.py:345-346`). Needed: a shared
   `show_n` option (`none|below|above|tick|legend`) that reads the actual per-group counts.
7. **Arbitrary / unequal n and adaptive rules (P1).** Unequal n is handled numerically
   (`pairwise.py:34`, `validators.py:53-63`) but visually nothing adapts: point size/alpha/jitter
   are fixed (`box_violin.py:73-77`, `dot_strip.py:63`, `beeswarm.py:67`). Needed: n-aware
   defaults (larger opaque markers at n<=10, smaller/translucent at n>=30, jitter width scaled
   by n), and a `barplot` warning when n<3 mirrors `barplot.py:46-47` for the grouped variant.
8. **Box / violin / point styling tokens (P2).** Hard-coded: box width 0.5, edge black, alpha 0.5,
   point edge black 0.2, alpha 0.8 (`box_violin.py:58-77`); raincloud box 0.14/white
   (`raincloud.py:68-74`). Needed options (style scope): `box_width`, `box_fill`
   (`filled|outline`), `box_edge_color`, `box_line_width`, `median_line_width`, `whisker_range`
   (`1.5iqr|minmax|p5p95`), `cap_width`, `show_outliers` independent of `points`,
   `point_edge_color`, `point_edge_width`, `point_alpha`, `point_shape`, `point_fill`
   (`filled|open`), `jitter_width`, `jitter_seed`, `violin_bandwidth`, `violin_inner`; and
   `StyleProfile` tokens `box_line_width`, `median_line_width`, `point_edge_color` so a lab
   preset can carry them.
9. **Orientation (P2).** No renderer supports horizontal layout (grep `orient|barh` in the seven
   files: not found). Needed: an `orientation` (`vertical|horizontal`) style option plus a
   horizontal bracket mode in `stats_overlay.annotate_pairwise` (currently y-only, `:180-185`).
10. **Category order and spacing (P2).** All renderers use first-seen order (`box_violin.py:35`,
    `barplot.py:36`, `_v04_shared.py:245`); no `order`, `reference_first`, or `group_gap`
    option; `ui_hints.py` has an `order` option only for `upset_plot` (`:272`).
11. **Axis policy (P2).** Bars get a zero baseline only through matplotlib sticky edges
    (`barplot.py:73`); none of the seven call `apply_axis_overrides`, so `y_min/y_max/y_ticks`
    are silently ignored (only forest/histogram/survival use it). Needed: explicit
    `baseline_zero` for bars, `apply_axis_overrides` with the observation extent so a user range
    can never crop points.
12. **Recommendation engine (P2).** Never recommends `dot_strip_plot`, `beeswarm_plot` or
    `raincloud_plot`; no n-per-group rule; bar rec (0.60) sits close behind box (0.72)
    (`plot_recommender.py:209-236`). Needed: a "replicate-level data, n<=~30 per group" rule
    that ranks dot/box-with-points above bars and attaches the pairwise stats hint.
13. **Consistency / honesty items (P3).** `paired_slopegraph` UI defaults differ from renderer
    fallbacks (`ui_hints.py:402-408` vs `paired_slope.py:81-85`); `capabilities.py` lacks entries
    for the v0.4 point plots; `raincloud` warns at >6 groups but exposes no options beyond tick
    rotation (`ui_hints.py:299`).
