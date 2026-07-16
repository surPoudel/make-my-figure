# Release notes — preprocessing/QC apps release candidate

> **Version naming note.** These notes were requested under the label **"v0.2"**, but
> the repository's actual internal version is **`0.6.1`** (single source of truth:
> `make_my_figure_core/version.py`). To avoid corrupting the established version scheme,
> **no version bump was made** — this is documented as a *release candidate only*. If you
> want an internal bump, the consistent next values would be `0.6.2` (patch: wires an
> existing engine into the GUIs) or `0.7.0` (minor: new user-facing workflow). Tell me
> which and I'll set it; I will **not** downgrade to `0.2.x`.

## Highlights — raw-like matrix QC & preprocessing, wired into both apps

The Python-only preprocessing/QC engine (already in `make_my_figure_core.matrix_workflow`)
is now reachable from the guided matrix workflow in **both** frontends.

### Streamlit (`apps/streamlit_app/matrix_wizard.py`)
- New optional **🧪 Preprocess (raw-like)** step between "define groups" and "recommend
  plots".
- Run QC diagnostics; preview any QC plot (value distribution, per-sample box, per-sample
  total/median, missingness, zero fraction, sample correlation, PCA, mean–variance).
- Recommended preprocessing workflows; **confirm-to-apply** (checkbox + button) to a
  derived copy stored in `st.session_state` — no silent preprocessing.
- Before/after QC comparison; a **Revert to raw matrix** control.
- Downstream validate / recommend / differential automatically use the **processed**
  matrix when present; the raw matrix is never mutated.
- Composite Figure Builder export now offers **PNG/SVG/PDF** (was PNG-only).

### Desktop (`apps/desktop_app/matrix_wizard.py`, `controller.py`)
- **③ Preprocess (raw-like)** tab: diagnostics text, **inline QC-plot preview**
  (any catalog kind of the current matrix), recommendation list, confirm-to-apply
  (runs on a background `QThread` worker), **Save before/after QC report…**, and
  **Revert**.
- GUI-free controller methods (`matrix_diagnose`,
  `matrix_preprocessing_recommendations`/`_methods`, `matrix_qc_plot[_catalog]`,
  `matrix_apply_preprocessing`, `matrix_before_after_report`) — unit-tested without Qt.

### Traceable statistics
- When a differential summary is computed on a processed matrix, both apps pass the
  `preprocessing_note`, `source_matrix_id`, and `preprocessing_spec_id`, so the stored
  result and the method sentence drawn on volcano/MA plots trace to the exact
  preprocessing chain.

## Guarantees preserved
- No silent preprocessing or column guessing — the user confirms every mapping and step.
- Original matrix preserved; every derived matrix recorded in a `PreprocessingSpec`.
- Statistics traceable; method sentences include preprocessing.
- Single visible **Publication** style; no journal-named style options.
- **No R / rpy2**, **no API/AI** required for the core workflow.
- No RNA-seq-branded workflow labels (generic feature-matrix terms).
- No font files committed. Optional Python-only count model (PyDESeq2) stays opt-in
  (`pip install -e ".[count-de]"`).

## Tests
- `tests/test_desktop_matrix_controller.py` — preprocessing controller methods +
  processed-matrix downstream + traceable differential (8 passed).
- `tests/test_streamlit_matrix_wizard.py` — AppTest coverage for the preprocess step and
  processed-matrix-downstream (runs where Streamlit is installed; skips otherwise).
- `tests/test_release_guardrails.py` — no R/rpy2, no committed fonts, no journal-named
  styles, no RNA-seq labels in the matrix UIs, generic value types (6 passed).
