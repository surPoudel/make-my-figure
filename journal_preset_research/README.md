# journal_preset_research - evidence behind the experimental publication presets

All files here are research records (2026-09-16). Publisher figure files live only under
`../PRIVATE_REFERENCE_ONLY/` (git-ignored); this folder holds manifests, coded observations,
aggregate statistics and the tools that produced them.

| file | what it is |
|---|---|
| `corpus_sampling_protocol.md` | the sampling procedure fixed before download (journals, dates, eligibility, deterministic order, caps) |
| `corpus_manifest.csv`, `corpus_manifest_local_summary.md` | inventory of published figures already present locally before this work (146 rows, 24 with images) |
| `corpus_manifest_expanded.csv`, `corpus_expansion_log.md` | the open-access corpus actually used: 50 papers per family (Nature-, Science-, Cell-family journals), 874 figure rows, licences, PMCIDs, run history, biases |
| `official_guidelines_audit.csv`, `official_guidelines_notes.md` | 159 publisher requirements/recommendations with source URLs and access dates (Science/Cell from dated Wayback captures) |
| `official_widths.json` | the stated column widths used for the ESTIMATED route and the preset targets |
| `cnsplots_comparison.md` | prior-art review of the cnsplots project (BSD-3) and what was and was not borrowed |
| `measurement_protocol.md` | evidence classes (OBSERVED / INFERRED / ESTIMATED / UNKNOWN), fields, formulas, sampling of panels |
| `visual_review_protocol.md` | the categorical coding scheme and its allowed values |
| `visual_review_<family>_<batch>.csv` (6 files) | 1,819 coded rows (1,765 quantitative panels) from the first three quantitative figures of every paper |
| `biological_group_comparison_corpus_<family>.csv` (3) and `biological_group_comparison_corpus.csv` | 1,398 bar/box/violin/dot panels coded for representation, n, summary, error, markers, statistics, colour |
| `auto_measurements.csv` | figure-level automated measurements (797 figures): sizes, colour statistics, text-size clusters; `route` = `typeset_pdf` (observed scale) or `web_jpeg` (estimated) |
| `analysis/style_measurements.csv` | the merged panel-level table |
| `analysis/style_summary_by_family.csv` | medians/IQR (numeric) and modal value/share (categorical) per family and plot group |
| `analysis/family_differences.md` | Kruskal-Wallis / chi-square with effect sizes; which conventions differ meaningfully and which are shared |
| `analysis/outliers.md` | panels outside 1.5 x IQR of their family group, excluded from central estimates |
| `analysis/group_comparison_summary.md` (+ `.json`) | the answers to the group-comparison research questions |
| `batches/*.json` | the paper/figure lists each reviewer worked from |
| `tools/` | `measure_figure.py`, `typeset_figures_from_pdf.py`, `fetch_typeset_pdfs.py`, `run_auto_measurements.py`, `analyze_measurements.py`, `analyze_group_comparison.py`, `derive_presets.py` |

Derived artefacts: `../style_profiles/experimental_publication_presets/` (the presets),
`../reports/journal_presets/evidence_trace.md` (every preset value with its evidence class),
`../reports/journal_presets/qc/`, `../reports/journal_presets/comparison_sheets/`,
`../reports/journal_presets/group_comparison_acceptance/`.

## Caveats to keep in mind

* Web-resolution figures (about 700 px wide) cannot give reliable absolute text or line sizes;
  those numbers are used only from the typeset-PDF route (Nature-family, 205 figures). Reviewers
  recorded `UNKNOWN` for line weights at web resolution by protocol.
* Roughly a third of the first download were 100-200 px PMC thumbnails; they were excluded from
  review and a repair pass fetched full-size renditions where available (see the expansion log).
* One reviewer batch (Cell group-comparison) detected that some image reads had been silently
  dropped by the tool and re-reviewed every figure; the other batches reported no such event but
  were not independently re-checked.
* Open-access sampling over-represents journals and papers with OA licences; flagship-journal
  papers are present (Nature 9, Science 16, Cell 8) but are a minority of each family.
