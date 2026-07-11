# Install & dependency QC

## Core dependencies (import-verified)
| package | version (this env) | used for |
|---|---|---|
| pandas | 2.2.3 | data |
| numpy | 2.1.2 | numerics |
| matplotlib | 3.10.8 | rendering/export |
| scipy | 1.17.1 | statistics |
| statsmodels | 0.14.6 | ANOVA/Cox/corrections |
| openpyxl | 3.1.5 | .xlsx |
| jsonschema | 4.23.0 | PlotSpec validation |
| networkx | 3.6.1 | network graph (v0.5) |
| adjustText | 1.3.0 | volcano label repel (v0.5) |

All 9 declared core deps import cleanly (`pyproject.toml` / `requirements.txt`).
`networkx` and `adjustText` were added in v0.5 and are declared in both.

## Optional dependencies
| package | status here | behavior when missing |
|---|---|---|
| streamlit | not installed in sandbox | Streamlit app + `test_app_smoke` skip; core/desktop unaffected |
| PySide6 (desktop) | Qt libs unavailable | desktop GUI + Qt tests skip; core/Streamlit unaffected |
| lifelines | not installed (not required) | Cox HR uses statsmodels PHReg instead |

Version pins are lower-bounds only (`>=`), not hard pins. Missing optional
dependencies degrade gracefully rather than crashing.

## Suggested clean-install check (run locally)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # core + streamlit + pytest
pip install -e ".[desktop]"                # + PySide6 for the desktop app
python -c "import make_my_figure_core; print('import OK')"
```
