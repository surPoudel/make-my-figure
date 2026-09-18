# Plot registry (main, documented 2026-09-17)

File: `make_my_figure_core/plots/registry.py` (578 lines). It imports every renderer
module by name (lines 18-57), holds three dispatch tables, and exposes the render/export
entry points that both frontends, the recommender, the Figure Builder and the tests use.

Do not quote a plot count as a fact. Count it:

```bash
python .agents/makemyfigure-developer/scripts/inspect_registry.py
# or, inline:
MPLBACKEND=Agg python -c "from make_my_figure_core.plots.registry import available_plot_types as a; print(len(a()), a())"
```

## 1. Tables inside registry.py that a new plot type must join

There are exactly three, all keyed by the module's `PLOT_TYPE` constant:

| Table | Line | Value | Read by |
|---|---|---|---|
| `_RENDERERS: Dict[str, Callable]` | 67 | `module.render` | `available_plot_types()`, `render()` dispatch. Insertion order **is** the UI order (both apps list `available_plot_types()` verbatim). Entries are grouped under `# --- v0.4 ---` / `# --- v0.5 ---` comments; append new ones at the end or under a new version comment. |
| `_DEFAULT_MAPPINGS: Dict[str, Dict]` | 111 | default `mapping` dict (column names that match the bundled example, plus option defaults) | `default_mapping()`, `make_spec()`, both frontends' initial widget values, `scripts/generate_example_data.py` (writes it into each example `plotspec.json`). |
| `_DISPLAY_NAMES: Dict[str, str]` | 174 | human label | `display_name()`; falls back to the raw key if missing. |

Also in the file: the import block (lines 18-57) - the module must be added there;
`_EXPORT_FORMATS = ("svg", "png", "pdf", "tiff", "eps")` (line 217) and
`_VECTOR_TEXT_RC` (line 222, keeps vector text editable). Neither is per-plot.

### What is NOT in registry.py (as of main)

There are no required-role, category, aux-table or ordering tables. On
`main` none of these exist as registry tables:

- **Required roles** are enforced inside each renderer via `get_mapping(..., required=True)`
  and `require_columns`. Documentation of required/optional columns lives in
  `examples/example_data_manifest.json` (`required_columns`, `optional_columns`, produced
  from `scripts/generate_example_data.py::EXAMPLES`) and in `docs/PLOT_TYPE_REQUIREMENTS.md`.
- **Categories / grouping of plot types**: none. The UI shows a flat list in `_RENDERERS`
  order. `recommendations/plot_recommender.py` and `matrix_workflow/recommendations.py`
  hard-code which plot types they may suggest, but that is not a category system.
- **Aux-table requirements**: discovered at call time - `render()` passes `aux` only when
  the renderer signature declares an `aux` parameter (line 330). Which aux tables exist
  for the bundled example is recorded per entry in the manifest (`aux_tables`), and
  `data.py` special-cases PCA metadata for the legacy `mock_data/` bundle.
- **Ordering**: dict insertion order of `_RENDERERS`.

## 2. Per-plot tables OUTSIDE registry.py that also need an entry

Adding a plot type touches these too (all keyed by `PLOT_TYPE`):

| Where | Required? | Notes |
|---|---|---|
| `make_my_figure_core/ui_hints.py::COLUMN_FIELDS` | yes | Column-chooser roles for both GUIs. `presets.role_keys` also reads it. |
| `make_my_figure_core/ui_hints.py::OPTIONS` | yes (may be `[]`) | Non-column options with `scope`. |
| `scripts/generate_example_data.py::EXAMPLES` | yes | Append an `Example(...)` at the END (seeding depends on list index), run the script, commit `examples/by_plot_type/<slug>/`, the manifest and the combined workbook. `tests/test_examples.py::test_every_supported_plot_type_has_example` enforces coverage. |
| `make_my_figure_core/styles/capabilities.py::_CAPS` | recommended | Regenerate with `python scripts/audit_style_capabilities.py --write`; unlisted types get the axes-based default. |
| `make_my_figure_core/statistics/runner.py::resolve_columns` and `statistics/test_registry.py::recommend_tests` | if the plot supports statistics and its roles are not `x`/`y`/`group` | Otherwise "No automatic statistical test is offered". |
| `make_my_figure_core/data.py::SAMPLE_FILES` (+ `mock_data/*.csv`, `plot_schema_manifest.json`) | no | Legacy fallback bundle; many later plot types are absent from it by design. |
| `recommendations/plot_recommender.py`, `matrix_workflow/recommendations.py` | optional | Only if the recommender should propose the new plot. |
| `tests/test_renderers_m2.py:23`, `tests/test_desktop_controller.py:29` | yes | Hard-coded count assertions; bump them. |
| `apps/desktop_app/main.py::_MATRIX_PLOT_TYPES`, `apps/streamlit_app/streamlit_app.py::_MATRIX_PLOT_TYPES*` | only for matrix-shaped plots | See renderer-contract.md section 7. |
| `docs/PLOT_TYPE_REQUIREMENTS.md`, `CHANGELOG.md` | yes | Documentation. |

