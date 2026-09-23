# Slide visual review - deck of 2026-09-22 (16 slides)

Test applied to each slide: *projected in a conference room, can someone at the back
understand the visual?* Renders reviewed at 1600 x 1200 (`tutorial/slides/_render/`).

| # | title | purpose | main message | visual hierarchy | plot readability | font readability | screenshot usefulness | white space | contrast | crowding | accuracy | demonstrates a capability? | back-of-room test | classification |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Make My Figure (title) | open | data table to publication figure | good | n/a | good | n/a | good | good | low | good | n/a | yes | KEEP |
| 2 | The problem this solves | motivate | scientists want to open, map, plot, test, record | weak: two small pictures compete with five bullets | weak (scatter 4.6 in wide, axis text unreadable) | good | table crop unreadable | adequate | good | high | good | no | NO | REDESIGN: one large before/after visual + one line |
| 3 | What Make My Figure is | describe | seven bullets | weak | weak (full window shrunk to 5.3 in) | good | miniature | adequate | good | high | good | no | NO | SPLIT: capabilities list (text only) + one large workspace slide |
| 4 | Design principle | philosophy | proposes / you decide / records | good | n/a | good | n/a | good | good | low | good | yes | yes | KEEP |
| 5 | Demo 1 table | mapping | detected types, cards | weak | n/a | good | full window shrunk to 7.2 in: unreadable | adequate | good | medium | good | partly | NO | REDESIGN: 5-8 row table excerpt + enlarged recommendation card + mapping rows |
| 6 | Demo 1 correct + second plot | mapping | one table, several plots | adequate | weak (box 5.5 in with 8 px text; scatter 2.3 in tall) | good | mapping crop good | adequate | good | medium | good | yes | NO | REDESIGN: two large exported plots side by side, mapping crop as inset |
| 7 | Demo 2 volcano | manual mapping | roles assigned by hand | weak | weak (two full windows at 5.5 in) | good | miniature | adequate | good | high | good | yes | NO | SPLIT: (a) the (none) state with the Messages text enlarged; (b) large refined volcano vs default |
| 8 | Statistics | statistics | chosen by you, documented | adequate | adequate (box figure 5.6 in; P labels ~9 px) | good | statistics panel at 5.4 in wide is readable | adequate | good | medium | good | yes | borderline | MINOR FIX: plot larger (7 in), panel crop of the settings + table only, bullets to two |
| 9 | Figure presets | presets | style travels | weak | weak (two full windows) | good | miniature | adequate | good | high | good; only user presets | partly | NO | REDESIGN: same data, default vs publication preset, large; second slide for Preview & apply |
| 10 | Reproducibility | packages | PlotSpec vs package | weak | weak (full window 7.4 in) | good | confirmation dialog readable; window not | adequate | good | high | good | yes | NO | REDESIGN: confirmation dialog large + package contents list; drop the window |
| 11 | Figure Builder | builder | panels carry data | adequate | weak (composite 11 in wide but panel text 6 px) | good | full dialog is navigation, acceptable once | adequate | good | medium | good | yes | borderline | MINOR FIX: show the exported composite large instead of the dialog preview; dialog crop as inset |
| 12 | Tutorial system | method | built against the real app | adequate | n/a | good (16 pt, six bullets) | n/a | adequate | good | high | good | n/a | borderline | SPLIT: flow diagram + one line; details to a second slide or the notes |
| 13 | Pilot validation | evidence | all PASS | good | n/a | good | n/a | good | good | low | good | n/a | yes | KEEP |
| 14 | 39 plot types | breadth | one workflow | good as a mosaic | thumbnails unreadable by design | good | n/a | good | good | high by design | good | yes | yes (as texture) | KEEP (caption says thumbnails) |
| 15 | Where this goes next | roadmap | pilot then review | good | n/a | good | n/a | good | good | low | good | n/a | yes | KEEP |
| 16 | Summary | close | five points | good | n/a | good | n/a | good | good | low | good | n/a | yes | KEEP |

Totals: KEEP 7, MINOR FIX 2, REDESIGN 5, SPLIT 3, REMOVE 0 (slide 3's bullet list survives as a
text slide; its miniature screenshots are removed).

## New slides required by the review

* Hero: **One dataset, multiple publication-ready views** (box + observations, violin +
  observations, bar + observations; same 36 observations, large).
* Hero: **From raw table to figure** (5-row excerpt, mapping rows, plot, publication preset,
  final).
* **Same data, different presentation** pairs: group comparison default vs preset; volcano
  default vs refined; heatmap basic vs refined; scatter basic vs refined; Kaplan-Meier default
  vs refined.
* **Observations under your control**: six renderings of the same observations with different
  marker size, jitter width, fill, edge and arrangement.
* **Publication presets**: the twelve experimental presets by their approved names, with the
  evidence caveat (experimental, not journal-approved).

## Rules adopted for the rebuilt deck

Large visual plus one short message. Plots occupy 50-80 % of the usable area and are rendered
for presentation (larger fonts and markers, same data) from SVG/PNG exports, never from shrunk
window captures. UI screenshots appear only as readable crops of the control that is being
taught, or as full windows on navigation slides. Body text 18-20 pt Arial, titles 28 pt, dark
text, one accent colour.

## Rebuilt deck (22 slides) - what changed

Per-slide record: `slide_review_rebuilt.csv`. Effective font sizes of every placed image:
`plot_font_qc.csv` (from `tutorial/slides/plot_font_qc.py`; rule: plot tick labels >= 9 pt OK,
UI text >= 9 pt OK, 8-9 pt borderline, below 7 pt not used).

* Plots are presentation renders from `tutorial/showcase/` (170 x 150 mm figures, axis labels
  20 pt, ticks 17 pt, legend 16 pt, annotations 15 pt, markers 90 pt², same data as the
  manuscript copies; `audit/showcase_data_integrity.csv` records identical n, tests and P values).
  Placed at 3.6-5.5 in they read at 9-14 pt; no window capture is used as a figure anywhere.
* Full-window screenshots: none. UI crops: statistics settings (5.4 in), 3. Options (5.4 in),
  Messages text (11 in), 2. Map columns before / after (5.4 in), the preview dialog split into
  its two halves (11 in each), the package confirmation (5 in). Five UI crops sit at 8.2-8.9 pt
  effective text and are marked BORDERLINE in the QC; they are readable at 1600 px and are
  narrated on the slide's message line.
* New slides: hero "One dataset, multiple publication-ready views" (5), "The observations are
  yours to show" (6), preview before / after (8) and change list (9), four same-data pairs
  (10-13), hero "From an ambiguous table to a publication figure" (14).
* Removed: the shrunk workspace and start-screen screenshots (old 3), the shrunk Demo 1 / Demo 2
  windows (old 5, 6, 7), the two-window preset slide (old 9), the window on the reproducibility
  slide (old 10), the Figure Builder dialog preview (old 11 - replaced by the exported composite),
  the six dense bullets of the tutorial-system slide (old 12).
* Original 16-slide review: KEEP 7, MINOR FIX 2, REDESIGN 5, SPLIT 3, REMOVE 0. Rebuilt deck:
  22 slides, of which 9 new, 6 redesigned, 7 kept.
