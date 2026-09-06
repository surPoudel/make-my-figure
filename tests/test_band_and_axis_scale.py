"""Median/IQR/range bands for the line plot and layout-level axis scales."""
import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.plots.base import summarize_band, summarize_error
from make_my_figure_core.plots.registry import make_spec, render


def test_summarize_band_order_statistics():
    vals = np.array([1.0, 2.0, 3.0, 4.0, 100.0])
    c, lo, hi = summarize_band(vals, "iqr")
    assert c == 3.0 and lo == 2.0 and hi == 4.0
    c, lo, hi = summarize_band(vals, "range")
    assert (c, lo, hi) == (3.0, 1.0, 100.0)
    # symmetric methods delegate to summarize_error and centre on the mean
    m, e = summarize_error(vals, "sd")
    c, lo, hi = summarize_band(vals, "sd")
    assert c == m and lo == pytest.approx(m - e) and hi == pytest.approx(m + e)
    # NaNs dropped; single value gives a zero-width band
    assert summarize_band(np.array([np.nan, 5.0]), "iqr") == (5.0, 5.0, 5.0)


def _timing_frame():
    rows = []
    for op in ("load", "render"):
        for n in (1000, 10000, 100000):
            for rep in range(5):
                rows.append({"rows": n, "operation": op, "seconds": (n / 1e5) * (1 + 0.1 * rep) + 0.01})
    return pd.DataFrame(rows)


def test_lineplot_iqr_band_and_log_axes():
    df = _timing_frame()
    spec = make_spec("lineplot_timecourse_with_error_band", "t.csv", "publication",
                     mapping={"x": "rows", "y": "seconds", "color": "operation", "error": "iqr"})
    spec["layout"] = {"x_scale": "log", "y_scale": "log"}
    res = render(spec, df)
    ax = res.figure.axes[0]
    assert ax.get_xscale() == "log" and ax.get_yscale() == "log"
    assert res.metadata["error_method"] == "iqr"
    # the centre line is the median of the five replicates at each size
    line = [l for l in ax.get_lines() if l.get_label() == "load"][0]
    med = df[(df.operation == "load") & (df.rows == 1000)].seconds.median()
    assert line.get_ydata()[0] == pytest.approx(med)


def test_log_scale_skipped_for_nonpositive_data():
    df = pd.DataFrame({"x": [0, 1, 2, 3], "y": [1.0, 2.0, 3.0, 4.0]})
    spec = make_spec("lineplot_timecourse_with_error_band", "t.csv", "publication",
                     mapping={"x": "x", "y": "y", "error": "none"})
    spec["layout"] = {"x_scale": "log"}
    res = render(spec, df)
    assert res.figure.axes[0].get_xscale() == "linear"


def test_oncoprint_input_order_and_sample_labels():
    rows = [{"s": s, "g": g, "f": "match"} for s in ("second", "first") for g in ("zeta", "alpha", "mid")]
    df = pd.DataFrame(rows)
    spec = make_spec("oncoprint_mutation_heatmap", "t.csv", "publication",
                     mapping={"sample": "s", "row": "g", "fill": "f", "order": "input"})
    ax = render(spec, df).figure.axes[0]
    assert [t.get_text() for t in ax.get_xticklabels()] == ["second", "first"]
    assert [t.get_text() for t in ax.get_yticklabels()][::-1][:3] == ["zeta", "alpha", "mid"] or \
        [t.get_text() for t in ax.get_yticklabels()][:3] == ["zeta", "alpha", "mid"]


def test_lineplot_style_by_varies_linestyle_and_marker():
    df = _timing_frame()
    df["platform"] = ["A", "B"] * (len(df) // 2)
    spec = make_spec("lineplot_timecourse_with_error_band", "t.csv", "publication",
                     mapping={"x": "rows", "y": "seconds", "color": "operation", "style_by": "platform", "error": "none"})
    ax = render(spec, df).figure.axes[0]
    lines = {l.get_label(): l for l in ax.get_lines() if not l.get_label().startswith("_")}
    assert set(lines) == {"load, A", "load, B", "render, A", "render, B"}
    assert lines["load, A"].get_color() == lines["load, B"].get_color()
    assert lines["load, A"].get_linestyle() != lines["load, B"].get_linestyle()
    assert lines["load, A"].get_marker() != lines["load, B"].get_marker()
