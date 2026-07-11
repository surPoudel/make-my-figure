"""UMAP / t-SNE embedding scatter from precomputed coordinates.

For v0.4, upload precomputed UMAP/t-SNE coordinates as a table (one row per
cell/sample, with the 2D coordinates as columns). Direct ``.h5ad``/AnnData
support is planned for a future version.

The point color can be a categorical metadata column (cluster / cell type /
group → discrete palette + legend) or a continuous column (→ sequential
colormap + colorbar). An optional shape column varies the marker, and an
optional label column annotates each category centroid.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from make_my_figure_core.plots._v04_shared import ordered_unique, pick_column
from make_my_figure_core.plots.base import (
    RenderResult,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    place_legend,
    require_columns,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "embedding_scatter"

_X_ALIASES = ["UMAP_1", "UMAP1", "umap_1", "tSNE_1", "TSNE_1", "tsne1", "X_umap1",
              "dim1", "dim_1", "component_1", "PC1"]
_Y_ALIASES = ["UMAP_2", "UMAP2", "umap_2", "tSNE_2", "TSNE_2", "tsne2", "X_umap2",
              "dim2", "dim_2", "component_2", "PC2"]
_MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*", "<", ">"]


def _is_continuous(series: pd.Series) -> bool:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().mean() < 0.9:
        return False
    return numeric.nunique(dropna=True) > 12


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", None) or pick_column(df, _X_ALIASES)
    y = get_mapping(spec, "y", None) or pick_column(df, _Y_ALIASES)
    if not x or not y:
        from make_my_figure_core.plots.base import RenderError

        raise RenderError(
            f"{PLOT_TYPE}: could not find embedding coordinate columns. Provide 'x' and 'y' "
            f"(e.g. UMAP_1/UMAP_2 or tSNE_1/tSNE_2). Available: {list(df.columns)}")
    color_by = get_mapping(spec, "color", None)
    shape_by = get_mapping(spec, "shape", None)
    label_by = get_mapping(spec, "label", None)

    require_columns(df, [x, y], context=PLOT_TYPE)
    work = df.copy()
    work[x] = coerce_numeric(work, x, context=PLOT_TYPE)
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)

    has_color = bool(color_by and color_by in work.columns)
    has_shape = bool(shape_by and shape_by in work.columns)
    continuous = has_color and _is_continuous(work[color_by])
    color_mode = "continuous" if continuous else ("categorical" if has_color else "none")
    warnings: List[str] = []

    mk = dict(s=style.marker_size, edgecolors="white",
              linewidths=style.marker_edge_width * 0.6, alpha=style.marker_alpha)

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.9))
        shape_levels = ordered_unique(work[shape_by].tolist()) if has_shape else [None]

        if continuous:
            cvals = pd.to_numeric(work[color_by], errors="coerce").to_numpy(float)
            for si, sh in enumerate(shape_levels):
                sel = (work[shape_by].astype(str) == str(sh)).to_numpy() if has_shape else np.ones(len(work), bool)
                sc = ax.scatter(work[x][sel], work[y][sel], c=cvals[sel], cmap=style.sequential_cmap,
                                marker=_MARKERS[si % len(_MARKERS)], zorder=3, **mk)
            cbar = fig.colorbar(sc, ax=ax, fraction=0.045, pad=0.03)
            cbar.set_label(str(color_by), fontsize=style.axis_font_pt)
            cbar.ax.tick_params(labelsize=style.tick_label_pt)
        else:
            color_levels = ordered_unique(work[color_by].tolist()) if has_color else [None]
            for ci, lvl in enumerate(color_levels):
                csel = (work[color_by].astype(str) == str(lvl)).to_numpy() if has_color else np.ones(len(work), bool)
                col = style.color_for(ci) if has_color else style.color_for(0)
                for si, sh in enumerate(shape_levels):
                    ssel = (work[shape_by].astype(str) == str(sh)).to_numpy() if has_shape else np.ones(len(work), bool)
                    sel = csel & ssel
                    if not sel.any():
                        continue
                    lab = str(lvl) if (has_color and si == 0) else None
                    ax.scatter(work[x][sel], work[y][sel], color=col,
                               marker=_MARKERS[si % len(_MARKERS)], label=lab, zorder=3, **mk)

        # Annotate category centroids when a label column is supplied.
        if label_by and label_by in work.columns:
            for lvl in ordered_unique(work[label_by].tolist()):
                sub = work[work[label_by].astype(str) == str(lvl)]
                if len(sub):
                    ax.annotate(str(lvl), (sub[x].mean(), sub[y].mean()),
                                fontsize=style.annotation_pt, fontweight="bold",
                                ha="center", va="center",
                                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7))

        ax.set_xlabel(spec.get("layout", {}).get("x_label", str(x)))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", str(y)))
        ax.set_aspect("equal", adjustable="box")
        ax.margins(0.05)
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)

        from matplotlib.lines import Line2D

        def _shape_handles():
            return [Line2D([0], [0], marker=_MARKERS[i % len(_MARKERS)], linestyle="none",
                           markerfacecolor=style.text_color, markeredgecolor="white",
                           markersize=7, label=str(sh)) for i, sh in enumerate(shape_levels)]

        if color_mode == "categorical" and has_shape:
            # Two stacked legends in the reserved right margin (color, then shape).
            color_levels = ordered_unique(work[color_by].tolist())
            color_handles = [Line2D([0], [0], marker="o", linestyle="none",
                                    markerfacecolor=style.color_for(i), markeredgecolor="white",
                                    markersize=7, label=str(lvl))
                             for i, lvl in enumerate(color_levels)]
            leg1 = ax.legend(handles=color_handles, title=str(color_by), loc="upper left",
                             bbox_to_anchor=(1.02, 1.0), frameon=style.legend_frameon)
            ax.add_artist(leg1)
            ax.legend(handles=_shape_handles(), title=str(shape_by), loc="upper left",
                      bbox_to_anchor=(1.02, 0.45), frameon=style.legend_frameon)
            fig.subplots_adjust(right=0.72)
        elif color_mode == "categorical":
            place_legend(ax, style, title=str(color_by), force_outside=True)
        elif has_shape:
            place_legend(ax, style, title=str(shape_by), handles=_shape_handles(),
                         labels=[str(s) for s in shape_levels], force_outside=True)
        else:
            fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[x, y, color_by, shape_by, label_by])
    meta["n_points"] = int(len(work))
    meta["color_mode"] = color_mode
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
