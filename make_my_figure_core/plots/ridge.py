"""Ridge / density plot: stacked KDEs per group, vertically offset."""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots.base import (
    RenderError,
    RenderResult,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    require_columns,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "ridge_or_density_plot"


def _kde(values: np.ndarray, grid: np.ndarray):
    from scipy.stats import gaussian_kde

    return gaussian_kde(values)(grid)


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    group = get_mapping(spec, "group", None)
    overlap = float(get_mapping(spec, "overlap", 0.7))

    require_columns(df, [x], context=PLOT_TYPE)
    work = df.copy()
    work[x] = coerce_numeric(work, x, context=PLOT_TYPE)

    if group and group in work.columns:
        groups: List[Any] = list(dict.fromkeys(work[group].tolist()))
    else:
        groups = ["all"]
        group = None

    warnings: List[str] = []
    allx = work[x].dropna().to_numpy()
    if allx.size == 0:
        raise RenderError(f"{PLOT_TYPE}: no numeric values in '{x}'.")
    grid = np.linspace(float(np.min(allx)), float(np.max(allx)), 256)

    densities = []
    for g in groups:
        vals = (work if group is None else work[work[group] == g])[x].dropna().to_numpy()
        if vals.size < 2 or np.ptp(vals) == 0:
            densities.append(None)
            warnings.append(f"Group '{g}' has too few/constant values for a density estimate.")
            continue
        d = _kde(vals, grid)
        densities.append(d)

    valid = [d for d in densities if d is not None]
    max_d = max((d.max() for d in valid), default=1.0)
    step = max_d * (1.0 - overlap)

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.9))
        yticks, yticklabels = [], []
        n = len(groups)
        for i, (g, d) in enumerate(zip(groups, densities)):
            baseline = (n - 1 - i) * step  # top group plotted highest
            yticks.append(baseline)
            yticklabels.append(str(g))
            if d is None:
                continue
            col = style.color_for(i)
            ax.fill_between(grid, baseline, baseline + d, color=col, alpha=0.6,
                            linewidth=style.spine_width_pt, edgecolor="black", zorder=n - i)
            ax.plot(grid, baseline + d, color="black", lw=style.spine_width_pt, zorder=n - i)

        ax.set_yticks(yticks)
        ax.set_yticklabels(yticklabels)
        ax.set_xlabel(spec.get("layout", {}).get("x_label", x))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", str(group) if group else ""))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax)
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[x, group])
    meta["groups"] = [str(g) for g in groups]
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
