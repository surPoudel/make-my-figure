"""Correctness of matrix-workflow transformations (reproducible, non-mutating)."""

import numpy as np
import pandas as pd
import pytest

import make_my_figure_core.matrix_workflow as mw
from make_my_figure_core.matrix_workflow import transformations as T
from make_my_figure_core.matrix_workflow.examples import (
    CTRL,
    SAMPLES,
    TREAT,
    build_example_matrix,
)


@pytest.fixture
def spec():
    return mw.MatrixSpec(feature_id_column="feature_id", feature_display_column="feature_name",
                         annotation_columns=["bioType", "annotationLevel"],
                         value_columns=list(SAMPLES), value_type="log_normalized",
                         confirmed_by_user=True)


@pytest.fixture
def matrix():
    return build_example_matrix()


@pytest.fixture
def groups():
    return mw.metadata_from_assignment({**{c: "Ctrl" for c in CTRL},
                                        **{t: "Treatment" for t in TREAT}})


def test_wide_to_long_shape_and_columns(matrix, spec, groups):
    long, ts = T.wide_to_long(matrix, spec, groups)
    assert long.shape[0] == len(matrix) * len(SAMPLES)
    assert {"feature_id", "feature_label", "sample_id", "value", "group"}.issubset(long.columns)
    assert set(long["group"].dropna().unique()) == {"Ctrl", "Treatment"}
    assert ts.transformation_type == "wide_to_long" and ts.reversible


def test_wide_to_long_does_not_mutate_input(matrix, spec):
    before = matrix.copy()
    T.wide_to_long(matrix, spec)
    pd.testing.assert_frame_equal(matrix, before)


def test_row_zscore_is_correct(matrix, spec):
    z, _ = T.row_zscore(matrix, spec)
    vals = z[SAMPLES].to_numpy()
    assert np.allclose(np.nanmean(vals, axis=1), 0, atol=1e-9)
    assert np.allclose(np.nanstd(vals, axis=1), 1, atol=1e-6)


def test_top_variable_features_selects_most_variable(spec):
    df = pd.DataFrame({"feature_id": ["a", "b", "c"],
                       "feature_name": ["a", "b", "c"],
                       "bioType": ["x"] * 3, "annotationLevel": [1, 2, 3]})
    for i, s in enumerate(SAMPLES):
        df[s] = [0.0, 100.0 * (i % 2), 1.0]   # b has highest variance
    sub, ts = T.top_variable_features(df, spec, top_n=1, method="variance")
    assert list(sub["feature_id"]) == ["b"]
    assert ts.parameters["top_n"] == 1


def test_sample_correlation_matrix(matrix, spec):
    corr, ts = T.sample_correlation(matrix, spec, method="pearson")
    assert corr.shape == (len(SAMPLES), len(SAMPLES) + 1)  # +1 sample_id col
    assert ts.parameters["method"] == "pearson"


def test_pca_returns_scores_and_variance(matrix, spec):
    scores, ts = T.compute_pca(matrix, spec, n_components=2)
    assert list(scores.columns)[:1] == ["sample_id"]
    assert scores.shape[0] == len(SAMPLES)
    ve = ts.parameters["variance_explained"]
    assert len(ve) == 2 and all(0 <= v <= 1 for v in ve)
    assert len(ts.parameters["loadings"]) == 2


def test_hierarchical_clustering_k_assignment(matrix, spec):
    out, ts = T.hierarchical_clustering(matrix, spec, k=3)
    assert "cluster" in out.columns
    assert out["cluster"].nunique() == 3
    assert len(ts.parameters["row_order"]) == len(matrix)
    assert len(ts.parameters["column_order"]) == len(SAMPLES)
    assert ts.parameters["cluster_assignment_column"] == "cluster"


def test_group_means(matrix, spec, groups):
    gm, ts = T.group_means(matrix, spec, groups, stat="mean", error="sd")
    assert {"group", "value", "error"}.issubset(gm.columns)
    assert set(gm["group"].unique()) == {"Ctrl", "Treatment"}
