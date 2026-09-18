# Data loading, column roles and examples (main, documented 2026-09-17)

## Role naming conventions in the registry (read before choosing roles for a new plot)

- Grouped comparisons (bar, grouped bar, box/violin, dot/strip, beeswarm, raincloud): `x` = categorical
  grouping column, `y` = numeric value, optional `hue`/`group`/`color` = second factor.
- Distribution plots over one numeric variable (histogram, ridge/density): `x` = the NUMERIC value,
  `group` = categorical series; wide input uses `value_columns` (a multi-column role).
- Paired / longitudinal designs (paired slopegraph, spider, swimmer): `subject`, `condition` or
  `time`, `value`, optional `group`.
- Two numeric axes (scatter, volcano, MA, embedding): `x`, `y` (or `p` for significance), optional
  `color`, `label`, `size`.
- Matrix inputs: `row_id` plus `value_columns`; aux tables (PCA metadata) via `aux`.
Choose the convention of the family the new plot belongs to; `find_related_renderers.py --roles`
scores by these names, and `statistics/runner.resolve_columns` maps them to value/group columns
(x-numeric plots need their own entry there; see references/statistics.md).

## 1. The column-role system

A PlotSpec `mapping` is one flat JSON object (`schemas/plot_spec.schema.json`:
`additionalProperties` of type string/number/boolean/null/array). It carries **both**
column roles (values are column names, or lists of column names) and plot options
(thresholds, booleans, method names). There is no separate options block on `main`.
The split between the two is declared in `make_my_figure_core/ui_hints.py`:
`COLUMN_FIELDS[plot_type]` lists the role keys; `OPTIONS[plot_type]` lists the rest.
`make_my_figure_core/presets.py::role_keys` / `split_mapping` use exactly that
declaration to keep column names out of style presets.

Role names are per-plot conventions, not a global enum. Names in use on `main`
(collect them with `python -c "from make_my_figure_core import ui_hints; print(sorted({k for v in ui_hints.COLUMN_FIELDS.values() for k in v}))"`):

- Generic axes: `x`, `y`, `color` (categorical colour-by), `group`, `shape`, `size`,
  `label`, `id_col`, `style_by`.
- Errors: `error` is **not** a column - it is the method name (`sem|sd|ci95|none`, or
  `iqr|range` for line bands) consumed by `base.summarize_error` / `summarize_band`.
- Significance tables: `p`, `x`/`y` as `logFC`/`AveExpr` (MA), `fdr`, `label`, `id_col`.
- Survival: `time`, `event`, `group`, `survival_columns` (precomputed form).
- Composition: `stack`, `facet_or_sort_by`.
- Matrices: `row_id` (heatmap, dendrogram, hierarchical clustering) or `matrix_row_id`
  (PCA), `value_columns` (list), `metadata_key` (PCA: column in the metadata table that
  matches sample column names), `exclude_columns`.
- Oncoprint: `sample`, `row`, `fill`. Classifier plots: `label`, `score`, `score2`,
  `prob`, `true`, `predicted`. Forest: `label`, `estimate`, `lower`, `upper`.
- Paired / longitudinal: `subject`, `condition`, `value`, `time`, `start`, `end`,
  `duration`. GWAS: `chrom`, `pos`, `snp`. Agreement: `method_a`, `method_b`.
  Dose-response: `dose`, `response`. Sets: `sets` (list). Flows/networks: `source`,
  `target`, `value`/`weight`, `interaction_type`.

Multi-column roles are enumerated in `ui_hints.MULTI_COLUMN_FIELDS`
(`value_columns`, `survival_columns`); frontends must render a multi-select for them.

Roles that live in an **aux** table rather than the main table: PCA `color`/`shape`
(`ui_hints.PCA_METADATA_FIELDS`), network node attributes (picked by alias from the
`nodes` aux table in `plots/network_graph.py::_node_table`).

## 2. Required vs optional roles: where validation happens

1. **Schema level** (`spec/validate.py::validate_plot_spec`): only shape - the five
   required top-level keys (`plot_type`, `input_table`, `mapping`, `journal_style`,
   `output`), value types inside `mapping`, known plot type and known style. It does not
   know which roles a plot needs.
2. **Renderer level**: `get_mapping(spec, key, required=True, context=PLOT_TYPE)` raises
   `RenderError("<plot>: mapping 'key' is required.")`; `require_columns(df, [...])`
   raises with the list of available columns; `coerce_numeric` raises when a role column
   has no numeric values. Optional roles default to `None` and are guarded with
   `if col:` (e.g. `color_by = get_mapping(spec, "color", None)`).
3. **Frontend level**: both GUIs offer a `"(none)"` sentinel; `DesktopController.build_spec`
   drops mapping values that are `None` or `""` before the spec is validated. The
   Streamlit generic option loop leaves `number` options with `default=None` unset unless
   the user types a value.
4. **Statistics level**: `statistics/runner.resolve_columns` maps roles to
   `value_column`/`group_column`/... with per-plot overrides; `statistics/validators.py`
   checks group counts and pairing before a test runs.

