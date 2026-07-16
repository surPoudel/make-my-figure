"""Differential summary from a PROCESSED matrix: derived matrix drives downstream
plots, and the method sentence + provenance trace back to the preprocessing chain."""

import numpy as np
import pandas as pd
import pytest

import make_my_figure_core.matrix_workflow as mw
from make_my_figure_core.plots.registry import figure_to_bytes, make_spec, render


def _raw():
    rng = np.random.default_rng(3)
    samples = [f"S{i:02d}" for i in range(8)]
    v = rng.lognormal(3, 1.2, size=(120, 8)); v[:, :4] *= 3   # group + total imbalance
    v[:20, 4:] *= 4                                            # some real signal in Trt
    d = pd.DataFrame({"feature_id": [f"F{i:04d}" for i in range(120)], "bioType": ["x"] * 120})
    for j, s in enumerate(samples):
        d[s] = np.round(v[:, j])
    spec = mw.MatrixSpec(feature_id_column="feature_id", annotation_columns=["bioType"],
                         value_columns=samples, value_type="raw_numeric",
                         source_file="raw.tsv", confirmed_by_user=True)
    meta = mw.metadata_from_assignment({s: ("Ctrl" if i < 4 else "Trt") for i, s in enumerate(samples)})
    return d, spec, meta, samples


def test_processed_matrix_feeds_pca_and_heatmap():
    df, spec, meta, samples = _raw()
    steps = [{"method": "total_sum", "params": {"scale_factor": 1e6}},
             {"method": "log2", "params": {"pseudocount": 1.0}}]
    final, dspec, ps = mw.run_preprocessing(df, spec, steps)
    assert dspec.value_type == "log_normalized"
    for pt, mp in (("pca_scatter_from_matrix", {"matrix_row_id": "feature_id", "value_columns": samples}),
                   ("heatmap_clustered_matrix", {"row_id": "feature_id", "value_columns": samples,
                                                 "scale": "row_zscore"})):
        res = render(make_spec(pt, "proc", "publication", mapping=mp), final)
        assert res.figure is not None


def test_differential_summary_method_sentence_includes_preprocessing():
    df, spec, meta, samples = _raw()
    steps = [{"method": "median_scale", "params": {}},
             {"method": "log2", "params": {"pseudocount": 1.0}}]
    final, dspec, ps = mw.run_preprocessing(df, spec, steps, output_matrix_id="proc1")
    ds = mw.feature_differential_summary(
        final, dspec, meta, group_a="Trt", group_b="Ctrl", test="welch_t",
        preprocessing_note=ps.method_sentence(), source_matrix_id="proc1",
        preprocessing_spec_id=ps.output_matrix_id)
    sent = ds.method_sentence()
    assert "median-scaled" in sent and "log2" in sent and "Welch" in sent
    assert ds.source_matrix_id == "proc1"
    assert ds.preprocessing_spec_id == "proc1"


def test_volcano_from_processed_differential_traces_and_renders():
    df, spec, meta, samples = _raw()
    final, dspec, ps = mw.run_preprocessing(
        df, spec, [{"method": "log2", "params": {"pseudocount": 1.0}}], output_matrix_id="log2mat")
    ds = mw.feature_differential_summary(final, dspec, meta, group_a="Trt", group_b="Ctrl",
                                         test="welch_t", preprocessing_note=ps.method_sentence(),
                                         source_matrix_id="log2mat")
    ps_spec = make_spec("volcano_plot", "diff", "publication",
                        mapping={"x": "log2_fold_change", "p": "adjusted_p_value",
                                 "label": "feature_label", "use_fdr": True})
    res = render(ps_spec, ds.table)
    assert len(figure_to_bytes(res.figure, "svg")) > 0
    # every plotted effect/p value comes from the stored table (traceable)
    assert ds.table["adjusted_p_value"].notna().any()
    assert ds.source_matrix_id == "log2mat"
