# Does every control actually change the figure?

Reported from the running app: the Palette did nothing on the neighbourhood
enrichment matrix, and the figure-width preset did nothing anywhere visible. Both
were real. Spot-checking was clearly not enough, so `option_efficacy.py` renders
every plot type twice per control — once at the default, once at a changed value —
and compares the pixels.

    python quality_audit/option_efficacy.py              # all 45 plot types
    python quality_audit/option_efficacy.py volcano_plot # one

## What it had to get right first

A naive version of this audit reports a great many bugs that are not bugs. Seven
corrections, every one of them found by chasing a surprising result instead of
believing it. Three were caught only after the audit had already sent agents off
to fix renderers that were never broken.

1. **`Option.scope` is not a PlotSpec address.** This was the worst of them. The
   audit read `scope="style"` as "this value belongs in `spec["style"]`". It does
   not: `OPTION_SCOPES` is documented as *"What a Figure Preset may carry an option
   in"* — a preset-portability class that `presets.split_mapping` uses to sort
   **mapping** keys into portable vs data-bound. Both kinds stay in `mapping`, and
   neither frontend consults `scope` when writing a spec. Values written to
   `spec["style"]` are dropped by `StyleProfile.with_overrides`, which skips keys
   that are not profile attributes — silently. Result: **104 live controls
   condemned**, including the error-bar statistic and every tick-rotation option.
   The tell was in the audit's own output and was missed: `scope="style"` options
   scored **0 effective out of 131**. A control class with a 0% pass rate is a
   broken instrument, not 131 broken renderers.
2. **Byte equality does not work.** Three plot types (`volcano_plot`,
   `network_graph`, `lollipop_mutation_plot`) render differently every time —
   `adjustText`'s iterative overlap resolution converges differently with canvas
   state. On those, *every* control differed and so reported as working: a false
   pass on everything. The audit now measures that drift and only counts a change
   that clearly exceeds it.
3. **An invented key name invents bugs.** An early run asked for
   `layout.axis_label_pad`, which nothing reads, and reported a dead control on 42
   of 45 plot types. The real keys are `x_label_pad` / `y_label_pad`.
4. **Some controls only mean something together.** `explicit_figure_size()` is
   all-or-nothing by design, so patching `width_mm` alone and calling it dead sent
   an agent hunting a bug that was not there. It did sit beside a real one — a
   half-pinned size was being discarded — but the audit has to ask the question
   the code answers.
5. **A test value equal to the default proves nothing.** `column_width: "single"`
   is already the default for several examples; `cluster_legend: "rows"` renders
   exactly like its `"auto"` default when only rows are clustered. Every control is
   now tried with every candidate value and counts as working if any moves the
   figure.
6. **A control needs a precondition met.** The clustered heatmap's example ships
   with `cluster_k_rows = 0`, so it draws no cluster bars and all eight cluster-bar
   controls looked dead — controls that have their own passing tests. `PRECONDITIONS`
   switches the feature on before judging its settings.
7. **A control needs something to act on.** `ax.axison` is the honest test: after
   `ax.axis("off")` matplotlib still reports tick labels with text and still calls
   the spines visible, so asking those questions directly says a chord diagram has
   ticks when it has none. Controls whose target element is absent are reported
   `not-exercised`.

The lesson worth keeping: **a finding is a hypothesis about the harness as much as
about the code.** Every theme this audit produced had to be verified against drawn
geometry before anything was changed, and three of the four largest themes
dissolved on contact.

## Findings

45 plot types, every declared option plus the global style and layout controls:

| verdict | first run (harness still wrong) | after the corrections and the fixes |
|---|---|---|
| works | 867 | **1252** |
| declared unsupported | 55 | 54 |
| not exercised | 76 | 143 |
| **dead — offered and ignored** | **214** | **40** |
| indeterminate (masked by label drift) | 85 | 81 |
| raised on an extreme test value | 9 | 9 |

Most of the drop is the harness learning to ask better questions, not code being
fixed — roughly 150 of the original 214 were never defects. That is the honest
split and it is worth stating plainly, because the first number was circulated
before it had been checked.

