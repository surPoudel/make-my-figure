"""Clustered heatmap from a feature-by-sample matrix.

The first (row-id) column holds row labels; all remaining columns are numeric
sample values. Optional hierarchical clustering reorders rows/columns using
SciPy; if SciPy linkage fails for any reason we fall back to original order
and record a warning (never fail silently).
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots.base import (
    RenderError,
    RenderResult,
    base_metadata,
    figure_size,
    get_mapping,
    require_columns,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "heatmap_clustered_matrix"


def _leaf_order(matrix: np.ndarray) -> List[int]:
    """Return a hierarchical-clustering leaf order for the matrix rows."""
    from scipy.cluster.hierarchy import leaves_list, linkage

    # correlation distance is undefined for zero-variance rows; guard with euclidean fallback
    z = linkage(matrix, method="average", metric="euclidean")
    return list(leaves_list(z))


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    row_id = get_mapping(spec, "row_id", None)
    if not row_id:
        row_id = df.columns[0]
    require_columns(df, [row_id], context=PLOT_TYPE)

    cluster_rows = bool(get_mapping(spec, "cluster_rows", True))
    cluster_cols = bool(get_mapping(spec, "cluster_columns", True))
    color_scale = str(get_mapping(spec, "color_scale", "diverging"))

    work = df.copy()
    row_labels = work[row_id].astype(str).tolist()
    value_cols = [c for c in work.columns if c != row_id]
    numeric = work[value_cols].apply(lambda s: __import__("pandas").to_numeric(s, errors="coerce"))
    if numeric.shape[1] == 0:
        raise RenderError(f"{PLOT_TYPE}: no value columns besides row id '{row_id}'.")

    matrix = numeric.to_numpy(dtype=float)
    warnings: List[str] = []
    if np.isnan(matrix).any():
        warnings.append("Matrix contains missing/non-numeric values; shown as blank cells.")

    col_labels = list(value_cols)
    row_order = list(range(matrix.shape[0]))
    col_order = list(range(matrix.shape[1]))

    filled = np.nan_to_num(matrix, nan=0.0)
    if cluster_rows and matrix.shape[0] > 2:
        try:
            row_order = _leaf_order(filled)
        except Exception as exc:  # pragma: no cover - defensive
            warnings.append(f"Row clustering skipped: {exc}")
    if cluster_cols and matrix.shape[1] > 2:
        try:
            col_order = _leaf_order(filled.T)
        except Exception as exc:  # pragma: no cover - defensive
            warnings.append(f"Column clustering skipped: {exc}")

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

    # Auto-scale label font to matrix size so labels stay readable but not huge.
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
    # Wider figure for many columns so labels don't crowd.
    n_c = len(ordered_cols)
    aspect = 0.95 if n_c <= 14 else min(1.4, 0.95 + 0.02 * (n_c - 14))

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=aspect))
        im = ax.imshow(ordered, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax,
                       interpolation="nearest")
        if col_fs > 0:
            ax.set_xticks(range(len(ordered_cols)))
            ax.set_xticklabels(ordered_cols, rotation=90, fontsize=col_fs)
        else:
            ax.set_xticks([])
            warnings.append(f"{len(ordered_cols)} columns: labels hidden for legibility.")
        if row_fs > 0:
            ax.set_yticks(range(len(ordered_rows)))
            ax.set_yticklabels(ordered_rows, fontsize=row_fs)
        else:
            ax.set_yticks([])
            warnings.append(f"{len(ordered_rows)} rows: row labels hidden for legibility.")
        ax.set_xlabel(spec.get("layout", {}).get("x_label", "Sample"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", str(row_id)))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
        cbar.ax.tick_params(labelsize=style.tick_label_pt, width=style.tick_width,
                            length=style.tick_length)
        cbar.outline.set_linewidth(style.spine_width_pt)
        cbar.set_label(spec.get("layout", {}).get("colorbar_label", "z-score"),
                       fontsize=style.axis_font_pt)
        for spine in ax.spines.values():
            spine.set_visible(False)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[row_id] + value_cols)
    meta["matrix_shape"] = [int(matrix.shape[0]), int(matrix.shape[1])]
    meta["clustered_rows"] = cluster_rows and row_order != list(range(matrix.shape[0]))
    meta["clustered_columns"] = cluster_cols and col_order != list(range(matrix.shape[1]))
    meta["color_scale"] = color_scale
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
