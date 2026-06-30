"""Bar plot with error bars (mean +/- SEM/SD/CI over replicates)."""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt

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
            edgecolor="black",
            linewidth=style.spine_width_pt,
            width=0.65,
            capsize=2.5,
            error_kw={"elinewidth": style.spine_width_pt, "capthick": style.spine_width_pt},
        )
        ax.set_xticks(list(positions))
        ax.set_xticklabels([str(c) for c in categories])
        ax.set_xlabel(spec.get("layout", {}).get("x_label", x))
        ylab = spec.get("layout", {}).get("y_label", y)
        if error_method.lower() != "none":
            ylab = f"{ylab} (mean ± {error_method.upper()})"
        ax.set_ylabel(ylab)
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[x, y, color_by])
    meta["error_method"] = error_method
    meta["categories"] = [str(c) for c in categories]
    meta["centers"] = [None if c != c else round(float(c), 6) for c in centers]
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
