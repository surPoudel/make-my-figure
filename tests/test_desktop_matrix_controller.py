"""Desktop controller matrix-workflow methods (GUI-free — no Qt event loop).

The Qt wizard is a thin layer over these, so exercising them here covers the
desktop workflow logic without needing PySide6 (which can't load in the sandbox).
"""

import matplotlib
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


def test_build_matrix_plots_render(ctrl, data, spec, meta):
    recs = ctrl.matrix_recommendations(data, spec, meta, has_differential=False)
    for key in ("heatmap", "pca", "box_by_group"):
        rec = next(r for r in recs if r.key == key)
        _spec, result, pi = ctrl.matrix_build_plot(
            data, rec, spec, metadata=meta,
            selected_features=["FEAT00000"] if key == "box_by_group" else None)
        assert result.figure is not None
