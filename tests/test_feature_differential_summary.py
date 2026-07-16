"""Feature-level differential summary: correctness, scale-aware fold change,
traceability, and confirmation gating."""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

import make_my_figure_core.matrix_workflow as mw
from make_my_figure_core.matrix_workflow.examples import CTRL, SAMPLES, TREAT, build_example_matrix


@pytest.fixture
def matrix():
    return build_example_matrix()


def _spec(value_type="log_normalized"):
    return mw.MatrixSpec(feature_id_column="feature_id", feature_display_column="feature_name",
                         annotation_columns=["bioType", "annotationLevel"],
                         value_columns=list(SAMPLES), value_type=value_type,
                         confirmed_by_user=True)


@pytest.fixture
def groups():
    return mw.metadata_from_assignment({**{c: "Ctrl" for c in CTRL},
                                        **{t: "Treatment" for t in TREAT}})


def test_gate_requires_confirmation(matrix, groups):
    spec = _spec()
    spec.confirmed_by_user = False
    with pytest.raises(ValueError):
        mw.feature_differential_summary(matrix, spec, groups, group_a="Treatment", group_b="Ctrl")


def test_pvalue_matches_scipy_for_a_feature(matrix, groups):
    spec = _spec()
    ds = mw.feature_differential_summary(matrix, spec, groups, group_a="Treatment",
                                         group_b="Ctrl", test="welch_t")
    frame = spec.feature_frame(matrix)
    a = frame.loc["FEAT00000", TREAT].to_numpy(float)
    b = frame.loc["FEAT00000", CTRL].to_numpy(float)
    _, p = stats.ttest_ind(a, b, equal_var=False)
    row = ds.table[ds.table["feature_id"] == "FEAT00000"].iloc[0]
    assert row["p_value"] == pytest.approx(p, rel=1e-6)
    assert 0 <= row["adjusted_p_value"] <= 1
    assert "Welch" in ds.method_sentence()


def test_bh_fdr_matches_statsmodels(matrix, groups):
    from statsmodels.stats.multitest import multipletests
    spec = _spec()
    ds = mw.feature_differential_summary(matrix, spec, groups, group_a="Treatment",
                                         group_b="Ctrl", test="welch_t")
    p = ds.table["p_value"].to_numpy()
    finite = np.isfinite(p)
    exp = multipletests(p[finite], method="fdr_bh")[1]
    got = ds.table["adjusted_p_value"].to_numpy()[finite]
    assert np.allclose(got, exp, atol=1e-9)


def test_logscale_uses_mean_difference_as_log2fc(matrix, groups):
    ds = mw.feature_differential_summary(matrix, _spec("log_normalized"), groups,
                                         group_a="Treatment", group_b="Ctrl")
    assert (ds.table["effect_type"] == "log2_fold_change").all()
    row = ds.table.iloc[0]
    assert row["log2_fold_change"] == pytest.approx(row["mean_a"] - row["mean_b"], abs=1e-9)


def test_linear_scale_uses_ratio_log2fc():
    # positive linear data -> log2 ratio of means
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"feature_id": [f"F{i}" for i in range(20)],
                       "feature_name": [f"F{i}" for i in range(20)],
                       "bioType": ["x"] * 20, "annotationLevel": [1] * 20})
    for s in SAMPLES:
        df[s] = rng.uniform(10, 100, 20)
    spec = _spec("normalized")
    groups = mw.metadata_from_assignment({**{c: "Ctrl" for c in CTRL}, **{t: "Treatment" for t in TREAT}})
    ds = mw.feature_differential_summary(df, spec, groups, group_a="Treatment", group_b="Ctrl")
    row = ds.table.iloc[0]
    exp = np.log2((row["mean_a"] + 1.0) / (row["mean_b"] + 1.0))
    assert row["log2_fold_change"] == pytest.approx(exp, abs=1e-9)


def test_unknown_scale_defers_fold_change(matrix, groups):
    ds = mw.feature_differential_summary(matrix, _spec("unknown_user_confirmed"), groups,
                                         group_a="Treatment", group_b="Ctrl")
    assert (ds.table["effect_type"] == "mean_difference").all()
    assert ds.table["log2_fold_change"].isna().all()
    assert any("unconfirmed" in w.lower() for w in ds.warnings)


def test_output_has_required_columns_and_annotations(matrix, groups):
    ds = mw.feature_differential_summary(matrix, _spec(), groups, group_a="Treatment", group_b="Ctrl")
    for c in ("feature_id", "feature_label", "bioType", "annotationLevel", "n_a", "n_b",
              "mean_a", "mean_b", "log2_fold_change", "p_value", "adjusted_p_value",
              "correction_method", "test_name", "effect_size", "ci_low", "ci_high"):
        assert c in ds.table.columns, c


def test_multi_group_anova(matrix):
    spec = _spec()
    g = mw.metadata_from_assignment({**{c: "A" for c in CTRL[:2]},
                                     **{c: "B" for c in CTRL[2:]},
                                     **{t: "C" for t in TREAT}})
    ds = mw.feature_differential_summary(matrix, spec, g, group_a="A", test="anova")
    assert ds.table["p_value"].notna().any()
    assert "ANOVA" in ds.method_sentence()