A one-shot consistency check for the core tables (all lists should be empty except the
legacy `mock_data` one):

```bash
MPLBACKEND=Agg python - <<'PY'
from make_my_figure_core.plots import registry as r
from make_my_figure_core import ui_hints, examples, data
from make_my_figure_core.styles import capabilities as c
pts = r.available_plot_types()
for name, table in [("display", r._DISPLAY_NAMES), ("default_mapping", r._DEFAULT_MAPPINGS),
                    ("ui_hints.COLUMN_FIELDS", ui_hints.COLUMN_FIELDS), ("ui_hints.OPTIONS", ui_hints.OPTIONS),
                    ("capabilities._CAPS (default used)", c._CAPS), ("mock_data (legacy, optional)", data.SAMPLE_FILES)]:
    print(name, [p for p in pts if p not in table])
print("examples", [p for p in pts if not examples.has_example(p)])
PY
```

## 3. Public functions in registry.py

| Function | Line | Behaviour |
|---|---|---|
| `available_plot_types() -> List[str]` | 225 | `list(_RENDERERS)` in insertion order. |
| `display_name(plot_type) -> str` | 229 | `_DISPLAY_NAMES.get(pt, pt)`. |
| `default_mapping(plot_type) -> dict` | 233 | Copy of `_DEFAULT_MAPPINGS[pt]` (empty dict if absent). |
| `make_spec(plot_type, input_table, journal_style, *, mapping, layout, statistics, output, source)` | 237 | Builds a PlotSpec; `output` defaults to `spec.validate.default_output_block()` (svg/png/pdf, 89x70 mm, 300 dpi); `source` (worksheet provenance) is mirrored into `statistics["source"]`. The desktop app uses its own `DesktopController.build_spec` instead (adds `layout.column_width`, normalises statistics). |
| `render(spec, df, *, style=None, validate=True, aux=None) -> RenderResult` | 272 | Pipeline: legacy style-name migration -> `validate_plot_spec(known_plot_types=available_plot_types(), known_styles=list_profiles())` -> `load_profile` unless `style` given -> `style.with_overrides(spec.get("style"))` -> `warn_ignored_style_controls` -> dispatch (with `aux` if declared) -> `apply_publication_layout` on `figure.axes[0]` if `spec["layout"]` -> re-place legend if `layout.legend_location` -> `metadata.setdefault("spec", spec)` -> manual `annotations` -> `check_publication_readiness` -> optional `auto_fix_layout` + `check_layout`. Every post-step is wrapped so it can only add warnings, never fail the render. |
| `export_figure(fig, base_path, formats, dpi=300) -> List[str]` | 449 | Writes `base_path.<fmt>` for each format in `_EXPORT_FORMATS` (unknown formats skipped silently); `bbox_inches="tight"` with `_bbox_extra_artists` so long axis labels are not clipped; dpi only for png/tiff; tiff uses LZW. |
| `write_sidecar(spec, metadata, base_path) -> str` | 475 | `base_path.plot_spec.json` = `{"plot_spec": spec, "render_metadata": metadata minus "spec"}`. |
| `write_stats_sidecar(spec, result, base_path) -> Optional[str]` | 484 | `base_path.stats_spec.json` via `statistics.schemas.stats_sidecar_payload`; `None` when no `stats_report`. |
| `figure_to_bytes(fig, fmt, dpi=300) -> bytes` | 501 | In-memory single format (Streamlit downloads, Figure Builder, desktop preview). |
| `export_bundle_bytes(spec, result, *, formats, dpi, basename) -> bytes` | 519 | ZIP with each format + `plot_spec.json` (+ `stats_spec.json`). Default formats svg/png/pdf. |
| `render_to_files(spec, df, base_path, *, formats, style, aux) -> dict` | 552 | `render` + `export_figure` + both sidecars; returns `{"files", "sidecar", "stats_sidecar", "metadata", "warnings"}`. Formats/dpi fall back to `spec["output"]`. |

Private but worth knowing: `_bbox_extra_artists(fig)` (line 429) extends matplotlib's
default tight-bbox artist list with axis labels and titles.

Re-exported from `make_my_figure_core/__init__.py`: `render`, `render_to_files`,
`available_plot_types`, `display_name`, `default_mapping`, `make_spec`,
`export_bundle_bytes`, `figure_to_bytes`, `RenderResult`. `export_figure`,
`write_sidecar`, `write_stats_sidecar` must be imported from `plots.registry` directly
(the desktop controller does so).

## 4. Registration checklist (minimal, core only)

1. Create `make_my_figure_core/plots/<name>.py` with `PLOT_TYPE` and `render` (see
   renderer-contract.md).
