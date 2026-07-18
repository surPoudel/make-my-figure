# Baseline test results (independent re-run)

## Environment
- OS: Linux (WSL2), repo on /mnt/c (OneDrive) — slow FS, not app logic.
- Python 3.11.8 (miniconda) · numpy 2.1.2 · pandas 2.2.3 · scipy 1.17.1 · matplotlib 3.10.8
- statsmodels 0.14.6 · networkx 3.6.1 · PySide6 6.11.1 (native libs missing → Qt skips)
- Streamlit: NOT installed → Streamlit tests skip
- 37 registered plot types

## Command
`python -m pytest -q -p "no:pytest-qt" --ignore=tests/test_desktop_gui.py`
(Bare `pytest -q` cannot collect here: pytest-qt imports Qt → libEGL/libxkbcommon missing.)

## Result (with interrupted work + audit fix in place)
1063 passed, 5 skipped (baseline, before the rotated-label fix + its regression test).
After the audit's rotated-label fix + 2 regression tests: 1065 passed, 5 skipped.

## Skips (5) — all environment/optional, none hide a release blocker
- test_app_smoke.py — Streamlit not installed (importorskip). Acceptable.
- test_streamlit_matrix_wizard.py — Streamlit not installed. Acceptable.
- test_pop_out_panels.py — Qt native libs unavailable. Acceptable.
- test_performance.py — Qt native libs unavailable. Acceptable.
- one optional-extra test (fitz/PyMuPDF or count-de/PyDESeq2) absent. Acceptable.

These must be run in a full dev env (Streamlit installed; Qt libs present) on the
target platforms; commands are in docs/CROSS_PLATFORM_QC.md.
