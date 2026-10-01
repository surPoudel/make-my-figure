"""Cell-type composition drawn as pie/donut glyphs at spot positions.

The Janesick Fig. 5i idea: each Visium spot carries a mixture of cell types, so
the spot is drawn as a small pie rather than a single colour. Input is a long
table — one row per (spot, category) with a count or fraction, plus the spot's
coordinates.

Normalisation is explicit. Counts are converted to fractions only when the spec
says ``normalize="fraction"``; fractions that do not sum to one are reported
rather than quietly rescaled, because a spot summing to 0.6 usually means a
missing category, not a rounding error.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Wedge

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

PLOT_TYPE = "spatial_composition_map"

_SUM_TOLERANCE = 0.02


def render(spec: Dict[str, Any], df: pd.DataFrame, style: StyleProfile) -> RenderResult:
    spot = get_mapping(spec, "spot", required=True, context=PLOT_TYPE)
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    category = get_mapping(spec, "category", required=True, context=PLOT_TYPE)
    value = get_mapping(spec, "value", required=True, context=PLOT_TYPE)
    require_columns(df, [spot, x, y, category, value], context=PLOT_TYPE)

    block = spatial_block(spec)
    warnings: List[str] = []

    data = df[[spot, x, y, category, value]].copy()
    numeric_coordinates(data, x, y, context=PLOT_TYPE)
    data[value] = pd.to_numeric(data[value], errors="coerce")
    if data[value].isna().any():
        raise RenderError(f"{PLOT_TYPE}: {int(data[value].isna().sum())} row(s) have a "
                          f"non-numeric {value!r}. Composition cannot be inferred from them.")
    if (data[value] < 0).any():
        raise RenderError(f"{PLOT_TYPE}: {int((data[value] < 0).sum())} row(s) have a "
                          f"negative {value!r}. A negative composition is not meaningful.")

    normalize = str(block.get("normalize", "fraction"))
    if normalize not in ("fraction", "as_given"):
        raise RenderError(f"{PLOT_TYPE}: spatial.normalize must be 'fraction' or "
                          f"'as_given', got {normalize!r}.")

    totals = data.groupby(spot)[value].sum()
    if normalize == "fraction":
        data["_f"] = data[value] / data[spot].map(totals)
        empty = totals[totals <= 0]
        if len(empty):
            warnings.append(f"{len(empty)} spot(s) have a total of zero and are not drawn.")
    else:
        data["_f"] = data[value]
        off = totals[(totals - 1.0).abs() > _SUM_TOLERANCE]
        if len(off):
            warnings.append(
                f"{len(off)} spot(s) have fractions summing to something other than 1 "
                f"(range {off.min():.3f}-{off.max():.3f}). With normalize='as_given' they "
                "are drawn as provided and not rescaled — a short sum usually means a "
                "missing category.")

    levels_all = ordered_levels(data[category].astype(str), block.get("category_order"))

    # top-K + Other, and a minimum-fraction threshold, both explicit
    top_k = block.get("top_k")
    min_fraction = block.get("min_fraction")
    other_label = str(block.get("other_label", "Other"))
    collapsed = []
    if top_k or min_fraction:
        weight = data.groupby(data[category].astype(str))["_f"].sum().sort_values(ascending=False)
        keep = set(weight.index)
        if top_k:
            keep &= set(weight.head(int(top_k)).index)
        if min_fraction is not None:
            share = weight / weight.sum()
            keep &= set(share[share >= float(min_fraction)].index)
        collapsed = [c for c in weight.index if c not in keep]
        if collapsed:
            data[category] = data[category].astype(str).where(
                data[category].astype(str).isin(keep), other_label)
            data = data.groupby([spot, x, y, category], as_index=False)["_f"].sum()
            warnings.append(f"{len(collapsed)} categor(ies) below the requested threshold "
                            f"were merged into {other_label!r}: {', '.join(collapsed[:6])}"
                            + ("..." if len(collapsed) > 6 else ""))

    levels = ordered_levels(data[category].astype(str), block.get("category_order"))
    if other_label in levels:
        levels = [c for c in levels if c != other_label] + [other_label]
    override = block.get("palette")
    colours = {c: (block.get("other_color", "#bdbdbd") if c == other_label and collapsed
                   else (override[i % len(override)] if override else style.color_for(i)))
               for i, c in enumerate(levels)}

    spots = data.groupby(spot).agg(**{"_x": (x, "first"), "_y": (y, "first")})
    # Size the glyphs from the actual spacing between spots rather than from the
    # overall span: a fraction of the nearest-neighbour distance leaves the pies
    # separated on any layout, regular grid or not.
    if block.get("glyph_radius") is not None:
        radius = float(block["glyph_radius"])
    else:
        pts = spots[["_x", "_y"]].to_numpy(dtype=float)
        if len(pts) > 1:
            from scipy.spatial import cKDTree
            nn = cKDTree(pts).query(pts, k=2)[0][:, 1]
            nn = nn[np.isfinite(nn) & (nn > 0)]
            spacing = float(np.median(nn)) if nn.size else 1.0
        else:
            spacing = 1.0
        radius = 0.42 * spacing
    donut = float(block.get("donut_hole", 0.0))
    w, h = figure_size(spec, style, aspect=0.95)
    drawn = 0

    show_legend = bool(block.get("legend", True))
    fig_w, legend_rect = (widen_for_outside_legend(w, levels, style, str(category))
                          if show_legend else (w, None))

    with style.apply():
        fig, ax = plt.subplots(figsize=(fig_w, h))
        bg_record = draw_background_image(ax, block)
        for sid, grp in data.groupby(spot, sort=False):
            cx, cy = float(grp[x].iloc[0]), float(grp[y].iloc[0])
            fr = grp.set_index(grp[category].astype(str))["_f"]
            total = float(fr.sum())
            if total <= 0:
                continue
            start = float(block.get("start_angle", 90.0))
            for lv in levels:
                frac = float(fr.get(lv, 0.0))
                if frac <= 0:
                    continue
                extent = 360.0 * frac / (total if normalize == "as_given" and total > 0 else 1.0)
                ax.add_patch(Wedge((cx, cy), radius, start, start + extent,
                                   width=radius * (1 - donut) if donut else None,
                                   facecolor=colours[lv], edgecolor="none", zorder=3))
                start += extent
            drawn += 1
        ax.autoscale_view()
        ax.set_xlim(float(spots["_x"].min()) - 2 * radius, float(spots["_x"].max()) + 2 * radius)
        ax.set_ylim(float(spots["_y"].min()) - 2 * radius, float(spots["_y"].max()) + 2 * radius)

        apply_crop(ax, block)
        finish_spatial_axes(ax, block, show_axes=bool(block.get("show_axes", False)))
        bar = add_scale_bar(ax, block, style)
        title = (spec.get("layout", {}) or {}).get("title")
        if title:
            ax.set_title(str(title))

        if show_legend:
            handles = [Line2D([0], [0], marker="o", linestyle="none", markersize=7,
                              markerfacecolor=colours[c], markeredgecolor="white", label=c)
                       for c in levels]
            # Always outside: a legend placed "best" lands on the tissue, which is
            # the part of the figure the reader came for.
            fig.tight_layout(rect=legend_rect)
            ax.legend(handles=handles, title=str(category), loc="upper left",
                      bbox_to_anchor=(1.02, 1.0), frameon=style.legend_frameon,
                      ncol=max(1, int(block.get("legend_columns", 1))))
        else:
            fig.tight_layout()

    meta = base_metadata(spec, style, data, used_columns=[spot, x, y, category, value])
    meta["spatial"] = {
        **coordinate_record(x, y, block),
        "spot_column": spot, "category_column": category, "value_column": value,
        "categories": levels, "normalize": normalize,
        "top_k": top_k, "min_fraction": min_fraction,
        "collapsed_categories": collapsed, "other_label": other_label if collapsed else None,
        "n_spots": int(len(spots)), "n_spots_drawn": int(drawn),
        "glyph_radius": radius, "donut_hole": donut,
        "scale_bar": bar, "background_image": bg_record,
    }
    if bar and not bar.get("drawn"):
        warnings.append(f"Scale bar not drawn: {bar['reason']}.")
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
