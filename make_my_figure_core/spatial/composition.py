"""Local cell-type composition around each focal cell.

This is the representation the CC neighbourhood method clusters, and the input
to every enrichment number downstream, so it is kept deliberately plain: count
the cell types among a cell's neighbours, optionally normalise to fractions.
Nothing is smoothed, weighted or imputed here.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from make_my_figure_core.spatial.neighbors import NeighborGraph, SpatialError


def cell_type_levels(series: pd.Series) -> List[str]:
    """Stable, explicit cell-type ordering: categorical order if declared, else sorted."""
    if isinstance(series.dtype, pd.CategoricalDtype):
        return [str(c) for c in series.cat.categories]
    return sorted({str(v) for v in series.dropna().unique()})


def local_composition(df: pd.DataFrame, cell_type_column: str, graph: NeighborGraph,
                      *, normalize: str = "fraction",
                      levels: Optional[Sequence[str]] = None
                      ) -> Tuple[np.ndarray, List[str]]:
    """Return an (n_cells, n_types) matrix of neighbour composition.

    ``normalize="count"`` gives raw neighbour counts; ``"fraction"`` divides by the
    number of neighbours of that cell. A cell with no neighbours yields a row of
    zeros under either setting — an undefined composition is reported as empty
    rather than silently filled in.
    """
    if normalize not in ("count", "fraction"):
        raise SpatialError("normalize must be 'count' or 'fraction'.")
    if cell_type_column not in df.columns:
        raise SpatialError(f"cell-type column {cell_type_column!r} is not in the table.")

    series = df[cell_type_column]
    if series.isna().any():
        raise SpatialError(
            f"{int(series.isna().sum())} row(s) have no value in {cell_type_column!r}. "
            "Cells without a cell type cannot contribute to composition — label or remove them.")

    lv = [str(v) for v in levels] if levels is not None else cell_type_levels(series)
    index = {t: i for i, t in enumerate(lv)}
    unknown = sorted({str(v) for v in series.unique()} - set(index))
    if unknown:
        raise SpatialError(f"cell types not in the declared level list: {unknown}")

    codes = np.array([index[str(v)] for v in series], dtype=int)
    out = np.zeros((len(df), len(lv)), dtype=float)
    for i, nb in enumerate(graph.indices):
        if len(nb) == 0:
            continue
        counts = np.bincount(codes[nb], minlength=len(lv))
        out[i] = counts / counts.sum() if normalize == "fraction" else counts
    return out, lv
