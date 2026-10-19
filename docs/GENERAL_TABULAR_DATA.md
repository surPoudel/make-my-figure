# General tabular data — roles, transformations, derived data

For an ordinary experimental table: one row per observation, columns named however
the experimenter named them (`treatment`, `social setting`, `colony id`,
`bee body size_mm`, `total quantity`). Ecology, entomology, agriculture, physiology,
behaviour — anything that is not a feature × sample matrix.

This is **not** the [matrix workflow](MATRIX_WORKFLOW.md). Nothing here normalises,
filters, or treats numeric columns as expression values, and an experimental table is
not profiled as an "expression-like matrix" (up to v1.3.0 it was; see
`tests/test_experimental_table_is_not_a_feature_matrix.py`).

Desktop: **📋 Prepare table (roles, transform, ANOVA)…** under the data buttons.
Browser: the **📋 Prepare table** expander under the table preview.
Engine: `make_my_figure_core.tabular`.

## 1. Column roles

| Role | Meaning |
|---|---|
| Identifier | one distinct value per row (`sample id`) |
| Response | a measured value (`total quantity`) |
| Factor / group | a categorical treatment or grouping (`treatment`, `social setting`) |
| Time | a time variable; use it as a factor when only a few times were sampled |
| Covariate | a continuous predictor adjusted for (`bee body size_mm`) |
| Subject / colony | the experimental unit; rows sharing it are **not** independent replicates |
| Label, Other metadata, Ignore | carried along, not analysed |

Suggestions come from names and values and always show their reason; your choice
always wins. A constant column is suggested as metadata, because it has nothing to
analyse.

## 2. Transformations

| Method | Formula | Defined for |
|---|---|---|
| `log10`, `log2`, `ln` | log(x + offset) | x + offset > 0 |
| `sqrt` | √(x + offset) | x + offset ≥ 0 |
| `zscore` | (x − mean) / SD, sample SD (ddof = 1) | a column with spread |

* A transformation **adds a column** next to the original — `log10(total quantity)`,
  `log2(count + 1)`. The original column and the original table never change. Plot,
  test or export either one; switching is a matter of choosing the column.
* The **offset is explicit** and defaults to **0**. Nothing gets a silent `+ 1`. A
  non-zero offset appears in the new column's name and in the record.
* **Invalid values are never hidden.** Before anything is applied, the preview shows
  the number of values the method is undefined for (0 and negatives for a log), and
  the smallest one. The default is to **refuse**. You can instead choose to record
  those observations as **missing in the new column**. The originals are kept, and
  the number affected is recorded.
* A column that already holds log values (its name says `log`, `log2FC`, `-log10`… or
  it was made by a log transformation here) is not logged again.
* Text inside a numeric column is reported, not converted.
* Transformations are always recomputed from the raw table. A derived column is never
  transformed by accident.

The preview shows original and transformed values side by side, with the method, base,
offset, valid / invalid / missing counts, and the range before and after. **Apply**
builds the derived table, **Cancel** leaves everything as it was, and **Reset** clears
the list. **↩ Revert to original data** in the editor goes back to the raw table.

## 2a. Wide tables: reshape to long form

A **wide** table keeps one row per plant (animal, plot, colony) and one column per
repeated measurement — `Month_4, Month_6, Month_8, Month_10`. The box/violin, line and
facet plots and the statistics need one row per observation. **↕ Wide → long…**
(desktop, beside *Prepare table*; browser: the **↕ Wide → long** expander) gathers the
chosen columns into two new ones:

| wide | long |
|---|---|
| `Species, Age, Nitrogen, Replicate, Month_4 … Month_10` (60 rows) | `Species, Age, Nitrogen, Replicate, Month, Growth_cm` (240 rows) |

* **Suggested automatically.** When numeric columns share a name with a number after
  it (`Month_4`, `Day1`, `week.2`), the button reads *(suggested)* and the dialog opens
  with those columns ticked, the prefix (`Month_`) removed and the levels turned into
  numbers (4, 6, 8, 10). Nothing is changed until **Reshape and use**.
* **Every other column is kept** and repeated on each row (Species, Age, Nitrogen,
  Replicate) — those are what the facets, colours and statistics use.
* **Names that hold several factors** (`A_Young`, `B_Old`) split into several columns:
  *Column names go to* `Species, Age`, *Split names at* `_`.
* **Empty cells** are left out (no observation) and counted, or kept as missing.
* **Refused, with the reason:** a new column named like a kept one, gathered columns
  that mix numbers and text, names that do not split into the requested parts, two
  columns that give the same level.

The wide table is never modified. The desktop app saves the long table **beside the
wide file** as `<name>_long.csv` with `<name>_long.transformations.json` (never
overwriting: an existing name gains ` (2)`, ` (3)`, …); the browser offers both as
downloads. **Revert to original data** returns to the wide table. The reshape is the
first step of the table record: column transformations added afterwards act on the
long table, and a Figure Package stores the wide table, the long table and the
record, and replays the reshape to verify it (`identical`). Engine:
`make_my_figure_core.tabular.reshape` (`WideToLong`, `suggest_wide_to_long`,
`preview_wide_to_long`, `wide_to_long`). Tests: `tests/test_wide_to_long.py`.

## 3. Saving derived data

**Export table with derived columns…** (button and File menu) writes the table **with
the transformed values themselves** (CSV, TSV or XLSX), plus
`<name>.transformations.json`:

```
workflow, source_name, source_sha256 (of the original file), source_sheet,
source_table_digest (raw table as loaded), transforms [column, method, offset,
invalid policy, output column, ddof], preprocessing_steps [base, n_valid,
n_invalid, n_missing ...], derived_columns, output_table_digest,
exported_table_digest, column_roles, app_version, created_at
```

A **Figure Package** saved from a derived table contains:

* the raw table (`source_table`) and the derived table (`derived_table`, with
  `derived_from` lineage), each frozen and checksummed;
* the record (`preprocessing_spec.json`, `workflow: "table"`);
* the PlotSpec that maps the derived column.

Reopening needs neither the source file nor its folder. Editing the source after
packaging changes nothing in the package. Changing any byte of a frozen table fails
integrity verification. Reopening also replays the record on the frozen raw table and
reports `identical` when it reproduces the frozen derived table exactly.
Test: `tests/test_table_workflow_end_to_end.py`.

## 4. Factorial analysis

See [STATISTICS_FACTORIAL.md](STATISTICS_FACTORIAL.md). The design is checked first;
a design that cannot be estimated is explained and not computed.

## Transformation versus axis scale

A log10 **transformation** changes the numbers: 1, 10, 100, 1000 become 0, 1, 2, 3,
and a test on the derived column tests those. A log10 **axis**
([AXIS_SCALING.md](AXIS_SCALING.md)) changes only how the original numbers are drawn.
One consequence to keep in mind: a mean on a log axis is the arithmetic mean of the raw
values. The mean of a log-transformed column is the mean of the logs, which is the log
of the **geometric** mean. They differ whenever values vary.
