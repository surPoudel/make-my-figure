# Portable Figure Package (`.mmfpackage`)

## Status: NOT on `main`

As of 2026-09-17, `main` (bb45c12, release v1.1.0) has **no** `make_my_figure_core/package/`,
no `docs/FIGURE_PACKAGES.md`, no `schemas/figure_package_manifest.schema.json` and no
`tests/test_figure_package*.py`. On `main` the reproducibility artifacts are the PlotSpec sidecar
(`*.plot_spec.json`), the StatsSpec sidecar (`*.stats_spec.json`) and the FigureSpec sidecar
(`*.figure_spec.json`); none of them carries data.

The Figure Package lives on two unmerged branches (both present as local and `origin/` refs):

| Branch | Worktree (sibling of this checkout) | Notes |
|---|---|---|
| `feature/portable-figure-package-v1.1.1` | `../make_my_plot_v111` | v1.1.1 candidate; the original implementation |
| `feature/evidence-derived-journal-presets` | `../make_my_plot_journal_presets` | carries the same package code plus a pandas>=3 string-dtype fix in `package/tabledata.py` (`_STRING_DTYPE_NAMES`, `_HAS_DEFAULT_STR_DTYPE`) and one extra integrity test |

`diff -rq` between the two `make_my_figure_core/package/` directories shows only `tabledata.py`
differing. Everything below was read from the `feature/evidence-derived-journal-presets` worktree.

**When merged to main, update this file**: remove this status section, re-check every path and
symbol below against the merged code, and add the package tests to the "builder/all-plot-type"
lists in `figure-builder.md` and the round-trip list in `plotspec.md`.

## 1. Three artifacts, three purposes

`make_my_figure_core/package/__init__.py` docstring and `manifest.py::ARTIFACT_DESCRIPTIONS`
define the vocabulary that both frontends must use verbatim:

* **PlotSpec** `*.plot_spec.json` - the recipe for one plot; needs the source data to reopen.
* **Figure preset** `*.mmfpreset.json` - reusable appearance/configuration; no data.
* **Figure package** `*.mmfpackage` - recipe + frozen tables + statistics/preprocessing records +
  imported assets + previews + checksums; reopens without the original files.

## 2. Module map (`make_my_figure_core/package/`)

| Module | Purpose | Key symbols |
|---|---|---|
| `manifest.py` | constants, checksums, environment record, manifest schema validation | `PACKAGE_FORMAT = "make_my_figure.figure_package"`, `PACKAGE_FORMAT_VERSION = 1`, `SUPPORTED_FORMAT_VERSIONS = (1,)`, `PACKAGE_EXTENSION = ".mmfpackage"`, `MANIFEST_NAME`, `ENVIRONMENT_PATH = "environment/environment.json"`, `PRIVACY_NOTICE`, `sha256_bytes`, `sha256_file`, `utc_now_iso`, `environment_record`, `load_manifest_schema`, `validate_manifest`, `json_bytes` |
| `tabledata.py` | lossless DataFrame <-> JSON ("mmftable") | `TABLE_FORMAT = "make_my_figure.table"`, `TABLE_FORMAT_VERSION = 1`, `encode_table`, `decode_table`, `table_to_json_bytes`, `table_from_json_bytes`, `table_digest`, `table_summary`, `TableEncodingError` |
| `writer.py` | assemble ZIP + manifest | `TableSource`, `AssetSource`, `PlotComponent`, `PackageContent`, `WriteReport`, `PackageWriteError`, `build_package_bytes`, `write_figure_package`, `default_package_filename`, `estimate_package_size`, limits `LARGE_PACKAGE_WARN_BYTES`, `MAX_ORIGINAL_COPY_BYTES`, `CSV_COPY_MAX_CELLS` |
| `reader.py` | open, verify, reconstruct | `FigurePackage`, `PackageTable`, `PackageError`, `PackageFormatError`, `PackageIntegrityError`, `PackageVersionError`, `inspect_figure_package`, `open_figure_package`, `single_plot_inputs`, `rebuild_composite`, `verify_statistics`, `verify_preprocessing` |
| `security.py` | untrusted-ZIP rules | `PackageSecurityError`, `check_member_name`, `scan_zip`, `safe_basename`, `read_member`, caps `MAX_ENTRIES`, `MAX_ENTRY_BYTES`, `MAX_TOTAL_BYTES`, `MAX_COMPRESSION_RATIO`, `MAX_MANIFEST_BYTES` |
| `assemble.py` | frontend-independent "what was on screen" -> `PackageContent` | `MatrixContext`, `content_for_single_plot`, `content_for_composite` |
| `__init__.py` | re-exports all of the above plus `is_package_path` | |

