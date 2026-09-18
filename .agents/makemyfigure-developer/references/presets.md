# Figure Presets and Layout Presets

Written 2026-09-17 against `main` (bb45c12). Presets shipped in v1.1.0
(`CHANGELOG.md`, "Figure presets for every plot type"). Everything below is on
main unless marked otherwise.

## 1. Where the code lives

| Path | Role |
|---|---|
| `make_my_figure_core/presets.py` | The whole preset core: scope tables, `extract_preset`, `apply_preset`, validation, files, `PresetStore`, layout presets |
| `make_my_figure_core/ui_hints.py` | `Option.scope` (`"style"` or `"config"`), `column_fields(plot_type)`, `options(plot_type)`, `PCA_METADATA_FIELDS`; the registry presets classify against |
| `scripts/build_figure_preset_qc.py` | Per-plot preset QC harness (`check_plot`) and the committed matrix `reports/figure_preset_qc/all_plot_preset_matrix.csv` + README |
| `tests/test_figure_preset_qc.py` | Runs `check_plot` for every `available_plot_types()` entry and checks the committed CSV matches the registry |
| `tests/test_figure_presets.py` | Unit tests for scope rules, extraction, application, store, layout presets |
| `tests/test_figure_preset_ui_wiring.py`, `tests/test_streamlit_presets.py`, `tests/test_figure_preset_palette_transfer.py` | Frontend wiring, Streamlit session round-trip, palette-order transfer |
| `apps/desktop_app/main.py` (`action_apply_preset`, `_collect_style_overrides`, preset panel around line 660) | Desktop UI |
| `apps/desktop_app/stats_panel.py::FigureBuilderDialog` | Figure Builder, uses `LayoutPresetStore` |
| `apps/streamlit_app/streamlit_app.py` (`_presets.*` calls around lines 829-943 and 1206) | Streamlit UI |
| `docs/manuals/User_Manual/parts/04_publication_colour_annotations_presets_plotspec_builder.md` | User manual section |

There is no `schemas/*preset*.json`: the only JSON schema on main is
`schemas/plot_spec.schema.json`. Preset validation is procedural
(`validate_preset`, `validate_layout_preset`).

## 2. Why presets exist and what they separate

A PlotSpec binds one figure to one table (`input_table`, column roles,
thresholds). A Figure Preset is the part worth carrying to other data. Because
the PlotSpec mixes scopes inside `mapping`, `layout` and `statistics`,
`presets.py` classifies every key by scope using the registry rather than a
hand-written per-plot list:

- column roles: `ui_hints.column_fields(plot_type)` (+ `value_columns`, + PCA
  metadata fields) -> `role_keys`;
- plot options: `ui_hints.Option.scope` declared on each option ->
  `option_scopes`; `tests/test_figure_presets.py::test_every_option_declares_a_valid_scope`
  and the threshold/visual parametrised tests police the declarations;
- shared blocks split on fixed sets in presets.py: `LAYOUT_STYLE_KEYS`
  (geometry, legend/colorbar placement, `column_width`, `aspect`, margins,
  `auto_fix_layout`) vs `LAYOUT_CONFIG_KEYS` (`title`, `x_label`, `y_label`);
  `OUTPUT_KEYS` (all style); `STATS_DISPLAY_KEYS = ("annotation",)` is style,
  the rest of `statistics` is analysis; `STATS_NEVER_KEYS` drops `source` and
  `_annotation_info`;
- `MAPPING_DATA_KEYS` (`selected_points`, `selected_labels`, `label_offsets`,
  `point_offsets`, `sets`) are data-bound and never enter a preset;
  `MAPPING_STYLE_EXTRA_KEYS` are colorbar geometry keys treated as style;
- `STYLE_TOKEN_KEYS` is the allow-list for `spec["style"]`; unknown keys are
  dropped with a note in `preset["notes"]`.

`split_mapping(plot_type, mapping) -> MappingSplit(roles, style_options,
config_options, data_extras, unknown)`. Unregistered mapping keys are treated as
config (they might depend on the data).

## 3. Two modes

- `style`: journal_style, style tokens, layout geometry, visual options, output
  defaults, statistics display block. No table name, columns, thresholds, axis
  labels, limits, or annotations. Applies across plot types (universal parts).
- `full`: everything in style plus `mapping_roles`, `config_options` (incl.
  unknown keys), `labels` (title/x_label/y_label), `statistics` (analysis, only
  when `enabled`), `annotations`. Refused for a different plot type.

