# Testing reference — MakeMyFigure

Reconstructed from the live checkout on 2026-09-17 (branch
`feature/makemyfigure-developer-agent`, forked from `main` at bb45c12). Every
statement below names the file or command it came from. Re-run the commands in the
last section before trusting a number.

## 1. Layout and naming

- All tests live in one flat directory, `tests/`. There are no sub-packages; pytest
  is pointed at it by `[tool.pytest.ini_options] testpaths = ["tests"]` in
  `pyproject.toml` (the only pytest configuration in the repo — no `pytest.ini`,
  no `conftest` outside `tests/`, no markers registered).
- Files are `tests/test_<topic>.py`; functions are `def test_<what_it_asserts>()`.
  Newer files use long descriptive names in plain English
  (`tests/test_histogram_distribution.py::test_x_range_that_would_cut_bars_off_is_refused`);
  older files use terse names (`tests/test_renderers.py::test_export_svg_png_pdf`).
  Follow the descriptive style for new tests.
- Version/era files exist and are still live: `tests/test_v04_plots.py`,
  `tests/test_v05_features.py`, `tests/test_v1_1_renderer_options.py`,
  `tests/test_renderers_m2.py` (milestone 2). A new plot type does not get a new
  "vN" file; it gets its own topic file (the histogram pattern).
- Count files and functions with commands, never by hand:

```bash
find tests -name 'test_*.py' | wc -l                                  # test modules
grep -rhoE '^\s*(async )?def test_[A-Za-z0-9_]+' tests --include='*.py' | wc -l   # test functions (source)
MPLBACKEND=Agg python -m pytest --collect-only -q -p no:pytest-qt --ignore=tests/test_desktop_gui.py | tail -1   # collected items incl. parametrisation
```

On 2026-09-17 these gave 95 modules, 925 `def test_` functions, and
"1648 tests collected in 23.54s" (parametrisation over the 38 plot types is why the
collected count is much higher than the function count).

## 2. Running the suite

### Headless / Linux / WSL2 (the environment the release audit used)

```bash
MPLBACKEND=Agg python -m pytest -q -p no:pytest-qt --ignore=tests/test_desktop_gui.py
```

- `tests/conftest.py` already calls `matplotlib.use("Agg")` before anything else and
  inserts the repo root on `sys.path`, so the suite runs from a bare checkout without
  `pip install -e .`. Setting `MPLBACKEND=Agg` as well is belt-and-braces for scripts
  that import matplotlib before conftest is loaded.
- `-p no:pytest-qt` is required whenever PySide6 is installed but its native
  libraries are not (`libEGL`, `libxkbcommon`): the pytest-qt plugin imports Qt at
  start-up and aborts collection. Documented in `README.md` (lines 183-184) and in
  `reports/fable5_release_audit/baseline_test_results.md`.
- `--ignore=tests/test_desktop_gui.py` skips the one module that needs a real Qt
  event loop. The other Qt-touching modules (`tests/test_pop_out_panels.py`,
  `tests/test_performance.py`, `tests/test_desktop_controller.py`) use
  `pytest.importorskip("PySide6")` and skip themselves cleanly.
- Streamlit modules (`tests/test_app_smoke.py`, `tests/test_streamlit_matrix_wizard.py`,
  `tests/test_streamlit_presets.py`) `importorskip("streamlit")`.

