"""Individual transcript detections in tissue coordinates, coloured by gene.

Xenium-style data: one row per detected transcript, not per cell. Point counts
run to millions, so this renderer is built around two commitments — nothing is
subsampled unless the spec asks for it (and then it is recorded), and dense
marks are rasterised inside vector output so a PDF stays openable.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

from make_my_figure_core.plots._spatial_shared import (
    add_scale_bar, apply_crop, coordinate_record, draw_background_image,
    finish_spatial_axes, numeric_coordinates, ordered_levels, resolve_marker_size,
    spatial_block, widen_for_outside_legend,
)
from make_my_figure_core.plots.base import (
    resolve_figure_size,
    RenderError, RenderResult, base_metadata, figure_size, get_mapping, require_columns,
    resolve_legend_location,
    requested_width
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "spatial_transcript_map"


def render(spec: Dict[str, Any], df: pd.DataFrame, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    gene = get_mapping(spec, "gene", required=True, context=PLOT_TYPE)
    quality = get_mapping(spec, "quality")
    require_columns(df, [c for c in (x, y, gene, quality) if c], context=PLOT_TYPE)

    block = spatial_block(spec)
    warnings: List[str] = []
    n_input = len(df)

    data = df[[c for c in (x, y, gene, quality) if c]].copy()
    numeric_coordinates(data, x, y, context=PLOT_TYPE)

    # --- explicit filtering, each step counted -------------------------------
    filters: List[Dict[str, Any]] = []
    genes_wanted = block.get("genes")
    if genes_wanted:
        before = len(data)
        data = data[data[gene].astype(str).isin([str(g) for g in genes_wanted])]
        filters.append({"filter": "genes", "kept": [str(g) for g in genes_wanted],
                        "rows_before": before, "rows_after": int(len(data))})
        if data.empty:
            raise RenderError(f"{PLOT_TYPE}: none of the requested genes {genes_wanted} "
                              f"are present in {gene!r}.")
    if quality is not None and block.get("min_quality") is not None:
        thr = float(block["min_quality"])
        before = len(data)
        qv = pd.to_numeric(data[quality], errors="coerce")
        data = data[qv >= thr]
        filters.append({"filter": "min_quality", "column": quality, "threshold": thr,
                        "rows_before": before, "rows_after": int(len(data))})
        warnings.append(f"Quality filter {quality!r} >= {thr:g} removed "
                        f"{before - len(data)} of {before} transcripts.")

    # --- subsampling is opt-in only -----------------------------------------
    max_points = block.get("max_points")
    subsample = None
    if max_points is not None and len(data) > int(max_points):
        seed = int(block.get("subsample_seed", 0))
        kept = int(max_points)
        data = data.sample(n=kept, random_state=seed).sort_index()
        subsample = {"requested_max_points": kept, "seed": seed,
                     "rows_before": n_input, "rows_after": int(len(data))}
        warnings.append(
            f"Subsampled to {kept} of {n_input} transcripts because spatial.max_points was "
            f"set (seed {seed}). This is a user-requested operation and is recorded in the "
            "provenance; it is never applied on its own.")
    elif len(data) > 2_000_000:
        warnings.append(
            f"{len(data):,} transcripts are being drawn without subsampling. Rendering and "
            "export will be slow; set spatial.max_points if you want an explicit, recorded "
            "subsample.")

    levels = ordered_levels(data[gene].astype(str), block.get("gene_order"))
    override = block.get("palette") or block.get("gene_colors")
    colours = {g: (override[i % len(override)] if override else style.color_for(i))
               for i, g in enumerate(levels)}

    # Transcripts are drawn far smaller than cells, so the automatic size is a
    # fraction of the global point size; a size the spec pins is scaled by that
    # same control rather than replaced - see resolve_marker_size.
    size = resolve_marker_size(block, auto=max(1.0, style.marker_size * 0.25),
                               style_size=style.marker_size)
    alpha = float(block.get("alpha", 0.75))
    # Transcript maps are dense by nature; rasterise unless told otherwise.
    raster = bool(block.get("rasterize", True))
    w, h = figure_size(spec, style, aspect=0.95)

    show_legend = bool(block.get("legend", True) and levels)
    fig_w, legend_rect = (widen_for_outside_legend(w, levels, style, str(gene),
                                                   limit=requested_width(spec))
                          if show_legend else (w, None))

    with style.apply():
        fig, ax = plt.subplots(figsize=resolve_figure_size(spec, (fig_w, h)))
        bg_record = draw_background_image(ax, block)

        ctx = block.get("context_points")     # optional cell/background layer
        if ctx and isinstance(ctx, dict) and {"x", "y"} <= set(ctx):
            ax.scatter(ctx["x"], ctx["y"], s=float(ctx.get("size", 2.0)),
                       c=ctx.get("color", "#dddddd"), alpha=float(ctx.get("alpha", 0.6)),
                       linewidths=0.0, edgecolors="none", rasterized=True, zorder=1)

        # Deterministic draw order: genes in declared order, rows in table order.
        for g in levels:
            part = data[data[gene].astype(str) == g]
            if part.empty:
                continue
            ax.scatter(part[x], part[y], s=size, c=[colours[g]], alpha=alpha,
                       linewidths=0.0, edgecolors="none", marker=".",
                       rasterized=raster, zorder=2)

        apply_crop(ax, block)
        finish_spatial_axes(ax, block, show_axes=bool(block.get("show_axes", False)),
                            x_label=x, y_label=y)
        bar = add_scale_bar(ax, block, style)
        title = (spec.get("layout", {}) or {}).get("title")
        if title:
            ax.set_title(str(title))

        if show_legend:
            handles = [Line2D([0], [0], marker="o", linestyle="none", markersize=6,
                              markerfacecolor=colours[g], markeredgecolor="none", label=g)
                       for g in levels]
            fig.tight_layout(rect=legend_rect)
            ax.legend(handles=handles, title=str(gene), loc="upper left",
                      bbox_to_anchor=(1.02, 1.0), frameon=style.legend_frameon,
                      ncol=max(1, int(block.get("legend_columns", 1))))
        else:
            fig.tight_layout()

    meta = base_metadata(spec, style, data, used_columns=[x, y, gene, quality])
    meta["spatial"] = {
        **coordinate_record(x, y, block),
        "gene_column": gene, "genes": levels,
        "n_transcripts_input": int(n_input), "n_transcripts_drawn": int(len(data)),
        "filters": filters, "subsample": subsample,
        "quality_column": quality, "rasterized_marks": bool(raster),
        "scale_bar": bar, "background_image": bg_record,
    }
    if bar and not bar.get("drawn"):
        warnings.append(f"Scale bar not drawn: {bar['reason']}.")
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
