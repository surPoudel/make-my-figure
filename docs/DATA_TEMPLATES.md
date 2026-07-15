# Data Templates — using and replacing example data

> **Published papers and figures are used only as visual style references** for layout, typography, panel structure, legends, annotations, spacing, and general publication formatting. The bundled example datasets are **synthetic** unless explicitly marked otherwise. Synthetic examples are not copied from published papers and must not be cited as real biological findings.

## The fastest way to start

1. In the app choose **Use example data** and pick your plot type.
2. Click **Save template** to export the example table (`.csv`, `.tsv`, or `.xlsx`).
3. Open it in Excel or a text editor and **replace the rows with your own data**,
   keeping the column names.
4. Back in the app, choose **Open data file / Upload** and select your edited file.

## Rules that always apply

- Keep the **required column names** for your plot type (see
  [PLOT_TYPE_REQUIREMENTS.md](PLOT_TYPE_REQUIREMENTS.md)). Column **order doesn't matter**.
- Keep **measurements numeric** and **labels/IDs as text**.
- Most plots want **long format** (one observation per row), not pre-aggregated means.
- For matrix plots (heatmap, PCA) the **first column is the row label** and every other
  column is a numeric sample.
- For **PCA**, the sample-metadata table's `sample_id` values must match the matrix
  column headers exactly.

## Per-plot replacement notes

- **Bar plot with error bars** — Keep one row per replicate. Replace the condition labels and measurement values; the app computes the mean and SEM/SD/CI for you.
- **Grouped bar plot with error bars** — One row per replicate. 'genotype' is the x-axis, 'treatment' is the grouping color.
- **Box / violin plot with points** — One row per sample/observation. Switch box vs violin with the 'kind' option.
- **Scatter plot** — x and y must be numeric. Leave 'label' blank for points you don't want annotated.
- **Line / time-course with error band** — Long format: one row per time point per replicate. 'treatment' colors the lines.
- **Clustered heatmap** — First column = row label (gene). All other columns are numeric samples.
- **Volcano plot** — One row per gene/feature. Provide p_value (and adjusted_p_value if available).
- **Enrichment dot plot** — One row per enriched term. Provide FDR (the app derives -log10 FDR if missing).
- **Kaplan-Meier survival curve** — One row per patient. event=1 means the event occurred; event=0 means censored.
- **Stacked composition bar plot** — Long format: one row per sample per cell type. Fractions should sum to ~1 per sample.
- **Waterfall plot** — One row per patient. Use negative values for tumor shrinkage.
- **PCA scatter (matrix + metadata)** — Provide the matrix (genes x samples) as data, and a metadata table whose 'sample_id' matches the matrix sample column names.
- **Oncoprint mutation heatmap** — One row per alteration (a patient/gene can appear multiple times).
- **Lollipop mutation plot** — One row per protein position. Positions and counts must be integers.
- **ROC curve** — true_label is 1 for the positive class, 0 for negative. Scores are continuous.
- **Forest plot** — One row per subgroup. Provide the estimate and its CI bounds.
- **Ridge / density plot** — One row per observation. The x value (pseudotime/score) must be numeric.

## Common mistakes

- **Bar plot with error bars:** Do not pre-average — give raw replicate rows.; Keep 'condition' as text, 'measurement' as numbers.
- **Grouped bar plot with error bars:** Keep both grouping columns categorical (text).
- **Box / violin plot with points:** Use enough samples per group (>=5) for a meaningful distribution.
- **Scatter plot:** Blank labels are fine; non-numeric x/y will be dropped.
- **Line / time-course with error band:** Keep time numeric and data in long (not wide) format.
- **Clustered heatmap:** Keep the first column as labels; every other column must be numeric.
- **Volcano plot:** p-values must be numeric (scientific notation is fine).
- **Enrichment dot plot:** gene_ratio should be a fraction between 0 and 1.
- **Kaplan-Meier survival curve:** Encode event as 1/0, not text.
- **Stacked composition bar plot:** Fractions per sample should add up to about 1.0.
- **Waterfall plot:** best_percent_change must be numeric (can be negative).
- **PCA scatter (matrix + metadata):** Metadata sample_id values must exactly match the matrix column headers.
- **Oncoprint mutation heatmap:** alteration_type should use a small, consistent set of labels.
- **Lollipop mutation plot:** Use integer protein positions and counts.
- **ROC curve:** Include both classes (some 1s and some 0s).
- **Forest plot:** ci_low must be <= estimate <= ci_high.
- **Ridge / density plot:** Provide many rows per group for smooth densities.
