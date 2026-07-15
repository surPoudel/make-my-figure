"""Heatmap: log+z-score scale and the raw-count nudge."""

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.clustering import SCALES, scale_matrix
from make_my_figure_core.plots.registry import make_spec, render


def test_log_zscore_scale_available_and_centers_rows():
    assert "log_zscore" in SCALES
    X = np.array([[0.0, 10.0, 1_000_000.0], [2.0, 3.0, 4.0]])
    scaled, _ = scale_matrix(X, "log_zscore")
    # each row (feature) is centered after log + z-score
    assert np.allclose(np.nanmean(scaled, axis=1), 0.0, atol=1e-9)
    assert np.isfinite(scaled).all()


def _count_matrix():
    return pd.DataFrame({
        "gene": [f"g{i}" for i in range(6)],
        "S1": [0, 5, 10, 50000, 2, 900000], "S2": [1, 6, 12, 40000, 3, 800000],
        "S3": [0, 4, 9, 60000, 1, 700000],
    })


def test_raw_count_matrix_nudges_when_unscaled():
    spec = make_spec("heatmap_clustered_matrix", "m.csv", "publication")
    spec["mapping"] = {"row_id": "gene", "scale": "none",
                       "cluster_rows": False, "cluster_columns": False}
    res = render(spec, _count_matrix())
    assert any("washed out" in w or "raw counts" in w for w in res.warnings)


def test_log_zscore_renders_and_suppresses_nudge():
    spec = make_spec("heatmap_clustered_matrix", "m.csv", "publication")
    spec["mapping"] = {"row_id": "gene", "scale": "log_zscore",
                       "cluster_rows": False, "cluster_columns": False}
    res = render(spec, _count_matrix())
    assert res.figure is not None
    assert not any("washed out" in w for w in res.warnings)
