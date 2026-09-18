# PlotSpec, StatsSpec, matrix-workflow specs and FigureSpec

Documented from `main` as of 2026-09-17 (checkout: branch `feature/makemyfigure-developer-agent`,
forked from `main` at bb45c12). Every path below is relative to the repo root.

## 1. Where the PlotSpec machinery lives

| Concern | Location |
|---|---|
| JSON Schema (the only schema file for PlotSpec) | `schemas/plot_spec.schema.json` (repo root, bundled via `make_my_figure_core/resources.py::resource_path("schemas", ...)`) |
| Loading + validating | `make_my_figure_core/spec/validate.py` — `load_schema`, `validate_plot_spec`, `SpecValidationError`, `default_output_block` |
| Public re-exports | `make_my_figure_core/spec/__init__.py` |
| Building a spec with defaults | `make_my_figure_core/plots/registry.py::make_spec` |
| Rendering + sidecars | `make_my_figure_core/plots/registry.py` — `render`, `render_to_files`, `write_sidecar`, `write_stats_sidecar`, `export_bundle_bytes`, `figure_to_bytes` |
| StatsSpec (the `statistics` block) | `make_my_figure_core/statistics/schemas.py` |
| Manual annotation layer (`annotations` block) | `make_my_figure_core/annotations.py` — `Annotation`, `parse_annotations`, `apply_annotations` |
| Scope classification (analytical vs presentation) | `make_my_figure_core/presets.py` + `make_my_figure_core/ui_hints.py` |
| Matrix-workflow specs | `make_my_figure_core/matrix_workflow/{matrix_spec,metadata_spec,preprocessing_spec,differential_summary}.py`, `make_my_figure_core/plots/handoff.py` |
| FigureSpec (multi-panel) | `make_my_figure_core/panels/models.py`, `make_my_figure_core/panels/builder.py::multipanel_sidecar` (see `figure-builder.md`) |

There is **no** `make_my_figure_core/spec/schemas/` directory. `spec/` holds only `__init__.py`
and `validate.py`; the schema is the root-level `schemas/plot_spec.schema.json`.

## 2. The blocks of a PlotSpec

The schema (`schemas/plot_spec.schema.json`) requires five keys and declares a handful of
optional ones. It is deliberately permissive: the root object has no `additionalProperties: false`,
`plot_type` is a bare `string` (not an enum), `mapping` values may be string/number/bool/null/array,
and the only enum is `output.formats` (`svg`, `pdf`, `png`, `tiff`, `eps`).

| Block | Required | Declared in schema | Who consumes it |
|---|---|---|---|
| `plot_type` | yes | string | `registry.render` dispatches on it via `_RENDERERS` |
| `input_table` | yes | string | a label only; the DataFrame is passed separately. `DesktopController.load_plotspec` uses its basename to find the data file next to the JSON |
| `mapping` | yes | object | column roles **and** per-plot options live here together (see section 6). Renderers read it with `plots/base.py::get_mapping` |
| `journal_style` | yes | string | resolved with `styles/engine.py::load_profile`; legacy journal names are migrated by `is_legacy_style_name`/`normalize_style_name` inside `render` |
| `output` | yes | object (`formats`, `width_mm`, `height_mm`, `dpi`) | `render_to_files` reads `formats` and `dpi`; `default_output_block` supplies defaults |
| `layout` | no | free object | the shared PublicationLayoutSpec: `plots/base.py::apply_publication_layout` (tick rotation/pad, label pads, margins, x/y scale), `figure_size` (`column_width`, `aspect`), `resolve_legend_location` (`legend_location`), `layout_qc.auto_fix_layout` (`auto_fix_layout`), plus `title`/`x_label`/`y_label` read by each renderer |
| `style` | no | **not declared** in the schema | `StyleProfile.with_overrides(spec.get("style"))` in `render`; keys are StyleProfile fields (see `STYLE_TOKEN_KEYS` in `presets.py`). `styles/capabilities.py::warn_ignored_style_controls` reports keys a plot type cannot honour |
| `statistics` | no | free object | the StatsSpec; normalised by `statistics/schemas.py::normalize_stats_spec`, executed by `plots/stats_integration.py::run_and_annotate` |
| `annotations` | no | array | universal manual annotation layer (`AnnotationSpec` dicts), applied to `figure.axes[0]` by `render` after the renderer returns |
| `column_annotations` | no | array | heatmap column annotation strips (`plots/heatmap.py`); also produced by `matrix_workflow/plot_builder.py` and `grouping.py` |
| `source` | no | object with `source_workbook_name`, `source_workbook_hash`, `source_sheet_name`, `source_sheet_index`, `source_sheet_type`, `source_header_row` | worksheet provenance; `make_spec(source=...)` also mirrors it into `statistics.source`; the matrix workflow adds more keys (section 7) |

