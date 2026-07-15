"""In-app differential screen (normalized matrix, per-feature two-group test)."""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from make_my_figure_core.differential import differential_screen
from make_my_figure_core.recommendations import recommend_for_table


def _matrix():
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"gene": [f"g{i}" for i in range(30)]})
    for s in ["C1", "C2", "C3"]:
        df[s] = rng.normal(5, 1, 30)
    for s in ["T1", "T2", "T3"]:
        df[s] = rng.normal(6, 1, 30)   # shifted up
    return df


_LABELS = {"C1": "Ctrl", "C2": "Ctrl", "C3": "Ctrl",
           "T1": "Treat", "T2": "Treat", "T3": "Treat"}


def test_welch_pvalue_and_log2fc_match_scipy():
    df = _matrix()
    r = differential_screen(df, feature_col="gene", group_labels=_LABELS,
                            test="welch_t", log_input=True, reference_group="Ctrl")
    row = r.table.iloc[0]
    a = df.loc[0, ["C1", "C2", "C3"]].to_numpy(float)
    b = df.loc[0, ["T1", "T2", "T3"]].to_numpy(float)
    exp = stats.ttest_ind(b, a, equal_var=False)
    assert row["pvalue"] == pytest.approx(exp.pvalue, rel=1e-9)
    assert row["log2FoldChange"] == pytest.approx(b.mean() - a.mean(), rel=1e-9)
    assert r.reference_group == "Ctrl" and r.test_group == "Treat"


def test_padj_is_bh_and_bounded():
    r = differential_screen(_matrix(), feature_col="gene", group_labels=_LABELS)
    padj = r.table["padj"].to_numpy()
    p = r.table["pvalue"].to_numpy()
    assert np.all((padj[np.isfinite(padj)] >= 0) & (padj[np.isfinite(padj)] <= 1))
    assert np.all(padj[np.isfinite(padj)] >= p[np.isfinite(padj)] - 1e-9)  # adj >= raw


def test_requires_exactly_two_groups():
    bad = dict(_LABELS); bad["T3"] = "Third"
    with pytest.raises(ValueError):
        differential_screen(_matrix(), feature_col="gene", group_labels=bad)


def test_students_t_available():
    r = differential_screen(_matrix(), feature_col="gene", group_labels=_LABELS,
                            test="students_t")
    assert r.method == "students_t" and "Student" in r.method_sentence()


def test_raw_count_matrix_warns():
    df = pd.DataFrame({"gene": [f"g{i}" for i in range(10)]})
    for s in ["C1", "C2", "T1", "T2"]:
        df[s] = [0, 5, 10, 50000, 2, 900000, 3, 7, 100, 250000][:10]
    r = differential_screen(df, feature_col="gene",
                            group_labels={"C1": "C", "C2": "C", "T1": "T", "T2": "T"})
    assert any("raw counts" in w for w in r.warnings)


def test_results_table_is_recommended_as_precomputed_differential():
    r = differential_screen(_matrix(), feature_col="gene", group_labels=_LABELS)
    rs = recommend_for_table(r.table, "screen__diff.csv")
    assert rs.schema == "precomputed_differential"
    assert any(x.plot_type == "volcano_plot" and x.kind == "direct"
               for x in rs.recommendations)
