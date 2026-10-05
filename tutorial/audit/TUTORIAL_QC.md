# Tutorial QC — brought up to v1.2.0

Generated 2026-10-05, on `feature/desktop-tutorial` after merging the released
v1.2.0 code into the branch. **The tutorial branch has not been merged into
`main`, and nothing here went into the v1.2.0 release.**

## What changed and why

The branch was **55 commits behind** `main`. Its tutorials predated everything in
v1.2.0 — the six spatial plot types, the shared typography system, the width
work, the cluster-bar controls — so its screenshots showed software that no
longer existed. v1.2.0 was merged **into** the branch (`main` → tutorial, never
the reverse). One conflict, `.gitignore`, resolved as a union of both sides' rules.

## Plot coverage

| | before | now |
|---|---|---|
| Registered plot types | 39 (at the branch's old base) | **45** |
| Plot types with a page | 5 | **45** |
| Plot types with none | 40 | **0** |

**The 45 are not 45 of the same thing, and the manifest's `plot_tutorials_written: 45`
should be read with that in mind:**

- **5 hand-written walkthroughs** — `volcano_plot`, `scatterplot_with_regression`,
  `heatmap_clustered_matrix`, `boxplot_or_violin_with_points`,
  `kaplan_meier_survival_curve`. Each is a step-by-step session against the real
  app, with screenshots, specific UI text and a validated automation script.
  These are the standard.
- **40 generated reference pages** — produced by
  `tutorial/automation/generate_plot_reference.py` from the live registry, the
  bundled example manifest and the option tables. Every column name, role, option,
  default, choice list, export format and figure size on those pages is read from
  the build, so none of it can be wrong in the way hand-written documentation
  drifts. They include the warnings the released renderer actually emits on each
  bundled example. They are **not** walkthroughs and do not claim to be: no
  screenshots, no click path. They exist because a reader looking up "what columns
  does the oncoprint need and what can I change" previously had nowhere to go.

Pages are regenerated, never hand-edited; the generator refuses to overwrite a
hand-written page.

## Automation (Phase 31) — run against the real application

`tutorial/automation/validate_tutorials.py` drives the actual desktop app
offscreen and records each check as the script performs the tutorial's own steps.
Run on the merged v1.2.0 code:

| | |
|---|---|
| Tutorials run | **13** |
| Status | **13 PASS, 0 fail** |
| Checks | **146 passed, 0 failed** |
| Captures | **125** |

Including `master_capabilities` (48 checks, one continuous session covering the
main capabilities) and `observations_jitter` (20 checks).

Covered by the suite: manual column mapping, ambiguous column names, scatter,
group comparison, volcano, clustered heatmap, Kaplan-Meier, publication presets,
Figure Preset, Figure Package, Figure Builder, getting started, master replay.

## Screenshots (Phase 30)

**140 files were refreshed from the real application running v1.2.0 code** — the
automation re-captured them during the validation run, so the images show the
released build and not the 1.1.1 software they showed before. They are genuine Qt
output, not mock-ups.

One limitation, stated rather than glossed: the captures are taken **offscreen**.
Window chrome, OS-level file dialogs and anything the window manager draws may
differ from what you see on a Mac or Windows desktop. The application content —
panels, controls, labels, the figure itself — is what the app really draws.

## Plot gallery

`tutorial/PLOT_GALLERY.md` regenerated: header now reads 1.2.0, **45 entries, 45
thumbnails**, including all six spatial plot types, with the tutorial column
filled from the pages that now exist.

## Not done in this pass

Stated plainly so nobody assumes otherwise:

1. **No tutorial exists for the six spatial plot types as a *workflow*.** They have
   reference pages, and they appear in the gallery, but there is no chapter walking
   through a spatial analysis end to end.
2. **The Matrix Workflow chapter was not re-validated** against v1.2.0 beyond the
   automation suite's existing coverage.
3. **MMFPackage tutorial library** (`tutorial/mmfpackages/`) was not built out; the
   Figure Package automation passes, but there is no per-plot package library with
   an `INDEX.md`.
4. **Slides and the User Manual in this branch were not rebuilt.** The manual in
   `main` was regenerated for v1.2.0; this branch's seminar deck still reflects
   the earlier material.
5. **Video scripts** were not re-recorded or re-timed; 5 exist.
6. **Nobody followed a tutorial by hand on a real desktop.** The automation
   follows the steps; a person reading the prose and clicking along has not.

## Standing rule

Tutorial work does not flow back into `main`. The v1.2.0 release contains no
tutorial commit, verified two ways: the branch is not an ancestor of the release
commit, and of the 355 paths it touches only `.gitignore` exists there.
