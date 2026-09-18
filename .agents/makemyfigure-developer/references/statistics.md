# Statistics: engine, StatsSpec, renderer integration, validation

Written 2026-09-17 against `main` (bb45c12). Numbers of tests/plots are not
quoted as facts; enumerate from code.

## 1. Where the code lives

| Path | Role |
|---|---|
| `make_my_figure_core/statistics/__init__.py` | Public surface: `run_statistics`, `StatResult`, `StatsReport`, `StatsError`, `TESTS`, `recommend_tests`, `adjust_pvalues`, `apply_correction`, `canonical_method`, `default_stats_spec`, `normalize_stats_spec`, `validate_stats_spec`, `stats_sidecar_payload`, `AnnotationItem`, `build_pairwise_annotations`, `stat_text_panel`, `method_reporting`, `glm_regression` |
| `statistics/schemas.py` | StatsSpec shape: `VALID_TESTS`, `VALID_MODES`, `ANNOTATION_CONTENTS`, `default_annotation`, `default_stats_spec`, `normalize_stats_spec`, `validate_stats_spec`, `stats_sidecar_payload` |
| `statistics/runner.py` | `run_statistics`, `resolve_columns`, `_dispatch`, `_run_pairwise_family`, `_run_within_x`, `_run_correlation` |
| `statistics/test_registry.py` | `TestInfo`, `TESTS` (id -> label, family, parametric, pairing/subject requirements, min/max groups), `recommend_tests` (advisory "auto") |
| `statistics/models.py` | `StatResult` (every field a figure or sidecar may show), `StatsReport`, `StatsError`; `to_dict`/`from_dict` |
| `statistics/pairwise.py`, `anova.py`, `nonparametric.py`, `categorical.py`, `survival.py`, `regression.py` | Test implementations (scipy/statsmodels/lifelines-style code paths) |
| `statistics/effect_sizes.py` | Cohen's d, Hedges' g, Cohen's dz, Cliff's delta, rank-biserial, eta/omega squared, epsilon squared, Cramer's V |
| `statistics/multiple_testing.py` | `canonical_method`, `adjust_pvalues`, `apply_correction`: `none`, `bonferroni`, `holm`, `benjamini_hochberg` (aliases `bh`, `fdr`, `fdr_bh`) |
| `statistics/method_reporting.py` | `stars_for_p`, `format_p`, `method_sentence`, `methods_paragraph`, `legend_sentence`, `annotation_tokens`, `render_annotation` |
| `statistics/annotations.py` | `AnnotationItem`, `build_pairwise_annotations`, `stat_text_panel` |
| `statistics/validators.py` | `two_group_arrays`, `paired_arrays`, `multi_group_arrays`, `group_levels` (design checks that raise `StatsError`) |
| `statistics/_versions.py` | `software_versions()` recorded on every result |
| `plots/stats_integration.py` | `run_and_annotate`: the single bridge renderers call |
| `plots/stats_overlay.py` | Bracket/above-bar/corner drawing (geometry only) |
| `scripts/statistics_oracle.py`, `tests/test_statistics_oracle_validation.py` | Independent scipy/statsmodels oracle |
| `benchmarks/r_validation/` | Independent R validation (R scripts, Python exporters, reports, `FINAL_VALIDATION_MATRIX.csv`); `tests/test_r_validation_regressions.py` pins fixes |
| `docs/STATISTICS.md`, `docs/STATISTICAL_ANNOTATIONS.md`, `docs/STATISTICAL_ANNOTATION_FORMATTING.md`, `docs/FEATURE_LEVEL_STATISTICS.md` | Documentation |

## 2. Guiding rules (enforced by tests)

- Never fabricate a p-value: a figure may only show text derived from a stored
  `StatResult` (`tests/test_stats_annotations.py::test_annotation_backed_by_stored_result`,
  `tests/test_above_bar_annotation.py::test_every_label_is_reproducible_from_its_stored_result`).
