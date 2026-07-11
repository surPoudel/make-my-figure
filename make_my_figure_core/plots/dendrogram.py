"""Standalone hierarchical clustering dendrogram.

Accepts a ``features x samples`` matrix (first column = row labels, remaining
columns numeric). Clusters either the rows (features) or the columns (samples,
by transposing) with a configurable linkage method and distance metric, then
draws a SciPy dendrogram. This is deliberately kept separate from the clustered
heatmap but reuses the shared clustering utilities so behaviour matches.

TODO (future): accept a precomputed linkage/distance table directly. For v0.4
the linkage is always computed from the numeric matrix.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots._v04_shared import linkage_matrix, numeric_matrix
from make_my_figure_core.plots.base import (
    RenderResult,
    base_metadata,
    figure_size,
    get_mapping,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "hierarchical_dendrogram"

_METHODS = ("average", "complete", "single", "ward")
_MAX_LEAF_LABELS = 40


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    row_id = get_mapping(spec, "row_id", None)
    method = str(get_mapping(spec, "method", "average")).lower()
    if method not in _METHODS:
        method = "average"
    metric = str(get_mapping(spec, "metric", "euclidean")).lower()
    orientation = str(get_mapping(spec, "orientation", "top")).lower()
    if orientation not in ("top", "left"):
        orientation = "top"
    cluster = str(get_mapping(spec, "cluster", "rows")).lower()
    if cluster not in ("rows", "columns"):
        cluster = "rows"

    row_labels, value_cols, matrix, warnings = numeric_matrix(df, row_id, context=PLOT_TYPE)
    warnings = list(warnings)

    if cluster == "columns":
        data = matrix.T
        labels = list(value_cols)
        entity = "sample"
    else:
        data = matrix
        labels = list(row_labels)
        entity = "feature"

    from scipy.cluster.hierarchy import dendrogram

    if data.shape[0] < 2:
        # Degenerate: nothing to cluster. Keep it honest rather than crash.
        from make_my_figure_core.plots.base import RenderError

        raise RenderError(f"{PLOT_TYPE}: need at least 2 {entity}s to cluster (got {data.shape[0]}).")

    z = linkage_matrix(data, method=method, metric=metric)

    n_leaves = data.shape[0]
    show_labels = n_leaves <= _MAX_LEAF_LABELS
    if not show_labels:
        warnings.append(f"{n_leaves} leaves: labels hidden for legibility "
                        f"(<= {_MAX_LEAF_LABELS} shown).")

    # Height grows with the number of leaves when drawn as a left dendrogram;
    # width grows for a top dendrogram, so leaf labels stay readable.
    aspect = 0.62 if orientation == "top" else max(0.6, min(2.2, 0.05 * n_leaves + 0.4))
    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=aspect))
        dendrogram(
            z,
            ax=ax,
            orientation=orientation,
            labels=[str(x) for x in labels],
            no_labels=not show_labels,
            color_threshold=0,
            above_threshold_color=style.color_for(0),
            leaf_rotation=90 if orientation == "top" else 0,
        )
        # Tidy leaf-label font to the style's tick size.
        tick_axis = ax.get_xaxis() if orientation == "top" else ax.get_yaxis()
        for lbl in tick_axis.get_ticklabels():
            lbl.set_fontsize(style.tick_label_pt)

        dist_label = f"Distance ({method}, {metric})"
        leaf_label = f"{entity.capitalize()}s"
        if orientation == "top":
            ax.set_ylabel(dist_label)
            ax.set_xlabel(leaf_label)
        else:
            ax.set_xlabel(dist_label)
            ax.set_ylabel(leaf_label)

        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)
        fig.tight_layout()

    meta = base_metadata(spec, style, df, used_columns=[row_id or df.columns[0]] + value_cols)
    meta["linkage_method"] = method
    meta["metric"] = metric if method != "ward" else "euclidean"
    meta["clustered"] = cluster
    meta["n_leaves"] = int(n_leaves)
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