Schema: `schemas/figure_package_manifest.schema.json` (bundled via `resource_path`).
User doc: `docs/FIGURE_PACKAGES.md`.

## 3. Container layout and manifest

ZIP members written by `writer.build_package_bytes` (all with a fixed 1980-01-01 timestamp so
bytes are deterministic):

```
manifest.json
plot_spec.json | figure_spec.json            (single_plot | composite)
stats_spec.json                              (only when statistics ran)
render_metadata.json                         (single plot)
matrix_spec.json, sample_metadata_spec.json, preprocessing_spec.json   (matrix workflow)
panels/<component_id>/plot_spec.json, stats_spec.json, panel.json      (composite)
data/<table_id>.mmftable.json  +  data/<table_id>.csv (convenience copy, <= CSV_COPY_MAX_CELLS)
data/original/<table_id>/<original filename>  (copied when <= MAX_ORIGINAL_COPY_BYTES)
assets/<asset_id>/<sanitised image name>     (imported external panels)
preview/figure.png .svg .pdf
environment/environment.json
README.txt
```

Manifest fields (schema-required ones in bold): **package_format**, **format_version**,
**created_with** {application, version, commit}, **created_at**, **figure_kind**
(`single_plot` | `composite`), **name**, **privacy_notice**, **specs** {plot_spec | figure_spec,
stats_spec, matrix_spec, sample_metadata_spec, preprocessing_spec -> internal paths},
**components** [component_id, kind (`plot` | `make_my_figure_panel` | `external_figure_panel`),
label, title, plot_type, plot_spec, stats_spec, table_id, aux_tables {name -> table_id}, asset,
width_in, height_in], **tables** [table_id, role (`source_table` | `derived_table` | `aux_table`
| `metadata_table`), path, encoding `mmftable/1`, sha256, bytes, content_digest, n_rows,
n_columns, columns, dtypes, n_missing, display_name, derived_from, csv_copy, original_file
{filename, sheet_name, header_row, path, sha256, bytes, included, note}, provenance], assets,
previews, **files** [path, sha256, bytes, role] for every member except the manifest itself,
relationships (`derived_from` edges), environment (path), warnings, compatibility
{min_reader_format_version, reader_must_verify_checksums, features}.

The **environment record** (`manifest.environment_record`) stores application version and
commit (from `version.build_info`), Python version, platform, matplotlib backend and the
installed versions of numpy, pandas, matplotlib, scipy, statsmodels, openpyxl, jsonschema.

Privacy: absolute paths are never written unless `PackageContent.record_original_paths=True`
(then `original_file.original_location`). Originals are recorded by basename + SHA-256.

## 4. Writer API

```python
content = content_for_single_plot(spec, df, result, table_name=..., aux=..., source_path=...,
                                  sheet_name=..., provenance=..., matrix=MatrixContext(...), name=...)
report  = write_figure_package(content, "figure")        # adds .mmfpackage, writes via .part + os.replace
data, manifest, warnings = build_package_bytes(content)  # in-memory variant (Streamlit download)
```

`content_for_single_plot` freezes the exact DataFrame the renderer received as
`role="derived_table"` when a `MatrixContext.source_dataframe` differs from it (and then also
freezes the original as `role="source_table"` with a `derived_from` relationship), otherwise
as the single source table; aux tables become `aux_table` entries referenced from
`PlotComponent.aux_tables`; `stats_payload` is `stats_sidecar_payload(spec["statistics"], result.stats_report)`.
`content_for_composite(mpf, fig, panel_results=[...], panel_sources={...})` walks a
`MultiPanelFigure`, deduplicates identical tables by digest (`_dedup_table`), turns imported
panels into `AssetSource`s and stores `Panel.to_dict()` as `panel_record`.
`build_package_bytes` validates the finished manifest against the schema and raises
`PackageWriteError` on duplicate ids, unknown table references, missing assets or an invalid
manifest.

## 5. Reader API, integrity and errors

