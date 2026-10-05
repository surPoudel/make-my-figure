"""Spatial analysis for MakeMyFigure (experimental, v2 line).

Public surface kept small on purpose: a neighbour graph, the local composition
it implies, CC neighbourhood identification, and the published CT-CN enrichment
and QC calculations.
"""

from make_my_figure_core.spatial.composition import cell_type_levels, local_composition
from make_my_figure_core.spatial.enrichment import (
    conditional_entropy, contingency, ct_cn_enrichment, neighborhood_qc,
)
from make_my_figure_core.spatial.neighborhoods import (
    NeighborhoodResult, identify_neighborhoods_cc,
)
from make_my_figure_core.spatial.neighbors import (
    NeighborGraph, NeighborGraphSpec, SpatialError, build_neighbor_graph,
)

__all__ = [
    "NeighborGraph", "NeighborGraphSpec", "SpatialError", "build_neighbor_graph",
    "local_composition", "cell_type_levels",
    "identify_neighborhoods_cc", "NeighborhoodResult",
    "ct_cn_enrichment", "contingency", "conditional_entropy", "neighborhood_qc",
]