2. `registry.py`: add the module to the import block; add entries to `_RENDERERS`,
   `_DEFAULT_MAPPINGS`, `_DISPLAY_NAMES`.
3. `ui_hints.py`: add `COLUMN_FIELDS[PLOT_TYPE]` and `OPTIONS[PLOT_TYPE]`.
4. `scripts/generate_example_data.py`: append an `Example`, run it, commit outputs.
5. `python scripts/audit_style_capabilities.py --write`.
6. Bump the two count assertions in tests; add a renderer test (see `tests/test_v04_plots.py`
   for the parametrised pattern, `tests/test_examples.py` renders every manifest entry).
7. If matrix-shaped or aux-dependent, edit the frontend sets listed in section 2.

## 5. Who calls `render()` (so you know what a registry change affects)

| Caller | Path | Notes |
|---|---|---|
| Desktop | `apps/desktop_app/controller.py::DesktopController.render` (line ~433) | Passes every loaded aux table as `aux`. Export via `export_files` (`export_figure` + `write_sidecar`) and `export_bundle`. |
| Desktop Matrix Workflow | `controller.matrix_build_plot`, `matrix_qc_plot` | Render `PlotInputs.dataframe` with `PlotInputs.aux`. |
| Streamlit | `apps/streamlit_app/streamlit_app.py` (line ~1229) | `render(spec, df, style=style, aux=render_aux)`; downloads via `figure_to_bytes`. |
| Figure Builder | `make_my_figure_core/panels/builder.py::_render_panel_figure` | Re-renders each panel's PlotSpec; `export_multipanel` has its own savefig loop. |
| Recommender | `recommendations/plot_recommender.py::_draft` | Uses `make_spec` only (drafts, does not render). |
| QC / selftest | `apps/desktop_app/main.py::run_selftest` (line ~2963), `scripts/generate_*_gallery.py`, `scripts/build_figure_preset_qc.py` | Iterate `available_plot_types()`; a new type is exercised automatically. |
| Tests | `tests/test_examples.py` (every manifest entry), `tests/test_figure_preset_qc.py` (parametrised over `available_plot_types()`), `tests/test_app_smoke.py` | Plus the two fixed-count tripwires listed in section 2. |

## 6. Sidecar formats written by the registry

- `<base>.plot_spec.json` (`write_sidecar`): `{"plot_spec": <spec as rendered, including
  any legacy-style migration>, "render_metadata": <RenderResult.metadata minus "spec">}`.
  `render_metadata` therefore contains `publication_check`, `layout_qc`, the renderer's
  scientific keys (n per group, error method, cutoffs, ...) and `statistics_report`.
- `<base>.stats_spec.json` (`write_stats_sidecar`): `statistics.schemas.stats_sidecar_payload`
  = normalised StatsSpec + `results` (each `StatResult.to_dict()`) + `method_paragraph`,
  `legend_sentence`, `correction_method`, `warnings`, `software_versions`, `disclaimer`.
- The ZIP from `export_bundle_bytes` contains the same two JSON files next to the images.
- Multi-panel figures use `panels/builder.multipanel_sidecar` instead (references each
  panel's PlotSpec and StatsSpec).

Reading a sidecar back: `DesktopController.load_plotspec(path)` (controller.py:164)
requires `plot_type` at the top level, so it opens a bare PlotSpec but **rejects the
`{"plot_spec": ...}` wrapper that `write_sidecar` produces** unless the caller unwraps it
first. No frontend on `main` unwraps it (grep `"plot_spec"` in `apps/`). Keep this in
mind when documenting "reproduce a saved figure".

## Verify this is still current

```bash
# the three tables and their line numbers
grep -n "^_RENDERERS\|^_DEFAULT_MAPPINGS\|^_DISPLAY_NAMES\|^_EXPORT_FORMATS\|^def " make_my_figure_core/plots/registry.py
# every registered type should appear exactly three times as a "PLOT_TYPE:" key (3 tables)
python -c "import re;s=open('make_my_figure_core/plots/registry.py').read();from make_my_figure_core.plots.registry import available_plot_types as a;print(len(re.findall(r'\.PLOT_TYPE: ', s)), '==', 3*len(a()))"
# tests that pin the count
grep -rn "available_plot_types()) ==\|plot_types()) ==" tests/
# module-level tables (expect exactly _RENDERERS, _DEFAULT_MAPPINGS, _DISPLAY_NAMES, _EXPORT_FORMATS, _VECTOR_TEXT_RC)
grep -n "^_[A-Z_]* *[:=]" make_my_figure_core/plots/registry.py
```

## Caution: duplicate keys in `ui_hints.OPTIONS`

The `OPTIONS` dict literal on main contains a few plot types twice (later entry wins silently). Add
each new key ONCE, before the closing brace, and never "fix" an existing duplicate as part of an
unrelated plot change. `scaffold_plot.py --wire` warns when it sees duplicates.
