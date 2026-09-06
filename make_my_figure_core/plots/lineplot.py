"""Line / time-course plot with a centre line and an error band.

Band methods: ``sem``/``sd``/``ci95`` (mean-centred, symmetric), ``iqr`` and ``range``
(median-centred order statistics, for replicate measurements), or ``none``.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots.base import (
    RenderResult,
    apply_publication_layout,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    place_legend,
    resolve_legend_location,
    require_columns,
    style_axes,
    summarize_band,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "lineplot_timecourse_with_error_band"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    color_by = get_mapping(spec, "color", None)
    error_method = str(get_mapping(spec, "error", "sem"))

    require_columns(df, [x, y], context=PLOT_TYPE)
    work = df.copy()
    work[x] = coerce_numeric(work, x, context=PLOT_TYPE)
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)

    # Optional second grouping: ``style_by`` varies line style and marker within each colour
    # level (e.g. colour = workload, style = platform), so series stay distinguishable in
    # greyscale. Legend entries read "<colour level>, <style level>".
    style_by = get_mapping(spec, "style_by", None)
    if style_by and style_by not in work.columns:
        style_by = None
    if color_by and color_by in work.columns:
        color_levels = list(dict.fromkeys(work[color_by].tolist()))
    else:
        color_levels = [None]
    style_levels = list(dict.fromkeys(work[style_by].tolist())) if style_by else [None]
    series = [(c, st) for c in color_levels for st in style_levels]
    _LS = ["-", "--", ":", "-."]
    _MK = ["o", "s", "^", "D"]
    warnings: List[str] = []

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.7))
        for (c, st) in series:
            ci = color_levels.index(c)
            sti = style_levels.index(st)
            s = c
            sub = work if c is None else work[work[color_by] == c]
            if st is not None:
                sub = sub[sub[style_by] == st]
            if sub.empty:
                continue
            xs = sorted(sub[x].dropna().unique())
            means, lows, highs = [], [], []
            for xv in xs:
                vals = sub.loc[sub[x] == xv, y].to_numpy()
                c, lo, hi = summarize_band(vals, error_method)
                means.append(c)
                lows.append(lo)
                highs.append(hi)
            xs = np.asarray(xs, dtype=float)
            means = np.asarray(means, dtype=float)
            lows = np.asarray(lows, dtype=float)
            highs = np.asarray(highs, dtype=float)
            col = style.color_for(ci)
            label = None if s is None else (f"{s}, {st}" if st is not None else str(s))
            ax.plot(xs, means, color=col, lw=style.line_width_pt, label=label,
                    marker=_MK[sti % len(_MK)], linestyle=_LS[sti % len(_LS)],
                    markersize=max(3.0, style.line_width_pt * 2.2))
            if error_method.lower() != "none":
                ax.fill_between(xs, lows, highs, color=col, alpha=0.2, linewidth=0)

        ax.set_xlabel(spec.get("layout", {}).get("x_label", x))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", y))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        if series != [(None, None)]:
            place_legend(ax, style, title=(str(color_by) or None) if str(color_by).strip() else None,
                         location=resolve_legend_location(spec, style))
        style_axes(ax, style)
        fig.tight_layout()
        apply_publication_layout(fig, ax, spec, style)

    meta = base_metadata(spec, style, work, used_columns=[x, y, color_by])
    meta["error_method"] = error_method
    meta["series"] = [f"{c}, {st}" if st is not None else str(c) for c, st in series if c is not None]
    meta["style_by"] = style_by
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
