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
Full non-GUI suite on the newest environment after the fixes: **2299 passed, 13 skipped, 0 failed** (`matplotlib_compat_full_suite_newest.txt`). Development stack (3.10.8) full suite after the fixes: **2306 passed, 5 skipped, 0 failed** (`matplotlib_compat_full_suite_mpl310.txt`).

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

## Re-check on 2026-09-22 after merging `main` (v1.1.1 candidate, 39 plot types)

`origin/main` at 84458dd (figure packages, the Circos-style chord diagram, the pandas 3 fixes already on
this branch, version 1.1.1) was merged into this branch (c5bb8b0; the only conflict was the header of
`reports/figure_preset_qc/README.md`, resolved to main's 39-renderer version). The whole-library
fingerprint was then re-run in three fresh environments: development (matplotlib 3.10.8 / numpy 2.1.2 /
pandas 2.2.3), legacy (`/tmp/mpl38`: 3.8.4 / 2.0.2 / 2.2.3) and newest (`/tmp/mplnew`: 3.11.2 / 2.4.6 /
pandas 3.0.6). 1051 renders per environment (1038 + the 13 chord-diagram cells), 0 failed everywhere.

### New defect found: pandas-version-dependent sample order (stacked composition bars)

Compared with the development stack, the newest stack drew `stacked_bar_composition` with a different
sample order in all 13 renders (development: S01, S14, S13, S12, ...; pandas 3: S01, S02, S03, ...).
Cause: `plots/stacked.py` ordered samples by the grouping column with `Series.sort_values()`, whose
default kind is quicksort, which is not stable. Rows that tie on the key (every sample in the same group)
come out in an arbitrary order that depends on the dtype path - pandas 2 `object` columns and pandas 3
default `str` columns sort ties differently. The bars' values were identical; only their order changed.
The same latent tie-order dependence existed in 19 further `sort_values` calls across the renderers
(oncoprint gene frequency, lollipop position and top-n label selection, volcano / MA label ranking,
enrichment top-n, network top-n edges, waterfall, calibration, precision-recall, Manhattan, spider).

Fix: every `sort_values` in `make_my_figure_core/plots/` now passes `kind="stable"`, so ties keep the
input order on every pandas version. `tests/test_renderer_sort_stability.py` scans the renderers for
unstable sorts and renders a stacked composition with scrambled input under both `object` and `string`
dtypes (passes on all three environments). On the development stack the fix changes 39 renders:
`stacked_bar_composition` (sample order within a group now follows the table), `oncoprint_mutation_heatmap`
(two genes with the same frequency, PTEN and BRAF in the bundled example, now keep table order) and
`lollipop_mutation_plot` (draw order of lollipops at tied positions and tie-breaking of the top-n labels).
All are orders that were previously arbitrary; no value, count or statistic changed.

### Fingerprint results after the fix

| comparison | renders | failed | data / limits / tick-label text differ | label position only |
|---|---|---|---|---|
| 3.8.4 vs 3.10.8 (`matplotlib_compat_compare_raw_2026-09-22.txt`) | 1051 | 0 | **0** | 18 (adjustText: lollipop, network, volcano) |
| 3.10.8 vs 3.11.2 + pandas 3.0.6 (`matplotlib_compat_compare_newest_raw_2026-09-22.txt`) | 1051 | 0 | 292 | 279 |

The 292 newest-stack differences are exactly the set documented above on 2026-09-17: 16 renders whose
automatic tick labels matplotlib 3.11 chooses differently (`dose_response_curve` log ticks under every
preset, one bar plot, one clustered heatmap, one ridge plot) and the 276 group-comparison renders whose
points-based significance bracket lands on a marginally different data value because matplotlib 3.11
places the axes box slightly differently. No data artist differs in any of the 1051 renders, and the
chord diagram is identical on all three stacks. Before the fix the same comparison had 305 differences
(the 13 stacked-bar renders on top of these 292).

### Experimental preset QC on 39 plot types

`scripts/experimental_preset_qc.py` re-run on the merged tree (`qc/qc_matrix.csv`, `qc/README.md`,
previews regenerated): 12 presets x 39 plot types = 468 cells, **293 PASS, 69 WARN, 106 FAIL**
(2026-09-16: 456 cells, 289 / 69 / 98). The chord diagram PASSes under Single column 57 mm (S),
Single column 89 mm (N) and Full width 183 mm (N) and FAILs under the other nine with one to three
overlapping label pairs (segment labels around the ring at the larger preset text sizes) - reported and
left out of `recommended_for`, never fixed by shrinking text, like the volcano and MA gene labels.
`recommended_for` and the `experimental.qc` block of every preset were refreshed from the matrix
(`journal_preset_research/tools/apply_qc_to_presets.py`): 24 / 23 / 22 / 22 / 23 / 16 plot types for
the 89 mm (N) / 85 mm (C) / 174 mm (C) / 184 mm (S) / 183 mm (N) / 57 mm (S) presets; each gc preset
still PASSes on its own plot type.

Two cells depend on adjustText's label placement and flipped between otherwise identical runs
(`gc_box_points_light` x `lollipop_mutation_plot` and `gc_bar_points_jittered` x `network_graph`,
FAIL in the first run, PASS in the second and in five isolated re-runs). Their status in the committed
matrix is the second run's; they should be read as borderline.

### Test suites after the merge and the fix

Run one after the other's start on 2026-09-22 (concurrent processes, disjoint output paths), all after the
merge and the stable-sort fix:

| environment | command | result | log |
|---|---|---|---|
| development: matplotlib 3.10.8 / numpy 2.1.2 / pandas 2.2.3 | full headless suite (`-p no:pytest-qt --ignore=tests/test_desktop_gui.py`) | **2449 passed, 4 skipped, 0 failed** | `matplotlib_compat_full_suite_mpl310_2026-09-22.txt` |
| legacy: matplotlib 3.8.4 / numpy 2.0.2 / pandas 2.2.3 | non-GUI suite (`-k "not qt and not Qt and not streamlit and not desktop" --deselect tests/test_release_guardrails.py`) | **2371 passed, 9 skipped, 73 deselected, 0 failed** | `matplotlib_compat_full_suite_mpl38_2026-09-22.txt` |
| newest: matplotlib 3.11.2 / numpy 2.4.6 / pandas 3.0.6 | same non-GUI suite | **2371 passed, 9 skipped, 73 deselected, 0 failed** | `matplotlib_compat_full_suite_newest_2026-09-22.txt` |

The merged tree before the stable-sort fix also passed the development-stack suite (2446 passed, 4
skipped); the three additional tests are `tests/test_renderer_sort_stability.py`. The 73 deselected
tests in the throwaway environments are the Qt / Streamlit / desktop-controller tests (PySide6 and
Streamlit are not installed there) and the release-guardrail test, which checks the release tag state.
