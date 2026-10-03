# Figure Preset system - current capability audit

Branch `feature/evidence-derived-journal-presets`, read-only audit of the worktree. Companion table:
`reports/journal_presets/current_preset_capability_audit.csv` (118 rows, one per property/control).
All line numbers refer to files in this worktree at the time of the audit.

## 1. The `.mmfpreset.json` schema (format_version 1)

There is no JSON Schema file for presets (`schemas/` holds only `plot_spec.schema.json` and
`figure_package_manifest.schema.json`). The de-facto schema is the dict built by `extract_preset`
(`make_my_figure_core/presets.py:239-263`) and checked by `validate_preset` (`presets.py:438-458`).

Top-level fields, both modes:

| field | source | notes |
|---|---|---|
| `format` | `"make_my_figure.figure_preset"` (`presets.py:57`) | anything else refused (`:441`) |
| `format_version` | `1` (`presets.py:58`) | newer refused, no migration hooks (`:444-451`) |
| `name`, `description` | caller | name -> library file name via `safe_filename` (`:533-536`) |
| `mode` | `"style"` or `"full"` (`:65`) | |
| `plot_type` | spec | compatibility key |
| `journal_style` | spec, default `"publication"` | always re-applied (`:335-336`) |
| `created`, `app_version` | generated | informational |
| `style` | `spec["style"]` filtered to `STYLE_TOKEN_KEYS` (`:103-112`, `:203-212`) | unknown keys dropped with a `notes` entry |
| `layout` | `spec["layout"]` minus `title/x_label/y_label` (`:72-83`, `:173-184`) | unknown layout keys default to style |
| `options` | mapping keys whose `ui_hints.Option.scope == "style"` plus colorbar extras (`:152-170`, `:90-92`) | |
| `output` | `formats`, `width_mm`, `height_mm`, `dpi` (`:95`) | |
| `statistics_display` | `statistics["annotation"]` only (`:98`) | |
| `notes` | optional list | |
| `universal` | optional bool, set by `universal_preset_from` (`:421-431`) | |

Full mode adds: `mapping_roles` (column roles from `ui_hints.column_fields` + `value_columns`
+ PCA metadata roles, `:141-149`), `config_options` (config-scoped **and unregistered** mapping
keys, `:257`), `labels` (`title`, `x_label`, `y_label`), `statistics` (analysis block, only when
`enabled`, minus `source`/`_annotation_info`), `annotations` (manual annotation layer).

Neither mode carries `input_table`, `source`, row values, `selected_points`, `selected_labels`,
`label_offsets`, `point_offsets` or `sets` (`MAPPING_DATA_KEYS`, `:87-89`).

A second, unrelated file kind exists for the Figure Builder: `.mmflayout.json`
(`make_my_figure.figure_layout_preset`, `presets.py:61-63`, `:651-775`).

## 2. Style mode vs full mode

- **style**: `style`, `layout` (geometry only), `options` (style-scoped), `output`,
  `statistics_display`, `journal_style`. Cross-plot-type apply is allowed: universal parts are
  written, plot-specific options that are not registered for the target are skipped and listed,
  and a warning is added (`presets.py:320-328`, `:349-357`).
- **full**: everything above plus `mapping_roles`, `config_options`, `labels`, `statistics`,
  `annotations`. Cross-plot-type apply raises `PresetError` (`:321-325`). Roles are applied only if
  the new table has the column; otherwise `unresolved_roles` is populated and nothing is substituted
  (`:286-294`, `:371-383`). Statistics column keys are checked the same way (`:393-402`).

Scope of a plot option is declared at the `Option` (`ui_hints.py:62-89`); default is `config`, so a
new option can only reach a style preset by explicit `scope="style"`. Tests pin thresholds to
config (`tests/test_figure_presets.py:67-77`) and visual options to style (`:80-86`).

## 3. Compatibility rules

1. `validate_preset` on every apply/save/load.
2. `preset["plot_type"] == spec["plot_type"]` decides "same type". Style presets of another type
   apply universal parts; full presets of another type are refused; `strict_plot_type=True`
   refuses any mismatch (no frontend passes it).
3. `options` are filtered against `ui_hints.options(target)` plus the colorbar extra keys
   (`presets.py:351-357`).
4. **Capabilities are not consulted by `apply_preset`.** `styles/capabilities.py` is used only to
   *warn* at render time (`registry.py:320-336`) and to print a caption in Streamlit
   (`streamlit_app.py:1175-1180`). `filter_style_controls_for_plot`, `applicable_controls` and
   `validate_style_controls_for_plot` have no callers outside their module. Its `_UNIVERSAL`
   set names keys that are not real tokens (`dpi`, `figure_width_mm`, `background`,
   `panel_background`; `capabilities.py:63-67`), and `STYLE_CONTROL_CAPABILITY` mixes style tokens
   with mapping options (`node_color`, `edge_color`, `colorbar_label`; `:45-60`).
