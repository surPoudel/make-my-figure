# Manuscript claims that would become supportable - only after validation and release

The MakeMyFigure manuscript (Poudel et al., 2026; bioRxiv submission of 2026-09-15) must **not** be
updated to describe the experimental publication presets. Nothing on the branch
`feature/evidence-derived-journal-presets` is merged, released or user-tested. This file records
which sentences could be written *later*, what evidence each would need, and which claims must
never be made.

## Claims that could be made after merge, release and manual acceptance

| Candidate claim | Evidence it would need | Where the evidence would come from |
|---|---|---|
| "MakeMyFigure ships evidence-derived publication style presets whose values were measured on N open-access research figures from three journal families (Nature-, Science- and Cell-family journals) and cross-checked against the publishers' stated artwork requirements." | The final corpus counts (papers, figures, panels per family), the measurement protocol, and the official-requirements audit with access dates | `journal_preset_research/corpus_manifest_expanded.csv`, `style_measurements.csv`, `official_guidelines_audit.csv` |
| "Presets are applied in style mode only: they change typography, line weights, palette, legend and axis geometry, and never the data, statistics or thresholds." | The runtime guard and its tests passing in the released build | `make_my_figure_core/preset_preview.py::assert_style_safe`, `tests/test_preset_preview_and_layout_qc.py`, `tests/test_experimental_presets.py` |
| "Every preset is previewed on synthetic data before it is applied, with a list of the settings that will change." | The preview dialog present in both frontends of the released build | desktop `action_preview_preset`, Streamlit preview block; manual acceptance record |
| "Presets target a physical column width and are checked at that width for overlapping text and minimum font size." | The QC matrix for the released presets with no FAIL cells on the recommended plot types | `reports/journal_presets/qc/qc_matrix.csv` |
| "Journal families differed measurably in X but not in Y." | The family-differences analysis with effect sizes | `journal_preset_research/analysis/family_differences.md` |

## Claims that must never be made

* That a preset is a journal's template, is "compliant", "approved", "endorsed" or "ready" for
  any journal, or that it improves acceptance odds.
* That the presets reproduce any published figure (they encode aggregate conventions only).
* That the measured values are exact for text sizes: point sizes from web-resolution images are
  ESTIMATED under a stated width assumption; only the typeset-PDF route yields INFERRED sizes with
  an observed scale.
* Any number from this branch before it is regenerated on the released build.

## Status at the time of writing (2026-09-16)

Experimental; not merged; not released; no user testing. See `MANUAL_PRESET_ACCEPTANCE.md` for
what the author has to test before any of the above becomes true.
