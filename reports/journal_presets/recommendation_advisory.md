# Advisory: should the recommendation engine prefer distribution-preserving plots?

**Status: advisory only. No recommendation behaviour was changed on this branch.** Any change to
`make_my_figure_core/recommendations/plot_recommender.py` needs its own tests and the author's
approval.

## What the corpus shows (journal_preset_research/analysis/group_comparison_summary.md)

1,398 group-comparison panels from 116 open-access papers (Nature-, Science- and Cell-family
journals, 2023-2026), coded by visual review.

| question | finding |
|---|---|
| Are individual observations shown? | yes in 78% of panels (Science 83%, Cell 79%, Nature 71%); among bar panels, 80% overlay the points |
| Most common representation overall | bar + points 49%; dot/strip + summary 14%; bar without points 13%; box + points 9%; violin + points 3% |
| Small groups (every group <= 10 observations; 844 panels) | bar + points 68%, dot/strip + summary 12%, box + points 10%, bar alone 6% |
| Large groups (a group >= 30; 141 panels) | dot/strip + summary 30%, box + points 23%, violin + points 12%, bar + points 8% |
| Marker size vs n | small n: medium markers 61%; large n: small markers 77% (jitter stays the dominant arrangement, 61-72%) |
| Statistical annotation | none 26%; bracket + P value 21%; bracket + stars 20%; exact P values dominate in Nature-family 2026 papers, stars in Science/Cell |
| Summary and error as stated in captions | mean 69% / median 17%; SEM 33%, SD 15%, IQR whiskers 14%, none 21%; a quarter of Science-family panels never define the error bar |
| n printed in the panel | 6% (below or above a category); 56% state it in the caption |
| Zero baseline | bars 84% yes; box/violin panels often not |

## What this implies for recommendations

* When the data are replicate-level (long format, a categorical group column and a continuous
  value), the field's dominant practice for small n is a **summary with every observation shown**.
  Recommending a bar *without* points as the default group-comparison plot no longer matches
  practice. The current recommender (`plot_recommender.py`, `generic_long` branch) ranks
  box/violin 0.72 > ridge 0.62 > bar 0.60 and never proposes the dot/strip or beeswarm plots
  (see group_comparison_renderer_audit.md).
* For **large groups** the field shifts to distribution-preserving displays (dot/strip with a
  summary, box + points, violin + points); a bar + points display is the minority (8%). The shared
  observations engine already emits a suggestion above 60 observations per group.
* The corpus does **not** support ranking bar + points above box + points on quality grounds; it
  shows what is common. A recommender that follows practice would offer, for few groups and raw
  observations: bar + points, box + points, dot/strip + summary (small n) - and box/violin + points
  or dot/strip + summary (large n) - side by side, and let the user preview them on their data
  (the preset gallery `preset_preview.preview_gallery` exists for exactly this).

## Proposed (not implemented) rule, for separate testing

```
if long-format, 2-6 groups, continuous value, >= 3 observations per group:
    n_max = largest group size
    if n_max <= 30:  offer [bar+points, box+points, dot_strip+summary] with equal rank,
                     and the previews of gc_bar_points_jittered / gc_box_points_outline
    else:            offer [box+points, violin+points, dot_strip+summary] first, bar+points after,
                     with the density note from plots/observations.adaptive_marker
never rank a bar without points above the same bar with points when observations are available
```

The summary statistic (mean/median) and the error definition (SD/SEM/CI) remain explicit user
choices; a recommendation must never pre-select SEM because it is common.

## Why this is not applied now

The author asked for this to remain advisory until separately tested and approved; changing
recommendations alters what users are shown for every long-format table and needs its own
acceptance pass (recommendation tests, the Matrix Workflow hand-off, and the desktop/browser
recommendation panels).
