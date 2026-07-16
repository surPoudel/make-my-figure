"""Bar plot with error bars (mean +/- SEM/SD/CI over replicates)."""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt

from make_my_figure_core.plots.base import (
    autorotate_xticklabels,
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

PLOT_TYPE = "barplot_with_error_bar"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    error_method = str(get_mapping(spec, "error", "sem"))
    color_by = get_mapping(spec, "color", x)

    require_columns(df, [x, y], context=PLOT_TYPE)
    work = df.copy()
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)

    # Preserve first-seen category order.
    categories: List[Any] = list(dict.fromkeys(work[x].tolist()))

    centers, errors = [], []
    for cat in categories:
        vals = work.loc[work[x] == cat, y].to_numpy()
        c, e = summarize_error(vals, error_method)
        centers.append(c)
        errors.append(e)

    warnings: List[str] = []
    if any(work.groupby(x)[y].count() < 2):
        warnings.append("Some categories have < 2 replicates; error bars are zero there.")

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.8))
        positions = range(len(categories))
        colors = [style.color_for(i) for i in positions]
        ax.bar(
            list(positions),
            centers,
            yerr=errors if error_method.lower() != "none" else None,
            color=colors,
            edgecolor="#222222",
            linewidth=style.bar_edge_width,
            width=0.68,
            capsize=style.errorbar_capsize,
            error_kw={"elinewidth": style.errorbar_line_width,
                      "capthick": style.errorbar_line_width},
        )
        ax.set_xticks(list(positions))
        ax.set_xticklabels([str(c) for c in categories])
        autorotate_xticklabels(ax, style, rotation=get_mapping(spec, "x_tick_rotation", "auto"))
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
        # Finalize layout before annotating so bracket labels are measured
        # against the final axes geometry.
        fig.tight_layout()

        from make_my_figure_core.plots.stats_integration import run_and_annotate

        positions_map = {str(c): p for c, p in zip(categories, positions)}
        tops_map = {}
        for c, center, err in zip(categories, centers, errors):
            if center == center:  # not NaN
                tops_map[str(c)] = float(center) + (float(err) if err == err else 0.0)
        stats_report = run_and_annotate(spec, work, style, PLOT_TYPE, ax=ax,
                                        positions=positions_map, tops=tops_map, mode="bracket")

    meta = base_metadata(spec, style, work, used_columns=[x, y, color_by])
    meta["error_method"] = error_method
    meta["categories"] = [str(c) for c in categories]
    meta["centers"] = [None if c != c else round(float(c), 6) for c in centers]
    if stats_report is not None:
        meta["statistics_report"] = stats_report.to_dict()
    return RenderResult(figure=fig, metadata=meta, warnings=warnings,
                        stats_report=stats_report)