- Renderers never compute tests or format p-values themselves. They compute
  geometry (positions, tops) and call `run_and_annotate`. Volcano/MA plots use
  p-values supplied in the input and never recompute them
  (`test_volcano_does_not_invent_pvalues`). The one descriptive exception on
  main is `plots/scatter.py::_fit_line`, which draws an OLS line via
  `scipy.stats.linregress` and an optional fit-stats box (`show_fit_stats`
  options); it is a plot option, not a StatsSpec result, and is not in the
  sidecar. Do not copy that pattern for a new plot: route through the engine.
- Test selection is advisory: `test: "auto"` calls `recommend_tests` and takes
  `primary`; the result records the exact test used. Invalid designs produce a
  warning or `StatsError`, not a questionable number.
- Family-wide correction applies only to `comparison_type == "two_group"`
  results; omnibus/correlation/survival/categorical results get
  `correction_method="none"` and are judged at alpha directly.

## 3. StatsSpec (the `statistics` block of a PlotSpec)

`default_stats_spec()` keys: `enabled` (False), `test` ("auto"),
`comparison_mode` ("auto"), `correction` ("benjamini_hochberg"), `alpha` 0.05,
`alternative` "two-sided", `posthoc` False, `posthoc_test` "welch_t", column
overrides (`value_column`, `group_column`, `subgroup_column`, `subject_column`,
`time_column`, `event_column`, `x_column`, `y_column`, `row_column`,
`col_column`), `reference_group`, `selected_pairs`, `annotate` True,
`annotation` (see annotations.md for the full display block).

`VALID_TESTS`: auto, students_t, welch_t, mann_whitney, paired_t, wilcoxon,
one_way_anova, two_way_anova, rm_anova, kruskal_wallis, chi_square,
fishers_exact, logrank, cox_ph, pearson, spearman, linear_regression.
`glm` is in `TESTS` and handled by `run_statistics` but is not in `VALID_TESTS`,
so `normalize_stats_spec` resets it to auto when it arrives via a PlotSpec; the
GLM path is reached by callers passing an un-normalised spec (matrix workflow /
`docs/FEATURE_LEVEL_STATISTICS.md`).

`VALID_MODES`: auto, all_pairs, vs_control, selected_pairs, within_x, omnibus.

`normalize_stats_spec` fills defaults, coerces unknown enum values back to
defaults, canonicalises the correction name, mirrors legacy `annotation.mode`
into `annotation.content`, and preserves unknown keys. `validate_stats_spec`
returns a list of messages. Column defaults come from the plot mapping through
`runner.resolve_columns` (value = mapping `y`; group = `x` or `group`; grouped
bar uses `x` as group and `group` as subgroup; KM uses `group`; scatter uses
`color` as subgroup; stacked/oncoprint use `x`/`sample` and `stack`/`row` as
contingency rows/columns).

## 4. Comparison shapes supported by the runner

| Shape | Trigger | Result records |
|---|---|---|
| Two groups, one comparison | two_group test, 2 levels | one `two_group` result |
| All pairs | `all_pairs` (or auto without reference) | k choose 2 `two_group` results, corrected as a family |
| Versus control | `vs_control` + `reference_group` (auto uses it when set) | k-1 results |
| Selected pairs | `selected_pairs=[[a,b],...]` | listed pairs only |
| Hue within x (grouped bar) | subgroup column present and mode auto/within_x/omnibus | per x level, pairs of subgroups; `extra={"x_level", "within_x": True}`, `block_column=x` |
| Paired | `paired_t` / `wilcoxon` with `subject_column` | pairing validated by `validators.paired_arrays` |
| Omnibus | `one_way_anova` / `kruskal_wallis` (>= 3 groups); `posthoc=True` adds pairwise (`posthoc_test`) or Dunn | omnibus + optional two_group family |
| Two-way / repeated measures | `two_way_anova` (value + two factors), `rm_anova` (value + within factor + subject) | omnibus per term |
| Correlation / regression | `pearson`, `spearman`, `linear_regression`; per subgroup when a colour column is set | `correlation`/`regression` results |
| Survival | `logrank` (one result), `cox_ph` (one per level vs reference) | `survival` results |
| Categorical | `chi_square`, `fishers_exact` on a contingency of row x col columns | `categorical` result; r x c Fisher is a seeded Monte Carlo approximation and says so |

