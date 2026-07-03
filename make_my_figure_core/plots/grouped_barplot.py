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
    place_legend,
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

    positions_map: Dict[str, float] = {}
    tops_map: Dict[str, float] = {}

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
            for xi, xl in enumerate(x_levels):
                key = (str(xl), str(g))
                positions_map[key] = float(x_idx[xi] + offset)
                if centers[xi] == centers[xi]:
                    tops_map[key] = float(centers[xi]) + (float(errors[xi]) if errors[xi] == errors[xi] else 0.0)
            ax.bar(
                x_idx + offset,
                centers,
                bar_width,
                yerr=errors if error_method.lower() != "none" else None,
                label=str(g),
                color=style.color_for(gi),
                edgecolor="#222222",
                linewidth=style.bar_edge_width,
                capsize=style.errorbar_capsize,
                error_kw={"elinewidth": style.errorbar_line_width,
                          "capthick": style.errorbar_line_width},
            )

        # Also register whole-cluster positions (keyed by the x-level alone) so a
        # comparison of the x-factor across clusters (e.g. WT vs KO) can be drawn
        # spanning cluster centers, not just subgroup-within-cluster comparisons.
        for xi, xl in enumerate(x_levels):
            positions_map[str(xl)] = float(x_idx[xi])
            cluster_tops = [tops_map[(str(xl), str(g))] for g in groups
                            if (str(xl), str(g)) in tops_map]
            if cluster_tops:
                tops_map[str(xl)] = max(cluster_tops)

        ax.set_xticks(x_idx)
        ax.set_xticklabels([str(c) for c in x_levels])
        ax.set_xlabel(spec.get("layout", {}).get("x_label", x))
        ylab = spec.get("layout", {}).get("y_label", y)
        if error_method.lower() != "none":
            ylab = f"{ylab} (mean ± {error_method.upper()})"
        ax.set_ylabel(ylab)
        ax.margins(y=0.08)
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)
        # Place the legend first (it shrinks the axes width); annotate afterwards
        # so bracket-label widths are measured against the final axes geometry.
        place_legend(ax, style, title=str(group), force_outside=True)

        from make_my_figure_core.plots.stats_integration import run_and_annotate

        stats_report = run_and_annotate(spec, work, style, PLOT_TYPE, ax=ax,
                                        positions=positions_map, tops=tops_map, mode="bracket")

    meta = base_metadata(spec, style, work, used_columns=[x, group, y])
    meta["error_method"] = error_method
    meta["x_levels"] = [str(c) for c in x_levels]
    meta["groups"] = [str(g) for g in groups]
    if stats_report is not None:
        meta["statistics_report"] = stats_report.to_dict()
    return RenderResult(figure=fig, metadata=meta, warnings=warnings,
                        stats_report=stats_report)
