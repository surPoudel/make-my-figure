"""Desktop controller matrix-workflow methods (GUI-free — no Qt event loop).

The Qt wizard is a thin layer over these, so exercising them here covers the
desktop workflow logic without needing PySide6 (which can't load in the sandbox).
"""

import matplotlib
import pandas as pd
import pytest

matplotlib.use("Agg")

from apps.desktop_app.controller import DesktopController
import make_my_figure_core.matrix_workflow as mw
from make_my_figure_core.matrix_workflow.examples import CTRL, SAMPLES, TREAT, build_example_matrix


@pytest.fixture
def ctrl():
    return DesktopController()


@pytest.fixture
def data(ctrl):
    return ctrl.loaded_from_dataframe(build_example_matrix(), "matrix.tsv")


@pytest.fixture
def spec():
    return mw.MatrixSpec(feature_id_column="feature_id", feature_display_column="feature_name",
                         annotation_columns=["bioType", "annotationLevel"],
                         value_columns=list(SAMPLES), value_type="log_normalized",
                         source_file="matrix.tsv", confirmed_by_user=True)


@pytest.fixture
def meta(ctrl):
    return ctrl.matrix_metadata_from_assignment({**{c: "Ctrl" for c in CTRL},
                                                 **{t: "Treatment" for t in TREAT}})


def test_suggest_spec_excludes_annotation(ctrl, data):
    s = ctrl.matrix_suggest_spec(data)
    assert "annotationLevel" in s.annotation_columns
    assert "annotationLevel" not in s.value_columns
    assert s.confirmed_by_user is False


def test_validate_and_recommend(ctrl, data, spec, meta):
    rep = ctrl.matrix_validate(data, spec, meta)
    assert rep.ok, rep.errors
    recs = ctrl.matrix_recommendations(data, spec, meta, has_differential=False)
    ready = {r.key for r in recs if r.readiness_status == "ready"}
    assert {"heatmap", "pca", "box_by_group"}.issubset(ready)


def test_statistics_gate(ctrl, spec):
    one = ctrl.matrix_metadata_from_assignment({c: "Ctrl" for c in CTRL})
    assert not ctrl.matrix_can_run_statistics(spec, one).ok


def test_differential_summary_and_build_volcano(ctrl, data, spec, meta):
    ds = ctrl.matrix_differential_summary(data, spec, meta, group_a="Treatment",
                                          group_b="Ctrl", test="welch_t")
    assert "log2_fold_change" in ds.table.columns
    recs = ctrl.matrix_recommendations(data, spec, meta, has_differential=True)
    volc = next(r for r in recs if r.key == "volcano")
    spec_dict, result, pi = ctrl.matrix_build_plot(data, volc, spec, metadata=meta,
                                                   differential_table=ds.table)
    assert result.figure is not None
    assert pi.plot_type == "volcano_plot"


def test_style_overrides_apply_to_matrix_plot(ctrl, data, spec, meta):
    recs = ctrl.matrix_recommendations(data, spec, meta, has_differential=False)
    rec = next(r for r in recs if r.key == "heatmap_zscore")
    overrides = {"palette_name": "grayscale", "font_family": "DejaVu Sans",
                 "axis_font_pt": 15.0, "tick_label_pt": 13.0, "marker_size": 60.0}
    spec_dict, result, pi = ctrl.matrix_build_plot(
        data, rec, spec, metadata=meta, params={"top_n": 20}, style_overrides=overrides)
    # overrides are recorded in the spec (reproducible sidecar) ...
    assert spec_dict["style"]["palette_name"] == "grayscale"
    assert spec_dict["style"]["font_family"] == "DejaVu Sans"
    # ... and actually take effect: grayscale drives the heatmap colormap.
    from make_my_figure_core.styles.engine import load_profile
    resolved = load_profile("publication").with_overrides(spec_dict["style"])
    assert resolved.diverging_cmap == "gray"
    assert resolved.axis_font_pt == 15.0
    assert result.figure is not None


