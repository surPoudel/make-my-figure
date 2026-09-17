# matplotlib version compatibility check (2026-09-17)

## Trigger

Manual acceptance step D1 on a MacBook (desktop app, bundled "Box / violin plot with points" example)
failed before any figure was shown:

```
Unexpected error: boxplot() got an unexpected keyword argument 'orientation'
```

`Axes.boxplot` and `Axes.violinplot` accept `orientation=` only from matplotlib 3.10 (October 2024);
older releases use the boolean `vert=`. The rewritten box/violin renderer on this branch passed
`orientation=` unconditionally, while the package declares `matplotlib>=3.6`. Every other renderer,
the observations engine, the bar renderer and the bracket engine use the word `orientation` only for
their own arguments, not for matplotlib calls (checked in the branch diff against 193f637).

## Fix (matplotlib < 3.10)

`make_my_figure_core/plots/box_violin.py`: `_orientation_kwargs(method, orientation)` inspects the
installed signature once per call and returns `{"orientation": ...}` on matplotlib >= 3.10 or
`{"vert": bool}` on older releases. No deprecation warning is emitted on either.

Tests (`tests/test_box_violin_publication_options.py`): the helper's two branches, and 16 renders
(4 kinds x 2 orientations x unequal-n / 2x3 hue designs, statistics on) under a simulated legacy
`Axes.boxplot`/`Axes.violinplot` that reject `orientation=`; the drawn geometry (axis limits, box and
violin patches, whisker/median/bracket lines, every observation marker) must be identical to the
native path. On a real legacy matplotlib the simulation is skipped and the same equality check runs.

## Whole-library check on two matplotlib versions

`scripts/render_fingerprint_all_plots.py` renders every plot type under Publication defaults and every
experimental preset (38 x 13 = 494 renders) plus the 17 group-comparison test designs under every
box/violin kind x orientation x point arrangement (24) and bar summary/error x orientation (8)
combination (17 x 32 = 544 renders), and writes a geometry fingerprint per render: figure size, axis
limits, hashes of every line / patch / collection, every text string with its position, tick labels
and axis labels.

| environment | matplotlib | numpy | pandas | scipy | statsmodels | adjustText |
|---|---|---|---|---|---|---|
| development (WSL2, Python 3.11) | 3.10.8 | 2.1.2 | 2.2.3 | 1.17.1 | 0.14.6 | 1.3.0 |
| legacy venv (`/tmp/mpl38`, Python 3.11) | 3.8.4 | 2.0.2 | 2.3.3 | 1.17.1 | 0.15.0 | 1.4.0 |
| newest venv (`/tmp/mplnew`, Python 3.11; what a fresh `pip install` gives today) | 3.11.2 | 2.4.6 | 3.0.5 | 1.17.1 | 0.15.0 | 1.4.0 |

Result (`matplotlib_compat_compare_raw.txt`):

| renders | failed (either version) | data artists / limits / tick labels / label text differ | label position only |
|---|---|---|---|
| 1038 | 0 | 0 | 30 |

The 30 position-only differences are the repelled gene labels of `volcano_plot` (10 presets),
`lollipop_mutation_plot` (10) and `network_graph` (10): adjustText nudges labels using text extents,
which differ slightly between matplotlib font-metric versions. Label strings are identical, the
largest shift is 2.6 % of the axis range, and no data artist moved. All 544 group-comparison renders
(including every statistics bracket and P-value text, which depend on scipy/statsmodels) are identical
across the two environments.

Before the fix, the 3.8.4 environment failed every `boxplot_or_violin_with_points` render
(13 preset cells and 408 group-comparison cells) with the error above.

## Newest releases (matplotlib 3.11.2, numpy 2.4.6, pandas 3.0.5)

Result (`matplotlib_compat_compare_newest_raw.txt`, compared with the development environment):

| renders | failed | data artists differ | tick-label text differs | bracket data-unit drift | label position only |
|---|---|---|---|---|---|
| 1038 | 0 | 0 | 16 | 276 | 279 |

* **Data artists** (bars, boxes, violins, error bars, every observation marker, curves, heatmap cells,
  network nodes/edges) are identical in all 1038 renders.
* **Tick-label text** (16 renders: `dose_response_curve` log ticks under every preset, one `barplot`,
  `heatmap_clustered_matrix`, `ridge_or_density_plot` case): matplotlib 3.11 changed its automatic
  tick locator/formatter choices (e.g. `0, 1, 2, 3` vs `0.0, 0.5, ...`). Axis limits and data are the
  same; this is matplotlib's default tick selection, which the package does not override.