`make_spec(plot_type, input_table, journal_style, *, mapping, layout, statistics, output, source)`
fills `mapping` from `registry.default_mapping` and `output` from `default_output_block()`
(svg/png/pdf, 89 x 70 mm, 300 dpi) when they are omitted.

## 3. Versioning

There is no `spec_version` field on a PlotSpec and no migration framework for the spec body.
What exists:

* `make_my_figure_core/version.py::__version__` is the single application version; it is recorded
  in `MatrixSpec.app_version` and `PreprocessingSpec.app_version` (not in a PlotSpec).
* Style-name migration: `render` rewrites removed journal profiles to `publication` before
  validation and appends a notice to `result.warnings` and `metadata["style_migration"]`.
  `DesktopController.load_plotspec` and the Streamlit "Open PlotSpec" path call
  `normalize_style_name` too. Tests: `tests/test_style_migration.py`, `tests/test_learned_styles.py`.
* StatsSpec back-compat: `normalize_stats_spec` mirrors the legacy `annotation.mode` into
  `annotation.content` and preserves unknown keys.
* Figure presets and layout presets carry their own `PRESET_FORMAT_VERSION` /
  `LAYOUT_PRESET_FORMAT_VERSION` (both 1) in `presets.py`; a newer version is refused
  (`tests/test_figure_presets.py::test_wrong_format_and_newer_version_are_refused`).
* The matrix-workflow dataclasses use `from_dict` that ignores unknown keys, so older/newer
  JSON loads (`tests/test_workbook_provenance.py::test_legacy_matrix_spec_without_source_fields_loads`).

## 4. Validation

`validate_plot_spec(spec, *, known_plot_types=None, known_styles=None, schema_path=None)`
runs `jsonschema.Draft202012Validator(schema).iter_errors`, collects `"<path>: <message>"`
strings, then layers two app-level checks: `plot_type in known_plot_types` and
`journal_style in known_styles`. All messages are raised together in
`SpecValidationError(errors: List[str])`. `render` calls it with
`known_plot_types=available_plot_types()` and `known_styles=list_profiles()` unless
`validate=False`. Because the schema has no plot-type enum, **registry membership is the
only thing that makes a `plot_type` valid**. Tests: `tests/test_validate.py`
(`test_unknown_plot_type_reported`, `test_bad_output_format_rejected`, ...).

Renderer-level validation is the renderer's job: `plots/base.py::require_columns`,
`get_mapping(required=True)`, `coerce_numeric` raise `RenderError` with the available columns
listed.

## 5. Render result, sidecars and open/save paths

`render(spec, df, *, style=None, validate=True, aux=None) -> RenderResult` where
`RenderResult(figure, metadata, warnings, stats_report)` (`plots/base.py`). After the renderer
returns, `render` applies the layout block, legend relocation, stamps `metadata["spec"]`, applies
manual annotations, and adds `metadata["publication_check"]` and `metadata["layout_qc"]`.
`aux` is only forwarded to renderers whose signature declares an `aux` parameter.

Files written on export (all in `plots/registry.py`):

| File | Writer | Payload |
|---|---|---|
| `<base>.svg/.png/.pdf/.tiff/.eps` | `export_figure` | `bbox_inches="tight"`, `_bbox_extra_artists`, `_VECTOR_TEXT_RC` (editable text) |
| `<base>.plot_spec.json` | `write_sidecar` | `{"plot_spec": spec, "render_metadata": metadata minus "spec"}` |
| `<base>.stats_spec.json` | `write_stats_sidecar` (only when `result.stats_report` is not None) | `statistics/schemas.py::stats_sidecar_payload` = normalised StatsSpec + results + method paragraph + software versions |
| `<base>.figure_spec.json` | `panels/builder.py::multipanel_sidecar` | composite figure (section 8) |
| ZIP in memory | `export_bundle_bytes` | figure files + both sidecars |

