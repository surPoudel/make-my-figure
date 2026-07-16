"""Hotfix/polish coverage: QC layout+export, volcano p/FDR, count normalizations,
z-score axis option, GLM regression, scatter regression stats, group defaults.

All pure-Python (numpy/scipy/statsmodels), no GUI, no private data. Where a value
has an exact reference (scipy/statsmodels), we assert exact agreement.
"""

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")

import make_my_figure_core.matrix_workflow as mw
from make_my_figure_core.matrix_workflow import normalization as N
from make_my_figure_core.matrix_workflow.qc_plots import short_sample_labels
from make_my_figure_core.plots.registry import make_spec, render


def _matrix(n_feat=300, n_samp=8, seed=0, longnames=True):
    rng = np.random.default_rng(seed)
    cols = ([f"3345{23 + i:03d}_DHP{i + 1:03d}" for i in range(n_samp)] if longnames
            else [f"S{i}" for i in range(n_samp)])
    df = pd.DataFrame({"gid": [f"F{i:04d}" for i in range(n_feat)], "bioType": ["x"] * n_feat})
    for j, c in enumerate(cols):
        df[c] = np.round(rng.lognormal(3, 1.3, n_feat) * (1 + 0.1 * j))
    spec = mw.MatrixSpec(feature_id_column="gid", annotation_columns=["bioType"],
                         value_columns=cols, value_type="raw_numeric",
                         source_file="syn", confirmed_by_user=True)
    return df, spec, cols


# --- QC layout + export -----------------------------------------------------
def test_short_sample_labels_unique_and_short():
    cols = [f"3345{23 + i:03d}_DHP{i + 1:03d}" for i in range(12)]
    labels = short_sample_labels(cols)
    assert len(set(labels.values())) == len(cols)          # unique
    assert all(len(v) <= 8 for v in labels.values())       # short
    short = [f"S{i}" for i in range(4)]
    assert short_sample_labels(short) == {c: c for c in short}  # already short: unchanged


def test_before_after_report_writes_vector_and_contact_sheet(tmp_path):
    df, spec, cols = _matrix()
    meta = mw.metadata_from_assignment({c: ("A" if i < 4 else "B") for i, c in enumerate(cols)})
    steps = [{"method": "total_sum", "params": {"scale_factor": 1e6}},
             {"method": "log2", "params": {"pseudocount": 1.0}}]
    final, dspec, ps, records = mw.before_after_report(df, spec, steps, str(tmp_path), metadata=meta)
    for name in ("before_after_contact_sheet.png", "before_after_contact_sheet.pdf",
                 "preprocessing_report.md", "qc_summary.csv"):
        assert (tmp_path / name).exists() and (tmp_path / name).stat().st_size > 0
    # per-plot vector artifacts exist
    per = tmp_path / "per_plot"
    assert any(p.suffix == ".pdf" for p in per.iterdir())
    assert any(p.suffix == ".svg" for p in per.iterdir())
    # report records the short->full sample-name legend
    assert "short" in (tmp_path / "preprocessing_report.md").read_text()


def test_report_path_with_spaces(tmp_path):
    # OneDrive-style path with spaces must work (cross-platform safety).
    d = tmp_path / "My Reports" / "qc out"
    d.mkdir(parents=True)
    df, spec, cols = _matrix(n_feat=100, n_samp=4)
    _f, _s, _p, _r = mw.before_after_report(
        df, spec, [{"method": "log2", "params": {}}], str(d),
        qc_kinds=["value_density", "library_size"])
    assert (d / "before_after_contact_sheet.png").exists()


# --- volcano p-value / FDR selection ---------------------------------------
def _diff_table(n=200, with_fdr=True, with_p=True, seed=0):
    rng = np.random.default_rng(seed)
    d = pd.DataFrame({"feature_id": [f"F{i}" for i in range(n)],
                      "feature_label": [f"G{i}" for i in range(n)],
                      "log2_fold_change": rng.normal(0, 1.5, n)})
    if with_p:
        d["p_value"] = rng.uniform(0, 1, n)
    if with_fdr:
        d["adjusted_p_value"] = rng.uniform(0, 1, n)
    return d


