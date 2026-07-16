"""QC plots render, and the before/after report writes its artifacts + is reproducible."""

import os

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")

import make_my_figure_core.matrix_workflow as mw
from make_my_figure_core.matrix_workflow.qc_plots import qc_plot_catalog, qc_plot_inputs
from make_my_figure_core.plots.registry import figure_to_bytes, make_spec, render


def _raw(n=150, seed=0):
    rng = np.random.default_rng(seed)
    samples = [f"S{i:02d}" for i in range(8)]
    v = rng.lognormal(3, 1.4, size=(n, 8)); v[:, :4] *= 3
    d = pd.DataFrame({"feature_id": [f"F{i:04d}" for i in range(n)], "bioType": ["x"] * n})
    for j, s in enumerate(samples):
        d[s] = np.round(v[:, j])
    spec = mw.MatrixSpec(feature_id_column="feature_id", annotation_columns=["bioType"],
                         value_columns=samples, value_type="raw_numeric",
                         source_file="raw", confirmed_by_user=True)
    meta = mw.metadata_from_assignment({s: ("A" if i < 4 else "B") for i, s in enumerate(samples)})
    return d, spec, meta


def _render(pi):
    spec = make_spec(pi.plot_type, "qc", "publication", mapping=pi.mapping)
    for k, v in (pi.spec_extra or {}).items():
        spec[k] = v
    return render(spec, pi.dataframe, aux=pi.aux or None)


@pytest.mark.parametrize("kind", [c["key"] for c in qc_plot_catalog()])
def test_every_qc_plot_renders_and_exports(kind):
    df, spec, meta = _raw()
    pi = qc_plot_inputs(kind, df, spec, metadata=meta, title=kind)
    res = _render(pi)
    for fmt in ("png", "svg", "pdf"):
        assert len(figure_to_bytes(res.figure, fmt)) > 0, (kind, fmt)


def test_before_after_report_writes_artifacts(tmp_path):
    df, spec, meta = _raw()
    steps = [{"method": "total_sum", "params": {"scale_factor": 1e6}},
             {"method": "log2", "params": {"pseudocount": 1.0}}]
    final, dspec, ps, records = mw.before_after_report(
        df, spec, steps, str(tmp_path), metadata=meta,
        qc_kinds=["value_density", "library_size", "pca"])
    assert os.path.exists(tmp_path / "preprocessing_report.md")
    assert os.path.exists(tmp_path / "qc_summary.csv")
    assert os.path.exists(tmp_path / "before_after_contact_sheet.png")
    # before/after images exist for each requested QC kind
    assert all(r["before"] and r["after"] for r in records)
    # the report is reproducible: derived matrix is log-scaled and method sentence records it
    assert dspec.value_type == "log_normalized"
    txt = open(tmp_path / "preprocessing_report.md", encoding="utf-8").read()
    assert "total-sum" in txt and "log2" in txt


def test_report_does_not_mutate_original(tmp_path):
    df, spec, meta = _raw()
    before = df.copy()
    mw.before_after_report(df, spec, [{"method": "log2", "params": {"pseudocount": 1.0}}],
                           str(tmp_path), metadata=meta, qc_kinds=["library_size"])
    pd.testing.assert_frame_equal(df, before)
