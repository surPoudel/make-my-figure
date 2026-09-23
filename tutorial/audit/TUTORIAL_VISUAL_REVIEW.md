# Tutorial visual and content review (2026-09-23)

Reviewer question for every section: does the visual teach an important Make My Figure
capability at a size a reader can actually read, and is every claim true of the application?

Scale for the assessments: **good** / **adequate** / **weak**.

| section | purpose | main message | visual hierarchy | plot readability | font readability | screenshot usefulness | white space | contrast | crowding | accuracy | shows an important capability? | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| README | orientation | one idea: you decide the mapping | good | n/a | good | n/a | good | good | low | good | yes (philosophy) | KEEP |
| 00 Getting started | navigation | layout and menus | adequate | n/a | good | full-window shots are right here (navigation) | adequate | good | the 3357 px tall control-column capture is a scroll, not a figure | good; "&" mnemonic note correct | yes | MINOR FIX: add close-ups of the three group boxes a beginner needs first |
| 01 Mapping master | philosophy + skill | table does not need perfect names | good | adequate: figures are window captures at 1680 px, plot text ~10 px | adequate | good for the mapping rows (widget crops) | good | good | low | good, quoted from the live run | yes, the strongest section | MINOR FIX: add exported plots (large) next to each window capture; add before/after preset |
| 01 Reshaping | scope of restructuring | only what exists | adequate | n/a | good | none | good | good | low | good | partly | KEEP (no screenshots by design; add one Define groups capture later) |
| plots/scatter | plot tutorial | per-group regression | adequate | weak: only window captures; the exported figure is not shown large | adequate | mapping/options crops good | adequate | good | medium | good | partly: no marker/edge controls exist for scatter (flagged) | REDESIGN visuals: exported plot large, default vs refined |
| plots/box-violin | plot tutorial | summary + observations + test | adequate | good for 05b (figure crop) | adequate | statistics panel crop is excellent | adequate | good | medium | good | yes, but on main the observation controls are only point size | REDESIGN: showcase observation controls (now available after merging the presets branch), preset before/after |
| plots/volcano | manual mapping | detection vs manual roles | good | adequate | adequate | Messages crop is convincing | good | good | medium | good | yes | MINOR FIX: add default vs refined exported volcano at full width |
| plots/heatmap | matrix mapping | value columns are a choice | adequate | weak: 200-row heatmap has no readable row labels (by design) | adequate | Value columns crop good | adequate | good | low | good | partly | REDESIGN visuals: basic vs refined (colormap, labels for a 30-row subset, group strip) |
| plots/kaplan-meier | survival | group role + log-rank | good | good (figure crop) | good | good | good | good | low | good | yes | MINOR FIX: default vs refined |
| 06 Statistics | reference | you choose the test | good | good | good | panel crop excellent | good | good | low | good, values quoted from the run | yes | KEEP |
| 09 Styling | reference | where appearance lives | adequate | n/a | good | none | good | good | low | good | partly | MINOR FIX: add one before/after of the Publication style groups |
| 10 Figure presets | concept | style travels, data stay | good | adequate (window captures) | adequate | save dialog crop excellent | good | good | medium | good | yes, but only user presets; the publication presets are not shown | REDESIGN: add experimental publication presets, Preview & apply, "preset is a starting point" |
| 11 Reproducibility | concept | PlotSpec vs package | good | adequate | good | confirmation and reopened window are convincing | good | good | medium | good | yes | KEEP |
| 12 Figure Builder | dialog | panels carry data | good | adequate | adequate | full dialog capture is right (navigation) | adequate | good | medium | good | yes | KEEP |
| 13 Export | reference | the buttons | good | n/a | good | none | good | good | low | good | partly | KEEP |
| 14 Complete workflow | sequence | the path | good | n/a | good | none | good | good | low | good | yes | KEEP |
| PLOT_GALLERY | index | 39 real renders | good | thumbnails 160 px are for browsing only | good | good | good | good | high by nature | good | yes | KEEP |

## Cross-cutting findings

1. **Window captures used as figures.** Every plot tutorial shows the result as a 1680 x 1000
   window capture. Plot text is 10 px or less. Rule from now on: window capture for *how to do
   it*, exported plot (PNG at 200 dpi or SVG) for *what you get*, and enlarged crops of the
   control group that matters.
2. **The strongest capability was not shown.** Individual observations with controllable
   arrangement, jitter width, size, marker, fill, edge, opacity, box fill, group spacing and
   sample-size labels exist on the presets branch but not on main, so the pilot could only show
   `Point size` and `Overlay points`. The presets branch has now been merged into the tutorial
   branch (see `MISSING_SHOWCASE_CAPABILITIES.md` for what is and is not available).
3. **Publication presets were absent.** The pilot showed only user-saved presets. The
   evidence-derived experimental presets (six width presets, six group-comparison presets) and
   the *Preview & apply* dialog are now available on this branch and get their own chapter.
4. **No same-data contrast.** Nothing showed the same observations under two presentations.
   Showcases 1-5 (`tutorial/showcase/`) add before/after pairs with a data-integrity check.
5. **Accuracy held.** No claim in the pilot text was found to contradict the application;
   the three application findings (ampersand mnemonic, two statistics switches, Spearman row
   labels) stand.

## Actions taken (2026-09-23)

| finding | action |
|---|---|
| window captures used as figures | every plot page now has a *Before / after* section with renders from the application's renderer (`showcase/`), manuscript typography in the pages, presentation typography in `*_pres.png`; window captures remain for *how to do it* |
| observation controls not shown | new chapter `03_Group_Comparisons/showing_individual_observations_and_jitter.md` (action script `observations_jitter`, 20 checks PASS, 17 captures incl. the real Preview & apply dialog) |
| publication presets absent | new chapter `10_Figure_Presets/publication_presets.md` (action script `publication_presets`, 13 checks PASS); `showcase/presets_used.md` lists the exact preset files and properties |
| no same-data contrast | five showcases (group comparison with six presets and six point treatments, volcano, heatmap, scatter, survival); `audit/showcase_data_integrity.csv` - identical data hash, group n, tests and P values across every copy |
| capability claims | `audit/MISSING_SHOWCASE_CAPABILITIES.md`: main vs this branch, what is not available (scatter marker controls, regression CI, risk table, heatmap strip only via Define groups) |
| video scripts | `group_comparison_box` rewritten as a live transformation (observations off / on, jitter, size, marker style, statistics, preview, apply, adjust, export); `figure_preset` and the master script updated |

Additional application findings from these runs: the *Sample-size labels* placed below the
groups overlap the tick marks in the desktop preview (`screenshots/observations_jitter/07_box_outline_n_labels.png`);
the *Preview & apply...* button label shows the ampersand mnemonic like the group titles.
