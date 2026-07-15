"""Shared hierarchical-clustering utilities (v0.5).

Frontend-agnostic helpers used by the clustered heatmap, the standalone
dendrogram, and the hierarchical-clustering table output: matrix scaling,
distance/linkage computation with validated metric/method combinations, cutting
the tree into ``k`` clusters, building the cluster-assignment table, and mapping
clusters to colorblind-safe colors. SciPy only — no new dependency.

> Clustering is an *exploratory summary*. Callers are responsible for confirming
> the chosen distance metric, linkage, scaling, and k are appropriate for their
> data and for interpreting biological meaning.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

DISTANCE_METRICS = ("euclidean", "correlation", "cosine", "cityblock")
LINKAGE_METHODS = ("average", "complete", "single", "ward")
SCALES = ("none", "row_zscore", "column_zscore", "center_rows", "log", "log_zscore")
# Methods that are only valid with a Euclidean metric.
_EUCLIDEAN_ONLY = ("ward", "centroid", "median")

# Colorblind-safe qualitative palette for cluster tracks (Okabe-Ito + extensions).
CLUSTER_PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00",
                   "#56B4E9", "#F0E442", "#999999", "#117733", "#882255",
                   "#44AA99", "#332288"]


# Hierarchical clustering builds an O(n^2) pairwise-distance matrix, so a huge
# feature axis (e.g. 55k genes) exhausts RAM. Cap the number of clustered/shown
# features to the most variable ones by default; users can raise it or pre-filter.
DEFAULT_MAX_CLUSTER_FEATURES = 2000


class ClusteringError(Exception):
    """Raised for invalid clustering configuration (friendly message)."""


def top_variable_indices(matrix: np.ndarray, k: int) -> np.ndarray:
    """Indices of the ``k`` highest-variance rows (original order preserved)."""
    var = np.nanvar(np.asarray(matrix, dtype=float), axis=1)
    var = np.nan_to_num(var, nan=-1.0)
    k = int(min(max(k, 1), var.size))
    if k >= var.size:
        return np.arange(var.size)
    idx = np.argpartition(var, var.size - k)[-k:]
    return np.sort(idx)


def cap_rows_by_variance(matrix: np.ndarray, labels: List[str], max_rows: Optional[int],
                         warnings: List[str], *, keep_labels=None, what: str = "features"):
    """Limit the row (feature) axis to the top-``max_rows`` by variance.

    Prevents the O(n^2) clustering distance matrix from exhausting RAM on very
    tall matrices. Any ``keep_labels`` (e.g. highlighted genes) are always
    retained even if low-variance. Returns ``(matrix, labels, kept_indices)``;
    ``kept_indices`` is ``None`` when no capping was needed.
    """
    n = len(labels)
    if not max_rows or max_rows <= 0 or n <= max_rows:
        return matrix, labels, None
    keep = set(int(i) for i in top_variable_indices(matrix, max_rows).tolist())
    if keep_labels:
        wanted = {str(s).strip().lower() for s in keep_labels}
        for i, lab in enumerate(labels):
            if str(lab).strip().lower() in wanted:
                keep.add(i)
    idx = sorted(keep)
    warnings.append(
        f"{n} {what} exceed the {max_rows}-{what[:-1]} limit for clustering/display; "
        f"showing the top {max_rows} by variance (plus any highlighted) to stay within "
        f"memory. Pre-filter your matrix or raise 'max_features' to change this.")
    return matrix[idx], [labels[i] for i in idx], np.array(idx)


def scale_matrix(matrix: np.ndarray, scale: str) -> Tuple[np.ndarray, List[str]]:
    """Apply a scaling transform to a features x samples matrix.

    Rows are features. Returns ``(scaled, warnings)`` and never mutates input.
    """
    warnings: List[str] = []
    scale = (scale or "none").lower()
    X = np.array(matrix, dtype=float)
    if scale in ("log", "log_zscore"):
        if np.nanmin(X) < 0:
            warnings.append("Log scale requested but matrix has negatives; used log1p(clip>=0).")
        X = np.log1p(np.clip(X, 0, None))
    if scale == "log_zscore":
        # log-transform (above) then per-row (per-feature) z-score — the standard
        # readable heatmap for raw counts: compresses dynamic range, then shows
        # each feature's relative pattern across samples.
        mu = np.nanmean(X, axis=1, keepdims=True)
        sd = np.nanstd(X, axis=1, ddof=0, keepdims=True)
        sd[sd == 0] = 1.0
        X = (X - mu) / sd
    elif scale == "row_zscore":
        mu = np.nanmean(X, axis=1, keepdims=True)
        sd = np.nanstd(X, axis=1, ddof=0, keepdims=True)
        sd[sd == 0] = 1.0
        X = (X - mu) / sd
    elif scale == "column_zscore":
        mu = np.nanmean(X, axis=0, keepdims=True)
        sd = np.nanstd(X, axis=0, ddof=0, keepdims=True)
        sd[sd == 0] = 1.0
        X = (X - mu) / sd
    elif scale == "center_rows":
        X = X - np.nanmean(X, axis=1, keepdims=True)
    return X, warnings


def _validate(method: str, metric: str, n_objects: int) -> None:
    if method not in LINKAGE_METHODS:
        raise ClusteringError(f"Unknown linkage method '{method}'. Use one of {LINKAGE_METHODS}.")
    if metric not in DISTANCE_METRICS:
        raise ClusteringError(f"Unknown distance metric '{metric}'. Use one of {DISTANCE_METRICS}.")
    if method in _EUCLIDEAN_ONLY and metric != "euclidean":
        raise ClusteringError(
            f"Linkage '{method}' requires the euclidean metric (got '{metric}'). "
            f"Choose method=average/complete/single for '{metric}', or metric=euclidean for ward.")
    if n_objects < 2:
        raise ClusteringError("Need at least 2 objects to cluster.")


def compute_linkage(matrix: np.ndarray, *, method: str = "average",
                    metric: str = "euclidean", axis: str = "rows"):
    """Return a SciPy linkage for rows (features) or columns (samples).

    ``axis='columns'`` clusters the transpose. Constant rows/NaNs are handled:
    NaNs are imputed to the row mean (then 0) so distances are defined.
    """
    from scipy.cluster.hierarchy import linkage
    from scipy.spatial.distance import pdist

    X = np.array(matrix, dtype=float)
    if axis == "columns":
        X = X.T
    # Impute NaNs (row mean, then 0) so pdist is defined.
    if np.isnan(X).any():
        col_ok = np.where(np.isnan(X), np.nan, X)
        row_means = np.nanmean(col_ok, axis=1, keepdims=True)
        row_means = np.nan_to_num(row_means, nan=0.0)
        inds = np.where(np.isnan(X))
        X[inds] = np.take(row_means[:, 0], inds[0])
        X = np.nan_to_num(X, nan=0.0)
    _validate(method, metric, X.shape[0])
    # correlation/cosine distance is undefined for zero-variance rows; nudge them.
    if metric in ("correlation", "cosine"):
        var = X.var(axis=1)
        if (var == 0).any():
            X = X.copy()
            X[var == 0] += np.linspace(0, 1e-9, X.shape[1])
    dist = pdist(X, metric=metric)
    return linkage(dist, method=method)


def cut_k(linkage_z, k: int, n_objects: int) -> np.ndarray:
    """Cut the tree into exactly ``k`` clusters; returns 1-based cluster ids."""
    from scipy.cluster.hierarchy import fcluster

    if not isinstance(k, int) or k < 2 or k > n_objects:
        raise ClusteringError(f"k must be an integer in [2, {n_objects}] (got {k!r}).")
    return fcluster(linkage_z, t=k, criterion="maxclust")


def cut_distance(linkage_z, threshold: float) -> np.ndarray:
    """Cut the tree at a distance threshold; returns 1-based cluster ids."""
    from scipy.cluster.hierarchy import fcluster

    return fcluster(linkage_z, t=float(threshold), criterion="distance")


def leaf_order(linkage_z) -> List[int]:
    from scipy.cluster.hierarchy import leaves_list

    return list(leaves_list(linkage_z))


def cluster_color_map(cluster_ids: np.ndarray, prefix: str = "Cluster") -> Dict[str, str]:
    """Map ``f"{prefix} {id}"`` -> hex color, in ascending cluster-id order."""
    uniq = sorted(set(int(c) for c in cluster_ids))
    return {f"{prefix} {cid}": CLUSTER_PALETTE[i % len(CLUSTER_PALETTE)]
            for i, cid in enumerate(uniq)}


def assignment_table(labels: List[str], cluster_ids: np.ndarray, order: List[int],
                     *, prefix: str = "Cluster", id_name: str = "feature",
                     extra: Optional[pd.DataFrame] = None,
                     values: Optional[np.ndarray] = None) -> pd.DataFrame:
    """Build the cluster-assignment table (one row per clustered object)."""
    pos_in_order = {leaf: i for i, leaf in enumerate(order)}
    rows = []
    for i, lab in enumerate(labels):
        rows.append({
            id_name: lab,
            "cluster": f"{prefix} {int(cluster_ids[i])}",
            "cluster_id": int(cluster_ids[i]),
            "dendrogram_order": int(pos_in_order.get(i, i)),
        })
    tbl = pd.DataFrame(rows)
    if values is not None and len(values) == len(labels):
        tbl["mean_value"] = np.round(np.asarray(values, dtype=float), 4)
    if extra is not None and len(extra) == len(labels):
        tbl = pd.concat([tbl.reset_index(drop=True), extra.reset_index(drop=True)], axis=1)
    return tbl.sort_values(["cluster_id", "dendrogram_order"]).reset_index(drop=True)


def cluster_summary(cluster_ids: np.ndarray, *, method: str, metric: str, scale: str,
                    k: Optional[int], axis: str, warnings: List[str]) -> Dict[str, Any]:
    """Summary dict: number/size of clusters + the parameters used."""
    uniq, counts = np.unique(cluster_ids, return_counts=True)
    return {
        "n_clusters": int(len(uniq)),
        "cluster_sizes": {f"Cluster {int(c)}": int(n) for c, n in zip(uniq, counts)},
        "linkage_method": method, "distance_metric": metric, "scaling": scale,
        "k": k, "clustered_axis": axis, "warnings": list(warnings),
        "note": ("Exploratory clustering summary — verify metric/linkage/scaling/k are "
                 "appropriate for your data before interpreting."),
    }
