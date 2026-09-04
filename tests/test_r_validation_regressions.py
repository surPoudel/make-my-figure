"""Regression tests for defects found by the independent R validation
(benchmarks/r_validation/reports/DISCREPANCY_REPORT.md)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from make_my_figure_core.statistics import categorical


def _rxc_table() -> pd.DataFrame:
    # Frozen 3x4 table (data/synthetic/P_contingency_3x4.csv crosstab at the time of the finding).
    return pd.DataFrame([[19, 21, 15, 11], [16, 18, 13, 16], [12, 5, 17, 17]],
                        index=["s1", "s2", "s3"], columns=["g1", "g2", "g3", "g4"])


def test_fisher_rxc_is_reproducible():
    """Before the fix, scipy's default r x c Fisher p-value was an unseeded Monte Carlo
    estimate: five consecutive calls on the same table gave 0.0483, 0.0464, 0.0446,
    0.0466, 0.0438 (R fisher.test exact: 0.046215). The p-value must now be identical
    across calls and be labelled as an approximation."""
    tab = _rxc_table()
    p = [categorical.fishers_exact(tab, row_col="r", col_col="c").p_value for _ in range(3)]
    assert p[0] == p[1] == p[2]
    assert abs(p[0] - 0.046215) < 0.003  # Monte Carlo error with 200k resamples
    r = categorical.fishers_exact(tab, row_col="r", col_col="c")
    assert r.extra.get("p_value_method") == "monte_carlo"
    assert r.extra.get("n_resamples") == 200_000
    assert any("Monte Carlo approximation" in w for w in r.warnings)


def test_fisher_2x2_path_unchanged():
    tab = pd.DataFrame([[7, 2], [1, 6]], index=["A", "B"], columns=["yes", "no"])
    r = categorical.fishers_exact(tab, row_col="arm", col_col="response")
    from scipy import stats
    orr, p = stats.fisher_exact(np.array([[7, 2], [1, 6]]))
    assert r.p_value == p and r.estimate == orr
    assert not any("Monte Carlo" in w for w in r.warnings)


def _spec(df, id_col, cols):
    from make_my_figure_core.matrix_workflow.matrix_spec import MatrixSpec
    return MatrixSpec(feature_id_column=id_col, value_columns=list(cols), value_type="raw_numeric", confirmed_by_user=True)


def test_quantile_normalization_ties_get_equal_values_and_match_bolstad():
    """Before the fix, tied values were mapped through numpy's unstable argsort, so identical
    inputs (e.g. zeros) received different normalized values (W matrix: 2,847 of 4,800 cells
    differed from the ordinal reference, max 56.2). limma::normalizeQuantiles(ties=TRUE) is the
    reference: average ranks, reference interpolated at the average rank."""
    from make_my_figure_core.matrix_workflow import normalization as N
    df = pd.DataFrame({"id": list("abcdef"), "s1": [0, 0, 5, 2, 0, 9.0], "s2": [1, 1, 1, 4, 7, 3.0], "s3": [0, 3, 3, 3, 8, 8.0]})
    out, params, _ = N.quantile_normalize(df, _spec(df, "id", ["s1", "s2", "s3"]))
    m = out[["s1", "s2", "s3"]].to_numpy()
    assert params["ties"] == "average"
    # tied inputs -> identical outputs within a column
    assert m[0, 0] == m[1, 0] == m[4, 0]
    assert m[1, 2] == m[2, 2] == m[3, 2] and m[4, 2] == m[5, 2]
    # limma reference computed by hand: ref = row means of sorted columns; interpolate at (rank-1)/(n-1)
    ref = np.sort(df[["s1", "s2", "s3"]].to_numpy(), axis=0).mean(axis=1)
    grid = np.arange(6) / 5
    from scipy.stats import rankdata
    for j, c in enumerate(["s1", "s2", "s3"]):
        r = rankdata(df[c].to_numpy(), method="average")
        np.testing.assert_allclose(m[:, j], np.interp((r - 1) / 5, grid, ref), rtol=0, atol=1e-12)


def test_voom_matches_limma_definition():
    """Before the fix, `voom` returned edgeR-style log-CPM with a library-size-scaled prior
    (max 0.75 log2 units away from limma::voom()$E on the W benchmark). limma's definition is
    E = log2((count + 0.5) / (lib.size * norm.factor + 1) * 1e6)."""
    from make_my_figure_core.matrix_workflow import normalization as N
    rng = np.random.default_rng(3)
    counts = rng.negative_binomial(4, 0.05, size=(60, 4)).astype(float) * np.array([0.5, 1.0, 1.5, 2.5])
    df = pd.DataFrame(counts, columns=["a", "b", "c", "d"]); df.insert(0, "g", [f"g{i}" for i in range(60)])
    spec = _spec(df, "g", ["a", "b", "c", "d"])
    out, params, _ = N.voom(df, spec)
    nf = N.tmm_norm_factors(counts)
    expected = np.log2((counts + 0.5) / (counts.sum(axis=0) * nf + 1.0) * 1e6)
    np.testing.assert_allclose(out[["a", "b", "c", "d"]].to_numpy(), expected, rtol=0, atol=1e-12)
    assert params["prior_scaling"].startswith("unscaled")


def _render_metric(plot_type, df, key):
    import json
    from pathlib import Path
    import matplotlib
    matplotlib.use("Agg")
    from make_my_figure_core.plots.registry import render
    base = json.loads((Path(__file__).resolve().parents[1] / "examples" / "by_plot_type" / "roc" / "plotspec.json").read_text())
    spec = {"plot_type": plot_type, "journal_style": "publication", "mapping": {"label": "true_label", "score": "score_model_a"},
            "input_table": base["input_table"], "output": base["output"]}
    res = render(spec, df)
    val = res.metadata[key]["score_model_a"]
    import matplotlib.pyplot as plt
    plt.close(res.figure)
    return val


def test_roc_auc_and_ap_do_not_depend_on_row_order_with_tied_scores():
    """Before the fix, tied scores were split by numpy's unstable argsort: five shuffles of one
    200-row table gave AUC 0.7337, 0.713, 0.7067, 0.7117, 0.7265 (tie-corrected Mann-Whitney AUC
    and pROC: 0.725442) and AP 0.6574 ... 0.6313."""
    from scipy.stats import mannwhitneyu
    rng = np.random.default_rng(7); n = 200
    label = rng.binomial(1, 0.4, n); score = np.round(rng.normal(0, 1, n) + 0.8 * label, 0)
    df = pd.DataFrame({"true_label": label, "score_model_a": score})
    aucs = {_render_metric("roc_curve", df.sample(frac=1, random_state=s).reset_index(drop=True), "auc") for s in range(4)}
    aps = {_render_metric("precision_recall_curve", df.sample(frac=1, random_state=s).reset_index(drop=True), "auprc") for s in range(4)}
    assert len(aucs) == 1 and len(aps) == 1
    u = mannwhitneyu(score[label == 1], score[label == 0]).statistic
    assert abs(aucs.pop() - u / ((label == 1).sum() * (label == 0).sum())) < 5e-5  # metadata rounds to 4 dp


def test_feature_summary_mann_whitney_effect_sign_matches_rank_biserial():
    """Before the fix the summary used 1 - 2U/(n_a n_b): for group A > group B it reported -0.92 while
    statistics.effect_sizes.rank_biserial_from_u gave +0.92 for the same U (and the fold change was
    positive). The sign must agree with the mean difference and with the statistics engine."""
    from make_my_figure_core.matrix_workflow.differential_summary import feature_differential_summary
    from make_my_figure_core.matrix_workflow.metadata_spec import metadata_from_assignment
    from make_my_figure_core.statistics import effect_sizes as es
    from scipy import stats
    df = pd.DataFrame({"f": ["x"], "a1": [5.0], "a2": [6.0], "a3": [7.0], "a4": [8.0], "a5": [9.0],
                       "b1": [1.0], "b2": [2.0], "b3": [3.0], "b4": [4.0], "b5": [5.5]})
    cols = [c for c in df.columns if c != "f"]
    spec = _spec(df, "f", cols); spec.value_type = "log_normalized"
    meta = metadata_from_assignment({c: ("A" if c.startswith("a") else "B") for c in cols})
    summ = feature_differential_summary(df, spec, meta, group_a="A", group_b="B", test="mann_whitney", correction="benjamini_hochberg")
    row = summ.table.iloc[0]
    u = stats.mannwhitneyu(df[["a1", "a2", "a3", "a4", "a5"]].to_numpy()[0], df[["b1", "b2", "b3", "b4", "b5"]].to_numpy()[0]).statistic
    assert row["effect_size"] == es.rank_biserial_from_u(u, 5, 5)[1] > 0
    assert row["mean_difference"] > 0


def test_rank_tests_treat_last_bit_near_ties_as_ties():
    """An all-zero gene's log-CPM values differ only in the last bit between libraries. Before the
    fix the Mann-Whitney screen on the W benchmark returned U = 12, p = 0.28 for such a gene
    (R: U = 18, p = 1) and 21/400 genes had U shifted by 0.5-1 from spurious tie-breaking."""
    from make_my_figure_core.differential import differential_screen
    from make_my_figure_core.matrix_workflow.preprocessing import apply_step
    rng = np.random.default_rng(11)
    counts = rng.negative_binomial(3, 0.02, size=(50, 8)).astype(float) * np.array([0.6, 0.8, 1.0, 1.3, 0.7, 1.1, 1.6, 0.9])
    counts[0, :] = 0.0                                             # all-zero gene
    df = pd.DataFrame(counts, columns=[f"s{i}" for i in range(8)]); df.insert(0, "g", [f"g{i}" for i in range(50)])
    lc, _, _ = apply_step(df, _spec(df, "g", list(df.columns[1:])), "cpm", params={"log": True, "prior_count": 0.5})
    vals = lc.iloc[0, 1:].to_numpy(float)
    assert vals.max() - vals.min() < 1e-9                         # equal in exact arithmetic
    labels = {c: ("A" if i < 4 else "B") for i, c in enumerate(df.columns[1:])}
    res = differential_screen(lc, feature_col="g", group_labels=labels, test="mann_whitney", log_input=True, reference_group="A")
    row = res.table.set_index("g").loc["g0"]
    assert np.isnan(row["pvalue"]) or row["pvalue"] == 1.0          # constant gene: no evidence, never p = 0.28
