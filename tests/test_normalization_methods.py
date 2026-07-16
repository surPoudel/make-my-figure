"""Normalization methods: hand-calculated correctness."""

import numpy as np
import pandas as pd

import make_my_figure_core.matrix_workflow as mw
from make_my_figure_core.matrix_workflow import normalization as N


def _df(vals, samples=("S1", "S2", "S3")):
    arr = np.asarray(vals, dtype=float)
    d = pd.DataFrame({"feature_id": [f"F{i}" for i in range(arr.shape[0])]})
    for j, s in enumerate(samples):
        d[s] = arr[:, j]
    spec = mw.MatrixSpec(feature_id_column="feature_id", value_columns=list(samples),
                         value_type="raw_numeric", confirmed_by_user=True)
    return d, spec


def test_total_sum_normalization():
    df, spec = _df([[1.0, 2.0, 4.0], [3.0, 6.0, 4.0]])   # col totals 4, 8, 8
    out, params, _w = N.total_sum(df, spec, scale_factor=100.0)
    # S1 col scaled by 100/4: [25, 75]; each column sums to 100
    assert np.allclose(out[["S1", "S2", "S3"]].to_numpy().sum(axis=0), 100.0)
    assert out["S1"].tolist() == [25.0, 75.0]


def test_median_scale_matches_medians():
    df, spec = _df([[2.0, 4.0, 8.0], [4.0, 8.0, 16.0], [6.0, 12.0, 24.0]])
    out, _p, _w = N.median_scale(df, spec)
    meds = np.median(out[["S1", "S2", "S3"]].to_numpy(), axis=0)
    assert np.allclose(meds, meds[0])                    # medians equalized


def test_upper_quartile_non_negative_only_warns():
    df, spec = _df([[-1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    _out, _p, warns = N.upper_quartile(df, spec)
    assert any("non-negative" in w.lower() for w in warns)


def test_quantile_normalization_matches_distributions():
    df, spec = _df([[5.0, 4.0], [2.0, 6.0], [3.0, 1.0]], samples=("S1", "S2"))
    out, _p, warns = N.quantile_normalize(df, spec)
    s1 = np.sort(out["S1"].to_numpy()); s2 = np.sort(out["S2"].to_numpy())
    assert np.allclose(s1, s2)                           # identical distributions
    assert any("same distribution" in w.lower() for w in warns)


def test_column_zscore():
    df, spec = _df([[1.0, 10.0], [2.0, 20.0], [3.0, 30.0]], samples=("S1", "S2"))
    out, _p, _w = N.zscore(df, spec, axis="column")
    m = out[["S1", "S2"]].to_numpy()
    assert np.allclose(m.mean(axis=0), 0, atol=1e-9)
    assert np.allclose(m.std(axis=0), 1, atol=1e-9)


def test_robust_scale_centers_on_median():
    df, spec = _df([[10.0, 1.0], [20.0, 2.0], [30.0, 3.0]], samples=("S1", "S2"))
    out, _p, warns = N.robust_scale(df, spec)
    assert np.allclose(np.median(out[["S1", "S2"]].to_numpy(), axis=0), 0, atol=1e-9)
    assert any("unit" in w.lower() or "iqr" in w.lower() for w in warns)


def test_center_sample_median():
    df, spec = _df([[1.0, 100.0], [3.0, 300.0], [5.0, 500.0]], samples=("S1", "S2"))
    out, params, _w = N.center(df, spec, mode="sample_median")
    assert np.allclose(np.median(out[["S1", "S2"]].to_numpy(), axis=0), 0, atol=1e-9)
    assert params["mode"] == "sample_median"


def test_no_r_or_rpy2_imported_by_normalization():
    import sys
    import make_my_figure_core.matrix_workflow.normalization  # noqa: F401
    assert "rpy2" not in sys.modules
