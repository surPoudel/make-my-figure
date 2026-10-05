"""Spatial neighbour graphs for cellular-neighbourhood analysis.

Two graph constructions are supported, both of them explicit: k-nearest
neighbours and fixed-radius neighbours. Every parameter that changes the result
is carried on :class:`NeighborGraphSpec` and recorded in provenance, because a
neighbourhood result is meaningless without the graph that produced it.

The rule that matters scientifically: **cells from different samples or images
never become neighbours**. Tissue sections have unrelated coordinate systems, so
a graph built across them would invent adjacency that does not exist. The graph
is therefore built per sample and reassembled, never globally.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

_METRICS = {"euclidean": 2, "manhattan": 1, "chebyshev": np.inf}
_METHODS = ("knn", "radius")
_UNITS = ("pixel", "micrometre", "millimetre", "arbitrary")


class SpatialError(Exception):
    """Raised when a spatial input or parameter combination cannot be used."""


@dataclass(frozen=True)
class NeighborGraphSpec:
    """Every input that changes the neighbour graph, and nothing that does not."""

    method: str = "knn"
    k: Optional[int] = 10
    radius: Optional[float] = None
    metric: str = "euclidean"
    include_self: bool = True
    sample_column: Optional[str] = None
    coordinate_units: str = "arbitrary"
    # Distance ties are broken by ascending row position, so a given table always
    # yields the same graph. Recorded because it is a real choice, not a detail.
    tie_handling: str = "stable_by_row_order"

    def __post_init__(self) -> None:
        if self.method not in _METHODS:
            raise SpatialError(f"method must be one of {_METHODS}, got {self.method!r}")
        if self.metric not in _METRICS:
            raise SpatialError(f"metric must be one of {sorted(_METRICS)}, got {self.metric!r}")
        if self.coordinate_units not in _UNITS:
            raise SpatialError(f"coordinate_units must be one of {_UNITS}, "
                               f"got {self.coordinate_units!r}")
        if self.method == "knn":
            if self.k is None or int(self.k) < 1:
                raise SpatialError("knn requires k >= 1.")
        else:
            if self.radius is None or float(self.radius) <= 0:
                raise SpatialError("radius neighbours require radius > 0.")

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.method, "k": self.k, "radius": self.radius,
                "metric": self.metric, "include_self": self.include_self,
                "sample_column": self.sample_column,
                "coordinate_units": self.coordinate_units,
                "tie_handling": self.tie_handling}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NeighborGraphSpec":
        known = {f: d[f] for f in
                 ("method", "k", "radius", "metric", "include_self",
                  "sample_column", "coordinate_units", "tie_handling") if f in d}
        return cls(**known)


@dataclass
class NeighborGraph:
    """Neighbour indices per cell, as positions into the source frame."""

    indices: List[np.ndarray]
    spec: NeighborGraphSpec
    n_cells: int
    warnings: List[str] = field(default_factory=list)

    def sizes(self) -> np.ndarray:
        return np.array([len(i) for i in self.indices], dtype=int)

    def to_dict(self) -> Dict[str, Any]:
        sizes = self.sizes()
        return {"graph": self.spec.to_dict(), "n_cells": int(self.n_cells),
                "neighbors_min": int(sizes.min()) if len(sizes) else 0,
                "neighbors_max": int(sizes.max()) if len(sizes) else 0,
                "neighbors_mean": float(sizes.mean()) if len(sizes) else 0.0,
                "warnings": list(self.warnings)}


def _coords(df: pd.DataFrame, x: str, y: str) -> np.ndarray:
    for col in (x, y):
        if col not in df.columns:
            raise SpatialError(f"coordinate column {col!r} is not in the table.")
    xy = np.column_stack([pd.to_numeric(df[x], errors="coerce").to_numpy(dtype=float),
                          pd.to_numeric(df[y], errors="coerce").to_numpy(dtype=float)])
    if not np.isfinite(xy).all():
        bad = int((~np.isfinite(xy).all(axis=1)).sum())
        raise SpatialError(
            f"{bad} row(s) have non-finite coordinates in {x!r}/{y!r}. "
            "Spatial analysis will not silently drop them — remove or repair them first.")
    return xy


def build_neighbor_graph(df: pd.DataFrame, x: str, y: str,
                         spec: NeighborGraphSpec) -> NeighborGraph:
    """Build the neighbour graph, one independent graph per sample/image."""
    from scipy.spatial import cKDTree

    xy = _coords(df, x, y)
    n = len(df)
    if n == 0:
        raise SpatialError("the spatial table is empty.")

    if spec.sample_column:
        if spec.sample_column not in df.columns:
            raise SpatialError(f"sample column {spec.sample_column!r} is not in the table.")
        labels = df[spec.sample_column].astype(object).to_numpy()
    else:
        labels = np.zeros(n, dtype=int)

    p = _METRICS[spec.metric]
    out: List[np.ndarray] = [np.empty(0, dtype=int)] * n
    warnings: List[str] = []
    if not spec.sample_column:
        warnings.append(
            "No sample/image column was given, so every cell in the table is treated as one "
            "tissue. If this table holds more than one section, set the sample column — "
            "otherwise cells from different sections become neighbours.")

    for label in pd.unique(labels):
        pos = np.flatnonzero(labels == label)
        sub = xy[pos]
        tree = cKDTree(sub)
        m = len(pos)

        if spec.method == "knn":
            k_req = int(spec.k)
            # +1 because the query point is always its own nearest neighbour.
            k_eff = min(k_req + 1, m)
            if k_req + 1 > m:
                warnings.append(
                    f"sample {label!r}: k={k_req} needs {k_req + 1} cells including the focal "
                    f"cell, but the sample has {m}; using the {k_eff - 1} available neighbours.")
            _, idx = tree.query(sub, k=k_eff, p=p)
            idx = np.atleast_2d(idx)
            for r in range(m):
                row = idx[r]
                row = row[row < m]                      # cKDTree pads with m when k > points
                if spec.include_self:
                    keep = row
                else:
                    keep = row[row != r]
                out[pos[r]] = pos[keep]
        else:
            radius = float(spec.radius)
            found = tree.query_ball_point(sub, r=radius, p=p)
            for r in range(m):
                row = np.sort(np.asarray(found[r], dtype=int))
                if not spec.include_self:
                    row = row[row != r]
                out[pos[r]] = pos[row]

    if spec.method == "radius":
        empty = sum(1 for a in out if len(a) == 0)
        if empty:
            warnings.append(
                f"{empty} cell(s) have no neighbour within radius={spec.radius} "
                f"{spec.coordinate_units}. Their local composition is undefined and is reported "
                "as all-zero rather than imputed.")

    return NeighborGraph(indices=out, spec=spec, n_cells=n, warnings=warnings)