`open_figure_package(src, *, assets_dir=None, load_previews=False) -> FigurePackage` runs, in
order and before any data are used: `security.scan_zip` (names, links, sizes, ratio) ->
`_read_manifest` (present, JSON, `package_format` marker, integer `format_version` in
`SUPPORTED_FORMAT_VERSIONS`, schema-valid) -> integrity (every listed file present with the
recorded byte count **and** SHA-256; any unlisted member is an error) -> decode tables and check
their shape against the manifest -> parse specs and per-component panel specs -> copy assets
into a fresh directory under `safe_basename` names -> cross-check component table/asset refs.

Error classes (all `PackageError` subclasses with user-facing `str(exc)`):

| Class | Raised for |
|---|---|
| `PackageFormatError` | not a ZIP, missing/invalid manifest, wrong `package_format`, schema violation, missing listed file, undecodable table, dangling component reference, and any `PackageSecurityError` (wrapped: "rejected for safety") |
| `PackageIntegrityError` | unlisted extra file, size or SHA-256 mismatch, table shape mismatch |
| `PackageVersionError` | `format_version` newer than supported ("Update the application") or dropped |

`inspect_figure_package` returns the validated manifest without checksum verification (for
"Recent files" style previews). `FigurePackage` exposes `kind`, `name`, `components`,
`plot_spec`, `stats_payload`, `matrix_spec`, `sample_metadata_spec`, `preprocessing_spec`,
`figure_spec`, `table_for(component)`, `aux_for(component)`, `source_table()`, `derived_table()`,
`summary_lines()`, `integrity == "verified"`.

Reconstruction: `single_plot_inputs(pkg) -> (spec, df, aux)` (deep-copies the spec and
normalises legacy style names); `rebuild_composite(pkg) -> MultiPanelFigure` (uses
`panels.panel_from_dict`, `FigureLayout.from_dict`, attaches frozen tables/aux, points imported
panels at the extracted assets, then `autolabel()`).

### Statistics and preprocessing verification on reopen

* `verify_statistics(stored_payload, fresh_report) -> List[str]`: compares the stored
  `stats_spec.json["results"]` with `report.results` re-run on the frozen data; identity keys
  (`test_id`, `group_a/b`, `n_total`, `correction_method`, `effect_size_name`) must match
  exactly; numeric keys (`statistic`, `p_value`, `adjusted_p_value`, `effect_size`, CI bounds)
  via `math.isclose(rel_tol=1e-9)`. Empty list = identical. Mismatch is reported as a warning,
  never used to overwrite the stored results.
* `verify_preprocessing(pkg, *, max_cells=5_000_000) -> {"status", "detail"}`: re-runs the stored
  `PreprocessingSpec` steps on the frozen source table with
  `matrix_workflow.run_preprocessing` and compares to the frozen derived table
  (`np.array_equal`, falling back to `allclose(rtol=1e-10)`). Status is `identical`, `differs`,
  `skipped` (no records or too large) or `error`. `_replay_params` prefers a step's
  `user_parameters` (written by v1.1.1+) over the merged `parameters`. The figure is always
  drawn from the frozen derived table regardless of the outcome.

### Security rules (`security.py`)

Relative forward-slash names only (no `..`, `.`, empty segments, drive letters, backslashes,
control characters); symlink/char/block/FIFO entries rejected; `MAX_ENTRIES` 5000, 1 GiB per
entry, 3 GiB total, compression ratio cap 400 for members over 1 MiB; `read_member` enforces the
byte limit even if the header lies; nothing is unpickled or executed
(`tests/test_figure_package_integrity.py::test_no_pickle_or_code_paths_in_reader`).

### Table encoding (`tabledata.py`)

Per-column kind + dtype; floats via shortest round-trip repr with explicit NaN/Inf/-0.0 handling;
ints exact; strings vs missing distinct; categoricals with categories and order; datetimes as
nanoseconds. Bytes are deterministic so `table_digest(df)` (SHA-256 of the encoding) is a content
digest. The v1.1.1 frontends also write `source.source_table_sha256` into exported PlotSpecs
(`apps/desktop_app/controller.py` and `apps/streamlit_app/streamlit_app.py` on those branches)
so "Open PlotSpec" can warn when the data changed.

## 6. What a new plot type must do to be package-compatible

Usually **nothing renderer-specific**. The package stores the PlotSpec verbatim, the exact
DataFrame(s) the renderer received, and the StatsSpec payload; reopening calls the ordinary
`registry.render(spec, df, aux=aux)`. Any renderer that is PlotSpec-complete (see
`plotspec.md` section 10) and deterministic therefore round-trips. The controller-level test
`tests/test_figure_package_controller.py::test_every_plot_type_packages_and_reopens` iterates
`available_plot_types()`, so a new type is covered automatically once it has an example.

