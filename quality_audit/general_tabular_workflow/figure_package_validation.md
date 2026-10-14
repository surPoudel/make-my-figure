# Figure Package validation — derived tables and axis scales

All checks run against the real code; tests are named so they can be re-run.

## Derived table from the bee workbook (`tests/test_table_workflow_end_to_end.py`)

| Step | Check | Result |
|---|---|---|
| Transform | `log10(bee body size_mm)` added; values equal `np.log10` of the originals (atol 1e-15); original columns and raw table unchanged | pass |
| Export | CSV holds the transformed values (rtol 1e-15); `.transformations.json` records workflow, source sheet, 64-hex source sha256, column, output column, base 10, offset 0, invalid policy, output and exported digests | pass |
| Save | package written from the main window's own context (`_matrix_context()` → raw `source_table`, `derived_table` with `derived_from`, `preprocessing_spec.json` with `workflow: "table"`) | pass |
| Source edited after packaging | the workbook was overwritten with an unrelated table | package unaffected |
| Package moved, source deleted | package moved to another folder; workbook deleted | reopens |
| Fresh process | reopened by a separate Python process: derived values identical (exact list equality), raw values identical, mapping `y = log10(bee body size_mm)`, derived columns listed | pass |
| Replay | `verify_preprocessing` re-runs the record on the frozen raw table → `identical` | pass |
| Tamper | one digit changed inside the frozen derived table → `PackageIntegrityError` on opening | detected |

## Axis scales (`quality_audit/general_tabular_workflow/axis_scale_audit.py`)

For each of the 9 applicable plot axes × 3 log bases × 3 tick formats (81
combinations), the render was packaged, reopened through `loaded_from_package`, and
re-rendered. The PNG digest (100 dpi) is identical to the original render in **81 of
81**, and a PlotSpec JSON round trip is likewise identical in 81 of 81
(`axis_scaling_validation.csv`, columns `plotspec_roundtrip_identical`,
`package_roundtrip_identical`).

## Matrix packages unchanged

A matrix-workflow package still writes `source_matrix` / `derived_matrix` and replays
through the matrix chain. The table-workflow branch is taken only when the record says
`workflow: "table"`. Existing package tests: `tests/test_figure_package*.py` — all pass
in the full suite.

## Browser app

The browser app packages a derived table through the same `content_for_single_plot` +
`MatrixContext` path and attaches the uploaded original file to the raw table
(`tests/test_streamlit_table_tools_and_axis_scale.py` checks that the Figure Package
download is offered with a derived table).
