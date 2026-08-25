# Collaborator concerns C1–C3 — final resolution report

Three concern packages were read, reproduced, diagnosed, fixed, tested and inspected independently.
Per-concern detail is in `C1_resolution.md`, `C2_resolution.md`, `C3_resolution.md`; the pre-work
triage is in `concern_inventory.md`.

---

## C1 — Survival / lifespan curve: percentage scale, log-rank test, customizable headers

**Concern.** A lifespan figure like Fig. 1F of PMID 42402962 could not be produced. The collaborator
noted the Kaplan–Meier plot works in "fractions of 1 rather than percentages", divided their values
by 100, supplied `Book4.xlsx`, and still "did not get a graph corresponding to the one attached".
They asked whether the workbook was wrong, for a log-rank test, and for customizable column headers.

**Reproduction.** The workbook holds an **already-computed survival curve** — a time column plus
three columns of S(t), one per group, all sharing the header `event`. Mapping `time`/`event` and
rendering gave `events: 1` out of 28 rows and a flat step at S = 0.9643 across the whole axis, **with
no warning**. Confirmed visually. The workbook's headers happen to equal the renderer's own defaults
(`time_months`, `event`), so the mapping auto-resolved and nothing prompted confirmation.

**Root cause.** *Faulty assumption plus absent input validation* in `plots/survival.py`. The
estimator counts events with `sum((times == t) & (events == 1))`; given probabilities only the single
t = 0 row equals 1.0, so one event was counted and the curve never fell again. Compounded by a
hard-coded `ylim(0, 1.02)` and y-label, no input form for a precomputed curve, and — explaining the
"headers are fixed" remark — `ui_hints.options()` returning an **empty list** for this plot type, so
it exposed no user controls at all.

**Fix.** Two input forms (`subject_level` default, new `precomputed` taking `survival` /
`survival_columns`); strict event-indicator validation that accepts 0/1, maps a two-level coding
*and reports which value it treated as the event*, and raises with actionable guidance on anything
with more levels; `y_scale` fraction/percent driving limits and the default label; `reference_line`
in axis units; `group_labels` to name curves independently of spreadsheet headers; `curve_style`
step/line with `line` refused for estimated curves; an explicit refusal to compute a log-rank test
from a precomputed curve. The resolved indicator is written back into the mapped column of the
renderer's own copy so the drawn curve and the reported test read one source of truth. Four options
and a fourth column role are now exposed to both frontends.

**Tests.** `tests/test_survival_input_forms.py`, 20 tests — **16 fail on the old code, all 20 pass
after**. Includes a PlotSpec round-trip through the exported sidecar.

**Validation.** Log-rank checked against `statsmodels.duration.survfunc.survdiff`: 2-group
|Δχ²| = 2.3 × 10⁻¹⁴, p 3.2 × 10⁻¹⁶; 3-group |Δχ²| = 3.1 × 10⁻¹⁵; tolerance 1 × 10⁻¹⁰ — **PASS**, and
reported as a difference rather than as exact agreement. A 1/2-coded input gives a **bit-identical**
χ² to 0/1 (difference 0.0), proving the recoding reaches the statistics. Event counts under 1/2
coding matched ground truth exactly. The output was rendered from the collaborator's own workbook and
compared against their screenshot: 0–100 "% survival", "age (days)", three curves, the same curve
separating first and crossing 50 % at ≈ 28–29 with the others at ≈ 31–33, dotted 50 % guide, no
clipping or overlap.

**On the log-rank request, honestly:** the test was already implemented and is correct, but it
**cannot** be computed from `Book4.xlsx`. A log-rank statistic needs the number at risk and the
number of events per group at each event time; a digitised curve determines neither, and dividing by
100 does not change that. Subject-level rows (age at death, 0/1 indicator, group) would yield both
the curves and the test. The software now says so instead of returning a meaningless number.

**Status. Resolved,** with the log-rank limitation stated rather than worked around.

---

## C2 — Figures 4E, 4F and 5B could not be produced from `Book5.xlsx`

**Concern.** "I also could not find easy ways to generate these types of graphs (from Fig. 4E, 4F,
and 5B …)." The three sheets are named exactly `Fig4E`, `Fig4F`, `Fig5B`.

**Reproduction.** The plot types already existed; the sheets could not be shaped. `Fig4E` carries a
genotype label **merged** over each block of nine replicate columns; `Fig4F`'s real header is on
**row 3**, also merged; `Fig5B` has **two** header rows plus blank spacer columns. Read with the
default header every sheet came back mostly `Unnamed: n`. The loader warns *"confirm the header row
or choose 'No header'"* — and doing so changed nothing: `header=0`, `2`, `3` and `None` all returned
byte-identical frames, for Excel and for CSV alike.

