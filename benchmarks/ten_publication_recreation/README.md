# Ten-publication recreation benchmark

Scales the [one-publication pilot](../one_publication_recreation/) to **10 distinct
publications across 10 distinct plot types**. Each panel is recreated from a real
publication's associated **public** data, through Make My Figure's normal render
path in the single **Publication** style — proving the engine on real data, not
just synthetic demos.

## Ground rules (same as the pilot)
- **Real, license-recorded public data only** (CC0 / public-domain / permissive
  benchmark datasets). Each `publications/<id>/source/provenance.json` records the
  article + data license and how it was verified.
- **No copyrighted figure images stored** — `reference_image_stored=false`
  everywhere; targets are described textually (`source/figure_targets.md`); no
  image-similarity is claimed.
- **Rendered through the app** (`registry.render`, `journal_style="publication"`),
  each panel exporting PNG/SVG/PDF + a PlotSpec, with per-panel `scientific_qc.md`
  and `visual_qc.md`.
- **No RNA-seq differential-expression** is run; **no journal-named styles**.
- **Honest labels** — no panel is called an "exact reproduction." Classic datasets
  (Iris, Wine, Digits, …) are recreated as *publication-grade visualizations from
  the associated data*; where a published quantity is reproduced exactly (e.g. the
  Zachary network's node/edge set, per-city odds ratios from published 2×2 counts)
  it is labeled a *scientific reproduction*.

## The 10 publications / plot types
See `manifest.json` and `reports/summary_table.csv`. Distinct plot types:
scatter/regression, box/ridge distribution, PCA, clustered heatmap, forest,
Kaplan–Meier, ROC, confusion matrix, calibration, network graph.

## Reproduce
The panels + records here were produced through the app's render path; the shared
helper is `scripts/_lib.py`. To re-render/validate:
```bash
python -m pytest tests/test_ten_publication_recreation.py -q -p no:pytest-qt
```
Raw downloads are cached under each `publications/<id>/raw_data/` (small,
license-clean) or regenerated from bundled Python datasets (scikit-learn / networkx).

## License-restricted targets (deferred, NOT included)
TCGA, cBioPortal, GDSC, and MSK-IMPACT panels were **intentionally excluded** —
those carry data-use terms that don't clearly permit redistribution, so they are
not committed as data. See `reports/rejected_candidates.md`. The app supports those
plot types; only the *license-clean data* is the gating factor.

> These recreations are for quality assurance and style validation. They are
> publication-grade, scientifically-traceable recreations from associated public
> data — not official reproductions and not pixel-identical to any published figure.
