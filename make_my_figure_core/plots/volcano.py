"""Volcano plot for differential-analysis results.

x = log2 fold change, y = -log10(p). Points are colored by
up/down/non-significant given fold-change and p-value cutoffs. Optional
labels are drawn for the most significant labeled features.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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

PLOT_TYPE = "volcano_plot"

_NS_COLOR = "#B0B0B0"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", "log2_fold_change")
    p_col = get_mapping(spec, "p", None) or get_mapping(spec, "p_value", "p_value")
    label_col = get_mapping(spec, "label", None)
    lfc_cutoff = float(get_mapping(spec, "lfc_cutoff", 1.0))
    p_cutoff = float(get_mapping(spec, "p_cutoff", 0.05))
    max_labels = int(get_mapping(spec, "max_labels", 15))

    require_columns(df, [x, p_col], context=PLOT_TYPE)
    work = df.copy()
    work[x] = coerce_numeric(work, x, context=PLOT_TYPE)
    work[p_col] = coerce_numeric(work, p_col, context=PLOT_TYPE)

    warnings: List[str] = []
    # Guard against p == 0 (would be inf): clamp to smallest positive value.
    positive = work[p_col][work[p_col] > 0]
    floor = float(positive.min()) if not positive.empty else 1e-300
    pvals = work[p_col].clip(lower=floor)
    if (work[p_col] <= 0).any():
        warnings.append("Non-positive p-values clamped to the smallest positive value before -log10.")
    work = work.assign(_neglog10p=-np.log10(pvals))

    up = (work[x] >= lfc_cutoff) & (work[p_col] <= p_cutoff)
    down = (work[x] <= -lfc_cutoff) & (work[p_col] <= p_cutoff)
    ns = ~(up | down)

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.9))
        marker = dict(s=8, edgecolors="none", alpha=0.8)
        ax.scatter(work.loc[ns, x], work.loc[ns, "_neglog10p"], color=_NS_COLOR,
                   label="n.s.", **marker)
        ax.scatter(work.loc[up, x], work.loc[up, "_neglog10p"], color=style.color_for(1),
                   label=f"Up (≥{lfc_cutoff})", **marker)
        ax.scatter(work.loc[down, x], work.loc[down, "_neglog10p"], color=style.color_for(0),
                   label=f"Down (≤-{lfc_cutoff})", **marker)

        ax.axvline(lfc_cutoff, ls="--", lw=style.spine_width_pt, color="0.4")
        ax.axvline(-lfc_cutoff, ls="--", lw=style.spine_width_pt, color="0.4")
        ax.axhline(-np.log10(p_cutoff), ls="--", lw=style.spine_width_pt, color="0.4")

        # Label the top significant features that carry a non-empty label.
        if label_col and label_col in work.columns:
            sig = work[(up | down)].copy()
            sig = sig[sig[label_col].astype(str).str.strip().ne("")
                      & sig[label_col].notna()]
            sig = sig.sort_values("_neglog10p", ascending=False).head(max_labels)
            for _, row in sig.iterrows():
                ax.annotate(str(row[label_col]), (row[x], row["_neglog10p"]),
                            fontsize=style.axis_font_pt - 1, xytext=(2, 2),
                            textcoords="offset points")

        ax.set_xlabel(spec.get("layout", {}).get("x_label", "log2 fold change"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", "-log10(p)"))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        ax.legend(frameon=False, loc="best", markerscale=1.5)
        style_axes(ax)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[x, p_col, label_col])
    meta["lfc_cutoff"] = lfc_cutoff
    meta["p_cutoff"] = p_cutoff
    meta["n_up"] = int(up.sum())
    meta["n_down"] = int(down.sum())
    meta["n_ns"] = int(ns.sum())
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
