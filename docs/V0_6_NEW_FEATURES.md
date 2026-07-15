# What's new in v0.6

v0.6 focuses on making the app **faster, more intelligent about what to plot, and
easier to trust before export** — it does not add new plot types. There are still
**17 plot types**, one style identity, and no RNA-seq analysis capability. This
page is an overview; each area has a dedicated doc linked below.

> **Publication style, not an official template.** Make My Figure does not
> provide official journal templates or claim compliance with any journal's
> formatting requirements. The Publication style is a general manuscript-ready
> visual style.

## 1. Figure recommendations

After you load a table, Make My Figure profiles its columns (cheaply — no heavy
analysis) and suggests figures that fit the data's shape: a grouping column and a
numeric value suggest a box/violin or bar plot; a fold-change + p-value column
pair suggests a volcano plot; a wide numeric matrix suggests a clustered heatmap
or PCA; and so on. Each suggestion comes with a confidence, a plain-language
reason, a one-click PlotSpec draft, and any warnings.

- Desktop: the **Recommended figures** panel (Generate / Add to Figure Builder /
  Dismiss per card).
- Streamlit: the **"Recommended figures"** expander.
- Analyses that could be slow on large data (matrix clustering, PCA) are flagged
  `requires_confirmation` and never run without an explicit yes.

See [docs/RECOMMENDED_FIGURES.md](RECOMMENDED_FIGURES.md) for the full data-type →
figure table and the settings.

> Make My Figure can recommend plots and statistical workflows from uploaded data
> structure, but users are responsible for confirming that the recommended
> figures and tests match their experimental design.

## 2. Publication QC

A new scoring engine (`make_my_figure_core/qc`) inspects a rendered figure — and
optionally its PlotSpec and statistics report — and returns a 0–100 score with a
pass/warn/fail level and a list of specific, actionable checks (export DPI,
label crowding, legend overlap, missing units, missing method report, contrast,
and more). QC is advisory: it never blocks rendering or export. Selected checks
have one-click, non-destructive **auto-fixes** that produce a new PlotSpec.

- Desktop: the **"Publication QC"** button opens a dialog with an **Auto-fix &
  re-render** action.
- Streamlit: the **"Publication QC"** expander.

See [docs/PUBLICATION_QC.md](PUBLICATION_QC.md).

## 3. Publication-recreation benchmarks

`benchmarks/publication_recreation/` is a license-safe QA suite: 18 manifest
entries (mostly deterministic synthetic datasets plus one CC0 real dataset),
recreated through the app's normal rendering path and scored with Publication
QC. It exists to catch regressions and to derive **aggregate** style
improvements — it is not a library of reproduced journal figures, and it makes
no claim of journal endorsement.

> Publication benchmark recreations are used for quality assurance and style
> improvement. They are not official reproductions unless explicitly stated and
> license-permitted.

See [docs/PUBLICATION_BENCHMARKS.md](PUBLICATION_BENCHMARKS.md) for the
licensing policy and how to run it, and
[docs/V0_6_PUBLICATION_STYLE_LESSONS.md](V0_6_PUBLICATION_STYLE_LESSONS.md) for
the style lessons that came out of it.

## 4. Performance

Long tasks (statistics, clustering, exports, figure construction) can now run on
a background `QThreadPool` worker in the desktop app
(`apps/desktop_app/workers.py`) instead of freezing the GUI thread, and
continuous controls (sliders, spinboxes) debounce their re-renders. `scipy` is
already imported lazily, deferred until statistics are actually used, which
shortens cold start. `scripts/benchmark_performance.py` measures cold import,
example load, render, export, and recommendation timings and writes a Markdown
report.

A known limitation carried into v0.6: the desktop preview canvas is still
rebuilt on every render rather than updated in place, which is the main
remaining source of preview flicker/lag. See
[docs/WINDOWS_PERFORMANCE.md](WINDOWS_PERFORMANCE.md) for Windows-specific
causes (OneDrive-synced paths, PyInstaller cold start) and how to benchmark.

## 5. One Publication style + PlotSpec migration

Make My Figure now exposes a **single style identity: Publication**
(`make_my_figure_core/styles/engine.py`). The older journal-named profiles
(`nature_like`, `science_like`, `cell_like`, and their `*_learned` variants) are
no longer offered in the UI or in `list_profiles()`. If you load an older
PlotSpec JSON that still names one of those profiles, `registry.render()`
transparently maps it to `publication`, renders normally, and adds a
non-fatal warning plus `metadata["style_migration"]` explaining what happened —
old saved files keep working without any action from you. This is a scope
decision about how many named looks the app exposes, not a claim about journal
templates; see [docs/STYLE_PROFILES.md](STYLE_PROFILES.md).

## What is NOT supported

- **No RNA-seq differential-expression analysis.** Make My Figure does not run
  RNA-seq differential expression analysis in this version. Upload a
  precomputed differential results table if you want volcano or MA plots.
  edgeR/limma/DESeq2 are referenced only as **header-naming conventions** that
  `de_detect.py` recognizes when confirming a volcano column mapping — the app
  never computes or recomputes a p-value.
- **No official journal templates.** The Publication style is a general
  manuscript-ready visual style; it does not guarantee compliance with any
  specific journal's formatting requirements.
- **No new plot types in v0.6.** Still 17 renderers; recommendations and
  benchmarks only ever point at existing renderers (a few schema detections —
  Manhattan/Q-Q, network graph, dose-response curve fitting — are recognized but
  have no renderer, and are surfaced as explicit warnings, never faked).

## See also

- [README.md](../README.md) — overall app description and feature list.
- [docs/STATISTICS.md](STATISTICS.md), [docs/STATISTICAL_ANNOTATIONS.md](STATISTICAL_ANNOTATIONS.md)
- [docs/MULTI_PANEL_FIGURES.md](MULTI_PANEL_FIGURES.md)
- [docs/EXPORTING_PUBLICATION_FIGURES.md](EXPORTING_PUBLICATION_FIGURES.md)
- [docs/V0_6_IMPLEMENTATION_PLAN.md](V0_6_IMPLEMENTATION_PLAN.md) — the original planning doc for this release.
