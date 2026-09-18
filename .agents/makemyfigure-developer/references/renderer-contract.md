# Renderer contract (main, documented 2026-09-17)

A renderer is one module in `make_my_figure_core/plots/`. The contract below is what
`plots/registry.py::render` and the shared helpers in `plots/base.py` actually assume.
Read `plots/barplot.py` (99 lines) and `plots/box_violin.py` (105 lines) as the canonical
minimal examples; `plots/scatter.py` shows the corner-panel statistics mode and
click-to-identify metadata; `plots/pca.py` and `plots/network_graph.py` show `aux` tables.

## 1. What the module must define

```python
PLOT_TYPE = "snake_case_identifier"          # the key used everywhere (spec["plot_type"])

def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult: ...
# optional variant, detected by inspect.signature in registry.render (registry.py:330):
def render(spec, df, style, aux: Optional[Dict[str, pd.DataFrame]] = None) -> RenderResult: ...
```

- `spec` is an already-validated PlotSpec dict (schema + known type/style). The renderer
  must not mutate it.
- `df` is the loaded `pandas.DataFrame` for `spec["input_table"]`. The renderer must not
  mutate it; every existing renderer starts with `work = df.copy()`.
- `style` is a resolved `StyleProfile` with `spec["style"]` overrides already applied by
  the registry (`style.with_overrides`). Renderers never read `spec["style"]`.
- `aux` (only if declared) is `{name: DataFrame}`; the registry passes `aux or {}`.
  Names in use on main: `"metadata"` (PCA sample metadata) and `"nodes"` /
  `"node_attributes"` / `"node_table"` (network node attributes). See data-mapping.md.

### RenderResult (`plots/base.py:29`)

| Field | Type | Meaning |
|---|---|---|
| `figure` | `matplotlib.figure.Figure` | The figure. Create it inside `with style.apply():`. |
| `metadata` | `dict` | Reproducibility record; start from `base_metadata(...)`. |
| `warnings` | `list[str]` | Human-readable, non-fatal notes. Registry appends to it. |
| `stats_report` | `StatsReport \| None` | Returned by `run_and_annotate`; registry uses it to write `*.stats_spec.json`. |

Hard failures raise `RenderError` (`plots/base.py:24`) with a message that names
`PLOT_TYPE`, the offending mapping key/column and, where useful, the available columns
(`require_columns` already formats this).

## 2. Reading the spec

- **mapping** - `get_mapping(spec, key, default=None, *, required=False, context=PLOT_TYPE)`
  (`base.py:52`). Column roles and plot options live in the same `spec["mapping"]` dict;
  `required=True` raises `RenderError` on a missing/empty value. Validate columns with
  `require_columns(df, [cols], context=PLOT_TYPE)` and convert with
  `coerce_numeric(df, col, context=PLOT_TYPE)` (raises when nothing is numeric).
- **layout** - `spec.get("layout", {})`. Keys renderers read directly: `x_label`, `y_label`,
  `title`, `column_width` (`default|single|onehalf|double`), `aspect`, and (via
  `apply_axis_overrides`) `x_min/x_max/y_min/y_max/x_scale/y_scale`. Keys applied
  centrally by the registry after render, so renderers need not handle them:
  `x_tick_rotation`, `y_tick_rotation`, `*_pad`, margins (`apply_publication_layout`,
  `base.py:427`), `legend_location` (`resolve_legend_location` + `place_legend`),
  `auto_fix_layout`.
- **style** - use tokens only: `style.color_for(i)`, `style.palette`, `style.marker_size`,
  `style.line_width_pt`, `style.spine_width_pt`, `style.errorbar_*`, `style.bar_edge_width`,
  `style.annotation_pt`, `style.text_color`, `style.sequential_cmap` / `diverging_cmap`,
  `style.legend_*`. Full field list: `styles/engine.py:134-190`.
- **statistics** - never read `spec["statistics"]` yourself; hand it to
  `stats_integration.run_and_annotate` (section 4).
- **annotations**, **column_annotations**, **source** - registry/heatmap-specific; a new
  renderer ignores them (the registry applies `spec["annotations"]` to `figure.axes[0]`).