`render_to_files` chains render, export and both sidecars and returns
`{"files", "sidecar", "stats_sidecar", "metadata", "warnings"}`.

Frontend paths:

* Desktop: `apps/desktop_app/controller.py::DesktopController.export_files` (figure files +
  `write_sidecar`; it does **not** call `write_stats_sidecar`), `export_bundle`, and
  `load_plotspec(path) -> (spec, data_path_or_None)` which requires a top-level `plot_type`
  (i.e. a raw spec, not the `{"plot_spec": ...}` sidecar wrapper) and resolves the data by
  `input_table` basename or the sole data file in the directory. Menu actions:
  `apps/desktop_app/main.py::action_open_plotspec`, the "Save PlotSpec" dialog writes
  `self._current_spec` verbatim. The preset loader (`presets.py::coerce_to_preset`) *does* accept
  a sidecar wrapper.
* Streamlit: `apps/streamlit_app/streamlit_app.py` "Open PlotSpec" data-source mode (same
  `plot_type` check + `normalize_style_name`), and the Export section builds the sidecar dict
  inline and offers `<base>.plot_spec.json` / `<base>.stats_spec.json` downloads.

## 6. Analytical vs presentation: what a style preset must never touch

The PlotSpec does not separate analysis from appearance structurally, so `presets.py`
classifies every key by scope using the registry, not hand lists:

* **Column roles** come from `ui_hints.column_fields(plot_type)` (`COLUMN_FIELDS` dict).
  `MULTI_COLUMN_FIELDS` (`value_columns`, `survival_columns`) take lists.
* **Per-plot options** come from `ui_hints.options(plot_type)` (`OPTIONS` dict of
  `ui_hints.Option`). Each `Option` declares `scope="style"` or `scope="config"`; the default
  is `"config"`, so a new threshold cannot leak into a style preset by omission.
  `tests/test_figure_presets.py::test_thresholds_and_data_dependent_options_are_config_scoped`
  and `test_visual_options_are_style_scoped` pin representative keys.
* **Mapping keys that are neither** (click-to-label picks, UpSet `sets`) are in
  `MAPPING_DATA_KEYS`; colorbar geometry keys in `MAPPING_STYLE_EXTRA_KEYS`.
* **layout**: `LAYOUT_STYLE_KEYS` (geometry, rotation, pads, margins, legend/colorbar location,
  `auto_fix_layout`) are presentation; `LAYOUT_CONFIG_KEYS` (`title`, `x_label`, `y_label`) are
  data-bound text. Axis limits are config.
* **output**: all of `OUTPUT_KEYS` are presentation (export defaults).
* **statistics**: only `STATS_DISPLAY_KEYS = ("annotation",)` is presentation; the test,
  comparison mode, correction, alpha, column names, reference group are analytical.
  `STATS_NEVER_KEYS` (`source`, `_annotation_info`) never travel.
* **style**: only `STYLE_TOKEN_KEYS` (StyleProfile field names) are accepted; others are dropped
  with a note.
* **Never in any preset**: `input_table`, `source`, `annotations` in style mode (they are full-mode
  configuration), and row-level data.

Rule for the agent: a style preset (and any style-only code path) may change `style`,
`LAYOUT_STYLE_KEYS`, `output`, `statistics.annotation`, and `scope="style"` options. It must
never alter column roles, `scope="config"` options (thresholds, bin widths, clustering method,
axis limits), the statistics test configuration, `input_table`, `source`, or `annotations`.
`tests/test_figure_presets.py::test_style_preset_has_no_data_for_every_plot_type` is
parametrised over `available_plot_types()`, so a new plot type is checked automatically.
See `presets.md` for the preset file formats.

## 7. StatsSpec and matrix-workflow specs

**StatsSpec** (`statistics/schemas.py`): `default_stats_spec()` lists every key (`enabled`,
`test`, `comparison_mode`, `correction`, `alpha`, `alternative`, `posthoc*`, the `*_column`
roles, `reference_group`, `selected_pairs`, `annotate`, `annotation`). `VALID_TESTS`,
`VALID_MODES`, `VALID_ANNOTATION_MODES`, `ANNOTATION_CONTENTS` are the enums;
`validate_stats_spec` returns problems as strings. Renderers call
`plots/stats_integration.py::run_and_annotate(spec, df, style, plot_type, ax=..., positions=...,
tops=..., mode=...)` which returns the `StatsReport` placed on `RenderResult.stats_report`.
See `statistics.md`.