**Root cause.** *Parser bug, in two parts.* (1) `load_table` declared and documented `header=` but
never forwarded it — three Excel dispatch calls passed three positional arguments, and
`_read_delimited` had no `header` parameter at all. `load_excel_sheet`, `preview_excel_sheet` and the
recorded `source_header_row` all fed that dead path, so the software's own advice could not be acted
on. (2) A merged group label survived only on the first column of its block, because Excel stores a
merged value once. A third finding surfaced while rendering 5B: `ridge_or_density_plot` implemented
only the ridge half of its own name, and with two groups the upper ridge is drawn **over** the lower
one, hiding the comparison. *Frontend propagation* compounded all of it: neither frontend had a
header-row control, so a GUI user could not reach the parameter even once it worked.

**Fix.** `header` forwarded on all six dispatch paths; `_read_delimited` honours it and names columns
positionally for `header=None`; empty and negative header specs rejected; multi-row headers
supported. Merged group labels recovered by reading the worksheet's **actual merged ranges** with
openpyxl — exact rather than heuristic — and composed into unambiguous names, with repeats
disambiguated so nine same-named replicates stay nine columns. New `header_fill`: `"merged"`
(default, trusts only recorded merges) or `"forward"` (opt-in, carries an outer label across blanks),
because a blank header can equally mean "no name" and inferring an unrecorded span would be inventing
structure. The differing default for delimited text — which records no merges at all — is explicit in
the code. `density_mode: "overlay"` added to the ridge/density renderer. `header_fill` threaded
through the desktop controller, and a **header-row control added to the Streamlit sidebar** (mode,
row number, stacked-rows, and the forward-fill checkbox), which also clears stale mappings when the
header changes.

**Result.** `Fig4E` → index + 9 + 9; `Fig4F` → spacer + `Hz` + 9 + 9; `Fig5B` → `type 2a/2x/2b
myofibers | LrpprcWT / LrpprcP27A`. n = 9 per group matches the paper. All three panels render.

**Tests.** `tests/test_header_row_and_merged_headers.py`, 19 tests — **15 fail on the old code, all
19 pass after**. Includes an AST guard on the Streamlit call site (Streamlit is not installed here, so
the call site is inspected rather than executed) and a desktop-controller propagation test.

**Scientific comparison.** No statistic is claimed to reproduce the paper. Every point on the 4F line
plot was checked against an independent pandas group mean: all 12 agree **exactly** (0.00,
tolerance 1 × 10⁻⁹), n = 9 behind each. The paired *t* test the paper used is implemented and matches
`scipy.stats.ttest_rel` exactly (t and p both 0.0 difference). **Methodological differences stated:**
4E/4F use a *paired* test because the genotypes were electroporated into contralateral muscles of the
same mouse, and statistical annotation is **not wired into** the line plot, so no p-value can be
drawn on those two panels; Fig. 5B is described as "Gaussian distributions" whereas `overlay` draws a
**kernel density estimate**, which matters here because the type 2a distribution is visibly bimodal;
the paper's two-way ANOVA over fibre type and genotype was not run.

**Visual.** All three opened. 4F rises to a plateau with WT above P27A and overlapping SEM bands; 4E
declines over 60 contractions; 5B first showed the **occlusion defect** in ridge mode — which is what
prompted the overlay mode — and in overlay both distributions are fully visible and largely
superimposed, consistent with the paper's "no significant difference in the size".

**Multi-sheet checks.** All three sheets listed, classified advisorily and selectable; each selection
returned a different frame with no stale carry-over; provenance persisted including the header row
actually used; output slugs identify the sheet.

**Status. Resolved.** The panels are producible; the annotation gap on line plots is documented.

---

## C3 — P-values above each bar, as in Fig. 2F

**Concern.** "…it would be [good] if the P-values could be automatically added on top of each bar as
in the graph in Fig. 2F." That figure compares each RNAi to one control and puts a single marker over
each bar. No data file was supplied, so this was reproduced synthetically.

**Reproduction.** The comparisons already worked (`comparison_mode: vs_control` with a
`reference_group`). Rendering them drew **7 stacked brackets**, inflated the y-axis to **2.86× the
data max**, and compressed the bars into the bottom third of the panel — confirmed visually. A second
suspicion was ruled out: the BH correction *is* applied (the values live on
`StatResult.adjusted_p_value`) and matches statsmodels exactly.

