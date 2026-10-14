# Input workbook audit — `demo data.xlsx`

Fixture copy: `tests/fixtures/bee_demo_workbook.xlsx`
(sha256 `7f37ef4f94725297902681caf38600b1aede6fc67f413722986117ddbdc5d45a`, 10 703 bytes;
the two copies supplied, `demo data.xlsx` and `demo data (1).xlsx`, are byte-identical).

## Sheets

One worksheet, `Sheet1`: 4 rows × 11 columns, no missing values, header in row 1.

| Column | Type | Values | Distinct | Suggested role |
|---|---|---|---|---|
| sample id | integer | 1, 2, 3, 4 | 4 | identifier |
| treatment | text | a, b, a, b | 2 | factor |
| social setting | text | aa, bb, cc, dd | 4 | factor (each level once — no replication) |
| time | integer | 2, 4, 2, 4 | 2 | time (use as a factor) |
| bee age | integer | 5, 6, 5, 4 | 3 | response / covariate |
| bee body size_mm | float | 3.1, 3.3, 3.5, 3.9 | 4 | response / covariate |
| colony id | text | A, B, C, D | 4 | subject / colony |
| total quantity | integer | 100 ×4 | 1 | metadata (constant) |
| quantity a | integer | 50 ×4 | 1 | metadata (constant) |
| quantity b | integer | 61 ×4 | 1 | metadata (constant) |
| quantity c | integer | 32 ×4 | 1 | metadata (constant) |

## Design

* `treatment` and `time` are **completely confounded**: a → 2 and b → 4 in every row.
* `social setting` has one observation per level; `colony id` is unique per row (each
  row an independent unit).
* `total quantity` and `quantity a/b/c` are constant. A response with no variation
  cannot be analysed.
* Note for the data owner: quantity a + b + c = 143 in every row, while `total
  quantity` = 100. Either the parts are not components of the total, or a value was
  entered incorrectly.

## Consequences (verified in the application)

* `total quantity ~ treatment * social setting * time` is **not estimable**, and the
  app says why: constant response, treatment/time confounded, 12 of 16 combinations
  empty, 4 observations for 4 identifiable parameters (0 residual df). No F or P is
  produced (`tests/test_table_workflow_end_to_end.py::test_three_way_design_on_the_bee_workbook_is_explained_not_computed`).
* Even a main-effects model `bee body size_mm ~ treatment + time` is refused, because
  of the confounding. `bee body size_mm ~ treatment` is estimable, with 2 residual df
  and a warning that the error variance is poorly estimated.
* `two_way_anova` (the plot statistics panel) now refuses the confounded design too,
  instead of reporting `NaN`.
* Up to v1.3.0 the workbook was profiled as an `expression_like_matrix` and the sheet
  as `matrix`. It is now a generic experimental table
  (`tests/test_experimental_table_is_not_a_feature_matrix.py`).

A separate, clearly labelled **simulated** replicated design
(`tutorial/general_tabular_data/data/simulated_bee_factorial.csv`, and the validation
designs in `tests/fixtures/factorial/`) is used wherever factorial statistics must
actually be computed. It is not presented as real bee data.
