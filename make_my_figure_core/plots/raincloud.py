"""Raincloud plot: half-violin (cloud) + box summary + raw points (rain).

Combines three complementary views of a distribution per group — a density
"cloud" (half-violin), a compact box summary, and the raw jittered points —
so the reader sees the shape, the summary, and the individual observations at
once. Reuses matplotlib's violinplot/boxplot; points use the shared jitter.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots._v04_shared import jitter, ordered_unique
from make_my_figure_core.plots.base import (
    autorotate_xticklabels,
    RenderResult,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    require_columns,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "raincloud_plot"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)

    require_columns(df, [x, y], context=PLOT_TYPE)
    work = df.copy()
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)

    groups = ordered_unique(work[x].tolist())
    warnings: List[str] = []
    if len(groups) > 6:
        warnings.append("Raincloud reads best with <=6 groups; consider faceting for more.")

    per_group = []
    for g in groups:
        vals = work[work[x] == g][y].to_numpy(float)
        per_group.append(vals[np.isfinite(vals)])

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.72))
        for gi, vals in enumerate(per_group):
            if vals.size == 0:
                continue
            col = style.color_for(gi)
            # (a) Cloud: half-violin shifted to the right of the group position.
            if vals.size > 1 and np.ptp(vals) > 0:
                vp = ax.violinplot([vals], positions=[gi + 0.05], widths=0.9,
                                   showextrema=False, showmeans=False, showmedians=False)
                for body in vp["bodies"]:
                    # Clip to the right half only (the "cloud").
                    verts = body.get_paths()[0].vertices
                    verts[:, 0] = np.clip(verts[:, 0], gi + 0.05, None)
                    body.set_facecolor(col)
                    body.set_edgecolor(col)
                    body.set_alpha(0.35)
            # (b) Box summary just left of center.
            bp = ax.boxplot([vals], positions=[gi - 0.12], widths=0.14, patch_artist=True,
                            showfliers=False, medianprops=dict(color=style.text_color,
                                                               linewidth=style.line_width_pt))
            for patch in bp["boxes"]:
                patch.set_facecolor("white")
                patch.set_edgecolor(col)
                patch.set_linewidth(style.spine_width_pt)
            for element in ("whiskers", "caps"):
                for artist in bp[element]:
                    artist.set_color(col)
                    artist.set_linewidth(style.spine_width_pt)
            # (c) Rain: raw points jittered to the left.
            dx = jitter(vals.size, width=0.07, seed=gi + 1)
            ax.scatter(gi - 0.28 + dx, vals, color=col, s=max(8.0, style.marker_size * 0.5),
                       edgecolors="white", linewidths=style.marker_edge_width * 0.7,
                       alpha=style.marker_alpha, zorder=3)

        ax.set_xticks(range(len(groups)))
        ax.set_xticklabels([str(g) for g in groups])
        autorotate_xticklabels(ax, style, rotation=get_mapping(spec, "x_tick_rotation", "auto"))
        ax.set_xlim(-0.6, len(groups) - 0.15)
        ax.set_xlabel(spec.get("layout", {}).get("x_label", str(x)))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", str(y)))
        ax.margins(y=0.08)
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[x, y])
    meta["n_groups"] = len(groups)
    meta["components"] = ["half_violin", "box", "raw_points"]
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
