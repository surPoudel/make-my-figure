# From expression matrix to visualization (planned - after pilot review)

TITLE: Matrix workflow - from expression matrix to visualization
TARGET LENGTH: 8:00
DATASETS: tutorial/datasets/feature_sample_matrix.csv, tutorial/datasets/sample_metadata.csv
START STATE: start screen.
ACTION SCRIPT: `automation/tutorials/matrix_workflow.py` - to be written after the pilot is approved; it will drive the real `Matrix workflow...` dialog (`apps/desktop_app/matrix_wizard.py`).

Outline, following the five tabs of the dialog as they are labelled today:

| segment | tab / screen | content |
|---|---|---|
| 1 | Data preview | feature-by-sample matrix; what a MatrixSpec records |
| 2 | ① Map columns | Feature ID column, Feature display column, Value scale (you confirm), value columns; **Confirm mapping** |
| 3 | ② Define groups | assign value columns to groups; **Upload metadata file...** with `sample_metadata.csv`; **Confirm groups** |
| 4 | ③ Preprocess (raw-like) | **Run diagnostics**, QC plot preview, recommended preprocessing - "you choose; not applied automatically"; **Apply preprocessing -> use processed matrix**; before/after report; **Revert to raw matrix** |
| 5 | ④ Validation | what is checked before recommendations |
| 6 | ⑤ Recommend & generate | feature-level differential summary (Test, Correction, Group A, Group B, **Compute differential summary**); recommended plots; **Open in plot editor**, **Quick preview** |
| 7 | plot editor | PCA, heatmap with group strip, volcano from the differential summary |

KEY MESSAGE: Recommendations are advisory; every step waits for the user's confirmation.