Not supported on main: dose-response curve comparisons, ROC/PR curve
comparisons (DeLong etc.), Bland-Altman limits as a StatsSpec test, trend tests
on time courses, mixed models. `recommend_tests` returns no primary for plot
types outside bar/box/grouped-bar, scatter, KM, stacked/oncoprint; volcano and
lollipop only get notes.

## 5. The result objects and sidecar

`StatResult` fields include `test_id`, `test_name`, `comparison_type`
(two_group | omnibus | correlation | regression | survival | categorical),
`grouping_columns`, `value_column`, `group_a`/`group_b`, `paired_id_column`,
`block_column`, `n_total`, `n_by_group`, `statistic`, `statistic_name`, `df`,
`df2`, `p_value`, `adjusted_p_value`, `correction_method`, `reject_null`,
`alpha`, `effect_size_name`, `effect_size`, effect CI, estimate CI
(`confidence_interval_low/high`, `ci_level`, `estimate`, `estimate_name`),
`alternative`, `paired`, `assumptions_checked`, `warnings`,
`missing_data_policy`, `method_sentence`, `extra`, `reproducibility`,
`software_versions`. `display_p` returns the adjusted p when present.
`to_dict` cleans NaN/inf to None and numpy scalars to Python.

`StatsReport`: `results`, `correction_method`, `method_paragraph`,
`legend_sentence`, `warnings`, `config` (the spec; `run_and_annotate` adds
`_annotation_info`), `software_versions`; `to_dict`/`from_dict`.

Sidecars: `registry.write_stats_sidecar` writes `<base>.stats_spec.json` from
`schemas.stats_sidecar_payload(stats_spec, report)` = normalised spec, results,
method paragraph, legend sentence, correction, warnings, software versions,
disclaimer. `export_bundle_bytes` includes it in the ZIP. The renderer's
metadata also carries `statistics_report` and the registry attaches
`RenderResult.stats_report`.

## 6. How a renderer opts in (`plots/stats_integration.run_and_annotate`)

Signature: `run_and_annotate(spec, df, style, plot_type, *, ax=None, positions=None,
tops=None, mode="bracket", corner_loc="upper left") -> StatsReport | None`.

- Returns None when `statistics.enabled` is false. Otherwise runs
  `run_statistics(df, stats_spec, plot_type=..., mapping=spec["mapping"])`.
- `mode="bracket"`: pass `positions` `{str(category): x}` and `tops`
  `{str(category): y_top}` (bars: mean + error; boxes: max). For hue-within-x,
  key both by `(str(x_level), str(group))`. Draws brackets
  (`stats_overlay.annotate_pairwise`) or, with `annotation.placement="above_bar"`,
  one label per compared bar (`annotate_above`, falling back to brackets for
  pairs without the shared reference). Non-two-group results (ANOVA, KW) are
  added as a corner text panel with headroom reserved.
- `mode="corner"`: `stat_text_panel` lines at `corner_loc` (scatter uses
  upper left; stacked uses upper right).
- `mode="survival"`: text panel at `annotation.location` (default lower left).
- Renderers must call it after `tight_layout` / legend placement so label
  widths are measured against final axes geometry (see comments in
  `plots/barplot.py`, `plots/grouped_barplot.py`), then put the report on
  `RenderResult(stats_report=...)` and `meta["statistics_report"]`.

Current callers on main: barplot, box_violin, grouped_barplot (bracket), scatter,
stacked (corner), survival (survival; refuses with a warning for precomputed
curves). To add a plot type: (1) add it to `recommend_tests` if `auto` should
work, (2) add a `resolve_columns` branch if the mapping names differ from
`x`/`y`/`group`, (3) compute positions/tops and call `run_and_annotate`,
(4) add a test in the style of `tests/test_stats_integration.py` and
`tests/test_stats_annotations.py`.

## 7. Validation against independent implementations

