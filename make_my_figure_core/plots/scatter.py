"""Scatter plot with optional per-/overall regression line."""

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
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "scatterplot_with_regression"


def _fit_line(ax, xs: np.ndarray, ys: np.ndarray, color: str, style: StyleProfile):
    """Least-squares fit; returns (slope, intercept, r) or None if degenerate."""
    mask = ~(np.isnan(xs) | np.isnan(ys))
    xs, ys = xs[mask], ys[mask]
    if xs.size < 2 or np.ptp(xs) == 0:
        return None
    slope, intercept = np.polyfit(xs, ys, 1)
    xline = np.linspace(xs.min(), xs.max(), 100)
    ax.plot(xline, slope * xline + intercept, color=color, lw=style.line_width_pt)
    # Pearson r
    if ys.std() == 0:
        r = float("nan")
    else:
        r = float(np.corrcoef(xs, ys)[0, 1])
    return (float(slope), float(intercept), r)


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    color_by = get_mapping(spec, "color", None)
    fit_line = bool(get_mapping(spec, "fit_line", True))
    label_col = get_mapping(spec, "label", None)

    require_columns(df, [x, y], context=PLOT_TYPE)
    work = df.copy()
    work[x] = coerce_numeric(work, x, context=PLOT_TYPE)
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)

    fits: Dict[str, Any] = {}
    warnings: List[str] = []

    mk = dict(s=style.marker_size, edgecolors="white",
              linewidths=style.marker_edge_width, alpha=style.marker_alpha)
    has_groups = bool(color_by and color_by in work.columns)

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.78))

        if has_groups:
            groups = list(dict.fromkeys(work[color_by].tolist()))
            for gi, g in enumerate(groups):
                sub = work[work[color_by] == g]
                col = style.color_for(gi)
                ax.scatter(sub[x], sub[y], color=col, label=str(g), zorder=3, **mk)
                if fit_line:
                    fit = _fit_line(ax, sub[x].to_numpy(float), sub[y].to_numpy(float), col, style)
                    if fit:
                        fits[str(g)] = {"slope": fit[0], "intercept": fit[1], "pearson_r": fit[2]}
        else:
            col = style.color_for(0)
            ax.scatter(work[x], work[y], color=col, zorder=3, **mk)
            if fit_line:
                fit = _fit_line(ax, work[x].to_numpy(float), work[y].to_numpy(float), col, style)
                if fit:
                    fits["all"] = {"slope": fit[0], "intercept": fit[1], "pearson_r": fit[2]}

        # Optional point labels.
        if label_col and label_col in work.columns:
            for _, row in work.iterrows():
                txt = str(row[label_col]).strip()
                if txt and txt.lower() != "nan":
                    ax.annotate(txt, (row[x], row[y]), fontsize=style.annotation_pt,
                                xytext=(3, 3), textcoords="offset points")

        ax.set_xlabel(spec.get("layout", {}).get("x_label", x))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", y))
        ax.margins(0.05)
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)

        from make_my_figure_core.plots.stats_integration import run_and_annotate

        stats_report = run_and_annotate(spec, work, style, PLOT_TYPE, ax=ax,
                                        mode="corner", corner_loc="upper left")
        if has_groups:
            # Legend outside so it never sits on top of points.
            place_legend(ax, style, title=str(color_by), force_outside=True)
        else:
            fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[x, y, color_by, label_col])
    meta["fit_line"] = fit_line
    meta["regression"] = fits
    if stats_report is not None:
        meta["statistics_report"] = stats_report.to_dict()
    return RenderResult(figure=fig, metadata=meta, warnings=warnings,
                        stats_report=stats_report)