5. `PresetStore.list(plot_type)` shows same-type presets plus any `universal` preset (`:598-600`).

## 4. Global vs plot-specific

Global (apply to any plot type): the 36 `STYLE_TOKEN_KEYS`, the 26 `LAYOUT_STYLE_KEYS`, `output`,
`statistics_display`, `journal_style`. Plot-specific: everything in `options` /
`config_options` (mapping namespace), including colorbar geometry, which the UIs write into
`mapping` even though it is also accepted as a layout key (`heatmap.py:462-470`).

Namespace overlaps worth knowing for a journal library:
- `x_tick_rotation` and `y_label_pad` exist both as layout keys and as per-plot mapping options
  (`ui_hints.py:106-107`, `:160`, `:355`).
- `y_label_rotation` is in `LAYOUT_STYLE_KEYS` (`presets.py:76`) but heatmap/clustering read it from
  `mapping` only (`heatmap.py:448`, `hierarchical_clustering.py:94`); a layout-level value is a no-op.
- `legend_loc` is a style token (`engine.py:177`) and a lollipop mapping option (`ui_hints.py:278`).
- `x_scale`/`y_scale`/`colorbar_label` are unknown layout keys and therefore travel in *style*
  presets (`presets.py:183`), although the first two change axis semantics and the last is text
  about the data.
- `ui_hints.OPTIONS` defines `manhattan_plot`, `paired_slopegraph` and `swimmer_plot` twice
  (`ui_hints.py:298/401`, `:317/390`, `:329/410`); the later literal wins, so this is cosmetic today.

## 5. Style tokens - how they reach renderers

`registry.render` loads the profile, applies `spec["style"]` through `StyleProfile.with_overrides`
(`engine.py:261-290`), and every renderer wraps drawing in `style.apply()` (an `rc_context` from
`rc_params()`, `engine.py:206-259`). Tokens therefore reach renderers three ways:

- **rcParams only** (all 39 renderers, no direct read): `font_family`, `base_font_pt`,
  `font_weight`, `grid`, `grid_width`, `grid_alpha`, `legend_frameon` (also `place_legend`).
- **rcParams + shared helper**: `tick_label_pt`, `tick_width`, `tick_length`, `tick_direction`,
  `show_top_spine`, `show_right_spine` via `style_axes` (31 renderers, `base.py:261-278`);
  `legend_loc`, `legend_outside`, `legend_ncol`, `legend_frameon` via `place_legend`
  (17 renderers, `base.py:353-390`).
- **direct reads** (from a regex scan of `make_my_figure_core/plots/*.py`): `color_for`/palette 33,
  `line_width_pt` 21, `marker_size` 18, `spine_width_pt` 17, `text_color` 14,
  `marker_edge_width` 13, `tick_label_pt` 10, `marker_alpha` 10, `axis_font_pt` 9,
  `annotation_pt` 8 (+ `stats_overlay.py:64`, `annotations.py:115`), `legend_pt` 7,
  `title_font_pt` 7, `sequential_cmap` 6, `errorbar_line_width` 4, `errorbar_capsize` 4,
  `bar_edge_width` 3, `diverging_cmap` 2, `legend_title_pt` 2.

Tokens with **no reader anywhere**: `regression_line_width` (scatter uses `line_width_pt`,
`scatter.py:40`; both apps still write it, `main.py:1204`, `streamlit_app.py:1058`) and
`panel_label_pt` (panels use `FigureLayout.label_size`, `panels/builder.py:201`).
`title_font_weight` is read by 6 renderers but is not in `STYLE_TOKEN_KEYS`, so a preset cannot
carry it (`presets.py:103-112`).

Tokens with a UI control: desktop exposes palette, font family, title/axis/tick/annotation/legend
pt, marker size, line width, spine width, grid, legend outside (`main.py:1064-1125`); Streamlit the
same minus font family (`streamlit_app.py:1046-1081`). The other ~20 tokens (edge widths, alphas,
tick geometry, spines, grid width/alpha, legend frame/ncol, text colour, weights, cmaps, explicit
`palette`) are preset-serializable and render correctly but are invisible in the controls; the
desktop restore path writes back only 8 numeric tokens + palette + font + 2 booleans
(`main.py:979-1002`), Streamlit 10 tokens + palette (`streamlit_app.py:907-916`).

Default-value drift: engine `title_font_pt` 13 / `annotation_pt` 9.5 vs UI defaults 14 / 10
(`engine.py:150-152`, `main.py:1075-1078`, `streamlit_app.py:881-882`).

