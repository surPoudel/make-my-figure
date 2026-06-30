"""Lollipop mutation plot: stem + marker at each protein position."""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

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

PLOT_TYPE = "lollipop_mutation_plot"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", "protein_position")
    y = get_mapping(spec, "y", "sample_count")
    color_by = get_mapping(spec, "color", None)
    label_col = get_mapping(spec, "label", None)
    max_labels = int(get_mapping(spec, "max_labels", 5))

    require_columns(df, [x, y], context=PLOT_TYPE)
    work = df.copy()
    work[x] = coerce_numeric(work, x, context=PLOT_TYPE)
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)
    work = work.dropna(subset=[x, y]).sort_values(x)

    if color_by and color_by in work.columns:
        types = list(dict.fromkeys(work[color_by].astype(str).tolist()))
        color_map = {t: style.color_for(i) for i, t in enumerate(types)}
        point_colors = [color_map[str(t)] for t in work[color_by]]
    else:
        color_map = None
        point_colors = [style.color_for(0)] * len(work)

    warnings: List[str] = []

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.5))
        xs = work[x].to_numpy(dtype=float)
        ys = work[y].to_numpy(dtype=float)
        ax.vlines(xs, 0, ys, color="0.6", linewidth=style.spine_width_pt, zorder=1)
        ax.scatter(xs, ys, s=np.clip(ys * 12, 20, 200), c=point_colors,
                   edgecolors="black", linewidths=style.spine_width_pt, zorder=3)

        # Protein backbone line.
        ax.axhline(0, color="black", lw=style.line_width_pt)

        # Label the highest-count positions.
        if label_col and label_col in work.columns:
            top = work.sort_values(y, ascending=False).head(max_labels)
            for _, r in top.iterrows():
                txt = str(r[label_col]).strip()
                if txt and txt.lower() != "nan":
                    ax.annotate(txt, (r[x], r[y]), fontsize=style.axis_font_pt - 1,
                                xytext=(0, 3), textcoords="offset points", ha="center")

        ax.set_ylim(bottom=0)
        ax.set_xlabel(spec.get("layout", {}).get("x_label", "Protein position"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", y))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        if color_map is not None:
            handles = [Patch(facecolor=color_map[t], edgecolor="black", label=str(t))
                       for t in types]
            ax.legend(handles=handles, title=str(color_by), frameon=False, loc="best")
        style_axes(ax)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[x, y, color_by, label_col])
    meta["n_positions"] = int(len(work))
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
