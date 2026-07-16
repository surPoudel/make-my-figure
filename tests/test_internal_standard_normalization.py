"""Internal-standard / control-feature / reference normalization."""

import numpy as np
import pandas as pd
import pytest

import make_my_figure_core.matrix_workflow as mw
from make_my_figure_core.matrix_workflow import normalization as N


def _df():
    # 2 internal-standard feature rows (constant 100 across samples) + 3 real features.
    d = pd.DataFrame({"feature_id": ["IS_A", "IS_B", "F1", "F2", "F3"]})
    d["S1"] = [100.0, 100.0, 10.0, 20.0, 30.0]
    d["S2"] = [200.0, 200.0, 40.0, 80.0, 120.0]      # 2x IS -> should normalize to same as S1
    d["IScol1"] = [1.0, 1.0, 2.0, 2.0, 2.0]           # per-feature IS measurement column
    spec = mw.MatrixSpec(feature_id_column="feature_id", value_columns=["S1", "S2"],
                         annotation_columns=["IScol1"], value_type="raw_numeric",
                         confirmed_by_user=True)
    return d, spec


def test_internal_standard_features_divides_by_is_signal():
    df, spec = _df()
    out, params, _w = N.internal_standard_features(df, spec, feature_ids=["IS_A", "IS_B"],
                                                   how="median", operation="divide")
    # S1 IS median=100 -> [10,20,30]/100; S2 IS median=200 -> [40,80,120]/200.
    real = out[out["feature_id"].isin(["F1", "F2", "F3"])]
    assert np.allclose(real["S1"].to_numpy(), [0.1, 0.2, 0.3])
    assert np.allclose(real["S2"].to_numpy(), [0.2, 0.4, 0.6])
    assert params["operation"] == "divide"
    assert "is_stability_cv" in params


def test_internal_standard_features_missing_ids_raises():
    df, spec = _df()
    with pytest.raises(ValueError):
        N.internal_standard_features(df, spec, feature_ids=["nope"])


def test_control_features_uses_same_mechanism():
    df, spec = _df()
    out, params, _w = N.control_features(df, spec, feature_ids=["IS_A", "IS_B"])
    assert params["role"] == "control_features"
    real = out[out["feature_id"].isin(["F1", "F2", "F3"])]
    assert np.allclose(real["S1"].to_numpy(), [0.1, 0.2, 0.3])
    assert np.allclose(real["S2"].to_numpy(), [0.2, 0.4, 0.6])


def test_internal_standard_columns_divides_per_feature():
    df, spec = _df()
    out, params, _w = N.internal_standard_columns(df, spec, is_columns=["IScol1"], operation="divide")
    # F1..F3 divided by IScol1=2 -> S1 F1 becomes 5.0
    row = out[out["feature_id"] == "F1"].iloc[0]
    assert row["S1"] == 5.0 and row["S2"] == 20.0
    assert params["is_columns"] == ["IScol1"]


def test_reference_sample_normalization():
    df, spec = _df()
    out, params, _w = N.reference_sample(df, spec, reference="S1", operation="divide")
    # S1 relative to itself is 1 everywhere
    assert np.allclose(out["S1"].to_numpy(), 1.0)
    assert "S1" in params["reference"]