## 6. Figure size, aspect, margins, colorbar, export

- Size is chosen by `layout.column_width` in {default, single, onehalf, double} ->
  130/110/140/180 mm (`engine.py:97`, `base.py:124-142`). `WIDTH_PRESETS_MM.get(width)` succeeds for
  every alias, so the profile's `single_column_width_mm`/`double_column_width_mm` are never used
  (`engine.py:195-198`). `layout.aspect` is honoured but has no UI control.
- `output.width_mm`/`height_mm` are written by both apps (`controller.py:335-341`,
  `streamlit_app.py:1248,1264`) and carried by presets, but only echoed into metadata
  (`base.py:651-652`); the desktop writes 110 mm even for `default`/`onehalf`. There is **no
  physical-width targeting** (e.g. 89 mm / 183 mm) in the render path.
- Margins/padding/rotation/scales: `apply_publication_layout` on `figure.axes[0]` of every plot
  (`registry.py:344-351`, `base.py:427-543`); 8 renderers also call it themselves.
- Legend: `layout.legend_location` (14 named positions) re-places the axes[0] legend for any plot
  that has one (`registry.py:353-381`); outside placement reserves fixed margins (`base.py:375-376`).
- Colorbar: `colorbar_location/pad/shrink/fraction` read by heatmap, hierarchical_clustering,
  confusion_matrix, enrichment; UI controls for location/pad/shrink only.
- Export: `formats` (svg/pdf/png/tiff/eps), `dpi`; vector text always editable
  (`registry.py:222`, `engine.py:252-254`). Neither single-figure UI has a formats control that
  feeds the spec.

## 7. Validation

- `validate_preset` (`presets.py:438-458`): format, integer version <= 1, mode, plot_type, block
  types. It does not validate token names or values.
- `preset_contains_data` (`:461-477`): key-name check (`input_table`, `source`, `rows`, ...), data
  extras inside options, and full-only blocks inside a style preset. Enforced only by `save_preset`
  (`:510-514`); `load_preset`/`apply_preset` do not run it. Free-text leakage (e.g. a column name
  typed into `title` of a full preset) is allowed by design.
- `coerce_to_preset` (`:480-503`) accepts raw PlotSpecs and `*.plot_spec.json` sidecars as full
  presets; legacy journal style names are mapped to `publication` (`engine.py:373-393`).
- `PresetStore.list` silently skips any file that fails validation (`:596-597`).

## 8. Save / load / store paths

`default_preset_dir()` (`presets.py:543-556`): `MAKE_MY_FIGURE_PRESETS` env override, else
`%APPDATA%\MakeMyFigure\presets`, `~/Library/Application Support/MakeMyFigure/presets`, or
`$XDG_DATA_HOME/make_my_figure/presets`. One flat directory shared by figure presets and layout
presets; `list/save/load/delete/import_file/export_file` (`:574-644`). There is no bundled,
read-only library location for shipped presets, no tags, versions or provenance beyond `created`.

## 9. UI flows

**Desktop** (`apps/desktop_app/main.py`): "Figure preset" group box (`:698-732`) and File menu
(`:1276-1285`). Apply = `load_preset` -> `_build_spec()` -> `apply_preset(columns=...)` ->
`_apply_spec_to_controls(result.spec, keep_plot_type=True)` -> `render_preview()` (`:762-794`).
Unresolved roles open a message box; skipped options are reported as a count. Save dialog offers
"Figure style only" / "Full figure configuration" (`:796-840`). Import accepts `.mmfpreset.json`,
`.plot_spec.json` and `.json`.

**Streamlit** (`apps/streamlit_app/streamlit_app.py`): sidebar expander "Figure preset"
(`:959-1024`). Apply stages widget-state keys via `_preset_to_session` (`:898-956`) and reruns;
values are written into `st.session_state` at the top of the next run (`:156-163`). Save is a form
whose request is fulfilled after the full spec is assembled (`:1276-1288`), with a download button.
Import is a file uploader saved straight into the store (`:1014-1021`). "Reset to Publication
defaults" restores `_STYLE_DEFAULTS` only (`:878-887`, `:1022-1024`), not per-plot `opt_*` keys.

**Preview before apply: none in either frontend as committed.** The only visual feedback is the
ordinary figure re-render after the preset has already been written into the controls. There is no
dry-run render, no side-by-side, no thumbnail, and no diff of what will change.
`reports/journal_presets/previews/` and `comparison_sheets/` exist but are empty and no generator
script references them.

