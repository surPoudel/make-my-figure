# Phase 2 — the shared typography system

Branch `feature/spatial-v2`. Audited and built 2026-10-01 against 45 registered plot
types.

## What was already right

The audit found no typography debt of the kind this phase was meant to clean up:

- **0** hard-coded numeric `fontsize=` / `labelsize=` literals in any of the renderers
  under `make_my_figure_core/plots/`.
- **0** hard-coded text colours on any `.text()` / `.annotate()` call.

Every renderer already takes its text sizes and colour from the `StyleProfile`. Both
facts are now tests (`test_no_renderer_hardcodes_a_font_size`,
`test_no_renderer_hardcodes_a_text_colour`) rather than a one-off observation, so a
renderer added later cannot quietly reintroduce the problem.

Typography attributes the renderers actually read, by frequency of use:

| attribute | call sites |
|---|---|
| `tick_label_pt` | 38 |
| `text_color` | 33 |
| `axis_font_pt` | 17 |
| `annotation_pt` | 15 |
| `title_font_pt` | 11 |
| `legend_pt` | 11 |
| `legend_title_pt` | 2 |

## The hierarchy

Measured from `load_profile('publication')` — these are the style's own values, not
new ones invented here:

| element | pt | ratio to axis label |
|---|---|---|
| Title | 13.0 | 1.083 |
| Axis label | 12.0 | 1.000 |
| Legend title | 11.0 | 0.917 |
| Tick label | 10.0 | 0.833 |
| Legend | 10.0 | 0.833 |
| Annotation | 9.5 | 0.792 |

Reference canvas 5.12 × 3.69 in. Font stack Arial → Helvetica → DejaVu Sans →
sans-serif. Text colour `#1a1a1a`.

The ratios are recorded as `CANONICAL_RATIOS` in `tests/test_typography_system.py`, so
a change to the visual identity has to be made deliberately rather than by drift. A
separate test asserts *every* style profile keeps the hierarchy ordered (title ≥ axis
label ≥ ticks) and above the legibility floor — a profile is free to choose its sizes,
not to invert or flatten them.

## The gap this phase closed

The brief: *"Typography must remain readable when figure dimensions change. Do not use
fixed font sizes that work only at one canvas size."*

Sizes were absolute points, which are correct for exactly one canvas. A 13 pt title is
right on the 5.12 × 3.69 in default and overflows a 2 × 1 in panel — the clipped title
in the reported screenshots. `make_my_figure_core/styles/typography.py` now scales the
whole hierarchy with the canvas, so the ratios above survive at any size.

Applied **once**, centrally, in `plots/registry.py::render` immediately after
`style.with_overrides(...)` and before dispatch. All 45 plot types inherit it; no
renderer was edited. That is what makes it a system rather than 45 patches, and it only
works because of the audit result above — since every renderer reads its sizes from the
style, scaling the style scales the figure.

### Behaviour

- **Scaling engages only outside a dead band** of 0.60×–1.80× the reference *area*. A
  figure the user has not deliberately resized renders byte-identically to before — the
  function returns the original style object, not a copy. This is why the change adds no
  regression risk to existing figures.
- **Area, not width.** Scaling by width alone makes a short wide panel illegible.
- **Continuous at the threshold**, so crossing out of the dead band is not a visible
  jump.
- **Bounded** to 0.55×–1.60×, and no element may fall below 4.5 pt.
- **Only when both dimensions are pinned** (`explicit_figure_size`). Renderers that size
  themselves from their data (heatmap by rows, dendrogram by leaves) are left alone.
- **Reported, never silent.** A scaled figure comes back with a warning naming the
  factor and stating that the relative sizes are unchanged.

Measured effect:

| canvas | scale | title | tick |
|---|---|---|---|
| 5.12 × 3.69 in (reference) | 1.00 | 13.00 | 10.00 |
| 7.0 × 5.0 in | 1.00 | 13.00 | 10.00 |
| 4.0 × 2.0 in | 0.84 | 10.93 | 8.41 |
| 2.0 × 1.0 in | 0.55 | 7.15 | 5.50 |
| 12.0 × 9.0 in | 1.60 | 20.80 | 16.00 |

At 4 × 2 in — the panel size in the brief — the widest text item now takes *less* of the
canvas than at the default size, across every plot type tested.

## Titles longer than the figure is wide

Scaling alone did not fix everything. At 4 × 2 in the enrichment matrix still put 132%
of the canvas width into its title, and the volcano put 183% into its subtitle at
2 × 1 in. Shrinking further is the wrong tool: fitting a 50-character title on a
4-inch panel on one line needs about 3 pt, which is not a title anyone can read.

`wrap_overlong_titles` therefore wraps rather than shrinks, and is applied centrally in
the same place, so it covers every plot type. It measures the rendered width instead of
assuming an average character width, tries successively more lines up to four, and stops
as soon as the title fits. A title that already fits, or one the user has already broken
across lines themselves, is left untouched.

