"""Structure-changing transforms + transform/guidance recommendations."""

import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.transforms import apply_transform
from make_my_figure_core.recommendations import recommend_for_table


def _wide():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"gene": [f"g{i}" for i in range(15)]})
    for s in ["S1", "S2", "S3", "S4"]:
        df[s] = rng.normal(5, 2, 15)
    return df


def test_wide_to_long():
    out = apply_transform(_wide(), "wide_to_long",
                          {"value_cols": ["S1", "S2", "S3", "S4"]})
    assert list(out.columns) == ["column", "value"]
    assert len(out) == 60 and out["value"].dtype.kind == "f"


def test_correlation_matrix_square_with_feature_col():
    out = apply_transform(_wide(), "correlation_matrix",
                          {"columns": ["S1", "S2", "S3", "S4"]})
    assert out.columns[0] == "feature"
    assert list(out["feature"]) == ["S1", "S2", "S3", "S4"]
    assert out.shape == (4, 5)   # feature col + 4 corr columns


def test_value_counts():
    df = pd.DataFrame({"grp": ["a", "a", "b", "c", "c", "c"]})
    out = apply_transform(df, "value_counts", {"column": "grp"})
    assert list(out.columns) == ["grp", "count"]
    assert out.set_index("grp")["count"].to_dict() == {"a": 2, "b": 1, "c": 3}


def test_unknown_transform_raises():
    with pytest.raises(ValueError):
        apply_transform(_wide(), "nope", {})


def test_matrix_gets_transform_and_guidance_recs():
    rs = recommend_for_table(_wide(), "matrix.csv")
    kinds = {r.kind for r in rs.recommendations}
    assert "transform" in kinds and "guidance" in kinds
    tnames = {r.plot_type for r in rs.recommendations if r.kind == "transform"}
    assert {"ridge_or_density_plot", "heatmap_clustered_matrix"} <= tnames
    # guidance for volcano/MA explains stats are needed and is NOT one-click
    guide = [r for r in rs.recommendations if r.kind == "guidance"]
    assert guide and all(g.plot_spec_draft is None and g.instructions for g in guide)
    assert not any(g.is_renderable for g in guide)
