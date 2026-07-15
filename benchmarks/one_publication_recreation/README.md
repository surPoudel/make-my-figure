# One-publication recreation benchmark

A proof-of-concept showing that **Make My Figure** can take a real open-access
publication's associated data, curate it reproducibly, and recreate its figure
panels through the app's normal render path (single **Publication** style) —
then assemble them in the Figure Builder — with scientific + visual QC.

**Publication:** Gorman KB, Williams TD, Fraser WR (2014). *Ecological Sexual
Dimorphism and Environmental Variability within a Community of Antarctic Penguins
(Genus Pygoscelis).* PLoS ONE 9(3):e90081. DOI
[10.1371/journal.pone.0090081](https://doi.org/10.1371/journal.pone.0090081).
Article **CC BY 4.0**; associated data **CC0** (Palmer Station LTER, tidied
release via palmerpenguins).

**Panels recreated (3):** A — bill length vs depth scatter by species
(`scatterplot_with_regression`); B — body mass by species with pairwise stats
(`boxplot_or_violin_with_points` + Mann-Whitney/BH); C — morphometric PCA
(`pca_scatter_from_matrix`). Assembled into a labelled multi-panel figure.

**Legal:** no article figure images are stored — only citation, figure numbers,
and textual target descriptions (`source/figure_targets.md`); no image-similarity
is computed. Raw data are CC0. See `source/license_notes.md`.

**Honest label:** *Publication-grade recreation* — scientifically traceable to the
CC0 data and visually publication-grade, not pixel-identical.

## Reproduce
```
python scripts/download_data.py          # CC0 data (skips if cached / offline)
python scripts/curate_data.py            # reproducible processed tables
python scripts/recreate_panels.py        # render panels through Make My Figure + QC
python scripts/assemble_figure_builder.py# Figure Builder assembly
python scripts/evaluate_recreation.py    # report + summary
python -m pytest tests/test_one_publication_recreation.py -q -p no:pytest-qt
```

## Layout
- `source/` — paper metadata, license notes, textual figure targets
- `raw_data/` — CC0 downloads + checksums
- `processed_data/` — reproducible per-panel tables + curation log
- `recreated_panels/panel_{A,B,C}/` — processed data, target spec, PlotSpec,
  StatsSpec (B), PNG/SVG/PDF, scientific/visual QC, differences
- `figure_builder/` — assembled figure (PNG/SVG/PDF) + FigureSpec
- `qc/` — aggregate scientific/visual QC, summary CSV, recreation report

Make My Figure does not run RNA-seq differential-expression analysis and does not
expose journal-specific style names; this benchmark uses only the Publication style.
