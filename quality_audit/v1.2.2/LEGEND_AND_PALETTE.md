# Legend positioning and colour customization

Branch `feature/legend-and-palette-controls`, off `fix/figure-builder-alignment`
at `7413b63` — the branch under test. `main` (`da7614d`) carries none of that
work, so branching there would have meant developing against a base the author
is not using.

45 plot types registered; 45 have bundled examples and all 45 were audited.

## What was wrong, measured before anything was changed

| | before | after |
|---|---|---|
| legend offset / gap / padding | **no control existed** — location only | seven controls, offset exact to **0.00 pt** on every plot that draws a legend |
| MA plot Up / Down colours | **no control** — palette slots 1 and 0 | `color_up` / `color_down` / `color_ns`, defaults unchanged |
| Bland–Altman limits of agreement | one shared colour for both limits | independent, still matching by default |
| Bland–Altman observations | no way to mark points outside the limits | optional agreement categories, counts in the metadata |
| UpSet bars | **no colour control at all** | set bars, intersection bars and membership dots, independently |
| 10 groups on an 8-colour palette | two groups silently got one colour | reported, with palettes that would fit |
| per-category colour | **no mechanism existed** | by position (every plot type) or by name |
| palette chooser | 4 palettes, no kinds | grouped qualitative / sequential / diverging / grayscale |

Reported line-colour controls on Bland–Altman (`point_color`, `bias_line_color`,
`ci_band_color`, `reference_line_color`) were **not** reproducibly ignored: all
four already reached their artists, measured. What was missing is listed above.

## Audit: every registered plot, every control it declares

`styling_audit.py` asks each plot type only what its capabilities say it has, and
then checks the control did it. **45 of 45 clean.**

| check | result |
|---|---|
| renders | 45 / 45 |
| legend offset moves the legend by what was asked (±1 pt) | 27 pass, 9 draw no legend in their example, 9 declare no legend |
| palette change alters the drawn colours | 44 pass, 1 n/a |
| one category's colour reaches that artist | 33 pass, 12 have no categorical colour |
| **every numeric field of the render metadata identical under styling** | **45 / 45** |
| PlotSpec → JSON → render gives the same figure | 45 / 45 |
| PNG + PDF + SVG export | 45 / 45 |
| two exports byte-identical | 45 / 45 |

Category counts, on the two plot types that take a grouping column:

| groups | 2 | 3 | 5 | 10 |
|---|---|---|---|---|
| distinct colours | 2 | 3 | 5 | 8 of 10, **warned**, alternatives named |

`tab20` renders the same 10 (and 14) groups with no repeats and no warning, so
the suggestion is checked rather than assumed.

## Regression tests added

| file | tests | covers |
|---|---|---|
| `tests/test_legend_geometry.py` | 23 | offsets in points, gap, padding, no-relocation, round trip, preset portability, controls hidden where there is no legend |
| `tests/test_semantic_class_colors.py` | 18 | MA / Bland–Altman / UpSet classes, label wording, counts and statistics unchanged |
| `tests/test_palette_system.py` | 21 | 2 / 3 / 5 / 8 / 10 / 14 categories, capacity warning and its alternatives, overrides by name and position, the catalogue |

Full suite: **4084 passed** under `-n 12`; the one failure is
`test_pop_out_panels`, which crashes an xdist worker on Qt and passes serially.

## Visual QC

`quality_audit/v1.2.2/visual_qc/` — four contact sheets, for the things a
measurement cannot judge:

* `01_legend_geometry.png` — offsets, an outside legend that stays outside, gap, padding
* `02_class_colours.png` — MA, Bland–Altman and UpSet, default beside recoloured
* `03_category_capacity.png` — 2 / 3 / 5 / 10 groups, and the suggested palettes
* `04_colour_kinds.png` — categorical, named override, sequential, diverging

## Unresolved and deliberately not changed

* **A 110-dpi preview and a 300-dpi export differ in fine text placement** on the
  two label-repelling plot types. Text fitted to its axes is fitted for the size
  it is drawn at; within one output size the result is deterministic and two
  exports are byte-identical. Pre-existing and by design, recorded here because
  the audit meets it.
* **9 plot types draw no legend in their bundled example** (bar, box, beeswarm,
  dot strip, histogram, paired slopegraph, forest, QQ, heatmap). They declare
  `supports_legend` correctly and get one when the data has groups; the audit
  cannot exercise the offset on an example without one.
* **`handlelength` is settable in the PlotSpec but not in the desktop panel** —
  six legend geometry rows is already a lot of UI for one group.
* **The Streamlit app has no widgets for the new controls.** It honours them when
  a spec carries them; adding the controls there is separate work.
