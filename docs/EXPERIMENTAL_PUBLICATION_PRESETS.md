# Experimental publication presets (evidence-derived; not merged, not released)

**Status: experimental, on branch `feature/evidence-derived-journal-presets` only.** Nothing described
here is in a released MakeMyFigure build, and the MakeMyFigure manuscript does not describe it.

## What they are

A small library of Figure *style* presets (`style_profiles/experimental_publication_presets/*.mmfpreset.json`)
whose values were **measured** on published open-access research figures and **checked against the
publishers' stated artwork requirements**, plus companion Figure Builder layout presets for panel
letters and figure width. They are shown in both apps only when "Show experimental presets" is
ticked, are read-only, and always go through the preview-before-apply dialog.

They are **not** journal templates. A preset name never contains a journal name or any wording such
as "compliant", "approved" or "ready"; the neutral names give the physical width and an evidence-set
letter (N, S, C). Which journals each evidence set was measured from is stated in the preset's
provenance block and in `journal_preset_research/` - because that is provenance, not a claim.

## What a preset can and cannot change

Can change (style mode): font family and sizes, axis-line/tick/error-bar/marker weights, marker size,
palette, legend geometry, spines, grid, target width in mm, export DPI/format, and the *geometry* of
statistical brackets (tick height, gaps, label offset, font size).

Can never change: the data, column roles, group assignment, summary statistic (mean/median), error
definition (SD/SEM/CI), thresholds, transformations, normalisation, feature selection, the statistical
test, P values, adjusted P values, or *what* a statistical annotation says (stars vs P values, which
comparisons are shown). This is enforced three times: the library validator refuses such files
(`experimental_presets.validate_experimental_preset`), the guarded apply path refuses at run time
(`preset_preview.apply_with_guard`), and the scientific-identity tests re-render with statistics on
and assert the numbers are identical (`tests/test_preset_scientific_identity.py`).

## Preview before apply

Desktop: **Preview & apply…** (or **Apply** on an experimental preset) opens a dialog with the current
look and the preset side by side, drawn on **your loaded data** (your groups and replicate counts;
falls back to the bundled synthetic example when nothing is loaded), the list of every setting that
would change, the provenance text, and a data-safety line. Nothing is applied until you click Apply;
Cancel leaves everything untouched. Browser: the **Preview** button in the "Figure preset" expander
does the same. Experimental presets can be copied into your own library ("Save as my preset") - the
copy keeps a provenance note and is then an ordinary editable preset.

## How the values were derived

See `reports/journal_presets/evidence_trace.md` (one row per value with its evidence class):

| class | meaning |
|---|---|
| OFFICIAL | a stated publisher requirement/recommendation (`journal_preset_research/official_guidelines_audit.csv`, accessed 2026-09-16; Science and Cell pages came from dated Wayback captures because the live sites block automated access) |
| INFERRED | measured on typeset-PDF figures whose physical size is known (Nature-family open-access PDFs; text sizes from glyph heights at 300-600 dpi, vector stroke widths read directly) |
| OBSERVED | a convention read from the corpus (share of coded panels) |
| ESTIMATED | derived under a stated assumption (e.g. marker size class -> pt²) |
| SHARED | no meaningful difference between families (p ≥ 0.01 or effect below medium), so the same value is used everywhere - no difference is manufactured |

Corpus: `journal_preset_research/corpus_manifest_expanded.csv` (open-access papers, 2023-2026, three
families, sampled by the protocol in `corpus_sampling_protocol.md`); visual review per
`visual_review_protocol.md`; the group-comparison subset in `biological_group_comparison_corpus.csv`
with its summary in `analysis/group_comparison_summary.md`. Publisher images are kept only under
`PRIVATE_REFERENCE_ONLY/` (git-ignored) and are never redistributed.

Known limitation: absolute text sizes for the Science- and Cell-evidence presets come from the
publishers' stated ranges (OFFICIAL), not from measurement, because their typeset PDFs are behind
interactive access checks and web-resolution images cannot give reliable point sizes. The
Nature-evidence presets carry INFERRED sizes from typeset PDFs.

## Group-comparison presets

`gc_*` presets set the *representation* of bar/box/violin panels with individual observations
(arrangement, marker fill/edge, bar/box width and fill, error caps) for `barplot_with_error_bar` and
`boxplot_or_violin_with_points`. The number of observations always comes from the data; marker size
and opacity adapt within bounded rules by group size and nothing is ever hidden. The summary
statistic and error definition are the user's explicit choice and are recorded in the PlotSpec and
metadata; the presets do not touch them.

## QC and acceptance

* `python scripts/experimental_preset_qc.py` - every preset x every plot type at its target width:
  overlapping text, clipped annotations, legend over data, smallest effective font vs the 5 pt
  minimum, exported width vs target (`reports/journal_presets/qc/`). Overlap is reported, never
  "fixed" by shrinking text.
* `python scripts/experimental_preset_comparison_sheets.py` - Publication defaults vs each preset at
  one physical scale (`reports/journal_presets/comparison_sheets/`).
* `MANUAL_PRESET_ACCEPTANCE.md` - the author's manual test script for both apps.
* Tests: `tests/test_experimental_presets.py`, `tests/test_preset_preview_and_layout_qc.py`,
  `tests/test_preset_scientific_identity.py`, `tests/test_figure_preset_ui_wiring.py`.

## Release rule

Do not merge, tag, release or modify the shipping preset library from this branch. The presets are
ready for author review and manual testing only.