Of the nine that raise, eight are the audit's own doing: it tries the end of each
numeric range, and a histogram bin width of 500000 over a range of [5, 46] is
correctly refused. The ninth was real — see `percentile_clip` below.

## Fixed

- **The global Palette did nothing to the enrichment matrix.** Two causes stacked:
  the renderer fell back to a hard-coded `"RdBu_r"` instead of the style's
  diverging colormap, and the bundled example pinned the same value in its
  `spatial` block, where a spec setting correctly outranks a style default. Both
  removed. The publication style's diverging default *is* `RdBu_r`, so the default
  figure is byte-identical (measured 0.000000) and the control now works.
- **All six spatial plot types offered no options whatsoever** — the renderers read
  about nineteen appearance settings each from the `spatial` block, none declared.
  They now have 3–12 each, overlaid so a GUI value outranks the saved file.
- **Nothing in the Figure size panel redrew the preview.** No signal was connected
  to any of the four controls, so the section was inert.
- **Three of four width presets exported at the same size** — `build_spec` mapped
  only `double` separately. Now 110 / 130 / 140 / 180 mm.
- **A half-pinned size was silently discarded** on seven plot types. Pinning a
  width alone — the usual way to fit a figure to a journal column — did nothing.
  New `resolve_figure_size()`; the unpinned dimension keeps its data-driven value
  rather than being stretched, because for a heatmap that dimension is a
  legibility requirement, not a ratio.
- **Sankey's width preset was hard-coded to `"double"`**, so `column_width` was
  read nowhere. Note this *changed a shipped default*: the Sankey example pins
  `column_width: "single"`, which the hard-coded value had been overriding, so the
  example figure moved from 7.09 x 4.39 to 6.00 x 4.00 in. Checked for clipping at
  both sizes; there is none.
- **Spatial point size was unreachable** because every bundled example pins one.
  The global control now *scales* the pinned size rather than replacing it — a
  1.4 pt transcript map should not jump to 45 — so the default is byte-identical
  and the control still moves every mark.
- **An option carried in `spec["style"]` was swallowed without a word**, which is
  the same trap that produced correction 1. Now resolved centrally.
- **`percentile_clip` crashed the feature map** (`object of type 'float' has no
  len()`): the control is one spinner, the renderer wants `[low, high]`. A single
  value now means a symmetric trim from each tail, and `0` means off.

## Decisions taken, worth knowing

- **The enrichment matrix keeps its guide lines.** Deferring to the global grid
  setting would strip them from every figure of this type, since the publication
  profile has `grid=False`, and there is no signal distinguishing "the user
  unticked Grid" from "this profile has grids off". The per-plot Grid option is the
  control, in the same way the clustered heatmap owns its own cell-border settings.
- **`neighborhood_enrichment_matrix` + `column_width` stays dead.** The control is
  read, but a legibility floor of `0.30 x columns + 3.0` = 11.4 in for the
  28-column example exceeds every preset. Making the preset win means redesigning
  that floor and changing default spatial figure sizes.

## Still open

Forty, in small groups: `legend_title_pt` on six plot types; `annotation_pt` on
three that draw their labels outside the normal text path; `y_label_pad` on three;
and a scatter of per-plot options whose preconditions the bundled examples do not
meet (`group_separators` needs column groups, `max_features` cannot bite on a
30-gene example). Each needs a judgement about whether the control or the example
is wrong, which is why none was swept up in a bulk fix.

Two for the author:

1. **`error` is declared `scope="style"`**, so a saved *style* preset carries the
   error-bar statistic. Applying a colleague's "Lab Default Barplot" can silently
   turn SD bars into SEM. That is arguably analysis, not appearance. Changing it
   alters what existing presets carry.
2. **`Option.scope` reads like a block address.** It is a preset-portability class,
   and misreading it as a location is what produced 104 false findings here.
   Renaming it (`preset_scope`) or documenting it on the dataclass would stop the
   next reader repeating it.

This audit is the regression test for all of it: re-run it after any fix and the
verdict column says whether the control is live.
