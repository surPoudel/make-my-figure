"""v0.5.2: memory guards for RAM-intensive clustering + RNA-seq matrix parsing.

Huge matrices (e.g. a 55k-gene RSEM count table) previously OOM'd because
hierarchical clustering builds an O(n^2) distance matrix. These tests verify the
feature-axis cap (top-variable subset) and the robust sample-column detection
(dropping annotation columns like geneSymbol/bioType/annotationLevel).
"""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")

from make_my_figure_core import clustering as C
from make_my_figure_core.plots.registry import make_spec, render


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _rsem_like(n_genes=3000, n_samples=6, seed=0):
    """A features x samples matrix with RNA-seq-style annotation columns."""
    rng = np.random.default_rng(seed)
    counts = rng.poisson(50, size=(n_genes, n_samples)).astype(float)
    # make a handful of genes highly variable so top-variance selection is deterministic
    hv = min(20, n_genes)
    counts[:hv] += rng.normal(0, 500, size=(hv, n_samples))
    data = {"geneID": [f"ENSG{i:07d}" for i in range(n_genes)],
            "geneSymbol": [f"Gene{i}" for i in range(n_genes)],   # non-numeric
            "bioType": ["protein_coding"] * n_genes,               # non-numeric
            "annotationLevel": rng.integers(1, 4, n_genes)}        # numeric annotation!
    for j in range(n_samples):
        data[f"S{j+1}"] = counts[:, j]
    return pd.DataFrame(data)


# --- clustering helpers -----------------------------------------------------
def test_top_variable_indices_picks_highest_variance():
    m = np.array([[1, 1, 1], [0, 5, 10], [2, 2, 2], [0, 100, 200]], dtype=float)
    idx = set(C.top_variable_indices(m, 2).tolist())
    assert idx == {1, 3}   # the two highest-variance rows


def test_cap_rows_by_variance_subsets_and_keeps_highlighted():
    m = np.random.default_rng(1).normal(0, 1, (500, 5))
    m[0] = 0.0   # row 'g0' is constant (lowest variance) but we force-keep it
    labels = [f"g{i}" for i in range(500)]
    warns = []
    mat, labs, idx = C.cap_rows_by_variance(m, labels, 50, warns, keep_labels=["g0"])
    assert mat.shape[0] == len(labs) <= 51 and "g0" in labs   # highlighted kept
    assert any("exceed" in w for w in warns)
    # no cap when under the limit
    mat2, labs2, idx2 = C.cap_rows_by_variance(m, labels, 1000, [])
    assert idx2 is None and len(labs2) == 500


# --- heatmap on a large RNA-seq-style matrix --------------------------------
def test_heatmap_caps_features_and_does_not_blow_up():
    df = _rsem_like(n_genes=3000, n_samples=6)
    spec = make_spec("heatmap_clustered_matrix", "m.tsv", "publication")
    spec["mapping"] = dict(spec["mapping"], row_id="geneID",
                           exclude_columns=["annotationLevel"], max_features=500)
    r = render(spec, df)
    assert r.metadata["matrix_shape"][0] == 500        # capped from 3000
    assert r.metadata["matrix_shape"][1] == 6          # 6 samples (annotation cols dropped)
    assert any("exceed" in w for w in r.warnings)
    assert r.metadata["publication_check"]["passed"]


def test_heatmap_drops_annotation_columns_and_reports_samples():
    df = _rsem_like(n_genes=100, n_samples=4)
    spec = make_spec("heatmap_clustered_matrix", "m.tsv", "publication")
    spec["mapping"] = dict(spec["mapping"], row_id="geneID",
                           exclude_columns=["annotationLevel"])
    r = render(spec, df)
    # only the 4 real sample columns survive (geneSymbol/bioType non-numeric, annotationLevel excluded)
    assert r.metadata["matrix_shape"][1] == 4
    assert any("Ignored non-sample column" in w for w in r.warnings)
    assert any("Using 4 sample column" in w for w in r.warnings)


def test_heatmap_highlight_row_survives_the_cap():
    df = _rsem_like(n_genes=1000, n_samples=5)
    target = df["geneID"].iloc[900]     # a low-variance gene deep in the list
    spec = make_spec("heatmap_clustered_matrix", "m.tsv", "publication")
    spec["mapping"] = dict(spec["mapping"], row_id="geneID",
                           exclude_columns=["annotationLevel"], max_features=100,
                           highlight_rows=[target], show_row_labels=False)
    r = render(spec, df)
    assert r.metadata["matrix_shape"][0] <= 101   # 100 top-var + the highlighted one
    plt.close(r.figure)


# --- hierarchical_clustering caps too ---------------------------------------
def test_hierarchical_clustering_caps_rows():
    df = _rsem_like(n_genes=2500, n_samples=6)
    spec = make_spec("hierarchical_clustering", "m.tsv", "publication")
    spec["mapping"] = dict(spec["mapping"], row_id="geneID", k=3,
                           exclude_columns=["annotationLevel"], max_features=400)
    r = render(spec, df)
    assign = r.metadata.get("cluster_assignment")
    assert assign is not None and len(assign) == 400        # clustered the capped set
    assert len({row["cluster"] for row in assign}) == 3


# --- PCA restricts to metadata samples (drops annotation columns) -----------
def test_pca_uses_only_metadata_samples():
    df = _rsem_like(n_genes=800, n_samples=5)
    meta = pd.DataFrame({"SampleID": [f"S{j+1}" for j in range(5)],
                         "Group": ["A", "A", "B", "B", "B"]})
    spec = make_spec("pca_scatter_from_matrix", "m.tsv", "publication")
    spec["mapping"] = dict(spec["mapping"], matrix_row_id="geneID",
                           metadata_key="SampleID", color="Group")
    r = render(spec, df, aux={"metadata": meta})
    # annotationLevel + geneSymbol/bioType must NOT be counted as samples
    assert any("not present in metadata" in w for w in r.warnings)
    assert r.metadata["color_by"] == "Group"
    plt.close(r.figure)


def test_numeric_matrix_exclude_param():
    from make_my_figure_core.plots._v04_shared import numeric_matrix

    df = _rsem_like(n_genes=10, n_samples=3)
    labels, cols, mat, warns = numeric_matrix(df, "geneID", context="t",
                                              exclude=["annotationLevel"])
    assert set(cols) == {"S1", "S2", "S3"}   # annotation cols excluded/dropped
    assert mat.shape == (10, 3)