**Matrix workflow** (`make_my_figure_core/matrix_workflow/`, re-exported from its `__init__.py`):

| Dataclass | Module | Serialisation | Notes |
|---|---|---|---|
| `MatrixSpec` | `matrix_spec.py` | `to_dict` (asdict) / `from_dict` (ignores unknown keys) | roles over a feature matrix: `feature_id_column`, `value_columns`, `annotation_columns`, `value_type` in `VALUE_TYPES`, missing/duplicate policies, worksheet provenance, `confirmed_by_user`, `app_version`. `suggest_matrix_spec`, `looks_log_scale` |
| `SampleMetadataSpec` | `metadata_spec.py` | same | `sample_to_group`, group/batch/paired/covariate columns; helpers `groups()`, `default_group_pair()`, `metadata_frame()` |
| `PreprocessingStep`, `PreprocessingSpec` | `preprocessing_spec.py` | same, steps nested | ordered chain with `method_name`, `parameters`, `qc_before/after`, `method_sentence()` for methods text |
| `DifferentialSummary` | `differential_summary.py` | not JSON (holds a DataFrame) | `test_name`, `correction_method`, `groups`, provenance ids `source_matrix_id`, `preprocessing_spec_id`; built by `feature_differential_summary` |
| `PlotEditorHandoff` | `plots/handoff.py` | in-memory | carries `plot_type`, `data`, `mappings`, `aux`, `spec_extra`, `provenance` into the normal plot editor. `build_matrix_provenance` produces the PlotSpec `source` block with `source_workflow="matrix"`, `source_matrix_id`, `source_matrix`, optional `source_metadata`, and the worksheet keys |

Round-trip tests: `tests/test_matrix_workflow_core.py::test_matrix_spec_json_round_trip`,
`::test_metadata_spec_json_round_trip`, `tests/test_workbook_provenance.py::test_matrix_spec_round_trips_worksheet_provenance`,
`tests/test_matrix_handoff.py` (validates handoff specs against `available_plot_types()`).

## 8. FigureSpec (multi-panel)

`panels/models.py::MultiPanelFigure.to_dict()` = `{"name", "panels": [Panel.to_dict()...],
"layout": FigureLayout.to_dict(), "legend_text"}`. Each panel record carries `panel_kind`
(`make_my_figure_panel` | `external_figure_panel`), the full `plot_spec`, `stats_spec`
(falls back to `plot_spec["statistics"]`), provenance (`source_name/workbook/sheet`, derived
from `plot_spec["source"]` when blank), `width_in`/`height_in`, the imported-image record
(`image_path` basename only, `image_meta`, fit/crop/rotate/flip flags) and per-panel
`annotations`. `panels/builder.py::multipanel_sidecar` writes
`<base>.figure_spec.json` = `{"figure": ..., "draft_legend": ..., "disclaimer": ...}`.
Reload: `panel_from_dict(d, assets_dir)` and `FigureLayout.from_dict`. Tables are **not**
stored in a FigureSpec (that is what the Figure Package adds on the v1.1.1 branch; see
`figure-package.md`). Details in `figure-builder.md`.

## 9. How round trip is tested today

* `tests/test_reproducibility_export_qc.py::test_plotspec_roundtrip_reproduces_key_metadata`
  (parametrised over a `REPRESENTATIVE` list): `render_to_files` -> reload
  `sidecar["plot_spec"]` -> `render` again -> compare `plot_type`, `data_columns_used` and numeric
  fingerprints (`n_up`, `n_down`, `n_ns`, `n_clusters`, `matrix_shape`) in metadata; also checks
  SVG contains `<text`. Companion tests: `test_volcano_annotation_settings_roundtrip`,
  `test_manual_annotationspec_roundtrip`.
* `tests/test_examples.py::test_plotspec_validates` / `test_example_renders` /
  `test_example_exports_all_formats` over every manifest entry.
