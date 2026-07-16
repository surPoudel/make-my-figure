"""Plot recommendation engine: readiness depends on confirmed mapping/groups."""

import make_my_figure_core.matrix_workflow as mw
from make_my_figure_core.matrix_workflow.examples import CTRL, SAMPLES, TREAT
from make_my_figure_core.matrix_workflow.recommendations import (
    NEEDS_GROUP,
    READY,
    recommend_from_differential_table,
    recommend_plots,
)


def _spec(confirmed=True):
    return mw.MatrixSpec(feature_id_column="feature_id", value_columns=list(SAMPLES),
                         value_type="log_normalized", confirmed_by_user=confirmed)


def _groups():
    return mw.metadata_from_assignment({**{c: "Ctrl" for c in CTRL},
                                        **{t: "Treatment" for t in TREAT}})


def test_matrix_only_recommends_matrix_plots_ready():
    recs = recommend_plots(_spec(), None, has_differential_summary=False, n_features=300)
    types = {r.plot_type for r in recs if r.readiness_status == READY}
    assert {"heatmap_clustered_matrix", "hierarchical_clustering",
            "pca_scatter_from_matrix"}.issubset(types)


def test_group_plots_need_groups_until_confirmed():
    recs = recommend_plots(_spec(), None, n_features=300)
    box = [r for r in recs if r.plot_type == "boxplot_or_violin_with_points"][0]
    assert box.readiness_status == NEEDS_GROUP
    recs2 = recommend_plots(_spec(), _groups(), n_features=300)
    box2 = [r for r in recs2 if r.plot_type == "boxplot_or_violin_with_points"][0]
    assert box2.readiness_status == READY
    assert "wide_to_long" in box2.required_transformations


def test_volcano_needs_differential_then_becomes_ready():
    recs = recommend_plots(_spec(), _groups(), has_differential_summary=False, n_features=300)
    volc = [r for r in recs if r.plot_type == "volcano_plot"][0]
    assert volc.readiness_status != READY
    assert "feature_differential_summary" in volc.required_transformations
    recs2 = recommend_plots(_spec(), _groups(), has_differential_summary=True, n_features=300)
    volc2 = [r for r in recs2 if r.plot_type == "volcano_plot"][0]
    assert volc2.readiness_status == READY


def test_large_matrix_flags_heatmap_visual_warning():
    recs = recommend_plots(_spec(), None, n_features=5000)
    heat = [r for r in recs if r.plot_type == "heatmap_clustered_matrix"][0]
    assert any("top-variable" in w.lower() or "top variable" in w.lower()
               for w in heat.visual_warnings)


def test_recommendations_serialize():
    recs = recommend_plots(_spec(), _groups(), n_features=300)
    d = [r.to_dict() for r in recs]
    assert all("readiness_status" in r and "plot_type" in r for r in d)


def test_precomputed_table_recommendations():
    recs = recommend_from_differential_table(has_average_abundance=True, has_matrix=True)
    types = {r.plot_type for r in recs}
    assert "volcano_plot" in types and "ma_plot" in types
    assert "heatmap_clustered_matrix" in types  # matrix present -> top-feature heatmap