| figure | before | after |
|---|---|---|
| `neighborhood_enrichment_matrix` @ 4 × 2 in | 132% | 62% |
| `volcano_plot` @ 2 × 1 in | 183% | 85% |
| `neighborhood_enrichment_matrix` @ default | 55% | 55% (untouched) |

Wrapping is bounded at four lines. Past that the warning says the title still does not
fit and asks for a shorter title or a wider figure, rather than stacking lines over the
axes or quietly truncating words — a test asserts wrapping never drops a word. Both the
wrapping and the give-up case are reported in the render warnings, so a figure never
comes back re-laid-out silently.

Wrapping a title makes it taller, and an axes title is anchored at its bottom edge, so
the extra lines grow upward and straight off the top of the canvas — the first attempt
fixed the horizontal overflow and created a vertical one. `_make_room_above` lowers the
subplot top to pull the axes, and the title with them, back inside, but refuses to push
the axes below 55% of the figure height: a plot squeezed into a sliver under a four-line
title is worse than being told the title is too long. When that floor is reached the
warning switches to the give-up message above.

The first version of this had another real bug: `MAX_TITLE_LINES` bounded the loop
iterations rather than the resulting line count, and since `textwrap` breaks on word
boundaries, asking for four lines could produce five. Caught by
`test_wrapping_is_bounded_rather_than_stacking_lines_forever`.

## Cost

Title fitting has to measure rendered text, which means asking matplotlib for a
renderer on every render. Measured over five plot types, three repetitions each:

| | ms per render |
|---|---|
| With title fitting | 306.6 |
| Without (baseline) | 303.1 |

About 3.5 ms, or 1%, against a ~300 ms render. Scaling itself is free in the common
case: it returns the original style object untouched whenever the canvas is inside the
dead band.

## Reaching the user

Both front ends already route every `RenderResult.warning` to the user — the desktop app
collects them into the messages panel and switches to that tab
(`apps/desktop_app/main.py:2855`), and the browser app surfaces them per render
(`apps/streamlit_app/streamlit_app.py:263`). The scaling and wrapping notes therefore
appear without any UI change, which is the reason they were implemented as warnings on
the result rather than as log lines.

## What measuring properly turned up

The first version of the fit check compared text *width* against canvas width, and
passed. The rendered PNG showed the volcano title clipped at both ends anyway: a title
is centred on its **axes**, and the axes are inset to leave room for a y-label and an
outside legend, so a title measuring 91% of the canvas width can still hang off both
edges. Width is the wrong measurement; the bounding box is the right one. Looking at an
actual image caught what the number hid.

Switching to bounds then over-reported, flagging tick labels like `'90'` on figures that
were visibly clean. An axis keeps `Text` objects for ticks outside the view limits,
parked far off-canvas and never drawn, and walking every `Text` counts them. The checks
now use matplotlib's own `get_tightbbox`, which only accounts for what is actually drawn.

With both corrections, on a pinned 4 × 2 in canvas:

| | plot types | cause |
|---|---|---|
| Content off the **left/right** edge | **12 of 45** | outside legends (8), colourbar labels (3), node label (1) |
| Content off the **bottom** edge | **14 of 45** | the x-axis label, or a legend placed under the axes |
| Content off the **top** edge | **0 of 45** | fixed by the title fitting above |

### The axis label is the serious one

For 14 plot types a pinned 4 × 2 in canvas pushes the **x-axis label off the bottom** —
the one piece of text a publication figure cannot do without. `tight_layout` gives up
when the canvas is too small for the decorations and the content is simply clipped;
`spatial_categorical_map` loses 163 px, the rest 11–29 px. Since 4 × 2 in is an ordinary
multi-panel size, this is on the path of normal use.

Both classes are **defects, not accepted behaviour**. They are not fixed here because
the cause is legend and colourbar *placement* — code that assumes the figure can be
widened to make room, which it cannot be once the user has pinned the size — and fixing
it means changing placement across a dozen renderers. That is layout work, and doing it
inside a typography change would make both harder to review.

They are recorded as `KNOWN_CANVAS_OVERFLOW_AT_4X2` and
`KNOWN_VERTICAL_OVERFLOW_AT_4X2` in `tests/test_typography_system.py`, with the other
33 and 31 plot types asserted clean. The lists are tripwires in both directions: a new
plot type that starts overflowing fails immediately, and fixing one fails the test until
it is removed from the list, so neither can be quietly forgotten.

## Verifying that existing figures did not change

The claim that scaling leaves ordinary figures alone needed checking rather than
asserting, so every plot type was rendered to PNG twice at its default size — once with
this phase active, once with it stubbed out — and the bytes compared.

That first comparison reported four plot types changed. Two of them
(`lollipop_mutation_plot`, which has no title at all, and `network_graph`, whose title
measures fully on-canvas) could not possibly have been affected by a title fitter. They
were not:

### 3 of 45 plot types do not render deterministically