Documentation of required columns per plot: `examples/example_data_manifest.json`
(`required_columns`, `optional_columns`, `common_mistakes`) and `docs/PLOT_TYPE_REQUIREMENTS.md`.

## 3. Loaders (`make_my_figure_core/io/`)

### `loaders.load_table(source, *, source_name=None, file_type=None, sheet_name=None, header=0, header_fill="merged") -> TableInfo`

- `source` may be a path, raw `bytes`, or a binary file-like object (Streamlit upload).
- Extensions: delimited `.csv .tsv .txt .tab` (delimiter sniffed with `csv.Sniffer`,
  fallback to per-line consistency, then `.tsv`->tab, else comma); Excel
  `.xlsx .xls .xlsm` (`sheet_name` selects one sheet, default first). Unknown or missing
  extension: parsed as delimited text with a leading warning.
- Text is decoded `utf-8-sig`; floats parsed with `float_precision="round_trip"` so CSV
  and Excel copies of the same table load to identical doubles
  (`tests/test_loader_float_round_trip.py`).
- ID-like columns (name contains one of `_ID_HINTS = id, sample, patient, barcode,
  accession, replicate`) are forced to `string` dtype so `"001"` never becomes `1`.
- `header` may be an int, `None` (columns named `column_1..n`), or a list of rows for a
  stacked header (`_combine_header_rows`); for Excel, merged header ranges are read from
  the file (`_merged_header_grid`, `header_fill="merged"|"forward"`).
- `_post_process`: strips header whitespace, warns on duplicate column names, classifies
  `numeric_columns` vs `categorical_columns` (numeric dtype and not ID-like), records
  `missing_value_counts` and a warning listing them. Raises `LoaderError` for zero
  columns/rows or an unreadable file.
- `TableInfo` fields: `dataframe`, `source_name`, `delimiter`, `numeric_columns`,
  `categorical_columns`, `missing_value_counts`, `warnings`, and worksheet provenance
  (`source_workbook_name/hash`, `source_sheet_name/index/type`, `source_header_row`);
  `provenance()` returns only the non-null fields and is what `make_spec(source=...)`
  stores under `spec["source"]`.
- `table_info_from_dataframe(df, name)` runs the same post-processing on an in-memory
  frame (used after melts/transforms).

### `workbook.py` (multi-sheet Excel)

`inspect_excel_workbook(source)` -> `WorkbookInfo` (sheet names, hidden state, per-sheet
`WorksheetInfo` with an advisory `sheet_type` from `classify_worksheet`: `differential_results`,
`matrix`, `metadata`, `enrichment`, `documentation`, `generic`, `empty`, `unknown`).
`preview_excel_sheet` for the GUI table preview; `load_excel_sheet(workbook, sheet_name,
*, header, header_fill, sheet_type)` -> `TableInfo` with provenance filled in.
`sheet_output_dir` / `output_basename` / `sanitize_sheet_name_for_path` keep exports
worksheet-aware. Fixture: `examples/multi_sheet_workbook/synthetic_multisheet.xlsx`.

### Matrix inputs

Matrix plots take the main table as feature-by-sample: `row_id` (default: first column)
plus numeric sample columns. Which non-id columns are measurements is decided by
`plots/_v04_shared.resolve_value_columns` (honours `mapping["value_columns"]`, otherwise
`classify_matrix_columns` treats low-cardinality integer columns as annotations, not
values) and, in the GUIs, by `grouping.value_matrix_columns`. The Matrix Workflow
formalises this as `matrix_workflow.MatrixSpec` (`feature_id_column`, `value_columns`,
`value_type`, missing/duplicate policies, `confirmed_by_user`) and produces plot-ready
inputs through `matrix_workflow.plot_builder.build_plot_inputs` -> `PlotInputs`
(`dataframe`, `mapping`, `aux`, `spec_extra`).

### Aux tables

`registry.render(..., aux={name: DataFrame})`. On `main` two renderers declare `aux`:
`pca.py` (`aux["metadata"]`, joined on `metadata_key`) and `network_graph.py`
(`aux["nodes"|"node_attributes"|"node_table"]`). The bundled example records them in the
manifest entry's `aux_tables`; `examples.load_example` returns them as
`Dict[str, TableInfo]`. Desktop passes every loaded aux table; Streamlit passes PCA
metadata and, for `network_graph`, the bundled `nodes` table (see renderer-contract.md).

## 4. Missing-value behaviour

- Loaders never impute; they count and warn (`TableInfo.missing_value_counts`).
- Renderers convert role columns with `pd.to_numeric(errors="coerce")` and then drop NaN
  for summaries (`summarize_error`, `summarize_band`, `box_violin` `dropna()`,
  `ordered_unique` skips NaN/blank categories).
- Documented exceptions, always accompanied by a warning string:
  heatmap shows NaN as blank cells; `_v04_shared.numeric_matrix` treats missing entries as
  0 for linkage; PCA replaces missing entries with the feature mean; Manhattan drops
  out-of-range p-values and reports the count.
