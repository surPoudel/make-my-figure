"""Cellular-neighbourhood identification.

Implements the CC method as published (Tao et al. 2024, "CN identification
methods / CC"): each cell is represented by the cell-type frequencies among its
nearest *m* neighbours **including itself**, and those representations are
clustered with k-means.

This is deliberately the conservative baseline rather than the newest method.
It is *not* CNE, and is never labelled as such: CNE additionally uses Gaussian
distance weighting, perplexity-adapted variance, inverse-dataset-frequency
scaling and spatially regularised k-means, and is out of scope here because it
could not be validated against the published outputs within this branch.

The number of neighbourhoods is a user decision. Nothing here estimates the
biologically correct number, and no default pretends to.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from make_my_figure_core.spatial.composition import local_composition
from make_my_figure_core.spatial.neighbors import (
    NeighborGraph, NeighborGraphSpec, SpatialError, build_neighbor_graph,
)


@dataclass
class NeighborhoodResult:
    """Assignments plus everything needed to explain or reproduce them."""

    labels: pd.Series                      # neighbourhood label per input row
    representation: np.ndarray             # (n_cells, n_types) composition clustered
    cell_type_levels: List[str]
    centroids: np.ndarray
    method: str
    n_neighborhoods: int
    m_neighbors: int
    random_seed: int
    inertia: float
    graph_record: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        sizes = self.labels.value_counts().sort_index()
        return {"method": self.method, "n_neighborhoods": int(self.n_neighborhoods),
                "m_neighbors": int(self.m_neighbors), "random_seed": int(self.random_seed),
                "cell_type_levels": list(self.cell_type_levels),
                "inertia": float(self.inertia),
                "neighborhood_sizes": {str(k): int(v) for k, v in sizes.items()},
                "neighbor_graph": self.graph_record,
                "warnings": list(self.warnings)}


def identify_neighborhoods_cc(df: pd.DataFrame, x: str, y: str, cell_type_column: str,
                              *, n_neighborhoods: int, m_neighbors: int = 10,
                              sample_column: Optional[str] = None,
                              coordinate_units: str = "arbitrary",
                              random_seed: int = 0,
                              metric: str = "euclidean",
                              label_prefix: str = "CN") -> NeighborhoodResult:
    """CC neighbourhoods: local composition among the nearest ``m`` neighbours, then k-means."""
    from sklearn.cluster import KMeans

    if int(n_neighborhoods) < 2:
        raise SpatialError("n_neighborhoods must be at least 2.")
    if int(m_neighbors) < 1:
        raise SpatialError("m_neighbors must be at least 1.")
    n = len(df)
    if n < int(n_neighborhoods):
        raise SpatialError(
            f"cannot ask for {n_neighborhoods} neighbourhoods from {n} cells.")

    # "nearest m neighbours including itself" — the focal cell is one of the m.
    graph_spec = NeighborGraphSpec(
        method="knn", k=max(int(m_neighbors) - 1, 0) or 1, metric=metric,
        include_self=True, sample_column=sample_column,
        coordinate_units=coordinate_units)
    graph = build_neighbor_graph(df, x, y, graph_spec)

    rep, levels = local_composition(df, cell_type_column, graph, normalize="fraction")

    km = KMeans(n_clusters=int(n_neighborhoods), random_state=int(random_seed), n_init=10)
    codes = km.fit_predict(rep)

    width = len(str(int(n_neighborhoods)))
    labels = pd.Series([f"{label_prefix}{c + 1:0{width}d}" for c in codes],
                       index=df.index, name="neighborhood")

    warnings = list(graph.warnings)
    present = labels.nunique()
    if present < int(n_neighborhoods):
        warnings.append(
            f"k-means returned {present} non-empty neighbourhoods out of the "
            f"{n_neighborhoods} requested.")
    sizes = labels.value_counts()
    tiny = sizes[sizes < max(3, 0.001 * n)]
    if len(tiny):
        warnings.append(
            f"very small neighbourhood(s): {', '.join(f'{k} (n={v})' for k, v in tiny.items())}. "
            "Enrichment for these rests on few cells and should be read with that in mind.")

    return NeighborhoodResult(
        labels=labels, representation=rep, cell_type_levels=levels,
        centroids=np.asarray(km.cluster_centers_, dtype=float),
        method="CC", n_neighborhoods=int(n_neighborhoods), m_neighbors=int(m_neighbors),
        random_seed=int(random_seed), inertia=float(km.inertia_),
        graph_record=graph.to_dict(), warnings=warnings)
