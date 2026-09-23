"""Grouped (two-factor) bar plot with error bars.

Bars are dodged within each x-level cluster by the ``group`` column. Shares the summary/error,
observation-overlay, n-label, fill and orientation options of the simple bar plot through
:mod:`make_my_figure_core.plots._bar_shared`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots._bar_shared import (
    BarOptions,
    GroupSummary,
    annotate_statistics,
    apply_baseline_policy,
    draw_bars,
    fold_n_into_labels,
    n_legend_labels,
    record_metadata,
    summarize_group,
    value_extent,
)
from make_my_figure_core.plots.base import (
    autorotate_xticklabels,
    RenderResult,
    apply_axis_overrides,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    place_legend,
    require_columns,
    style_axes,
)
from make_my_figure_core.plots.observations import add_n_labels, draw_observations
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "grouped_barplot_with_error_bar"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    group = get_mapping(spec, "group", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    opts = BarOptions.from_spec(spec, default_width=0.8, context=PLOT_TYPE)

    require_columns(df, [x, group, y], context=PLOT_TYPE)
    work = df.copy()
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)

    x_levels: List[Any] = list(dict.fromkeys(work[x].tolist()))
    groups: List[Any] = list(dict.fromkeys(work[group].tolist()))

    n_groups = len(groups)
    total_width = opts.bar_width           # width of the whole cluster (historical 0.8)
    bar_width = total_width / max(n_groups, 1)
    x_idx = np.arange(len(x_levels))

    warnings: List[str] = list(opts.warnings)

    # summaries[g][xi]
    summaries: Dict[Any, List[GroupSummary]] = {
        g: [summarize_group(work.loc[(work[x] == xl) & (work[group] == g), y].to_numpy(),
                            opts.summary, opts.error) for xl in x_levels]
        for g in groups
    }
    if any(s.n < 2 for cells in summaries.values() for s in cells if s.n > 0):
        warnings.append("Some cells have < 2 replicates; error bars are zero there.")

    positions_map: Dict[Any, float] = {}
    tops: Dict[Tuple[str, str], float] = {}
    group_n: Dict[str, int] = {}
    n_drawn = 0
    obs_extents: List[Tuple[float, float]] = []
    all_summaries: List[GroupSummary] = []

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.7))
        obs_style = opts.observation_style_for_width(bar_width) if opts.points else None
        rng = np.random.default_rng(obs_style.seed) if obs_style is not None else None
        for gi, g in enumerate(groups):
            cells = summaries[g]
            all_summaries += cells
            offset = (gi - (n_groups - 1) / 2.0) * bar_width
            color = style.color_for(gi)
            cell_positions = [float(x_idx[xi] + offset) for xi in range(len(x_levels))]
            draw_bars(ax, cell_positions, cells, [color] * len(cells), opts=opts, style=style,
                      width=bar_width, label=str(g))
            for xi, xl in enumerate(x_levels):
                key = (str(xl), str(g))
                positions_map[key] = cell_positions[xi]
                group_n[f"{xl}|{g}"] = cells[xi].n
                top = cells[xi].top
                if opts.points and cells[xi].n:
                    info = draw_observations(ax, cell_positions[xi], cells[xi].values, color=color,
                                             style=style, obs=obs_style, orientation=opts.orientation,
                                             rng=rng, base_size=style.marker_size)
                    n_drawn += info["n"]
                    obs_extents.append((info["min"], info["max"]))
                    if top != top or info["max"] > top:
                        top = info["max"]
                    if info["suggestion"] and info["suggestion"] not in warnings:
                        warnings.append(info["suggestion"])
                if top == top:
                    tops[key] = float(top)

        # Also register whole-cluster positions (keyed by the x-level alone) so a
        # comparison of the x-factor across clusters (e.g. WT vs KO) can be drawn
        # spanning cluster centers, not just subgroup-within-cluster comparisons.
        cluster_tops: Dict[str, float] = {}
        for xi, xl in enumerate(x_levels):
            positions_map[str(xl)] = float(x_idx[xi])
            cell_tops = [tops[(str(xl), str(g))] for g in groups if (str(xl), str(g)) in tops]
            if cell_tops:
                cluster_tops[str(xl)] = max(cell_tops)

        tick_labels = [str(c) for c in x_levels]
        if opts.show_n == "below":
            # One n per cluster when every cell agrees, otherwise the per-group counts in order.
            cluster_counts = []
            for xl in x_levels:
                ns = [group_n[f"{xl}|{g}"] for g in groups]
                cluster_counts.append(ns)
            tick_labels = [f"{lab}\n(n = {ns[0]})" if len(set(ns)) == 1
                           else f"{lab}\n(n = {', '.join(str(n) for n in ns)})"
                           for lab, ns in zip(tick_labels, cluster_counts)]
        layout = spec.get("layout", {}) or {}
        cat_label = layout.get("x_label", x)
        val_label = layout.get("y_label", y)
        suffix = opts.value_label_suffix()
        if suffix:
            val_label = f"{val_label} {suffix}"
        if opts.horizontal:
            ax.set_yticks(x_idx)
            ax.set_yticklabels(tick_labels)
            ax.set_ylabel(cat_label)
            ax.set_xlabel(val_label)
            ax.margins(x=0.08)
        else:
            ax.set_xticks(x_idx)
            ax.set_xticklabels(tick_labels)
            autorotate_xticklabels(ax, style, rotation=get_mapping(spec, "x_tick_rotation", "auto"))
            ax.set_xlabel(cat_label)
            ax.set_ylabel(val_label)
            ax.margins(y=0.08)
        title = layout.get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)

        # Axis policy: zero baseline when nothing is negative; whiskers and points always inside.
        low, high = value_extent(all_summaries, obs_extents)
        baseline_zero = apply_baseline_policy(ax, opts=opts, low=low, high=high)
        extent = ((min(low, 0.0) if baseline_zero else low), high) if low == low else None
        axis_overrides = apply_axis_overrides(
            ax, spec, x_extent=extent if opts.horizontal else None,
            y_extent=None if opts.horizontal else extent)

        # n labels: per cell above the bars, folded into the tick labels (below) or the legend.
        if opts.show_n == "above":
            cell_keys = [(str(xl), str(g)) for g in groups for xl in x_levels]
            add_n_labels(ax, [positions_map[k] for k in cell_keys],
                         [group_n[f"{k[0]}|{k[1]}"] for k in cell_keys],
                         where="above", style=style, orientation=opts.orientation,
                         tops=[tops.get(k, float("nan")) for k in cell_keys])
        legend_labels: Optional[List[str]] = None
        if opts.show_n == "legend":
            legend_labels = n_legend_labels(
                [str(g) for g in groups],
                [[group_n[f"{xl}|{g}"] for xl in x_levels] for g in groups])

        # Place the legend first (it shrinks the axes width); annotate afterwards
        # so bracket-label widths are measured against the final axes geometry.
        if legend_labels is not None:
            handles, _ = ax.get_legend_handles_labels()
            place_legend(ax, style, title=str(group), handles=handles, labels=legend_labels,
                         force_outside=True)
        else:
            place_legend(ax, style, title=str(group), force_outside=True)

        headroom = 0.0
        if opts.show_n == "above":
            v0, v1 = ax.get_xlim() if opts.horizontal else ax.get_ylim()
            headroom = 0.07 * (v1 - v0)
        tops_map: Dict[Any, float] = {k: v + headroom for k, v in tops.items()}
        tops_map.update({k: v + headroom for k, v in cluster_tops.items()})
        stats_report = annotate_statistics(spec, work, style, PLOT_TYPE, ax, positions=positions_map,
                                           tops=tops_map, opts=opts, warnings=warnings)

    meta = base_metadata(spec, style, work, used_columns=[x, group, y])
    record_metadata(meta, opts, group_n=group_n, baseline_zero=baseline_zero,
                    n_observations_drawn=n_drawn, axis_overrides=axis_overrides)
    meta["x_levels"] = [str(c) for c in x_levels]
    meta["groups"] = [str(g) for g in groups]
    meta["centers"] = {str(g): [None if s.center != s.center else round(float(s.center), 6)
                                for s in summaries[g]] for g in groups}
    if stats_report is not None:
        meta["statistics_report"] = stats_report.to_dict()
    return RenderResult(figure=fig, metadata=meta, warnings=warnings,
                        stats_report=stats_report)
