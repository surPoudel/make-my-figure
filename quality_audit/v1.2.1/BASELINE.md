# v1.2.1 hotfix — baseline on unmodified v1.2.0

Recorded before any code change, from the branch
`hotfix/v1.2.1-rendering-builder-state`, which was created from the **v1.2.0 tag**
and not from `main`.

## Source

| Field | Value |
|---|---|
| Tag | `v1.2.0` (annotated) |
| Commit | `420344b684f1620c6730c42de7e8e118161d63d0` (`420344b`) |
| Hotfix branch | `hotfix/v1.2.1-rendering-builder-state` |
| Branch point | exactly `420344b` — verified by `git rev-parse` after creation |
| Worktree | separate, so nothing from `main`, `feature/spatial-v2` or the tutorial branch can enter |

**Why not `main`.** `main` has moved on since the release: it carries post-v1.2.0
rendering fixes (label fitting, axis-label clearance, stats-box placement) that are
not part of v1.2.0 and would make a "reproduce the released behaviour" exercise
meaningless. The hotfix is v1.2.0 plus only the fixes v1.2.1 needs.

## Environment

| Component | Version |
|---|---|
| `version.py` | 1.2.0 |
| Registered plot types | **45** (queried from `registry.available_plot_types()`) |
| Python | 3.11.9 |
| Platform | Linux 6.18.33.2 (WSL2), glibc 2.43 |
| matplotlib | 3.10.8 |
| PySide6 (Qt) | 6.11.2 |
| numpy / pandas / scipy | 2.1.2 / 2.2.3 / 1.17.1 |

Qt runs headless here (`QT_QPA_PLATFORM=offscreen`), matplotlib on `Agg`.

## Reported regressions under investigation

| # | Area | Author's observation |
|---|---|---|
| 1 | Figure margins | changing a margin needs several interactions before the change appears |
| 2 | Figure Builder | a finalized plot is restyled on insertion; typography changes, fonts overlap, statistics text becomes disproportionate |
| 2B | Statistics text | too large relative to the plot, may be clipped; P values can render broken (`p < 0.`) |
| 3 | New-plot state | styling from the previous plot leaks into a new one |
| 4 | Spatial ROI | renders essentially black; palette controls appear not to work |
| 5 | Palettes generally | colour controls broken or partial on calibration, Bland-Altman, QQ, dendrogram, slopegraph, beeswarm, dot/strip, forest |
| 6 | Matrix Workflow PCA | does not use the confirmed sample-metadata groups for colour/legend |

Author's additional requirement, recorded with the colour work: plots that use a
single colour should expose explicit colour pickers for each meaningful artist,
in the style the volcano already uses for its up / down / not-significant classes,
rather than a categorical palette control that does not apply.

## Test baseline

Full suite on `420344b`, counts recorded dynamically rather than quoted from
history — see `BASELINE_TESTS.txt` next to this file.
