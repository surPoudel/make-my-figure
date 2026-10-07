# v1.2.1 — final report

## Baseline

| | |
|---|---|
| Source | the **v1.2.0 tag**, `420344b` — not `main`, which had moved on |
| Branch | `hotfix/v1.2.1-rendering-builder-state` |
| Plot types | 45 (queried from the live registry) |
| Tests on v1.2.0 | **3957 passed, 3 skipped, 0 failed** |
| Environment | Python 3.11.9, matplotlib 3.10.8, PySide6 6.11.2, WSL2 glibc 2.43 |

## BUG 1 — margins needed several interactions

**Reproduced.** Not signals and not debouncing: one click already produced
exactly one render, and the value already reached the spec.

**Root cause.** The interface and the engine meant opposite things.
`base.py`'s own comment states that right/top are matplotlib *edge positions*
("right=0.75 leaves a quarter blank"); the spin boxes offered them as *insets*
ranged 0.0–0.5. Nudging Right gave `right=0.02` against a left of 0.116,
matplotlib refused the pair, and the refusal was appended to a warning string
that was truncated out of view. Five clicks did nothing; the sixth passed left
and collapsed the plot to a sliver.

**Fix.** Converted at the boundary, with the inverse conversion on load so a spec
saved with `margin_right=0.70` no longer returns clamped to the widget maximum.
Separately, `title_edit`, `xlabel_edit`, `ylabel_edit` and `style_combo` were
connected to **no signal at all** — typing a title drew nothing until an
unrelated control triggered a redraw.

**Validation.** One interaction, one visible change; PlotSpec round-trip no
longer alters a saved figure.

## BUG 2 — Figure Builder did not preserve a finalized plot

**Reproduced and measured** at identical physical size:

| | standalone | builder (v1.2.0) | builder (v1.2.1) |
|---|---|---|---|
| title | 16.48 pt | 20.00 | **16.48** |
| axis label | 14.83 pt | 7.50 | **14.83** |
| tick | 11.53 pt | 6.50 | **11.53** |
| statistics | 10.71 pt | 13.00 | **10.71** |

**Root cause.** Three mechanisms compounded. The builder's font spin boxes always
held a value, so `FigureLayout`'s documented "`None` keeps each panel's own size"
was unreachable from the interface and every panel was restyled on insertion.
Only four of nine typography tokens were overridden, so the title, statistics and
legend heading stayed at full size while the axis labels and ticks dropped —
inverting the hierarchy 2.4×, which is what made text collide. And the
compensating scale pass was switched off whenever overrides were present.

**Fix.** The override group is a checkbox, **off by default**; when used it
replaces the whole hierarchy.

**Whitespace trimming: NOT implemented.** The restyling is fixed, but a separate
"trim panel whitespace" control was not added — see Known limitations.

## BUG 2B — statistics typography

- **The control was dead.** "Annotation font pt" did nothing for the corner
  statistics panel: 6 pt and 20 pt both drew 7.83 pt. The bracket engine honoured
  the setting; the corner panel never read it. Now 6.0 → 6.00, 20.0 → 19.00.
- **`p < 0.` was not a formatting fault.** `format_p` is correct at every default
  (`p = 0.120`, `p = 0.049`, `p < 0.001`). That was a correctly formatted string
  running past the canvas edge, with as little as **26%** visible at a three-up
  panel width. Now 100% visible at 81.3, 60.0, 45.7 and 40.0 mm.
- **One further defect, found by writing the test:** `format_p(0.049, digits=1)`
  returned `p = 0.0` — a significant result reported as none. `digits` is
  settable from 1 in the interface. Now `p < 0.1`.

## BUG 3 — style state leaked into a new plot

**Root cause.** There was no plot-state object. Every plot-local setting lived
only in long-lived Qt widgets that outlive the plot, so nothing ever cleared
them: `reset_to_upload` cleared the data session, and the plot-type widgets were
cleared only because they are destroyed and rebuilt.

