# C2 — Figures 4E, 4F and 5B could not be produced from the supplied workbook

## Concern

"I also could not find easy ways to generate these types of graphs (from Fig. 4E, 4F, and 5B of this
paper). The corresponding data is attached (Book 5)."

The concern asks for the *graphs*, not for a reproduction of the paper's statistics. The paper is used
here only to establish what each panel is.

## What the three panels are

From the paper's own captions (Stephan et al., *J Cachexia Sarcopenia Muscle* 2026,
doi:10.1002/jcsm.70220):

| panel | content | form | stated statistics |
|---|---|---|---|
| 4E | fatigue protocol: force over successive contractions, LrpprcWT vs LrpprcP27A | mean ± SEM, n = 9 | paired *t* test |
| 4F | force–frequency: force against stimulation frequency in Hz | mean ± SEM, n = 9 | paired *t* test |
| 5B | Gaussian distributions of Feret's minimal diameters, types 2a / 2x / 2b myofibres | distributions per genotype | two-way ANOVA (Fig. 5 overall) |

`Book5.xlsx` has three sheets named exactly `Fig4E`, `Fig4F`, `Fig5B`, matching the request.

## Reproduction

The blocker is the shape of the sheets, not the plot types — `lineplot_timecourse_with_error_band`
and `ridge_or_density_plot` both already exist.

| sheet | shape | header layout |
|---|---|---|
| `Fig4E` | 60 × 19 | row 1 holds a genotype label **merged** over each block of nine replicate columns |
| `Fig4F` | — | the real header is on **row 3**, also merged over two blocks of nine |
| `Fig5B` | 19 929 × 8 | **two** header rows: fibre type on row 1, genotype on row 3, plus blank spacer columns |

Read with the default header row every sheet came back mostly `Unnamed: n`:

```
Fig4E  ['Unnamed: 0', 'LrpprcWT', 'Unnamed: 2', … 'LrpprcP27A', 'Unnamed: 11', …]
Fig4F  ['Unnamed: 0', 'Unnamed: 1', 'Unnamed: 2', … ]        (all unnamed)
Fig5B  ['type 2a myofibers', 'Unnamed: 1', 'Unnamed: 2', … ]
```

The loader does warn — *"Some columns have no header — confirm the header row or choose 'No header'."*
So the next step is to select a different header row. Doing that changes nothing:

```
Fig4F  header=0 -> ['Unnamed: 0', 'Unnamed: 1', …]
Fig4F  header=2 -> ['Unnamed: 0', 'Unnamed: 1', …]      identical
Fig4F  header=3 -> ['Unnamed: 0', 'Unnamed: 1', …]      identical
Fig4F  header=None -> ['Unnamed: 0', 'Unnamed: 1', …]   identical
```

The same held for CSV input. A user following the software's own advice sees no change and would
reasonably conclude the file is at fault.

## Root cause

**Two defects, both parser bugs.**

**1. The `header` argument was accepted and discarded.** `load_table` declares
`header: Union[int, None] = 0` and `_read_excel` implements it correctly, but the three Excel
dispatch calls in `load_table` passed only three positional arguments — `_read_excel(source,
source_name, sheet_name)` — so the default `0` always won. `_read_delimited` had no `header`
parameter at all, so the delimited path could not honour it either. `load_excel_sheet` and
`preview_excel_sheet` both expose `header=` and both fed the same dead path, and
`info.source_header_row = header` recorded a value that had not been used. Selecting a header row, or
"no header", was inert throughout.

**2. A merged group label survived on only the first column of its block.** Excel stores a merged
range once, in its top-left cell, leaving the rest empty, so pandas reports every later column of the
block as `Unnamed: n`. Eight of every nine replicate labels were therefore lost even once the right
header row could be chosen.

A third, smaller finding came out of rendering panel 5B: `ridge_or_density_plot` is named "Ridge /
density plot" but implemented only the ridge half. With two groups the upper ridge is drawn over the
lower one at the default `overlap=0.7`, so the comparison is hidden rather than shown — the opposite
of what a two-distribution panel needs.

## Code changed

`make_my_figure_core/io/loaders.py`

- `load_table` now forwards `header` on **all six** dispatch paths (three Excel, three delimited).
- `_read_delimited` takes `header`, applies it, and names columns `column_1…N` when `header=None`,
  matching what the Excel path already did.
- New `_normalise_header_rows` validates the argument: an empty sequence and a negative row are
  rejected with a `LoaderError` rather than silently accepted.
