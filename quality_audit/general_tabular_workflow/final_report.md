# Final report — macOS crash, general tabular workflow, log axes, factorial ANOVA

Date 2026-10-13. Machine: WSL2 Linux, Python 3.11.9, PySide6 6.11.2 (plus 6.12.0 in a
scratch environment for the crash work), R 4.5.3 (base R only, conda env `r_gsea`).

## Branches and commits

| Branch | Base | Contents |
|---|---|---|
| `hotfix/pyside6-6.12.0-refcount-crash` | `v1.3.0` | `4c473f2` exclude PySide6 6.12.0, binding probe in `--selftest` (pushed; CI build passed on macOS/Windows/Linux) |
| `feat/general-tabular-workflow` | `4c473f2` | `423eaf0` binding-probe fix · `2ee7d97` title-focus fix · `4a2a91d` features · `94d1445` coefficient table · `915323e` version label 1.4.0.dev1 (pushed) |

Nothing has been merged, tagged or released. The version label is `1.4.0.dev1`, a
development label so test builds can be told apart; it is not a release.

## 1. macOS crash

See `crash_investigation.md`. The cause was PySide6/shiboken6 **6.12.0**, bundled into
v1.3.0 because the release build installs the newest PySide6 its range allows. It
releases one reference too many per signal emit (`True` −1.000 per call) and per
`QTimer.singleShot` (`None` −1.005), against 0.000 on 6.11.2. The fix excludes 6.12.0,
and `--selftest` now fails any build that bundles a drifting binding. The author built
the hotfix on a Mac and reports that the user's crash is gone. The user's full `.ips`
report was never obtained.

Found later on the feature branch: the binding probe created a bare `QCoreApplication`,
so any later `QWidget` in the same process aborted. It took down a test worker. The
probe now creates a `QApplication`. **This fix also belongs on the hotfix branch.**

## 2. Desktop title box losing focus (reported during this work)

There were two causes: a detached widget became a top-level window and took
activation, and the new canvas called `setFocus()`. Both are fixed. Tested on all 45
plot types plus the violin mode (51 tests; 4 fail on the v1.3.0 code). Not yet tried
on a Mac.

## 3. General tabular workflow

* **Roles:** suggested with reasons; manual choices always win.
* **Transformations:** reused method names, the existing `PreprocessingStep` record and
  the package lineage, with new safety rules. Each transformation adds a column; the
  offset defaults to 0; invalid values are refused unless the user records them as
  missing; a log of a log is refused; transformations are always recomputed from the raw
  table.
* **Preview:** original vs transformed values with counts and ranges; Apply / Cancel /
  Reset; Revert.
* **Persistence:** the table is exported with its actual derived values plus a JSON
  record (source sha256, sheet, column, method, base, offset, invalid policy and counts,
  output checksum). Figure Packages hold raw + derived + record, replay to `identical`,
  survive a deleted or edited source, and detect tampering.
* **Classification:** experimental tables are no longer called expression matrices.
  Annotated count matrices, including low-count ones and ones with three or fewer
  samples, stay matrices.
* **Browser app:** transform expander, design check, axis controls and package support.
* **Performance:** at 10⁶ rows, the preview takes 33 ms. Applying two transforms takes
  3.8 s with checksums, a one-time Apply; the dialog and browser working copies take
  0.2 s, and the browser's change check takes 87 ms (was 1.4 s per rerun). The dialog no
  longer rebuilds the derived table once per column.

## 4. Axis display scaling

log10 / log2 / ln, plain / power / scientific notation, minor ticks, and explicit ranges,
applied centrally on the 7 plot types whose axis carries a positive magnitude
(`styles/capabilities.AXIS_SCALE_AXES`). The other 38 each record a reason.
**`plot_capability_audit.csv`: 90 / 90. `axis_scaling_validation.csv`: 81 / 81.** That
covers plotted values identical, limits containing the data, at least 2 labelled ticks,
fonts unchanged, PNG/PDF/SVG export, and a PlotSpec and a Figure Package round trip
byte-identical.

