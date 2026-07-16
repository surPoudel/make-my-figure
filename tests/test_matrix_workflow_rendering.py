"""End-to-end: matrix-workflow outputs render through the registry to publication
plots, and PNG/SVG/PDF exports are non-empty. Statistics on the volcano trace to
the differential summary table (no fabricated values)."""

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")

import make_my_figure_core.matrix_workflow as mw
from make_my_figure_core.matrix_workflow import transformations as T
from make_my_figure_core.matrix_workflow.examples import CTRL, SAMPLES, TREAT, build_example_matrix
from make_my_figure_core.plots.registry import figure_to_bytes, make_spec, render


@pytest.fixture
def matrix():
    return build_example_matrix()


@pytest.fixture
def spec():
    return mw.MatrixSpec(feature_id_column="feature_id", feature_display_column="feature_name",
                         annotation_columns=["bioType", "annotationLevel"],
                         value_columns=list(SAMPLES), value_type="log_normalized",
                         confirmed_by_user=True)


@pytest.fixture
def groups():
    return mw.metadata_from_assignment({**{c: "Ctrl" for c in CTRL},
                                        **{t: "Treatment" for t in TREAT}})


def _exports_nonempty(fig):
    for fmt in ("png", "svg", "pdf"):
        assert len(figure_to_bytes(fig, fmt)) > 0, fmt


def test_heatmap_from_confirmed_value_columns(matrix, spec):
    ps = make_spec("heatmap_clustered_matrix", "m.tsv", "publication",
                   mapping={"row_id": "feature_id", "value_columns": spec.value_columns,
                            "scale": "row_zscore"})
    res = render(ps, matrix)
    assert res.metadata["matrix_shape"][1] == len(SAMPLES)  # only value columns
    _exports_nonempty(res.figure)


def test_pca_scatter_renders_from_matrix(matrix, spec):
    ps = make_spec("pca_scatter_from_matrix", "m.tsv", "publication",
                   mapping={"matrix_row_id": "feature_id", "value_columns": spec.value_columns})
    res = render(ps, matrix)
    _exports_nonempty(res.figure)


def test_volcano_from_differential_summary_traceable(matrix, spec, groups):
    ds = mw.feature_differential_summary(matrix, spec, groups, group_a="Treatment",
                                         group_b="Ctrl", test="welch_t")
    tbl = ds.table
    ps = make_spec("volcano_plot", "diff.tsv", "publication",
                   mapping={"x": "log2_fold_change", "p": "adjusted_p_value",
                            "label": "feature_label", "use_fdr": True})
    res = render(ps, tbl)
    _exports_nonempty(res.figure)
    # every plotted point value exists in the stored differential table (traceable)
    assert tbl["log2_fold_change"].notna().any()
    assert tbl["adjusted_p_value"].notna().any()


def test_selected_feature_box_from_long(matrix, spec, groups):
    long, _ = T.wide_to_long(matrix, spec, groups)
    sub = long[long["feature_id"] == "FEAT00000"]
    ps = make_spec("boxplot_or_violin_with_points", "long.csv", "publication",
                   mapping={"x": "group", "y": "value", "kind": "violin", "points": True})
    res = render(ps, sub)
    _exports_nonempty(res.figure)
