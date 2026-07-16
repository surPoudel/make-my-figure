# Known limitations — preprocessing/QC apps release candidate

## Version naming
- Requested label is **"v0.2"**, but the repository's real version is **`0.6.1`**
  (`make_my_figure_core/version.py`). I did **not** bump or downgrade the version — a
  downgrade to `0.2.x` would corrupt the established scheme. Decide the intended internal
  version (`0.6.2` patch, or `0.7.0` minor) and I will set it in `version.py` (pyproject
  reads it dynamically; the desktop About dialog imports it). **No git tag** was created.

## Cannot be executed in this sandbox (verify in WSL/native)
- **Streamlit** is not installed here, so the Streamlit app and its AppTest cannot run;
  they are covered by AST parse + the pure-`matrix_workflow` call-sequence check, and skip
  gracefully in pytest.
- **Qt/PySide6** cannot load (`libEGL.so.1` missing), so the desktop app, desktop GUI
  tests, and the PyInstaller **desktop build** cannot run here. Desktop logic is covered by
  the GUI-free controller tests. A Windows `.exe` must be built on native Windows.

## Functional notes
- The Streamlit "value histogram" requested in the flow is served by the **value density**
  QC plot (per-sample distribution); there is no separate histogram plot type.
- QC plots subsample to ≤4000 features for distribution plots (speed); this is a
  visualization sample, not a change to the analysed matrix.
- Streamlit QC before/after plots render on demand (not persisted); large matrices will
  take a moment to render each QC plot.
- QC plots in Streamlit are previews and are not individually addable to the Figure
  Builder; **processed-matrix downstream plots** (heatmap/PCA/volcano/…) can be added.
- The optional count model (PyDESeq2) requires `pip install -e ".[count-de]"`; it is never
  imported by the core workflow.

## Data / privacy
- Private local files are excluded from git via `.git/info/exclude` (not the committed
  `.gitignore`): `GREEN-*.txt`, `voom_norm_annot*`, `meta_info_detail.csv`, `clauderesume`,
  `outputs/`, `.agents/`, and the untracked benchmark `figures/`/`raw/` dirs. None are
  required by any test.