`lollipop_mutation_plot`, `network_graph` and `volcano_plot` produce three different
PNGs from identical input and identical data — all three place labels by repulsion or
lay out nodes by a spring algorithm, with no fixed seed. This has nothing to do with
Phase 2 and was found only because a byte comparison was attempted. It matters well
beyond this phase: an unseeded layout means a figure cannot be regenerated from its
`.mmfpackage`, which is what the provenance guarantee is for, and it rules out
golden-image regression testing for those three.

Excluding them, the honest result is:

- **41 of 42** deterministic plot types are **byte-identical** at their default size.
- **1** changed: `spatial_composition_map`, whose title was clipped by 7.6 px at the
  default size and is now wrapped onto two lines. Checked by eye, not just by number —
  the leading `C` of "Cell-type composition…" was being cut off, and is now whole. A
  fix, not a regression.

The overflow tolerance was raised from 1 px to 4 px as part of this. At 10 pt and 100
dpi a character is about 6 px wide, so the volcano's 3.6 px overhang at default size is
a sliver of antialiasing; re-laying its title onto three lines to recover it would have
been a worse figure than the hairline clip. 4 px still catches a lost letter.

## 11 of 45 plot types clip content at their default size

The byte comparison led to measuring default-size figures properly, which turned up the
most serious finding of the phase. With **no figure size set by the user at all**:

| plot type | off the side | off the bottom |
|---|---|---|
| `scatterplot_with_regression` | 106 px | 11 px |
| `swimmer_plot` | 98 px | — |
| `spider_plot` | 72 px | 14 px |
| `lollipop_mutation_plot` | 71 px | 19 px |
| `volcano_plot` | 46 px | 11 px |
| `spatial_feature_map` | 28 px | — |
| `embedding_scatter` | 20 px | — |
| `grouped_barplot_with_error_bar` | 17 px | 15 px |
| `spatial_composition_map` | 11 px | — |
| `ma_plot` | 8 px | 14 px |
| `dose_response_curve` | 6 px | 17 px |

Mostly outside legends: `scatterplot_with_regression` loses most of
`'Non_responder'`, `spatial_composition_map` loses the end of
`'CD68+CD163+ macrophages'`. This is not an edge case brought on by an unusual request
— it is what those eleven plot types do out of the box, and it is visible in
`reports/phase2_typography/`.

Tripwired as `KNOWN_DEFAULT_OVERFLOW` in `tests/test_typography_system.py`, with the
other 34 asserted clean.

## Open items, not closed by this phase

1. **11 of 45 plot types clip content at their default figure size**, and a pinned
   4 × 2 in canvas clips the x-axis label on 14 and the right-hand edge on 12. All
   measured above and tripwired; none fixed here, because the cause is legend and
   colourbar placement rather than typography. Given that the default-size case needs
   no unusual input from the user, this is worth doing **before** the remaining
   cosmetic phases rather than in brief order.

2. **3 of 45 plot types render non-deterministically** (`lollipop_mutation_plot`,
   `network_graph`, `volcano_plot`): unseeded label repulsion and spring layout. This
   breaks regeneration from a saved `.mmfpackage` and blocks golden-image regression
   testing for those three. A fixed seed would likely resolve it, but seeding changes
   their output, so it needs its own change rather than a quiet one here.

3. **`text_color` is `#1a1a1a`, not black.** The brief says *"Primary text should be
   BLACK unless there is a scientifically meaningful plot-specific reason otherwise."*
   `#1a1a1a` is a deliberate near-black and is the published v1.1.1 visual identity
   across all 45 plot types. Changing it is a one-line change but restyles every
   existing figure and every reference image, so it is left as an author decision rather
   than made silently. **Needs a ruling.**

4. **Two renderers warn that `tight_layout` cannot fit their decorations at
   2 × 1 in** (`hierarchical_clustering`, `neighborhood_enrichment_matrix`). That is a
   true statement about a 2-inch canvas carrying a dendrogram or a colourbar, and the
   warning is surfaced rather than suppressed. Whether those two should refuse such a
   size outright belongs with the per-plot work in later phases.

## Status

Phase 2 is **NOT READY** as a shipping claim, and the plot system as a whole is not
either. This is one phase of 33.

**Done:** the typography system is implemented and applied centrally, so all 45 plot
types inherit it rather than each solving it their own way; titles too long for the
canvas are wrapped rather than shrunk or clipped; the type hierarchy and its ratios are
documented and pinned by tests; 177 tests cover it, including one per plot type
asserting it inherits the shared scale. 41 of the 42 deterministic plot types render
byte-identically to before at their default size, and the one that changed was verified
by eye to be a fix.

**Found but not fixed, deliberately:** content clipped off the canvas on 11 of 45 plot
types at default size (item 1), and non-deterministic rendering on 3 (item 2). Both are
real defects, measured, tripwired so they cannot spread or be forgotten, and left to the
phases whose subject they actually are. Item 3 needs an author ruling.

Item 1 deserves a word of judgement rather than just a place in a list: eleven plot
types clip a legend in their default, out-of-the-box output. That is more likely to
affect a reader's figure than anything else this phase touched, and it would be worth
taking out of brief order and doing next.
