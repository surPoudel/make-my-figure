# v0.5 publication-readiness QC plan

A QC pass to confirm statistics, annotations, plots, exports, and reproducibility
are correct and publication-quality before release. Principle: **do not assume
correctness from passing tests** — validate against trusted oracles, and disable
(or clearly document) anything uncertain rather than returning questionable
results.

| # | Area | What is tested | Oracle / method | Pass criteria | High-risk |
|---|---|---|---|---|---|
| 1 | Statistics correctness | Every implemented test's statistic, df, p, effect size, CI | **scipy / statsmodels** recomputed independently (`scripts/statistics_oracle.py`) | all fields within tight rtol (1e-6 same-formula, 1e-4 cross-lib) | two-way/rm ANOVA, log-rank, CIs |
| 2 | Statistical design safety | Paired/subject requirements, table-size, family of correction | `statistics/validators.py` + tests | unsafe configs raise `StatsError`, not silent wrong results | paired without id, ward+metric |
| 3 | RNA-seq | Precomputed-DE→volcano; normalized matrix→heatmap | column detection + verbatim p-values | p read verbatim; **no** DE recompute | claiming an R pipeline (none exists) |
| 4 | Statistical annotations | Values come from stored `StatResult`; brackets align; stacking | annotation tests + invariant | renderer never recomputes stats | bracket/group alignment |
| 5 | Plot rendering | All 37 types render from example data | parametrized render tests | no crash; publication check passes | new types |
| 6 | Publication quality | Font sizes, clipping, legend overlap, contrast | `qa/publication_check.py` + visual gallery | check passes; gallery inspected | dense networks, crowded labels |
| 7 | Export | SVG/PDF/PNG non-empty; SVG/PDF vector text | export + round-trip tests | files > threshold; `<text>` in SVG | tight-bbox clipping |
| 8 | Reproducibility | PlotSpec / annotation round-trip re-renders identically | reload sidecar + re-render | key metadata reproduces | stat/annotation persistence |
| 9 | GUI (desktop) | Launch, pop-out/dock, no stale figures | Qt-guarded tests | run where Qt present | untestable headless |
| 10 | GUI (Streamlit) | Launch + per-type render | `streamlit.testing` app-smoke | runs where streamlit installed | skipped without streamlit |
| 11 | Documentation | Claims match implementation | manual audit | no overpromise | RNA-seq / pop-out claims |
| 12 | Known limitations | Documented honestly | this plan + reports | limitations listed | — |

## Trusted oracles
- **scipy.stats** — t-tests, Mann-Whitney, Wilcoxon, ANOVA (f_oneway), Kruskal-Wallis,
  chi-square, Fisher, Pearson/Spearman/linregress.
- **statsmodels** — two-way / RM ANOVA (`anova_lm`, `AnovaRM`), log-rank
  (`duration.survfunc.survdiff`), Cox PHReg, `multipletests` (BH/Holm/Bonferroni).
- **Hand-computed** — Cohen's d/dz, Hedges g, η², Cramér's V, CI formulas.

## Results
- `outputs/publication_qc/statistics_oracle_results.md` — the statistics table.
- `outputs/publication_qc/PUBLICATION_QC_REPORT.md` — consolidated findings.
- `outputs/publication_qc/{VISUAL,GUI,INSTALL_DEPENDENCY}_QC_*.md`.
- Galleries: `outputs/style_qa_gallery/v0_5/`, `reports/v04_qa/`.

## Known high-risk areas (watched closely)
- Cox HR uses statsmodels PHReg with the **PH assumption not auto-checked** (stated
  in the method sentence) — reported as an estimate + Wald CI only.
- Desktop pop-out panels are **unverified headless** (no Qt libs in CI/sandbox).
- Network/clustering are **exploratory** summaries; correlation networks are labelled
  as association, not mechanism.
