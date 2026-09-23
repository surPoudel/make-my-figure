# Showcase capability audit - what the application supports today

Read from `make_my_figure_core/ui_hints.py` on the tutorial branch after merging
`feature/evidence-derived-journal-presets` (2026-09-23). "main" refers to `main` at 84458dd,
the v1.1.1 candidate, which the pilot was first built on.

## Individual observations and jitter

| control | main (v1.1.1 candidate) | this branch (presets branch merged) | plots |
|---|---|---|---|
| box + points | `points` on/off, `point_size` (pt²) | `points`, arrangement, jitter width, size, marker, fill, edge, edge width, opacity | Box / violin plot with points |
| violin + points | via `kind = violin` | `kind` box / violin / box+violin / summary, `violin_alpha` | Box / violin plot with points |
| bar + points | **not available** | `points` (default off) with the same point controls | Bar plot with error bars, Grouped bar plot |
| grouped box / violin | **not available** | `hue` role (dodged boxes / violins) | Box / violin plot with points |
| grouped bars | yes (`x`, `group`) | yes, plus observations | Grouped bar plot with error bars |
| strip / jitter | `jitter` on/off, `summary` | arrangement jitter / centered / beeswarm, jitter width | Dot / strip plot, Beeswarm, Raincloud |
| marker size | box only (`point_size` 8 pt²) | `point_size` 0-120 pt² (0 = adaptive to n) | all six |
| marker shape | **not available** | `point_marker` o, s, ^, D, v | all six |
| marker fill | **not available** | `point_fill` filled / open | all six |
| marker edge | **not available** | `point_edge` dark / same / none | all six |
| marker edge width | **not available** | `point_edge_width` 0-3 pt | all six |
| opacity | **not available** | `point_alpha` 0-1 (0 = adaptive) | all six |
| jitter amount | **not available** | `point_jitter_width` 0-0.9 of the group spacing | all six |
| group spacing | **not available** | `group_spacing` 0.5-2.0 | Box / violin |
| unequal replicate counts | yes | yes; `show_n` labels below / above / legend | box, bars |
| statistics brackets | yes (6. Statistics) | yes; bracket geometry in points, stacked to avoid collisions | box, bars, strip, beeswarm, raincloud, paired |
| P-value labels | yes (stars, P, adjusted P, effect, custom) | same | same |
| multiple comparisons | yes (BH, Bonferroni, Holm) | same | same |

Verdict: on main the jitter showcase could not be honest beyond point size, so the tutorial
branch now carries the presets branch. Everything shown in `tutorial/showcase/` and the
observations chapter is rendered from these controls.

## Publication presets

| item | main | this branch |
|---|---|---|
| user presets (style / full) with Apply | yes | yes |
| evidence-derived publication presets | **none** | 12 experimental presets in `style_profiles/experimental_publication_presets/`: Single column 57 mm (S), 85 mm (C), 89 mm (N); Full width 174 mm (C), 183 mm (N), 184 mm (S); Bar + observations (jittered), Bar + observations (open circles), Box + observations (light fill), Box + observations (outline), Many observations per group, Violin + observations |
| preview before apply | **none** | *Preview & apply...* dialog (before / after render on the loaded data, change list) |
| opt-in | - | "Show experimental presets" checkbox; experimental presets are never applied without the preview |

Naming: the letters (S), (C), (N) denote the evidence set used to derive the values; the
presets are **experimental**, carry a provenance block and an evidence class per value, and are
not approved by, or compliant with, any journal. The tutorial and the slides say so wherever a
preset is shown.

## Other showcase plots

| desired | current behaviour | code | implement before completion? |
|---|---|---|---|
| Scatter: marker size, edge colour, edge width per point | no plot-level option; marker size and edge come from the Publication style profile (② Typography / ③ Axes) and apply to the whole figure; the `color` role sets the palette | `plots/scatter.py`, `ui_hints.OPTIONS["scatterplot_with_regression"]` | no - the style profile controls are enough for a before/after; flagged for the presets project |
| Scatter: confidence band around the regression line | **not supported**; the fit shows line + stats box only | `plots/scatter.py` | no - stated in the tutorial as unavailable |
| Volcano: marker size option | not a plot option; marker size follows the style profile; colours, cutoffs, labels, arrows, label box are options | `plots/volcano.py` | no - style profile suffices |
| Heatmap: group colour strip | available only through *Define groups... > Heatmap / PCA (keep the matrix + add a group color strip)* or the Matrix workflow, not as a plain option | `apps/desktop_app/grouping_panel.py`, `plots/heatmap.py` | no - shown via Define groups in the tutorial |
| Heatmap: dendrogram drawn with the heatmap | the Clustered heatmap reorders rows / columns but does not draw the tree; the tree is a separate plot type (Hierarchical clustering dendrogram) or the combined Hierarchical clustering (heatmap + clusters) plot | `plots/heatmap.py`, `plots/hierarchical_clustering.py` | no - the tutorial uses the combined plot type where a tree is wanted |
| Kaplan-Meier: line width, risk table | line width from the style profile; **no number-at-risk table** | `plots/survival.py` | no - flagged |
| Forest plot: marker by weight | `reference`, `log_scale` only | `plots/forest.py` | no |

## Gaps that limit the demonstrations (flagged, not hidden)

1. **Scatter has no per-point marker controls** beyond the style profile; the same-data scatter
   contrast is therefore typography, palette, marker size via the profile, and regression
   statistics - not edge or fill.
2. **No confidence interval for regression** anywhere in the application.
3. **No number-at-risk table** for Kaplan-Meier.
4. **Presets are experimental** and live on an unmerged branch; the tutorial says so.
5. On **main alone**, the observations and presets chapters cannot be reproduced. If the author
   decides against merging the presets branch, those chapters must be removed rather than
   softened.