- `scripts/statistics_oracle.py::run_oracle` recomputes every implemented test
  with scipy/statsmodels directly (not the app path) on fixed seeded data and
  compares statistic, df, p, effect size, CI and adjusted p with tight
  tolerances; `tests/test_statistics_oracle_validation.py` parametrises over
  its rows and requires full coverage. Running the script writes
  `outputs/publication_qc/statistics_oracle_results.md`.
- `benchmarks/r_validation/`: R scripts `R/00_setup.R` ... `16_plot_derived.R`
  (base R, survival, car, rstatix, effectsize, dunn.test, limma, edgeR,
  DESeq2), `python/export_make_my_figure_reference.py` and `compare_outputs.py`,
  inventories (`statistical_inventory.csv`, `transformation_inventory.csv`,
  `recommendation_inventory.csv`), `reports/VALIDATION_REPORT.md`,
  `DISCREPANCY_REPORT.md`, `RECOMMENDATION_AUDIT.md`, and
  `FINAL_VALIDATION_MATRIX.csv` (component rows with EXACT / NUMERICALLY_EQUIVALENT
  / ACCEPTABLE_IMPLEMENTATION_DIFFERENCE counts). Class A = exact method
  equivalence; Class B = scientific concordance for by-design different models
  (per-gene Welch vs limma-voom/edgeR/DESeq2). R is a reference only; the app
  has no R dependency. Re-run instructions are in its README. Fixes found by it
  are pinned in `tests/test_r_validation_regressions.py` (seeded r x c Fisher,
  quantile-normalisation ties, voom definition, ROC tie order, Mann-Whitney
  effect sign, near-tie ranks).

## 8. Gaps to know about

- No StatsSpec JSON schema file; validation is `validate_stats_spec`.
- `glm` is reachable only outside PlotSpec normalisation.
- Proportional-hazards assumption is not checked for `cox_ph` (noted in
  `recommend_tests`).
- Effect-size CIs exist only where the implementation sets `effect_ci_*`.
- Renderers other than the six callers above ignore `statistics.enabled`
  silently; the engine will not warn for them unless the renderer calls in.

## Verify this is still current

```bash
cd "<repo>" && grep -n "^VALID_TESTS\|^VALID_MODES\|^ANNOTATION_CONTENTS" -A4 make_my_figure_core/statistics/schemas.py
grep -rn "run_and_annotate(" make_my_figure_core/plots/*.py | grep -v stats_integration.py   # which renderers opt in
python -c "from make_my_figure_core.statistics import TESTS; print(sorted(TESTS))"
MPLBACKEND=Agg python -m pytest tests/test_statistics_oracle_validation.py tests/test_stats_integration.py tests/test_r_validation_regressions.py -q
```

## Adding a NEW statistical test (not just a new plot)

A reference figure may show a test the engine lacks (e.g. a two-sample Kolmogorov-Smirnov test).
That is a statistics-engine change, larger than the renderer, and touches every one of these
(verify names with `grep -n` before editing; they are the authoritative locations on main):
`statistics/pairwise.py` (or the family module) for the implementation; `statistics/test_registry.py`
`TESTS` entry (family, parametric flag, group-count range) and `recommend_tests`;
`statistics/schemas.py` `VALID_TESTS`; `statistics/runner.py` dispatch (`TWO_GROUP` and the
`_run_*` branch); `statistics/method_reporting.py` wording if any; `scripts/statistics_oracle.py`
plus `tests/test_statistics_oracle_validation.py` (it requires every TESTS entry to be covered);
`benchmarks/r_validation/` inventory so the R cross-check can include it. Ask the author whether
the test is wanted in the same change or as a follow-up; ship the plot with the existing tests
(e.g. Mann-Whitney / Kruskal-Wallis) if the answer is "later".

## The "survival" text-panel mode is generic

`run_and_annotate(..., mode="survival")` draws a positionable text panel at
`statistics.annotation.location`; nothing in it is survival-specific. Any plot whose x axis is
numeric (no category positions for brackets) can use it, as can `mode="corner"` for the fixed
corner panel. Treat the mode name as historical.