**Root cause.** *Missing feature in the annotation layer, not a statistics defect.*
`plots/stats_overlay.py` could only draw brackets spanning two categories, so comparisons sharing one
reference had to become N−1 stacked brackets. There was no way to say "this label belongs to that
bar".

**Fix.** `annotate_above()` places one label over each compared bar, leaves the reference unmarked and
expands the y-limit by one text line. `infer_reference_group()` recovers the shared group from the
items, and returns `None` when they do **not** share exactly one group — all-pairs comparisons — since
a label above one bar could not say which pair it described. `annotation.placement` (`"bracket"`
default, `"above_bar"`) dispatches; anything unplaceable **falls back to brackets** so switching
placement can never silently lose a comparison; an unknown placement raises. The placement lives in
the shared overlay engine, verified on bars and on box/violin.

**Result.** 7 labels, 0 brackets, headroom **1.13×** (was 2.86×).

**Tests.** `tests/test_above_bar_annotation.py`, 16 tests — **12 fail on the old code, all 16 pass
after**. Includes a rendered-bounding-box check that no two labels overlap, and a parametrised proof
that every drawn label equals `render_annotation(stored result)` for `stars`, `p` and `p_adj`.

**Validation.** Welch p-values match `scipy.stats.ttest_ind(equal_var=False)` exactly (0.0, all 7);
BH-adjusted match `statsmodels multipletests(fdr_bh)` to ≤ 2.7 × 10⁻²⁰; tolerance 1 × 10⁻¹². Every
drawn label traced back to its own stored `StatResult`.

**Methodological difference, stated not substituted.** The paper reports "one-way ANOVA" for each
RNAi versus control, which in practice means ANOVA plus a comparisons-against-control post-hoc —
Dunnett's test. **Dunnett's test is not implemented in MakeMyFigure.** The demonstration uses Welch's
*t* with BH correction and is **not** a reproduction of the paper's statistic; a figure made this way
should be labelled with the test actually used. One-way ANOVA remains available as an omnibus test and
correctly returns a single result to which `vs_control` does not apply.

**Status. Resolved** for the requested placement; the Dunnett gap is recorded, not approximated.

---

## Summary

| item | value |
|---|---|
| Branch | `fix/collaborator-concerns-c1-c3` (created off `main`) |
| Starting commit | `7c8b5a5` |
| Final local commit | one commit on this branch, local only (`git log -1 fix/collaborator-concerns-c1-c3`); the hash is not quoted here because it changes whenever this file is amended into it |
| Pushed | **NO** |
| Tag / release / visibility change | none |

**Files changed (10 tracked):** `make_my_figure_core/plots/survival.py`,
`make_my_figure_core/io/loaders.py`, `make_my_figure_core/io/workbook.py`,
`make_my_figure_core/plots/ridge.py`, `make_my_figure_core/plots/stats_overlay.py`,
`make_my_figure_core/plots/stats_integration.py`, `make_my_figure_core/statistics/schemas.py`,
`make_my_figure_core/ui_hints.py`, `apps/desktop_app/controller.py`,
`apps/streamlit_app/streamlit_app.py`.

**Files added (4):** three test modules plus this `reports/collaborator_concerns/` directory
(inventory, three per-concern reports, this report).

**Tests run.** Targeted per concern first, then the affected modules
(`test_statistics_core`, `test_stats_annotations`, `test_renderers_m2`, `test_recommendations`,
`test_examples`, `test_reproducibility_export_qc`, `test_loaders`, `test_multisheet_ui`,
`test_controller_workbook`, `test_grouping`, `test_matrix_workflow_core`, `test_matrix_handoff`),
then the full suite.

**pytest result.** Two environments, reported separately because installing an optional extra
changes what runs:

| environment | result |
|---|---|
| Streamlit absent (as delivered) | `1258 passed, 5 skipped`, reproduced across two runs (476 s, 486 s) |
| Streamlit installed | `1264 passed, 3 skipped, 2 failed` (522 s) |

Baseline before any change: `1203 passed, 5 skipped`. **+57 new tests, 0 regressions.**

The two failures appear only once Streamlit is installed, because the tests covering them were being
skipped for a missing import. **Both are pre-existing and neither is caused by this work** — each was
run against the original `7c8b5a5` file and fails identically, with the same error text:

