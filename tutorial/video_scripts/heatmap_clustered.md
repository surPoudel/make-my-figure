# Clustered heatmap from a feature-by-sample matrix

TITLE: Clustered heatmap - choosing the value columns
TARGET LENGTH: 2:30
DATASET: tutorial/datasets/feature_sample_matrix.csv
START STATE: start screen, no data.
ACTION SCRIPT: `python tutorial/automation/run_tutorial.py heatmap_clustered --onscreen --pause 1.5`

| time | screen | action | narration |
|---|---|---|---|
| 0:00-0:08 | start screen | - | "A clustered heatmap from a matrix of two hundred features and twelve samples." |
| 0:08-0:30 | Data preview, Recommended figures | **Open data file**, `feature_sample_matrix.csv` | "Two identifier columns, then S01 to S12. The application recognises an expression-like matrix and recommends the clustered heatmap and PCA." |
| 0:30-1:05 | 2. Map columns | **Clustered heatmap**; row_id = gene_symbol; point at Value columns | "This plot type has one drop-down, row_id, and a list of value columns. The twelve sample columns are pre-selected; the identifiers are not. Set row_id to gene_symbol. Deselect any column that is an annotation, not a measurement." |
| 1:05-1:50 | 3. Options | scale = row_zscore; cluster_columns off | "Scale rows to z-scores so patterns, not baselines, drive the colours. Switching column clustering off keeps the samples in file order." |
| 1:50-2:15 | preview | - | "Rows are reordered by hierarchical clustering; the colour bar shows the z-score." |
| 2:15-2:30 | 5. Export | **Export PNG**, **Export PDF** | "Export. For large matrices PNG is quicker; PDF stays vector." |

FINAL STATE: row-z-scored heatmap, columns unclustered.
EXPORT: `heatmap.png`, `heatmap.pdf`.
KEY MESSAGE: Value columns are a choice, not a guess; keep annotations out of them.
