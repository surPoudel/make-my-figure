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

    if color_by and color_by in work.columns:
        series = list(dict.fromkeys(work[color_by].tolist()))
    else:
        series = [None]
    warnings: List[str] = []

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.7))
        for si, s in enumerate(series):
            sub = work if s is None else work[work[color_by] == s]
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
            col = style.color_for(si)
            label = None if s is None else str(s)
            ax.plot(xs, means, color=col, lw=style.line_width_pt, label=label, marker="o",
                    markersize=3)
            if error_method.lower() != "none":
                ax.fill_between(xs, lows, highs, color=col, alpha=0.2, linewidth=0)

        ax.set_xlabel(spec.get("layout", {}).get("x_label", x))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", y))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        if series != [None]:
            ax.legend(title=str(color_by), frameon=False, loc="best")
        style_axes(ax, style)
        fig.tight_layout()
        apply_publication_layout(fig, ax, spec, style)

    meta = base_metadata(spec, style, work, used_columns=[x, y, color_by])
    meta["error_method"] = error_method
    meta["series"] = [str(s) for s in series if s is not None]
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
