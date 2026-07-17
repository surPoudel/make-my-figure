# Make My Figure — v1.0.0 release notes

> **Status: v1.0.0 release candidate (`1.0.0rc1`).** This is the first public-style
> release candidate. The final `v1.0.0` tag will be cut once the release candidate has
> been verified on macOS, native Windows, and WSL/Linux by a maintainer. See
> "Verification" below.

## What Make My Figure is

A local-first tool that turns tabular data (CSV / TSV / XLSX) into publication-ready
scientific plots and multi-panel figures. Upload a table, pick a plot, confirm how your
columns map, and export a clean figure plus a reproducible JSON spec.

## Major capabilities

- **37 plot types** across comparisons, relationships, time/trajectory, matrix/omics,
  statistical/model, genomics-style summaries, composition/set/flow/network, and more.
- **Matrix workflow** — map a feature-by-sample matrix, build/upload metadata, validate
  groups, get plot recommendations, and generate heatmaps / PCA / correlation /
  selected-feature plots.
- **Raw-like QC & preprocessing** — diagnostics + QC plots, recommended preprocessing,
  confirm-before-apply, a derived matrix, and before/after QC. Nothing is applied
  silently; the original matrix is preserved and every step is recorded in a
  `PreprocessingSpec`. Normalizations include CPM, TMM (TMM-CPM), voom-style logCPM,
  log/arcsinh/sqrt, total-sum/median/quantile/upper-quartile, z-score (row/column/global),
  robust/standard scaling, and internal-standard/control-feature methods — all
  pure-Python.
- **Statistics** — t-tests (Student/Welch), Mann–Whitney, paired t / Wilcoxon, ANOVA,
  Kruskal–Wallis, Dunn's, chi-square, Fisher's exact, log-rank, Cox PH, Pearson/Spearman,
  linear regression, and GLM regression (Gaussian/binomial/Poisson/negative-binomial/
  Gamma). BH/Bonferroni/Holm correction. Every drawn value comes from a stored result;
  a method sentence describes what was run.
- **Volcano / MA** — choose the raw p-value or the adjusted p-value / FDR for the y-axis;
  the choice is stored in the spec.
- **Annotations & Figure Builder** — significance brackets/labels and multi-panel
  composition with panel labels.
- **Publication style** — one visible style, Arial-first font stack (no bundled fonts),
  colorblind-aware palettes (incl. black-and-white), plot-aware controls, and vector
  export with editable text.
- **Reproducibility** — PlotSpec / StatsSpec / MatrixSpec / MetadataSpec /
  PreprocessingSpec / FigureSpec sidecars on every export.

## Known limitations

- Publication is a general style, **not** an official journal template; no compliance
  is claimed.
- Not a substitute for statistical review — the user chooses appropriate methods.
- Large matrices may need filtering / top-variable features for responsive heatmaps.
- Exact reproduction of a published figure needs the original data, methods, dimensions,
  fonts, and license clarity.
- Small cross-platform font/backend differences are expected.

## Verification

```bash
python -m pytest -q
python scripts/run_cross_platform_qc.py --output reports/release_cross_platform_qc/current_platform
```

On this candidate's build platform (WSL/Linux): full test suite passing with the Qt
plugin disabled, and the QC harness renders 37/37 plot types with 0 errors and 0
forbidden style labels. macOS and native Windows should be verified by a maintainer with
the same commands before the final tag (see docs/CROSS_PLATFORM_QC.md).

## Guarantees

- **No official journal templates** and no journal-named style options (single visible
  style: Publication).
- **No R / rpy2** anywhere; the optional count-model differential path is Python-only.
- **No AI/API dependency** for core plotting or statistics.
- **Local-first**: no telemetry, no cloud upload; data stay on your machine.
- **No bundled font files.**

## Upgrade notes

Legacy journal-named style profiles (`nature_like` / `science_like` / `cell_like` and
`*_learned`) are migrated to `publication` automatically on load; no user action needed.
