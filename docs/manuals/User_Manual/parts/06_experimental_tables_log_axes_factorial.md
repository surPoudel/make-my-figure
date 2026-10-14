## Part XXVIII — Ordinary experimental tables, log axes and factorial ANOVA

### 76. Experimental tables are not matrices

A table with one row per observation (treatment, time, colony, body size, a measured
quantity) is handled as an ordinary table. Make My Figure recognises it by its factor
columns, whose few levels repeat down the rows, and by numeric columns that include
coded factors or constants. It recommends group comparison plots, not heatmaps or
PCA. Click **📋 Prepare table (roles, transform, ANOVA)…** (browser: the
**📋 Prepare table** expander).

### 77. Column roles

Assign each column a role: identifier, response, factor/group, time, covariate,
subject/colony (the experimental unit), label, other metadata, or ignore. Suggestions
show their reason; your choice always wins. Rows that share a subject are not
independent replicates.

![Assigning column roles in the Prepare table dialog.](../../assets/screenshots/tabular_02_assign_column_roles.png)

### 78. Transformations with a preview

log10, log2, ln, square root and z-score each **add a new column** (`log10(x)`) beside
the original. The original table never changes. The offset is explicit and defaults
to 0. Values a transformation is undefined for (0 and negatives for a log) are counted
in the preview and refused, unless you choose to record them as missing in the new
column. The preview shows original and transformed values with valid / invalid /
missing counts and both ranges. Apply, Cancel, Reset; **↩ Revert to original data**
in the editor.

![Original versus log10-transformed values before applying.](../../assets/screenshots/tabular_03_transform_preview_log10.png)

**Export table with derived columns…** writes the transformed values (CSV / TSV /
XLSX) plus a JSON record of how each column was made. A Figure Package stores the raw
table, the derived table and the record, and replays the record when it is reopened.

### 79. Log axes and tick notation (display only)

Under **5. Publication style ▸ Axis scale & range**: Linear / Log10 / Log2 / Natural
log; tick labels Plain (1, 10, 1,000), Powers (10⁰, 10¹) or Scientific (×10ⁿ on a
linear axis); minor ticks; minimum and maximum. The axis changes, the values do not:
statistics and exports keep the original numbers. Offered on bar, grouped bar,
scatter, box/violin, line, dot/strip and paired plots. A log axis is refused, with a
message, for values ≤ 0, for a column that already holds log values, or for a range
that would hide data.

![Raw values on a log10 axis with plain tick labels.](../../assets/screenshots/tabular_07_raw_values_on_log10_axis.png)

A log-transformed column and a log axis are different analyses. A mean on a log axis
is the arithmetic mean; the mean of log values is the log of the geometric mean.

### 80. Factorial ANOVA and non-estimable designs

**3 Factorial analysis**: a response, up to three factors, optional covariates and a
subject column; full factorial or main effects; Type II (default) or Type III
(sum-to-zero contrasts) sums of squares; partial η² for each term. The design is
checked first. Complete confounding, empty factor combinations, no residual degrees
of freedom, a constant response, or repeated rows from one subject are explained,
and nothing is computed. Validated against base R (509 of 509 quantities agree).

![A three-way design that four observations cannot support.](../../assets/screenshots/tabular_04_three_way_design_not_estimable.png)

See `docs/GENERAL_TABULAR_DATA.md`, `docs/AXIS_SCALING.md`, `docs/STATISTICS_FACTORIAL.md`
and the step-by-step tutorial in `tutorial/general_tabular_data/`.
