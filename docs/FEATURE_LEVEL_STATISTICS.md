# Feature-level differential summary

`make_my_figure_core.matrix_workflow.feature_differential_summary` computes a
**generic per-feature comparison** between user-defined groups on a *normalized*
feature matrix.

> **Preprocessing provenance.** When the input is a **derived** (preprocessed)
> matrix, pass `preprocessing_note` (the `PreprocessingSpec.method_sentence()`),
> `source_matrix_id`, and `preprocessing_spec_id`. Both apps do this automatically
> when you compute a differential summary after applying preprocessing, so the
> stored result — and the method sentence drawn on volcano/MA plots — trace back to
> the exact preprocessing chain, e.g.:
>
> *"Values were median-scaled across samples, transformed as log2(x + 1), and
> compared between Ctrl and Treatment using Welch's t-test with Benjamini-Hochberg
> FDR correction."*

It is **not** a raw-count differential-expression pipeline and **not** a
count-based model, and it uses no R. If you already have a differential table from
another tool, use it directly (precomputed mode) — the app plots it verbatim.

## Inputs (all user-confirmed)

- a confirmed `MatrixSpec` (value columns + `value_type`);
- a confirmed `SampleMetadataSpec` (groups);
- `group_a` / `group_b` (or all groups for a multi-group test);
- `test` and `correction`.

Statistics are gated: the call raises unless both specs are `confirmed_by_user`.

## Tests & correction

- Two-group: `welch_t`, `students_t`, `mann_whitney`, `paired_t`, `wilcoxon`.
- Multi-group: `anova`, `kruskal`.
- Correction: `benjamini_hochberg` (FDR), `bonferroni`, `holm`.

Effect sizes: Cohen's d + a t-based 95% CI of the mean difference (t-tests);
rank-biserial correlation (Mann-Whitney).

## Fold-change rules (never inferred silently)

| `value_type` | Effect reported |
|---|---|
| `log_normalized` | mean difference on the log scale = the log2 fold change |
| `normalized` / `raw_numeric` | log2 fold change of `(mean_a + pseudocount)/(mean_b + pseudocount)` |
| `unknown_user_confirmed` | mean difference only; a warning asks you to confirm the scale |

Negative values do not by themselves decide the scale — you confirm `value_type`.

## Output

A tidy table with `feature_id`, `feature_label`, annotation columns, `n_a`, `n_b`,
`mean_a`/`mean_b`, `median_a`/`median_b`, `effect_type`, `log2_fold_change`,
`mean_difference`, `statistic`, `effect_size`, `ci_low`/`ci_high`, `p_value`,
`adjusted_p_value`, `correction_method`, `test_name`, plus a `method_sentence()`.

## Traceability invariant

Every p-value, adjusted p-value, effect size, or statistic shown on a figure must
trace to a stored differential-summary row (or a `StatsSpec` result). If a value
is not traceable, it is not shown. Volcano and MA plots read these columns
directly; they never recompute a statistic.
