# Make My Figure — v1.1.0 release notes

> **Status: v1.1.0 (stable).** Second stable release, following v1.0.0. Built from the
> `v1.1.0` tag by the GitHub Actions native runners (macOS, Windows, Linux) with a
> `--selftest` smoke test on every platform. The full changelog entry is in
> [`CHANGELOG.md`](../CHANGELOG.md); the release audit trail is in
> [`docs/releases/v1.1.0/`](releases/v1.1.0/).

## What Make My Figure is

A local-first tool that turns tabular data (CSV / TSV / XLSX) into publication-style
scientific plots and multi-panel figures. Load a table, pick a plot, confirm how your
columns map, and export a clean figure plus a reproducible JSON record (PlotSpec).

## Highlights of v1.1.0

- **Figure presets for every plot type.** Save the reusable part of a figure's
  configuration — *style only* (typography, palette, geometry, legend and colorbar
  placement, export size, visual plot options) or *full configuration* (adds column roles,
  thresholds, labels and the statistics test) — and apply it to another dataset. A preset
  never contains the table, its values or worksheet provenance; roles a new table cannot
  satisfy are reported, never substituted. Figure Builder **layout presets** carry grid,
  panel sizes, gutters and label style.
- **Histogram plot type** (long or wide input, per-group panels or overlays, bars and/or
  frequency polygon, counts / frequency / percent / density, cumulative option). Now 38
  plot types.
- **Independent R validation of the statistics.** Every statistical test, correction,
  normalisation/transform, QC metric, PCA, clustering and the feature-level differential
  screen was compared with independent R implementations on seeded synthetic datasets, the
  bundled examples and a public count matrix: 2,625 comparisons, no failures. The
  comparison found and fixed six numerical defects (see *Fixed*). The feature-level screen
  is compared with limma-voom, edgeR and DESeq2 as **concordance only**; it is not a
  replacement for those models. Regression tests pin the fixes.
- **Survival, forest and histogram controls:** precomputed survival curves, validated 0/1
  event indicator, axis-range and tick overrides that refuse to hide plotted data, log /
  symlog axis scales for line plots, IQR / range bands, line style by a second category.
- **Export fixes.** A tight bounding box that includes axis labels and titles (long labels
  are no longer clipped); editable text in browser SVG/PDF exports; a concrete installed
  font stack so exports, Figure Builder letters and legends keep the Publication font.
- **Packaging.** Installed wheels ship the bundled resources (schemas, style profiles, mock
  data, examples), so `pip install` of the wheel renders out of the box. Native installers
  carry the version in their file names.
- **User Manual and Quick Start** (Markdown, DOCX and PDF) generated from the code and the
  running application with bundled synthetic data only; a plot catalogue generated from the
  registry.

## Fixed (numerical)

- r × c Fisher's exact test: unseeded Monte Carlo p-value → seeded, 200,000 resamples,
  method recorded in the result.
- ROC AUC and average precision depended on input row order for tied scores → ties collapse
  to one operating point.
- Quantile normalisation broke ties by sort order → Bolstad/limma average-rank algorithm.
- `voom` used a library-size-scaled prior → the voom definition.
- Mann–Whitney effect size in the feature-level summary had the wrong sign.
- Last-bit near-ties in rank tests are treated as ties.

## Downloads

| System | File |
|---|---|
| macOS | `MakeMyFigure-1.1.0.dmg` (also `MakeMyFigure-1.1.0-macos.zip`) |
| Windows | `MakeMyFigure-1.1.0-Setup.exe` (also `MakeMyFigure-1.1.0-windows.zip`) |
| Linux | `MakeMyFigure-1.1.0-linux-x86_64.tar.gz` or `MakeMyFigure-1.1.0.AppImage` |
| Python | `make_my_figure_core-1.1.0-py3-none-any.whl`, `make_my_figure_core-1.1.0.tar.gz` |
| Manuals | `MakeMyFigure_v1.1.0_Quick_Start.pdf`, `MakeMyFigure_v1.1.0_User_Manual.pdf` |

**Linux binaries:** the tar.gz and AppImage are built on the Ubuntu 24.04 runner and need glibc 2.38 or newer (Ubuntu 24.04+, Fedora 39+, Debian 13+). On older distributions, including Ubuntu 22.04 and current WSL2 Ubuntu images, use the Python wheel or the source install instead.

`SHA256SUMS.txt` on the release page lists the checksum of every asset. The status bar
(desktop) and the banner (browser) show `Make My Figure v1.1.0 · <commit> · <platform> ·
<backend>`; **Help → About** shows the version.

## Known limitations

- Publication is a general manuscript style, **not** an official journal template; no
  compliance is claimed.
- Not a substitute for statistical review — the user chooses appropriate methods.
- Figure Builder composites embed panel content as raster at the export DPI; panel letters
  and titles stay vector. Export single plots for fully vector output.
- Installers are unsigned; macOS Gatekeeper and Windows SmartScreen require the documented
  first-launch steps.
- Small cross-platform font/backend differences are expected.

## Verification

```bash
python -m pytest -q                      # full suite
python -m pytest tests/test_r_validation_regressions.py -q
python scripts/validate_documented_workflows.py   # workflows described in the manuals
```

Release gates, test counts and the R-benchmark re-run for this release are recorded in
`docs/releases/v1.1.0/release_v1.1.0_audit.md`.