## 3. Helpers in `plots/base.py` (and `_v04_shared.py`)

| Helper | Line | Use |
|---|---|---|
| `require_columns(df, cols, *, context)` | 43 | Missing-column `RenderError` with available columns listed. |
| `get_mapping(spec, key, default, *, required, context)` | 52 | Read a role/option. |
| `coerce_numeric(df, col, *, context)` | 61 | `pd.to_numeric(errors="coerce")`, error if all NaN. |
| `summarize_error(values, method)` | 71 | `(mean, err)` for `sem|sd|std|ci95|none`; NaNs dropped. |
| `summarize_band(values, method)` | 98 | `(center, lo, hi)`; adds `iqr` and `range` (median-centred). |
| `figure_size(spec, style, *, aspect)` | 127 | Honours `layout.column_width` / `layout.aspect`; pass to `plt.subplots(figsize=...)`. |
| `apply_axis_overrides(ax, spec, ...)` | 145 | Axis limits / log scales from layout; record what it returns in `meta["axis_overrides"]`. |
| `style_axes(ax, style)` | 261 | Tick params, spine visibility from tokens. Call after drawing. |
| `autorotate_xticklabels(ax, style, rotation=...)` | 281 | Categorical x labels; pass `get_mapping(spec, "x_tick_rotation", "auto")`. Call before `tight_layout`. |
| `place_legend(ax, style, *, title, handles, labels, force_outside, loc, location)` | 353 | The only sanctioned way to draw a legend. |
| `LEGEND_LOCATIONS`, `resolve_legend_location(spec, style)` | 395/413 | Named positions shared by all plots. |
| `apply_publication_layout(fig, ax, spec, style)` | 427 | Applied by the registry; renderers may call it for secondary axes. |
| `dedupe_labels_by_distance`, `choose_label_column`, `resolve_point_labels`, `build_pickable_points`, `nearest_pickable` | 546-620 | Click-to-identify support (`meta["pickable_points"]`). |
| `base_metadata(spec, style, df, *, used_columns)` | 640 | Common metadata block (section 5). |

`plots/_v04_shared.py`: `classify_matrix_columns`, `resolve_value_columns`
(honours `mapping["value_columns"]`), `pick_column(df, aliases)`, `numeric_matrix`,
`linkage_matrix`, `jitter`, `beeswarm_offsets`, `summary_stat`, `neg_log10`,
`ordered_unique` (first-seen order, drops NaN/blank). Reuse these instead of re-implementing.

Standard body shape (from `barplot.py`): resolve mapping -> `require_columns` -> `work =
df.copy()` -> compute geometry -> `with style.apply(): fig, ax = plt.subplots(figsize=
figure_size(...))` -> draw -> labels/title -> `style_axes` -> `fig.tight_layout()` ->
`run_and_annotate(...)` -> build metadata -> `return RenderResult(...)`.

## 4. Statistics: how results are received and drawn

`plots/stats_integration.py::run_and_annotate(spec, work, style, PLOT_TYPE, *, ax=None,
positions=None, tops=None, mode="bracket", corner_loc="upper left")`:

1. `normalize_stats_spec(spec.get("statistics"))`; returns `None` when not `enabled`.
2. `statistics.runner.run_statistics(df, stats_spec, plot_type=, mapping=)` -> `StatsReport`.
   Column resolution is in `runner.resolve_columns` (`runner.py:36`): by default
   `value=mapping["y"]`, `group=mapping["x"] or mapping["group"]`, `time`, `event`; a
   handful of plot types have explicit overrides there. A new plot type whose roles
   differ from `x`/`y`/`group` needs an entry in `resolve_columns` (and, for the advisory
   suggestions, in `statistics/test_registry.recommend_tests`).
3. Draws via `plots/stats_overlay.py`:
   - `mode="bracket"` - `positions` = `{str(category): x}` (or `{(str(x_level), str(group)): x}`
     for within-x designs), `tops` = data top per key. Pairwise two-group results become
     brackets (`annotate_pairwise`) or per-bar labels (`annotate_above`, placement
     `above_bar`); omnibus results go to a corner panel.
   - `mode="corner"` - text panel at `corner_loc` (scatter, stacked).
   - `mode="survival"` - text panel, location from `statistics.annotation.location`.
