"""Cell-type x cellular-neighbourhood enrichment, as a dot matrix.

Two quantities in one panel, following CNTools Fig. 3A (Tao et al. 2024):
colour carries the enrichment score, point area carries the cell type's
frequency within that neighbourhood. Rows are neighbourhoods, columns are cell
types.

The renderer plots the numbers it is given and does not recompute them. The
enrichment table is produced by ``make_my_figure_core.spatial.ct_cn_enrichment``
so that the figure and the analysis record can never disagree — exactly the
failure mode a dot matrix invites, where colour and size come from different
passes over the data.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import CenteredNorm, Normalize
from matplotlib.lines import Line2D

from make_my_figure_core.plots.base import (
    resolve_figure_size,
    RenderError, RenderResult, base_metadata, figure_size, get_mapping, require_columns,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "neighborhood_enrichment_matrix"


def _order(series: pd.Series, declared) -> List[str]:
    present = [str(v) for v in pd.unique(series.astype(str))]
    if declared:
        first = [str(v) for v in declared if str(v) in present]
        return first + sorted(set(present) - set(first))
    return sorted(present)


def render(spec: Dict[str, Any], df: pd.DataFrame, style: StyleProfile) -> RenderResult:
    row = get_mapping(spec, "neighborhood", required=True, context=PLOT_TYPE)
    col = get_mapping(spec, "cell_type", required=True, context=PLOT_TYPE)
    score = get_mapping(spec, "enrichment", required=True, context=PLOT_TYPE)
    freq = get_mapping(spec, "frequency")
    require_columns(df, [c for c in (row, col, score, freq) if c], context=PLOT_TYPE)

    # Through the shared helper, so GUI settings reach this plot too - it used to
    # read spec["spatial"] directly and so ignored everything the user chose.
    from make_my_figure_core.plots._spatial_shared import spatial_block

    block = spatial_block(spec)
    warnings: List[str] = []

    data = df[[c for c in (row, col, score, freq) if c]].copy()
    data[score] = pd.to_numeric(data[score], errors="coerce")
    if freq:
        data[freq] = pd.to_numeric(data[freq], errors="coerce")
        if (data[freq].dropna() < 0).any():
            raise RenderError(f"{PLOT_TYPE}: {freq!r} has negative values; point area "
                              "cannot represent a negative frequency.")

    rows = _order(data[row], block.get("neighborhood_order"))
    cols = _order(data[col], block.get("cell_type_order"))
    dup = data.duplicated(subset=[row, col]).sum()
    if dup:
        raise RenderError(
            f"{PLOT_TYPE}: {dup} duplicate (neighbourhood, cell type) pair(s). "
            "Each cell of the matrix must have exactly one value.")

    n_missing = int(data[score].isna().sum())
    if n_missing:
        warnings.append(f"{n_missing} matrix cell(s) have no enrichment score and are left "
                        "blank rather than drawn as zero.")

    finite = data[score].dropna()
    if finite.empty:
        raise RenderError(f"{PLOT_TYPE}: no finite enrichment scores to draw.")
    lo = float(block["vmin"]) if block.get("vmin") is not None else float(finite.min())
    hi = float(block["vmax"]) if block.get("vmax") is not None else float(finite.max())
    centre = block.get("center", 0.0)
    if centre is not None:
        # Enrichment is a log ratio: zero means "as expected", so a diverging
        # scale centred on zero is the honest default.
        half = max(abs(hi - float(centre)), abs(float(centre) - lo)) or 1.0
        norm = Normalize(vmin=float(centre) - half, vmax=float(centre) + half)
        scale_kind = f"diverging (symmetric about {float(centre):g})"
    else:
        norm = Normalize(vmin=lo, vmax=hi)
        scale_kind = "linear"
    # Follow the active style unless the spec names a colormap. The fallback used
    # to be a hard-coded "RdBu_r", which meant the Palette control did nothing at
    # all to this plot - choosing grayscale still produced a red/blue figure.
    # A diverging scale is centred on zero, so it takes the style's diverging
    # colormap; an uncentred one takes the sequential.
    _default_cmap = (style.diverging_cmap if centre is not None
                     else style.sequential_cmap)
    cmap = plt.get_cmap(block.get("cmap") or _default_cmap)

    max_area = float(block.get("max_point_area", 260.0))
    ridx = {r: i for i, r in enumerate(rows)}
    cidx = {c: i for i, c in enumerate(cols)}
    xs, ys, cs, ss = [], [], [], []
    fmax = float(data[freq].max()) if freq and data[freq].notna().any() else 1.0
    for _, r in data.iterrows():
        if pd.isna(r[score]):
            continue
        xs.append(cidx[str(r[col])]); ys.append(ridx[str(r[row])]); cs.append(float(r[score]))
        ss.append(max_area * (float(r[freq]) / fmax if freq and fmax > 0 and pd.notna(r[freq])
                              else 0.55))

    # Grow with the matrix so labels stay legible - but an explicit request
    # from the user wins, because a figure that ignores the size you asked for
    # cannot be fitted to a column. Resolved last, and per dimension, so pinning
    # only a width (the usual way to fit a journal column) is honoured too
    # instead of being thrown away for want of a height.
    w, h = figure_size(spec, style, aspect=0.62)
    w, h = resolve_figure_size(spec, (max(w, 0.30 * len(cols) + 3.0),
                                      max(h, 0.34 * len(rows) + 2.0)))

    with style.apply():
        fig, ax = plt.subplots(figsize=(w, h))
        sc = ax.scatter(xs, ys, c=cs, s=ss, cmap=cmap, norm=norm,
                        linewidths=0.3, edgecolors="white", zorder=3)
        ax.set_xticks(range(len(cols)))
        ax.set_xticklabels(cols, rotation=90, ha="center", fontsize=style.tick_label_pt)
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels(rows, fontsize=style.tick_label_pt)
        ax.set_xlim(-0.6, len(cols) - 0.4)
        ax.set_ylim(len(rows) - 0.4, -0.6)     # first neighbourhood at the top
        # Name the axes: the tick labels are identifiers, and a reader should not
        # have to infer that 'CT_00' is a cell type or 'CN1' a neighbourhood.
        ax.set_xlabel(str(block.get("x_label", "Cell type")), fontsize=style.axis_font_pt)
        ax.set_ylabel(str(block.get("y_label", "Cellular neighbourhood")),
                      fontsize=style.axis_font_pt)
        ax.set_axisbelow(True)
        # The guide grid follows the global Grid control unless the spec pins
        # spatial.grid. It used to be drawn unconditionally, which meant turning
        # the Grid checkbox off did nothing at all on this plot type - the one
        # kind of broken control the user cannot diagnose from the figure.
        # Default True, not style.grid. The publication profile sets grid=False,
        # so deferring to it would drop the faint guide lines this matrix has
        # always drawn - they are what lets the eye carry a dot back to its row
        # and column across a 28-column figure. The control is still real: the
        # per-plot Grid option lands in the block via spatial_block(), so an
        # explicit choice wins while the published default is kept.
        if block.get("grid", True):
            ax.grid(True, which="major", color="#eeeeee", linewidth=0.6, zorder=0)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        title = (spec.get("layout", {}) or {}).get("title")
        if title:
            ax.set_title(str(title))
        # Reserve the right margin first: tight_layout afterwards would otherwise
        # reclaim it and clip the size key.
        needs_key = bool(freq and block.get("size_legend", True))
        fig.tight_layout(rect=(0, 0.12 if needs_key else 0.0, 0.98, 1))

        # If any value falls outside the drawn range, the colourbar says so with an
        # arrow rather than letting a clipped point look like an extreme one.
        below = bool((finite < norm.vmin).any())
        above = bool((finite > norm.vmax).any())
        extend = ("both" if below and above else
                  "min" if below else "max" if above else "neither")
        cb = fig.colorbar(sc, ax=ax, fraction=0.03, pad=0.02, extend=extend)
        cb.set_label(str(block.get("colorbar_label", "Enrichment score")),
                     fontsize=style.axis_font_pt)
        cb.ax.tick_params(labelsize=style.tick_label_pt)
        if extend != "neither":
            n_out = int((finite < norm.vmin).sum() + (finite > norm.vmax).sum())
            warnings.append(
                f"{n_out} value(s) fall outside the colour range "
                f"[{norm.vmin:.3g}, {norm.vmax:.3g}] and are drawn at the end colours; the "
                "colourbar is extended to show this. Widen vmin/vmax to bring them in.")

        if needs_key:
            # A dot matrix is unreadable without a size key. It goes below the
            # matrix rather than to the right, where it would sit underneath the
            # colourbar and be invisible.
            levels = [0.25, 0.5, 1.0]
            handles = [Line2D([0], [0], marker="o", linestyle="none",
                              markerfacecolor="#999999", markeredgecolor="white",
                              markersize=np.sqrt(max_area * f) / 2.0,
                              label=f"{f * fmax:.2f}") for f in levels]
            # Place the key below whatever the x axis actually occupies, measured
            # rather than assumed. A fixed offset collides with the tick labels
            # as soon as the figure is short or the user sets their own margins.
            anchor_y = 0.005
            lowest = 0.0
            try:
                fig.canvas.draw()
                renderer = fig.canvas.get_renderer()
                lowest = min(
                    [t.get_window_extent(renderer).y0 for t in ax.get_xticklabels()
                     if t.get_text()]
                    + ([ax.xaxis.label.get_window_extent(renderer).y0]
                       if ax.get_xlabel() else []))
                anchor_y = max(0.005, (lowest / fig.bbox.height) - 0.03)
            except Exception:  # noqa: BLE001 - placement must never break a render
                pass
            leg = fig.legend(handles=handles,
                             title=str(block.get("size_legend_title", "Frequency in CN")),
                             loc="upper center", bbox_to_anchor=(0.5, anchor_y),
                             ncol=len(levels), frameon=style.legend_frameon,
                             handletextpad=1.2, columnspacing=2.4,
                             fontsize=style.tick_label_pt)
            # If the layout leaves no room, say so instead of overlapping quietly.
            try:
                fig.canvas.draw()
                r2 = fig.canvas.get_renderer()
                if leg.get_window_extent(r2).y1 > lowest + 1:
                    warnings.append(
                        "The size key overlaps the x-axis labels: this layout leaves no "
                        "room beneath them. Increase the figure height, raise the bottom "
                        "margin, or set size_legend=false.")
            except Exception:  # noqa: BLE001
                pass

    meta = base_metadata(spec, style, data, used_columns=[row, col, score, freq])
    meta["spatial"] = {
        "neighborhood_column": row, "cell_type_column": col,
        "enrichment_column": score, "frequency_column": freq,
        "neighborhoods": rows, "cell_types": cols,
        "n_matrix_cells": int(len(rows) * len(cols)), "n_drawn": int(len(xs)),
        "missing_cells": n_missing, "color_scale": scale_kind,
        "vmin": float(norm.vmin), "vmax": float(norm.vmax),
        "max_point_area": max_area, "frequency_max": fmax,
        "recomputed_values": False,
        "note": ("Values are plotted as supplied; the renderer never recomputes them, so "
                 "the figure and the analysis record cannot disagree."),
    }
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