Refusals are reported, never silent: values ≤ 0, an already-log column, a non-positive
or data-hiding range, and a linear bar range that truncates bars. Two placement defects
on log axes were fixed:
* the scatter regression box covered 11–19 of 60 points; it now covers 0, or 1 on log-log;
* significance labels fell outside the axes; there are now none outside.

Legacy `y_scale: "log"` specs on other plot types still draw as before. Style presets
carry the tick notation, never the scale or range.

## 5. Statistics

* `factorial_anova` (1–3 factors, covariates, Type II / Type III with sum contrasts,
  partial η²) runs only after `check_design`. That check covers confounding, empty
  cells, rank deficiency (including nested factors under a main-effects model),
  residual df, constant response, and repeated subjects. Mixed models are not fitted,
  and the app says so.
* **R validation:** 509 / 509 quantities agree, with worst relative difference
  6.5 × 10⁻¹³ against a prespecified 10⁻⁹ (`factorial_statistics_validation.csv`).
  Transformations: 190 / 190, worst 2.1 × 10⁻¹⁶. Where R's `scale()` silently returns
  zeros after the SD overflows, ours refuses (`transformation_validation.csv`).
* **Correction:** `two_way_anova`'s effect size was SS/SS_total labelled as partial η²
  (0.549 vs a true 0.756 on the unbalanced validation design). It now refuses designs
  it cannot estimate.

## 6. Bee workbook

See `input_workbook_audit.md`. 4 rows; treatment ≡ time; social setting once per
level; the quantity columns are constant (and a + b + c ≠ total). The three-way ANOVA
is explained as not estimable. All factorial statistics were computed on clearly
labelled **simulated** replicated designs.

## 7. Independent review

A separate reviewer reproduced 10 defects (2 high), all of them now fixed, each with a
regression test:
1. a nested design under main effects was accepted with wrong F and P;
2. a truncated linear bar axis was silently accepted;
3. a nanomolar response was called constant;
4. low-count matrices were reclassified as tables;
5. axis settings were lost on reopening a spec without a style block;
6. legacy log specs changed;
7. a contradictory note appeared;
8. on a comma-decimal locale, 1,5 was read as 15;
9. a missing subject ID dropped rows;
10. invalid rows past the 20th were unmarked.

Two unverified items were also confirmed and fixed: labels outside log axes, and
`catalog_id` matched as a log column.

## 8. Tests

* Baseline at `d69e848`: 4208 passed, 13 skipped.
* Final, at `915323e` (version 1.4.0.dev1, including the coefficient table):
  * **serial (authoritative): 4518 passed, 13 skipped, 0 failed** (1 h 02 min);
  * parallel: 4514 passed, 13 skipped, 0 failed (`test_pop_out_panels.py` runs only
    in the serial run).
* Packaged `--selftest` from source: OK, now also covering the table transform, a
  three-way ANOVA, a log axis and binding refcounts.

## 9. Documentation

* New: `docs/GENERAL_TABULAR_DATA.md`, `docs/AXIS_SCALING.md`,
  `docs/STATISTICS_FACTORIAL.md`, and the tutorial `tutorial/general_tabular_data/`
  (10 steps, 9 screenshots from the real app, a simulated dataset and its generator).
* Updated: the style contract, packages, statistics, desktop, transformations, the
  CHANGELOG, and the User Manual part 06 source.
* **Not done here:** rebuilding the User Manual PDF/DOCX (`scripts/build_manuals.py`
  needs pandoc, which this machine lacks).

## Unresolved / for the author

* **Mac checks:** title focus, the table workflow, and the axis controls on a real Mac;
  the screenshots were taken on Linux, where emoji render as boxes.
* **Port to the hotfix:** if v1.3.1 ships before this branch, bring over the
  binding-probe fix (and the title-focus fix).
* **Style contract item 7:** it says plot type changes reset styling. The app resets on
  a new plot or new data instead. This predates this work and was not changed.
* **Not offered:** mixed models, post-hoc comparisons after a factorial model, and more
  than 3 factors.
* **Bee workbook:** committed as a test fixture; the author should confirm it may be
  public.
* **Release version:** a minor release (**1.4.0**): new features plus three fixes that
  change results (the two-way ANOVA effect size, classification, and refusing
  non-estimable designs).
