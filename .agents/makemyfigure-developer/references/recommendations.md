# Figure recommendations (data-shape → advisory plot suggestions)

Documented from the code on branch `feature/makemyfigure-developer-agent` (forked from
`main` on 2026-09-17, version `1.1.0` in `make_my_figure_core/version.py`). Paths are
relative to the repository root.

There are **two separate recommendation engines**. Do not confuse them:

| Engine | Package | Input | Used by |
|---|---|---|---|
| Table recommender | `make_my_figure_core/recommendations/` | any freshly loaded table (`DataFrame`) | desktop "Recommended figures" panel, Streamlit "Recommended figures" expander |
| Matrix-workflow recommender | `make_my_figure_core/matrix_workflow/recommendations.py` (+ `transform_recommendations.py` for preprocessing) | a confirmed `MatrixSpec` (+ optional `SampleMetadataSpec`, differential summary) | desktop `matrix_wizard.py` step ⑤, Streamlit `matrix_wizard.py` step 4 |

This file is mostly about the first. The second is summarised at the end.

## 1. Pipeline of the table recommender

Entry points live in `make_my_figure_core/recommendations/recommendation_runner.py`:

- `recommend_for_table(df, table_name="data") -> RecommendationSpec` — run on upload.
- `recommend_after_analysis(df, *, stats_report=None, differential=False, has_matrix=False, table_name=...)` — follow-up suggestions after statistics ran or a differential table exists; falls back to `recommend_for_table` when nothing matched, and returns `schema="post_analysis"` otherwise.

`recommend_for_table` does, in order:

1. `data_profiler.profile_table(df, table_name)` → `DataProfile`
2. `schema_detector.detect_schema(profile, df)` → one schema string
3. `plot_recommender.recommend_plots(profile, schema, df, table_name)` → direct recs
4. `transform_recommender.recommend_transforms(...)` → reshape-then-plot recs
5. `transform_recommender.recommend_guidance(...)` → informational recs
6. Adds notes (e.g. the "Make My Figure does not run differential-expression analysis" note, `_DE_NOTE`) and wraps everything in a `RecommendationSpec`.

The public surface is re-exported from `make_my_figure_core/recommendations/__init__.py`
(`profile_table`, `detect_schema`, `SCHEMAS`, `recommend_plots`, `recommend_for_table`,
`recommend_after_analysis`, `suggest_stats`, and the dataclasses).

### 1.1 Data models (`recommendation_models.py`)

- `ColumnRole(role, column, confidence, reason)` — one detected semantic role.
- `DataProfile` — column kinds (`numeric`/`categorical`/`datetime`/`id`/`binary`), missingness, duplicate id columns, `roles`, and matrix flags: `is_matrix`, `matrix_kind` (`"count_like"` | `"expression_like"`), `matrix_feature_col`, `matrix_sample_columns`, `is_correlation_matrix`, `is_adjacency_matrix`. Helpers: `role_column(role)`, `has_role(role)`, `to_dict()`.
- `Recommendation` — `id`, `plot_type`, `display_name`, `confidence` (0–1 float), `why`, `required_mappings`, `missing_mappings`, `suggested_statistics`, `suggested_style` (always `"publication"`), `suggested_thresholds`, `estimated_cost` (`low|medium|high`), `requires_confirmation`, `warnings`, `plot_spec_draft`, and the v0.6.1 fields `kind` (`"direct"` | `"transform"` | `"guidance"`), `transform`, `instructions`. Property `is_renderable` is true only for `kind == "direct"` with a draft whose `plot_type` is in `registry.available_plot_types()`.
- `RecommendationSpec(table_name, schema, profile_summary, recommendations, notes)` with `.top`.

Everything is JSON-serialisable via `to_dict()` so a recommendation set can ride along with a session or report.

### 1.2 Profiling (`data_profiler.py`)

`profile_table` is pure pandas/numpy, "safe to run on upload". Key mechanics:

