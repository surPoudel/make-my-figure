"""Bar plot with error bars (mean or median, with SEM/SD/CI/IQR whiskers over replicates).

Optionally overlays every individual observation (``points``), the per-category n, an outline
fill and a horizontal orientation; see :mod:`make_my_figure_core.plots._bar_shared` for the
shared option and summary logic, and :mod:`make_my_figure_core.plots.observations` for the
point engine.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

from make_my_figure_core.plots._bar_shared import (
    BarOptions,
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

PLOT_TYPE = "barplot_with_error_bar"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    color_by = get_mapping(spec, "color", x)
    opts = BarOptions.from_spec(spec, default_width=0.68, context=PLOT_TYPE)

    require_columns(df, [x, y], context=PLOT_TYPE)
    work = df.copy()
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)

    # Preserve first-seen category order.
    categories: List[Any] = list(dict.fromkeys(work[x].tolist()))
    summaries = [summarize_group(work.loc[work[x] == cat, y].to_numpy(), opts.summary, opts.error)
                 for cat in categories]

    warnings: List[str] = list(opts.warnings)
    if any(s.n < 2 for s in summaries):
        warnings.append("Some categories have < 2 replicates; error bars are zero there.")

    # Bar colours: by category (the default) or by a second column - the ``color`` role. A colour
    # role naming a missing column is reported, never silently ignored.
    color_levels: List[Any] = []
    if color_by and color_by != x:
        if color_by in work.columns:
            color_levels = list(dict.fromkeys(work[color_by].tolist()))
            first_level = {cat: work.loc[work[x] == cat, color_by].iloc[0] for cat in categories}
            colors = [style.color_for(color_levels.index(first_level[cat])) for cat in categories]
        else:
            warnings.append(f"Colour column '{color_by}' is not in the table; bars are coloured "
                            "by category.")
            color_by = x
            colors = [style.color_for(i) for i in range(len(categories))]
    else:
        color_by = x
        colors = [style.color_for(i) for i in range(len(categories))]

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.8))
        positions = list(range(len(categories)))
        draw_bars(ax, positions, summaries, colors, opts=opts, style=style, width=opts.bar_width)

        # Individual observations over the bars: every value, at the bar's position.
        obs_extents: List[Optional[Tuple[float, float]]] = [None] * len(categories)
        n_drawn = 0
        if opts.points:
            obs_style = opts.observation_style_for_width(opts.bar_width)
            rng = np.random.default_rng(obs_style.seed)
            for i, (pos, summ, color) in enumerate(zip(positions, summaries, colors)):
                info = draw_observations(ax, pos, summ.values, color=color, style=style, obs=obs_style,
                                         orientation=opts.orientation, rng=rng,
                                         base_size=style.marker_size)
                n_drawn += info["n"]
                if info["n"]:
                    obs_extents[i] = (info["min"], info["max"])
                if info["suggestion"] and info["suggestion"] not in warnings:
                    warnings.append(info["suggestion"])

        tick_labels = [str(c) for c in categories]
        counts = [s.n for s in summaries]
        if opts.show_n == "below":
            tick_labels = fold_n_into_labels(tick_labels, counts)
        layout = spec.get("layout", {}) or {}
        cat_label = layout.get("x_label", x)
        val_label = layout.get("y_label", y)
        suffix = opts.value_label_suffix()
        if suffix:
            val_label = f"{val_label} {suffix}"
        if opts.horizontal:
            ax.set_yticks(positions)
            ax.set_yticklabels(tick_labels)
            ax.set_ylabel(cat_label)
            ax.set_xlabel(val_label)
            ax.margins(x=0.08)
        else:
            ax.set_xticks(positions)
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
        low, high = value_extent(summaries, [e for e in obs_extents if e is not None])
        baseline_zero = apply_baseline_policy(ax, opts=opts, low=low, high=high)
        extent = ((min(low, 0.0) if baseline_zero else low), high) if low == low else None
        axis_overrides = apply_axis_overrides(
            ax, spec, x_extent=extent if opts.horizontal else None,
            y_extent=None if opts.horizontal else extent)

        # Per-category top of everything drawn (whisker end or highest point) for n labels and
        # brackets, so neither is ever drawn through the data.
        tops: List[float] = []
        for summ, ext in zip(summaries, obs_extents):
            top = summ.top
            if ext is not None and (top != top or ext[1] > top):
                top = ext[1]
            tops.append(top)
        if opts.show_n == "above":
            add_n_labels(ax, positions, counts, where="above", style=style,
                         orientation=opts.orientation, tops=tops)
        if opts.show_n == "legend":
            handles = [Patch(facecolor=("white" if opts.bar_fill == "outline" else c), edgecolor=c)
                       for c in colors]
            place_legend(ax, style, handles=handles,
                         labels=n_legend_labels([str(c) for c in categories], [[n] for n in counts]))
        elif color_levels:
            handles = [Patch(facecolor=("white" if opts.bar_fill == "outline" else style.color_for(i)),
                             edgecolor=style.color_for(i)) for i in range(len(color_levels))]
            place_legend(ax, style, title=str(color_by), handles=handles,
                         labels=[str(lv) for lv in color_levels])

        # Finalize layout before annotating so bracket labels are measured
        # against the final axes geometry.
        fig.tight_layout()

        positions_map = {str(c): float(p) for c, p in zip(categories, positions)}
        tops_map: Dict[str, float] = {}
        headroom = 0.0
        if opts.show_n == "above":
            v0, v1 = ax.get_xlim() if opts.horizontal else ax.get_ylim()
            headroom = 0.07 * (v1 - v0)
        for c, top in zip(categories, tops):
            if top == top:  # not NaN
                tops_map[str(c)] = float(top) + headroom
        stats_report = annotate_statistics(spec, work, style, PLOT_TYPE, ax, positions=positions_map,
                                           tops=tops_map, opts=opts, warnings=warnings)

    meta = base_metadata(spec, style, work, used_columns=[x, y, color_by])
    record_metadata(meta, opts,
                    group_n={str(c): s.n for c, s in zip(categories, summaries)},
                    baseline_zero=baseline_zero, n_observations_drawn=n_drawn,
                    axis_overrides=axis_overrides)
    meta["categories"] = [str(c) for c in categories]
    meta["centers"] = [None if s.center != s.center else round(float(s.center), 6) for s in summaries]
    meta["color_by"] = str(color_by)
    if stats_report is not None:
        meta["statistics_report"] = stats_report.to_dict()
    return RenderResult(figure=fig, metadata=meta, warnings=warnings,
                        stats_report=stats_report)