- New `_merged_header_grid` reads the worksheet's **actual merged ranges** with openpyxl and expands
  each label across the columns its range covers. This is exact rather than heuristic: the file
  records the span, so nothing is guessed. It returns `None` — falling back to pandas' behaviour —
  for a legacy `.xls`, an unseekable stream, or when openpyxl cannot read the file.
- New `_compose_names` joins the levels into one unambiguous name per column
  (`"type 2a myofibers | LrpprcWT"`), and `_uniquify` disambiguates repeats the way pandas does, so
  nine same-named replicates stay nine distinct columns.
- New `header_fill` parameter, `"merged"` (default) or `"forward"`. The default trusts only recorded
  merges. `"forward"` additionally carries an outer label rightwards across blanks, which is what a
  human reads off a sheet where the author typed the label once without merging. It is **opt-in**
  because a blank header can equally mean "this column has no name", and inferring a span the file
  never recorded would be inventing structure.
- Multi-row headers are supported (`header=[0, 2]`), combined by `_combine_header_rows` when pandas
  produced the MultiIndex.

`make_my_figure_core/io/workbook.py` — `header` annotations widened to accept a sequence;
`load_excel_sheet` forwards `header_fill`.

`apps/desktop_app/controller.py` — `load_workbook_sheet` and `_load_sheet` forward `header_fill`, so
the desktop frontend can reach it.

`make_my_figure_core/plots/ridge.py` — new `density_mode`: `"ridge"` (default, unchanged) or
`"overlay"`, which puts every group on a common density axis with a real "Density" label, a legend,
translucent fills and the outlines drawn on top so an overlapped distribution stays readable.

`make_my_figure_core/ui_hints.py` — `density_mode` exposed as an option.

## Result on the supplied workbook

| sheet | header used | columns recovered |
|---|---|---|
| `Fig4E` | `header=0` | index + **9 `LrpprcWT` + 9 `LrpprcP27A`** |
| `Fig4F` | `header=2` | spacer + `Hz` + **9 + 9** |
| `Fig5B` | `header=[0, 2]`, `header_fill="forward"` | `type 2a/2x/2b myofibers | LrpprcWT / LrpprcP27A` |

n = 9 per group matches the paper's stated n = 9. All three panels then render:

- **4E** — 1 080 long rows (60 contractions × 9 × 2), mean ± SEM band per genotype.
- **4F** — 108 long rows, Hz levels 10/40/80/120/160/200.
- **5B** — 62 545 diameters across three fibre types × two genotypes; overlay density per genotype.

## Tests added

`tests/test_header_row_and_merged_headers.py` — 17 tests, every workbook written in-test with
openpyxl. **15 of the 17 fail against the pre-fix code and all 17 pass after.**

Coverage: header row honoured for delimited text and for Excel; `header=None` gives positional names
on both; empty and negative header specs rejected; a merged label spans its block with distinct
names and no `Unnamed`; an **un**merged blank is *not* given an invented span under the default;
`header_fill="forward"` is opt-in and recovers the visual reading; a two-level header composes both
levels and stays numeric; unknown `header_fill` rejected; an ordinary single-header sheet is
unchanged; worksheet provenance records the chosen header row; end-to-end merged-block → long frame →
grouped line plot with every drawn point checked against the pandas group mean; density overlay shows
both groups from a shared baseline; ridge remains the default; unknown `density_mode` rejected.

## Scientific comparison

The concern asked for graphs, so no statistic is claimed to reproduce the paper. Two checks were run
anyway, because a plot that draws the wrong number is worse than a plot that will not draw.

**Plotted values.** Every point on the 4F line plot was compared against an independent pandas
group mean:

| input | quantity | expected | observed | difference | tolerance | result |
|---|---|---|---|---|---|---|
| Fig4F, LrpprcWT, 6 Hz levels | group mean force | `pandas` group mean | drawn y value | 0.00 (exact) at all 6 | 1 × 10⁻⁹ | PASS |
| Fig4F, LrpprcP27A, 6 Hz levels | group mean force | `pandas` group mean | drawn y value | 0.00 (exact) at all 6 | 1 × 10⁻⁹ | PASS |

All 12 points agree exactly, with n = 9 behind each, and SEM defined and non-zero throughout. The
values themselves are the collaborator's unpublished-to-us copy of the paper's data and are not
reproduced here; the check was run locally and reported as a difference against an independent
computation on the same rows.