* **Bracket drift** (276 group-comparison renders with statistics on): the significance bracket is
  specified in points above the highest drawn point/error bar. Measured on both versions the bracket is
  physically identical (tick 3.8 pt, gap above the data 6.8 pt), but matplotlib 3.11 places the axes
  box slightly differently (e.g. left edge 0.1597 vs 0.1567 of the figure width) because tick-label
  extents changed, so the same physical offset corresponds to a marginally different data value
  (largest difference 0.9 % of the axis range) and the auto-expanded axis limit follows. Stars and P
  values are the same strings.
* **Label position only** (279): adjustText 1.4.0 vs 1.3.0 nudges repelled gene labels differently
  and draws a different number of empty connector annotations (volcano, lollipop, network); label
  strings are the same multiset in every render. The 3.8.4 environment also had adjustText 1.4.0, so
  its 30 label-position differences have the same origin.

### Full test suite on the newest environment - two further compatibility defects found and fixed

The first full run (2260 passed, 38 failed) exposed two defects that the render fingerprint could
not see, plus one environment gap:

| failing tests | cause | fix |
|---|---|---|
| 18 x `test_figure_preset_qc.py::test_plot_type_passes_preset_qc` | `scripts/build_figure_preset_qc.py::_perturb` wrote into the array returned by `Series.to_numpy()`; pandas 3 (copy-on-write) returns a read-only view -> `ValueError: assignment destination is read-only`. Only the QC script's synthetic "different dataset" step; no renderer or statistics code writes into `to_numpy()` results (AST scan of `make_my_figure_core/`, `apps/`, `scripts/`). | copy before writing |
| 19 x figure-package round trips (`test_figure_package.py`, `_controller.py`, `_integrity.py`) | pandas 3 infers the new default `str` dtype for text columns; `package/tabledata.py` recognised only `string`/`string[python]`/`string[pyarrow]` and stored `str` columns as `object`, so the reopened table failed the exact identity check (`dtype str != object`). Values were never altered. | `str` is encoded as kind `string` with its dtype name; decoding a `str` column on a pandas without that dtype (2.x) yields `object`, which is what that pandas would infer itself. New test `test_string_columns_round_trip_under_every_pandas_string_dtype`, run on pandas 2.2.3, 2.3.3 and 3.0.5. |
| 1 x `test_publication_recreation_pipeline.py::test_curation_is_deterministic` | `scikit-learn` was not installed in the throwaway venv (optional dependency of the benchmark pipeline). | installed; passes |

After the fixes the previously failing modules pass on all three environments (newest: 94 passed;
3.8.4: 46 passed). One 3.10.8 rerun of those modules reported a single failure
(`test_single_plot_round_trip[volcano_plot]`) while other test processes were running in the same
checkout; the same module run alone passed (20 passed) and the test passes in isolation, so it is
recorded here as a collision between concurrent runs, not a defect. The final suites below were run
one at a time. Running the suite also rewrites the byte counts in
`benchmarks/publication_recreation/recreated_panels/karate_network/qc/visual_qc.md`; that file was
restored and is not part of this change.
Full non-GUI suite on the newest environment after the fixes: **2299 passed, 13 skipped, 0 failed** (`matplotlib_compat_full_suite_newest.txt`). The development-stack (3.10.8) full suite rerun is recorded in `matplotlib_compat_full_suite_mpl310.txt` when it completes.

## Test suites on matplotlib 3.8.4

* `tests/test_box_violin_publication_options.py`: 96 passed.
* `tests/test_bar_observations_publication_options.py`, `tests/test_stats_brackets_geometry.py`: passed
  together with the above (152 total in the targeted run).
* Full non-GUI suite (2026-09-17, after the fix): **2281 passed, 13 skipped, 0 failed** (65 GUI/Streamlit tests
  deselected, `tests/test_release_guardrails.py` deselected because it checks the release tag state):
  `matplotlib_compat_full_suite_mpl38.txt`.

## What the tester should check on the MacBook

```
python -c "import matplotlib; print(matplotlib.__version__)"
```

Any version from 3.6 upward now works for the box/violin renderer. After pulling this branch, repeat
D1-D14 of `MANUAL_PRESET_ACCEPTANCE.md`; the exported figure must match the Windows/WSL render except
for the adjustText label nudges named above.
