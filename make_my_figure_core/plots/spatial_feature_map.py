"""Cells or spots in tissue coordinates, coloured by a continuous value.

Gene or marker expression, QC scores, module scores — anything numeric that
varies across tissue.

The rule this renderer exists to keep: **the colour scale never lies about the
numbers.** No transform, normalisation, clipping or standardisation is applied
unless the spec asks for it by name; whatever is applied is recorded in the
metadata and written into the colourbar label, so a reader can tell
``log2(expression)`` from ``expression`` by looking at the figure.

Accepts either shape:

* wide — one ``value`` column, optionally facetted by sample/image;
* long — a ``feature`` column plus a ``value`` column, facetted by feature.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import CenteredNorm, LogNorm, Normalize, SymLogNorm

from make_my_figure_core.plots._spatial_shared import (
    add_scale_bar, apply_crop, coordinate_record, draw_background_image, facet_grid,
    finish_spatial_axes, numeric_coordinates, ordered_levels, share_facet_limits,
    should_rasterize, spatial_block,
)
from make_my_figure_core.plots.base import (
    RenderError, RenderResult, base_metadata, figure_size, get_mapping, require_columns,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "spatial_feature_map"

# Transforms the user may ask for by name. Nothing is applied implicitly.
_TRANSFORMS = {
    "none":   (lambda v: v,                      "{}"),
    "log2":   (lambda v: np.log2(v),             "log2({})"),
    "log10":  (lambda v: np.log10(v),            "log10({})"),
    "log1p":  (lambda v: np.log1p(v),            "log(1 + {})"),
    "log2p1": (lambda v: np.log2(v + 1.0),       "log2(1 + {})"),
    "sqrt":   (lambda v: np.sqrt(v),             "sqrt({})"),
}
_STRICTLY_POSITIVE = {"log2", "log10"}
_NON_NEGATIVE = {"log1p", "log2p1", "sqrt"}


def _apply_transform(values: pd.Series, name: str, label: str) -> Tuple[pd.Series, str]:
    if name not in _TRANSFORMS:
        raise RenderError(
            f"{PLOT_TYPE}: unknown spatial.transform {name!r}. "
            f"Choose one of {sorted(_TRANSFORMS)}.")
    fn, fmt = _TRANSFORMS[name]
    finite = values.dropna()
    if name in _STRICTLY_POSITIVE and (finite <= 0).any():
        n = int((finite <= 0).sum())
        raise RenderError(
            f"{PLOT_TYPE}: transform {name!r} needs strictly positive values, but {n} "
            f"value(s) are <= 0. Zeros are not nudged and negatives are not dropped — "
            f"use 'log1p'/'log2p1' if zeros are expected, or leave the data untransformed.")
    if name in _NON_NEGATIVE and (finite < 0).any():
        n = int((finite < 0).sum())
        raise RenderError(
            f"{PLOT_TYPE}: transform {name!r} needs non-negative values, but {n} "
            f"value(s) are < 0.")
    return values.map(fn) if name != "none" else values, fmt.format(label)


def _limits(values: np.ndarray, block: Dict[str, Any]) -> Tuple[float, float, Optional[List[float]]]:
    """Resolve vmin/vmax. Percentile clipping happens only when explicitly requested."""
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        raise RenderError(f"{PLOT_TYPE}: no finite values to colour by.")
    clip = block.get("percentile_clip")
    clipped = None
    if clip:
        if len(clip) != 2 or not (0 <= float(clip[0]) < float(clip[1]) <= 100):
            raise RenderError(f"{PLOT_TYPE}: spatial.percentile_clip must be "
                              f"[low, high] within 0..100, got {clip!r}.")
        lo, hi = np.percentile(finite, [float(clip[0]), float(clip[1])])
        clipped = [float(clip[0]), float(clip[1])]
    else:
        lo, hi = float(finite.min()), float(finite.max())
    if block.get("vmin") is not None:
        lo = float(block["vmin"])
    if block.get("vmax") is not None:
        hi = float(block["vmax"])
    if not np.isfinite(lo) or not np.isfinite(hi) or lo == hi:
        hi = lo + 1.0 if lo == hi else hi
    return float(lo), float(hi), clipped


def _norm(block: Dict[str, Any], lo: float, hi: float, values: np.ndarray):
    scale = str(block.get("color_scale", "linear")).lower()
    if scale == "linear":
        if block.get("center") is not None:
            return CenteredNorm(vcenter=float(block["center"])), "linear (centered)"
        return Normalize(vmin=lo, vmax=hi), "linear"
    if scale == "log":
        finite = values[np.isfinite(values)]
        if (finite <= 0).any():
            raise RenderError(
                f"{PLOT_TYPE}: spatial.color_scale='log' needs strictly positive values; "
                f"{int((finite <= 0).sum())} are <= 0. Use 'symlog', or transform the data "
                f"explicitly with spatial.transform.")
        return LogNorm(vmin=max(lo, float(finite[finite > 0].min())), vmax=hi), "log"
    if scale == "symlog":
        lt = float(block.get("symlog_linthresh", 1.0))
        return SymLogNorm(linthresh=lt, vmin=lo, vmax=hi), f"symlog (linthresh={lt:g})"
    if scale == "diverging":
        centre = float(block.get("center", 0.0))
        half = max(abs(hi - centre), abs(centre - lo))
        return Normalize(vmin=centre - half, vmax=centre + half), "diverging (symmetric)"
    raise RenderError(f"{PLOT_TYPE}: unknown spatial.color_scale {scale!r}. "
                      "Choose linear, log, symlog or diverging.")


def render(spec: Dict[str, Any], df: pd.DataFrame, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    value = get_mapping(spec, "value", required=True, context=PLOT_TYPE)
    feature = get_mapping(spec, "feature")          # long form: facet by feature
    facet = get_mapping(spec, "facet")              # wide form: facet by sample/image
    if feature and facet:
        raise RenderError(f"{PLOT_TYPE}: use either 'feature' (long form) or 'facet' "
                          "(wide form), not both.")
    require_columns(df, [c for c in (x, y, value, feature, facet) if c], context=PLOT_TYPE)

    block = spatial_block(spec)
    warnings: List[str] = []

    cols = [c for c in (x, y, value, feature, facet) if c]
    data = df[cols].copy()
    numeric_coordinates(data, x, y, context=PLOT_TYPE)
    data[value] = pd.to_numeric(data[value], errors="coerce")

    n_missing = int(data[value].isna().sum())
    if n_missing:
        warnings.append(
            f"{n_missing} cell(s) have no {value!r} value; they are drawn in "
            f"{block.get('missing_color', '#e0e0e0')} rather than omitted, so absent data "
            "is visible instead of looking like empty tissue.")

    transform = str(block.get("transform", "none"))
    values, colour_label = _apply_transform(data[value], transform, str(value))
    data["_v"] = values
    if transform != "none":
        warnings.append(f"Values were transformed with {transform!r} because the spec asked "
                        f"for it; the colourbar is labelled {colour_label!r}.")

    split_col = feature or facet
    levels = ordered_levels(data[split_col].astype(str),
                            block.get("feature_order") or block.get("facet_order")) \
        if split_col else [None]
    nrows, ncols = facet_grid(len(levels), block.get("facet_columns"))
    w, h = figure_size(spec, style, aspect=0.95)

    shared = bool(block.get("shared_color_scale", True))
    if not shared and len(levels) > 1:
        warnings.append("Each panel uses its own colour scale (shared_color_scale=false); "
                        "panels are not comparable by colour.")

    arr_all = data["_v"].to_numpy(dtype=float)
    g_lo, g_hi, clipped = _limits(arr_all, block)
    cmap = plt.get_cmap(block.get("cmap") or style.sequential_cmap)
    cmap = cmap.copy()
    cmap.set_bad(block.get("missing_color", "#e0e0e0"))

    size = float(block.get("marker_size", style.marker_size))
    alpha = float(block.get("alpha", style.marker_alpha))
    raster = should_rasterize(len(data), block)
    panel_limits: Dict[str, List[float]] = {}

    with style.apply():
        fig, axes = plt.subplots(nrows, ncols, figsize=(w * ncols, h * nrows), squeeze=False)
        used_axes, mappable, bg_record = [], None, None
        for idx, lv in enumerate(levels):
            ax = axes[idx // ncols][idx % ncols]
            sub = data if lv is None else data[data[split_col].astype(str) == lv]
            bg_record = draw_background_image(ax, block) or bg_record
            if shared or lv is None:
                lo, hi = g_lo, g_hi
            else:
                lo, hi, _ = _limits(sub["_v"].to_numpy(dtype=float), block)
            panel_limits[str(lv)] = [lo, hi]
            norm, norm_kind = _norm(block, lo, hi, sub["_v"].to_numpy(dtype=float))
            # Missing values are drawn as their own layer rather than pushed through
            # the colour mapping: the cells stay visible, and matplotlib is never asked
            # to normalise a NaN.
            vals = sub["_v"].to_numpy(dtype=float)
            absent = ~np.isfinite(vals)
            if absent.any():
                ax.scatter(sub[x][absent], sub[y][absent], s=size,
                           c=block.get("missing_color", "#e0e0e0"), alpha=alpha,
                           linewidths=0.0, edgecolors="none",
                           marker=str(block.get("marker", "o")),
                           rasterized=raster, zorder=1)
            sc = ax.scatter(sub[x][~absent], sub[y][~absent], c=vals[~absent],
                            cmap=cmap, norm=norm, s=size,
                            alpha=alpha, linewidths=0.0, edgecolors="none",
                            marker=str(block.get("marker", "o")),
                            rasterized=raster, zorder=2)
            mappable = mappable or sc
            apply_crop(ax, block)
            finish_spatial_axes(ax, block, show_axes=bool(block.get("show_axes", False)))
            if lv is not None:
                ax.set_title(str(lv), fontsize=style.axis_font_pt)
            used_axes.append(ax)

        for k in range(len(levels), nrows * ncols):
            axes[k // ncols][k % ncols].set_visible(False)

        shared_lims = share_facet_limits(used_axes, block)
        bars = [add_scale_bar(ax, block, style) for ax in used_axes]

        title = (spec.get("layout", {}) or {}).get("title")
        if title:
            # See the categorical map: suptitle needs the size stated explicitly.
            if len(levels) > 1:
                fig.suptitle(str(title), fontsize=style.title_font_pt)
            else:
                used_axes[0].set_title(str(title))
        fig.tight_layout()

        if block.get("colorbar", True) and mappable is not None:
            label = block.get("colorbar_label") or colour_label
            if shared or len(levels) == 1:
                cb = fig.colorbar(mappable, ax=[a for a in used_axes], fraction=0.035, pad=0.02)
                cb.set_label(str(label), fontsize=style.axis_font_pt)
                cb.ax.tick_params(labelsize=style.tick_label_pt)
            else:
                warnings.append("No shared colourbar drawn: each panel has its own scale.")

    meta = base_metadata(spec, style, data, used_columns=[x, y, value, feature, facet])
    _, norm_kind = _norm(block, g_lo, g_hi, arr_all)
    meta["spatial"] = {
        **coordinate_record(x, y, block),
        "value_column": value, "feature_column": feature, "facet_column": facet,
        "panels": [lv for lv in levels if lv is not None],
        "n_cells": int(len(data)), "missing_value_count": n_missing,
        "transform": transform, "colorbar_label": colour_label,
        "color_scale": norm_kind, "cmap": str(block.get("cmap") or style.sequential_cmap),
        "vmin": g_lo, "vmax": g_hi,
        "vmin_explicit": block.get("vmin") is not None,
        "vmax_explicit": block.get("vmax") is not None,
        "percentile_clip": clipped, "shared_color_scale": shared,
        "panel_limits": panel_limits, "shared_facet_limits": bool(shared_lims),
        "rasterized_marks": bool(raster),
        "scale_bar": bars[0] if bars else None,
        "scale_bar_per_facet": len([b for b in bars if b]),
        "background_image": bg_record,
    }
    if bars and bars[0] and not bars[0].get("drawn"):
        warnings.append(f"Scale bar not drawn: {bars[0]['reason']}.")
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
