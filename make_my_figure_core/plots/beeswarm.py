"""Beeswarm plot: individual observations per group with collision avoidance.

Like the dot/strip plot, but points are laid out with a quasi-beeswarm
algorithm (see ``_v04_shared.beeswarm_offsets``): observations are binned by
value and spread symmetrically within each bin so same-value points do not
overprint. This is a lightweight, dependency-free approximation of a true
force-directed beeswarm (documented limitation) — it reads cleanly for typical
publication group sizes without requiring an extra package.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots._v04_shared import (
    beeswarm_offsets,
    ordered_unique,
    summary_stat,
)
from make_my_figure_core.plots.base import (
    autorotate_xticklabels,
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

PLOT_TYPE = "beeswarm_plot"

_SUMMARY_CHOICES = ("none", "mean", "median", "ci", "sd", "sem")


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    color_by = get_mapping(spec, "color", None)
    summary = str(get_mapping(spec, "summary", "mean")).lower()
    if summary not in _SUMMARY_CHOICES:
        summary = "mean"

    require_columns(df, [x, y], context=PLOT_TYPE)
    work = df.copy()
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)

    groups = ordered_unique(work[x].tolist())
    has_color = bool(color_by and color_by in work.columns and color_by != x)
    color_levels = ordered_unique(work[color_by].tolist()) if has_color else []
    warnings: List[str] = []

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.72))
        for gi, g in enumerate(groups):
            sub = work[work[x] == g]
            yy = sub[y].to_numpy(float)
            mask = np.isfinite(yy)
            yy = yy[mask]
            if yy.size == 0:
                continue
            dx = beeswarm_offsets(yy, width=0.32, seed=gi + 1)
            if has_color:
                clabels = sub[color_by].astype(str).to_numpy()[mask]
                for ci, lvl in enumerate(color_levels):
                    sel = clabels == str(lvl)
                    if sel.any():
                        ax.scatter(gi + dx[sel], yy[sel], color=style.color_for(ci),
                                   label=str(lvl) if gi == 0 else None, s=style.marker_size,
                                   edgecolors="white", linewidths=style.marker_edge_width,
                                   alpha=style.marker_alpha, zorder=3)
            else:
                ax.scatter(gi + dx, yy, color=style.color_for(0), s=style.marker_size,
                           edgecolors="white", linewidths=style.marker_edge_width,
                           alpha=style.marker_alpha, zorder=3)
            if summary != "none":
                center, err = summary_stat(yy, summary)
                if np.isfinite(center):
                    ax.plot([gi - 0.3, gi + 0.3], [center, center], color=style.text_color,
                            lw=style.line_width_pt * 1.3, zorder=4, solid_capstyle="round")
                    if err > 0:
                        ax.errorbar(gi, center, yerr=err, color=style.text_color,
                                    lw=style.errorbar_line_width, capsize=style.errorbar_capsize,
                                    zorder=4)

        ax.set_xticks(range(len(groups)))
        ax.set_xticklabels([str(g) for g in groups])
        autorotate_xticklabels(ax, style, rotation=get_mapping(spec, "x_tick_rotation", "auto"))
        ax.set_xlabel(spec.get("layout", {}).get("x_label", str(x)))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", str(y)))
        ax.set_xlim(-0.6, len(groups) - 0.4)
        ax.margins(y=0.08)
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)
        if has_color:
            place_legend(ax, style, title=str(color_by), force_outside=True)
        else:
            fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[x, y, color_by])
    meta["n_groups"] = len(groups)
    meta["summary"] = summary
    meta["layout_algorithm"] = "quasi-beeswarm (value-binned; not force-directed)"
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