def test_preprocessing_controller_methods(ctrl, tmp_path):
    # raw-like skewed count matrix as a LoadedData
    import numpy as np
    rng = np.random.default_rng(0)
    cols = [f"S{i:02d}" for i in range(8)]
    v = rng.lognormal(3, 1.4, size=(200, 8)); v[:, :4] *= 3
    dfr = pd.DataFrame({"feature_id": [f"F{i:04d}" for i in range(200)], "bioType": ["x"] * 200})
    for j, c in enumerate(cols):
        dfr[c] = np.round(v[:, j])
    data = ctrl.loaded_from_dataframe(dfr, "raw.tsv")
    ms = mw.MatrixSpec(feature_id_column="feature_id", annotation_columns=["bioType"],
                       value_columns=cols, value_type="raw_numeric", source_file="raw.tsv",
                       confirmed_by_user=True)
    meta = ctrl.matrix_metadata_from_assignment({c: ("A" if i < 4 else "B") for i, c in enumerate(cols)})

    qc = ctrl.matrix_diagnose(data, ms)
    assert qc.skewness_summary["overall"] > 1.0
    recs = ctrl.matrix_preprocessing_recommendations(qc)
    assert recs and all(r.steps for r in recs)
    # a QC plot renders
    _spec, res = ctrl.matrix_qc_plot(data, ms, "library_size", metadata=meta)
    assert res.figure is not None
    # apply a chain -> derived LoadedData + processed spec
    steps = [{"method": "filter", "params": {"max_zero_frac": 0.9}},
             {"method": "total_sum", "params": {"scale_factor": 1e6}},
             {"method": "log2", "params": {"pseudocount": 1.0}}]
    derived, dspec, ps = ctrl.matrix_apply_preprocessing(data, ms, steps, metadata=meta)
    assert dspec.value_type == "log_normalized"
    assert derived.info.dataframe.shape[0] <= dfr.shape[0]
    assert "log2" in ps.method_sentence()
    # before/after report writes artifacts
    final, ds2, ps2, records = ctrl.matrix_before_after_report(
        data, ms, steps, str(tmp_path), metadata=meta, )
    import os
    assert os.path.exists(tmp_path / "preprocessing_report.md")
    # original data untouched
    assert data.info.dataframe.shape[0] == 200


def test_processed_matrix_downstream_and_traceable(ctrl, tmp_path):
    """A derived (preprocessed) matrix feeds heatmap/PCA/volcano, and the differential
    method sentence + stored result trace back to the exact preprocessing chain."""
    import numpy as np
    rng = np.random.default_rng(1)
    cols = [f"S{i:02d}" for i in range(8)]
    v = rng.lognormal(3, 1.4, size=(300, 8)); v[:, :4] *= 3
    dfr = pd.DataFrame({"feature_id": [f"F{i:04d}" for i in range(300)]})
    for j, c in enumerate(cols):
        dfr[c] = np.round(v[:, j])
    raw = ctrl.loaded_from_dataframe(dfr, "raw.tsv")
    ms = mw.MatrixSpec(feature_id_column="feature_id", value_columns=cols,
                       value_type="raw_numeric", source_file="raw.tsv", confirmed_by_user=True)
    meta = ctrl.matrix_metadata_from_assignment({c: ("A" if i < 4 else "B")
                                                 for i, c in enumerate(cols)})
    steps = [{"method": "total_sum", "params": {"scale_factor": 1e6}},
             {"method": "log2", "params": {"pseudocount": 1.0}}]
    derived, dspec, ps = ctrl.matrix_apply_preprocessing(raw, ms, steps, metadata=meta)

    # differential summary on the processed matrix is traceable to the preprocessing
    ds = ctrl.matrix_differential_summary(
        derived, dspec, meta, group_a="A", group_b="B", test="welch_t",
        preprocessing_note=ps.method_sentence(), source_matrix_id=ps.output_matrix_id,
        preprocessing_spec_id=ps.output_matrix_id)
    assert "log2" in ds.method_sentence().lower()
    assert ds.source_matrix_id == ps.output_matrix_id
    assert ds.preprocessing_spec_id == ps.output_matrix_id

    # derived matrix feeds heatmap + PCA
    recs = ctrl.matrix_recommendations(derived, dspec, meta, has_differential=True)
    for key in ("heatmap", "pca"):
        rec = next(r for r in recs if r.key == key)
        _s, result, _pi = ctrl.matrix_build_plot(derived, rec, dspec, metadata=meta)
        assert result.figure is not None
    # and a volcano built from the traceable differential table
    volc = next(r for r in recs if r.key == "volcano")
    _s, vres, vpi = ctrl.matrix_build_plot(derived, volc, dspec, metadata=meta,
                                           differential_table=ds.table)
    assert vres.figure is not None and vpi.plot_type == "volcano_plot"


def test_build_matrix_plots_render(ctrl, data, spec, meta):
    recs = ctrl.matrix_recommendations(data, spec, meta, has_differential=False)
    for key in ("heatmap", "pca", "box_by_group"):
        rec = next(r for r in recs if r.key == key)
        _spec, result, pi = ctrl.matrix_build_plot(
            data, rec, spec, metadata=meta,
            selected_features=["FEAT00000"] if key == "box_by_group" else None)
        assert result.figure is not None
