# Quality-hardening baseline

Recorded before any change, per Phase 0. Everything here is measured, not estimated.

## Repository state

| | |
|---|---|
| Branch | `feature/spatial-v2` |
| Commit | `df1addd` |
| Latest stable tag | `v1.1.1` (untouched; this work does not modify it) |
| **Registered plot types** | **45** (from `registry.available_plot_types()`, authoritative) |
| Tests collected | 2244 |
| Last full run | 2240 passed, 4 skipped, 0 failed |

The brief estimated ~44 plot types; the registry reports **45**. The registry wins.

## Known-good subsystems at baseline

* Preset QC matrix: 45/45 PASS
* Style-capability drift: 0
* Figure-package round trips: 87 tests passing, incl. spatial
* Figure size: explicit width/height honoured by all 45 types (246 tests)
* Figure margins: applied across all 45 types (49 tests)

## Defects confirmed from the supplied screenshots

Two screenshots were supplied (two of the three files are byte-identical).

### Volcano plot

| ID | Defect | Status at baseline |
|---|---|---|
| V1 | Labels overlap each other (`GENE0066`/`GENE0016`; `GENE0106` over points) | reproducible |
| V2 | Ignored-control warning is ungrammatical **and** gives the wrong reason | reproduced below |
| V3 | "Append (n=…)" count | **already working** — title shows `Up 53 · Down 44 · NS 403`, legend shows `Down (n=44)`, `Up (n=53)` |

V3 is listed in the brief as broken. It is not, at this commit. It is recorded here so the
claim is checked rather than assumed, and it will be covered by a regression test regardless.

**V2 reproduction.** `warn_ignored_style_controls("volcano_plot", {...})` returns:

```
Style control 'line_width_pt' a volcano colours points by significance class
(up / down / not significant) - set those three colours in the plot options;
the palette does not apply; it was ignored for this volcano_plot.
```

Two faults, both architectural rather than cosmetic:

1. the reason is a sentence fragment that does not follow "Style control 'x'", so the
   message is not readable English;
2. `PlotStyleCapabilities` carries **one** `unsupported_controls_reason` per plot type, so
   every unsupported control receives the same explanation. A *line width* control is
   explained with a sentence about *colours*, which is actively misleading.

### Clustered heatmap

| ID | Defect | Status |
|---|---|---|
| H1 | Cluster legend clipped at the right edge ("Clus…") | visible in screenshot |
| H2 | Row labels crowded at ~30 rows | visible |
| H3 | "Cluster" strip label repeated and colliding with column labels | visible |
| H4 | Colourbar label placement | to confirm |

## Scope note

The brief has 33 phases and asks for a tutorial, screenshot, publication example and
Figure Package for every one of the 45 plot types, plus a gallery-wide regression suite.
That is a large programme of work. This file records the starting point so progress is
measurable against it, and so that any claim of completion can be checked.
