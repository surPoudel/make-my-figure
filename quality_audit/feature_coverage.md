# Does every visual decision have a control?

The option audit answers a narrower question: does every control that *is* offered
actually change the figure. It cannot see a feature the renderer decides for
itself — a dash pattern, a grey, a bar width, a pad baked into the source with no
way to reach it. Those are the figures an author cannot finish without editing
Python, and they are the gap between "the controls work" and "you can control the
figure".

    python quality_audit/feature_coverage.py
    python quality_audit/feature_coverage.py volcano_plot --verbose

## Result

| | first run | now |
|---|---|---|
| appearance literals in drawing calls | 126 | 65 |
| with a plausible option | 81 | **65** |
| **with no control** | **45** | **0** |

The literal count drops as well as the uncovered count, because several of the
fixes replaced a literal with a resolver rather than adding an option beside it.

## What it deliberately does not flag

A literal is not automatically a missing control, and flagging every number in a
renderer produces a list nobody can act on. Excluded, each with the reason in the
source:

* **`interpolation="nearest"`** on a heatmap. A heatmap cell *is* a datum;
  offering smoothing would let an author blur measured values into a picture that
  implies data between the samples. That is a correctness decision the tool
  should keep making, not a style choice.
* **`ha` / `va`**. These place text relative to its own anchor — how a label is
  attached, not how it looks. Exposing them produces labels that drift off what
  they annotate.
* **`grid` and `tick_params`**. Governed by the global Grid control and the style
  profile. Per-plot grid dash patterns would be four more ways for one figure set
  to disagree with itself.
* **Structural arguments** (`zorder`, `transform`, `clip_on`, `label`, …) and the
  values `0`, `1`, `"none"`, `None`, `"auto"`, which mean "off" or "absent".

## What was added

**Reference and threshold lines — 13 sites across 9 plot types.** A volcano's
fold-change cutoffs, a ROC diagonal, a Bland-Altman limit of agreement, a
waterfall's response thresholds, a forest plot's null line. Every one had both the
dash pattern **and** the grey hard-coded. Now `reference_line_style` and
`reference_line_color`, resolved by one shared helper. Two plots keep a
considered default through it: the Bland-Altman limits stay on the palette colour
(they are a related pair, not a neutral reference) and the precision-recall
baseline stays dotted (it marks prevalence, not a target) until an author
overrides them.

**Bar thickness — 6 sites across 5 plot types.** Each bar-shaped plot had its own
number from 0.6 to 0.85, none reachable, so the gap between bars — which is most
of what makes a grouped figure readable — could only be changed in Python. One
`bar_width` control, where `0` means "keep this plot's own default", because 0.6
for an UpSet matrix and 0.85 for a waterfall are considered choices rather than
accidents.

**Point outline colour — 3 plot types.** The style already carried the outline
*width* but never its colour, so three renderers hard-coded one: white to
separate overlapping points, black to weight an estimate. Both are legitimate;
neither should be the only option. `marker_edge_color`, with `auto` meaning "what
this plot already did".

**Colourbar geometry — 3 sites across 2 plot types.** Same `colorbar_pad` /
`colorbar_fraction` names the clustered heatmap already used, so there is one
vocabulary.

**`bold_cluster_labels`** on the embedding scatter, and **a real bug**: the forest
plot hard-coded `capsize=2.5` while `style.errorbar_capsize` already existed and
was simply not being read.

## Two things found on the way

**Three duplicate keys in `OPTIONS`.** `paired_slopegraph`, `manhattan_plot` and
`swimmer_plot` each appeared twice in the same dict literal — an empty
placeholder shadowed by the real entry later. Harmless while they stayed empty,
since Python keeps the last, and a trap the moment anyone adds an option to the
first one. Which is exactly what happened here: the point-outline control was
declared, the UI never showed it, and nothing complained. The placeholders are
gone and two tests now guard it — no duplicate keys, and every declared option
reachable through `ui_hints.options()`.

**Two controls removed rather than shipped dead.** `colorbar_pad` is *not*
offered on `embedding_scatter` or `network_graph`: both call `tight_layout()`
after creating their colourbar, which recomputes every axes position and discards
the pad. The control would have been visible and done nothing — worse than its
absence. Making it real there means reordering their layout, which moves the
colourbar on every existing figure of those types, so it is written down here
instead.

The same reasoning removed a `reference_line_style` declaration from
`enrichment_dotplot`: its dotted line is the **grid**, not a reference line, and
the global grid control governs that.

## Still not covered by this audit

It reads keyword arguments to drawing calls. It does not see:

* **positional** styling arguments;
* values computed just above the call and passed by name;
* **thresholds and defaults that are scientific rather than visual** — the
  waterfall's RECIST response lines are drawn at a hard-coded +20 / −30, which
  are clinical conventions an author may legitimately need to change, and no
  keyword-argument scan will find them.

That last one is the next gap worth closing, and it matters more than anything
this pass fixed: a hard-coded number that changes what a figure *claims* is a
worse defect than one that changes how it looks.
