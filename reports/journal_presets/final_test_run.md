# Final full test suite - branch feature/evidence-derived-journal-presets (all changes applied)

Same environment and command as baseline_test_run.md (WSL2, Python 3.11, MPLBACKEND=Agg, `-p no:pytest-qt`), run 2026-09-16.

Result: **2360 passed, 5 skipped, 9 warnings in 1579.83s (0:26:19)**  (baseline before changes: 1706 passed, 5 skipped)

Targeted re-run of the new/changed modules after the last fix (experimental library incl. every shipped preset x every plot type,
preview/layout QC, scientific identity, box/violin options, bar observations, bracket geometry, UI wiring, figure-preset QC):
708 passed (final_targeted_tests.txt).

Windows (PySide6, portable Python 3.11): Qt GUI, controllers, pop-out panels, performance, wiring, Streamlit presets: 87 passed, 1 skipped
(windows_qt_tests_final.txt).

No failures. The 654 additional passing tests are the new modules listed in FINAL_REPORT.md section 5.
