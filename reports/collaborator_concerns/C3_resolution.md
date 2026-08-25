# C3 — P-values above each bar, as in Fig. 2F

## Concern

"I could generate a graph as in this paper attached but it would be [good] if the P-values could be
automatically added on top of each bar as in the graph in Fig. 2F of the attached article."

The graph itself was already producible. What was missing is the **annotation placement**.

## What Fig. 2F does

From the paper (Rai, Coleman, Curley & Demontis, *J Gerontol A Biol Sci Med Sci* 2026, `glag153`),
Fig. 2E,F: "Representative micrographs (E) and quantification (F) … The graphs display the mean ± SD
with n = 5–14 retinas from independent flies per group. The statistical analysis refers to **the
comparison of each RNAi to control mcherryRNAi by one-way ANOVA** (\*\*p < .01, \*\*\*p < .001)."

So: a mean ± SD bar plot in which every condition is compared against a **single control**, with one
marker sitting **directly above the bar it refers to** and no marker over the control.

No data file was supplied with this concern, so it is reproduced with synthetic data shaped like that
screen: one control plus seven conditions, n = 8 each.

## Reproduction

The comparison itself was already supported — `comparison_mode: "vs_control"` with a
`reference_group` produces one two-group result per condition, and the Benjamini–Hochberg correction
is applied across the family. Rendering that on a bar plot gave:

```
7 results (each condition vs control)
bracket artists drawn : 7
y-axis top            : 483.9
data max              : 169.4
headroom ratio        : 2.86x
```

Opened and inspected: seven brackets stacked one above another fill the upper two-thirds of the
panel and the bars — the data — are compressed into the bottom third. Every bracket also starts at
the control bar, so the same left-hand edge is redrawn seven times. It is legible but it is not the
published convention, and it gets worse with every extra condition.

A separate check ruled out a second suspicion: the BH correction *is* applied. The values live on
`StatResult.adjusted_p_value` (I first probed a wrong attribute name) and match
`statsmodels.stats.multitest.multipletests(method="fdr_bh")` exactly. No defect there.

## Root cause

**Missing feature in the annotation layer, not a defect in the statistics.**

`plots/stats_overlay.py` documents itself as the module that "draws non-overlapping significance
brackets (auto-stacked)" and that was its only output. Every annotated comparison had to become a
bracket spanning two categories, so a set of comparisons that all share one reference could only be
drawn as N−1 stacked brackets. There was no way to say "this label belongs to that bar".

The statistics were correct throughout; the drawing vocabulary was too narrow.

## Code changed

`make_my_figure_core/plots/stats_overlay.py`

- **`annotate_above(...)`** places one label directly over the bar of each compared category, keeps
  the reference bar unmarked, and expands the y-limit by a single text line so nothing is clipped.
  It returns which items it placed and which it could not.
- **`infer_reference_group(items)`** recovers the shared group from the comparisons themselves, so a
  caller that already said `reference_group` in the StatsSpec need not repeat it. It returns `None`
  when the comparisons do **not** share exactly one group — all-pairs comparisons, for example —
  because a label above a single bar cannot say which of two non-reference groups was compared.
  Refusing to guess there is the point.

`make_my_figure_core/plots/stats_integration.py`

- Reads `annotation.placement` (`"bracket"` default, or `"above_bar"`) and dispatches accordingly.
- Anything `annotate_above` could not place **falls back to the bracket engine** rather than being
  dropped, so switching placement can never silently lose a comparison.
- An unrecognised placement raises `StatsError` instead of being ignored.

`make_my_figure_core/statistics/schemas.py`

- `default_annotation()` gains `placement: "bracket"` (unchanged behaviour by default) and
  `above_bar_pad_frac: 0.02`.

The placement lives in the shared overlay engine, so it works for any renderer that already routes
through it — verified on both `barplot_with_error_bar` and `boxplot_or_violin_with_points`.

## Result

```
placement            : above_bar
labels placed        : 7   (one per condition; control unmarked)
reference inferred   : control
bracket artists      : 0
y-axis top           : 191.8
headroom ratio       : 1.13x   (was 2.86x)
```

## Tests added

`tests/test_above_bar_annotation.py` — 16 tests, synthetic fixtures.
**12 of the 16 fail against the pre-fix code and all 16 pass after.**

