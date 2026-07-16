# Tutorial: analyzing a raw‑like counts / intensity matrix

This walks through a raw, unnormalized feature matrix (e.g. RSEM expected counts:
`geneID / geneSymbol / bioType / annotationLevel` + many sample columns) from upload to
a publishable, **traceable** figure — Python‑only, no R.

Core principle: the app **diagnoses** and **recommends**, but **never transforms
silently**. You confirm every step; the original matrix is untouched; each derived
matrix + step is saved in a reproducible `PreprocessingSpec`.

> Status: the preprocessing/QC engine below is available in
> `make_my_figure_core.matrix_workflow`. A one‑click GUI wizard for it is a follow‑up;
> today the raw‑counts path runs through this API (the desktop app already does mapping,
> grouping, and plotting).

## 1. Load + map columns (you confirm the roles)
```python
import pandas as pd
import make_my_figure_core.matrix_workflow as mw

df = pd.read_csv("my_raw_counts.tsv", sep="\t")
value_cols = [c for c in df.columns if "DHP" in c]        # your sample columns

spec = mw.MatrixSpec(
    feature_id_column="geneID", feature_display_column="geneSymbol",
    annotation_columns=["bioType", "annotationLevel"],     # NOT treated as values
    value_columns=value_cols, value_type="raw_numeric",
    source_file="my_raw_counts", confirmed_by_user=True)
```

## 2. Define groups
```python
meta = mw.metadata_from_assignment({s: "Ctrl" if cond_ctrl(s) else "Treatment"
                                    for s in value_cols})   # use YOUR real design
```

## 3. Diagnose (evidence, not a verdict)
```python
qc = mw.diagnose_matrix(df, spec)
print(qc.suspected_data_type, qc.skewness_summary, qc.zero_fraction)
for w in qc.warnings: print("•", w)
```
Typical raw‑count findings: strongly right‑skewed, many zeros, uneven per‑sample totals.

## 4. See recommended preprocessing (nothing auto‑applies)
```python
for r in mw.recommend_preprocessing(qc):
    print(r.name, "->", [s["method"] for s in r.steps], "|", r.reason)
```

## 5. Confirm preprocessing + before/after QC report
```python
steps = [
    {"method": "filter",    "params": {"max_zero_frac": 0.7, "drop_constant": True}},
    {"method": "total_sum", "params": {"scale_factor": 1e6}},   # CPM‑like
    {"method": "log2",      "params": {"pseudocount": 1.0}},
]
final, dspec, ps, _ = mw.before_after_report(
    df, spec, steps, out_dir="reports/preprocessing_qc/mydata", metadata=meta)
print(ps.method_sentence())
```
Writes `before_after_contact_sheet.png/pdf`, `preprocessing_report.md`, `qc_summary.csv`,
`per_plot/` — showing value distribution, per‑sample box, library size, mean–variance,
PCA, and sample correlation **before vs after**. A good raw‑count normalization equalizes
library sizes, spreads the log distribution, stabilizes mean–variance, and removes the
technical library‑size axis from PCA.

## 6. Downstream plots from the PROCESSED matrix `final`
```python
from make_my_figure_core.plots.registry import make_spec, render, export_figure

hs = make_spec("hierarchical_clustering", "proc", "publication",
               mapping={"row_id": "geneID", "value_columns": value_cols, "cluster": "rows",
                        "k": 3, "scale": "row_zscore", "max_features": 1500})
export_figure(render(hs, final).figure, "reports/preprocessing_qc/mydata/heatmap", ["png","svg","pdf"])
```
QC plots on any matrix: `mw.qc_plot_inputs(kind, df, spec, metadata=meta)` for
`kind in [c["key"] for c in mw.qc_plot_catalog()]`.

## 7. Statistics + volcano (traceable to the preprocessing)
```python
ds = mw.feature_differential_summary(
    final, dspec, meta, group_a="Treatment", group_b="Ctrl", test="welch_t",
    preprocessing_note=ps.method_sentence(), source_matrix_id="proc",
    preprocessing_spec_id=ps.output_matrix_id)
print(ds.method_sentence())      # includes the FULL preprocessing chain
vol = make_spec("volcano_plot", "diff", "publication",
                mapping={"x": "log2_fold_change", "p": "adjusted_p_value",
                         "label": "feature_label", "use_fdr": True})
export_figure(render(vol, ds.table).figure, "reports/preprocessing_qc/mydata/volcano", ["png","svg","pdf"])
ds.table.to_csv("reports/preprocessing_qc/mydata/differential_summary.csv", index=False)
```

## Choosing methods for common situations
- **Strong right skew, non‑negative** → `log2(x + pseudocount)` (or `arcsinh` if many zeros).
- **Uneven sample totals** → `total_sum` (CPM‑like) or `median_scale` before `log2`.
- **Many zeros** → `filter` sparse features first; pseudocount choice is sensitive.
- **Negative values present** → do NOT log or use ratio fold change; z‑score/centering for
  visualization only (the app warns).
- **Already log/normalized** → do not re‑log; center/scale only.
- **Internal standards / housekeeping controls** → `internal_standard_features` /
  `internal_standard_columns` / `control_features` (see INTERNAL_STANDARD_NORMALIZATION.md).

## Count models (optional)
This is a **generic feature‑level differential summary** on normalized values — not a
count model. For a negative‑binomial count model, round to integer counts and use the
optional `pip install -e ".[count-de]"` (PyDESeq2, no R) path — see
`COUNT_MODEL_DE_INVESTIGATION.md`.

## Guarantees
No silent preprocessing • original matrix unchanged • every step in `PreprocessingSpec`
• method sentence includes preprocessing • volcano/MA trace to the stored result and
source matrix • Publication style throughout • no R, no rpy2.