- A role column with no numeric values at all is a `RenderError` (`coerce_numeric`).
Rule for new renderers: drop and warn; never fill silently.

## 5. Category ordering and orientation conventions

- Default category order is **first-seen order in the data**
  (`list(dict.fromkeys(...))` or `_v04_shared.ordered_unique`). There is no global
  `category_order` mapping key on `main`; users reorder by sorting their table.
- Plot-specific ordering options: oncoprint `order` (`frequency|input`), waterfall `sort`
  (`ascending|descending`), enrichment `top_n`, stacked `facet_or_sort_by`, confusion
  matrix classes sorted, heatmap/hierarchical clustering `sort_by_cluster` and
  clustering order. Colour levels follow the same first-seen rule and map to
  `style.color_for(i)` by index.
- Orientation: plots are vertical by default; there is no generic `orientation` role.
  Exceptions: dendrogram `orientation` (`top|left`), swimmer and UpSet set-size bars use
  `barh`. Tick-label angle is a layout/option concern (`x_tick_rotation`: `auto|
  horizontal|45|vertical`, `y_label_rotation`), handled by `autorotate_xticklabels` and
  `apply_publication_layout`.
- Input shape is declared, not guessed, where two shapes are accepted: histogram
  `input_form` (`long|wide`), survival `input_form` (`subject_level|precomputed`).

## 6. Example datasets: three tiers

| Tier | Location | Registered where | Loader |
|---|---|---|---|
| Per-plot examples (authoritative) | `examples/by_plot_type/<slug>/{data.csv,data.tsv,data.xlsx,plotspec.json,README.md,<aux>.csv}` + `examples/example_data_manifest.json` + `examples/Make_My_Figure_All_Example_Data.xlsx` | `scripts/generate_example_data.py::EXAMPLES` | `make_my_figure_core/examples.py` |
| Legacy mock data | `mock_data/*.csv|tsv` + `mock_data/plot_schema_manifest.json` | `make_my_figure_core/data.py::SAMPLE_FILES` (hand-maintained; covers only the original plot types) | `data.load_sample`; also `tests/conftest.py::PLOT_SAMPLES` |
| Workflow fixtures | `examples/statistics/<slug>/` (+ `manifest.json`), `examples/matrix_workflow/`, `examples/preprocessing_workflow/`, `examples/multi_sheet_workbook/` | `scripts/generate_stats_examples.py`, `matrix_workflow/examples.write_examples`, `scripts/generate_multi_sheet_fixture.py` | tests and the wizards |

All example data are synthetic, CC0, seeded (`SEED = 42`, per-example stream
`SEED + index`). Frontends call `examples.has_manifest()` and fall back to `data` if the
manifest is absent (`DesktopController.load_example`, Streamlit "Bundled sample").

### Registering a bundled example for a new plot type

1. In `scripts/generate_example_data.py` write a builder `b_<name>(rng) -> (df, aux_df_or_None)`.
2. Append `Example(plot_type, slug, sheet, use_case, builder, required_columns,
   optional_columns, replace_help, common_mistakes, aux_name=None)` to `EXAMPLES` **at
   the end** (inserting earlier reseeds and rewrites every later example). `sheet` must
   be Excel-safe (<= 31 chars) and unique.
3. Make sure `registry._DEFAULT_MAPPINGS[plot_type]` names the builder's columns; the
   script writes `default_mapping(plot_type)` into the example `plotspec.json`.
4. Run `python scripts/generate_example_data.py`; commit the new folder, the manifest and
   the combined workbook. `tests/test_examples.py` then validates the spec, loads all
   three formats, checks required columns, renders and exports the example.
5. Optionally add a row to `mock_data/` and `data.SAMPLE_FILES`; not required.

Manifest entry fields (`examples.entry(plot_type)`): `plot_type`, `name`, `slug`,
`description`, `use_case`, `required_columns`, `optional_columns`, `files`
(`csv|tsv|xlsx|plotspec|readme`), `aux_tables`, `excel_sheet`,
`recommended_style_profiles`, `compatible_renderers`, `expected_export_formats`,
`data_type`, `source`, `license`, `provenance`, `n_rows`, `user_replacement_note`,
`common_mistakes`.

## Verify this is still current

```bash
# role declarations and multi-column roles
grep -n "^COLUMN_FIELDS\|^MULTI_COLUMN_FIELDS\|^PCA_METADATA_FIELDS" make_my_figure_core/ui_hints.py
# loader surface and ID hints
grep -n "^def load_table\|^_ID_HINTS\|float_precision\|utf-8-sig" make_my_figure_core/io/loaders.py
# plot types with and without a bundled example / legacy mock file
MPLBACKEND=Agg python -c "from make_my_figure_core.plots.registry import available_plot_types as a; from make_my_figure_core import examples, data; p=a(); print('no example:', [x for x in p if not examples.has_example(x)]); print('no mock_data:', [x for x in p if x not in data.SAMPLE_FILES])"
# how examples are registered
grep -n "^EXAMPLES\|^class Example\|Appended last" scripts/generate_example_data.py
```
