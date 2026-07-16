"""Hierarchical clustering result view (v0.5).

A dedicated clustering *result* plot: cluster a features x samples matrix into
``k`` clusters, show the (scaled) matrix ordered by the dendrogram with a
cluster color strip on the clustered axis, and export the full cluster-assignment
table + summary in the render metadata (so the app can save the assignments as a
table). Distinct from the clustered heatmap (exploratory display) and the
standalone dendrogram (tree only).

Clustering is an exploratory summary — verify the chosen distance metric,
linkage, scaling, and k are appropriate for your data before interpreting.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core import clustering as _clust
from make_my_figure_core.plots._v04_shared import numeric_matrix
from make_my_figure_core.plots.base import (
    RenderError,
    RenderResult,
    base_metadata,
    get_mapping,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "hierarchical_clustering"


def _draw_cluster_strip(ax, side: str, codes: np.ndarray, colors: List[str], style) -> None:
    from matplotlib.colors import ListedColormap
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    cmap = ListedColormap(colors)
    divider = make_axes_locatable(ax)
    if side == "left":
        cax = divider.append_axes("left", size="4.5%", pad=0.06)
        cax.imshow(codes.reshape(-1, 1), aspect="auto", cmap=cmap, interpolation="nearest",
                   vmin=0, vmax=max(1, len(colors) - 1))
        cax.set_xlabel("Cluster", fontsize=max(7.5, style.tick_label_pt - 1))
    else:
        cax = divider.append_axes("top", size="4.5%", pad=0.06)
        cax.imshow(codes.reshape(1, -1), aspect="auto", cmap=cmap, interpolation="nearest",
                   vmin=0, vmax=max(1, len(colors) - 1))
        cax.set_ylabel("Cluster", rotation=0, ha="right", va="center",
                       fontsize=max(7.5, style.tick_label_pt - 1))
    cax.set_xticks([]); cax.set_yticks([])
    cax._colorbar = True
    for spine in cax.spines.values():
        spine.set_visible(False)


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    row_id = get_mapping(spec, "row_id", None)
    axis = str(get_mapping(spec, "cluster", "rows")).lower()
    if axis not in ("rows", "columns"):
        axis = "rows"
    k = int(get_mapping(spec, "k", 3))
    scale = str(get_mapping(spec, "scale", "row_zscore"))
    metric = str(get_mapping(spec, "distance_metric", "euclidean"))
    method = str(get_mapping(spec, "linkage_method", "average"))
    prefix = str(get_mapping(spec, "cluster_prefix", "Cluster"))
    exclude = get_mapping(spec, "exclude_columns", None)
    value_columns = get_mapping(spec, "value_columns", None)
    max_features = int(get_mapping(spec, "max_features", _clust.DEFAULT_MAX_CLUSTER_FEATURES))

    row_labels, value_cols, raw_matrix, warnings = numeric_matrix(
        df, row_id, context=PLOT_TYPE, exclude=exclude, value_columns=value_columns)
    # Memory guard: cap the feature (row) axis before the O(n^2) clustering when
    # clustering rows, so a huge matrix (e.g. 55k genes) can't exhaust RAM.
    if axis == "rows":
        raw_matrix, row_labels, _cap = _clust.cap_rows_by_variance(
            raw_matrix, row_labels, max_features, warnings)
    matrix, scale_warns = _clust.scale_matrix(raw_matrix, scale)
    warnings.extend(scale_warns)
    filled = np.nan_to_num(matrix, nan=0.0)

    # Cluster the chosen axis (this drives assignment + color strip).
    n_objects = raw_matrix.shape[0] if axis == "rows" else raw_matrix.shape[1]
    obj_labels = row_labels if axis == "rows" else list(value_cols)
    try:
        z = _clust.compute_linkage(filled, method=method, metric=metric, axis=axis)
        order = _clust.leaf_order(z)
        cluster_ids = _clust.cut_k(z, k, n_objects)
    except _clust.ClusteringError as exc:
        raise RenderError(f"{PLOT_TYPE}: {exc}") from exc

    # Order the OTHER axis by its own clustering (best-effort, for a clean map).
    other_axis = "columns" if axis == "rows" else "rows"
    n_other = raw_matrix.shape[1] if axis == "rows" else raw_matrix.shape[0]
    other_order = list(range(n_other))
    if n_other > 2:
        try:
            zo = _clust.compute_linkage(filled, method=method,
                                        metric=("euclidean" if method == "ward" else metric),
                                        axis=other_axis)
            other_order = _clust.leaf_order(zo)
        except Exception:
            pass

    if axis == "rows":
        row_order, col_order = order, other_order
    else:
        row_order, col_order = other_order, order

    ordered = matrix[np.ix_(row_order, col_order)]
    ordered_rows = [row_labels[i] for i in row_order]
    ordered_cols = [value_cols[j] for j in col_order]

    color_map = _clust.cluster_color_map(cluster_ids, prefix)
    ordered_labels = sorted(color_map.keys(), key=lambda s: int(s.split()[-1]))
    idx_of = {lab: i for i, lab in enumerate(ordered_labels)}
    colors = [color_map[lab] for lab in ordered_labels]
    codes = np.array([idx_of[f"{prefix} {int(cluster_ids[o])}"] for o in order])

    values_for_table = np.nanmean(raw_matrix, axis=1) if axis == "rows" else None
    table = _clust.assignment_table(
        obj_labels, cluster_ids, order, prefix=prefix,
        id_name=("feature" if axis == "rows" else "sample"),
        values=values_for_table)
    summary = _clust.cluster_summary(cluster_ids, method=method, metric=metric, scale=scale,
                                     k=k, axis=axis, warnings=warnings)

    vmax = np.nanmax(np.abs(matrix)) if np.isfinite(matrix).any() else 1.0
    diverging = scale in ("row_zscore", "column_zscore", "center_rows")
    cmap = style.diverging_cmap if diverging else style.sequential_cmap
    if diverging:
        vmin, vmax = -vmax, vmax
    else:
        vmin = float(np.nanmin(matrix)) if np.isfinite(matrix).any() else 0.0
        vmax = float(np.nanmax(matrix)) if np.isfinite(matrix).any() else 1.0

    w_in, _ = style.figure_size_inches(str((spec.get("layout") or {}).get("column_width", "default")),
                                       aspect=1.0)
    n_r, n_c = len(ordered_rows), len(ordered_cols)
    # Height: when per-row labels are hidden (many features), the rows are dense
    # colour bands, so keep a COMPACT, display-friendly block (a tall strip is
    # unreadable on screen). Only grow tall when row labels are actually shown.
    if n_r > 60:
        h_in = w_in * 1.2                              # compact block; all rows as bands
    elif n_r > 12:
        h_in = min(1.8 + 0.16 * n_r, 12.0)             # room for the visible row labels
    else:
        h_in = w_in * 0.9
    with style.apply():
        fig, ax = plt.subplots(figsize=(w_in, h_in))
        im = ax.imshow(ordered, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax,
                       interpolation="nearest")
        _draw_cluster_strip(ax, "left" if axis == "rows" else "top", codes, colors, style)

        row_fs = style.tick_label_pt if n_r <= 25 else (0.0 if n_r > 60 else max(6.0, style.tick_label_pt - 3))
        col_fs = style.tick_label_pt if n_c <= 25 else (0.0 if n_c > 60 else max(6.0, style.tick_label_pt - 3))
        if row_fs > 0:
            ax.set_yticks(range(n_r)); ax.set_yticklabels(ordered_rows, fontsize=row_fs)
        else:
            ax.set_yticks([])
        if col_fs > 0:
            ax.set_xticks(range(n_c)); ax.set_xticklabels(ordered_cols, rotation=90, fontsize=col_fs)
        else:
            ax.set_xticks([])
        ax.set_xlabel((spec.get("layout") or {}).get("x_label", "Sample"))
        ax.set_ylabel((spec.get("layout") or {}).get("y_label", str(row_id or df.columns[0])))
        title = (spec.get("layout") or {}).get("title")
        if title:
            fig.suptitle(title, fontsize=style.title_font_pt, fontweight="bold")
        cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
        cbar.set_label((spec.get("layout") or {}).get("colorbar_label",
                       "z-score" if diverging else "value"), fontsize=style.axis_font_pt)
        cbar.ax.tick_params(labelsize=style.tick_label_pt)
        # Cluster legend outside.
        from matplotlib.patches import Patch

        handles = [Patch(facecolor=color_map[lab], label=lab) for lab in ordered_labels]
        ax.legend(handles=handles, title=f"{k} clusters", loc="upper left",
                  bbox_to_anchor=(1.16, 1.0), frameon=False,
                  fontsize=max(7.5, style.legend_pt - 1), title_fontsize=max(8.0, style.legend_pt))
        for spine in ax.spines.values():
            spine.set_visible(False)
        fig.tight_layout()

    meta = base_metadata(spec, style, df, used_columns=[row_id or df.columns[0]] + list(value_cols))
    meta["clustered_axis"] = axis
    meta["k"] = k
    meta["scale"] = scale
    meta["distance_metric"] = metric
    meta["linkage_method"] = method
    meta["cluster_summary"] = summary
    meta["cluster_assignment"] = table.to_dict(orient="records")
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
