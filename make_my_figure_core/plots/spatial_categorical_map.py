"""Cells or spots in tissue coordinates, coloured by a discrete annotation.

Serves cluster maps, cell-type maps, region maps and neighbourhood-assignment
maps. The column changes; the geometry does not. One renderer covers all of them
rather than four near-identical ones.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

from make_my_figure_core.plots._spatial_shared import (
    add_scale_bar, apply_crop, categorical_styles, coordinate_record,
    draw_background_image, facet_grid, finish_spatial_axes, numeric_coordinates,
    ordered_levels, resolve_marker_size, share_facet_limits, should_rasterize,
    spatial_block, widen_for_outside_legend,
)
from make_my_figure_core.plots.base import (
    resolve_figure_size,
    RenderResult, base_metadata, figure_size, get_mapping, require_columns,
    resolve_legend_location,
    requested_width
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "spatial_categorical_map"


def render(spec: Dict[str, Any], df: pd.DataFrame, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    category = get_mapping(spec, "category", required=True, context=PLOT_TYPE)
    facet = get_mapping(spec, "facet")
    require_columns(df, [x, y, category] + ([facet] if facet else []), context=PLOT_TYPE)

    block = spatial_block(spec)
    warnings: List[str] = []

    cols = [x, y, category] + ([facet] if facet else [])
    data = df[cols].copy()
    numeric_coordinates(data, x, y, context=PLOT_TYPE)

    missing_label = str(block.get("missing_category_label", "Unassigned"))
    missing_colour = block.get("missing_color", "#d9d9d9")
    n_missing = int(data[category].isna().sum())
    if n_missing:
        data[category] = data[category].astype(object).where(data[category].notna(), missing_label)
        warnings.append(
            f"{n_missing} cell(s) have no {category!r} value; they are drawn as "
            f"{missing_label!r} in {missing_colour} rather than hidden.")

    cat_str = data[category].astype(str)
    levels = ordered_levels(cat_str, block.get("category_order"))
    if n_missing and missing_label in levels:
        levels = [lv for lv in levels if lv != missing_label] + [missing_label]

    override = block.get("palette")
    colours, markers, palette_warning = categorical_styles(
        levels, style, palette=override, base_marker=str(block.get("marker", "o")))
    if n_missing and missing_label in colours:
        colours[missing_label] = missing_colour
    if palette_warning:
        warnings.append(palette_warning)

    facet_levels = ordered_levels(data[facet].astype(str), block.get("facet_order")) \
        if facet else [None]
    nrows, ncols = facet_grid(len(facet_levels), block.get("facet_columns"))
    w, h = figure_size(spec, style, aspect=0.95)

    # A pinned spatial.marker_size is scaled by the global point size rather than
    # replaced by it, so both controls stay live - see resolve_marker_size.
    size = resolve_marker_size(block, auto=style.marker_size, style_size=style.marker_size)
    alpha = float(block.get("alpha", style.marker_alpha))
    edge = block.get("marker_edgecolor")
    raster = should_rasterize(len(data), block)

    show_legend = bool(block.get("legend", True))
    fig_w = w * ncols
    legend_rect = None
    if show_legend:
        fig_w, legend_rect = widen_for_outside_legend(
            w * ncols, levels, style, str(category), limit=requested_width(spec))

    with style.apply():
        fig, axes = plt.subplots(nrows, ncols,
                                 figsize=resolve_figure_size(spec, (fig_w, h * nrows)),
                                 squeeze=False)
        bg_record = None
        used_axes = []
        for idx, fv in enumerate(facet_levels):
            ax = axes[idx // ncols][idx % ncols]
            sub = data if fv is None else data[data[facet].astype(str) == fv]
            bg_record = draw_background_image(ax, block) or bg_record
            for lv in levels:
                part = sub[sub[category].astype(str) == lv]
                if part.empty:
                    continue
                ax.scatter(part[x], part[y], s=size, c=[colours[lv]],
                           alpha=alpha, marker=markers[lv],
                           linewidths=(style.marker_edge_width * 0.6) if edge else 0.0,
                           edgecolors=edge if edge else "none",
                           rasterized=raster, zorder=2)
            apply_crop(ax, block)
            finish_spatial_axes(ax, block, show_axes=bool(block.get("show_axes", False)),
                                x_label=x, y_label=y)
            if fv is not None:
                ax.set_title(str(fv), fontsize=style.axis_font_pt)
            used_axes.append(ax)

        for k in range(len(facet_levels), nrows * ncols):
            axes[k // ncols][k % ncols].set_visible(False)

        title = (spec.get("layout", {}) or {}).get("title")
        if title:
            # suptitle follows rcParams["figure.titlesize"], not axes.titlesize,
            # so the style's title size has to be passed explicitly or the figure
            # silently ignores the typography preset.
            if len(facet_levels) > 1:
                fig.suptitle(str(title), fontsize=style.title_font_pt)
            else:
                axes[0][0].set_title(str(title))

        shared = share_facet_limits(used_axes, block)
        # One bar per facet: each panel auto-scales its own limits, so a single
        # bar would be read against facets it does not describe.
        bars = [add_scale_bar(ax, block, style) for ax in used_axes]
        bar = bars[0] if bars else None

        if show_legend:
            handles = [Line2D([0], [0], marker=markers[lv], linestyle="none", markersize=7,
                              markerfacecolor=colours[lv], markeredgecolor="white", label=lv)
                       for lv in levels]
            # Always outside the tissue. A legend placed "best" lands on the
            # cells, which are the part of the figure the reader came for.
            fig.tight_layout(rect=legend_rect)
            axes[0][ncols - 1].legend(
                handles=handles, title=str(category), loc="upper left",
                bbox_to_anchor=(1.02, 1.0), frameon=style.legend_frameon,
                ncol=max(1, int(block.get("legend_columns", 1))))
        else:
            fig.tight_layout()

    meta = base_metadata(spec, style, data, used_columns=[x, y, category, facet])
    meta["spatial"] = {
        **coordinate_record(x, y, block),
        "category_column": category, "categories": levels,
        "n_cells": int(len(data)), "facet_column": facet,
        "facets": [f for f in facet_levels if f is not None],
        "rasterized_marks": bool(raster), "missing_category_count": n_missing,
        "scale_bar": bar, "scale_bar_per_facet": len([b for b in bars if b]),
        "shared_facet_limits": bool(shared), "background_image": bg_record,
    }
    if bar and not bar.get("drawn"):
        warnings.append(f"Scale bar not drawn: {bar['reason']}.")
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
