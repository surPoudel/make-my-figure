# Baseline full test suite - branch feature/evidence-derived-journal-presets at 193f637 (before any preset-library change)

Environment: WSL2 Linux, miniconda Python 3.11, matplotlib 3.10.8, pytest 9.1.1, MPLBACKEND=Agg, QT_QPA_PLATFORM=offscreen,
`-p no:pytest-qt` (PySide6 cannot load in this WSL image: libEGL/libxkbcommon missing), run 2026-09-16.

Command: `python -m pytest tests -q -p no:cacheprovider -p no:pytest-qt --continue-on-collection-errors`

Result: **1706 passed, 5 skipped, 8 warnings in 1326.58s (0:22:06)**

Collection errors (Qt-dependent modules, expected headless): 0 -> none

Reference: the branch's recorded Windows full-suite log (reports/v1.1.1_baseline/pytest_feature_branch_full.txt) is 1706 passed, 4 skipped.
The Qt GUI tests are exercised on Windows (see final report).
