"""Volcano plot for differential-analysis results.

x = log2 fold change, y = -log10(p or adjusted p). Points are colored Up / Down /
Not significant. Classification either comes from a precomputed ``class_col``
(so the figure matches the DE result's own thresholds exactly) or is derived from
fold-change and p-value cutoffs. Labels are drawn for the most significant and/or
explicitly selected features, with overlap avoidance (``adjustText`` when present,
otherwise a distance-based fallback). p-values are read from the table, never
recomputed.
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


def _repel_labels(ax, points, style, *, warnings):
    """Draw point labels with overlap avoidance.

    Uses ``adjustText`` when installed; otherwise a greedy distance-based
    de-collision (never fails the render).
    """
    texts = []
    for lx, ly, txt in points:
        texts.append(ax.text(lx, ly, txt, fontsize=style.annotation_pt, zorder=5))
    try:
        from adjustText import adjust_text  # type: ignore

        adjust_text(texts, ax=ax,
                    arrowprops=dict(arrowstyle="-", color="0.5", lw=0.5),
                    expand_points=(1.2, 1.4))
        return len(texts)
    except Exception:
        # Fallback: remove the naive texts and place distance-deduped offsets.
        for t in texts:
            t.remove()
        for lx, ly, txt in points:
            ax.annotate(txt, (lx, ly), fontsize=style.annotation_pt,
                        xytext=(3, 3), textcoords="offset points", zorder=5)
        return len(points)


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", "log2_fold_change")
    p_col = get_mapping(spec, "p", None) or get_mapping(spec, "p_value", "p_value")
    label_col = get_mapping(spec, "label", None)
    class_col = get_mapping(spec, "class_col", None)
    lfc_cutoff = float(get_mapping(spec, "lfc_cutoff", 1.0))
    p_cutoff = float(get_mapping(spec, "p_cutoff", 0.05))
    max_labels = int(get_mapping(spec, "max_labels", 15))
    label_sig_only = bool(get_mapping(spec, "label_significant_only", True))
    selected_labels = get_mapping(spec, "selected_labels", None) or []

    require_columns(df, [x, p_col], context=PLOT_TYPE)
    work = df.copy()
    work[x] = coerce_numeric(work, x, context=PLOT_TYPE)
    work[p_col] = coerce_numeric(work, p_col, context=PLOT_TYPE)

    warnings: List[str] = []
    positive = work[p_col][work[p_col] > 0]
    floor = float(positive.min()) if not positive.empty else 1e-300
    pvals = work[p_col].clip(lower=floor)
    if (work[p_col] <= 0).any():
        warnings.append("Non-positive p-values clamped to the smallest positive value before -log10.")
    work = work.assign(_neglog10p=-np.log10(pvals))

    # Classification: prefer a precomputed class column (keeps the figure aligned
    # with the DE result's own thresholds); otherwise derive from the cutoffs.
    if class_col and class_col in work.columns:
        cls = work[class_col].astype(str)
        up = cls.eq("Up")
        down = cls.eq("Down")
    else:
        up = (work[x] >= lfc_cutoff) & (work[p_col] <= p_cutoff)
        down = (work[x] <= -lfc_cutoff) & (work[p_col] <= p_cutoff)
    ns = ~(up | down)

    selected_set = {str(s).strip().lower() for s in selected_labels}

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.85))
        sig_size = max(22.0, style.marker_size * 0.6)
        ns_size = max(12.0, style.marker_size * 0.32)
        ax.scatter(work.loc[ns, x], work.loc[ns, "_neglog10p"], color=_NS_COLOR,
                   label="n.s.", s=ns_size, edgecolors="none", alpha=0.55, zorder=1)
        ax.scatter(work.loc[down, x], work.loc[down, "_neglog10p"], color=_DOWN_COLOR,
                   label=f"Down (n={int(down.sum())})", s=sig_size, edgecolors="white",
                   linewidths=0.4, alpha=0.95, zorder=3)
        ax.scatter(work.loc[up, x], work.loc[up, "_neglog10p"], color=_UP_COLOR,
                   label=f"Up (n={int(up.sum())})", s=sig_size, edgecolors="white",
                   linewidths=0.4, alpha=0.95, zorder=3)

        thr_lw = max(0.8, style.spine_width_pt * 0.8)
        ax.axvline(lfc_cutoff, ls="--", lw=thr_lw, color="0.5", zorder=0)
        ax.axvline(-lfc_cutoff, ls="--", lw=thr_lw, color="0.5", zorder=0)
        ax.axhline(-np.log10(p_cutoff), ls="--", lw=thr_lw, color="0.5", zorder=0)

        ymax = float(work["_neglog10p"].max()) if len(work) else 1.0
        ax.set_ylim(0, ymax * 1.18)

        # Labels: explicit selected genes always; otherwise top significant.
        n_labeled = 0
        if label_col and label_col in work.columns:
            xr = (work[x].max() - work[x].min()) or 1.0
            pts: List = []
            if selected_set:
                sel = work[work[label_col].astype(str).str.strip().str.lower().isin(selected_set)]
                pts += [(float(r[x]), float(r["_neglog10p"]), str(r[label_col]))
                        for _, r in sel.iterrows()]
            pool = work[(up | down)] if label_sig_only else work
            pool = pool[pool[label_col].astype(str).str.strip().ne("") & pool[label_col].notna()]
            pool = pool.sort_values("_neglog10p", ascending=False).head(max_labels)
            extra = [(float(r[x]), float(r["_neglog10p"]), str(r[label_col]))
                     for _, r in pool.iterrows()]
            # merge, keeping selected first, then dedupe by distance
            seen_txt = {t for _, _, t in pts}
            for p in extra:
                if p[2] not in seen_txt:
                    pts.append(p)
            kept = dedupe_labels_by_distance(pts, min_dx=xr * 0.05, min_dy=ymax * 0.04)
            n_labeled = _repel_labels(ax, kept, style, warnings=warnings)

        ax.set_xlabel(spec.get("layout", {}).get("x_label", "log$_2$ fold change"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", "-log$_{10}$(p)"))
        title = spec.get("layout", {}).get("title")
        subtitle = spec.get("layout", {}).get("subtitle")
        if title and subtitle:
            ax.set_title(title + "\n" + subtitle, fontsize=style.title_font_pt)
            # shrink the subtitle line
            ax.title.set_fontsize(style.title_font_pt)
        elif title:
            ax.set_title(title)
        elif subtitle:
            ax.set_title(subtitle, fontsize=max(9.0, style.annotation_pt))
        style_axes(ax, style)
        place_legend(ax, style, force_outside=True)
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
    meta["classified_from"] = "class_col" if (class_col and class_col in work.columns) else "cutoffs"
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