- Header aliases are in the module-level `_ALIASES` dict (roles: `group`, `subject`, `survival_time`, `survival_event`, `p_value`, `adj_p`, `logfc`, `ave_expr`, `chromosome`, `position`, `dose`, `response`, `source`, `target`, `mutation_gene`, `mutation_type`, `enrichment_term`, `enrichment_count`, `enrichment_ratio`, `estimate_lower`, `estimate_upper`, `label`, `score`). Matching uses `_find(columns, aliases)` on normalised names (`de_detect._norm`), exact first, then prefix/suffix substring fallback.
- `_column_kind(series, name)` decides numeric / binary / datetime / id / categorical; `_ID_HINTS` marks id-like names.
- Group fallback: if no alias matches, any non-id categorical with 2–20 levels (fewest levels wins) becomes `group`, provided a numeric column exists. This is what `tests/test_recommendations.py::test_unnamed_categorical_group_is_recommended` protects (`species` + `flipper_length_mm`).
- Matrix characterisation: `is_matrix` when ≥3 numeric columns, numerics are ≥50 % of columns, and a non-numeric feature column exists; `_classify_matrix` labels the block `count_like` (≥98 % non-negative, ≥95 % integral, max > 30) else `expression_like`.
- Correlation matrix: square, symmetric, unit diagonal, |values| ≤ 1. Adjacency: symmetric 0/1.

### 1.3 Schema detection (`schema_detector.py`)

`SCHEMAS` is the fixed vocabulary; `detect_schema` is priority-ordered (most specific first):

`precomputed_differential` → `survival` → `gwas` → `classification` → `dose_response` →
`network_edge_list` → `enrichment` → `mutation_matrix` → `correlation_matrix` →
`expression_like_matrix` / `numeric_matrix` → `paired` → `generic_long` → `unknown`.

- `generic_long` means: a `group` role plus at least one numeric column. It is the schema for the ordinary "one categorical + one value" table and yields box/violin, ridge, bar, grouped bar and scatter recs.
- `paired` needs `subject` + a 2-level `group` where most subjects appear under ≥2 levels.
- `matrix_plus_metadata` is in `SCHEMAS` and handled by `recommend_plots`, but **`detect_schema` never returns it** on this commit; it is only reachable if a caller passes it explicitly.

### 1.4 Rule structure and match scores (`plot_recommender.py`)

`recommend_plots` is one function with an inner `add(plot_type, conf, why, col_map, *, stats, thresholds, missing, warnings, cost, confirm, renderable)` helper and one `if/elif` branch per schema. Each `add` call:

- builds a mapping with `_mapping(plot_type, col_overrides)` — starts from `registry.default_mapping` and sets/removes only the keys listed in `ui_hints.COLUMN_FIELDS[plot_type]`;
- builds a one-click draft with `_draft` → `registry.make_spec(plot_type, table_name, "publication", mapping=..., statistics=...)`;
- optionally attaches `suggest_stats(plot_type, mapping, df)` (thin wrapper over `statistics.recommend_tests`, never raises — `stat_recommender.py`).

**Confidence values are hand-assigned constants per rule**, not computed. They are what the UIs display as "N % match" (Streamlit multiplies by 100). Examples as of this commit: volcano 0.92 (precomputed differential), KM 0.88, heatmap 0.85 (matrix), ROC 0.85, GWAS Manhattan 0.82 + Q-Q 0.70, dose-response 0.82, network 0.80, enrichment 0.80, oncoprint 0.78, paired slopegraph 0.75, generic-long box/violin 0.72 → ridge 0.62 → bar 0.60 → grouped bar 0.55 → scatter 0.50. Fallback scatter when nothing matched: 0.40. Recs are sorted by confidence descending.

Cost/confirmation: for matrix schemas `cells = n_rows × n_sample_columns`; above `_LARGE_CELLS = 40_000` the heatmap and PCA recs become `cost="high", requires_confirmation=True` (test: `test_large_matrix_requires_confirmation`). The PCA rec has its `plot_spec_draft` cleared because PCA needs an aux metadata table.

`_numeric_values(profile)` excludes columns already claimed by special roles (p, FDR, logFC, position, CI bounds, …) so the "value" column for box/bar is a genuine measurement.

### 1.5 Transform-aware and guidance recs (`transform_recommender.py`)

- `recommend_transforms` adds `kind="transform"` recs whose `transform` dict is `{name, params, result_columns, output_filename}` with `name` ∈ `wide_to_long` | `correlation_matrix` | `value_counts` (the registry in `make_my_figure_core/transforms.py::_TRANSFORMS`, applied by `apply_transform`). Ids are stable strings: `tf_ridge_columns`, `tf_box_columns`, `tf_corr_heatmap`, `tf_count_bar`. The returned list is filtered to `available_plot_types()`.
- `recommend_guidance` adds `kind="guidance"` recs (`guide_volcano`, `guide_ma`) for matrices, with `plot_spec_draft=None` and an `instructions` string explaining that a precomputed differential table is required. Guarded by `if "volcano_plot" in available_plot_types()`.

Tests: `tests/test_transforms.py` checks that a wide table yields both kinds and that guidance recs carry no draft.

## 2. How the apps consume it

### Desktop (`apps/desktop_app/`)

