"""Export MakeMyFigure's numerical outputs for the independent R validation.

Everything here calls the *live* core API (``make_my_figure_core``) exactly as the
GUIs do — no re-implementation of any formula. Inputs are the frozen synthetic
datasets in ``data/synthetic/``, the bundled example datasets, and the RSEM matrix
at the repository root. Outputs go to ``results/python/`` only. This script never
reads anything from ``results/R/``.

Run from the repository root::

    python benchmarks/r_validation/python/export_make_my_figure_reference.py
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402
matplotlib.use("Agg")

from make_my_figure_core import clustering  # noqa: E402
from make_my_figure_core.differential import differential_screen  # noqa: E402
from make_my_figure_core.matrix_workflow.differential_summary import feature_differential_summary  # noqa: E402
from make_my_figure_core.matrix_workflow.matrix_spec import MatrixSpec, suggest_matrix_spec, looks_log_scale  # noqa: E402
from make_my_figure_core.matrix_workflow.metadata_spec import metadata_from_assignment  # noqa: E402
from make_my_figure_core.matrix_workflow.preprocessing import apply_step  # noqa: E402
from make_my_figure_core.matrix_workflow.qc_diagnostics import diagnose_matrix  # noqa: E402
from make_my_figure_core.matrix_workflow.transform_recommendations import recommend_preprocessing  # noqa: E402
from make_my_figure_core.plots.registry import render  # noqa: E402
from make_my_figure_core.recommendations import recommend_for_table  # noqa: E402
from make_my_figure_core.statistics import run_statistics  # noqa: E402
from make_my_figure_core.statistics.multiple_testing import adjust_pvalues  # noqa: E402
from make_my_figure_core.statistics.regression import glm_regression  # noqa: E402
from make_my_figure_core.statistics.schemas import default_stats_spec  # noqa: E402

DATA = HERE.parent / "data" / "synthetic"
META = HERE.parent / "data" / "metadata"
OUT = HERE.parent / "results" / "python"
RSEM = ROOT / "GREEN-318289-STRANDED_RSEM_gene_count.2024-01-10_03-09-06.txt"
RSEM_ANNOT = ["geneID", "geneSymbol", "bioType", "annotationLevel"]

# Minimal required PlotSpec envelope (input_table/output are schema-required; values are placeholders).
_SPEC_BASE = json.loads((ROOT / "examples" / "by_plot_type" / "roc" / "plotspec.json").read_text())
_SPEC_BASE = {k: _SPEC_BASE[k] for k in ("input_table", "output")}

STAT_ROWS: list = []
LABEL_ROWS: list = []


# ----------------------------------------------------------------------------- helpers
def _f(v):
    try:
        if v is None:
            return np.nan
        return float(v)
    except (TypeError, ValueError):
        return np.nan


def emit_result(dataset_id: str, r, test_override: str | None = None, comparison: str | None = None) -> None:
    """Flatten a StatResult into the shared long format."""
    test_id = test_override or r.test_id
    if comparison is None:
        if r.comparison_type in ("two_group",) and r.group_a is not None and r.group_b is not None:
            comparison = f"{r.group_a}|{r.group_b}"
            if r.extra and r.extra.get("within_x"):
                comparison = f"{r.extra['x_level']}:{comparison}"
        elif r.comparison_type == "survival" and r.group_a is not None:
            comparison = f"{r.group_a}|{r.group_b}"
        elif r.extra and r.extra.get("term"):
            comparison = str(r.extra["term"])
        elif r.group_a is not None:
            comparison = str(r.group_a)
        else:
            comparison = "all"
    quantities = {
        "statistic": r.statistic, "df": r.df, "df2": getattr(r, "df2", None),
        "p_value": r.p_value, "adjusted_p_value": r.adjusted_p_value,
        "estimate": r.estimate, "ci_low": r.confidence_interval_low,
        "ci_high": r.confidence_interval_high, "effect_size": r.effect_size,
        "n_total": r.n_total,
    }
    for k, v in (r.extra or {}).items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            quantities[f"extra.{k}"] = v
        elif isinstance(v, dict):
            for kk, vv in v.items():
                if isinstance(vv, (int, float)) and not isinstance(vv, bool):
                    quantities[f"extra.{k}.{kk}"] = vv
    for q, v in quantities.items():
        STAT_ROWS.append({"dataset_id": dataset_id, "test_id": test_id, "comparison": comparison,
                          "quantity": q, "value": _f(v)})
    LABEL_ROWS.append({"dataset_id": dataset_id, "test_id": test_id, "comparison": comparison,
                       "statistic_name": r.statistic_name, "effect_size_name": r.effect_size_name,
                       "estimate_name": r.estimate_name, "correction_method": r.correction_method,
                       "warnings": " || ".join(r.warnings or [])})


def run(dataset_id: str, df: pd.DataFrame, plot_type: str, mapping: dict, **spec_over):
    spec = default_stats_spec()
    spec.update({"enabled": True, "correction": "none", "comparison_mode": "all_pairs"})
    spec.update(spec_over)
    report = run_statistics(df, spec, plot_type=plot_type, mapping=mapping)
    for r in report.results:
        emit_result(dataset_id, r)
    return report


def load(name: str) -> pd.DataFrame:
    sep = "\t" if name.endswith(".tsv") else ","
    return pd.read_csv(DATA / name, sep=sep)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_matrix(tag: str, df: pd.DataFrame, id_col: str, cols: list) -> None:
    out = df[[id_col] + cols].copy()
    out.to_csv(OUT / f"transform__{tag}.csv", index=False, float_format="%.15g")


# ----------------------------------------------------------------------------- statistics
def statistics_synthetic() -> None:
    box = "boxplot_or_violin_with_points"
    for ds in ["A_two_group_normal", "B_two_group_unequal_var", "C_two_group_ties",
               "D_two_group_small_n", "E_two_group_one_constant"]:
        df = load(ds + ".csv")
        for test in ["students_t", "welch_t", "mann_whitney"]:
            run(ds, df, box, {"x": "group", "y": "value"}, test=test,
                value_column="value", group_column="group")
    for ds in ["F_paired_normal", "G_paired_zeros_ties"]:
        df = load(ds + ".csv")
        for test in ["paired_t", "wilcoxon"]:
            run(ds, df, box, {"x": "condition", "y": "value"}, test=test,
                value_column="value", group_column="condition", subject_column="subject")
    for ds, g, v in [("H_three_groups_balanced", "dose", "response"),
                     ("I_five_groups_unbalanced", "group", "score")]:
        df = load(ds + ".csv")
        run(ds, df, box, {"x": g, "y": v}, test="one_way_anova", value_column=v, group_column=g)
        run(ds, df, box, {"x": g, "y": v}, test="kruskal_wallis", value_column=v, group_column=g)
        # Dunn post-hoc: raw p (correction none) and BH-adjusted family
        rep = run(ds, df, box, {"x": g, "y": v}, test="kruskal_wallis", value_column=v,
                  group_column=g, posthoc=True)
        rep2 = run_statistics(df, {**default_stats_spec(), "enabled": True, "test": "kruskal_wallis",
                                   "posthoc": True, "correction": "benjamini_hochberg",
                                   "value_column": v, "group_column": g},
                              plot_type=box, mapping={"x": g, "y": v})
        for r in rep2.results:
            if r.test_id == "dunn":
                emit_result(ds, r, test_override="dunn_bh")
        # pairwise Welch family with BH / Holm / Bonferroni through the runner
        for corr in ["benjamini_hochberg", "holm", "bonferroni"]:
            rep3 = run_statistics(df, {**default_stats_spec(), "enabled": True, "test": "welch_t",
                                       "comparison_mode": "all_pairs", "correction": corr,
                                       "value_column": v, "group_column": g},
                                  plot_type=box, mapping={"x": g, "y": v})
            for r in rep3.results:
                emit_result(ds, r, test_override=f"welch_t_{corr}")
        del rep
    for ds in ["J_two_way_balanced", "K_two_way_unbalanced"]:
        df = load(ds + ".csv")
        run(ds, df, "grouped_barplot_with_error_bar", {"x": "genotype", "y": "value", "group": "treatment"},
            test="two_way_anova", value_column="value", group_column="genotype",
            subgroup_column="treatment")
        # within-x Welch family (grouped plot default)
        run(ds, df, "grouped_barplot_with_error_bar", {"x": "genotype", "y": "value", "group": "treatment"},
            test="welch_t", comparison_mode="within_x", value_column="value",
            group_column="genotype", subgroup_column="treatment")
    df = load("L_repeated_measures.csv")
    run("L_repeated_measures", df, box, {"x": "time", "y": "value"}, test="rm_anova",
        value_column="value", group_column="time", subject_column="subject")
    for ds in ["M_linear_xy", "N_monotone_nonlinear_ties"]:
        df = load(ds + ".csv")
        for test in ["pearson", "spearman", "linear_regression"]:
            run(ds, df, "scatterplot_with_regression", {"x": "x", "y": "y"}, test=test,
                x_column="x", y_column="y")
    for ds, r_, c_ in [("O_contingency_2x2", "arm", "response"), ("P_contingency_3x4", "subtype", "grade"),
                       ("Q_contingency_small_expected", "arm", "response")]:
        df = load(ds + ".csv")
        for test in ["chi_square", "fishers_exact"]:
            run(ds, df, "stacked_bar_composition", {"x": r_, "group": c_}, test=test,
                row_column=r_, col_column=c_)
    for ds in ["R_survival_two_groups", "S_survival_three_groups"]:
        df = load(ds + ".csv")
        for test in ["logrank", "cox_ph"]:
            run(ds, df, "kaplan_meier_survival_curve", {"time": "time", "event": "event", "group": "group"},
                test=test, time_column="time", event_column="event", group_column="group")
    # GLM families
    df = load("T_glm_predictors.csv")
    for fam, y in [("gaussian", "y_gauss"), ("binomial", "y_binom"), ("poisson", "y_pois"),
                   ("negativebinomial", "y_negbin"), ("gamma", "y_gamma")]:
        try:
            rep = glm_regression(df, response=y, predictors=["x1", "x2"], family=fam, alpha=0.05)
            for r in rep.results:
                term = (r.extra or {}).get("term") or r.group_a or r.value_column
                emit_result("T_glm_predictors", r, test_override=f"glm_{fam}", comparison=str(term))
        except Exception as exc:  # noqa: BLE001
            LABEL_ROWS.append({"dataset_id": "T_glm_predictors", "test_id": f"glm_{fam}", "comparison": "all",
                               "warnings": f"ERROR: {exc}"})


def statistics_examples() -> None:
    root = ROOT / "examples" / "statistics"
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        ps = json.loads((folder / "plotspec.json").read_text())
        ss = json.loads((folder / "statsspec.json").read_text())
        df = pd.read_csv(folder / "data.csv")
        ss = dict(ss); ss["enabled"] = True
        rep = run_statistics(df, ss, plot_type=ps["plot_type"], mapping=ps.get("mapping", {}))
        for r in rep.results:
            emit_result(f"ex_{folder.name}", r)


def multiple_testing() -> None:
    rows = []
    for ds in ["U_pvalues", "V_pvalues_with_na"]:
        p = pd.read_csv(DATA / ds + ".csv" if False else DATA / f"{ds}.csv")["p"].tolist()
        p = [None if (x is None or (isinstance(x, float) and np.isnan(x))) else float(x) for x in p]
        for method in ["bonferroni", "holm", "benjamini_hochberg"]:
            adj, rej, canon = adjust_pvalues(p, method=method)
            for i, (pi, ai) in enumerate(zip(p, adj)):
                rows.append({"dataset_id": ds, "method": method, "index": i + 1,
                             "p": np.nan if pi is None else pi, "p_adj": np.nan if ai is None else ai})
    pd.DataFrame(rows).to_csv(OUT / "multiple_testing.csv", index=False, float_format="%.15g")


# ----------------------------------------------------------------------------- matrices
def _spec(df: pd.DataFrame, id_col: str, cols: list, value_type: str, annot: list | None = None) -> MatrixSpec:
    return MatrixSpec(feature_id_column=id_col, value_columns=list(cols),
                      annotation_columns=list(annot or []), value_type=value_type, confirmed_by_user=True)


def _step(tag: str, df, spec, method, params=None):
    new_df, new_spec, step = apply_step(df, spec, method, params=params or {})
    write_matrix(tag, new_df, spec.feature_id_column, spec.value_columns)
    return new_df, new_spec, step


def qc_json(tag: str, df, spec) -> dict:
    q = diagnose_matrix(df, spec).to_dict()
    q["_looks_log_scale"] = bool(looks_log_scale(df, spec.value_columns))
    (OUT / f"qc__{tag}.json").write_text(json.dumps(q, indent=1, default=str))
    recs = recommend_preprocessing(diagnose_matrix(df, spec))
    (OUT / f"preprocessing_recommendations__{tag}.json").write_text(json.dumps(
        [{"name": r.name, "steps": r.steps, "reason": r.reason, "assumptions": r.assumptions,
          "warnings": r.warnings} for r in recs], indent=1, default=str))
    return q


def pca_export(tag: str, df: pd.DataFrame, id_col: str, cols: list) -> None:
    """PCA exactly as the app draws it: render the plot and read the plotted coordinates."""
    spec = {"plot_type": "pca_scatter_from_matrix", "journal_style": "publication",
            "mapping": {"matrix_row_id": id_col, "value_columns": list(cols)}, **_SPEC_BASE}
    res = render(spec, df[[id_col] + cols])
    ax = res.figure.axes[0]
    xs, ys = [], []
    for coll in ax.collections:
        off = coll.get_offsets()
        for x, y in np.asarray(off):
            xs.append(float(x)); ys.append(float(y))
    pd.DataFrame({"sample": cols[:len(xs)], "PC1": xs, "PC2": ys}).to_csv(
        OUT / f"pca__{tag}.csv", index=False, float_format="%.15g")
    lab = {"x_label": ax.get_xlabel(), "y_label": ax.get_ylabel()}
    lab.update({k: v for k, v in res.metadata.items() if k in ("explained_variance_ratio", "n_samples", "n_features")})
    (OUT / f"pca__{tag}.json").write_text(json.dumps(lab, indent=1, default=str))
    matplotlib.pyplot.close(res.figure)


def clustering_export(tag: str, mat: np.ndarray, labels: list, method: str, metric: str) -> None:
    from scipy.cluster.hierarchy import cophenet
    z = clustering.compute_linkage(mat, method=method, metric=metric, axis="rows")
    coph = cophenet(z)
    n = len(labels); rows = []
    k = 0
    for i in range(n):
        for j in range(i + 1, n):
            rows.append({"a": labels[i], "b": labels[j], "cophenetic": float(coph[k])}); k += 1
    pd.DataFrame(rows).to_csv(OUT / f"cluster__{tag}__{method}_{metric}.csv", index=False, float_format="%.15g")
    pd.DataFrame({"height": np.sort(z[:, 2])}).to_csv(
        OUT / f"cluster_heights__{tag}__{method}_{metric}.csv", index=False, float_format="%.15g")


def matrices_synthetic() -> None:
    # W: counts
    W = load("W_count_matrix.tsv"); wcols = [c for c in W.columns if c not in ("gene_id", "biotype")]
    sW = _spec(W, "gene_id", wcols, "raw_numeric", ["biotype"])
    qc_json("W", W, sW)
    _step("W__total_sum_1e6", W, sW, "total_sum", {"scale_factor": 1e6})
    _step("W__cpm", W, sW, "cpm", {"log": False})
    _step("W__logcpm_prior0.5", W, sW, "cpm", {"log": True, "prior_count": 0.5})
    _step("W__logcpm_prior2", W, sW, "cpm", {"log": True, "prior_count": 2.0})
    _, _, st = _step("W__tmm_cpm", W, sW, "tmm", {"log": False})
    pd.DataFrame({"sample": wcols, "norm_factor": st.parameters["norm_factors"]}).to_csv(
        OUT / "tmm_factors__W.csv", index=False, float_format="%.15g")
    _step("W__tmm_logcpm_prior0.5", W, sW, "tmm", {"log": True, "prior_count": 0.5})
    _step("W__voom_logcpm", W, sW, "voom", {})
    _step("W__log2_pc1", W, sW, "log2", {"pseudocount": 1.0})
    _step("W__log10_pc1", W, sW, "log10", {"pseudocount": 1.0})
    _step("W__ln_pc1", W, sW, "ln", {"pseudocount": 1.0})
    _step("W__upper_quartile", W, sW, "upper_quartile", {})
    _step("W__median_scale", W, sW, "median_scale", {})
    _step("W__quantile", W, sW, "quantile", {})
    _step("W__sqrt", W, sW, "sqrt", {})
    _step("W__arcsinh_cf5", W, sW, "arcsinh", {"cofactor": 5.0})
    _step("W__winsorize_1_99", W, sW, "winsorize", {"lower": 1.0, "upper": 99.0})
    _step("W__row_zscore_ddof0", W, sW, "row_zscore", {})
    _step("W__zscore_row_ddof1", W, sW, "zscore", {"axis": "row", "ddof": 1})
    _step("W__column_zscore_ddof0", W, sW, "column_zscore", {})
    _step("W__global_zscore_ddof0", W, sW, "global_zscore", {})
    _step("W__standard_scale", W, sW, "standard_scale", {})
    _step("W__robust_scale_row", W, sW, "robust_scale", {"axis": "row"})
    _step("W__robust_scale_column", W, sW, "robust_scale", {"axis": "column"})
    _step("W__robust_scale_global", W, sW, "robust_scale", {"axis": "global"})
    for mode in ["sample_median", "feature_mean", "feature_median", "grand_median"]:
        _step(f"W__center_{mode}", W, sW, "center", {"mode": mode})
    _step("W__control_features_median_divide", W, sW, "control_features",
          {"feature_ids": ["gene0100", "gene0101", "gene0102", "gene0103", "gene0104"], "how": "median", "operation": "divide"})
    _step("W__internal_standard_features_mean_subtract", W, sW, "internal_standard_features",
          {"feature_ids": ["gene0100", "gene0101", "gene0102"], "how": "mean", "operation": "subtract"})
    _step("W__internal_standard_columns_median_divide", W, sW, "internal_standard_columns",
          {"is_columns": ["A_1", "A_2"], "how": "median", "operation": "divide"})
    _step("W__reference_sample_A_1_divide", W, sW, "reference_sample", {"reference": "A_1", "operation": "divide"})
    fdf, _, fstep = apply_step(W, sW, "filter", params={"max_zero_frac": 0.5, "drop_constant": True})
    pd.DataFrame({"gene_id": fdf["gene_id"]}).to_csv(OUT / "filter__W__maxzero0.5_dropconst.csv", index=False)
    fdf2, _, _ = apply_step(W, sW, "filter", params={"top_variable_n": 100})
    pd.DataFrame({"gene_id": fdf2["gene_id"]}).to_csv(OUT / "filter__W__top100var.csv", index=False)
    # DE on W: voom logCPM -> differential_screen (welch, student, MWU) and feature_differential_summary
    voom_df, voom_spec, _ = apply_step(W, sW, "voom", params={})
    labels = {c: ("A" if c.startswith("A_") else "B") for c in wcols}
    for test in ["welch_t", "students_t", "mann_whitney"]:
        res = differential_screen(voom_df, feature_col="gene_id", group_labels=labels, test=test,
                                  log_input=True, reference_group="A")
        res.table.to_csv(OUT / f"de_screen__W_voom__{test}.csv", index=False, float_format="%.15g")
    meta = metadata_from_assignment(labels)
    for test in ["welch_t", "students_t", "mann_whitney"]:
        summ = feature_differential_summary(voom_df, voom_spec, meta, group_a="B", group_b="A", test=test,
                                            correction="benjamini_hochberg")
        summ.table.to_csv(OUT / f"de_summary__W_voom__{test}.csv", index=False, float_format="%.15g")
    # linear-scale summary (ratio fold change with pseudocount) on CPM
    cpm_df, cpm_spec, _ = apply_step(W, sW, "cpm", params={"log": False})
    summ = feature_differential_summary(cpm_df, cpm_spec, meta, group_a="B", group_b="A", test="welch_t",
                                        correction="benjamini_hochberg", pseudocount=1.0)
    summ.table.to_csv(OUT / "de_summary__W_cpm__welch_t.csv", index=False, float_format="%.15g")
    # raw-count screen on the un-normalised matrix (should carry the raw-count warning)
    res = differential_screen(W, feature_col="gene_id", group_labels=labels, test="welch_t", log_input=False,
                              reference_group="A")
    res.table.to_csv(OUT / "de_screen__W_raw__welch_t_linear.csv", index=False, float_format="%.15g")
    (OUT / "de_screen__W_raw__warnings.json").write_text(json.dumps(res.warnings, indent=1))
    pca_export("W_voom", voom_df, "gene_id", wcols)
    mat = voom_df[wcols].to_numpy(float)
    for method, metric in [("average", "euclidean"), ("complete", "euclidean"), ("single", "euclidean"),
                           ("ward", "euclidean"), ("average", "correlation")]:
        clustering_export("W_voom_samples", mat.T, wcols, method, metric)
    # Class-A targets on plain log2-CPM (prior 0.5; no TMM) — this input is cell-wise identical on both sides,
    # so PCA / clustering / DE differences here isolate the component itself from the TMM tie-handling difference.
    lc_df, lc_spec, _ = apply_step(W, sW, "cpm", params={"log": True, "prior_count": 0.5})
    pca_export("W_logcpm", lc_df, "gene_id", wcols)
    mat = lc_df[wcols].to_numpy(float)
    for method, metric in [("average", "euclidean"), ("complete", "euclidean"), ("ward", "euclidean"), ("average", "correlation")]:
        clustering_export("W_logcpm_samples", mat.T, wcols, method, metric)
    for test in ["welch_t", "students_t", "mann_whitney"]:
        res = differential_screen(lc_df, feature_col="gene_id", group_labels=labels, test=test, log_input=True, reference_group="A")
        res.table.to_csv(OUT / f"de_screen__W_logcpm__{test}.csv", index=False, float_format="%.15g")
        summ = feature_differential_summary(lc_df, lc_spec, meta, group_a="B", group_b="A", test=test, correction="benjamini_hochberg")
        summ.table.to_csv(OUT / f"de_summary__W_logcpm__{test}.csv", index=False, float_format="%.15g")

    # X: intensities with missing values
    X = load("X_intensity_matrix_missing.tsv"); xcols = [c for c in X.columns if c != "protein"]
    sX = _spec(X, "protein", xcols, "raw_numeric")
    qc_json("X", X, sX)
    for tag, m, p in [("log2_pc1", "log2", {"pseudocount": 1.0}), ("ln_pc1", "ln", {"pseudocount": 1.0}),
                      ("log10_pc1", "log10", {"pseudocount": 1.0}), ("arcsinh_cf5", "arcsinh", {"cofactor": 5.0}),
                      ("sqrt", "sqrt", {}), ("median_scale", "median_scale", {}), ("total_sum_1e6", "total_sum", {"scale_factor": 1e6}),
                      ("upper_quartile", "upper_quartile", {}), ("row_zscore_ddof0", "row_zscore", {}),
                      ("column_zscore_ddof0", "column_zscore", {}), ("robust_scale_row", "robust_scale", {"axis": "row"}),
                      ("robust_scale_column", "robust_scale", {"axis": "column"}),
                      ("impute_feature_median", "impute", {"strategy": "feature_median"}),
                      ("impute_sample_median", "impute", {"strategy": "sample_median"}),
                      ("impute_constant0", "impute", {"strategy": "constant", "constant": 0.0}),
                      ("winsorize_1_99", "winsorize", {"lower": 1.0, "upper": 99.0}),
                      ("quantile", "quantile", {}),
                      ("center_sample_median", "center", {"mode": "sample_median"}),
                      ("center_feature_median", "center", {"mode": "feature_median"})]:
        _step(f"X__{tag}", X, sX, m, p)
    fdf, _, _ = apply_step(X, sX, "filter", params={"max_missing_frac": 0.1})
    pd.DataFrame({"protein": fdf["protein"]}).to_csv(OUT / "filter__X__maxmissing0.1.csv", index=False)

    # Y: log-like with negatives
    Y = load("Y_log_matrix_negatives.tsv"); ycols = [c for c in Y.columns if c != "feature"]
    sY = _spec(Y, "feature", ycols, "log_normalized")
    qc_json("Y", Y, sY)
    for tag, m, p in [("row_zscore_ddof0", "row_zscore", {}), ("zscore_row_ddof1", "zscore", {"axis": "row", "ddof": 1}),
                      ("column_zscore_ddof0", "column_zscore", {}), ("global_zscore_ddof0", "global_zscore", {}),
                      ("standard_scale", "standard_scale", {}), ("center_feature_mean", "center", {"mode": "feature_mean"}),
                      ("center_grand_median", "center", {"mode": "grand_median"}), ("robust_scale_row", "robust_scale", {"axis": "row"}),
                      ("arcsinh_cf5", "arcsinh", {"cofactor": 5.0}), ("quantile", "quantile", {}),
                      ("log2_pc1", "log2", {"pseudocount": 1.0})]:
        _step(f"Y__{tag}", Y, sY, m, p)
    pca_export("Y", Y, "feature", ycols)
    mat = Y[ycols].to_numpy(float)
    for method, metric in [("average", "euclidean"), ("complete", "euclidean"), ("single", "euclidean"),
                           ("ward", "euclidean"), ("average", "correlation"), ("complete", "cityblock"),
                           ("average", "cosine")]:
        clustering_export("Y_features", mat, Y["feature"].tolist(), method, metric)
        clustering_export("Y_samples", mat.T, ycols, method, metric)
    # heatmap-side scaling helpers (clustering.scale_matrix) — used by heatmap/hier-clustering plots
    for sc in ["row_zscore", "column_zscore", "center_rows", "log", "log_zscore"]:
        scaled, _w = clustering.scale_matrix(mat, sc)
        out = pd.DataFrame(scaled, columns=ycols); out.insert(0, "feature", Y["feature"])
        out.to_csv(OUT / f"transform__Y__heatmap_scale_{sc}.csv", index=False, float_format="%.15g")
    # meta-group DE on Y (already log): feature_differential_summary with anova/kruskal (multi-group)
    labels = {c: ("g1" if i < 3 else "g2" if i < 6 else "g3") for i, c in enumerate(ycols)}
    meta = metadata_from_assignment(labels)
    for test in ["anova", "kruskal"]:
        summ = feature_differential_summary(Y, sY, meta, group_a="g1", test=test, correction="holm")
        summ.table.to_csv(OUT / f"de_summary__Y__{test}.csv", index=False, float_format="%.15g")
    for test in ["welch_t", "paired_t", "wilcoxon"]:
        summ = feature_differential_summary(Y, sY, meta, group_a="g1", group_b="g2", test=test, correction="bonferroni")
        summ.table.to_csv(OUT / f"de_summary__Y__{test}.csv", index=False, float_format="%.15g")

    # Z: ties / constant row
    Z = load("Z_small_integer_matrix_ties.tsv"); zcols = [c for c in Z.columns if c != "id"]
    sZ = _spec(Z, "id", zcols, "raw_numeric")
    qc_json("Z", Z, sZ)
    for tag, m, p in [("quantile", "quantile", {}), ("row_zscore_ddof0", "row_zscore", {}),
                      ("robust_scale_row", "robust_scale", {"axis": "row"}), ("median_scale", "median_scale", {}),
                      ("upper_quartile", "upper_quartile", {}), ("total_sum_1e6", "total_sum", {"scale_factor": 1e6})]:
        _step(f"Z__{tag}", Z, sZ, m, p)


# ----------------------------------------------------------------------------- RSEM
def rsem() -> dict:
    raw = pd.read_csv(RSEM, sep="\t")
    cols = [c for c in raw.columns if c not in RSEM_ANNOT]
    spec = _spec(raw, "geneID", cols, "raw_numeric", RSEM_ANNOT[1:])
    vals = raw[cols].to_numpy(float)
    info = {
        "file": RSEM.name, "sha256": sha256(RSEM), "bytes": RSEM.stat().st_size,
        "shape": list(raw.shape), "annotation_columns": RSEM_ANNOT, "n_samples": len(cols),
        "min": float(np.nanmin(vals)), "max": float(np.nanmax(vals)),
        "n_cells": int(vals.size), "n_nonzero": int((vals != 0).sum()),
        "fraction_zero": float((vals == 0).mean()),
        "fraction_non_integer": float((np.mod(vals, 1) != 0).mean()),
        "n_non_integer_cells": int((np.mod(vals, 1) != 0).sum()),
        "fraction_rows_all_zero": float((vals.sum(axis=1) == 0).mean()),
        "library_sizes": {c: float(vals[:, i].sum()) for i, c in enumerate(cols)},
        "duplicate_geneID": int(raw["geneID"].duplicated().sum()),
        "duplicate_geneSymbol": int(raw["geneSymbol"].duplicated().sum()),
        "suggested_matrix_spec": suggest_matrix_spec(raw, source_file=RSEM.name).to_dict(),
    }
    (OUT / "rsem_characterisation.json").write_text(json.dumps(info, indent=1, default=str))
    qc_json("RSEM", raw, spec)
    # data-recommendation engine on the raw table (as the app sees it)
    rec = recommend_for_table(raw, table_name=RSEM.name)
    (OUT / "recommendations__RSEM.json").write_text(json.dumps(rec.to_dict() if hasattr(rec, "to_dict") else str(rec),
                                                              indent=1, default=str))
    # shared deterministic gene filter: raw CPM > 1 in >= 4 samples
    lib = vals.sum(axis=0)
    cpm_raw = vals / lib * 1e6
    keep = (cpm_raw > 1).sum(axis=1) >= 4
    filt = raw.loc[keep].reset_index(drop=True)
    pd.DataFrame({"geneID": filt["geneID"]}).to_csv(OUT / "rsem_filtered_genes.csv", index=False)
    fspec = _spec(filt, "geneID", cols, "raw_numeric", RSEM_ANNOT[1:])
    _step("RSEM__cpm", filt, fspec, "cpm", {"log": False})
    _step("RSEM__logcpm_prior0.5", filt, fspec, "cpm", {"log": True, "prior_count": 0.5})
    _step("RSEM__logcpm_prior2", filt, fspec, "cpm", {"log": True, "prior_count": 2.0})
    _, _, st = _step("RSEM__tmm_cpm", filt, fspec, "tmm", {"log": False})
    pd.DataFrame({"sample": cols, "norm_factor": st.parameters["norm_factors"]}).to_csv(
        OUT / "tmm_factors__RSEM.csv", index=False, float_format="%.15g")
    voom_df, voom_spec, _ = _step("RSEM__voom_logcpm", filt, fspec, "voom", {})
    _step("RSEM__log2_pc1", filt, fspec, "log2", {"pseudocount": 1.0})
    _step("RSEM__total_sum_1e6", filt, fspec, "total_sum", {"scale_factor": 1e6})
    _step("RSEM__upper_quartile", filt, fspec, "upper_quartile", {})
    _step("RSEM__median_scale", filt, fspec, "median_scale", {})
    # Sample -> group from the GEO-confirmed mapping (data/metadata/geo_sample_map.csv)
    gmap = pd.read_csv(META / "geo_sample_map.csv")
    name_to_group = {}
    for c in cols:
        lib_name = c.split("_", 1)[1]  # e.g. 2686012_Ctrl_1 -> Ctrl_1
        row = gmap[gmap["library_name"] == lib_name]
        name_to_group[c] = str(row["genotype"].iloc[0]) if len(row) else lib_name.rsplit("_", 1)[0]
    pd.DataFrame({"sample": cols, "group": [name_to_group[c] for c in cols]}).to_csv(
        META / "rsem_sample_groups.csv", index=False)
    ref = "Parental"
    for grp in sorted(set(name_to_group.values()) - {ref}):
        labels = {c: g for c, g in name_to_group.items() if g in (ref, grp)}
        res = differential_screen(voom_df, feature_col="geneID", group_labels=labels, test="welch_t",
                                  log_input=True, reference_group=ref)
        tag = grp.replace("/", "-").replace(" ", "_")
        res.table.to_csv(OUT / f"de_screen__RSEM_voom__welch_t__{tag}_vs_Parental.csv", index=False, float_format="%.15g")
        meta = metadata_from_assignment(labels)
        summ = feature_differential_summary(voom_df, voom_spec, meta, group_a=grp, group_b=ref, test="welch_t",
                                            correction="benjamini_hochberg")
        summ.table.to_csv(OUT / f"de_summary__RSEM_voom__welch_t__{tag}_vs_Parental.csv", index=False, float_format="%.15g")
    pca_export("RSEM_voom", voom_df, "geneID", cols)
    mat = voom_df[cols].to_numpy(float)
    for method, metric in [("average", "euclidean"), ("complete", "euclidean"), ("ward", "euclidean"),
                           ("average", "correlation")]:
        clustering_export("RSEM_voom_samples", mat.T, cols, method, metric)
    lc_df, lc_spec, _ = apply_step(filt, fspec, "cpm", params={"log": True, "prior_count": 0.5})
    pca_export("RSEM_logcpm", lc_df, "geneID", cols)
    mat = lc_df[cols].to_numpy(float)
    for method, metric in [("average", "euclidean"), ("complete", "euclidean"), ("ward", "euclidean"), ("average", "correlation")]:
        clustering_export("RSEM_logcpm_samples", mat.T, cols, method, metric)
    for grp in sorted(set(name_to_group.values()) - {ref}):
        labels = {c: g for c, g in name_to_group.items() if g in (ref, grp)}
        tag = grp.replace("/", "-").replace(" ", "_")
        res = differential_screen(lc_df, feature_col="geneID", group_labels=labels, test="welch_t", log_input=True, reference_group=ref)
        res.table.to_csv(OUT / f"de_screen__RSEM_logcpm__welch_t__{tag}_vs_Parental.csv", index=False, float_format="%.15g")
    return info


# ----------------------------------------------------------------------------- plot-derived statistics
def plot_derived() -> None:
    root = ROOT / "examples" / "by_plot_type"
    out: dict = {}
    for slug in ["roc", "precision_recall", "calibration", "confusion_matrix", "bland_altman", "dose_response",
                 "qq", "scatter", "kaplan_meier", "manhattan", "volcano", "heatmap", "hier_clustering",
                 "dendrogram", "pca", "network", "histogram", "enrichment", "ma_plot"]:
        folder = root / slug
        if not folder.exists():
            continue
        ps = json.loads((folder / "plotspec.json").read_text())
        df = pd.read_csv(folder / "data.csv")
        spec = {k: v for k, v in ps.items() if k in ("plot_type", "mapping", "journal_style", "layout", "input_table", "output")}
        spec.setdefault("journal_style", "publication")
        for k, v in _SPEC_BASE.items():
            spec.setdefault(k, v)
        aux = None
        if slug == "pca":
            mpath = folder / "metadata.csv"
            if mpath.exists():
                aux = {"metadata": pd.read_csv(mpath)}
        try:
            res = render(spec, df, aux=aux) if aux is not None else render(spec, df)
        except TypeError:
            res = render(spec, df)
        except Exception as exc:  # noqa: BLE001
            out[slug] = {"error": str(exc)}
            continue
        meta = {k: v for k, v in res.metadata.items()
                if k not in ("plot_spec", "style", "disclaimer", "software_versions")}
        entry = {"plot_type": ps["plot_type"], "metadata": meta, "warnings": list(res.warnings)}
        ax = res.figure.axes[0]
        entry["axis_labels"] = [ax.get_xlabel(), ax.get_ylabel()]
        entry["texts"] = [t.get_text() for t in ax.texts][:20]
        entry["legend"] = [t.get_text() for t in (ax.get_legend().get_texts() if ax.get_legend() else [])]
        if slug in ("scatter", "kaplan_meier", "roc", "precision_recall", "calibration", "bland_altman", "dose_response", "qq"):
            lines = []
            for ln in ax.lines:
                xd, yd = ln.get_xdata(), ln.get_ydata()
                lines.append({"label": ln.get_label(), "n": int(len(xd)),
                              "x": [float(v) for v in np.asarray(xd, float)[:400]],
                              "y": [float(v) for v in np.asarray(yd, float)[:400]]})
            entry["lines"] = lines
        out[slug] = entry
        matplotlib.pyplot.close(res.figure)
    (OUT / "plot_derived_statistics.json").write_text(json.dumps(out, indent=1, default=str))
    # data-recommendation engine on every bundled example table
    recs = {}
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        df = pd.read_csv(folder / "data.csv")
        try:
            r = recommend_for_table(df, table_name=folder.name)
            recs[folder.name] = r.to_dict() if hasattr(r, "to_dict") else str(r)
        except Exception as exc:  # noqa: BLE001
            recs[folder.name] = {"error": str(exc)}
    for name in ["W_count_matrix.tsv", "X_intensity_matrix_missing.tsv", "Y_log_matrix_negatives.tsv",
                 "Z_small_integer_matrix_ties.tsv", "A_two_group_normal.csv", "F_paired_normal.csv",
                 "M_linear_xy.csv", "O_contingency_2x2.csv", "R_survival_two_groups.csv", "T_glm_predictors.csv"]:
        df = load(name)
        r = recommend_for_table(df, table_name=name)
        recs[name] = r.to_dict() if hasattr(r, "to_dict") else str(r)
    (OUT / "recommendations__examples.json").write_text(json.dumps(recs, indent=1, default=str))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*"):
        old.unlink()
    statistics_synthetic()
    statistics_examples()
    multiple_testing()
    pd.DataFrame(STAT_ROWS).to_csv(OUT / "statistics_python.csv", index=False, float_format="%.15g")
    pd.DataFrame(LABEL_ROWS).to_csv(OUT / "statistics_python_labels.csv", index=False)
    matrices_synthetic()
    info = rsem()
    plot_derived()
    import scipy, statsmodels, matplotlib as mpl  # noqa: E402
    from make_my_figure_core.version import __version__
    env = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version, "platform": platform.platform(),
        "numpy": np.__version__, "scipy": scipy.__version__, "pandas": pd.__version__,
        "statsmodels": statsmodels.__version__, "matplotlib": mpl.__version__,
        "make_my_figure_core": __version__,
        "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
        "rsem_sha256": info["sha256"],
    }
    (HERE.parent / "results" / "python_environment.txt").write_text("\n".join(f"{k}: {v}" for k, v in env.items()) + "\n")
    print(f"exported {len(list(OUT.glob('*')))} files; {len(STAT_ROWS)} statistic rows")


if __name__ == "__main__":
    main()