**The paper's test.** The paired *t* test the paper used is implemented and was checked against
`scipy.stats.ttest_rel` on a synthetic 9-pair fixture:

| input | method | expected (scipy) | observed | difference | tolerance | result |
|---|---|---|---|---|---|---|
| n = 9 pairs, synthetic | paired *t* | t = 5.286914204245 | 5.286914204245 | 0.0 (exact) | 1 × 10⁻¹⁰ | PASS |
| same | p-value | 0.000739993653941 | 0.000739993653941 | 0.0 (exact) | 1 × 10⁻¹⁰ | PASS |

**Methodological differences from the paper, stated rather than glossed:**

- The paper's 4E/4F statistics are a **paired** *t* test, because the two genotypes were
  electroporated into contralateral muscles of the *same* mouse. The pairing is recoverable from the
  sheet (replicate position within each block), but statistical annotation is **not wired into**
  `lineplot_timecourse_with_error_band`, so no p-value can be drawn on these two panels (see
  limitations).
- Fig. 5B is described as "Gaussian distributions". The overlay mode draws a **kernel density
  estimate**, not a fitted Gaussian. For unimodal data the two look alike, but they are not the same
  thing and the type 2a distribution here is visibly bimodal, so the KDE shows structure a fitted
  Gaussian would smooth away. This is a difference in method, not an error, and is not called a
  reproduction of the paper's panel.
- Fig. 5 as a whole was analysed by two-way ANOVA over fibre type and genotype. That was not run
  here; nothing in this concern required it.

## Visual validation

All three rendered panels were opened and inspected.

- **4F** — monotonic rise to a plateau, WT above P27A, SEM bands overlapping throughout: consistent
  with the paper's "trend toward reduced force … no significant change in the force–frequency".
  Axes, units, legend and group colours correct; no clipping or label overlap.
- **4E** — force declining across 60 contractions, bands overlapping early and separating later:
  consistent with "no significant change in the fatigue protocol".
- **5B** — first rendered in the default ridge mode, where the WT curve **occluded** the P27A curve
  and the comparison could not be read. That is what prompted the `overlay` mode. In overlay both
  distributions are fully visible from a common baseline, the bimodal shape of both is apparent, and
  the two largely superimpose — consistent with the paper's "no significant difference in the size".

Those PNGs derive from collaborator data and were written to a temporary location only; they are
**not** committed.

## Multi-sheet checks

All three sheets are listed and selectable with advisory classifications (`matrix`, `matrix`,
`generic`) and none is withheld. Loading each in turn through `DesktopController.load_workbook_sheet`
gave a different frame each time with no stale carry-over, and worksheet provenance persisted
(`source_sheet_name`, `source_sheet_index`, `source_workbook_name`, `source_workbook_hash`,
`source_sheet_type`) along with the header row actually used. Output slugs identify the sheet
(`Fig4E`, `Fig4F`, `Fig5B`).

## Cross-frontend

The parser and renderer changes are in the shared core. `header_fill` was additionally threaded
through the desktop controller so that frontend can reach it; the Streamlit path calls the same
`load_excel_sheet`. Both frontends read `density_mode` from the shared `ui_hints`.

## Remaining limitations

- **No p-value can be drawn on 4E or 4F.** Statistical annotation is wired into six plot families
  (bar, grouped bar, box/violin, scatter, stacked, survival) and `lineplot_timecourse_with_error_band`
  is not one of them. The paired *t* test itself is available and exact; to annotate it today the
  collaborator would plot a single frequency as a box/violin or paired comparison. Wiring
  per-x-level statistics into the line plot is a genuine feature request, recorded here rather than
  attempted.
- **`overlay` draws a KDE, not a fitted Gaussian.** A "fit a normal distribution" option was not
  added; the paper's wording implies one.
- **Reshaping wide replicate blocks to long form still requires the grouping step.** The columns are
  now named correctly, so `melt_matrix_to_long` can be pointed at them, but the software does not
  infer "these nine columns are replicates of one condition" on its own — deliberately, since that
  is the guess the matrix-workflow rule says must be confirmed by the user.
- **Merged-header recovery needs openpyxl**, so it applies to `.xlsx`/`.xlsm` and not to legacy
  `.xls`, where the loader falls back to pandas' behaviour.
- **`header_fill="forward"` is not yet surfaced as a GUI control** — it is available through the
  controller and the core API. The GUI affordance is a follow-up.
- The desktop GUI layer was not exercised (PySide6 cannot load here); the GUI-free controller was.