- `controller.py::DesktopController.recommend_for_loaded(data)` → `recommend_for_table(data.info.dataframe, table_name=data.table_name)`; `recommend_after_analysis(...)` mirrors the core call.
- `main.py::_refresh_recommendations` runs on every `_set_data` when `self._auto_recommend` is true (default) and is wrapped in `try/except` — recommendations must never break the app.
- `recommendations_panel.py::RecommendationsPanel` renders one card per rec (`_make_card`) with signals `generateRequested` and `addToBuilderRequested`, plus a local `_dismiss`. Cards show plot type, confidence, `why`, `missing_mappings`, `warnings`; `requires_confirmation` triggers a Yes/No dialog in `main.py::_apply_recommendation` before rendering.
- Transform recs go through `controller.apply_transform(data, transform)` (calls `transforms.apply_transform`, wraps the result as a new `LoadedData` named after `output_filename`) and `controller.save_table` persists the reshaped CSV. `main.py` shows a "restore original data" affordance after a transform replaces the working table.
- `tests/test_ui_consistency.py::test_recommendation_scroll_has_min_height` reads the panel source to pin a layout invariant.

### Streamlit (`apps/streamlit_app/streamlit_app.py`, around the `"🔮 Recommended figures"` expander)

- Calls `recommend_for_table(table_info.dataframe, table_name=table_name)` inside `try/except`, prints `**Detected data type:** <schema>`, then one block per rec: display name, `int(round(confidence*100))% match`, `why`, `instructions` (guidance), `warnings`.
- A `Use ▸ <name>` button exists only for transform recs (applies the transform into `st.session_state["_grouped_df"]`) or for direct recs with a draft; it sets `st.session_state["rec_plot_type"]`, which seeds the "2. Plot type" selectbox once ("manual choice wins after").

### Manual coverage

`docs/manuals/User_Manual/parts/02_mapping_recommendations_matrix_preprocessing_statistics.md` Part VI ("Data-aware recommendations", sections 24–26) documents the engine for users, and `docs/manuals/audit/current_capabilities.md` lists it as "advisory; confidence is a heuristic score, not a probability".

## 3. Documentation pointers (and their drift)

- `docs/RECOMMENDED_FIGURES.md` — the user-facing description of the *table* recommender: how-it-works, a schema → figure table, app behaviour, and the v0.6.1 transform/guidance section. **Its schema table is stale relative to the code**: it still says MA is a "scatter substitute", Manhattan/Q-Q and dose-response are "not implemented", network graph is 0.3 / not renderable, and paired gets a warning that slopegraph is unavailable. On this commit `plot_recommender.py` recommends `ma_plot` (0.7), `manhattan_plot` + `qq_plot`, `dose_response_curve`, `network_graph` (0.8) and `paired_slopegraph` (0.75) directly (see `tests/test_recommendations.py::test_network_and_gwas_recommend_real_types`, `test_dose_response_recommends_curve`). Update the table when touching the engine.
- `docs/PLOT_RECOMMENDATIONS.md` — despite its name, documents the **matrix-workflow** recommender (`RecommendedPlot`, readiness statuses, `PlotEditorHandoff`).
- `docs/V0_6_NEW_FEATURES.md` §1 — release-level summary with the user-responsibility disclaimer.

## 4. Matrix-workflow recommender (summary)

`make_my_figure_core/matrix_workflow/recommendations.py::recommend_plots(matrix_spec, metadata, has_differential_summary=..., n_features=...)` returns `RecommendedPlot` entries with `key`, `plot_type`, `label`, `reason`, `required_data_shape`, `required_transformations`, `required_user_inputs`, `readiness_status` (`ready`, `needs_feature_selection`, `needs_group_selection`, `needs_transformation`, `unavailable`), `scientific_warnings`, `visual_warnings`. Ordered ready-first; nothing auto-generates. `recommend_from_differential_table(has_average_abundance=...)` covers a loaded results table. `transform_recommendations.py::recommend_preprocessing(qc)` and `normalization_catalog()` are the preprocessing side.

Both apps hand a chosen `RecommendedPlot` to `matrix_workflow.build_plot_inputs` and then to the normal plot editor via `plots/handoff.py::PlotEditorHandoff` (`controller.matrix_plot_handoff`); there is no second reduced plot UI. Tests: `tests/test_plot_recommendations.py`, `tests/test_preprocessing_recommendations.py`, `tests/test_matrix_handoff.py`; the bundled fixture `examples/matrix_workflow/expected_recommendations.json` is the golden list.

## 5. Adding an advisory rule for a new plot type