def _volcano(params, tbl):
    from make_my_figure_core.matrix_workflow.plot_builder import build_plot_inputs
    from make_my_figure_core.matrix_workflow.recommendations import RecommendedPlot
    rec = RecommendedPlot("volcano_plot", "Volcano", "x", key="volcano")
    spec = mw.MatrixSpec(feature_id_column="feature_id", value_columns=["a"],
                         value_type="log_normalized", confirmed_by_user=True)
    return build_plot_inputs(rec, pd.DataFrame({"feature_id": tbl.feature_id}), spec,
                             differential_table=tbl, params=params)


def test_volcano_pvalue_axis():
    pi = _volcano({"significance": "pvalue"}, _diff_table())
    assert pi.mapping["p"] == "p_value" and pi.mapping["use_fdr"] is False
    assert pi.mapping["significance"] == "pvalue"


def test_volcano_fdr_axis():
    pi = _volcano({"significance": "fdr"}, _diff_table())
    assert pi.mapping["p"] == "adjusted_p_value" and pi.mapping["use_fdr"] is True


def test_volcano_fdr_missing_falls_back_to_p():
    pi = _volcano({"significance": "fdr"}, _diff_table(with_fdr=False))
    assert pi.mapping["p"] == "p_value" and pi.mapping["use_fdr"] is False
    assert any("FDR" in w for w in pi.warnings)


def test_volcano_p_missing_falls_back_to_fdr():
    pi = _volcano({"significance": "pvalue"}, _diff_table(with_p=False))
    assert pi.mapping["p"] == "adjusted_p_value" and pi.mapping["use_fdr"] is True
    assert any("p-value" in w for w in pi.warnings)


def test_volcano_choice_round_trips_in_spec():
    pi = _volcano({"significance": "fdr", "p_cutoff": 0.1}, _diff_table())
    spec = make_spec(pi.plot_type, "d", "publication", mapping=pi.mapping)
    assert spec["mapping"]["significance"] == "fdr"
    assert spec["mapping"]["use_fdr"] is True


# --- count-style normalizations --------------------------------------------
def test_cpm_sums_to_million():
    df, spec, cols = _matrix(n_feat=500, n_samp=6, longnames=False)
    out, _p, _w = N.cpm(df, spec)
    assert np.allclose(out[cols].sum(axis=0).to_numpy(), 1e6, rtol=1e-6)


def test_tmm_factors_geomean_one():
    df, spec, cols = _matrix(n_feat=500, n_samp=6, longnames=False)
    f = N.tmm_norm_factors(df[cols].to_numpy(float))
    assert np.isclose(np.exp(np.mean(np.log(f))), 1.0, atol=1e-9)
    assert np.all(f > 0)


def test_voom_is_log_scale_and_weights_positive():
    df, spec, cols = _matrix(n_feat=400, n_samp=6, longnames=False)
    out, params, _w = N.voom(df, spec)
    assert params["output_scale"] == "log2_cpm"
    w = N.voom_weights(df, spec)
    assert w.shape == (400, 6) and bool((w.to_numpy() > 0).all())
    _f, dspec, ps = mw.run_preprocessing(df, spec, [{"method": "voom", "params": {}}],
                                         output_matrix_id="p")
    assert dspec.value_type == "log_normalized"


def test_count_methods_registered():
    for m in ("cpm", "tmm", "voom", "zscore"):
        assert m in mw.available_methods()


# --- z-score / robust-scale axis option ------------------------------------
@pytest.mark.parametrize("axis,ax", [("row", 1), ("column", 0)])
def test_zscore_axis_option(axis, ax):
    df, spec, cols = _matrix(n_feat=100, n_samp=6, longnames=False)
    out, _d, ps = mw.run_preprocessing(df, spec, [{"method": "zscore", "params": {"axis": axis}}],
                                       output_matrix_id="p")
    m = out[cols].to_numpy()
    assert np.allclose(np.nanmean(m, axis=ax), 0, atol=1e-9)
    assert ps.preprocessing_steps[0].parameters.get("axis") == axis


def test_zscore_default_is_rowwise():
    df, spec, cols = _matrix(n_feat=100, n_samp=6, longnames=False)
    out, _d, _p = mw.run_preprocessing(df, spec, [{"method": "zscore", "params": {}}],
                                       output_matrix_id="p")
    assert np.allclose(np.nanmean(out[cols].to_numpy(), axis=1), 0, atol=1e-9)


def test_robust_scale_axis():
    df, spec, cols = _matrix(n_feat=100, n_samp=6, longnames=False)
    out, _d, _p = mw.run_preprocessing(df, spec, [{"method": "robust_scale", "params": {"axis": "row"}}],
                                       output_matrix_id="p")
    assert np.allclose(np.nanmedian(out[cols].to_numpy(), axis=1), 0, atol=1e-9)


