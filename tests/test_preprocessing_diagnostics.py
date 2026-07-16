"""QC diagnostics on raw-like / skewed matrices (suggestions only, no classification)."""

import numpy as np
import pandas as pd

import make_my_figure_core.matrix_workflow as mw


def _matrix(kind="skewed", n=150, seed=0):
    rng = np.random.default_rng(seed)
    samples = [f"S{i:02d}" for i in range(6)]
    if kind == "skewed":
        vals = rng.lognormal(3, 1.5, size=(n, 6))
        vals[:, :2] *= 6.0                       # sample-total imbalance
        vals = np.round(vals)
    elif kind == "log_like":
        vals = rng.normal(5, 2, size=(n, 6))     # centred, some negatives
    df = pd.DataFrame({"feature_id": [f"F{i}" for i in range(n)],
                       "annotationLevel": rng.integers(1, 4, n)})
    for j, s in enumerate(samples):
        df[s] = vals[:, j]
    spec = mw.MatrixSpec(feature_id_column="feature_id", annotation_columns=["annotationLevel"],
                         value_columns=samples, value_type="raw_numeric", confirmed_by_user=True)
    return df, spec


def test_detects_skew_and_sample_total_differences():
    df, spec = _matrix("skewed")
    qc = mw.diagnose_matrix(df, spec)
    assert qc.skewness_summary["overall"] > 1.5
    t = qc.sample_total_summary
    assert t["max"] / max(t["min"], 1e-9) > 3
    assert qc.suspected_data_type in ("count_like", "intensity_like_skewed")
    assert any("skew" in w.lower() for w in qc.warnings)
    assert any("total" in w.lower() for w in qc.warnings)


def test_annotation_column_not_in_value_stats():
    df, spec = _matrix("skewed")
    qc = mw.diagnose_matrix(df, spec)
    # annotationLevel (1/2/3) is not a value column, so n_samples == 6 value columns only
    assert qc.n_samples == 6
    assert "annotationLevel" not in spec.value_columns


def test_negative_values_flagged_and_not_count_like():
    df, spec = _matrix("log_like")
    qc = mw.diagnose_matrix(df, spec)
    assert qc.negative_value_fraction > 0
    assert qc.suspected_data_type in ("log_like_or_normalized", "possibly_log_or_normalized")
    assert any("negative" in w.lower() for w in qc.warnings)


def test_qc_summary_round_trips():
    import json
    df, spec = _matrix("skewed")
    qc = mw.diagnose_matrix(df, spec)
    back = mw.QCMetricSummary.from_dict(json.loads(json.dumps(qc.to_dict())))
    assert back.suspected_data_type == qc.suspected_data_type
    assert back.n_features == qc.n_features