Coverage: one label over each compared bar and none over the control; no brackets drawn; headroom
demonstrably smaller than the bracket stack (asserted both in absolute terms and relative to the
bracket case); each label sits above *its own* bar's mean and inside the axes; **no two labels
overlap**, checked from rendered text bounding boxes; reference inferred from `vs_control` items;
`None` returned for all-pairs items; all-pairs comparisons fall back to brackets rather than
disappearing; every drawn label equals `render_annotation(stored result)` for `stars`, `p` and
`p_adj` (parametrised); reported p-values match scipy and statsmodels; non-significant comparisons
can be hidden; bracket remains the default; unknown placement rejected; and the placement works on
box/violin as well as bars.

## Scientific validation

The concern is about placement, so the first requirement is that moving a label must not change the
number it shows. Verified against independent oracles:

| input | quantity | expected | observed | difference | tolerance | result |
|---|---|---|---|---|---|---|
| 7 conditions vs control, n = 8, synthetic | Welch *t* p (each) | `scipy.stats.ttest_ind(equal_var=False)` | identical | 0.0 (exact, all 7) | 1 × 10⁻¹² | PASS |
| same | BH-adjusted p (each) | `statsmodels multipletests(fdr_bh)` | identical | ≤ 2.7 × 10⁻²⁰ | 1 × 10⁻¹² | PASS |
| same | drawn label vs stored result | `render_annotation(StatResult)` | identical string, all 7, all 3 content modes | exact | — | PASS |

The last row is the invariant that matters most here: the new placement draws text derived from one
stored `StatResult` each, exactly as the bracket engine does. Nothing is formatted at draw time.

**Methodological difference from the paper, stated rather than glossed over.** The paper reports
"one-way ANOVA" for the comparison of each RNAi to the control, which in practice means an ANOVA
followed by a multiple-comparisons-against-control post-hoc — Dunnett's test. **Dunnett's test is not
implemented in MakeMyFigure** (the 18 available procedures include one-way ANOVA and Kruskal–Wallis
as omnibus tests, and Dunn's test as a non-parametric post-hoc, but no Dunnett). What is available
for "each condition vs one control" is a per-condition two-group test with a multiple-testing
correction across the family, which is a different procedure with a different error-rate argument.

The demonstration above therefore uses Welch's *t* with BH correction and **is not** a reproduction of
the paper's statistic. A figure produced this way should be described by the test actually used, not
labelled "one-way ANOVA". One-way ANOVA is available if the user wants the omnibus result, but
selecting it does **not** produce per-condition comparisons: it is an omnibus-family test, returns a
single result, and `vs_control` does not apply to it — its p-value is surfaced as a corner panel
instead. That behaviour is unchanged and is correct; it is simply not what Fig. 2F shows.

## Visual validation

Both rendered figures were opened and compared.

- **Before** — seven stacked brackets, y-axis inflated to 2.86× the data, bars compressed into the
  lower third, the control edge redrawn seven times.
- **After** — mean ± SD bars using the full panel height, one marker centred over each condition's
  bar and clear of its error bar, the control bar unmarked, no clipping and no overlapping labels.
  This matches the convention in Fig. 2F.

Checked explicitly against the plot-correctness list: category order preserved (control first, as
supplied), each label above the correct category (verified by mapping tick label → position →
stored comparison), error bars unchanged, colours and legend unchanged, no silent filtering of rows.

Both PNGs are synthetic; no collaborator data is involved in this concern. They were written to a
temporary location and are not committed.

## Cross-frontend

The change is in the shared overlay and integration modules and in the shared StatsSpec schema, so
both frontends inherit it; the annotation block is part of the PlotSpec, so it round-trips through
the exported sidecar like any other setting. No frontend-specific code was touched.

## Remaining limitations

- **Dunnett's test is not implemented**, so the paper's exact procedure cannot be reproduced. Adding
  it would be the right way to serve this figure type properly, and is recorded as a follow-up rather
  than approximated.
- **`placement` is not yet a GUI control.** It is available in the StatsSpec and therefore in the
  PlotSpec and its sidecar; adding the checkbox to both frontends' statistics panels is a small
  follow-up.
- **`above_bar` needs a reference group.** With all-pairs comparisons it places nothing and the
  bracket engine takes over — deliberate, since the label would otherwise be ambiguous.
- **Labels are not de-collided horizontally.** The overlap test passes at eight groups because each
  label sits over its own bar, but with very long label text (a full `p = 0.000123` on twenty narrow
  bars) neighbouring labels could touch. The bracket engine has a stagger mechanism for this; the
  above-bar path does not, and a rotation or abbreviation option would be the fix if it comes up.
- **Only comparisons involving the reference are placed above bars**; anything else falls back to
  brackets in the same figure, which is correct but means a mixed request produces a mixed figure.
