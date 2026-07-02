"""Oncology-style waterfall plot of per-patient best percent change."""

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

PLOT_TYPE = "waterfall_plot"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", "patient_id")
    y = get_mapping(spec, "y", "best_percent_change")
    color_by = get_mapping(spec, "color", None)
    sort = str(get_mapping(spec, "sort", "ascending")).lower()

    require_columns(df, [y], context=PLOT_TYPE)
    work = df.copy()
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)
    work = work.dropna(subset=[y])

    ascending = sort != "descending"
    work = work.sort_values(y, ascending=ascending).reset_index(drop=True)
    positions = np.arange(len(work))
    warnings: List[str] = []

    # Color mapping: by category if provided, else by sign.
    if color_by and color_by in work.columns:
        cats = list(dict.fromkeys(work[color_by].tolist()))
        cmap = {c: style.color_for(i) for i, c in enumerate(cats)}
        colors = [cmap[c] for c in work[color_by]]
        legend_handles = cats
    else:
        colors = [style.color_for(1) if v > 0 else style.color_for(0) for v in work[y]]
        legend_handles = None

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.6))
        ax.bar(positions, work[y], color=colors, edgecolor="black",
               linewidth=style.spine_width_pt, width=0.85)
        ax.axhline(0, color="black", lw=style.spine_width_pt)
        # Common RECIST reference lines (informational only, not clinical advice).
        ax.axhline(20, ls="--", lw=style.spine_width_pt, color="0.6")
        ax.axhline(-30, ls="--", lw=style.spine_width_pt, color="0.6")

        ax.set_xticks([])
        ax.set_xlabel(spec.get("layout", {}).get("x_label", "Patients (sorted)"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", "Best % change"))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        if legend_handles is not None:
            from matplotlib.patches import Patch

            handles = [Patch(facecolor=cmap[c], edgecolor="black", label=str(c))
                       for c in legend_handles]
            ax.legend(handles=handles, title=str(color_by), frameon=False, loc="best")
        style_axes(ax, style)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[x, y, color_by])
    meta["n_patients"] = int(len(work))
    meta["sort"] = "ascending" if ascending else "descending"
    meta["n_decrease"] = int((work[y] < 0).sum())
    meta["n_increase"] = int((work[y] > 0).sum())
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