4. Returns the `StatsReport`. The renderer stores `meta["statistics_report"] =
   report.to_dict()` and passes `stats_report=report` to `RenderResult`.

Every label drawn is backed by a stored `StatResult` (`statistics/annotations.AnnotationItem`).
Renderers on main wired to statistics: barplot, grouped_barplot, box_violin, scatter,
survival, stacked; count them with
`grep -l run_and_annotate make_my_figure_core/plots/*.py`.

## 5. Metadata conventions

`base_metadata` provides: `plot_type`, `style_profile`, `data_columns_used`, `n_rows`,
`statistics` (echo of the spec block), `export_dimensions`, `disclaimer`, and `source`
(worksheet provenance) when present. The registry then adds `spec`, `publication_check`,
`layout_qc`, and optionally `style_migration`, `n_manual_annotations`,
`layout_autofix_applied`. `write_sidecar` strips `spec` from `render_metadata`.

Renderer-specific keys follow these observed conventions (grep `meta\["` in `plots/`):
- Scientific content that a reader would need to interpret the figure: `error_method`,
  `categories`/`groups`/`series`/`x_levels`, `centers`, `group_n` (n per group; also seen
  as `n_groups`, `n_samples`, `n_subjects`, `n_points`, `n_up`/`n_down`/`n_ns`),
  `summary` (which summary overlay), `regression` (fit parameters), `p_cutoff`,
  `lfc_cutoff`, `n_bins`, `normalize`, `scale`, `distance_metric`, `linkage_method`,
  `components` (PCA variance), `reference`, `sort`, `kind`.
- Interaction support: `pickable_points`, `pick_label_key`, `pick_label_column`,
  `pick_offset_key`.
- `statistics_report` when statistics ran.
Values must be JSON-serialisable (round floats, `str()` categories, `None` for NaN).

