# Volcano plot: automatic detection and manual role mapping

TITLE: Volcano plot from any differential-expression table
TARGET LENGTH: 3:00
DATASETS: tutorial/datasets/rnaseq_results.csv, tutorial/datasets/rnaseq_results_renamed.csv
START STATE: start screen, no data.
ACTION SCRIPT: `python tutorial/automation/run_tutorial.py volcano_manual_mapping --onscreen --pause 1.5`

| time | screen | action | narration |
|---|---|---|---|
| 0:00-0:08 | start screen | - | "In this tutorial we create a volcano plot from a differential-expression table, first with standard column names and then with names the application has never seen." |
| 0:08-0:25 | Data preview, Recommended figures | **Open data file**, `rnaseq_results.csv` | "The table has DESeq2-style columns: log2FoldChange, pvalue, padj. The application detects a differential result and recommends a volcano plot." |
| 0:25-0:50 | 2. Map columns, preview | choose **Volcano plot** | "Choosing the plot type fills the roles: x is log2FoldChange, p is pvalue, label is gene_symbol. The Messages tab asks you to confirm the detection. The figure draws." |
| 0:50-1:10 | start screen, Data preview | **Open data file**, `rnaseq_results_renamed.csv` | "The same numbers, other headers: effect_measure, p_raw, p_adjusted, name." |
| 1:10-1:35 | 2. Map columns, Messages | choose **Volcano plot** | "Now every role is (none) and the Messages tab says which required roles are missing. The column name does not need to follow a convention; assign the roles yourself." |
| 1:35-2:10 | 2. Map columns | x = effect_measure, p = p_raw, label = name, id_col = feature | "effect_measure is the log2 fold change. p_raw is the P value. name labels the points. The volcano renders - identical to the first one." |
| 2:10-2:40 | 2. Map columns, 3. Options | p = p_adjusted; log2FC cutoff 1, p cutoff 0.05; axis labels | "Switch to the adjusted P values and set the cutoffs. The header counts up, down and not significant." |
| 2:40-3:00 | 5. Export | **Export PNG**, **Export PDF** | "Export. The P values were taken from your table; the application did not recompute them." |

FINAL STATE: volcano with adjusted P, ten labelled genes.
EXPORT: `volcano.png`, `volcano.pdf`, `volcano.plot_spec.json`.
KEY MESSAGE: Detection is a convenience; every role can be assigned by hand.
