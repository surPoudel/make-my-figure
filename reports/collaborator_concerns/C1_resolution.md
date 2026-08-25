# C1 — Survival / lifespan curve: percentage scale, log-rank, customizable headers

## Concern

The collaborator wanted a lifespan figure like Fig. 1F of PMID 42402962 and could not produce it.
They observed that the existing Kaplan–Meier plot "is based on fractions of 1 rather than
percentages", divided their values by 100, supplied `Book4.xlsx`, and still "did not get a graph
corresponding to the one attached". They asked whether the workbook was wrong, for a log-rank test,
and for customizable column headers.

## Reproduction

`Book4.xlsx` has one sheet, 28 rows × 4 columns: a time column and **three columns all headed
`event`**, which pandas disambiguates to `event`, `event.1`, `event.2`. Each of the three holds a
monotonically non-increasing series running from 1.0 down to 0.0 — that is, an **already-computed
survival function S(t)**, one column per group, digitised from the published figure. It is not
subject-level time-to-event data.

Mapping `time → time_months` and `event → event` and rendering produced:

```
metadata groups : {'all': {'n': 28, 'events': 1}}
curve y-range   : 0.9643 … 1.0        (essentially flat across the whole time axis)
warnings        : []                  <- nothing said
```

Visually: a single step down at t = 0 and then a horizontal line at S = 0.964 for 47 months. That is
exactly the collaborator's report, and it is worse than an error because the figure looks finished.

The workbook's headers happen to be *identical to the renderer's own defaults* (`time_months`,
`event`), so the mapping auto-resolved and nothing ever asked the user to confirm it.

## Root cause

**Faulty assumption plus absent input validation** (shared core, `plots/survival.py`).

`_km_estimate` counts events with `d = sum((times == t) & (events == 1))`. Given survival
probabilities, the only row matching `events == 1` is the single t = 0 row where S = 1.0. So one
event was counted out of 28 rows, the estimator stepped once to 27/28 = 0.9643, and never moved
again. The renderer accepted any numeric column as an event indicator and reported no warning.

Three contributing defects, all in the same file:

1. no check that the event column is a 0/1 indicator;
2. the y-axis was hard-coded `ax.set_ylim(0, 1.02)` with the label fixed to "Survival probability",
   so a percentage axis was impossible;
3. there was no input form for an already-computed curve at all.

A fourth, separate finding explains the "headers are fixed" remark: `ui_hints.options()` returned an
**empty list** for this plot type — it exposed *no* user-facing options whatsoever (the median across
the 37 plot types is 1; volcano has 14). Column *roles* were always free-form, but there was no
control for scale, label or anything else, so the plot felt hard-wired.

## Code changed

`make_my_figure_core/plots/survival.py` (rewritten)

- **Two input forms.** `input_form: "subject_level"` (default, unchanged behaviour) and
  `input_form: "precomputed"`, where `survival` (one column) or `survival_columns` (a list, one per
  group) holds S(t) and is drawn as supplied without re-estimation.
- **Event-indicator validation** (`_resolve_event_indicator`), which separates three cases instead
  of lumping them:
  - already 0/1 → used as is;
  - exactly two distinct values, e.g. the 1/2 coding R commonly emits → the larger is taken as the
    event **and the choice is reported in a warning**, rather than silently counting only the 1s;
  - more than two distinct values → `RenderError`. When the values sit in [0, 1] and never increase
    — the collaborator's case — the message says the column looks like a survival curve and names
    `input_form='precomputed'` and `survival_columns` as the fix.
- **`y_scale`**: `"fraction"` (0–1, default) or `"percent"` (0–100), which scales the plotted values,
  sets the y-limit, and defaults the y-label to "Survival probability" or "% survival". Applies to
  both input forms.
- **`reference_line`**: an optional dotted horizontal line in the units of the axis (50 on a percent
  axis), matching the 50 % guide in the target figure.
- **`group_labels`**: names the curves independently of the spreadsheet headers, which is what makes
  `event`/`event.1`/`event.2` presentable without editing the data.
- **`curve_style`**: `"step"` (default, and the only correct choice for an estimated curve) or
  `"line"`, accepted **only** for the precomputed form; requesting `line` on an estimated curve
  warns and falls back to `step`.
- **Statistics honesty**: in precomputed mode a requested test is not run, and a warning states that
  a log-rank test needs per-subject event times or at-risk counts, neither of which can be recovered
  from a curve.
- **One source of truth for the event indicator.** The resolved 0/1 values are written back into the
  mapped column of the renderer's own copy, so the statistics runner — which looks the column up by
  name — tests exactly what was drawn. Without this a 1/2-coded input would have drawn one curve and
  reported a different test.

`make_my_figure_core/ui_hints.py`

- `column_fields` gains `survival_columns`; `options` gains `input_form`, `y_scale`,
  `reference_line`, `curve_style`.

`apps/streamlit_app/streamlit_app.py`

- **Correction to an earlier claim in this report.** Adding the options to `ui_hints` surfaced them
  in the desktop app, which reads that registry, but *not* in the browser app, which kept its own
  hardcoded copy of the role table. That copy had drifted to 18 of the 37 plot types, leaving 19 with
  no column-mapping controls at all. The app now calls `ui_hints.column_fields()` (with a documented
  additive override for the PCA colour/shape roles it offers on top) and renders any registered
  option that no other section already owns. All four survival options and the `survival_columns`
  role are now reachable in the browser, verified with Streamlit's own `AppTest` harness.