Warnings: plain sentences appended to a local `warnings: List[str]` and returned; used for
degraded-but-rendered situations (e.g. "Some categories have < 2 replicates; error bars
are zero there.", "Matrix contains missing/non-numeric values; shown as blank cells.").
Never `print`, never `warnings.warn`.

## 6. What a renderer must never do

- Mutate `df` or `spec` (copy first; `base.py` docstring makes this an acceptance criterion).
- Compute inferential statistics itself or print p-values that are not backed by a
  `StatResult` from `run_statistics`. Descriptive summaries (`summarize_error`, an OLS
  line for a scatter, thresholds for a volcano) are allowed; significance annotations go
  through `run_and_annotate`.
- Hard-code aesthetics: no literal colours, font sizes, line widths or marker sizes when a
  `StyleProfile` token exists. `scripts/audit_style_capabilities.py` lists every literal
  colour it finds in renderer source and regenerates `styles/capabilities._CAPS` from what
  the renderer actually reads, so an unused token also means a greyed-out GUI control.
- Draw a legend with raw `ax.legend(...)` outside `place_legend`, or `plt.show()`, or rely
  on global rcParams outside `with style.apply():`.
- Read `spec["style"]`, `spec["statistics"]` (except via `run_and_annotate`) or
  `spec["annotations"]` directly.
- Swallow errors: bad input is a `RenderError`; partial degradation is a warning.

## 7. Declaring options for the UI, and what the frontends do with them

Declarations live in the core, keyed by `PLOT_TYPE`:

- `make_my_figure_core/ui_hints.py::COLUMN_FIELDS[plot_type]` - mapping keys shown as
  column choosers. Keys in `MULTI_COLUMN_FIELDS` (`value_columns`, `survival_columns`)
  get a multi-select. `PCA_METADATA_FIELDS` lists roles read from the metadata table.
- `ui_hints.OPTIONS[plot_type]` - list of `Option(key, label, kind, default, choices,
  minimum, maximum, step, decimals, scope)`; `kind` in `choice|bool|number`; `scope` in
  `style|config` (decides whether a Figure Preset in style mode carries it; default
  `config`). `number` options with `default=None` are "optional/unset".
- `styles/capabilities.py::_CAPS[plot_type]` - which Publication style controls apply
  (regenerate with the audit script; add hand-written reasons/axis flags in the script's
  `_REASONS` / `_NO_AXES`). Unlisted plot types get the axes-based default.

How the frontends discover them (verified in the app sources):

- **Desktop**: `controller.plot_types()` = `[(pt, display_name(pt)) for pt in
  available_plot_types()]`; `controller.column_fields(pt)` and `controller.options(pt)`
  delegate to `ui_hints`. `main.py::_rebuild_mapping_and_options` (line ~2138)
  builds one combo per column field, a `QListWidget` for multi-column fields, and one
  widget per `Option` via `_make_option_widget`. The "Open example" menu iterates
  `controller.plot_types()`. The `--selftest` path iterates `available_plot_types()`.
- **Streamlit**: plot selector from `available_plot_types()`; column choosers from
  `column_fields_for(plot_type)` (= `ui_hints.column_fields` + `EXTRA_COLUMN_FIELDS`
  for PCA colour/shape); a generic loop near line 1064 renders every `ui_hints.options`
  entry not already set by a hand-written widget.

Does adding a plot type require editing a frontend file? For the generic path, **no**:
registering the module in `registry.py` and adding `ui_hints` entries makes the plot
appear with its column choosers and options in both apps. There are, however,
hard-coded sets you must extend in specific cases:

- Matrix-style plots (row-id + value columns): `apps/desktop_app/main.py::_MATRIX_PLOT_TYPES`
  (line ~112) and `apps/streamlit_app/streamlit_app.py::_MATRIX_PLOT_TYPES_EARLY` /
  `_MATRIX_PLOT_TYPES` (lines ~584 and ~611) gate the value-column picker.
- Plots that need an aux table from the bundled example in **Streamlit**: only
  `network_graph` (line ~1224) and PCA metadata are passed; desktop passes every aux
  table generically (`controller.render`).
- Optional niceties: desktop `_group_value_prefill` GV set (line ~2105); Streamlit
  per-plot `if plot_type == ...` widget blocks (lines ~640-800) - not required because
  of the generic loop.
- Tests pinning the plot count: `tests/test_renderers_m2.py:23` and
  `tests/test_desktop_controller.py:29` assert `len(...) == <N>` and must be bumped.

## Verify this is still current

```bash
# renderer signatures and aux users
grep -n "^def render" make_my_figure_core/plots/*.py | grep -v registry
grep -ln "aux" make_my_figure_core/plots/*.py
# helpers exported by base.py
grep -n "^def \|^class \|^[A-Z_]* = " make_my_figure_core/plots/base.py
# frontend hard-coded plot-type sets and count tripwires
grep -n "_MATRIX_PLOT_TYPES\|== 38\|== 3[0-9]" apps/desktop_app/main.py apps/streamlit_app/streamlit_app.py tests/test_renderers_m2.py tests/test_desktop_controller.py
# how options reach the GUIs
grep -n "ui_hints\.\(options\|column_fields\)" apps/desktop_app/controller.py apps/streamlit_app/streamlit_app.py
```

## Column resolution for statistics

A new plot type whose roles differ IN MEANING from the bar/box convention (`x` categorical, `y`
numeric, optional `group`) needs an entry in `statistics/runner.resolve_columns`; that includes every
x-NUMERIC plot (histogram, ridge, ECDF-like plots), because the default would take the numeric column
as the group and find no value column.

## Which renderers to copy from

`barplot.py` and `box_violin.py` follow the whole contract (style tokens only, `place_legend`,
`apply_axis_overrides`, `fig.tight_layout()` BEFORE `run_and_annotate`). Some older renderers predate
parts of it (raw `ax.legend`, literal colours or marker sizes, statistics before layout); when
`find_related_renderers.py` points at one of them, copy its scientific logic but not those habits.
`validate_plot_integration.py` flags direct inferential calls; the style-token rule is checked by
`scripts/audit_style_capabilities.py`.