Things that **would** break it:

* **Reading data from anywhere other than `df`/`aux`** (files on disk, URLs, module globals).
  Only what arrives through `render(spec, df, aux=...)` is frozen. Auxiliary tables must be
  passed through the `aux` dict so `content_for_single_plot` can freeze them as `aux_table`s.
* **Non-deterministic output without a seed** (random layouts, label repulsion). The package
  tests compare a structural figure signature; three plot types are documented as needing the
  `_reduced` comparison (text positions dropped). Expose any RNG seed in `mapping` (as
  `network_graph` does with `seed`).
* **Values that are not JSON-serialisable in the spec or metadata**. `manifest.json_bytes`
  converts numpy scalars/arrays, sets, tuples and `to_dict()` objects; anything else is
  stringified, which would not round-trip.
* **External images referenced from a PlotSpec**. Only Figure Builder imported panels are
  packaged (as `AssetSource`s); a renderer that draws a file path from `mapping` would lose it.
* **Table dtypes outside the mmftable kinds** (e.g. nested objects in cells). `encode_table`
  emits warnings for such cells; check `WriteReport.warnings`.

## 7. Test pattern to extend: `tests/test_figure_package.py::test_single_plot_round_trip`

The module builds a **structural signature** (`figure_signature(fig)`: figure size, per-axes
limits, ticks, labels, tick labels, text content+positions, line xy/colour/style, collection
offsets/facecolors, patch bounds, image digests, legend texts) and a helper `_round_trip`:

```python
res  = render(spec, df, aux=aux or None)
content = content_for_single_plot(spec, df, res, table_name=spec["input_table"], aux=aux, name=name)
rep  = write_figure_package(content, str(tmp_path / name))
pkg  = open_figure_package(rep.path)
spec2, df2, aux2 = single_plot_inputs(pkg)
pd.testing.assert_frame_equal(df, df2, check_exact=True, check_dtype=True)
res2 = render(spec2, df2, aux=aux2 or None)
assert compare_signatures(res.figure, render(spec, df, aux=aux or None).figure, res2.figure)
assert spec2 == json.loads(json.dumps(spec))
```

`compare_signatures(a, a_again, b)` renders the original twice; if the original is itself
non-deterministic it falls back to `_reduced` (text positions and patches removed). The test is
parametrised over `REPRESENTATIVE = [(plot_type, extra_spec_keys), ...]`; entries with
`"statistics"` additionally assert `stats_spec.json` exists, `verify_statistics(...) == []`, and
per-result numeric equality at `rel=1e-12`; entries without statistics assert no empty
`stats_spec.json` is written. To cover a new plot type, load its example with
`examples.load_example(plot_type)` and append `(plot_type, {})` (or with a statistics block) to
`REPRESENTATIVE`.

Other tests in the family: `test_composite_package_round_trip` (three panels incl. an imported
PNG; deletes the source assets before reopening), `test_derived_matrix_package_keeps_source_derived_and_records`,
`test_no_absolute_paths_and_manifest_lists_everything`, `test_clean_process_moved_package_and_lab_to_lab`
(subprocess reopen), `test_old_standalone_plotspec_still_loads_and_digest_detects_change`;
`tests/test_figure_package_integrity.py` (tampering, checksum, unlisted file, traversal names,
symlink, zip-bomb ratio, newer version, encoding precision); `tests/test_figure_package_controller.py`;
`tests/test_figure_package_ui_wiring.py` (source-level checks that both frontends route through the
core module and use the three-artifact wording).

## Verify this is still current

```bash
# on main: still absent?
ls make_my_figure_core/package docs/FIGURE_PACKAGES.md schemas/figure_package_manifest.schema.json 2>&1
git branch -a | grep -i "portable-figure-package\|journal-presets"
# on the branch worktree: symbols and versions
grep -n "PACKAGE_FORMAT_VERSION\|SUPPORTED_FORMAT_VERSIONS\|PACKAGE_EXTENSION" ../make_my_plot_journal_presets/make_my_figure_core/package/manifest.py
grep -n "^def test\|^REPRESENTATIVE" ../make_my_plot_journal_presets/tests/test_figure_package.py
diff -rq ../make_my_plot_v111/make_my_figure_core/package ../make_my_plot_journal_presets/make_my_figure_core/package | grep -v pycache
```
