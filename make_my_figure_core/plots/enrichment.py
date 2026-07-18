"""Enrichment dot plot: term vs ratio, point size = count, color = -log10(FDR)."""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots.base import (
    RenderResult,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    require_columns,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "enrichment_dotplot"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    y = get_mapping(spec, "y", "term")
    x = get_mapping(spec, "x", "gene_ratio")
    size_col = get_mapping(spec, "size", "gene_count")
    color_col = get_mapping(spec, "color", "neg_log10_fdr")
    fdr_col = get_mapping(spec, "fdr", "fdr")
    top_n = int(get_mapping(spec, "top_n", 20))

    require_columns(df, [y, x], context=PLOT_TYPE)
    work = df.copy()
    work[x] = coerce_numeric(work, x, context=PLOT_TYPE)

    warnings: List[str] = []
    # Derive -log10(FDR) color if absent.
    if color_col not in work.columns or work[color_col].isna().all():
        if fdr_col in work.columns:
            fdr = coerce_numeric(work, fdr_col, context=PLOT_TYPE).clip(lower=1e-300)
            work = work.assign(_color=-np.log10(fdr))
            color_col = "_color"
            warnings.append("Derived color from -log10(FDR).")
        else:
            work = work.assign(_color=work[x])
            color_col = "_color"
    else:
        work[color_col] = coerce_numeric(work, color_col, context=PLOT_TYPE)

    if size_col in work.columns:
        sizes_raw = coerce_numeric(work, size_col, context=PLOT_TYPE).to_numpy(dtype=float)
    else:
        sizes_raw = np.full(len(work), np.nan)
        size_col = None

    # Sort by x descending and keep the top N terms.
    work = work.assign(_sizes=sizes_raw)
    work = work.sort_values(x, ascending=False).head(top_n)
    work = work.iloc[::-1]  # so largest plots at top

    terms = work[y].astype(str).tolist()
    positions = np.arange(len(terms))

    sizes = work["_sizes"].to_numpy(dtype=float)
    if np.isnan(sizes).all():
        marker_sizes = np.full(len(work), 60.0)
    else:
        smin, smax = np.nanmin(sizes), np.nanmax(sizes)
        span = (smax - smin) or 1.0
        marker_sizes = 30 + 170 * (np.nan_to_num(sizes, nan=smin) - smin) / span

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.9))
        sc = ax.scatter(work[x], positions, s=marker_sizes, c=work[color_col],
                        cmap=style.sequential_cmap, edgecolors="black",
                        linewidths=style.spine_width_pt, zorder=3)
        ax.set_yticks(positions)
        ax.set_yticklabels(terms)
        ax.set_xlabel(spec.get("layout", {}).get("x_label", x))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", ""))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        ax.grid(axis="x", linestyle=":", linewidth=style.spine_width_pt, alpha=0.5)
        _cb_loc = str(get_mapping(spec, "colorbar_location", "right")).lower()
        if _cb_loc not in ("right", "left", "top", "bottom"):
            _cb_loc = "right"
        cbar = fig.colorbar(sc, ax=ax, location=_cb_loc,
                            fraction=float(get_mapping(spec, "colorbar_fraction", 0.046) or 0.046),
                            pad=float(get_mapping(spec, "colorbar_pad", 0.04) or 0.04),
                            shrink=float(get_mapping(spec, "colorbar_shrink", 1.0) or 1.0))
        cbar.set_label("-log10(FDR)", fontsize=style.axis_font_pt)
        cbar.ax.tick_params(labelsize=style.axis_font_pt)

        # Size legend (only when we have a size column).
        if size_col is not None and not np.isnan(sizes).all():
            for q in (0.25, 0.5, 1.0):
                ax.scatter([], [], s=30 + 170 * q, c="grey", edgecolors="black",
                           linewidths=style.spine_width_pt,
                           label=f"{int(smin + q * span)}")
            # Size key BELOW the plot (horizontal) so it clears both the data and
            # the right-hand colorbar.
            ax.legend(title=str(size_col), frameon=False, loc="upper center",
                      bbox_to_anchor=(0.5, -0.16), ncol=3, labelspacing=0.6,
                      borderpad=0.6, columnspacing=1.6, handletextpad=0.5,
                      fontsize=style.legend_pt, title_fontsize=style.legend_title_pt)
        style_axes(ax, style)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[y, x, size_col, color_col])
    meta["n_terms"] = int(len(terms))
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
