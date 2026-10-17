# Group-comparison plots with individual observations (experimental branch)

Bar, box, violin and dot/strip plots that show every replicate over a summary, with statistical
brackets that clear the points. Added on `feature/evidence-derived-journal-presets`; not released.

## The rules these renderers follow

* **n comes from the data.** Every observation in a group is drawn; groups of 6 and 17 are drawn
  as 6 and 17 points. No option sets or hides a replicate count.
* **Bounded adaptation, never removal.** Marker size, opacity and jitter width scale with the group
  size inside fixed limits (`make_my_figure_core/plots/observations.py`, `adaptive_marker`). Above
  60 observations in a group the renderer adds a warning suggesting a distribution plot (violin,
  box, raincloud); the points are still drawn.
* **The summary is explicit.** Bars use `summary` = `mean` (default, unchanged behaviour) or
  `median`; the error choice is `error` = `sem | sd | ci95 | ci95_t | iqr | none`. Both are
  *config* options (not carried by style presets) and both are recorded in the PlotSpec, the render
  metadata (`summary`, `error`, `error_definition`, `group_n`) and the methods sentence. Nothing
  defaults silently to a new choice; `ci95` keeps its previous 1.96 x SEM definition and `ci95_t`
  (Student t, df = n-1) is a new choice.
* **Statistics are the user's.** Presets may set the geometry of brackets (heights, gaps, font,
  line width) but never the test, the comparisons or whether stars or P values are shown.
* **Axes.** Bars keep a zero baseline when all values are non-negative (recorded as
  `baseline_zero`); box/violin plots do not force one. Observations are never cropped: a `y_max`
  that would hide points is refused rather than applied.

## Options (all in `mapping`, declared in `ui_hints`)

Shared observation options (style scope) on `boxplot_or_violin_with_points`, `barplot_with_error_bar`,
`grouped_barplot_with_error_bar`, `dot_strip_plot`, `beeswarm_plot`, `raincloud_plot`:

| key | values / default |
|---|---|
| `points` | show individual observations (bars: off by default to keep old renders identical; box/violin: on) |
| `point_arrangement` | `jitter` (default) / `centered` / `beeswarm` |
| `point_jitter_width` | fraction of category spacing, 0.35 |
| `point_size` | pt², 0 = adaptive from the style's marker size |
| `point_marker` | `o s ^ D v` |
| `point_fill` | `filled` / `open` |
| `point_edge` | `dark` / `same` (group colour) / `none` |
| `point_edge_width` | pt, 0.5 |
| `point_alpha` | 0 = adaptive |

Box/violin (`boxplot_or_violin_with_points`): `kind` (`box`, `violin`, `box+violin`, `summary`),
`box_width`, `box_fill` (`light` default, `filled`, `outline`), `box_line_width`, `median_line_width`,
`whisker_cap_width`, `show_outliers`, `violin_alpha`, `orientation` (`vertical`/`horizontal`),
`group_spacing`, `category_order` (config: `data`, `alphabetical`, `median_ascending`,
`median_descending`), `show_n` (`none`, `below`, `above`, `legend`), and an optional `hue` column
role that dodges boxes within each category (statistics then run within each category through the
existing StatsSpec `subgroup_column`).

### Facet grids (`facet_row`, `facet_col`)

