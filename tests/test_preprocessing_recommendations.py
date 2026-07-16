"""Preprocessing recommender: suggests appropriate workflows, never applies silently."""

import numpy as np
import pandas as pd

import make_my_figure_core.matrix_workflow as mw


def _qc(kind):
    rng = np.random.default_rng(1)
    samples = [f"S{i}" for i in range(6)]
    if kind == "skewed_totals":
        v = rng.lognormal(3, 1.5, size=(120, 6)); v[:, :2] *= 6
    elif kind == "log_like":
        v = rng.normal(4, 1.5, size=(120, 6))
    elif kind == "many_zeros":
        v = rng.lognormal(2, 1.2, size=(120, 6)); v[rng.random((120, 6)) < 0.5] = 0
    d = pd.DataFrame({"feature_id": [f"F{i}" for i in range(120)]})
    for j, s in enumerate(samples):
        d[s] = v[:, j]
    spec = mw.MatrixSpec(feature_id_column="feature_id", value_columns=samples,
                         value_type="raw_numeric", confirmed_by_user=True)
    return mw.diagnose_matrix(d, spec)


def test_skewed_with_total_imbalance_recommends_scale_then_log():
    recs = mw.recommend_preprocessing(_qc("skewed_totals"))
    top = recs[0]
    methods = [s["method"] for s in top.steps]
    assert methods[0] in ("total_sum", "median_scale")
    assert "log2" in methods
    assert top.reason and top.assumptions


def test_log_like_recommends_no_relog():
    recs = mw.recommend_preprocessing(_qc("log_like"))
    # first recommendation should avoid logging again
    assert all("log" not in s["method"] for s in recs[0].steps)
    assert "log" in recs[0].reason.lower()


def test_many_zeros_recommends_filtering():
    recs = mw.recommend_preprocessing(_qc("many_zeros"))
    assert any(any(s["method"] == "filter" for s in r.steps) for r in recs)


def test_recommendations_serialize_and_always_offer_internal_standard():
    recs = mw.recommend_preprocessing(_qc("skewed_totals"))
    names = [r.name for r in recs]
    assert any("nternal-standard" in n for n in names)
    assert all("name" in r.to_dict() and "steps" in r.to_dict() for r in recs)


def test_normalization_catalog_has_suitability_text():
    cat = mw.normalization_catalog()
    assert cat and all(c.reason and c.suitable_for for c in cat)
    ts = next(c for c in cat if c.method == "total_sum")
    assert ts.requires_positive_values is True
