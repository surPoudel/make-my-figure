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


# Colorblind-aware qualitative palette for annotation categories.
_ANNOT_PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9",
                  "#F0E442", "#999999", "#000000"]


def _draw_column_annotations(fig, ax, annotations, ordered_cols, style, warnings) -> None:
    """Draw thin categorical color strips above the heatmap (one per track).

    Each track colors samples by a metadata category and adds a compact legend.
    Missing samples are drawn as light grey.
    """
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
        # No sharex: a shared x-axis would bleed the main heatmap's rotated
        # sample labels onto the strip. imshow extents already align the columns.
        cax = divider.append_axes("top", size="5%", pad=0.06)
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
        # Legend handles for this track (kept small).
        from matplotlib.patches import Patch

        handles = [Patch(facecolor=colors[i % len(colors)], label=lv) for i, lv in enumerate(levels)]
        if handles:
            cax.legend(handles=handles, title=label, loc="center left",
                       bbox_to_anchor=(1.005, 0.5), fontsize=max(6.5, style.legend_pt - 2),
                       title_fontsize=max(7.0, style.legend_pt - 1), frameon=False,
                       handlelength=1.0, borderpad=0.2, labelspacing=0.2)


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
    n_c = len(ordered_cols)
    n_r = len(ordered_rows)

    # Optional sample (column) annotation strips, e.g. condition/batch bars.
    # spec['column_annotations'] = [{"label": str, "values": {sample: category}}]
    col_annotations = spec.get("column_annotations") or []

    # Figure size: width grows with columns; height grows with the number of
    # rows when row labels are shown, so gene labels stay legible and unclipped.
    layout = spec.get("layout", {}) or {}
    width_preset = str(layout.get("column_width", "default")).lower()
    w_in, _ = style.figure_size_inches(width_preset, aspect=1.0)
    if n_c > 14:
        w_in *= min(1.5, 1.0 + 0.02 * (n_c - 14))
    if row_fs > 0 and n_r > 12:
        target_h = 1.6 + 0.16 * n_r          # ~0.16 in per labeled row + margins
    else:
        target_h = w_in * (0.95 if n_c <= 14 else 1.15)
    target_h += 0.5 * len(col_annotations)   # room for annotation strips
    target_h = max(target_h, w_in * 0.6)
    figsize = (w_in, min(target_h, 22.0))

    with style.apply():
        fig, ax = plt.subplots(figsize=figsize)
        im = ax.imshow(ordered, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax,
                       interpolation="nearest")
        if col_annotations:
            _draw_column_annotations(fig, ax, col_annotations, ordered_cols, style, warnings)
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
            # With annotation strips stacked above ax, a normal ax title would
            # collide with them; use a figure-level suptitle instead.
            if col_annotations:
                fig.suptitle(title, fontsize=style.title_font_pt, fontweight="bold")
            else:
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
