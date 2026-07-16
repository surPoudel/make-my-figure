"""Transforms: hand-calculated correctness + safeguards. Original matrix never mutated."""

import numpy as np
import pandas as pd
import pytest

import make_my_figure_core.matrix_workflow as mw
from make_my_figure_core.matrix_workflow import preprocessing as pp


def _df(vals, samples=("S1", "S2")):
    d = pd.DataFrame({"feature_id": [f"F{i}" for i in range(len(vals))], "bioType": ["x"] * len(vals)})
    arr = np.asarray(vals, dtype=float)
    for j, s in enumerate(samples):
        d[s] = arr[:, j]
    spec = mw.MatrixSpec(feature_id_column="feature_id", annotation_columns=["bioType"],
                         value_columns=list(samples), value_type="raw_numeric", confirmed_by_user=True)
    return d, spec


def test_log2_with_pseudocount_and_no_mutation():
    df, spec = _df([[0.0, 3.0], [1.0, 7.0]])
    before = df.copy()
    out, params, warns = pp.log2(df, spec, pseudocount=1.0)
    assert np.allclose(out[["S1", "S2"]].to_numpy(), np.log2(np.array([[0.0, 3.0], [1.0, 7.0]]) + 1))
    assert params["pseudocount"] == 1.0
    pd.testing.assert_frame_equal(df, before)          # input untouched


def test_log_warns_on_negative_values():
    df, spec = _df([[-1.0, 2.0], [3.0, 4.0]])
    out, _p, warns = pp.log2(df, spec, pseudocount=1.0)
    assert any("negative" in w.lower() for w in warns)


def test_arcsinh_transform():
    df, spec = _df([[0.0, 5.0], [10.0, 50.0]])
    out, params, _w = pp.arcsinh(df, spec, cofactor=5.0)
    assert np.allclose(out[["S1", "S2"]].to_numpy(), np.arcsinh(np.array([[0.0, 5.0], [10.0, 50.0]]) / 5.0))
    assert params["cofactor"] == 5.0


def test_sqrt_transform_clips_negatives_with_warning():
    df, spec = _df([[4.0, 9.0], [-1.0, 16.0]])
    out, _p, warns = pp.sqrt(df, spec)
    assert out["S2"].tolist() == [3.0, 4.0]
    assert any("non-negative" in w.lower() for w in warns)


def test_winsorize_caps_and_reports():
    vals = [[float(x), float(x)] for x in range(100)]
    df, spec = _df(vals)
    out, params, _w = pp.winsorize(df, spec, lower=5, upper=95)
    m = out[["S1", "S2"]].to_numpy()
    assert m.min() >= np.percentile(np.arange(100), 5) - 1e-9
    assert m.max() <= np.percentile(np.arange(100), 95) + 1e-9
    assert params["capped_values"] > 0


def test_impute_feature_median_reports_count():
    df, spec = _df([[np.nan, 4.0], [2.0, 6.0], [8.0, np.nan]])
    out, params, _w = pp.impute(df, spec, strategy="feature_median")
    assert params["imputed"] == 2
    assert not out[["S1", "S2"]].isna().any().any()


def test_filter_removes_constant_and_sparse():
    df, spec = _df([[0.0, 0.0], [5.0, 5.0], [1.0, 9.0]])  # row0 all-zero, row1 constant
    out, params, _w = pp.filter_features(df, spec, max_zero_frac=0.5, drop_constant=True)
    assert params["removed"] == 2
    assert list(out["feature_id"]) == ["F2"]


def test_row_and_column_zscore_via_apply_step():
    df, spec = _df([[1.0, 3.0], [2.0, 4.0], [3.0, 5.0]])
    out_r, dspec, step = mw.apply_step(df, spec, "row_zscore")
    assert np.allclose(out_r[["S1", "S2"]].mean(axis=1), 0, atol=1e-9)
    out_c, _dspec, _s = mw.apply_step(df, spec, "column_zscore")
    assert np.allclose(out_c[["S1", "S2"]].to_numpy().mean(axis=0), 0, atol=1e-9)


def test_log_sets_derived_value_type_log_normalized():
    df, spec = _df([[1.0, 3.0], [2.0, 7.0]])
    _out, dspec, _step = mw.apply_step(df, spec, "log2", params={"pseudocount": 1.0})
    assert dspec.value_type == "log_normalized"
