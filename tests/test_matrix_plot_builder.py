"""build_plot_inputs turns each recommendation into inputs that actually render."""

import matplotlib
import pytest

matplotlib.use("Agg")

import make_my_figure_core.matrix_workflow as mw
from make_my_figure_core.matrix_workflow.examples import CTRL, SAMPLES, TREAT, build_example_matrix
from make_my_figure_core.matrix_workflow.plot_builder import build_plot_inputs
from make_my_figure_core.plots.registry import figure_to_bytes, make_spec, render


@pytest.fixture
def df():
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


@pytest.fixture
def diff(df, spec, groups):
    return mw.feature_differential_summary(df, spec, groups, group_a="Treatment",
                                           group_b="Ctrl", test="welch_t").table


def _render_ok(pi):
    ps = make_spec(pi.plot_type, "mw.tsv", "publication", mapping=pi.mapping)
    res = render(ps, pi.dataframe, aux=pi.aux or None)
    for fmt in ("png", "svg", "pdf"):
        assert len(figure_to_bytes(res.figure, fmt)) > 0
    return res


def _rec(recs, key):
    return next(r for r in recs if r.key == key)


def test_all_ready_matrix_recs_build_and_render(df, spec, groups, diff):
    recs = mw.recommend_plots(spec, groups, has_differential_summary=True, n_features=len(df))
    for key in ("heatmap", "heatmap_zscore", "clustering", "dendrogram",
                "sample_correlation_heatmap", "pca", "top_variable_heatmap", "pca_by_group"):
        pi = build_plot_inputs(_rec(recs, key), df, spec, metadata=groups)
        _render_ok(pi)


def test_group_plots_build_and_render(df, spec, groups):
    recs = mw.recommend_plots(spec, groups, n_features=len(df))
    for key in ("box_by_group", "dot_by_group", "bar_by_group"):
        pi = build_plot_inputs(_rec(recs, key), df, spec, metadata=groups,
                               selected_features=["FEAT00000", "FEAT00001"])
        assert pi.dataframe["group"].nunique() == 2
        _render_ok(pi)


def test_group_plot_without_selection_defaults_and_warns(df, spec, groups):
    recs = mw.recommend_plots(spec, groups, n_features=len(df))
    pi = build_plot_inputs(_rec(recs, "box_by_group"), df, spec, metadata=groups)
    assert any("most variable" in w for w in pi.warnings)
    _render_ok(pi)


def test_differential_plots_build_and_render(df, spec, groups, diff):
    recs = mw.recommend_plots(spec, groups, has_differential_summary=True, n_features=len(df))
    for key in ("volcano", "ma", "ranked_effect"):
        pi = build_plot_inputs(_rec(recs, key), df, spec, metadata=groups, differential_table=diff)
        _render_ok(pi)


def test_volcano_values_trace_to_table(df, spec, groups, diff):
    recs = mw.recommend_plots(spec, groups, has_differential_summary=True, n_features=len(df))
    pi = build_plot_inputs(_rec(recs, "volcano"), df, spec, differential_table=diff)
    # the volcano reads columns straight from the differential table (no recompute)
    assert pi.mapping["x"] == "log2_fold_change"
    assert pi.mapping["p"] == "adjusted_p_value"
    assert pi.dataframe is diff


def test_unconfirmed_matrix_raises(df, spec):
    spec.confirmed_by_user = False
    recs = mw.recommend_plots(spec, None, n_features=len(df))
    with pytest.raises(ValueError):
        build_plot_inputs(recs[0], df, spec)


def test_differential_plot_without_table_raises(df, spec, groups):
    recs = mw.recommend_plots(spec, groups, has_differential_summary=True, n_features=len(df))
    with pytest.raises(ValueError):
        build_plot_inputs(_rec(recs, "volcano"), df, spec, differential_table=None)