Neither mode ever contains row values, `input_table`, or worksheet provenance;
`preset_contains_data` is the guard and `save_preset` refuses on a hit.

## 4. File format

`PRESET_FORMAT = "make_my_figure.figure_preset"`, `PRESET_FORMAT_VERSION = 1`,
`PRESET_EXTENSION = ".mmfpreset.json"`. Top-level keys written by
`extract_preset`: `format`, `format_version`, `name`, `description`, `mode`,
`plot_type`, `journal_style`, `created` (UTC ISO), `app_version`, `style`,
`layout`, `options`, `output`, `statistics_display`, optional `notes`; full mode
adds `mapping_roles`, `config_options`, `labels`, `statistics`, `annotations`.
`universal_preset_from` produces a style preset with `options` emptied and
`universal: true`, listed for every plot type by the store.

Layout presets: `LAYOUT_PRESET_FORMAT = "make_my_figure.figure_layout_preset"`,
extension `.mmflayout.json`, keys `layout` (a `panels.models.FigureLayout`
dict), `panel_sizes` (positional width/height in inches), `n_panels`; must not
carry `panels`, `figure`, `plot_spec`, `table`.

## 5. APIs

- `extract_preset(spec, *, mode="style", name="", description="") -> dict`
- `apply_preset(preset, spec, *, columns=None, aux_columns=None, strict_plot_type=False) -> PresetApplyResult`
  with `.spec` (new dict; input untouched), `.applied`, `.skipped`,
  `.unresolved_roles`, `.warnings`, `.needs_remapping`. Roles are applied only
  when the new table has the column; nothing is ever substituted. Statistics
  column keys (`group_column`, `subgroup_column`, `subject_column`) are checked
  the same way and set to `None` when missing. Style presets for another plot
  type apply universal parts and list dropped options in `.skipped`.
- `validate_preset`, `preset_contains_data`, `coerce_to_preset` (accepts a
  preset, a raw PlotSpec, or an exported `*.plot_spec.json` sidecar; legacy
  journal style names are normalised), `save_preset`, `load_preset`,
  `load_preset_bytes`, `preset_to_json`, `safe_filename`.
- `PresetStore(directory=None)`: `list(plot_type=None, include_universal=True)`,
  `save(preset, overwrite=True)`, `load(path_or_name)`, `delete`,
  `import_file`, `export_file`. Directory from `default_preset_dir()`
  (`MAKE_MY_FIGURE_PRESETS` env override; else APPDATA / Library/Application
  Support / XDG data dir). Foreign JSON in the folder is ignored.
- Layout: `extract_layout_preset(mpf)`, `apply_layout_preset(preset, mpf)` (in
  place, re-runs `mpf.autolabel()`, warns on panel-count mismatch),
  `validate_layout_preset`, `save_layout_preset`, `load_layout_preset` (also
  accepts an exported FigureSpec and keeps only its geometry), `LayoutPresetStore`.

Round trip: `save_preset` -> `load_preset` is byte-exact JSON
(`test_save_load_roundtrip_is_exact`); the QC harness also re-extracts a style
preset from the applied spec and requires equality modulo `created`, `notes`,
`description`.

## 6. What a preset may and may not change

May (style mode): every `STYLE_TOKEN_KEYS` entry, `journal_style`, layout
geometry, `output` (formats, width_mm, height_mm, dpi), style-scoped plot
options, and `statistics.annotation` (how results are drawn).

May not (any mode): the table, worksheet provenance, row values, click-to-label
picks and offsets, UpSet `sets`.

Only in full mode, same plot type: column roles, thresholds and other
config-scoped options, axis labels, the statistics test/mode/correction/alpha,
manual annotations (restored at saved positions with a warning).

Rule of thumb when adding an option: if changing it could change what the data
says (cutoffs, bin widths, normalisation, top-N), declare `scope="config"`;
if it only changes how the same numbers look, `scope="style"`.
`tests/test_figure_presets.py::test_thresholds_and_data_dependent_options_are_config_scoped`
pins known examples.

## 7. How the apps expose presets

- Desktop (`apps/desktop_app/main.py`): a Figure preset panel with Apply, Save
  preset... (dialog offers style/full radio), Import, Export, Delete, Reset;
  `action_apply_preset` calls `load_preset` then `apply_preset(preset, base,
  columns=...)` and reports `unresolved_roles` instead of guessing. Figure
  Builder (`stats_panel.FigureBuilderDialog`) has layout preset actions via
  `LayoutPresetStore`. `tests/test_figure_preset_ui_wiring.py` asserts every
  action exists and that no frontend reimplements extraction.
