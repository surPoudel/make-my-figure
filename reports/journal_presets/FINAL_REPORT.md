# Experimental evidence-derived publication presets - final report (2026-09-16)

Branch `feature/evidence-derived-journal-presets`, worktree `make_my_plot_journal_presets`, forked from
`feature/portable-figure-package-v1.1.1` at 193f637. **Nothing was merged, tagged, pushed to main or
released; the shipping preset library (`style_profiles/starter_journal_style_profiles.json`,
`style_profiles/learned/`) is untouched; the manuscript was not changed.**

## 1. What was built

| area | result |
|---|---|
| Capability audit | `current_preset_capability_audit.csv/.md` (118 properties): no preview-before-apply, no physical-width targeting, journal profiles dead code, semantics-changing options classified as style |
| Physical width | numeric `column_width` in mm accepted by the style engine and every renderer path (`styles/engine.resolve_width_mm`, `plots/base.figure_size`) |
| Preview before apply | `make_my_figure_core/preset_preview.py`: before/after render (user's own data when loaded, else synthetic CC0 example), change list, `assert_style_safe` guard, `apply_with_guard`, `preview_gallery`; desktop dialog (`action_preview_preset`, experimental presets never applied blind, "Save as my preset"), Streamlit preview block |
| Experimental library | `make_my_figure_core/experimental_presets.py`: read-only bundled `.mmfpreset.json` + `.mmflayout.json` with provenance block, neutral-name rule, style-only rule (no analytical options, annotation geometry only), lab-copy helper; opt-in checkbox in both apps |
| Drawn-figure QC | `make_my_figure_core/qc/text_layout_qc.py`: text overlap, clipped annotations, legend over data (vertex-based), smallest effective font at target width, exported width vs target |
| Group-comparison renderers | shared observations engine (`plots/observations.py`: jitter / centred / beeswarm, bounded n-adaptive size/alpha, never hides points); box/violin rewritten (kinds box, violin, box+violin, summary; fills, widths, orientation, hue dodge, category order, n labels, axis policy); bars rewritten (`_bar_shared.py`; explicit `summary` mean/median and `error` sem/sd/ci95/ci95_t/iqr recorded in metadata; observations overlay; outline fill; caps; n labels; orientation; functional `color` role); statistics wired into dot/strip, beeswarm, raincloud, paired slopegraph |
| Bracket engine | per-bracket local start above the spanned groups' points/error bars, collision-avoiding stacking, point-based geometry (`*_pt`, legacy `*_frac` honoured), axis expanded to fit, horizontal orientation |
| Test data | `examples/group_comparison_test_data/` (17 synthetic designs: n = 3-50, unequal 5/8, 6/17, 4/9/13, 2 x 3, extreme value, overlapping, separated) |

## 2. Evidence

* **Official requirements**: 159 rows, three publishers (`official_guidelines_audit.csv`; Nature live pages, Science/Cell from dated Wayback captures because the live sites block automated clients; three Science Advances values marked UNVERIFIED).
* **Corpus**: 50 open-access papers per family (Nature-, Science-, Cell-family journals; 2023-2026), 874 figure rows, deterministic sampling protocol written first; plus 16 papers harvested earlier and the 24 locally available published panels. Publisher files only under `PRIVATE_REFERENCE_ONLY/` (1.4 GB, git-ignored).
* **Measurement**: 205 Nature-family figures rendered from typeset PDFs at known physical scale (text sizes INFERRED from glyph heights; stroke widths OBSERVED); 592 web-resolution figures measured for colour and layout only (absolute sizes ESTIMATED and excluded from central estimates).
* **Visual review**: 1,819 coded rows (1,765 quantitative panels) with the fixed protocol; **group-comparison subset** 1,398 bar/box/violin/dot panels from 116 papers.
* **Prior art**: cnsplots (BSD-3) reviewed; ideas noted, no code and no journal-named palettes copied.

Key findings (`analysis/family_differences.md`, `analysis/group_comparison_summary.md`):

| finding | value |
|---|---|
| Shared across families (no meaningful difference) | left+bottom spines (87-96%), outward ticks, no grid, white background, sans font, regular-weight axis labels, unframed legends, colour-blind-aware saturated categorical palettes |
| Meaningfully different | panel-letter case (Nature lower, Science/Cell upper; Cramer's V 0.65) and panel-letter size (Science much larger; V 0.60) - both match the publishers' stated rules; points overlaid on summaries (Science/Cell more than Nature) |
| Nature-family typeset text | dominant text 5.9 pt (IQR 5.4-6.4), largest cluster 6.7 pt, stroke modes 0.26 and 0.6 pt, in figures 151-182 mm wide |
| Individual observations shown | 78% of group-comparison panels (Science 83, Cell 79, Nature 71); 80% of bar panels carry points |
| Representation | bar+points 49%, dot/strip+summary 14%, bar 13%, box+points 9%, violin+points 3%; small n (<= 10): bar+points 68%; large n (>= 30): dot/strip+summary 30%, box+points 23%, violin+points 12%, bar+points 8% |
| Summary / error as stated in captions | mean 69% / median 17%; SEM 33%, SD 15%, IQR 14%, none 21% (a quarter of Science-family panels never define the error bar) |
| Statistics display | none 26%, bracket+P 21%, bracket+stars 20%; exact P values dominate in 2026 Nature-family papers, stars in Science/Cell; n printed in the panel in 6% |

## 3. The presets (`style_profiles/experimental_publication_presets/`)

Six family style presets with neutral names - Single column 57 / 85 / 89 mm and Full width 174 / 183 / 184 mm,
labelled (S), (C), (N) for the evidence set - each with a companion layout preset (figure width,
panel-letter case/size/weight from the publishers' statements), and six group-comparison presets
(`gc_bar_points_jittered`, `gc_bar_points_open`, `gc_box_points_outline`, `gc_box_points_light`,
`gc_violin_points`, `gc_dense_groups`). Every value carries an evidence class in
`experimental.value_evidence` and in `evidence_trace.md`. Where families did not differ, the same
value is used (no manufactured differences). Absolute text sizes for (S) and (C) come from the
publishers' stated ranges, not measurement (stated as a limitation in each preset).

## 4. QC

* `qc/qc_matrix.csv` - 12 presets x 38 plot types = 456 cells: **288 PASS, 69 WARN, 99 FAIL**. Family-preset non-PASS reasons: exported width off target in 72 cells (renderers that size themselves: grouped bars, waterfall, dose-response, UpSet, spider, Sankey, embedding scatter, oncoprint, lollipop, and legends placed outside), legend over data 36, text overlap 37 (gene labels in volcano/MA, dense tick labels at 57 mm), text under 5 pt 9 (Sankey/UpSet at narrow widths), clipped annotations 3. Overlap was never resolved by shrinking text; each preset now lists its PASS plot types in `experimental.recommended_for` (23 of 38 for the 85/89 mm presets, 22 for full width, 15 for the 57 mm preset). All six gc presets PASS on their own plot type.
* `group_comparison_acceptance/` - 6 gc presets x 17 synthetic datasets x 2 widths with statistics on: **196 PASS, 4 WARN** (the 2 x 3 hue design renders 147 mm at a 183 mm target because the legend sits outside), 0 FAIL; every observation drawn (n_points_drawn == n), brackets above points and error bars.
* `comparison_sheets/` - 10 plot types, Publication defaults vs every applicable preset at one physical scale.
* `reports/figure_preset_qc/all_plot_preset_matrix.csv` regenerated: 38/38 PASS with the new options; `scripts/audit_style_capabilities.py`: capabilities agree with renderer source.
* Scientific identity: `tests/test_preset_scientific_identity.py` - raw values, group n, summary, error definition, tests, P and adjusted P identical before/after a demanding preset on unequal designs.

## 5. Tests

* Baseline (before any change, headless WSL, `-p no:pytest-qt`): 1706 passed, 5 skipped (`baseline_test_run.md`).
* Final full suite (same environment, all changes applied): **2360 passed, 5 skipped, 9 warnings**, no failures (`final_test_run.md`); targeted re-run of the new modules after the last fix: 708 passed.
* Windows portable Python with PySide6 (Qt GUI, controllers, pop-out panels, performance, wiring, Streamlit presets): **87 passed, 1 skipped** (`windows_qt_tests_final.txt`).
* New test modules: experimental library (rules + every shipped preset on every plot type), preview & layout QC, scientific identity, box/violin options (79), bar observations (36), bracket geometry (20), UI wiring additions.

## 6. Author decisions and manual testing

`MANUAL_PRESET_ACCEPTANCE.md` (desktop D1-D14, browser S1-S7, wording W1-W3). Decisions the author
should make before any merge: whether the default bracket geometry may switch from y-range fractions
to points for old specs (it does on this branch when a spec sets no geometry keys); whether the
adaptive marker size should replace the fixed 8 pt² default for box/violin points (it does on this
branch); whether `error` on bar plots becomes a config option (it did; style presets no longer carry
it); the recommendation-engine change proposed in `recommendation_advisory.md` (not applied).

## 7. Known limitations

* Web-resolution corpus images limit line-weight and tick-direction judgements (recorded as UNKNOWN); about a third of the first download were 100-200 px thumbnails, excluded from review and repaired where full-size renditions existed.
* Science/Cell typeset PDFs are behind interactive access checks and were not fetched; their presets carry OFFICIAL text sizes.
* Twelve renderers size themselves or place legends outside and therefore miss the width target; they are listed per preset in the QC and excluded from `recommended_for`.
* One reviewer batch detected image reads silently dropped by the tooling and re-reviewed; other batches were not re-verified.
* Open-access sampling under-represents flagship journals (Nature 9, Science 16, Cell 8 papers).

Evidence-derived publication presets are ready for author review and manual testing. No preset has been merged into the shipping library and no release has been created.
