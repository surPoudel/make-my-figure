# Optional Python‑only count‑model differential analysis — investigation & decision

## Question
Can we offer a count‑model (negative‑binomial) differential analysis for genuine
count‑like matrices **without R**, safely?

## Packages considered
- **PyDESeq2** — pure‑Python re‑implementation of the DESeq2 method; actively
  maintained; no R, no rpy2. Depends on numpy/scipy/pandas (already present) plus
  `anndata` and `formulaic`. This is the only mature, maintained option.
- **edgePy / other "edgeR‑like" Python packages** — not maintained / not reliable;
  **rejected**.
- **rpy2 + R bridges** — explicitly **out of scope** (no R dependency allowed).

## Decision
Offer PyDESeq2 as an **optional, opt‑in extra** — never part of the core install,
the default workflow, or the core test suite.

- Install: `pip install -e ".[count-de]"`.
- Module: `make_my_figure_core/matrix_workflow/count_model_de.py`.
  - `count_model_available()` — true only if PyDESeq2 imports.
  - `validate_integer_counts()` — requires a non‑negative **integer** matrix.
  - `count_model_differential()` — raises a clear message pointing to this extra (and
    to the fallbacks) when it isn't installed; otherwise runs PyDESeq2 and returns a
    volcano/MA‑compatible table plus a `CountDESpec` (method + package version).
- It is **clearly distinguished** from the generic feature‑level differential summary
  and is called *optional count‑model differential analysis* — **not** an "RNA‑seq
  pipeline".

## Why not in core
- Extra transitive dependencies (`anndata`, `formulaic`) increase install weight and
  Windows/macOS install risk for users who don't need it.
- The core product targets normalized/processed matrices and precomputed differential
  tables; a count model is a niche add‑on.

## Honesty note
The PyDESeq2 code path follows the documented PyDESeq2 API but is **not exercised in
CI** (the extra is not installed there); its test skips gracefully when absent. Treat
it as experimental until you validate it in your environment.

## Fallbacks (recommended default path)
1. Provide a **precomputed differential table** from any tool → volcano/MA/ranked plots.
2. Use the **generic feature‑level differential summary** on a confirmed, appropriately
   **preprocessed** matrix (e.g. total‑sum/median scaling → log2 → Welch/Mann‑Whitney),
   with a fully traceable method sentence.

No R is required anywhere. No rpy2 is used. No count‑model dependency is required for
the core install or tests.
