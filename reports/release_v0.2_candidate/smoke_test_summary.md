# Smoke-test summary — preprocessing/QC apps release candidate

## What ran in this sandbox

| Check | Result |
|-------|--------|
| `from apps.desktop_app.controller import DesktopController` | ✅ OK (GUI-free logic imports; `matrix_qc_plot` present) |
| AST parse `apps/streamlit_app/matrix_wizard.py` | ✅ OK |
| AST parse `apps/streamlit_app/streamlit_app.py` | ✅ OK |
| AST parse `apps/desktop_app/matrix_wizard.py` | ✅ OK |
| All `self.controller.matrix_*` calls resolve to real methods | ✅ OK (0 missing) |
| End-to-end preprocessing call sequence (diagnose → recommend → run → QC render → to_dict/from_dict → traceable differential) | ✅ OK (verified via `matrix_workflow` directly) |
| Full test suite (Qt plugin disabled) | ✅ 976 passed, 5 skipped |

## What could NOT run here (honest — must verify in WSL/native)

| Check | Why it can't run here | How to run |
|-------|----------------------|-----------|
| `streamlit run apps/streamlit_app/streamlit_app.py` | `streamlit` not installed in sandbox | In WSL dev env: `pip install -r requirements.txt` then `streamlit run apps/streamlit_app/streamlit_app.py` — open the "Matrix workflow (guided)" and confirm the **🧪 Preprocess (raw-like)** step is reachable |
| `python -m apps.desktop_app.main` | No Qt binding loads (`libEGL.so.1` missing) | In WSL with Qt libs (`sudo apt-get install libegl1 libxkbcommon0`) or native Windows: launch, open Matrix workflow, confirm the **③ Preprocess (raw-like)** tab + QC preview |
| Streamlit AppTest (`tests/test_streamlit_matrix_wizard.py`) | `importorskip("streamlit")` skips | Run in WSL after installing streamlit: `python -m pytest tests/test_streamlit_matrix_wizard.py` |

## Manual live-verification checklist (for you, in WSL)
1. Streamlit: upload a raw-like matrix → map columns → define groups → open
   **🧪 Preprocess** → Run diagnostics → preview QC plots → pick a workflow → confirm
   checkbox → Apply → see "Downstream steps now use the processed matrix" → before/after
   QC → generate heatmap/PCA/volcano → export PNG/SVG/PDF.
2. Desktop: same flow via the wizard tabs; confirm QC preview renders, apply runs on a
   background worker (UI stays responsive), and the differential method sentence includes
   the preprocessing chain.
