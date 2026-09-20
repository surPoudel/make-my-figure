# Matrix workflow

Turn a **feature-by-sample matrix** (expression / protein / metabolite / any
numeric feature matrix) into publication-ready figures — with **no silent
guessing**. You confirm every column role and every group before anything is
plotted or analysed.

> **One plot editor.** The Matrix Workflow prepares and validates data, then hands
> the recommendation to the **same full plot editor** the normal workflow uses —
> there is no second, reduced plotting UI. On the *Recommend & generate* step, pick a
> recommended plot and click **Open in plot editor**: the plot-ready derived table
> loads into the normal editor with the plot type and column mappings pre-populated,
> and you get the *complete* controls — thresholds, labels, duplicate-label handling,
> annotations, colors, marker size, colorbar/clustering, legend/axes/layout, and
> PNG/PDF/SVG + PlotSpec export. A lightweight **Quick preview** stays for a fast
> look. Matrix/metadata/preprocessing/statistics/workbook **provenance** travels with
> the plot into the exported PlotSpec (`source` block), and you can **return to the
> Matrix Workflow** without losing its state.
>
> The PlotSpec `source` block carries identifiers and a method sentence only. To keep the full records **and** the data, **Save Figure Package**: the `.mmfpackage` holds the original matrix, the exact derived matrix the plot used, and the MatrixSpec, SampleMetadataSpec and PreprocessingSpec as JSON; on reopening the chain is replayed and checked against the frozen derived matrix (see `FIGURE_PACKAGES.md`).

> **Multi-sheet Excel:** if your matrix lives in one worksheet of a workbook, select
> that sheet first (see [MULTI_SHEET_EXCEL.md](MULTI_SHEET_EXCEL.md)). The selected
> worksheet drives the wizard, its provenance is stored on the MatrixSpec, and you may
> supply sample metadata from another worksheet or an external file.

> **Optional preprocessing/QC step (raw-like matrices).** Between "define groups"
> and "recommend plots", both apps offer an optional preprocessing step
> (Streamlit **🧪 Preprocess (raw-like)**; desktop **③ Preprocess (raw-like)** tab):
> QC diagnostics + QC-plot preview → recommended workflows → **confirm-to-apply** →
> a clearly-named **derived matrix** used by all downstream steps → before/after QC.
> The raw matrix is preserved and every step is recorded in a `PreprocessingSpec`.
> Details: [PREPROCESSING_QC.md](PREPROCESSING_QC.md),
> [RAW_COUNTS_TUTORIAL.md](RAW_COUNTS_TUTORIAL.md).

This is a *generic feature matrix* layer. It is **not** an RNA-seq pipeline: it
runs no raw-count differential-expression model and uses no R. Precomputed
differential tables are supported, and normalized matrices can be analysed with
generic feature-level statistics when you choose the method.

## The data model

`make_my_figure_core.matrix_workflow`:

- **`MatrixSpec`** — a *confirmed* column-role mapping: `feature_id_column`,
  `feature_display_column`, `annotation_columns`, `value_columns`,
  `excluded_columns`, `value_type` (`normalized` / `log_normalized` /
  `raw_numeric` / `unknown_user_confirmed`), plus missing-value and
  duplicate-feature policies and `confirmed_by_user`.
- **`SampleMetadataSpec`** — a *confirmed* sample→group mapping (`sample_id_column`,
  `group_column`, optional `batch_column` / `paired_id_column` / covariates, and
  the `sample_to_group` dict).

Both round-trip to/from JSON (`to_dict` / `from_dict`).

## Steps

1. **Upload** a CSV/TSV/TXT/XLSX matrix.
2. **Map columns.** `suggest_matrix_spec(df)` proposes a mapping — the feature id
   (first text column), a display column, the numeric **value** columns, and the
   **annotation** columns. Crucially, integer-coded low-cardinality numeric columns
   (e.g. `annotationLevel` in `{1,2,3}`) are proposed as *annotations, not values*.
   **You confirm** (`confirmed_by_user = True`) before anything proceeds.
3. **Define groups.** Upload a metadata table (`suggest_metadata_from_table`) or
   assign samples to groups in-app (`metadata_from_assignment`). Sample ids are
   matched against the value columns (`metadata_sample_match`).
4. **Validate** (`validate_matrix`): feature id exists, value columns are numeric,
   annotation columns are not values, metadata matches, group sizes, missing values,
   duplicate ids. A `ValidationReport` (ok / errors / warnings / summary) drives the UI.
5. **Recommend** plots (`recommend_plots`) — see [PLOT_RECOMMENDATIONS.md](PLOT_RECOMMENDATIONS.md).
6. **Transform** as needed (`transformations`) — see [TRANSFORMATIONS.md](TRANSFORMATIONS.md).
7. **Render** with the single Publication style and export / add to the Figure Builder.

## No-silent-guessing rule

Suggestions are always `confirmed_by_user = False`. Validation fails until the
mapping is confirmed; statistics are gated behind `require_for_statistics` (two
confirmed groups). Value scale is never inferred — fold change depends on the
`value_type` you confirm (see [FEATURE_LEVEL_STATISTICS.md](FEATURE_LEVEL_STATISTICS.md)).

## Using it in the app

In the **Streamlit** app, load a table and switch the sidebar **Workflow** toggle to
**"Matrix workflow (guided)"**. The wizard walks the steps above — ① map columns,
② define groups (build in-app or upload), ③ validation summary, ④ recommended plots
+ optional differential summary + generate — and each generated plot can be
downloaded (PNG/SVG/PDF) or added to a ⑤ Figure Builder collection to compose a
multi-panel figure. State is kept in `st.session_state` (prefix `mw_`) so it
survives reruns and does not reset when you change plots.

In the **desktop** app, click **"🧮 Matrix workflow…"** (next to *Define groups*).
The dialog has the same tabbed steps (① map → ② groups → ③ validation → ④ recommend
& generate); the feature-level differential summary runs on a **background thread**
(with a busy state + cancel) so the UI stays responsive, generated plots preview
in-dialog and can be saved (PNG/SVG/PDF) or **added to the Figure Builder**.

Both GUIs are thin layers over the same glue — `matrix_workflow.build_plot_inputs`
(shared with tests) and the desktop `DesktopController.matrix_*` methods — so the
workflow logic is identical and unit-tested independently of any GUI.

## Example fixtures

`examples/matrix_workflow/` (synthetic, no private data): a 300-feature ×
(2 annotation + 12 sample) matrix, `sample_metadata.csv` (6 Ctrl + 6 Treatment),
a `precomputed_differential_table.tsv`, a `feature_list.txt`, and
`expected_recommendations.json`.
