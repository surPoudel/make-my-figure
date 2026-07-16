# Release candidate checklist — preprocessing/QC apps (internal 0.6.1)

> Label requested: "v0.2 candidate". Actual repo version: **0.6.1** (unchanged — see
> `known_limitations.md` and `docs/RELEASE_NOTES_v0.2.md`). **Not a public release.**

| Item | Status | Notes |
|------|--------|-------|
| Preprocessing/QC engine present & tested | ✅ | `make_my_figure_core/matrix_workflow/` (committed earlier) |
| Streamlit preprocessing step wired | ✅ | `apps/streamlit_app/matrix_wizard.py` `_step_preprocess` + `_active_matrix` routing |
| Desktop preprocessing tab wired | ✅ | `apps/desktop_app/matrix_wizard.py` `③ Preprocess` tab + inline QC preview |
| GUI-free controller methods + tests | ✅ | `apps/desktop_app/controller.py`; `tests/test_desktop_matrix_controller.py` (8 passed) |
| Derived matrix flows downstream | ✅ | heatmap / PCA / correlation / box / volcano / MA / Figure Builder |
| Differential summary traceable to preprocessing | ✅ | `preprocessing_note` + `source_matrix_id` + `preprocessing_spec_id` in both apps |
| Composite Figure Builder export PNG/SVG/PDF | ✅ | was PNG-only (Streamlit) |
| Guardrails: no R/rpy2, no fonts, no journal styles, no RNA-seq labels | ✅ | `tests/test_release_guardrails.py` (6 passed) |
| Full test suite (Qt plugin disabled) | ✅ | 976 passed, 5 skipped |
| Docs updated | ✅ | README + RAW_COUNTS_TUTORIAL + PREPROCESSING_QC + MATRIX_WORKFLOW + FEATURE_LEVEL_STATISTICS + RELEASE_NOTES_v0.2 |
| Streamlit live smoke | ⏳ WSL | streamlit not installed in sandbox — run in dev env |
| Desktop live smoke | ⏳ WSL/native | Qt native libs (`libEGL.so.1`) absent in sandbox |
| Desktop build | ⏳ WSL/native | not run in sandbox (Qt cannot load); Windows `.exe` needs native Windows |
| Version bump | ⚠ deferred | repo at 0.6.1; awaiting your decision (0.6.2 / 0.7.0) — not downgraded to 0.2 |
| Git tag / GitHub Release / visibility | 🚫 not done | requires explicit "RUN PUBLIC RELEASE" |

## Do-not-do (respected)
- No public release, no GitHub Release, no git tag, no visibility change.
- No private data committed (GREEN-*.txt, voom_norm_annot*, meta_info_detail.csv,
  outputs/, clauderesume, unrelated benchmark figures — all excluded via
  `.git/info/exclude`).
- No font files, no R/rpy2, no build binaries staged.
