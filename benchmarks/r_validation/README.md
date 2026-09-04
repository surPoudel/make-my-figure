# Independent R validation of MakeMyFigure's numerical components

This folder holds a self-contained, re-runnable benchmark that checks every statistical test,
multiple-testing correction, matrix transformation / normalization, QC metric, PCA, hierarchical
clustering, differential screen and data-recommendation rule in `make_my_figure_core` against an
**independent R implementation** (base R, `survival`, `car`, `rstatix`, `effectsize`, `MASS`,
`dunn.test`, `limma`, `edgeR`, `DESeq2`). R is used only as a reference; **the production app stays
Python-native and users never need R.**

Two classes of comparison are kept strictly apart:

* **Class A — exact method equivalence.** Same statistical method on identical input; after matching
  documented conventions the numbers must agree to `abs 1e-10` or `rel 1e-8` (`EXACT` ≤ 1e-12).
* **Class B — scientific concordance.** Different models by design (e.g. MakeMyFigure's per-gene Welch
  t on log-CPM vs limma-voom / edgeR / DESeq2). Reported as correlations, direction agreement,
  top-N overlap and Jaccard — never as "identical".

## Layout

```
benchmarks/r_validation/
├── README.md                     this file
├── statistical_inventory.csv     every test / statistic, its scipy/statsmodels call, conventions, R reference
├── transformation_inventory.csv  every normalization / transform / QC metric, formula, defaults, R reference
├── recommendation_inventory.csv  every recommendation rule and how it was audited
├── source_publication_audit.md   verified publication + GEO GSE299655 record; sample→group mapping; RSEM nature
├── benchmark_manifest.json       commit, versions, OS, timestamp, seed, SHA-256 of every input/output
├── FINAL_VALIDATION_MATRIX.csv   one row per component with counts per class and a verdict
├── R/                            00_setup.R … 15_sessioninfo.R (read ONLY data/, examples/, the RSEM file)
├── python/
│   ├── generate_synthetic_data.py         seed 20250904 → data/synthetic/*.csv|tsv + MANIFEST.csv
│   ├── export_make_my_figure_reference.py drives the LIVE core API → results/python/
│   └── compare_outputs.py                 the only code that reads both result trees → comparisons, figures, tables
├── data/synthetic/               26 frozen datasets A–Z (statistics, multiple testing, matrices)
├── data/metadata/                geo_sample_map.csv (from the GEO SOFT record), rsem_sample_groups.csv
├── results/python/               MakeMyFigure outputs (long-format statistics, transforms, QC, PCA, clusters, DE)
├── results/R/                    R outputs with identical file names / column contracts
├── results/comparisons/          per-component comparison tables (+ bugfix before/after records)
├── results/statistics_python_vs_R.csv, transformation_python_vs_R.csv(+_summary), rnaseq_method_concordance.csv,
│   manuscript_validation_table.csv, R_sessionInfo.txt, python_environment.txt
├── figures/                      exact_method_concordance, transformation_concordance, rnaseq_concordance, qc_concordance (pdf+png)
└── reports/                      VALIDATION_REPORT.md, DISCREPANCY_REPORT.md, RECOMMENDATION_AUDIT.md, METHODS_FOR_MANUSCRIPT.md
```

## Independence safeguards

* R scripts read only `data/synthetic`, `data/metadata`, the bundled `examples/` and the RSEM matrix.
  `00_setup.R` asserts the data path is not under `results/python`. No R script opens any Python output.
* Python and R write the same long format (`dataset_id, test_id, comparison, quantity, value`) from
  independent code; `compare_outputs.py` merges on the key columns. Group order is "first appearance"
  on both sides (MakeMyFigure `group_levels`, R `unique()`); contingency levels are sorted (pandas
  `crosstab`, R sorted factor levels).
* Where a *documented* convention had to be matched (e.g. scipy's exact-vs-asymptotic rule for the
  Mann–Whitney U, Breslow ties in Cox, `ddof = 0` z-scores), the R script applies the same convention
  **and** reports R's default alongside as `R_default.*` context rows (never scored, listed in
  `results/comparisons/statistics_R_convention_context.csv`). No threshold was changed to improve
  agreement; the classes `ACCEPTABLE_IMPLEMENTATION_DIFFERENCE` / `METHOD_MISMATCH` /
  `UPSTREAM_INPUT_DIFFERENCE` carry a cause string and are audited in `reports/DISCREPANCY_REPORT.md`.

## Re-running

```bash
# 1. R environment (micromamba, conda-forge + bioconda), once:
micromamba create -y -p /tmp/mm/envs/rval -c conda-forge -c bioconda "r-base=4.3" bioconductor-limma \
  bioconductor-edger bioconductor-deseq2 r-survival r-car r-rstatix r-effectsize r-mass r-dunn.test \
  r-proc r-matrixstats r-jsonlite r-data.table r-exactranktests r-boot
# 2. From the repository root:
python benchmarks/r_validation/python/generate_synthetic_data.py
python benchmarks/r_validation/python/export_make_my_figure_reference.py
for s in benchmarks/r_validation/R/0[1-9]*.R benchmarks/r_validation/R/1[0-5]*.R; do /tmp/mm/envs/rval/bin/Rscript "$s"; done
python benchmarks/r_validation/python/compare_outputs.py
```

The RSEM matrix (`GREEN-318289-STRANDED_RSEM_gene_count.2024-01-10_03-09-06.txt`, SHA-256
`37922f56…`) is byte-identical to the GEO GSE299655 supplementary file; it is never modified. Every
derived representation (filtered gene list: raw CPM > 1 in ≥ 4 samples, CPM, log-CPM, TMM, voom,
rounded copy for DESeq2) is a separate output with its transformation recorded.

Nothing in this folder is pushed, merged, tagged, released or published by the validation run.
