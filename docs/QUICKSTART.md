# Make My Figure — Quickstart (Milestone 1)

> Nature-like / Science-like / Cell-like are **style aesthetics only**. They are
> not official journal templates and do not guarantee submission acceptance.

## 1. Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# or: pip install -e ".[app,dev]"
```

## 2. Run the web dashboard

```bash
streamlit run apps/streamlit_app/streamlit_app.py
```

Or run the **desktop app** (no command line needed once built — see
[DESKTOP_APP.md](DESKTOP_APP.md)):

```bash
pip install -e ".[desktop]"
python -m apps.desktop_app.main
```

Then in the browser:

1. Pick a **bundled sample** or **upload** a CSV / TSV / XLSX.
2. Review the table preview and any validation warnings.
3. Choose a **plot type**, **style profile**, and **column mapping**.
4. Preview the figure.
5. Download **SVG / PNG / PDF** and the reproducible **PlotSpec JSON**.

## 3. Use the library from Python

```python
from make_my_figure.io.loaders import load_table
from make_my_figure.plots.registry import make_spec, render_to_files

info = load_table("mock_data/volcano_plot.csv")
spec = make_spec("volcano_plot", "volcano_plot.csv", "nature_like")
out = render_to_files(spec, info.dataframe, "outputs/volcano",
                      formats=["svg", "png", "pdf"])
print(out["files"], out["sidecar"])
```

## 4. Regenerate example figures

```bash
python scripts/generate_examples.py --style nature_like
```

## 5. Run the tests

```bash
pytest -q
```

## Replacing mock data with your own data

Keep the **required column names** listed in
`mock_data/plot_schema_manifest.json` for each plot type, or remap your columns
in the dashboard sidebar. Validation is by **column name and type** — column
order does not matter.

## Supported plot types (all 17 manifest types)

| Plot type | Mock data | Required columns |
|---|---|---|
| Bar plot with error bars | `barplot_error_raw.csv` | `condition`, `replicate`, `measurement` |
| Grouped bar plot with error bars | `grouped_barplot_error.csv` | `genotype`, `treatment`, `replicate`, `expression` |
| Clustered heatmap | `heatmap_expression_matrix.tsv` | `gene` + numeric sample columns |
| Volcano plot | `volcano_plot.csv` | `gene`, `log2_fold_change`, `p_value` |
| Scatter plot | `scatter_regression.csv` | `sample_id`, `x_marker`, `y_response` |
| Box / violin with points | `box_violin_points.csv` | `sample_id`, `group`, `value` |
| Line / time-course with error band | `line_timecourse.tsv` | `time_hours`, `treatment`, `replicate`, `signal` |
| Ridge / density plot | `ridge_density.csv` | `cell_id`, `condition`, `pseudotime` |
| Enrichment dot plot | `enrichment_dotplot.csv` | `term`, `gene_ratio`, `fdr` |
| Kaplan-Meier survival | `survival_km.csv` | `sample_id`, `group`, `time_months`, `event` |
| Stacked composition | `stacked_composition.csv` | `sample_id`, `cell_type`, `fraction` |
| Waterfall plot | `waterfall_response.csv` | `patient_id`, `best_percent_change` |
| PCA scatter | `pca_expression_matrix.tsv` + `pca_sample_metadata.csv` | matrix `gene`+samples; metadata `sample_id` |
| Oncoprint | `oncoprint_long.csv` | `patient_id`, `gene`, `alteration_type` |
| Lollipop mutation plot | `lollipop_mutations.csv` | `gene`, `protein_position`, `sample_count` |
| ROC curve | `roc_curve_scores.csv` | `sample_id`, `true_label`, `score_model_a` |
| Forest plot | `forest_plot.csv` | `subgroup`, `hazard_ratio`, `ci_low`, `ci_high` |

> **PCA** needs two tables: an expression matrix (primary) and a sample-metadata
> table whose `sample_id` values match the matrix's sample column names. In the
> dashboard the bundled metadata loads automatically; for your own data, upload
> the metadata table in the sidebar when PCA is selected.
