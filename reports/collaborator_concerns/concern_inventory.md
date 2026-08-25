# Collaborator concern inventory

Local diagnostic notes. Prepared before any code was changed.

The files under `Concerns/` are treated as private diagnostic input: this inventory records their
*structure* and the *published* identifiers already in the associated papers, and does not reproduce
measured values. Nothing from `Concerns/` is copied into tests, fixtures or `examples/`.

Starting repository state: branch `main`, HEAD `7c8b5a5`, three pre-existing unrelated modifications
to benchmark files (left untouched), nothing staged.

---

## C1 — Survival / lifespan curve on a percentage scale, with a log-rank test

**Reported.** The collaborator wanted to reproduce a survival plot (Fig. 1F of PMID 42402962) and
could not. They note the existing Kaplan–Meier plot "is based on fractions of 1 rather than
percentages", so they divided their values by 100 and supplied `Book4.xlsx`, but "did not get a graph
corresponding to the one attached". They ask (i) whether anything is wrong with the workbook,
(ii) for this plot type plus a log-rank test, and (iii) for customizable column headers.

**Expected.** Three lifespan curves on a 0–100 "% survival" axis against age, as in the screenshot:
a 50 % reference line and a single significance annotation for the group comparison.

**Actual.** A near-flat step at S ≈ 0.964 across the whole time axis, on a 0–1 axis, with no warning.

**Supporting files.** `Book4.xlsx` (1 sheet, 28 rows × 4 columns: a time column plus **three columns
all headed `event`**, which pandas disambiguates to `event`, `event.1`, `event.2`; each holds a
monotonically non-increasing series from 1.0 to 0.0). `Screenshot …4.42.55 PM.png` — this is the
**target** figure from the paper, not MakeMyFigure output.

**Diagnosis.** The workbook holds an **already-computed survival curve** — S(t) per group in wide
form — not subject-level time-to-event data. The renderer expects one row per subject with a 0/1
event indicator. Given probabilities, `d = sum((times == t) & (events == 1))` matches only the single
row whose value is exactly 1.0, so one "event" is counted out of 28 rows and the curve never falls
again. Because the workbook's headers happen to equal the renderer's own defaults (`time_months`,
`event`), the mapping auto-resolved and nothing prompted the user to confirm it.

**Subsystems.** Primary: statistics/plotting input contract (shared core) with **no input
validation**. Secondary: plotting (y-axis hard-coded to `0–1.02`, y-label fixed to
"Survival probability"), and UI (`ui_hints.options('kaplan_meier_survival_curve')` returns **zero**
options — no scale, label or reference-line control; median across the 37 plot types is 1, volcano
has 14).

**Scientific risk.** **High.** A meaningless survival curve is produced silently from plausible
input. A user could publish it. Separately, a log-rank test **cannot** be computed from a digitized
curve alone — it needs per-subject event times or at-risk counts — so this part must be answered
honestly rather than implemented on unusable input.

**Release-blocking.** Yes for the silent-wrong-output part.

**Reproduction plan.** Load the workbook, map `time`/`event` to the columns whose names match the
defaults, render, and confirm one event is counted and the curve is flat. Then drive the same
PlotSpec through both frontends' shared path.

---

## C2 — Fig. 4E, 4F and 5B of the muscle-force paper could not be produced

**Reported.** "I also could not find easy ways to generate these types of graphs (from Fig. 4E, 4F,
and 5B …). The corresponding data is attached (Book 5)."

**Expected.** From the paper's own captions:
- **Fig. 4E** — fatigue protocol: force across successive contractions, two genotypes, mean ± SEM,
  n = 9.
- **Fig. 4F** — force–frequency: force against stimulation frequency (Hz), two genotypes,
  mean ± SEM, n = 9. Both analysed by paired *t* test.
- **Fig. 5B** — Gaussian distributions of Feret's minimal diameters for type 2a / 2x / 2b myofibres,
  two genotypes. Analysed by two-way ANOVA.

