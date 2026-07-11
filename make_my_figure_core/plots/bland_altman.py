"""Bland-Altman plot: agreement between two measurement methods.

For each paired observation, x = mean of the two methods, y = their difference
(A - B). Draws the mean bias and the 95% limits of agreement
(bias +/- 1.96 * SD of the differences). Optionally shades the 95% confidence
interval of the mean bias.
"""

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
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "bland_altman_plot"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    a = get_mapping(spec, "method_a", required=True, context=PLOT_TYPE)
    b = get_mapping(spec, "method_b", required=True, context=PLOT_TYPE)
    label_col = get_mapping(spec, "label", None)
    show_ci = bool(get_mapping(spec, "show_ci", False))

    require_columns(df, [a, b], context=PLOT_TYPE)
    work = df.copy()
    av = coerce_numeric(work, a, context=PLOT_TYPE).to_numpy(float)
    bv = coerce_numeric(work, b, context=PLOT_TYPE).to_numpy(float)
    mask = np.isfinite(av) & np.isfinite(bv)
    av, bv = av[mask], bv[mask]
    means = (av + bv) / 2.0
    diffs = av - bv

    n = int(diffs.size)
    bias = float(np.mean(diffs)) if n else float("nan")
    sd = float(np.std(diffs, ddof=1)) if n > 1 else 0.0
    loa_upper = bias + 1.96 * sd
    loa_lower = bias - 1.96 * sd
    warnings: List[str] = []

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.72))
        ax.scatter(means, diffs, color=style.color_for(0), s=style.marker_size,
                   edgecolors="white", linewidths=style.marker_edge_width,
                   alpha=style.marker_alpha, zorder=3)

        if show_ci and n > 1:
            ci = 1.96 * sd / np.sqrt(n)
            ax.axhspan(bias - ci, bias + ci, color=style.color_for(0), alpha=0.12, zorder=1)

        ax.axhline(bias, color=style.text_color, lw=style.line_width_pt, zorder=2)
        for loa, name in ((loa_upper, "+1.96 SD"), (loa_lower, "-1.96 SD")):
            ax.axhline(loa, color=style.color_for(1), lw=style.line_width_pt,
                       ls="--", zorder=2)

        # Right-edge annotations for the reference lines.
        xmax = float(np.nanmax(means)) if n else 1.0
        xmin = float(np.nanmin(means)) if n else 0.0
        xr = xmax + 0.02 * (xmax - xmin or 1.0)
        for yval, txt in ((bias, f"bias {bias:.3g}"),
                          (loa_upper, f"+1.96 SD {loa_upper:.3g}"),
                          (loa_lower, f"-1.96 SD {loa_lower:.3g}")):
            ax.annotate(txt, xy=(xr, yval), ha="right", va="bottom",
                        fontsize=style.annotation_pt, color=style.text_color)

        if label_col and label_col in work.columns:
            labels = work.loc[mask, label_col].astype(str).to_numpy()
            for mx, dy, txt in zip(means, diffs, labels):
                if txt and txt.lower() != "nan":
                    ax.annotate(txt, (mx, dy), fontsize=style.annotation_pt,
                                xytext=(3, 3), textcoords="offset points")

        ax.set_xlabel(spec.get("layout", {}).get("x_label", "Mean of methods"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", f"Difference ({a} - {b})"))
        ax.margins(0.08)
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[a, b, label_col])
    meta.update({"bias": bias, "sd_diff": sd, "loa_upper": loa_upper,
                 "loa_lower": loa_lower, "n": n})
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