- Streamlit (`apps/streamlit_app/streamlit_app.py`): expander listing
  `PresetStore().list(plot_type)`, Apply (`_preset_to_session` writes widget
  keys after `apply_preset` on a skeleton spec), Export (download of
  `preset_to_json`), Import (`load_preset_bytes` then `store.save`), Save after
  render (`extract_preset` with the chosen mode). Controls are keyed so a preset
  can set them (`test_streamlit_controls_are_keyed_so_a_preset_can_set_them`).
- Both frontends build `spec["style"]` from their own controls and write it
  before render; presets set those controls, they do not bypass them.

## 8. The per-plot preset QC every plot type must pass

`scripts/build_figure_preset_qc.py::check_plot(plot_type)`:

1. `examples.load_example(plot_type)` and render with defaults.
2. Change >= 3 settings: `STYLE_CHANGES` (title/axis/annotation pt, line width,
   marker size, legend pt), `palette_name="high_contrast"` when
   `supports_palette`, `LAYOUT_CHANGES` (45 deg ticks, margin_left,
   `column_width="double"`, `legend_location="outside right"`), `dpi=450`, the
   first style-scoped option and the first colour-ish choice option.
3. Save a style preset and a full preset; load both back (must equal).
4. Build a fresh spec on a different dataset (`data.sample_path` mock when its
   columns cover the example, else a perturbed copy).
5. Apply both presets, render.
6. Verify: typography (including the drawn title font size), layout + dpi and
   that the new figure's own title survived a style preset, legend (N/A with
   reason when `supports_legend` is False), annotation_pt, colour (N/A when
   nothing applies), plot-specific option (N/A when all options are config),
   `new_data_safe` (no leaks, no original column names or string values, new
   `input_table` everywhere), full-config round trip (roles, config options,
   labels, no unresolved roles), style re-extraction equality, PNG/PDF/SVG
   export, PlotSpec JSON round trip re-renders to the same record.

`python scripts/build_figure_preset_qc.py` writes
`reports/figure_preset_qc/all_plot_preset_matrix.csv` and `README.md` (exit 1
on any FAIL). `tests/test_figure_preset_qc.py::test_plot_type_passes_preset_qc`
is parametrised over the live registry and `test_matrix_covers_the_live_registry_with_the_required_columns`
fails if the committed CSV does not list exactly the registered plot types, so
adding a renderer requires regenerating and committing the CSV. Checks that can
never be N/A: preset_save, preset_load, style_roundtrip, full_config_roundtrip,
typography_roundtrip, layout_roundtrip, annotation_roundtrip, new_data_safe,
png/pdf/svg_export.

Prerequisites for a new plot type to pass: a bundled example in the examples
manifest, `ui_hints.COLUMN_FIELDS` and `OPTIONS` with scopes, a drawn title that
takes `title_font_pt`, a legend only if `supports_legend` says so, and colours
that come from the palette (or a style-scoped colour option).

## 9. Not on main: evidence-derived journal presets

Branch `feature/evidence-derived-journal-presets` (worktree
`../make_my_plot_journal_presets`, HEAD 9ea5ee5) adds experimental
evidence-derived publication presets (`single_89mm_N.mmfpreset.json`,
`layout_full_183mm_N.mmflayout.json` and similar), a preview-before-apply
flow, group-comparison renderer options and tests such as
`tests/test_experimental_presets.py`, `tests/test_preset_preview_and_layout_qc.py`,
`tests/test_preset_scientific_identity.py`. Its own commit message marks it
"not for release". None of it exists on main; do not reference those files or
behaviours when working here.

## Verify this is still current

```bash
cd "<repo>" && grep -n "^PRESET_\|^LAYOUT_PRESET_\|^STYLE_TOKEN_KEYS\|^LAYOUT_STYLE_KEYS\|^MAPPING_DATA_KEYS\|^def \|^class " make_my_figure_core/presets.py
MPLBACKEND=Agg python -m pytest tests/test_figure_preset_qc.py -q -x   # every registered plot type must PASS
head -3 reports/figure_preset_qc/all_plot_preset_matrix.csv && python -c "from make_my_figure_core.plots.registry import available_plot_types as a; print(len(a()))"
git log --oneline main..feature/evidence-derived-journal-presets | head -3   # confirms the journal-preset work is still off main
```