On `boxplot_or_violin_with_points` and `lineplot_timecourse_with_error_band`, two optional
column roles split the figure into a grid of panels - one per level of the row column, one
per level of the column column, both at once for a grid (ggplot's `facet_grid(row ~ col)`).
A 2 species x 2 ages x 3 nitrogen x 4 months design reads as `facet_row = Age`,
`facet_col = Species`, `x = Month`, `hue`/`color` = nitrogen. Built once for both plots by
`plots/facets.py`:

| what | behaviour |
|---|---|
| categories, colours | one category order (`category_order`) and one colour per hue level across every panel |
| value axis | shared across panels and fitted to all of them; `facet_share_y` (style) = false gives each panel its own |
| strips | `Species: Species_A` above columns and beside rows; `facet_labels` (style) = `value` drops the column name |
| tick labels | outer panels only (shared axes); `show_*_tick_labels` and tick angle act on every panel |
| x / y label, title, legend | one of each for the grid, carried by an invisible host axes (label `<facet-host>`) that spans the panels, so legend location/outside/geometry, label padding and visibility and title padding act on the grid exactly as on a single plot; a key above or below the grid is laid out in one row |
| log axes, axis range | applied to every panel; limits fitted to the values of all panels sharing the axis |
| statistics | run within each panel (brackets drawn per panel; each result records its panel in `extra["facet"]`; P values adjusted within the panel). With the statistics panel's **Also test across the whole grid** (`statistics.facet_scope = "figure"`), the test also runs once over every panel: an ANOVA gains the facet variables as factors - `Growth ~ Month * Age * Species` - through the validated factorial engine (at most three factors; four is explained, not computed); a pairwise or one-way test pools the panels. Reported in the statistics table and method sentence, not drawn (a bracket cannot span panels) |
| bracket headroom | brackets are stacked per panel from the same starting limits (stacking them on the shared axis one panel after another compounded: 115 where 107 is needed). A panel is shorter than a single plot, so a stack of all-pairs brackets takes more of its range; prefer `within_x` comparisons or a taller figure |
| strip labels | wrapped to two lines, then shrunk (to 70 % of the tick size) to fit the panel; still too long is reported |
| automatic size | panels grow the figure up to 10 x 10 in, then shrink instead, with a note once a panel is narrower than 1.3 in |
| empty combination | the panel is kept and reads "no observations" |
| limits | at most 12 levels per direction; a facet column equal to the x or hue column is allowed but warned |

Facet options are shown only once a facet column is mapped (`Option.requires`). A figure with
no facet column never reaches this code and renders exactly as before. Line plots can also draw
the error as `error_display = bars` (mean +/- SE/SD/CI as capped bars) instead of a band.
Example data: `tests/fixtures/plant_growth_facets.csv` (mock plant growth, 240 rows). Tests:
`tests/test_facet_grids.py`, `tests/test_desktop_facets_and_builder.py`.

Bars (`barplot_with_error_bar`, `grouped_barplot_with_error_bar`): `summary` (config), `error`
(config), `bar_width`, `bar_fill` (`filled`/`outline`), `bar_edge_width`, `bar_alpha`, `error_cap`,
`show_n`, `orientation`; the `color` role now colours bars by a second column.

## Statistical brackets

`plots/stats_overlay.annotate_pairwise` starts each bracket above the highest drawn element among
the groups it spans (points, error bars, whiskers, earlier brackets), stacks brackets with collision
avoidance, uses point-based geometry (derived from the annotation font size and line width, with
`*_pt` overrides; legacy `*_frac` values still honoured), expands the axis so the top label fits, and
supports horizontal orientation. Statistics now also run for `dot_strip_plot`, `beeswarm_plot`,
`raincloud_plot` and `paired_slopegraph` (paired tests) when `statistics.enabled` is true.

## Presets and previews

The `gc_*` experimental presets (`docs/EXPERIMENTAL_PUBLICATION_PRESETS.md`) encode the common
representations found in the corpus (bar + jittered filled points; bar + open circles; outline box +
points; light-filled box + points; violin + points; dense groups). Preview them on your own data
through the preset dialog; `preset_preview.preview_gallery` renders several on the same data.

## Test data and acceptance

`examples/group_comparison_test_data/` (synthetic, CC0; 2/3/4 groups, n = 3-50, unequal 5/8, 6/17,
4/9/13, a 2 x 3 design, one extreme observation, overlapping and separated groups).
`scripts/group_comparison_visual_acceptance.py` renders every gc preset x dataset x width with
statistics on and reports overlap/clipping/legibility (`reports/journal_presets/group_comparison_acceptance/`).
`tests/test_preset_scientific_identity.py` proves the numbers do not change under a preset.

## Requirements

The box/violin renderer works on every matplotlib release the package supports (`>= 3.6`): it passes
`orientation=` to matplotlib 3.10+ and `vert=` to older releases, drawing identical geometry either way
(`reports/journal_presets/matplotlib_compat_check.md`).
