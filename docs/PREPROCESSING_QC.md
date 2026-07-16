# Preprocessing & QC for raw‑like matrices

Support for **raw‑like, unnormalized, count‑like, intensity‑like, or strongly skewed**
feature matrices — Python‑only, transparent, and **never silent**.

`make_my_figure_core.matrix_workflow`:
- **`diagnose_matrix(df, matrix_spec)` → `QCMetricSummary`** — reports missing values,
  zeros, negatives, integer‑likeness, dynamic range, skew, per‑sample totals/medians,
  outlier samples/features, a *suspected data type* (count‑like / intensity‑like /
  possibly‑log‑or‑normalized), and warnings. These are **suggestions**, never a
  definitive classification.
- **`recommend_preprocessing(qc)` → `[PreprocessingWorkflow]`** — candidate chains, each
  with a reason, assumptions, warnings, and expected downstream plots.
- **`apply_step` / `run_preprocessing`** — apply confirmed steps. The original matrix is
  never mutated; a **new derived matrix** is returned plus a reproducible
  **`PreprocessingSpec`** (ordered `PreprocessingStep`s + a method sentence).

## No silent preprocessing
The app may say data *look* skewed/count‑like/unnormalized and *recommend* transforms,
but it never transforms or normalizes without your confirmation, and every choice is
saved in a `PreprocessingSpec`. Downstream plots reference the **named derived matrix**.

## Transforms (`preprocessing.py`)
`log2` / `ln` / `log10` (user pseudocount; warn on negatives), `arcsinh` (cofactor),
`sqrt`, `winsorize` (percentile caps, reports capped count), `impute`
(none / feature‑median / sample‑median / constant; reports imputed count), `filter`
(missingness / zero‑fraction / constant / low‑variance / low‑total / top‑variable).

## Normalization (`normalization.py`)
Total‑sum (library size), median scaling, upper‑quartile, quantile, row/column/global
z‑score, robust (median/IQR) scaling, standardization, centering, **internal‑standard**
(features or columns), **control‑feature**, and reference‑sample normalization. See
[NORMALIZATION_METHODS.md](NORMALIZATION_METHODS.md) and
[INTERNAL_STANDARD_NORMALIZATION.md](INTERNAL_STANDARD_NORMALIZATION.md).

## Downstream + statistics
Derived matrices feed the normal recommendations (heatmap, clustered heatmap, PCA,
correlation, selected‑feature plots) and the feature‑level differential summary. The
differential method sentence **includes the preprocessing** (e.g. *"Values were
median‑scaled across samples, then log2(x + 1) transformed, then compared between Ctrl
and Treatment using Welch's t‑test with Benjamini‑Hochberg FDR"*), and volcano/MA
annotations trace back to the stored result + source matrix. See
[FEATURE_LEVEL_STATISTICS.md](FEATURE_LEVEL_STATISTICS.md).

Optional count‑model analysis is documented in
[COUNT_MODEL_DE_INVESTIGATION.md](COUNT_MODEL_DE_INVESTIGATION.md). No R, no rpy2.
