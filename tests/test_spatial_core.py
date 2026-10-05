"""Spatial core validated against independent brute-force implementations.

Every calculation here is checked against code written a second time, directly
from the definition, rather than against a stored expectation produced by the
code under test. The published formulas come from Tao et al. 2024
(PLOS Comput Biol 20(8):e1012344).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.spatial import (
    NeighborGraphSpec, SpatialError, build_neighbor_graph, conditional_entropy,
    ct_cn_enrichment, identify_neighborhoods_cc, local_composition, neighborhood_qc,
)


@pytest.fixture(scope="module")
def cells() -> pd.DataFrame:
    rng = np.random.default_rng(12345)
    n = 120
    return pd.DataFrame({
        "x": rng.uniform(0, 100, n), "y": rng.uniform(0, 100, n),
        "cell_type": rng.choice(["Tumor", "T cell", "B cell", "Stroma"], n),
        "sample": rng.choice(["S1", "S2"], n),
    })


def _brute_knn(xy: np.ndarray, k: int, include_self: bool):
    out = []
    for i in range(len(xy)):
        d = np.sqrt(((xy - xy[i]) ** 2).sum(axis=1))
        order = np.lexsort((np.arange(len(xy)), d))   # distance, ties by row order
        sel = list(order[: k + 1]) if include_self else [j for j in order if j != i][:k]
        out.append(sorted(sel))
    return out


@pytest.mark.parametrize("k,include_self", [(5, True), (5, False), (1, True), (12, False)])
def test_knn_matches_brute_force_within_each_sample(cells, k, include_self):
    g = build_neighbor_graph(cells, "x", "y", NeighborGraphSpec(
        method="knn", k=k, include_self=include_self, sample_column="sample"))
    for s in cells["sample"].unique():
        pos = np.flatnonzero(cells["sample"].to_numpy() == s)
        bf = _brute_knn(cells.loc[cells["sample"] == s, ["x", "y"]].to_numpy(), k, include_self)
        for r, p in enumerate(pos):
            assert sorted(g.indices[p].tolist()) == sorted(pos[np.array(bf[r], int)].tolist())


def test_cells_from_different_samples_never_become_neighbours(cells):
    """The rule that keeps the analysis physically meaningful."""
    g = build_neighbor_graph(cells, "x", "y", NeighborGraphSpec(
        method="knn", k=20, sample_column="sample"))
    smp = cells["sample"].to_numpy()
    assert all(len(set(smp[nb])) <= 1 for nb in g.indices)


def test_radius_neighbours_match_brute_force(cells):
    radius = 15.0
    g = build_neighbor_graph(cells, "x", "y", NeighborGraphSpec(
        method="radius", radius=radius, include_self=False, sample_column="sample"))
    smp = cells["sample"].to_numpy()
    for s in cells["sample"].unique():
        pos = np.flatnonzero(smp == s)
        xy = cells.loc[cells["sample"] == s, ["x", "y"]].to_numpy()
        for r, p in enumerate(pos):
            d = np.sqrt(((xy - xy[r]) ** 2).sum(axis=1))
            exp = sorted(pos[np.flatnonzero((d <= radius) & (np.arange(len(xy)) != r))].tolist())
            assert sorted(g.indices[p].tolist()) == exp


def test_local_composition_counts_are_exact_and_fractions_sum_to_one(cells):
    g = build_neighbor_graph(cells, "x", "y", NeighborGraphSpec(
        method="knn", k=6, sample_column="sample"))
    counts, levels = local_composition(cells, "cell_type", g, normalize="count")
    fracs, _ = local_composition(cells, "cell_type", g, normalize="fraction")
    ct = cells["cell_type"].to_numpy()
    for i, nb in enumerate(g.indices):
        for j, t in enumerate(levels):
            assert counts[i, j] == sum(1 for q in nb if ct[q] == t)
    assert np.allclose(fracs.sum(axis=1), 1.0)


def test_ct_cn_enrichment_matches_the_published_formula(cells):
    """score = log2((|C_n,t| + F(t)) / (|C_n| + 1)) - log2(F(t))."""
    rng = np.random.default_rng(7)
    ct = cells["cell_type"].reset_index(drop=True)
    cn = pd.Series(rng.choice(["CN1", "CN2", "CN3"], len(ct)))
    table = ct_cn_enrichment(ct, cn)
    n = len(ct)
    freq = {t: v / n for t, v in ct.value_counts().items()}
    for _, row in table.iterrows():
        mask = cn == row["neighborhood"]
        c_nt = int(((ct == row["cell_type"]) & mask).sum())
        size_n = int(mask.sum())
        f_t = freq[row["cell_type"]]
        expected = math.log2((c_nt + f_t) / (size_n + 1.0)) - math.log2(f_t)
        assert row["enrichment_score"] == pytest.approx(expected, abs=1e-12)


def test_conditional_entropy_matches_direct_summation(cells):
    rng = np.random.default_rng(3)
    ct = cells["cell_type"].reset_index(drop=True)
    cn = pd.Series(rng.choice(["CN1", "CN2", "CN3"], len(ct)))
    tab = pd.crosstab(cn, ct).to_numpy().astype(float)
    n = tab.sum()
    expected = sum((tab[i, j] / n) * math.log2(tab[i].sum() / tab[i, j])
                   for i in range(tab.shape[0]) for j in range(tab.shape[1]) if tab[i, j] > 0)
    assert conditional_entropy(ct, cn) == pytest.approx(expected, abs=1e-12)


def test_perfectly_pure_neighbourhoods_have_zero_conditional_entropy():
    ct = pd.Series(["A"] * 50 + ["B"] * 50)
    cn = pd.Series(["CN1"] * 50 + ["CN2"] * 50)
    assert conditional_entropy(ct, cn) == pytest.approx(0.0, abs=1e-12)


def test_cc_neighbourhoods_are_deterministic_for_a_fixed_seed(cells):
    kw = dict(n_neighborhoods=3, m_neighbors=8, sample_column="sample", random_seed=42)
    a = identify_neighborhoods_cc(cells, "x", "y", "cell_type", **kw)
    b = identify_neighborhoods_cc(cells, "x", "y", "cell_type", **kw)
    assert a.labels.tolist() == b.labels.tolist()
    assert a.inertia == pytest.approx(b.inertia)


def test_cc_clusterings_agree_modulo_label_permutation(cells):
    """Different seeds may name clusters differently; the partition should still map 1:1."""
    a = identify_neighborhoods_cc(cells, "x", "y", "cell_type", n_neighborhoods=3,
                                  m_neighbors=8, sample_column="sample", random_seed=0)
    b = identify_neighborhoods_cc(cells, "x", "y", "cell_type", n_neighborhoods=3,
                                  m_neighbors=8, sample_column="sample", random_seed=1)
    table = pd.crosstab(a.labels, b.labels)
    # Each row's mass concentrated in one column => same partition under relabelling.
    assert (table.max(axis=1) / table.sum(axis=1)).min() > 0.95


def test_cc_records_every_parameter_needed_to_reproduce_it(cells):
    res = identify_neighborhoods_cc(cells, "x", "y", "cell_type", n_neighborhoods=3,
                                    m_neighbors=8, sample_column="sample", random_seed=5)
    rec = res.to_dict()
    assert rec["method"] == "CC" and rec["random_seed"] == 5 and rec["m_neighbors"] == 8
    assert rec["neighbor_graph"]["graph"]["include_self"] is True
    assert rec["neighbor_graph"]["graph"]["sample_column"] == "sample"


def test_non_finite_coordinates_are_refused_not_dropped(cells):
    bad = cells.copy()
    bad.loc[bad.index[0], "x"] = np.nan
    with pytest.raises(SpatialError, match="non-finite"):
        build_neighbor_graph(bad, "x", "y", NeighborGraphSpec(method="knn", k=5))


def test_missing_cell_type_is_refused_not_imputed(cells):
    bad = cells.copy()
    bad.loc[bad.index[0], "cell_type"] = None
    g = build_neighbor_graph(bad, "x", "y", NeighborGraphSpec(method="knn", k=5))
    with pytest.raises(SpatialError, match="no value"):
        local_composition(bad, "cell_type", g)


def test_k_larger_than_the_sample_warns_rather_than_failing_silently(cells):
    small = cells[cells["sample"] == "S1"].head(4)
    g = build_neighbor_graph(small, "x", "y", NeighborGraphSpec(
        method="knn", k=50, sample_column="sample"))
    assert any("available neighbours" in w for w in g.warnings)


def test_invalid_graph_parameters_are_rejected_at_construction():
    with pytest.raises(SpatialError):
        NeighborGraphSpec(method="knn", k=0)
    with pytest.raises(SpatialError):
        NeighborGraphSpec(method="radius", radius=0)
    with pytest.raises(SpatialError):
        NeighborGraphSpec(method="triangulation")
    with pytest.raises(SpatialError):
        NeighborGraphSpec(coordinate_units="furlongs")


def test_neighborhood_qc_reports_metrics_without_judging_them(cells):
    res = identify_neighborhoods_cc(cells, "x", "y", "cell_type", n_neighborhoods=3,
                                    m_neighbors=8, sample_column="sample", random_seed=0)
    qc = neighborhood_qc(cells["cell_type"], res.labels, samples=cells["sample"])
    assert {"n_cells", "shannon_entropy_bits", "dominant_cell_type", "is_rare",
            "n_samples_represented"} <= set(qc.columns)
    assert (qc["n_cells"] > 0).all()
    assert qc["fraction_of_all_cells"].sum() == pytest.approx(1.0)