* Per-feature: `tests/test_network_spec_consistency.py::test_plotspec_round_trip_preserves_edge_color_mapping`,
  `tests/test_duplicate_labels.py::test_plotspec_roundtrip_preserves_policy`,
  `tests/test_layout_and_annotations.py::test_layout_spec_round_trips`,
  `tests/test_pick_identify.py::test_click_to_label_roundtrip_*`,
  `tests/test_survival_input_forms.py::test_precomputed_spec_round_trips_through_the_sidecar`,
  `tests/test_v05_features.py::test_annotation_roundtrip`.
* Presets: `tests/test_figure_presets.py::test_a_raw_plotspec_loads_as_a_full_preset`,
  `::test_an_exported_sidecar_loads_as_a_preset`, `::test_save_load_roundtrip_is_exact`.
* FigureSpec: `tests/test_multipanel.py::test_sidecar_has_panel_specs`,
  `tests/test_imported_panels.py::test_figurespec_roundtrip_restores_imported_panel`,
  `tests/test_workbook_provenance.py::test_panel_records_and_round_trips_worksheet`.

The round trip is metadata/structure based; no test compares exported bytes.

## 10. Making a NEW plot type PlotSpec-complete

The schema needs **no edit** (no plot-type enum). Everything is registry-driven; missing any
of these fails an existing test.

1. `make_my_figure_core/plots/<name>.py`: `PLOT_TYPE = "<name>"` and
   `render(spec, df, style) -> RenderResult` (add `aux=None` only if it needs auxiliary tables).
   Read roles/options with `get_mapping`, validate with `require_columns`, build metadata with
   `base_metadata(spec, style, df, used_columns=[...])`, call `run_and_annotate` if statistics
   apply, never mutate `df`. See `renderer-contract.md`.
2. `make_my_figure_core/plots/registry.py`: import the module; add entries to `_RENDERERS`,
   `_DEFAULT_MAPPINGS` (must name the example dataset's columns) and `_DISPLAY_NAMES`.
3. `make_my_figure_core/ui_hints.py`: `COLUMN_FIELDS[<name>]` (roles; list-valued roles go in
   `MULTI_COLUMN_FIELDS`) and `OPTIONS[<name>]` with an explicit `scope` on every visual option.
   Preset tests over `available_plot_types()` will otherwise treat every option as analytical.
4. `make_my_figure_core/styles/capabilities.py`: add a `PlotStyleCapabilities` entry if the
   default flags are wrong (e.g. no legend, continuous colormap, node/edge colours); otherwise
   `_DEFAULT` applies. `tests/test_style_capabilities_audit.py` scans every registered type.
5. `scripts/generate_example_data.py`: add a builder + `Example(...)` entry and regenerate
   `examples/` and `examples/example_data_manifest.json` (`tests/test_examples.py::test_every_supported_plot_type_has_example`,
   and every per-type loop in `tests/test_publication_style.py`, `tests/test_desktop_controller.py`,
   `tests/test_layout_qc.py`, `tests/test_learned_styles.py`, `tests/test_app_smoke.py` loads
   the example). The manifest entry's `plotspec` file is validated by `test_plotspec_validates`.
6. Count tripwires: `tests/test_renderers_m2.py` and
   `tests/test_desktop_controller.py::test_catalog` assert the exact number of registered
   types; bump both.
7. Optional but expected: `make_my_figure_core/recommendations/plot_recommender.py` (so the
   recommender can propose it), `docs/PLOT_TYPE_REQUIREMENTS.md`, README plot list, CHANGELOG.
8. Round trip: add the type to `REPRESENTATIVE` in `tests/test_reproducibility_export_qc.py`
   if it produces numeric fingerprints, and make sure any renderer-specific metadata you want
   reproduced is deterministic.

## Verify this is still current

```bash
# schema still has no plot_type enum and spec/ still has only validate.py
python - <<'EOF'
import json; s=json.load(open("schemas/plot_spec.schema.json")); print(s["properties"]["plot_type"], s["required"])
EOF
ls make_my_figure_core/spec/
# sidecar writers and the scope tables
grep -n "def write_sidecar\|def write_stats_sidecar\|def render_to_files\|def make_spec" make_my_figure_core/plots/registry.py
grep -n "LAYOUT_STYLE_KEYS\|STATS_DISPLAY_KEYS\|STYLE_TOKEN_KEYS\|OPTION_SCOPES" make_my_figure_core/presets.py make_my_figure_core/ui_hints.py
# round-trip tests still exist
grep -rn "def test.*round.*trip\|def test_plotspec_roundtrip" tests | wc -l
```
