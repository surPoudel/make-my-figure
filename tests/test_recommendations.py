"""Tests for the v0.6 figure recommendation engine.

Covers schema detection and plot recommendations for each supported data
schema, verifies no recommendation implies RNA-seq differential-expression
analysis, and smoke-renders the clearly-renderable drafts.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.plots.registry import available_plot_types, render
from make_my_figure_core.recommendations import (
    detect_schema,
    profile_table,
    recommend_after_analysis,
    recommend_for_table,
)

_EXISTING = set(available_plot_types())
_FORBIDDEN = ("edger", "limma", "voom", "run de", "deseq", "rna-seq analysis",
              "differential expression analysis")


def _no_rnaseq(spec):
    for r in spec.recommendations:
        blob = (r.why + " " + " ".join(r.warnings)).lower()
        assert not any(term in blob for term in _FORBIDDEN), \
            f"recommendation leaked RNA-seq DE language: {blob}"


def _de_table():
    return pd.DataFrame({
        "gene": [f"G{i}" for i in range(12)],
        "logFC": np.linspace(-3, 3, 12),
        "AveExpr": np.linspace(2, 10, 12),
        "P.Value": np.linspace(1e-6, 0.5, 12),
        "adj.P.Val": np.linspace(1e-5, 0.6, 12),
    })


def _matrix(count_like=False, n=20, cols=6):
    rng = np.random.RandomState(0)
    df = pd.DataFrame({"gene": [f"g{i}" for i in range(n)]})
    for s in range(cols):
        df[f"sample_{s}"] = (rng.poisson(50, n) if count_like else rng.normal(6, 2, n))
    return df


# --- schema detection --------------------------------------------------------

@pytest.mark.parametrize("builder,expected", [
    (lambda: _de_table(), "precomputed_differential"),
    (lambda: _matrix(count_like=True), "numeric_matrix"),
    (lambda: _matrix(count_like=False), "expression_like_matrix"),
    (lambda: pd.DataFrame({"time_months": [5, 10, 15, 20, 25, 30],
                           "event": [1, 0, 1, 1, 0, 1],
                           "group": list("AAABBB")}), "survival"),
    (lambda: pd.DataFrame({"true_label": [0, 1, 0, 1, 1, 0],
                           "score": [.1, .9, .2, .8, .7, .3]}), "classification"),
    (lambda: pd.DataFrame({"source": list("ABC"), "target": list("BCA")}),
     "network_edge_list"),
    (lambda: pd.DataFrame({"chr": ["1", "1", "2", "2"], "pos": [10, 20, 30, 40],
                           "p": [.01, 1e-5, .2, 1e-3]}), "gwas"),
    (lambda: pd.DataFrame({"dose": [1, 10, 100, 1000], "response": [5, 40, 80, 95]}),
     "dose_response"),
    (lambda: pd.DataFrame({"subject": ["s1", "s1", "s2", "s2", "s3", "s3"],
                           "condition": ["pre", "post"] * 3,
                           "value": [1, 2, 3, 4, 5, 6]}), "paired"),
    (lambda: pd.DataFrame({"term": ["GO1", "GO2", "GO3"], "gene_count": [10, 20, 30],
                           "gene_ratio": [.1, .2, .3], "pvalue": [.01, .02, .03],
                           "fdr": [.05, .06, .07]}), "enrichment"),
    (lambda: pd.DataFrame({"patient_id": ["p1", "p1", "p2"], "gene": ["TP53", "KRAS", "TP53"],
                           "alteration": ["missense", "frameshift", "missense"]}),
     "mutation_matrix"),
])
def test_schema_detection(builder, expected):
    df = builder()
    prof = profile_table(df)
    assert detect_schema(prof, df) == expected


# --- recommendations per schema ---------------------------------------------

def test_differential_recommends_volcano_and_renders():
    df = _de_table()
    spec = recommend_for_table(df, "de.csv")
    assert spec.schema == "precomputed_differential"
    assert spec.top.plot_type == "volcano_plot"
    _no_rnaseq(spec)
    res = render(spec.top.plot_spec_draft, df)
    assert res.figure is not None
    plt.close(res.figure)


def test_matrix_recommends_heatmap_and_pca():
    df = _matrix()
    spec = recommend_for_table(df, "matrix.tsv")
    types = [r.plot_type for r in spec.recommendations]
    assert "heatmap_clustered_matrix" in types
    assert "pca_scatter_from_matrix" in types
    # PCA needs a metadata table -> flagged missing, not directly renderable
    pca = next(r for r in spec.recommendations if r.plot_type == "pca_scatter_from_matrix")
    assert pca.missing_mappings
    # DE note present; no RNA-seq analysis implied
    assert any("does not run differential-expression" in n for n in spec.notes)
    _no_rnaseq(spec)
    # heatmap draft renders
    hm = next(r for r in spec.recommendations if r.plot_type == "heatmap_clustered_matrix")
    res = render(hm.plot_spec_draft, df)
    assert res.figure is not None
    plt.close(res.figure)


def test_large_matrix_requires_confirmation():
    df = _matrix(n=3000, cols=20)
    spec = recommend_for_table(df, "big.tsv")
    hm = next(r for r in spec.recommendations if r.plot_type == "heatmap_clustered_matrix")
    assert hm.requires_confirmation and hm.estimated_cost == "high"


def test_survival_recommends_km_and_renders():
    df = pd.DataFrame({"time_months": [5, 10, 15, 20, 25, 30, 8, 22],
                       "event": [1, 0, 1, 1, 0, 1, 1, 0],
                       "group": list("AAAABBBB")})
    spec = recommend_for_table(df, "surv.csv")
    assert spec.top.plot_type == "kaplan_meier_survival_curve"
    res = render(spec.top.plot_spec_draft, df)
    assert res.figure is not None
    plt.close(res.figure)


def test_classification_recommends_roc_and_renders():
    rng = np.random.RandomState(1)
    df = pd.DataFrame({"true_label": rng.randint(0, 2, 40),
                       "score": rng.rand(40)})
    spec = recommend_for_table(df, "clf.csv")
    assert spec.top.plot_type == "roc_curve"
    res = render(spec.top.plot_spec_draft, df)
    assert res.figure is not None
    plt.close(res.figure)


def test_generic_long_recommends_box_and_renders():
    df = pd.DataFrame({"group": ["A"] * 6 + ["B"] * 6,
                       "value": list(np.r_[np.random.RandomState(2).normal(0, 1, 6),
                                           np.random.RandomState(3).normal(2, 1, 6)])})
    spec = recommend_for_table(df, "long.csv")
    assert spec.top.plot_type == "boxplot_or_violin_with_points"
    assert spec.top.suggested_statistics is not None
    res = render(spec.top.plot_spec_draft, df)
    assert res.figure is not None
    plt.close(res.figure)


def test_enrichment_recommends_dotplot():
    df = pd.DataFrame({"term": [f"GO:{i}" for i in range(8)],
                       "gene_count": np.arange(8) + 2,
                       "gene_ratio": np.linspace(.05, .4, 8),
                       "pvalue": np.linspace(1e-4, .04, 8),
                       "fdr": np.linspace(1e-3, .05, 8)})
    spec = recommend_for_table(df, "enrich.csv")
    assert spec.top.plot_type == "enrichment_dotplot"
    _no_rnaseq(spec)


def test_mutation_recommends_oncoprint():
    df = pd.DataFrame({"patient_id": ["p1", "p1", "p2", "p3", "p2"],
                       "gene": ["TP53", "KRAS", "TP53", "EGFR", "KRAS"],
                       "alteration": ["missense", "frameshift", "missense",
                                      "amplification", "frameshift"]})
    spec = recommend_for_table(df, "mut.csv")
    assert spec.top.plot_type == "oncoprint_mutation_heatmap"


def test_network_and_gwas_recommend_real_types():
    # v0.6 on the 37-plot base: these dedicated renderers now exist.
    net = recommend_for_table(pd.DataFrame({"source": list("ABC"), "target": list("BCA")}))
    assert net.schema == "network_edge_list"
    assert net.top.plot_type == "network_graph"
    gwas = recommend_for_table(pd.DataFrame({"chr": ["1", "2", "3"], "pos": [1, 2, 3],
                                             "p": [.01, .02, 1e-4]}))
    assert gwas.schema == "gwas"
    types = {r.plot_type for r in gwas.recommendations}
    assert "manhattan_plot" in types and "qq_plot" in types


def test_dose_response_recommends_curve():
    spec = recommend_for_table(pd.DataFrame({"dose": [1, 10, 100, 1000, 10000],
                                             "response": [3, 20, 55, 85, 96]}))
    assert spec.schema == "dose_response"
    assert spec.top.plot_type == "dose_response_curve"


def test_every_recommendation_uses_publication_style_and_existing_or_flagged():
    for builder in (_de_table, lambda: _matrix(), lambda: pd.DataFrame(
            {"group": list("AABB"), "value": [1, 2, 3, 4]})):
        spec = recommend_for_table(builder())
        _no_rnaseq(spec)
        for r in spec.recommendations:
            assert r.suggested_style == "publication"
            if r.plot_spec_draft is not None:
                assert r.plot_type in _EXISTING
                assert r.plot_spec_draft["journal_style"] == "publication"


def test_recommend_after_analysis_post_stats():
    df = pd.DataFrame({"group": ["A"] * 5 + ["B"] * 5,
                       "value": list(range(10))})
    spec = recommend_after_analysis(df, stats_report=object(), table_name="x")
    assert spec.recommendations
    assert spec.top.plot_type == "boxplot_or_violin_with_points"


def test_recommend_after_analysis_differential():
    df = _de_table()
    spec = recommend_after_analysis(df, differential=True, has_matrix=True)
    types = [r.plot_type for r in spec.recommendations]
    assert "volcano_plot" in types
    assert any("top-feature heatmap" in n for n in spec.notes)


def test_unnamed_categorical_group_is_recommended():
    """A low-cardinality categorical (not named 'group') + a numeric value column
    should still be detected as group/value and get box/violin recommendations."""
    import pandas as pd
    from make_my_figure_core.recommendations import recommend_for_table

    df = pd.DataFrame({
        "species": ["A", "A", "B", "B", "C", "C"] * 5,
        "flipper_length_mm": [181, 186, 195, 190, 210, 205] * 5,
    })
    rs = recommend_for_table(df, "grp_value")
    assert rs.schema == "generic_long"
    types = {r.plot_type for r in rs.recommendations}
    assert "boxplot_or_violin_with_points" in types
    assert not any("edger" in (r.why + " ".join(r.warnings)).lower() for r in rs.recommendations)


def test_generic_long_recommends_ridge_and_box():
    """A group + numeric value table should offer both box/violin and ridge."""
    import pandas as pd
    from make_my_figure_core.recommendations import recommend_for_table

    df = pd.DataFrame({"species": ["A", "B", "C"] * 8,
                       "flipper_length_mm": [181, 195, 210, 186, 190, 205] * 4})
    types = {r.plot_type for r in recommend_for_table(df, "p").recommendations}
    assert "boxplot_or_violin_with_points" in types
    assert "ridge_or_density_plot" in types


def test_edge_list_also_offers_a_chord_diagram_below_the_network_graph_and_it_renders():
    df = pd.DataFrame({"source": list("ABCA"), "target": list("BCAC"), "weight": [3, 1, 2, 4]})
    spec = recommend_for_table(df, "links.csv")
    assert spec.schema == "network_edge_list"
    by_type = {r.plot_type: r for r in spec.recommendations}
    assert "chord_diagram" in by_type
    assert by_type["chord_diagram"].confidence < by_type["network_graph"].confidence
    draft = by_type["chord_diagram"].plot_spec_draft
    assert draft["plot_type"] == "chord_diagram" and "group" not in draft["mapping"]
    assert draft["mapping"]["source"] == "source" and draft["mapping"]["target"] == "target"
    result = render(draft, df)
    assert result.metadata["n_categories"] == 3
    plt.close(result.figure)


def test_chord_diagram_is_not_recommended_for_ordinary_tables_or_matrices():
    plain = recommend_for_table(pd.DataFrame({"group": list("AABB"), "value": [1, 2, 3, 4]}))
    assert "chord_diagram" not in {r.plot_type for r in plain.recommendations}
    matrix = recommend_for_table(_matrix())
    assert "chord_diagram" not in {r.plot_type for r in matrix.recommendations}
    paired = recommend_for_table(pd.DataFrame({"subject": ["s1", "s1", "s2", "s2"],
                                               "group": ["pre", "post", "pre", "post"],
                                               "value": [1.0, 2.0, 1.5, 2.5]}))
    assert "chord_diagram" not in {r.plot_type for r in paired.recommendations}
