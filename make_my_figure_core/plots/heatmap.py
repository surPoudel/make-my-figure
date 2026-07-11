"""Clustered heatmap from a feature-by-sample matrix.

The first (row-id) column holds row labels; all remaining columns are numeric
sample values. Optional hierarchical clustering reorders rows/columns using
SciPy (via :mod:`make_my_figure_core.clustering`, with selectable distance
metric, linkage method, and scaling); if linkage fails we fall back to original
order and record a warning (never fail silently).

v0.5 additions (all optional, backward-compatible — defaults reproduce the
original euclidean/average, unscaled output):
  * ``scale`` (none/row_zscore/column_zscore/center_rows/log)
  * ``distance_metric`` and ``linkage_method``
  * ``cluster_k_rows`` / ``cluster_k_columns`` — cut the tree into k clusters,
    draw a cluster color strip + legend, and export the assignment table
  * ``sort_by_cluster`` — group rows/columns by cluster
  * ``highlight_rows`` / ``highlight_columns`` — bold+label selected features
    even when labels are otherwise hidden (paste a gene list)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core import clustering as _clust
from make_my_figure_core.plots.base import (
    RenderError,
    RenderResult,
    base_metadata,
    get_mapping,
    require_columns,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "heatmap_clustered_matrix"

# Colorblind-aware qualitative palette for annotation categories.
_ANNOT_PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9",
                  "#F0E442", "#999999", "#000000"]


def _order_and_linkage(filled: np.ndarray, axis: str, method: str, metric: str,
                       do_cluster: bool, warnings: List[str]):
    """Return (order, linkage) for one axis; falls back to identity on failure."""
    n = filled.shape[0] if axis == "rows" else filled.shape[1]
    order = list(range(n))
    linkage_z = None
    if do_cluster and n > 2:
        try:
            linkage_z = _clust.compute_linkage(filled, method=method, metric=metric, axis=axis)
            order = _clust.leaf_order(linkage_z)
        except _clust.ClusteringError as exc:
            warnings.append(f"{axis.capitalize()} clustering skipped: {exc}")
        except Exception as exc:  # pragma: no cover - defensive
            warnings.append(f"{axis.capitalize()} clustering skipped: {exc}")
    return order, linkage_z


def _draw_column_annotations(fig, ax, annotations, ordered_cols, style, warnings) -> None:
    """Draw thin categorical color strips above the heatmap (one per track)."""
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    divider = make_axes_locatable(ax)
    n = len(ordered_cols)
    for track in reversed(annotations):  # append from the top down
        label = str(track.get("label", "annotation"))
        values = track.get("values", {}) or {}
        cats = [str(values.get(c, "")) for c in ordered_cols]
        levels = [c for c in dict.fromkeys(cats) if c != ""]
        cmap_idx = {lv: i for i, lv in enumerate(levels)}
        strip = np.full((1, n), np.nan)
        for j, c in enumerate(cats):
            if c in cmap_idx:
                strip[0, j] = cmap_idx[c]
        cax = divider.append_axes("top", size="5%", pad=0.06)
        cax._colorbar = True  # decorative strip: skip the QA missing-label check
        cax.set_xlim(-0.5, n - 0.5)
        from matplotlib.colors import ListedColormap

        colors = [_ANNOT_PALETTE[i % len(_ANNOT_PALETTE)] for i in range(max(1, len(levels)))]
        cmap = ListedColormap(colors)
        cmap.set_bad("#EEEEEE")
        cax.imshow(strip, aspect="auto", cmap=cmap,
                   vmin=-0.5, vmax=max(0.5, len(levels) - 0.5), interpolation="nearest")
        cax.set_yticks([0]); cax.set_yticklabels([label], fontsize=max(7.0, style.tick_label_pt - 1))
        cax.set_xticks([])
        for spine in cax.spines.values():
            spine.set_visible(False)
        from matplotlib.patches import Patch

        handles = [Patch(facecolor=colors[i % len(colors)], label=lv) for i, lv in enumerate(levels)]
        if handles:
            cax.legend(handles=handles, title=label, loc="center left",
                       bbox_to_anchor=(1.005, 0.5), fontsize=max(6.5, style.legend_pt - 2),
                       title_fontsize=max(7.0, style.legend_pt - 1), frameon=False,
                       handlelength=1.0, borderpad=0.2, labelspacing=0.2)


def _draw_cluster_strip(ax, side: str, cluster_ids_in_order: np.ndarray,
                        color_map: Dict[str, str], prefix: str, style, *, legend: bool) -> None:
    """Draw a categorical cluster color strip beside the heatmap (left/top)."""
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    ordered_labels = sorted(color_map.keys(), key=lambda s: int(s.split()[-1]))
    idx_of = {lab: i for i, lab in enumerate(ordered_labels)}
    colors = [color_map[lab] for lab in ordered_labels]
    cmap = ListedColormap(colors)
    codes = np.array([idx_of[f"{prefix} {int(c)}"] for c in cluster_ids_in_order])
    divider = make_axes_locatable(ax)
    if side == "left":
        cax = divider.append_axes("left", size="4%", pad=0.06)
        cax.imshow(codes.reshape(-1, 1), aspect="auto", cmap=cmap, interpolation="nearest")
        cax.set_xticks([]); cax.set_yticks([])
        cax.set_xlabel("Cluster", fontsize=max(7.0, style.tick_label_pt - 1))
    else:  # top
        cax = divider.append_axes("top", size="4%", pad=0.06)
        cax.imshow(codes.reshape(1, -1), aspect="auto", cmap=cmap, interpolation="nearest")
        cax.set_xticks([]); cax.set_yticks([])
        cax.set_ylabel("Cluster", rotation=0, ha="right", va="center",
                       fontsize=max(7.0, style.tick_label_pt - 1))
    cax._colorbar = True
    for spine in cax.spines.values():
        spine.set_visible(False)
    if legend:
        handles = [Patch(facecolor=color_map[lab], label=lab) for lab in ordered_labels]
        ax.legend(handles=handles, title="Clusters", loc="upper left",
                  bbox_to_anchor=(1.14, 1.0), fontsize=max(7.0, style.legend_pt - 1),
                  title_fontsize=max(7.5, style.legend_pt), frameon=False,
                  handlelength=1.0, borderpad=0.3, labelspacing=0.3)


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    import pandas as pd

    row_id = get_mapping(spec, "row_id", None)
    if not row_id:
        row_id = df.columns[0]
    require_columns(df, [row_id], context=PLOT_TYPE)

    cluster_rows = bool(get_mapping(spec, "cluster_rows", True))
    cluster_cols = bool(get_mapping(spec, "cluster_columns", True))
    color_scale = str(get_mapping(spec, "color_scale", "diverging"))
    scale = str(get_mapping(spec, "scale", "none"))
    metric = str(get_mapping(spec, "distance_metric", "euclidean"))
    method = str(get_mapping(spec, "linkage_method", "average"))
    k_rows = get_mapping(spec, "cluster_k_rows", None)
    k_cols = get_mapping(spec, "cluster_k_columns", None)
    sort_by_cluster = bool(get_mapping(spec, "sort_by_cluster", False))
    prefix = str(get_mapping(spec, "cluster_prefix", "Cluster"))
    highlight_rows = {str(s).strip().lower() for s in (get_mapping(spec, "highlight_rows", None) or [])}
    highlight_cols = {str(s).strip().lower() for s in (get_mapping(spec, "highlight_columns", None) or [])}
    show_row_labels = get_mapping(spec, "show_row_labels", None)
    show_col_labels = get_mapping(spec, "show_col_labels", None)

    work = df.copy()
    row_labels = work[row_id].astype(str).tolist()
    value_cols = [c for c in work.columns if c != row_id]
    numeric = work[value_cols].apply(lambda s: pd.to_numeric(s, errors="coerce"))
    if numeric.shape[1] == 0:
        raise RenderError(f"{PLOT_TYPE}: no value columns besides row id '{row_id}'.")

    raw_matrix = numeric.to_numpy(dtype=float)
    warnings: List[str] = []
    if np.isnan(raw_matrix).any():
        warnings.append("Matrix contains missing/non-numeric values; shown as blank cells.")

    # Scaling (default 'none' reproduces the original output).
    matrix, scale_warns = _clust.scale_matrix(raw_matrix, scale)
    warnings.extend(scale_warns)

    col_labels = list(value_cols)
    filled = np.nan_to_num(matrix, nan=0.0)

    row_order, row_linkage = _order_and_linkage(filled, "rows", method, metric, cluster_rows, warnings)
    col_order, col_linkage = _order_and_linkage(filled, "columns", method, metric, cluster_cols, warnings)

    # --- k-cluster cuts (optional) ---
    row_cluster_ids = col_cluster_ids = None
    row_color_map = col_color_map = None
    meta_extra: Dict[str, Any] = {}
    if k_rows and row_linkage is not None:
        try:
            row_cluster_ids = _clust.cut_k(row_linkage, int(k_rows), raw_matrix.shape[0])
            row_color_map = _clust.cluster_color_map(row_cluster_ids, prefix)
            tbl = _clust.assignment_table(row_labels, row_cluster_ids, row_order,
                                          id_name="feature",
                                          values=np.nanmean(raw_matrix, axis=1))
            meta_extra["row_assignment"] = tbl.to_dict(orient="records")
            meta_extra["row_clusters"] = _clust.cluster_summary(
                row_cluster_ids, method=method, metric=metric, scale=scale,
                k=int(k_rows), axis="rows", warnings=[])
        except _clust.ClusteringError as exc:
            warnings.append(f"Row k-clustering skipped: {exc}")
    if k_cols and col_linkage is not None:
        try:
            col_cluster_ids = _clust.cut_k(col_linkage, int(k_cols), raw_matrix.shape[1])
            col_color_map = _clust.cluster_color_map(col_cluster_ids, prefix)
            tbl = _clust.assignment_table(col_labels, col_cluster_ids, col_order,
                                          id_name="sample")
            meta_extra["column_assignment"] = tbl.to_dict(orient="records")
            meta_extra["column_clusters"] = _clust.cluster_summary(
                col_cluster_ids, method=method, metric=metric, scale=scale,
                k=int(k_cols), axis="columns", warnings=[])
        except _clust.ClusteringError as exc:
            warnings.append(f"Column k-clustering skipped: {exc}")

    # Optionally group by cluster (stable within cluster by dendrogram order).
    if sort_by_cluster and row_cluster_ids is not None:
        pos = {leaf: i for i, leaf in enumerate(row_order)}
        row_order = sorted(range(raw_matrix.shape[0]),
                           key=lambda i: (int(row_cluster_ids[i]), pos.get(i, i)))
    if sort_by_cluster and col_cluster_ids is not None:
        pos = {leaf: i for i, leaf in enumerate(col_order)}
        col_order = sorted(range(raw_matrix.shape[1]),
                           key=lambda j: (int(col_cluster_ids[j]), pos.get(j, j)))

    ordered = matrix[np.ix_(row_order, col_order)]
    ordered_rows = [row_labels[i] for i in row_order]
    ordered_cols = [col_labels[j] for j in col_order]

    if color_scale == "diverging":
        cmap = style.diverging_cmap
        vmax = np.nanmax(np.abs(matrix)) if np.isfinite(matrix).any() else 1.0
        vmin, vmax = -vmax, vmax
    else:
        cmap = style.sequential_cmap
        vmin = float(np.nanmin(matrix)) if np.isfinite(matrix).any() else 0.0
        vmax = float(np.nanmax(matrix)) if np.isfinite(matrix).any() else 1.0

    def _label_fs(n: int) -> float:
        if n <= 15:
            return style.tick_label_pt
        if n <= 30:
            return max(7.0, style.tick_label_pt - 1)
        if n <= 60:
            return max(6.0, style.tick_label_pt - 3)
        return 0.0  # hide

    col_fs = _label_fs(len(ordered_cols))
    row_fs = _label_fs(len(ordered_rows))
    # Explicit overrides.
    if show_row_labels is True and row_fs == 0:
        row_fs = max(6.0, style.tick_label_pt - 3)
    if show_row_labels is False:
        row_fs = 0.0
    if show_col_labels is True and col_fs == 0:
        col_fs = max(6.0, style.tick_label_pt - 3)
    if show_col_labels is False:
        col_fs = 0.0
    if len(highlight_rows) > 60:
        warnings.append(f"{len(highlight_rows)} highlighted rows requested; consider fewer for legibility.")

    n_c = len(ordered_cols)
    n_r = len(ordered_rows)
    col_annotations = spec.get("column_annotations") or []

    layout = spec.get("layout", {}) or {}
    width_preset = str(layout.get("column_width", "default")).lower()
    w_in, _ = style.figure_size_inches(width_preset, aspect=1.0)
    if n_c > 14:
        w_in *= min(1.5, 1.0 + 0.02 * (n_c - 14))
    if row_fs > 0 and n_r > 12:
        target_h = 1.6 + 0.16 * n_r
    else:
        target_h = w_in * (0.95 if n_c <= 14 else 1.15)
    target_h += 0.5 * len(col_annotations)
    target_h = max(target_h, w_in * 0.6)
    figsize = (w_in, min(target_h, 22.0))

    with style.apply():
        fig, ax = plt.subplots(figsize=figsize)
        im = ax.imshow(ordered, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax,
                       interpolation="nearest")
        # Cluster color strips (drawn first so their divider axes sit outside).
        if row_color_map is not None:
            _draw_cluster_strip(ax, "left", row_cluster_ids[row_order], row_color_map,
                                prefix, style, legend=True)
        if col_color_map is not None:
            _draw_cluster_strip(ax, "top", col_cluster_ids[col_order], col_color_map,
                                prefix, style, legend=(row_color_map is None))
        if col_annotations:
            _draw_column_annotations(fig, ax, col_annotations, ordered_cols, style, warnings)

        # --- row tick labels (+ highlighting) ---
        hl_row_pos = [i for i, lab in enumerate(ordered_rows) if lab.lower() in highlight_rows]
        if row_fs > 0:
            ax.set_yticks(range(len(ordered_rows)))
            ax.set_yticklabels(ordered_rows, fontsize=row_fs)
            for i in hl_row_pos:
                ax.get_yticklabels()[i].set_fontweight("bold")
                ax.get_yticklabels()[i].set_color("#B2182B")
        elif hl_row_pos:  # labels hidden globally, but show highlighted ones
            ax.set_yticks(hl_row_pos)
            ax.set_yticklabels([ordered_rows[i] for i in hl_row_pos],
                               fontsize=max(7.0, style.tick_label_pt - 2), fontweight="bold",
                               color="#B2182B")
        else:
            ax.set_yticks([])
            if n_r > 60:
                warnings.append(f"{len(ordered_rows)} rows: row labels hidden for legibility.")

        # --- column tick labels (+ highlighting) ---
        hl_col_pos = [j for j, lab in enumerate(ordered_cols) if lab.lower() in highlight_cols]
        if col_fs > 0:
            ax.set_xticks(range(len(ordered_cols)))
            ax.set_xticklabels(ordered_cols, rotation=90, fontsize=col_fs)
            for j in hl_col_pos:
                ax.get_xticklabels()[j].set_fontweight("bold")
                ax.get_xticklabels()[j].set_color("#B2182B")
        elif hl_col_pos:
            ax.set_xticks(hl_col_pos)
            ax.set_xticklabels([ordered_cols[j] for j in hl_col_pos], rotation=90,
                               fontsize=max(7.0, style.tick_label_pt - 2), fontweight="bold",
                               color="#B2182B")
        else:
            ax.set_xticks([])
            if n_c > 60:
                warnings.append(f"{len(ordered_cols)} columns: labels hidden for legibility.")

        ax.set_xlabel(spec.get("layout", {}).get("x_label", "Sample"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", str(row_id)))
        title = spec.get("layout", {}).get("title")
        if title:
            if col_annotations or col_color_map is not None:
                fig.suptitle(title, fontsize=style.title_font_pt, fontweight="bold")
            else:
                ax.set_title(title)
        cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
        cbar.ax.tick_params(labelsize=style.tick_label_pt, width=style.tick_width,
                            length=style.tick_length)
        cbar.outline.set_linewidth(style.spine_width_pt)
        default_cbar = "z-score" if scale in ("row_zscore", "column_zscore") else "value"
        cbar.set_label(spec.get("layout", {}).get("colorbar_label", default_cbar),
                       fontsize=style.axis_font_pt)
        for spine in ax.spines.values():
            spine.set_visible(False)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[row_id] + value_cols)
    meta["matrix_shape"] = [int(raw_matrix.shape[0]), int(raw_matrix.shape[1])]
    meta["clustered_rows"] = cluster_rows and row_order != list(range(raw_matrix.shape[0]))
    meta["clustered_columns"] = cluster_cols and col_order != list(range(raw_matrix.shape[1]))
    meta["color_scale"] = color_scale
    meta["scale"] = scale
    meta["distance_metric"] = metric
    meta["linkage_method"] = method
    meta.update(meta_extra)
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
