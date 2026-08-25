# Verification record — C1, C2, C3 through the software

Confirms each concern is achievable through the paths a user actually takes, not only through direct
API calls. Every step exercised below is the function the browser app calls when the corresponding
control is used, in the same order and with the same defaults.

The harness lives at `Concerns/verify_ui_paths.py`, which is untracked, because it reads the
collaborator's workbooks. Its figures are written to `Concerns/_verify_out/` and are not committed.

## Loop A — reproduce and drive the UI code paths

`35/35 checks passed` at commit `ba46857`.

**C1** — worksheet dropdown lists the sheet; the sheet loads with the three repeated `event` headers
kept distinct (`event`, `event.1`, `event.2`); the mapping roles include `survival_columns` and it is
declared multi-column; `input_form`, `y_scale`, `reference_line` and `curve_style` are offered;
`input_form` still **defaults to `subject_level`**, and on that default this file is **refused with a
message naming `precomputed`** rather than drawn; with the controls set, three curves appear on a
0–100 "% survival" axis, the 50 % guide is drawn, the x label applies, and each curve equals the
supplied values × 100 to **0.0e+00** — nothing re-estimated. The loaded table is unchanged afterwards.

**C2** — all three sheets appear in the dropdown; the "Header row" control demonstrably changes what
is read (`header=0` vs `header=2` now differ). For `Fig4E` and `Fig4F`, "Define groups → Assign sample
groups (wide matrix)" assigns all **18** replicate columns to two genotypes and "Create grouped table"
produces the long frame (1 080 and 108 rows) via `melt_matrix_to_long`; the line plot then draws one
series per genotype with **every point equal to the group mean (0.0e+00)** and n ≥ 9 behind each.
`Fig5B` composes its two-level header, recovers 3 fibre types × 2 genotypes over 62 545 measurements,
and each fibre type renders both genotypes from a common density baseline.

**C3** — `bracket` remains the default placement; with `above_bar` there is one label above each of
the seven non-control bars, the control bar carries none, **every label is reproducible from its own
stored `StatResult`**, p-values match `scipy` and BH matches `statsmodels` (max |Δp| 0.0e+00,
|Δq| 2.7e-20), no two labels overlap when measured from rendered bounding boxes, and headroom falls
from 2.75× to 1.13× of the data range.

## Loop B — visual inspection

Opened and checked: the C1 survival curve (three curves, correct crossing order, 50 % guide, no
clipping), `Fig4F` (plateau, WT above P27A, overlapping SEM bands), `Fig5B` type 2a (both
distributions fully visible, bimodal shape preserved, largely superimposed) and the C3 bar plot
(marker centred over each bar, clear of its error bar, control unmarked).

## Loop C — regression and the built distribution

Full suite on the branch before merging the packaging fix: **1266 passed, 3 skipped, 2 failed**. The
two failures are the known pre-existing Streamlit pair, which surface only because Streamlit is now
installed; each fails identically against the pre-change file.

`fix/package-data-resources` was then merged, because a wheel built without it ships no `schemas/`
and cannot render at all. After the merge: targeted plus packaging tests **79 passed, 2 skipped**, and
the UI-path harness still **35/35**.

The distribution was built as `1.0.0+c1c3.<commit>` rather than plain `1.0.0`, because v1.0.0 is
already tagged and released with different code; the local-version suffix ties the artifact to its
commit and PyPI rejects such versions outright. `version.py` is restored to `1.0.0` after the build,
under a shell trap so an interrupted build cannot leave it modified.

**Installed-wheel check** — a clean virtual environment, `pip install` of the built wheel, then:
`missing_bundled_dirs()` empty; C1 refuses a curve as events and draws three curves on a percent axis;
C2 composes a stacked header and honours a chosen header row, and the density overlay works; C3 places
one label per non-control bar; and **all 37 registered plot types render** from the wheel's own
bundled examples. `7/7`.

## Known limitations, unchanged

- **No log-rank test is possible from `Book4.xlsx`.** It needs at-risk and event counts per time; a
  digitised curve has neither, and rescaling does not change that.
- **Dunnett's test is not implemented**, so C3's paper's exact procedure is not reproduced; the
  demonstration uses Welch's *t* with BH correction and says so.
- **No p-value can be drawn on the 4E/4F line plots** — statistical annotation is wired into six plot
  families and the line plot is not one of them. The paired *t* test itself is exact against `scipy`.
- **`overlay` draws a kernel density estimate**, not a fitted Gaussian as the paper's wording implies.
- **The C1 legend shows the spreadsheet headers** (`event`, `event.1`, `event.2`). A `group_labels`
  mapping exists but has no sidebar widget yet; renaming the columns before upload is the workaround.
- **The C2 legend title reads `group`**, the default name `melt_matrix_to_long` gives the column.
- **The desktop still renders `survival_columns` as a single combo.** `ui_hints` now declares it
  multi-column so that frontend can adopt it; the Qt widget was not changed because it cannot be
  exercised in this environment.
- **Neither GUI was clicked.** PySide6 cannot load `libxkbcommon.so.0` here, and the browser app was
  driven through Streamlit's `AppTest` harness and its own code paths rather than a real browser.
- **Linux only.** macOS and native Windows were not tested.