**Contract now enforced.** NEW PLOT resets plot-local styling; EDIT preserves it;
LOAD PLOTSPEC and LOAD FIGURE PACKAGE reset and then apply the stored spec
verbatim — loading used to be purely additive, so a spec carrying only margins
came back with the previous figure's palette, font and resolution. Application
preferences are untouched. **File ▸ New plot** added; it did not exist.

**Validation.** Driving the real application: **15 of 15 settings clean, 0
leaking**, where every one leaked before.

## BUG 4 — spatial ROI drew black

**Root cause.** With no `roi_category` mapped, the outline fell back to
`style.text_color` (`#1a1a1a`) for every region and `roi_fill_alpha` defaulted to
0.0, so an ROI table drew as a near-black wireframe. The bundled example only
looked correct because its own PlotSpec pins `roi_fill_alpha`. The three relevant
keys were absent from `GUI_SETTABLE_SPATIAL_KEYS`, so they were unreachable from
either frontend, and the one control that *was* shown (`alpha`) applied to
context points this plot type never receives.

**Fix and validation.** Regions take palette colours and fill by default: 1
near-black outline → **3 distinct colours**. `roi_edgecolor`, `roi_fill_alpha`
and `roi_linewidth` exposed and verified live; the dead control removed.

## BUG 5 — the colour system

**Shared root cause.** The chooser offered the same palette twice: `publication`
and `colorblind_safe` differed at **exactly one of eight entries**, so any figure
with six categories or fewer was pixel-identical between them — measured on **40
of the 45 plot types**. Index 0 across the four palettes was blue, blue, black,
black, which is precisely "only colorblind-safe or black works", since several
plots use only index 0.

**Second cause.** `beeswarm` and `dot_strip` rejected a colour column that named
the x column — colouring by the grouping variable, the obvious request — and
their fallback drew every group in one colour. `barplot` has the same guard but
falls back per category, which is right: one rule, three spellings.

**Fixes.** `colorblind_safe` is now a distinct colourblind-safe scheme; old specs
naming `nature_like` still resolve to Okabe-Ito. Beeswarm and dot/strip: **1
colour → 3**, with 3 legend entries.

