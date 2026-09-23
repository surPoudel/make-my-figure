"""Stacked composition bar plot (e.g. cell-type fractions per sample)."""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots.base import (
    autorotate_xticklabels,
    RenderResult,
    apply_publication_layout,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    place_legend,
    require_columns,
    resolve_legend_location,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "stacked_bar_composition"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", "sample_id")
    stack = get_mapping(spec, "stack", "cell_type")
    y = get_mapping(spec, "y", "fraction")
    sort_by = get_mapping(spec, "facet_or_sort_by", None) or get_mapping(spec, "sort_by", None)

    require_columns(df, [x, stack, y], context=PLOT_TYPE)
    work = df.copy()
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)

    warnings: List[str] = []
    # Pivot to samples x components (sum duplicates if any).
    pivot = work.pivot_table(index=x, columns=stack, values=y, aggfunc="sum", fill_value=0.0)

    # Optional ordering of samples by a grouping column.
    if sort_by and sort_by in work.columns:
        order_key = work.drop_duplicates(subset=[x]).set_index(x)[sort_by]
        pivot = pivot.loc[order_key.sort_values(kind="stable").index]

    components = list(pivot.columns)
    samples = [str(s) for s in pivot.index]
    positions = np.arange(len(samples))

    row_sums = pivot.sum(axis=1).replace(0, np.nan)
    if not np.allclose(row_sums.dropna(), 1.0, atol=0.05):
        warnings.append("Fractions do not all sum to ~1 per sample; bars show raw values.")

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.7))
        bottom = np.zeros(len(samples))
        for ci, comp in enumerate(components):
            vals = pivot[comp].to_numpy(dtype=float)
            ax.bar(positions, vals, bottom=bottom, width=0.8, label=str(comp),
                   color=style.color_for(ci), edgecolor="white", linewidth=0.3)
            bottom += vals

        # Ticks are centered on the bar positions; rotation from the layout control
        # (falls back to auto). A small tick pad keeps labels off the axis line.
        ax.set_xticks(positions)
        ax.set_xticklabels(samples)
        autorotate_xticklabels(ax, style, rotation=get_mapping(spec, "x_tick_rotation",
                               spec.get("layout", {}).get("x_tick_rotation", "auto")))
        ax.tick_params(axis="x", pad=3)
        if len(samples) > 30:
            ax.tick_params(axis="x", labelsize=style.axis_font_pt - 2)
        ax.set_xlabel(spec.get("layout", {}).get("x_label", x))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", y))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        place_legend(ax, style, title=str(stack),
                     location=resolve_legend_location(spec, style) if spec.get("layout", {}).get(
                         "legend_location") else ("center left", (1.02, 0.5), "right"))
        style_axes(ax, style)

        # Categorical association test (chi-square / Fisher) as a corner panel.
        # Defaults the contingency to x (row) vs stack (column) when not set.
        from make_my_figure_core.plots.stats_integration import run_and_annotate

        stats_report = run_and_annotate(spec, work, style, PLOT_TYPE, ax=ax,
                                        mode="corner", corner_loc="upper right")
        fig.tight_layout()
        apply_publication_layout(fig, ax, spec, style)

    meta = base_metadata(spec, style, work, used_columns=[x, stack, y, sort_by])
    meta["components"] = [str(c) for c in components]
    meta["n_samples"] = int(len(samples))
    if stats_report is not None:
        meta["statistics_report"] = stats_report.to_dict()
    return RenderResult(figure=fig, metadata=meta, warnings=warnings,
                        stats_report=stats_report)