Policy first: **a rule is not added merely because a renderer exists.** Every rule needs a
data signature the profiler can actually detect from headers/shape, a reason a user would
recognise, and a negative test showing ordinary tables do not trigger it. Plot types with
no detectable signature (e.g. swimmer, spider, Sankey, UpSet, Bland–Altman, waterfall,
forest on its own, embedding scatter) have **no rule on this commit** and that is deliberate.
Recommendations are advisory; the user confirms every mapping in the editor.

Checklist when a rule is justified:

1. **Roles.** If the signature needs new header aliases, add a key to `_ALIASES` in `data_profiler.py` and an `add(role, col, conf, reason)` block in `profile_table`. Keep aliases specific; broad words (e.g. `name`, `value`, `id`) already collide.
2. **Schema.** Either reuse an existing schema branch or add a string to `SCHEMAS` and a priority-ordered check in `detect_schema`. Put it *above* any more generic schema it could be mistaken for, and add a parametrised case to `tests/test_recommendations.py::test_schema_detection`.
3. **Rule.** In `plot_recommender.recommend_plots`, call `add(...)` inside the schema branch. Use only keys from `ui_hints.COLUMN_FIELDS[plot_type]` in the column map (unknown keys are dropped by `_mapping`). Pick a confidence consistent with neighbours (a secondary suggestion sits below the primary one for that schema). Set `cost`/`confirm` if the renderer is expensive. Leave `plot_spec_draft` intact only if `render(draft, df)` will work on the uploaded table as-is; otherwise clear it and populate `missing_mappings` (as the PCA rule does).
4. **Tests.** Add (a) a positive test that the schema and top `plot_type` come back and that the draft renders (`render(spec.top.plot_spec_draft, df)` pattern used in `test_survival_recommends_km_and_renders`), (b) a negative test on a plain `group + value` table and on a matrix asserting the new type is **absent**, and (c) confirm `test_every_recommendation_uses_publication_style_and_existing_or_flagged` still passes (it enforces `suggested_style == "publication"`, draft plot types ∈ registry, `journal_style == "publication"`, and no RNA-seq/DE vocabulary via `_FORBIDDEN`).
5. **Docs.** Update the schema table in `docs/RECOMMENDED_FIGURES.md`, the CHANGELOG `Unreleased` block, and, if the matrix workflow should also offer it, `matrix_workflow/recommendations.py` + `examples/matrix_workflow/expected_recommendations.json`.
6. **Do not** add a rule that implies computing statistics the app does not compute (the `_FORBIDDEN` list guards wording, not behaviour — keep both honest). Guidance recs (`kind="guidance"`) are the pattern for "you need an analysis first".

## 6. How false positives are tested today

There is **no dedicated false-positive suite**; negative coverage is spread across:

- `tests/test_recommendations.py::test_schema_detection` — 11 parametrised tables, each must map to exactly one schema, which indirectly asserts that e.g. a survival table is *not* `generic_long` and an enrichment table is *not* `precomputed_differential`.
- `test_every_recommendation_uses_publication_style_and_existing_or_flagged` and `_no_rnaseq` — wording/behaviour guard on three representative tables.
- `test_unnamed_categorical_group_is_recommended` — asserts no `edger` leakage.
- `tests/test_transforms.py` — guidance recs have no draft; transform recs list correct plot types.
- `tests/test_plot_recommendations.py::test_matrix_only_recommends_matrix_plots_ready`, `test_group_plots_need_groups_until_confirmed`, `test_volcano_needs_differential_then_becomes_ready` — readiness gating on the matrix side.
- `tests/test_release_guardrails.py::test_matrix_workflow_uis_have_no_rnaseq_or_journal_labels` — UI text guard.

Absent on main: a test that feeds every bundled example (`examples/by_plot_type/*/data.csv`) through `recommend_for_table` and asserts the *expected* schema per example, or that asserts a list of plot types that must *never* be recommended for a given schema. If you add rules, consider adding such a table-driven test rather than more ad-hoc cases.

## Verify this is still current

```bash
# schema vocabulary and rule branches
grep -n '"' make_my_figure_core/recommendations/schema_detector.py | sed -n 1,20p
grep -n 'add("' make_my_figure_core/recommendations/plot_recommender.py
# where the apps call the engine
grep -rn "recommend_for_table\|recommend_after_analysis" apps/ make_my_figure_core/ | grep -v "^make_my_figure_core/recommendations"
# run the engine tests (Qt-free)
MPLBACKEND=Agg python -m pytest -q -p no:pytest-qt tests/test_recommendations.py tests/test_plot_recommendations.py tests/test_transforms.py
```
