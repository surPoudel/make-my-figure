"""Forest plot of point estimates with confidence intervals."""

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

PLOT_TYPE = "forest_plot"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    label_col = get_mapping(spec, "label", "subgroup")
    estimate_col = get_mapping(spec, "estimate", "hazard_ratio")
    lower_col = get_mapping(spec, "lower", "ci_low")
    upper_col = get_mapping(spec, "upper", "ci_high")
    reference = float(get_mapping(spec, "reference", 1.0))
    log_scale = bool(get_mapping(spec, "log_scale", True))

    require_columns(df, [label_col, estimate_col, lower_col, upper_col], context=PLOT_TYPE)
    work = df.copy()
    for c in (estimate_col, lower_col, upper_col):
        work[c] = coerce_numeric(work, c, context=PLOT_TYPE)
    work = work.dropna(subset=[estimate_col, lower_col, upper_col])

    labels = work[label_col].astype(str).tolist()
    est = work[estimate_col].to_numpy(dtype=float)
    lo = work[lower_col].to_numpy(dtype=float)
    hi = work[upper_col].to_numpy(dtype=float)
    # Plot first row at top.
    y_pos = np.arange(len(labels))[::-1]
    warnings: List[str] = []

    # Asymmetric error bar lengths relative to the estimate.
    xerr = np.vstack([np.maximum(est - lo, 0), np.maximum(hi - est, 0)])

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.7))
        ax.errorbar(est, y_pos, xerr=xerr, fmt="s", color=style.color_for(0),
                    ecolor="black", elinewidth=style.line_width_pt, capsize=2.5,
                    markersize=4, markeredgecolor="black", linestyle="none")
        ax.axvline(reference, ls="--", color="0.5", lw=style.spine_width_pt)
        if log_scale and np.all(est > 0) and np.all(lo > 0):
            ax.set_xscale("log")
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels)
        ax.set_xlabel(spec.get("layout", {}).get("x_label", estimate_col))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[label_col, estimate_col, lower_col, upper_col])
    meta["n_rows"] = int(len(labels))
    meta["reference"] = reference
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