Caveat: an **untracked, uncommitted** module `make_my_figure_core/preset_preview.py` (236 lines,
mtime 2026-09-16 10:19, i.e. it appeared while this audit was running and was not present in the
initial listing) defines `preview_pair` (current vs preset-applied render on the bundled synthetic
example table), `describe_changes` (`(block, key, old, new)` rows), `assert_style_safe` (protected
analysis/config/label keys must not change under a style preset) and `apply_with_guard`. Nothing in
`apps/` or `tests/` imports it, so it is work in progress rather than shipped capability.

## 10. `starter_journal_style_profiles.json` and the learned profiles

`style_profiles/starter_journal_style_profiles.json` holds three starter token sets
(`nature_like`, `science_like`, `cell_like`: 7 pt base/axis, 8 pt title, 0.75-0.8 pt lines,
0.5-0.6 pt spines, 89/183, 55/120 and 85/180 mm column widths, svg/pdf/png) with an explicit
"not official templates" notice. At runtime it is **dead**: `load_profile` first normalizes all
three names to `publication` (`engine.py:373-393`, `:414-416`), so `_parse_profile`
(`:293-304`) is never reached, and even when it was, it kept only palette/cmaps/column width and
clamped width to >= 100 mm (`:303`). `list_profiles` returns `["publication"]` plus any learned
profile whose name starts with `publication` and contains no journal word (`:396-409`), so the
Streamlit and desktop style selectors (`streamlit_app.py:636-639`, `controller.py:82`) show only
"Publication". The same applies to `style_profiles/learned/*_like_learned.json`: their
`panel_label`, `markers`, `bars`, `error_bars`, `export.dpi`, `layout.default_aspect` and
`plot_type_defaults` blocks are not consumed by `_parse_learned` (`engine.py:340-360`).

## 11. Tests

`tests/test_figure_presets.py` (33 tests: scope tables, no-data guarantees per plot type,
apply/remap semantics, files, store, layout presets), `tests/test_figure_preset_palette_transfer.py`
(palette order + marker/line/tick round trip), `tests/test_figure_preset_qc.py` (per-plot QC
harness from `scripts/build_figure_preset_qc.py`; changes 6 style tokens, 4 layout keys and dpi),
`tests/test_figure_preset_ui_wiring.py` (13 source-level guards), `tests/test_streamlit_presets.py`
(4 AppTest flows). No test covers preview, physical width, or the orphan tokens.

## 12. Gaps that matter for a journal-style preset library

1. **No preview-before-apply** in either frontend as committed (section 9); the empty
   `reports/journal_presets/previews` folder and the untracked `preset_preview.py` show this is in
   progress, but neither frontend calls it and no test covers it.
2. **No physical width/height targeting.** Size is a 4-way alias table with non-journal widths
   (110 mm "single"); `output.width_mm` is metadata only; profile column widths are unreachable
   (`engine.py:97`, `:195-198`, `base.py:651-652`). A preset cannot say "89 mm wide, 7 pt type".
3. **Journal-named profiles are aliased away.** `starter_journal_style_profiles.json` and the
   learned profiles are unreachable and unlisted; `journal_style` in a preset is always
   `publication` after coercion. A journal library has to be expressed entirely through the
   `style`/`layout`/`options` blocks of presets.
4. **Orphan or non-serializable tokens**: `regression_line_width` and `panel_label_pt` render
   nothing; `title_font_weight` renders but cannot be saved; `y_label_rotation` as a layout key is
   a no-op.
5. **Renderer coverage is uneven**: `marker_size` reaches 18 renderers, `errorbar_*` 4,
   `bar_edge_width` 3, `legend_*` only the 17 renderers that call `place_legend`; forest hard-codes
   capsize/marker (`forest.py:52-55`), volcano hard-codes threshold guide lines (`volcano.py:193-195`),
   box/violin hard-codes the median colour (`box_violin.py:60`). `capabilities.py` warns but is not
   used to filter what a preset applies.
6. **Style-scoped options that change meaning**: `error` (sem/sd/ci95), histogram `normalize` and
   `log_y`, KM `y_scale`, and layout `x_scale`/`y_scale` all travel in style presets.
7. **Hidden tokens**: ~20 tokens (tick geometry, spines, grid width/alpha, marker edge/alpha, legend
   frame/ncol, text colour, weights, cmaps, explicit `palette`) have no control and are not written
   back into the UI after apply, so a journal preset that sets them works but is not inspectable.
8. **Library plumbing**: one flat user directory, no bundled read-only preset set, no tags/versions,
   no `universal` save action in the UI, description field unused, validation does not check token
   names or value ranges, and `preset_contains_data` runs only on save.
9. **No preset JSON Schema** under `schemas/`; the format is defined only in code.
10. **Default drift** between engine and UI (`title_font_pt` 13 vs 14, `annotation_pt` 9.5 vs 10)
    means "Reset to Publication defaults" and an untouched PlotSpec render differently.