**Per-artist colour pickers** (author's request), following the volcano's
existing pattern, all verified to change the figure:

| plot | pickers |
|---|---|
| calibration | curve, point, point outline |
| Bland-Altman | point, mean-difference line, confidence band |
| Q-Q | point, point outline |
| forest | estimate marker, confidence interval |
| dendrogram | branch |

Two were dead on first test and were fixed rather than shipped: the Q-Q p-value
branch hard-coded `edgecolors="none"`, and the Bland-Altman band is gated on
`show_ci`.

**Capability truthfulness.** Those five plots now declare
`supports_group_colors=False` with a reason, so the palette's categorical meaning
is explained rather than silently inert. An earlier attempt declared
`supports_palette=False`, which the project's own capability audit correctly
rejected — those renderers still take their single accent from palette index 0.

**Complete audit: 119 colour controls across all 45 plot types** →
`palette_contract.csv`.

## BUG 6 — Matrix Workflow PCA ignored confirmed groups

**Root cause.** Grouping depended on *which of two recommendations was clicked*
rather than on the data: "PCA scatter" sits at position 5 of the list and "PCA
colored by group" last at 13. The plain entry also shipped an empty `aux`, so the
editor's metadata menus were empty and the grouping could not be restored by hand.

**A worse fault underneath.** The renderer restricted samples to those listed in
the metadata **before** the decomposition. Supplying a group column therefore
silently deleted samples and changed the analysis: dropping one sample of six
moved PC1 for the rest by about **20%**, and four missing raised "need >= 3
numeric sample columns". Only non-numeric annotation columns are dropped now;
unlisted samples are kept, drawn as `Unassigned`, and counted.

**Sample identity** was already matched by sample ID, not row position — verified
under interleaved matrix columns and shuffled metadata rows, and now covered by a
regression test so a refactor cannot reintroduce positional matching.

**Validation.** 2, 3 and 4 groups each produce that many colours and legend
entries; coordinates are invariant to grouping (`max|delta| = 0.0`).

## Full gallery

| | |
|---|---|
| Registered plot types | **45** |
| Audited | **45** |
| Clean | **45 of 45** |

Each: render, publication-style render, PNG/SVG/PDF export, PlotSpec round-trip
and Figure Package round-trip, all producing an identical figure.

## Tests

- **22 new permanent regression tests**, one per defect, each failing on v1.2.0.
- Serial suite (as CI runs it): **3979 passed, 3 skipped, 0 failed**.
- Parallel suite (12 workers): identical result in 5m05s vs 37m52s.

## Visual QC

45 plot types rendered and measured for clipped and overlapping text; the Figure
Builder compared against standalone at identical dimensions across title, axis
label, tick and statistics sizes. Two false alarms in the audit harness itself
were traced and corrected: the reference digest had been taken *after* exporting,
and exporting re-draws a figure, re-running the label-refit callbacks.

## Packaging

| Artifact | Platform | Arch | SHA-256 |
|---|---|---|---|
| `MakeMyFigure-1.2.1-Setup.exe` | Windows `windows-2025-vs2026` | x86_64 | `a20f044d66d2eaad…` |
| `MakeMyFigure-1.2.1-windows.zip` | Windows | x86_64 | `1441c8918172608c…` |
| `MakeMyFigure-1.2.1.dmg` | macOS `macos-26-arm64` | **arm64** | `515ecd561b6f089f…` |
| `MakeMyFigure-1.2.1.AppImage` | Linux `ubuntu-22.04` | x86_64 | `fa7a639074675fe4…` |
| `MakeMyFigure-1.2.1-linux-x86_64.tar.gz` | Linux | x86_64 | `6cdefdc12af095f1…` |
| `make_my_figure_core-1.2.1-py3-none-any.whl` | any | any | `5833dd2a32272cc0…` |
| `make_my_figure_core-1.2.1.tar.gz` | any | any | `69a286e1a0928714…` |

All five platform artifacts built by one Actions run (`37569012996`) from commit
`4812f2f` — verified per job through the API, not assumed — and smoke-tested on
the runner that built them. Every published digest was re-verified by downloading
the asset and hashing it locally: **7 of 7 match**.

## Release

| | |
|---|---|
| Commit | `4812f2f` |
| Tag | `v1.2.1`, annotated |
| URL | https://github.com/surPoudel/make-my-figure/releases/tag/v1.2.1 |
| **v1.2.0** | **unchanged at `420344b`, still published** |

## Forward merge

Not yet performed. `main` is ahead with post-v1.2.0 work (label fitting,
axis-label clearance, stats-box placement). The hotfix must be merged forward so
these defects cannot return; that merge is a separate step and is listed below.

## Known limitations

1. **Figure Builder whitespace trimming was not implemented.** The brief asked
   for a "trim panel whitespace / fit content" concept kept separate from style.
   The restyling defect is fixed, but no such control was added. The underlying
   two-pass render — where pass 1's *trimmed* aspect sizes a box that pass 2 fills
   *untrimmed*, changing a panel's aspect by up to 20% when height is "auto" —
   remains.
2. **Windows and macOS were not validated interactively.** Each artifact was
   built and smoke-tested (`--selftest`, plus an `xcb` check under `xvfb` on
   Linux) on its own runner, but no person launched them, clicked through and
   exported a figure.
3. **The macOS artifact is arm64 only.** No x86_64 macOS build is produced, and
   the README install table does not say so.
4. **Three continuous plots** (confusion matrix, enrichment dot plot, spatial
   feature map) show no change between two palettes, because the palette selects
   a colormap and two palettes can resolve to the same one. Pre-existing,
   correctly declared non-categorical, not changed in a patch release.
5. **A panel still stores a PlotSpec, not a frozen resolved style.** Parity now
   holds because the builder no longer overrides fonts, which is the right fix
   for this release; freezing the resolved style on the panel would make parity
   structural rather than behavioural.
6. **Tutorial screenshots are now stale** wherever they show the Figure Builder
   font group (now a checkbox, off by default), the margin controls, or the
   spatial ROI plot. The tutorial branch is untouched, as instructed.
