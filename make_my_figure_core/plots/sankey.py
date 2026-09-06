"""Two-stage Sankey / alluvial flow diagram (matplotlib only).

Draws flow between a set of source categories and a set of target categories.
Node bar heights are proportional to the total flow through each node; ribbons
connecting them are proportional to each ``source -> target`` value and colored
by source.

TODO: v0.4 supports two-stage Sankey (source -> target) only; multi-stage
alluvial flows across three or more columns are planned for a future version.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots._v04_shared import ordered_unique
from make_my_figure_core.plots.base import (
    RenderError,
    RenderResult,
    base_metadata,
    coerce_numeric,
    get_mapping,
    require_columns,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "sankey_plot"

_NODE_W = 0.06
_GAP_FRAC = 0.03  # vertical gap between nodes as a fraction of total flow


def _ribbon(ax, x0, x1, a0, a1, b0, b1, color):
    """Fill a smooth S-curve band from left slice [a0,a1] to right slice [b0,b1]."""
    xs = np.linspace(x0, x1, 60)
    u = (xs - x0) / (x1 - x0)
    t = 3 * u ** 2 - 2 * u ** 3  # smoothstep
    top = a1 + (b1 - a1) * t
    bot = a0 + (b0 - a0) * t
    ax.fill_between(xs, bot, top, color=color, alpha=0.55, lw=0, zorder=2)


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    src = get_mapping(spec, "source", required=True, context=PLOT_TYPE)
    tgt = get_mapping(spec, "target", required=True, context=PLOT_TYPE)
    val = get_mapping(spec, "value", required=True, context=PLOT_TYPE)
    require_columns(df, [src, tgt, val], context=PLOT_TYPE)

    work = df.copy()
    work[val] = coerce_numeric(work, val, context=PLOT_TYPE)
    work = work[[src, tgt, val]].dropna()
    flows = work.groupby([src, tgt], sort=False)[val].sum().reset_index()
    if flows.empty:
        raise RenderError(f"{PLOT_TYPE}: no positive flows after aggregation.")

    sources = ordered_unique(flows[src].tolist())
    targets = ordered_unique(flows[tgt].tolist())
    total = float(flows[val].sum())
    gap = total * _GAP_FRAC

    def _stack(nodes, key):
        totals = {n: float(flows[flows[key] == n][val].sum()) for n in nodes}
        height = total + gap * (len(nodes) - 1)
        y = height
        pos = {}
        for n in nodes:
            top = y
            bottom = y - totals[n]
            pos[n] = [bottom, top, bottom]  # [base, top, running-cursor]
            y = bottom - gap
        return totals, pos, height

    src_tot, src_pos, h_left = _stack(sources, src)
    tgt_tot, tgt_pos, h_right = _stack(targets, tgt)
    warnings: List[str] = []

    with style.apply():
        w_in, _ = style.figure_size_inches("double", aspect=0.7)
        fig, ax = plt.subplots(figsize=(max(w_in, 6.0), max(w_in * 0.62, 4.0)))

        # Node bars.
        for i, n in enumerate(sources):
            b, t, _ = src_pos[n]
            ax.fill_betweenx([b, t], 0.0, _NODE_W, color=style.color_for(i), zorder=4)
            ax.text(-0.02, (b + t) / 2, str(n), ha="right", va="center",
                    fontsize=style.tick_label_pt)
        for j, n in enumerate(targets):
            b, t, _ = tgt_pos[n]
            ax.fill_betweenx([b, t], 1.0 - _NODE_W, 1.0, color="#8C8C8C", zorder=4)
            ax.text(1.02, (b + t) / 2, str(n), ha="left", va="center",
                    fontsize=style.tick_label_pt)

        # Ribbons (ordered by source then target for stable stacking).
        for i, s in enumerate(sources):
            sub = flows[flows[src] == s]
            for _, r in sub.iterrows():
                v = float(r[val])
                if v <= 0:
                    continue
                a0 = src_pos[s][2]
                a1 = a0 + v
                src_pos[s][2] = a1
                b0 = tgt_pos[r[tgt]][2]
                b1 = b0 + v
                tgt_pos[r[tgt]][2] = b1
                _ribbon(ax, _NODE_W, 1.0 - _NODE_W, a0, a1, b0, b1, style.color_for(i))

        ax.set_xlim(-0.28, 1.28)
        ax.set_ylim(-gap, max(h_left, h_right) + gap)
        ax.axis("off")
        ax._colorbar = True  # flow diagram: no meaningful x/y labels
        title = spec.get("layout", {}).get("title", f"{src} → {tgt}")
        ax.set_title(title, fontsize=style.title_font_pt, fontweight=getattr(style, "title_font_weight", "bold"))

    meta = base_metadata(spec, style, work, used_columns=[src, tgt, val])
    meta.update({"n_sources": len(sources), "n_targets": len(targets), "total_flow": total})
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
