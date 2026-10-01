"""Regions of interest drawn as polygons over tissue.

Takes a vertex table — one row per polygon vertex, ordered — and draws outlines
with optional fill and labels, over spatial points or a background image.

Import of ROI geometry is the deliberate scope here. There is no freehand
drawing tool: robustly reading a polygon someone else defined is worth more for
reproducibility than an interactive editor that would be hard to make reliable.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D

from make_my_figure_core.plots._spatial_shared import (
    add_scale_bar, apply_crop, coordinate_record, draw_background_image,
    finish_spatial_axes, numeric_coordinates, ordered_levels, spatial_block,
    widen_for_outside_legend,
)
from make_my_figure_core.plots.base import (
    RenderError, RenderResult, base_metadata, figure_size, get_mapping, require_columns,
    resolve_legend_location,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "spatial_roi_map"

MIN_VERTICES = 3


def render(spec: Dict[str, Any], df: pd.DataFrame, style: StyleProfile) -> RenderResult:
    roi = get_mapping(spec, "roi", required=True, context=PLOT_TYPE)
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    order = get_mapping(spec, "vertex_order")
    label_col = get_mapping(spec, "roi_label")
    category = get_mapping(spec, "roi_category")
    require_columns(df, [c for c in (roi, x, y, order, label_col, category) if c],
                    context=PLOT_TYPE)

    block = spatial_block(spec)
    warnings: List[str] = []

    cols = [c for c in (roi, x, y, order, label_col, category) if c]
    data = df[cols].copy()
    numeric_coordinates(data, x, y, context=PLOT_TYPE)

    polys, meta_rows, skipped = [], [], []
    for rid, grp in data.groupby(roi, sort=False):
        g = grp.sort_values(order) if order else grp
        verts = g[[x, y]].to_numpy(dtype=float)
        # A closing vertex repeating the first is common and harmless.
        if len(verts) > 1 and np.allclose(verts[0], verts[-1]):
            verts = verts[:-1]
        if len(verts) < MIN_VERTICES:
            skipped.append({"roi": str(rid), "n_vertices": int(len(verts)),
                            "reason": f"fewer than {MIN_VERTICES} distinct vertices"})
            continue
        polys.append(verts)
        cat = str(g[category].iloc[0]) if category else None
        # Shoelace area, in squared coordinate units.
        area = 0.5 * abs(np.dot(verts[:, 0], np.roll(verts[:, 1], 1))
                         - np.dot(verts[:, 1], np.roll(verts[:, 0], 1)))
        meta_rows.append({"roi": str(rid), "n_vertices": int(len(verts)),
                          "category": cat, "area": float(area),
                          "label": str(g[label_col].iloc[0]) if label_col else str(rid),
                          "centroid": [float(verts[:, 0].mean()), float(verts[:, 1].mean())]})

    if not polys:
        raise RenderError(
            f"{PLOT_TYPE}: no ROI had at least {MIN_VERTICES} vertices. "
            "Check the vertex table and the vertex_order column.")
    if skipped:
        warnings.append(
            f"{len(skipped)} ROI(s) were not drawn because they have fewer than "
            f"{MIN_VERTICES} distinct vertices: "
            + ", ".join(s['roi'] for s in skipped[:5])
            + ("..." if len(skipped) > 5 else "")
            + ". They are listed in the metadata rather than silently ignored.")

    tiny = [m["roi"] for m in meta_rows if m["area"] <= 0]
    if tiny:
        warnings.append(f"{len(tiny)} ROI(s) enclose zero area (degenerate or collinear "
                        f"vertices): {', '.join(tiny[:5])}.")

    cats = ordered_levels(pd.Series([m["category"] for m in meta_rows if m["category"]]),
                          block.get("roi_category_order")) if category else []
    override = block.get("palette")
    cat_colour = {c: (override[i % len(override)] if override else style.color_for(i))
                  for i, c in enumerate(cats)}
    default_edge = block.get("roi_edgecolor", style.text_color)
    edge = [cat_colour.get(m["category"], default_edge) if category else default_edge
            for m in meta_rows]
    fill_alpha = float(block.get("roi_fill_alpha", 0.0))
    lw = float(block.get("roi_linewidth", 1.4))
    w, h = figure_size(spec, style, aspect=0.95)

    show_legend = bool(cats and block.get("legend", True))
    fig_w, legend_rect = (widen_for_outside_legend(w, cats, style, str(category))
                          if show_legend else (w, None))

    with style.apply():
        fig, ax = plt.subplots(figsize=(fig_w, h))
        bg_record = draw_background_image(ax, block)

        pts = block.get("context_points")
        if pts and isinstance(pts, dict) and {"x", "y"} <= set(pts):
            ax.scatter(pts["x"], pts["y"], s=float(pts.get("size", 3.0)),
                       c=pts.get("color", "#cccccc"), alpha=float(pts.get("alpha", 0.7)),
                       linewidths=0.0, edgecolors="none", rasterized=True, zorder=1)

        coll = PolyCollection(polys, facecolors=[
            (*plt.matplotlib.colors.to_rgb(c), fill_alpha) for c in edge]
            if fill_alpha > 0 else "none",
            edgecolors=edge, linewidths=lw, zorder=3)
        ax.add_collection(coll)
        ax.autoscale_view()

        if block.get("roi_labels", True):
            for m in meta_rows:
                ax.annotate(m["label"], xy=m["centroid"], ha="center", va="center",
                            fontsize=style.annotation_pt, color=style.text_color, zorder=4)

        apply_crop(ax, block)
        finish_spatial_axes(ax, block, show_axes=bool(block.get("show_axes", False)))
        bar = add_scale_bar(ax, block, style)
        title = (spec.get("layout", {}) or {}).get("title")
        if title:
            ax.set_title(str(title))

        if show_legend:
            handles = [Line2D([0], [0], color=cat_colour[c], linewidth=lw, label=c)
                       for c in cats]
            fig.tight_layout(rect=legend_rect)
            ax.legend(handles=handles, title=str(category), loc="upper left",
                      bbox_to_anchor=(1.02, 1.0), frameon=style.legend_frameon)
        else:
            fig.tight_layout()

    meta = base_metadata(spec, style, data, used_columns=[roi, x, y, order, label_col, category])
    meta["spatial"] = {
        **coordinate_record(x, y, block),
        "roi_column": roi, "vertex_order_column": order,
        "roi_category_column": category, "roi_categories": cats,
        "n_rois_drawn": len(polys), "n_rois_skipped": len(skipped),
        "skipped_rois": skipped, "rois": meta_rows,
        "roi_fill_alpha": fill_alpha, "roi_linewidth": lw,
        "scale_bar": bar, "background_image": bg_record,
    }
    if bar and not bar.get("drawn"):
        warnings.append(f"Scale bar not drawn: {bar['reason']}.")
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
