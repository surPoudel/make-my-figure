"""Grouped (two-factor) bar plot with error bars."""

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
    summarize_error,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "grouped_barplot_with_error_bar"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    group = get_mapping(spec, "group", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    error_method = str(get_mapping(spec, "error", "sem"))

    require_columns(df, [x, group, y], context=PLOT_TYPE)
    work = df.copy()
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)

    x_levels: List[Any] = list(dict.fromkeys(work[x].tolist()))
    groups: List[Any] = list(dict.fromkeys(work[group].tolist()))

    n_groups = len(groups)
    total_width = 0.8
    bar_width = total_width / max(n_groups, 1)
    x_idx = np.arange(len(x_levels))

    warnings: List[str] = []

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.7))
        for gi, g in enumerate(groups):
            centers, errors = [], []
            for xl in x_levels:
                vals = work.loc[(work[x] == xl) & (work[group] == g), y].to_numpy()
                c, e = summarize_error(vals, error_method)
                centers.append(c)
                errors.append(e)
            offset = (gi - (n_groups - 1) / 2.0) * bar_width
            ax.bar(
                x_idx + offset,
                centers,
                bar_width,
                yerr=errors if error_method.lower() != "none" else None,
                label=str(g),
                color=style.color_for(gi),
                edgecolor="black",
                linewidth=style.spine_width_pt,
                capsize=2.0,
                error_kw={"elinewidth": style.spine_width_pt, "capthick": style.spine_width_pt},
            )

        ax.set_xticks(x_idx)
        ax.set_xticklabels([str(c) for c in x_levels])
        ax.set_xlabel(spec.get("layout", {}).get("x_label", x))
        ylab = spec.get("layout", {}).get("y_label", y)
        if error_method.lower() != "none":
            ylab = f"{ylab} (mean ± {error_method.upper()})"
        ax.set_ylabel(ylab)
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        ax.legend(title=str(group), frameon=False, loc="best")
        style_axes(ax)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[x, group, y])
    meta["error_method"] = error_method
    meta["x_levels"] = [str(c) for c in x_levels]
    meta["groups"] = [str(g) for g in groups]
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