### Qt GUI tests (Windows, or Linux with Qt runtime libraries)

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_desktop_gui.py -v
```

`tests/test_desktop_gui.py` holds 41 tests (`grep -c '^def test_'`). The v1.1.0
audit (`docs/releases/v1.1.0/release_v1.1.0_audit.md` §5a) ran them on WSL2 only after
adding conda-forge Qt libraries to `LD_LIBRARY_PATH`; on a Windows machine with
`pip install -e ".[desktop,dev]"` they run directly. Two of these tests hung or were
stale before v1.1.0 and were repaired in commit 5686c42; if a GUI test hangs under
offscreen, suspect a modal dialog first (the audit's diagnosis).

### Full suite in a complete environment

```bash
python -m pytest -q          # what README.md and docs/RELEASE_CHECKLIST.md prescribe
```

### Runtime

- Full headless suite: **1644 passed, 5 skipped in 952 s** on WSL2 with the repo on a
  OneDrive-synced `/mnt/c` path (audit §5, 2026-09-06). Expect roughly 15-16 min there;
  a local NVMe checkout is substantially faster (not measured in any tracked report).
- GUI module alone: 41 passed in 296 s (audit §5a).
- Focused files are quick: `tests/test_r_validation_regressions.py` 7 passed in ~10 s.

## 3. Shared fixtures and helpers

`tests/conftest.py` is the only conftest. It provides:

| Name | Kind | What it gives |
|---|---|---|
| `repo_root` | fixture | absolute checkout root |
| `mock_dir` | fixture | `mock_data/` path |
| `plot_case` | parametrised fixture | `(plot_type, csv_path, filename)` for each of the 18 entries in `PLOT_SAMPLES` (plot type -> golden mock file) |
| `PLOT_SAMPLES` | dict | the golden-input table itself; `tests/test_renderers.py` and `tests/test_examples.py` import it |
| `PCA_METADATA_FILE` | constant | `pca_sample_metadata.csv` |

Beyond conftest, tests reach for the core's own helpers rather than test-local
copies: `make_my_figure_core.examples.load_example(pt)` (bundled synthetic example per
plot type, manifest in `examples/`), `make_my_figure_core.plots.registry.available_plot_types()`,
`make_my_figure_core.validate.validate_plot_spec(spec, known_plot_types=...)`,
`make_my_figure_core.ui_hints.column_fields(pt)` / `ui_hints.options(pt)`, and
`make_my_figure_core.qa.publication_check`. Per-file `autouse` fixtures that call
`plt.close("all")` are common (see `tests/test_examples.py`).

## 4. Tests that enumerate every registered plot type

A new renderer enters these automatically the moment it is in
`make_my_figure_core/plots/registry.py::_RENDERERS`. Found with
`grep -nE 'available_plot_types\(' tests/*.py`:

| File | Test | What it demands of a new plot |
|---|---|---|
| `tests/test_examples.py` | `test_every_supported_plot_type_has_example` | a bundled example in `examples/` (via `scripts/generate_example_data.py`) |
| `tests/test_publication_style.py` | `test_publication_check_passes_for_all_examples[pt]` | the example render passes `qa/publication_check` (labels, font sizes, figure size) |
| `tests/test_desktop_controller.py` | `test_every_example_loads_and_renders` | loads and renders through the desktop controller (skips without PySide6) |
| `tests/test_desktop_gui.py` | `test_every_plot_type_loads_and_renders_in_gui` | same through the real GUI (Qt required) |
| `tests/test_app_smoke.py` | `test_app_runs_each_sample_plot_type` | Streamlit app path (skips without streamlit) |
| `tests/test_layout_and_annotations.py` | `test_all_axis_plots_honor_x_tick_rotation`, `test_all_plots_honor_y_tick_rotation` | shared layout controls take effect |
| `tests/test_layout_qc.py` | `test_layout_qc_never_crashes_on_any_plot_type` | layout QC scan |
| `tests/test_learned_styles.py` | `test_every_plot_type_renders_after_migration[name]` | renders under legacy profile names mapped to Publication |
| `tests/test_style_capabilities_audit.py` | `test_capabilities_agree_with_renderer_source_for_every_plot_type`, `test_every_registered_renderer_is_scanned` | the capability registry matches what the renderer source actually does |
| `tests/test_figure_presets.py` | `test_every_option_declares_a_valid_scope`, `test_style_preset_has_no_data_for_every_plot_type[pt]`, `test_full_preset_carries_roles_but_never_the_table[pt]`, `test_style_preset_applies_to_a_fresh_spec_and_renders[pt]` | every `ui_hints` Option declares `scope`; presets round-trip |
| `tests/test_figure_preset_qc.py` | `test_plot_type_passes_preset_qc[pt]` (+ a row-set equality test) | save -> apply -> export -> round-trip matrix written to `reports/figure_preset_qc/` |
| `tests/test_recommendations.py`, `tests/test_validate.py`, `tests/test_matrix_handoff.py` | use `available_plot_types()` as the known set | recommendation targets and PlotSpecs must name a registered type |

Hard-coded counts that must be bumped by hand when the registry grows
(`grep -rn '== 38' tests/`):

- `tests/test_renderers_m2.py:23` — `assert len(available_plot_types()) == 38`
- `tests/test_desktop_controller.py:29` — `assert len(controller.plot_types()) == 38`

(`tests/test_v04_plots.py:52` asserts the v0.4 subset is 18; leave it alone.)

## 5. Per-plot test families a new renderer needs

Modelled on `tests/test_histogram_distribution.py` (the v1.1.0 addition, 60+ tests)
and `tests/test_v1_1_renderer_options.py`. Give a new plot its own
`tests/test_<plot>.py` covering:

1. **Registration / wiring** — the pattern is
   `test_plot_type_is_wired_into_every_surface`: assert membership in
   `registry._RENDERERS`, `_DEFAULT_MAPPINGS`, `_DISPLAY_NAMES`,
   `available_plot_types()`, a human `display_name`, and the exact
   `ui_hints.column_fields(PLOT)` list and `{o.key for o in ui_hints.options(PLOT)}` set.
2. **Schema / PlotSpec validity** — `validate_plot_spec(spec, known_plot_types=available_plot_types())`
   accepts the example spec (`tests/test_validate.py` style). The JSON schema is
   permissive about `plot_type`; membership is what is checked.
3. **Column validation** — missing or wrongly typed required columns raise a clear
   error naming the column (`tests/test_renderers.py::test_missing_column_raises_clear_error`;
   histogram: `test_missing_wide_column_is_reported_by_name`).
4. **Render** — `test_bundled_example_renders`; numeric truth of what is drawn
   (`test_bar_heights_are_the_actual_counts`).
5. **Missing values** — NaN/empty groups are reported, not dropped silently
   (`test_group_with_no_finite_values_is_reported_not_dropped_silently`).
6. **Edge cases** — single value, no numeric data, inverted or clipping axis ranges
   refused (`test_a_single_distinct_value_still_draws`, `test_inverted_y_range_is_refused`).
7. **Input immutability** — `test_input_dataframe_is_not_mutated`
   (also generic: `tests/test_renderers.py::test_renderer_does_not_mutate_input`).
8. **Style controls** — tick rotation reaches every panel, opacity/size options
   honoured and invalid values refused, title weight follows the style token
   (`tests/test_v1_1_renderer_options.py::test_title_weight_follows_style_token`).
9. **Statistics** (if the plot carries a test) — pin against
   `tests/test_statistics_core.py` / `tests/test_stats_integration.py` patterns; the
   R-validated numbers live in `tests/test_r_validation_regressions.py`.
10. **PlotSpec round trip / reproducibility** — automatic binning or other derived
    parameters are recorded so the figure can be rebuilt
    (`test_automatic_binning_is_recorded_so_a_figure_can_be_reproduced`;
    `tests/test_reproducibility_export_qc.py`).
11. **Preset QC** — automatic via `tests/test_figure_preset_qc.py` once every Option has a
    `scope`; run `python -m pytest tests/test_figure_presets.py tests/test_figure_preset_qc.py -q`.
12. **Builder panel** — Figure Builder composition (`tests/test_multipanel.py`,
    `tests/test_imported_panels.py`); the controller-level render is covered by
    `tests/test_desktop_controller.py`.
13. **Export** — SVG/PNG/PDF via `tests/test_renderers.py::test_export_svg_png_pdf`
    when the plot is added to `conftest.PLOT_SAMPLES`; font survival through export in
    `tests/test_font_survives_export.py`.

Also add the plot to `conftest.PLOT_SAMPLES` with a `mock_data/` file so the generic
renderer/export tests run for it, and bump the two hard-coded counts in §4.

## 6. Guardrail and packaging tests worth knowing

- `tests/test_release_guardrails.py` — no rpy2/R runtime, no font files committed,
  Publication is the only visible style.
- `tests/test_style_leaks_and_version.py` — legacy journal names never surface;
  `build_info()` reports module path and commit.
- `tests/test_packaging.py` — `test_version_single_source`, PyInstaller spec sanity,
  CI matrix covers three OSes, icons exist, frozen resource resolution.
- `tests/test_package_data.py` — `setup.py::BUNDLED_DIRS`, `resources.BUNDLED_DIRS`,
  `MANIFEST.in` grafts and `pyproject` package-data all agree.
- `tests/test_r_validation_regressions.py` — the seven numerical fixes from the R
  benchmark (`benchmarks/r_validation/`).

## 7. How baselines are recorded

- The convention is a Markdown file `reports/<audit_name>/baseline_test_results.md`
  with sections **Environment** (OS, Python, key library versions, which optional
  deps were absent), **Command** (the exact pytest line), **Result** (`N passed, M
  skipped`), and **Skips** (one line per skip explaining why it is acceptable).
  The only instance today is `reports/fable5_release_audit/baseline_test_results.md`
  (`find reports -name 'baseline_test_results*.md'`).
- Release-level results go into `docs/releases/<tag>/release_<tag>_audit.md` §5 as a
  table of `Run | Command | Result` (see the v1.1.0 audit).
- Never edit an old baseline; add a new dated one.

## Verify this is still current

```bash
cd "<checkout>" && grep -n 'pytest' pyproject.toml                                  # pytest config still only testpaths
find tests -name 'test_*.py' | wc -l; grep -rhoE '^\s*def test_\w+' tests | wc -l   # module / function counts
grep -rn '== 38' tests/ ; MPLBACKEND=Agg python -c "from make_my_figure_core.plots.registry import available_plot_types as a; print(len(a()))"
grep -nE 'available_plot_types\(' tests/*.py | cut -d: -f1 | sort -u             # registry-enumerating files
```