# --- GLM regression ---------------------------------------------------------
def test_glm_gaussian_exact_vs_statsmodels():
    sm = pytest.importorskip("statsmodels.api")
    rng = np.random.default_rng(3)
    n = 250
    x1, x2 = rng.normal(0, 1, n), rng.normal(0, 1, n)
    y = 1 + 2 * x1 - 0.5 * x2 + rng.normal(0, 1, n)
    df = pd.DataFrame({"y": y, "x1": x1, "x2": x2})
    rep = mw.glm_regression(df, response="y", predictors=["x1", "x2"], family="gaussian")
    X = sm.add_constant(df[["x1", "x2"]])
    ref = sm.GLM(df["y"].to_numpy(), X.to_numpy(), family=sm.families.Gaussian()).fit()
    by = {r.extra["term"]: r for r in rep.results}
    for j, t in enumerate(["const", "x1", "x2"]):
        assert abs(by[t].estimate - ref.params[j]) < 1e-9
        assert abs(by[t].p_value - ref.pvalues[j]) < 1e-12


def test_glm_binomial_and_via_runner():
    pytest.importorskip("statsmodels.api")
    from make_my_figure_core.statistics import run_statistics
    rng = np.random.default_rng(4)
    n = 300
    x = rng.normal(0, 1, n)
    y = (1 / (1 + np.exp(-(0.5 + 1.5 * x))) > rng.uniform(size=n)).astype(int)
    df = pd.DataFrame({"y": y, "x": x})
    rep = mw.glm_regression(df, response="y", predictors=["x"], family="binomial")
    assert {"const", "x"} <= {r.extra["term"] for r in rep.results}
    # reachable through the standard stats entrypoint
    rep2 = run_statistics(df, {"enabled": True, "test": "glm", "response": "y",
                               "predictors": ["x"], "family": "binomial"})
    assert len(rep2.results) == 2 and all(r.p_value is not None for r in rep2.results)


def test_glm_bad_config_warns_not_crashes():
    pytest.importorskip("statsmodels.api")
    from make_my_figure_core.statistics import run_statistics
    df = pd.DataFrame({"y": [1.0, 2, 3], "x": [1.0, 2, 3]})
    rep = run_statistics(df, {"enabled": True, "test": "glm", "response": "nope",
                              "predictors": ["x"]})
    assert rep.warnings and not rep.results


# --- scatter regression annotation -----------------------------------------
def test_scatter_regression_stats_exact_and_toggleable():
    from scipy import stats as sps
    rng = np.random.default_rng(1)
    x = np.linspace(0, 10, 60)
    y = 2.5 * x + 4 + rng.normal(0, 3, 60)
    df = pd.DataFrame({"x": x, "y": y})
    lr = sps.linregress(x, y)
    spec = make_spec("scatterplot_with_regression", "d", "publication",
                     mapping={"x": "x", "y": "y", "fit_line": True})
    res = render(spec, df)
    reg = res.metadata["regression"]["all"]
    assert abs(reg["slope"] - lr.slope) < 1e-9
    assert abs(reg["p_value"] - lr.pvalue) < 1e-12
    assert abs(reg["r_squared"] - lr.rvalue ** 2) < 1e-12
    # hiding stats must not crash and must not drop them from metadata
    spec2 = make_spec("scatterplot_with_regression", "d", "publication",
                      mapping={"x": "x", "y": "y", "show_fit_stats": False})
    res2 = render(spec2, df)
    assert "all" in res2.metadata["regression"]


# --- group defaults ---------------------------------------------------------
def test_default_group_pair_distinct():
    meta = mw.metadata_from_assignment({"s1": "A", "s2": "A", "s3": "B", "s4": "B"})
    a, b = meta.default_group_pair()
    assert a == "A" and b == "B" and a != b
    one = mw.metadata_from_assignment({"s1": "A", "s2": "A"})
    assert one.default_group_pair() == ("A", None)


def test_same_group_comparison_blocked():
    df, spec, cols = _matrix(n_feat=100, n_samp=6, longnames=False)
    meta = mw.metadata_from_assignment({c: ("A" if i < 3 else "B") for i, c in enumerate(cols)})
    with pytest.raises(ValueError, match="same"):
        mw.feature_differential_summary(df, spec, meta, group_a="A", group_b="A", test="welch_t")