- `test_app_smoke.py::test_app_runs_each_sample_plot_type` — `ValueError: 'barplot_with_error_bar' is not in list` (the app's plot-type list no longer contains internal names)
- `test_streamlit_matrix_wizard.py::test_preprocess_diagnostics_runs` —
  `st.session_state has no key "get"`, which looks like a Streamlit 1.62 incompatibility in the
  test's own mocking; `requirements.txt` only pins `streamlit>=1.30`

They are outside the three concerns and were left alone.

**Skipped tests — skips, not passes:**

| test | reason |
|---|---|
| `test_pop_out_panels.py` | PySide6/Qt unavailable: `libxkbcommon.so.0` missing |
| `test_streamlit_matrix_wizard.py` | `streamlit` not installed |
| `test_app_smoke.py` | `streamlit` not installed |
| `test_count_model_de_optional.py` | optional `count-de` extra (pydeseq2) not installed |
| `test_publication_recreation_pipeline.py` | gapminder already cached; the offline path is not exercised |

`tests/test_desktop_gui.py` was **excluded from collection**, not skipped: it fails at import because
`PySide6.QtTest` cannot load `libxkbcommon.so.0`. It was not run and is not counted as passing.

**Platforms tested.** Linux only — `Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.35`,
Python 3.11.8. **macOS and native Windows were not tested and no claim is made about them.** All
fixes are pure-Python with no platform-specific code, and the new tests are platform-independent, but
that is reasoning rather than evidence.

**Frontends tested.** The shared core was exercised directly and through the GUI-free
`DesktopController`, and for C1 the controller path was shown to produce **identical** limits, labels,
curve count and curve coordinates to the direct core path.

Streamlit was subsequently installed (1.62.0) and the browser app **was** run: it serves, reports
healthy, and its script executes without raising. Streamlit's own `AppTest` harness was then used to
confirm each new control actually appears — the four survival options and the `survival_columns` role
for C1, the annotation-placement selector for C3, column-mapping controls for plot types that
previously had none, PCA's colour/shape controls preserved, and no duplicated widget introduced. The
one duplicate label that remains ("Location", twice) was verified present in the committed
pre-change file and is the Legend and Colorbar expanders sharing a label.

The Qt widget layer still could not be run — PySide6 imports but `QtTest` cannot load
`libxkbcommon.so.0` — so the desktop placement control is covered by parsing and by a StatsSpec
round-trip check rather than by clicking it.

**Unresolved / follow-ups (not fixed here):**

1. **Dunnett's test is not implemented** — needed to match the convention in C3's paper properly.
2. **Statistical annotation is not wired into `lineplot_timecourse_with_error_band`**, so C2's 4E/4F
   cannot carry the paper's paired *t* test on the figure.
3. **`overlay` draws a KDE, not a fitted Gaussian**; C2's paper says "Gaussian distributions".
4. **Partly closed.** `annotation.placement` (C3) now has a control in both frontends, and the C1
   survival options are reachable in both. Still open: `header_fill` (C2) has no GUI control, and the
   **desktop** GUI has no header-row control — its controller accepts both, but adding a Qt widget
   that cannot be exercised in this environment was judged worse than recording the gap.
5. **The browser app's duplicate role table is gone**, which also gave column-mapping controls to
   19 plot types that previously had none in that frontend. Seven other plot types still expose zero
   *options* (`pca_scatter_from_matrix`,
   `oncoprint_mutation_heatmap`, `roc_curve`, `precision_recall_curve`, `upset_plot`, `sankey_plot`,
   `embedding_scatter`) — the same shape of problem as C1's.
6. **Merged-header recovery needs openpyxl**, so legacy `.xls` falls back to pandas' behaviour.
7. **Above-bar labels are not de-collided horizontally**; fine at eight groups, but long text on many
   narrow bars could touch.

**Requires collaborator clarification — one item.** For C1, whether they want the *published curve
redrawn* (now supported, and what `Book4.xlsx` can support) or a *statistical comparison* of the three
groups. The latter needs per-animal data (age at death, 0/1 event, group); no log-rank test can come
from the digitised curve. Both readings are scientifically legitimate, they need different data, and
guessing would either withhold a working feature or invent a statistic — so it is asked rather than
assumed.

**Collaborator data safety — confirmed.** No file under `Concerns/` is tracked or staged
(`git ls-files Concerns/` returns 0; the directory remains untracked). No XLSX, PDF or screenshot is
committed. No collaborator values, gene/genotype tables or private absolute paths appear in any source
file, test or report: one docstring example that had used their column names was rewritten generically,
and two group means quoted in the C2 report were removed in favour of describing the check. Every test
fixture is synthetic and constructed in-test. Figures rendered from collaborator data were written to
a temporary location only and are not committed. The three pre-existing unrelated modifications under
`benchmarks/` were left untouched and excluded from the commit.