The renderer still copies before modifying, so the caller's DataFrame is untouched (asserted).

## Tests added

`tests/test_survival_input_forms.py` — 20 tests, all fixtures synthetic and built in-test.
**16 of the 20 fail against the pre-fix code and all 20 pass after**; the 4 that passed before cover
behaviour that already worked (notably the log-rank agreement) and are kept as guards.

Coverage: the reported failure raises with actionable text; many-level columns refused; precomputed
mode draws one curve per column; repeated headers stay three distinct curves; missing survival column
refused; increasing curve warns; log-rank refused in precomputed mode; `y_scale` limits and labels
(parametrised); percent applied to estimated curves; reference line in axis units; `group_labels`
without mutating input; 1/2 coding reported and counted correctly; recoded events give an identical
log-rank; log-rank vs statsmodels; `curve_style` guard both ways; bad `input_form`/`y_scale`
rejected; options exposed to the frontends; and a PlotSpec round-trip through the exported sidecar.

## Scientific validation

**Log-rank test, independently checked against `statsmodels.duration.survfunc.survdiff`** (lifelines
is not a dependency and is not installed):

| input | method | expected (statsmodels) | observed (MakeMyFigure) | difference | tolerance | result |
|---|---|---|---|---|---|---|
| 2 groups, n = 120, 87 events, synthetic | log-rank χ² | 5.052485463752 | 5.052485463752 | 2.3 × 10⁻¹⁴ | 1 × 10⁻¹⁰ | PASS |
| same, p-value | log-rank p | 0.0245906399326 | 0.0245906399326 | 3.2 × 10⁻¹⁶ | 1 × 10⁻¹⁰ | PASS |
| 3 groups, n = 150, synthetic | log-rank χ² | 2.738304893373 | 2.738304893373 | 3.1 × 10⁻¹⁵ | 1 × 10⁻¹⁰ | PASS |
| 2 groups, event coded 1/2 vs 0/1 | log-rank χ² | 2.733410754688 | 2.733410754688 | 0.0 (exact) | 1 × 10⁻¹² | PASS |

Agreement is to the limit of double precision but is **not exact**, so it is reported as a
difference rather than as equality. Event counts under 1/2 coding were checked against ground truth
and matched exactly (30 and 33).

**On the collaborator's log-rank request:** the test was already implemented and correct. It cannot
be applied to `Book4.xlsx` as supplied. A log-rank statistic is accumulated over event times from
the number at risk and the number of events in each group at each time; a digitised S(t) curve
determines neither. Dividing by 100 does not change this — the issue is the *kind* of data, not its
scale. To obtain a log-rank test the collaborator needs one row per animal with its age at death and
a 0/1 indicator (1 = died, 0 = censored/alive at the end) plus a group column; the software then
computes both the curves and the test. This is stated in the software's own warning rather than left
for the user to discover.

## Visual validation

Rendered from the collaborator's workbook in precomputed + percent mode with a 50 % reference line
and the three curves labelled, then opened and compared against their screenshot of the target
panel. Verified: y axis 0–100 labelled "% survival"; x axis labelled "age (days)"; three curves
present and distinguishable; the same curve separates downward earliest and crosses 50 % at ≈ 28–29
while the other two cross at ≈ 31–33, reproducing the ordering and crossing points of the target;
dotted 50 % guide at the right height; all curves reach 0; no clipping, no overlapping labels, legend
clear of the data.

Also inspected: the *pre-fix* output (flat line) to confirm the reported symptom, and a synthetic
subject-level curve on both fraction and percent axes to confirm censoring ticks still land on the
step they belong to.

Those PNGs derive from collaborator data and were written to a temporary location only; they are
**not** committed.

## Cross-frontend

The renderer fix is in the shared core, so both frontends inherit it. Reaching the *options* needed a
second change: the desktop reads `ui_hints` and picked them up, the browser app did not until its
duplicate role table was replaced (above). Both were then verified rather than assumed: for the same mapping, `DesktopController.build_spec` +
`.render` and the direct `registry.render` path produced identical y-limits, y-label, x-label, curve
count, `y_scale`, input form, **and identical curve coordinates**. Both frontends build their control
panels from `ui_hints`, which now reports 4 options and 4 column roles for this plot type.

## Remaining limitations

- **A log-rank test is impossible from a precomputed curve.** This is a property of the data, not a
  gap to be closed. The software now refuses and explains instead of returning a number.
- **`curve_style="line"` interpolates.** It exists so a digitised curve can be drawn the way its
  source figure was drawn; it is not offered for estimated curves.
- **No confidence bands and no at-risk table.** Neither was requested; both would need subject-level
  input.
- **Number-at-risk cannot be inferred** in precomputed mode, so censoring ticks are not drawn there —
  correctly, since the input does not record censoring.
- **The desktop GUI layer was not exercised**: PySide6 cannot load in this environment
  (`libxkbcommon.so.0` missing), so `tests/test_desktop_gui.py` is not collected here. The GUI-free
  controller *was* tested, and it is the controller that holds the logic.
- The collaborator's remark that headers are "fixed" was partly a misreading — any column could
  always be mapped to any role — but the underlying complaint was real: this plot type exposed no
  options at all. Seven other plot types still expose none (`pca_scatter_from_matrix`,
  `oncoprint_mutation_heatmap`, `roc_curve`, `precision_recall_curve`, `upset_plot`, `sankey_plot`,
  `embedding_scatter`); that is recorded as a follow-up rather than fixed here.
