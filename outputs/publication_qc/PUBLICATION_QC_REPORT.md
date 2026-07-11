# v0.5 publication-readiness QC report

Consolidated findings. Every claim below was checked; unverified items are
labelled as such. See `docs/V0_5_PUBLICATION_QC_PLAN.md` for the plan and
`statistics_oracle_results.md` for the per-statistic table.

## 1. Statistics correctness — ✅ VALIDATED
Independent recomputation via scipy/statsmodels (`scripts/statistics_oracle.py`,
`tests/test_statistics_oracle_validation.py`): **62/62 field checks pass**.
Covered: Student's/Welch's t (+df, Cohen's d, mean-diff CI), Mann-Whitney U,
paired t (+dz), Wilcoxon, one-way ANOVA (+df1/df2, η²), two-way ANOVA (per term
vs `anova_lm`), Kruskal-Wallis, chi-square (+Yates, Cramér's V), Fisher (odds
ratio), log-rank (vs `survdiff`), Pearson/Spearman/linear regression (slope, p,
R²), Hedges g, and Bonferroni/Holm/BH corrections (vs `multipletests`).
- **Cox HR** uses statsmodels PHReg; reported as HR + Wald CI with the method
  sentence stating the **PH assumption is not auto-checked**. (Not independently
  oracle'd — same engine; treated as an estimate, not a hypothesis test.)

## 2. Statistical design safety — ✅ VALIDATED
- Paired t / Wilcoxon **without a subject/pair ID** → no statistic, no p-value,
  clear warning ("requires a subject/pair ID column"); nothing is drawn.
- RM-ANOVA requires subject + factor (guarded).
- Chi-square warns when expected counts < 5 and recommends Fisher.
- Fisher odds ratio reported only for 2×2 (warns otherwise).
- Ward linkage with a non-euclidean metric → friendly `ClusteringError`.
- Multiple-testing correction is applied across the **two-group family only**;
  omnibus F/H tests are not folded in.
- Volcano reads DE p-values **verbatim** (no recompute); heatmaps/networks/
  clustering invent **no** p-values.

## 3. RNA-seq — ✅ ACCURATE (no overpromise)
There is **no raw-count DE pipeline and no R dependency** (removed in v0.2) and
**no `RnaSeqSpec`**. Implemented and working: (a) precomputed DE table → volcano
with confirmable column detection and verbatim p-values; (b) normalized matrix →
heatmap / PCA / clustering. Docs state this correctly (README: "does not run a
differential-expression pipeline").

## 4. Statistical annotations — ✅ (invariant holds)
Renderers draw only values stored on `StatResult` (no ad-hoc recompute); hidden
fields remain in the exported StatsSpec. Verified by `test_stats_annotations`,
`test_annotation_formatting`, `test_stats_integration`, and the reproducibility
round-trip (annotation choices persist in the PlotSpec and reproduce).

## 5. Plots + publication quality — ✅ (37/37)
All 37 plot types render from bundled example data and pass
`qa/publication_check` for every style profile (`test_publication_style`,
`test_desktop_controller` render-every-example, `test_v04_plots`,
`test_v05_features`). Visual galleries: `outputs/style_qa_gallery/v0_5/`
(networks, clustering, volcano modes, manual annotations) and `reports/v04_qa/`.
Residual: dense force-directed networks can crowd node labels (warned + label
thinning); very crowded volcano label requests warn + cap.

## 6. Export + reproducibility — ✅ VALIDATED
`test_reproducibility_export_qc` (9 tests): SVG/PDF/PNG non-empty; SVG keeps
editable `<text>`; PlotSpec sidecar reloads and re-renders with matching
metadata (n_up/n_down, matrix_shape, n_clusters, n_labeled); manual annotations
round-trip and appear in the SVG.

## 7. GUI — ⚠️ PARTIAL (environment-limited)
- **Streamlit**: app-smoke **skipped in this sandbox** (streamlit not installed
  here); it runs where streamlit is present. Per-type rendering is verified
  independently of Streamlit (controller + publication-style tests).
- **Desktop (Qt)**: cannot launch headless here (no `libxkbcommon`/`libEGL`, no
  sudo). Pop-out/dock logic has Qt-guarded tests (`test_pop_out_panels`) that run
  in a real environment; the manager is additive + guarded so a failure can't
  block startup. **Action: manually smoke-test the desktop app + View → Pop Out
  before release.**

## 8. Documentation — ✅ audited
No overpromising found for RNA-seq/R/RnaSeqSpec. Pop-out docs state the desktop
scope + Streamlit limitation. Journal-like (not official) disclaimer intact.

## Test summary (this sandbox)
`python -m pytest -q -p no:pytest-qt --ignore=tests/test_desktop_gui.py` →
all pass; skips = Streamlit app-smoke (no streamlit) + Qt pop-out tests (no Qt),
both justified by the environment.

## Known limitations (release notes)
- Cox HR: PH assumption not auto-checked (estimate + CI only).
- Desktop pop-out unverified headless — needs a manual smoke-test.
- Networks/clustering are exploratory; correlation networks = association only.
- No raw-count DE / R pipeline; no `RnaSeqSpec`.
- Streamlit has no native pop-out (desktop-only), as documented.
