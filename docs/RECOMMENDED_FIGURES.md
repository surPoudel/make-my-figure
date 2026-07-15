# Recommended figures

`make_my_figure_core/recommendations/` profiles an uploaded table and suggests
figures that fit its shape, with a one-click PlotSpec draft for each
suggestion. Profiling is cheap (column typing, role detection, shape checks);
anything that could be slow on real data (matrix clustering, PCA) is flagged
instead of run automatically.

> Make My Figure can recommend plots and statistical workflows from uploaded
> data structure, but users are responsible for confirming that the
> recommended figures and tests match their experimental design.

## How it works

1. `data_profiler.profile_table(df, table_name)` builds a `DataProfile`:
   column kinds (numeric/categorical/datetime/id/binary), missingness, and a
   list of detected semantic **roles** (`group`, `p_value`, `logFC`, `subject`,
   `survival_time`, …), plus matrix characterization (`is_matrix`,
   `matrix_kind`, `is_correlation_matrix`, …).
2. `schema_detector.detect_schema(profile, df)` classifies the table into one
   coarse **schema** (priority-ordered, most specific first) from a fixed
   vocabulary — see the table below.
3. `plot_recommender.recommend_plots(profile, schema, df, table_name)` maps the
   schema to one or more `Recommendation`s, each with a `plot_spec_draft` built
   from the registry's `make_spec` (so a "Generate" click is one call to
   `render()`).
4. The two entrypoints in `recommendation_runner.py`:
   - `recommend_for_table(df, table_name)` — run right after upload.
   - `recommend_after_analysis(df, *, stats_report=None, differential=False,
     has_matrix=False, table_name=...)` — follow-up suggestions once you've run
     statistics (suggests an annotated box/violin with significance brackets)
     or have a precomputed differential table (suggests volcano-family plots,
     plus a "top-feature heatmap" note if a matching matrix is also available).

Both return a `RecommendationSpec(table_name, schema, profile_summary,
recommendations, notes)`. Each `Recommendation` carries: `plot_type`,
`display_name`, `confidence` (0–1), `why` (plain-language reason),
`required_mappings` / `missing_mappings`, `suggested_statistics`,
`suggested_style` (always `"publication"`), `suggested_thresholds`,
`estimated_cost` (`"low"|"medium"|"high"`), `requires_confirmation`,
`warnings`, and `plot_spec_draft` (`None` when the recommendation cannot be
rendered directly — e.g. PCA needs a second metadata table, so its draft is
cleared and it is listed under `missing_mappings` instead).

## Data-type → recommended figures

| Detected schema | Trigger (roles/shape) | Recommended figure(s) | Notes |
|---|---|---|---|
| `precomputed_differential` | fold-change + p-value/FDR columns (not an enrichment table) | Volcano plot (0.92) | edgeR/limma/DESeq2 header conventions are recognized via `de_detect.py`; p-values are read verbatim, never computed. If effect-size CI columns are also present: Forest plot (0.6). If an average-expression column is present: a scatter substitute for MA plot (0.5, with a warning that MA is not implemented). |
| `survival` | time-to-event + event-status columns | Kaplan–Meier curve with log-rank (0.88) |  |
| `classification` | binary label + numeric prediction score | ROC curve (0.85) |  |
| `enrichment` | term + count/ratio + p-value/FDR columns | Enrichment dot plot (0.8) |  |
| `mutation_matrix` | sample/gene/alteration columns | Oncoprint (0.78); + Lollipop plot if protein positions present (0.55) |  |
| `correlation_matrix` | square, symmetric numeric matrix | Clustered heatmap (0.82, medium cost) |  |
| `numeric_matrix` / `expression_like_matrix` / `matrix_plus_metadata` | wide features×samples numeric matrix | Clustered heatmap (0.85); PCA scatter (0.7, needs a sample-metadata table) | Cost/confirmation escalate to `high`/`requires_confirmation=True` above ~40,000 matrix cells. A note suggests "Define groups" to enable group-comparison plots. |
| `paired` | subject id + 2-level group + repeated numeric value | Box/violin with points (0.7) | Warns that a paired slopegraph is not available; use a paired test. |
| `generic_long` | a group/category column + a numeric value | Box/violin with points (0.72); Bar plot with error bars (0.6); Grouped bar plot if a second categorical column exists (0.55); Scatter + regression if 2+ numeric columns (0.5) |  |
| `gwas` | chromosome + position + p-value/FDR | Scatter substitute (0.4) | Warns that Manhattan/Q-Q is not implemented. |
| `dose_response` | dose + response columns | Scatter + regression substitute (0.5) | Warns that dose-response curve fitting is not implemented. |
| `network_edge_list` | source + target columns | Network graph (0.3) | Not renderable in this version — listed with a warning, no draft. |
| `unknown` | none of the above matched | Scatter + regression fallback (0.4) if 2+ numeric columns exist | Otherwise: pick a plot type manually. |

No RNA-seq differential-expression analysis is ever recommended or run. For a
numeric/expression-like matrix the engine only ever suggests exploratory plots
(heatmap, PCA); for a precomputed differential table it recommends volcano and
related summaries, always reading the fold-change/p-value columns as given.

## Using recommendations in the app

- **Desktop app** — the **Recommended figures** panel refreshes automatically
  each time a table is loaded (`_auto_recommend`, on by default). Each card
  shows the plot type, confidence, reason, any missing mappings, and warnings,
  with three actions:
  - **Generate** — selects the plot type and fills the mapping/options widgets
    from the draft, then renders. You can still edit any mapping afterward in
    the normal "2. Map columns" / "3. Options" panels before exporting.
  - **Add to Figure Builder** — does the same, then saves the result as a panel
    (equivalent to clicking "Save current plot as panel").
  - **Dismiss** — removes the card without generating anything.
  - If `requires_confirmation` is set (matrix clustering/PCA above the cost
    threshold), a Yes/No dialog appears before anything is generated — no
    heavy analysis ever runs without an explicit confirmation.
- **Streamlit app** — the **"🔮 Recommended figures"** expander (collapsed by
  default) lists the same suggestions with confidence and warnings; clicking
  **"Use ▸ <name>"** sets the plot type for the sidebar mapping/render flow
  below, where you confirm/adjust the column mapping and click through to
  render — a natural confirmation step before any figure (including
  matrix-heavy ones) is actually produced.

## See also

- [docs/V0_6_NEW_FEATURES.md](V0_6_NEW_FEATURES.md)
- [docs/PUBLICATION_QC.md](PUBLICATION_QC.md) — score a generated recommendation before export.
- `make_my_figure_core/de_detect.py` — the DE-column alias detection used for volcano recommendations and mapping.
