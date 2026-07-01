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
    dedupe_labels_by_distance,
    figure_size,
    get_mapping,
    place_legend,
    require_columns,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "volcano_plot"

# Strong, colorblind-aware volcano colors (down=blue, up=red, n.s.=grey).
_NS_COLOR = "#BBBBBB"
_DOWN_COLOR = "#2166AC"
_UP_COLOR = "#B2182B"


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
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.85))
        sig_size = max(22.0, style.marker_size * 0.6)
        ns_size = max(12.0, style.marker_size * 0.32)
        ax.scatter(work.loc[ns, x], work.loc[ns, "_neglog10p"], color=_NS_COLOR,
                   label="n.s.", s=ns_size, edgecolors="none", alpha=0.6, zorder=1)
        ax.scatter(work.loc[down, x], work.loc[down, "_neglog10p"], color=_DOWN_COLOR,
                   label=f"Down (≤ -{lfc_cutoff:g})", s=sig_size, edgecolors="white",
                   linewidths=0.4, alpha=0.95, zorder=3)
        ax.scatter(work.loc[up, x], work.loc[up, "_neglog10p"], color=_UP_COLOR,
                   label=f"Up (≥ {lfc_cutoff:g})", s=sig_size, edgecolors="white",
                   linewidths=0.4, alpha=0.95, zorder=3)

        thr_lw = max(0.8, style.spine_width_pt * 0.8)
        ax.axvline(lfc_cutoff, ls="--", lw=thr_lw, color="0.5", zorder=0)
        ax.axvline(-lfc_cutoff, ls="--", lw=thr_lw, color="0.5", zorder=0)
        ax.axhline(-np.log10(p_cutoff), ls="--", lw=thr_lw, color="0.5", zorder=0)

        # Extra top headroom so labels are not clipped.
        ymax = float(work["_neglog10p"].max())
        ax.set_ylim(0, ymax * 1.18)

        # Label top significant features, dropping ones that collide.
        n_labeled = 0
        if label_col and label_col in work.columns:
            sig = work[(up | down)].copy()
            sig = sig[sig[label_col].astype(str).str.strip().ne("") & sig[label_col].notna()]
            sig = sig.sort_values("_neglog10p", ascending=False).head(max_labels)
            xr = (work[x].max() - work[x].min()) or 1.0
            pts = [(float(r[x]), float(r["_neglog10p"]), str(r[label_col]))
                   for _, r in sig.iterrows()]
            kept = dedupe_labels_by_distance(pts, min_dx=xr * 0.06, min_dy=ymax * 0.05)
            for lx, ly, txt in kept:
                ax.annotate(txt, (lx, ly), fontsize=style.annotation_pt,
                            xytext=(3, 3), textcoords="offset points", zorder=4)
            n_labeled = len(kept)

        ax.set_xlabel(spec.get("layout", {}).get("x_label", "log$_2$ fold change"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", "-log$_{10}$(p)"))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)
        place_legend(ax, style, force_outside=True)
        # markerscale so legend dots read clearly
        leg = ax.get_legend()
        if leg is not None:
            for h in leg.legend_handles:
                try:
                    h.set_sizes([40])
                except Exception:
                    pass

    meta = base_metadata(spec, style, work, used_columns=[x, p_col, label_col])
    meta["lfc_cutoff"] = lfc_cutoff
    meta["p_cutoff"] = p_cutoff
    meta["n_up"] = int(up.sum())
    meta["n_down"] = int(down.sum())
    meta["n_ns"] = int(ns.sum())
    meta["n_labeled"] = n_labeled
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