**Actual.** The data cannot be brought into a plottable shape at all.

**Supporting files.** `Book5.xlsx`, three sheets named exactly `Fig4E`, `Fig4F`, `Fig5B`:
- `Fig4E` — 60 × 19; row 1 carries **merged** group headers over two blocks of nine replicate
  columns; only the first column of each block keeps the label, the rest read `Unnamed: n`.
- `Fig4F` — the real header is on **row 3**, not row 1, and is likewise merged over two blocks;
  read with the default header the sheet is entirely `Unnamed: n`.
- `Fig5B` — 19 929 × 8, a genuine **two-level header** (fibre type on row 1, genotype on row 3) with
  blank spacer columns.

**Diagnosis — and a parser defect found while reproducing.** `load_excel_sheet` and
`preview_excel_sheet` both accept a `header=` argument, `_read_excel` implements it, and the loader
even emits *"Some columns have no header — confirm the header row or choose 'No header'."* But
`load_table` never forwards `header` to `_read_excel` (three call sites pass three positional
arguments), so **selecting a header row has no effect**: `header=0`, `2` and `3` return byte-identical
frames. The advice in the warning cannot be acted on. `_read_delimited` has no `header` parameter at
all, so the same is true for CSV/TSV. On top of that, merged group labels are not carried across their
block, so even the correct header row loses eight of every nine replicate labels.

**Subsystems.** Input parsing (primary, a real defect), then data mapping/reshaping.

**Scientific risk.** Medium. This blocks work rather than producing a wrong number, but the broken
`header` pass-through means a user following the software's own warning gets no change and may
conclude their file is at fault.

**Release-blocking.** Yes — an accepted-but-ignored parameter is a defect.

**Reproduction plan.** Load each sheet at several header rows and show the frames are identical;
then check whether the target plot types (`lineplot_timecourse_with_error_band`,
`ridge_or_density_plot`) can be driven once the header is resolved.

---

## C3 — P-values above each bar, as in Fig. 2F

**Reported.** "I could generate a graph as in this paper attached but it would be [good] if the
P-values could be automatically added on top of each bar as in the graph in Fig. 2F."

**Expected.** From that paper's caption: a mean ± SD bar plot where "the statistical analysis refers
to **the comparison of each RNAi to control mcherryRNAi by one-way ANOVA** (**p < .01, ***p < .001)".
So one marker sits **directly above each bar**, denoting that group versus a single reference group.

**Actual.** MakeMyFigure supports the comparison (`mode: vs_control` with `reference_group` exists in
the StatsSpec) but `plots/stats_overlay.py` can only draw **pairwise brackets**. For a screen with
many groups this stacks one bracket per comparison instead of placing a marker over each bar, which is
both unreadable and not the requested convention.

**Supporting files.** `glag153.pdf` — methodological reference only; no data file was supplied, so
this is reproduced with synthetic data.

**Subsystems.** Annotation (primary). Statistics only insofar as the reference-group comparison must
be the value shown.

**Scientific risk.** Low-to-medium. Nothing is computed wrongly; the risk is that a user hand-letters
p-values onto a figure instead, losing the link between the drawn value and a stored result.

**Release-blocking.** No — a missing feature, not a defect.

**Reproduction plan.** Build a synthetic multi-group bar plot, request `vs_control`, render, and show
the bracket stack. Then add an above-bar placement and verify the annotated value equals the stored
`StatResult` for that group.

---

## Cross-cutting checks to run

- **Multi-sheet rule** (C2): all three sheets listed and selectable, the selected sheet drives the
  analysis, switching sheets clears stale state, worksheet provenance survives into the spec.
- **Feature identity rule** (C1): the three same-named `event` columns must stay three columns.
- **Cross-frontend** (all three): the fixes are in the shared core, so the desktop controller and the
  Streamlit path must agree for the same PlotSpec.
- **Scientific correctness**: any p-value shown must be checked against SciPy/statsmodels
  independently, and the log-rank question in C1 answered on what the input can actually support.
