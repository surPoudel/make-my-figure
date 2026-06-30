"""Box or violin plot with overlaid jittered points."""

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

PLOT_TYPE = "boxplot_or_violin_with_points"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    kind = str(get_mapping(spec, "kind", "box")).lower()
    show_points = bool(get_mapping(spec, "points", True))

    require_columns(df, [x, y], context=PLOT_TYPE)
    work = df.copy()
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)

    groups: List[Any] = list(dict.fromkeys(work[x].tolist()))
    data = [work.loc[work[x] == g, y].dropna().to_numpy() for g in groups]
    positions = list(range(1, len(groups) + 1))
    warnings: List[str] = []

    # Deterministic jitter so previews are reproducible.
    rng = np.random.default_rng(42)

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.8))
        if kind == "violin":
            parts = ax.violinplot(data, positions=positions, showmeans=False,
                                  showmedians=True, showextrema=False)
            for i, body in enumerate(parts["bodies"]):
                body.set_facecolor(style.color_for(i))
                body.set_alpha(0.45)
                body.set_edgecolor("black")
                body.set_linewidth(style.spine_width_pt)
            if "cmedians" in parts:
                parts["cmedians"].set_color("black")
                parts["cmedians"].set_linewidth(style.line_width_pt)
        else:
            kind = "box"
            bp = ax.boxplot(data, positions=positions, widths=0.5, patch_artist=True,
                            showfliers=not show_points,
                            medianprops={"color": "black", "linewidth": style.line_width_pt})
            for i, box in enumerate(bp["boxes"]):
                box.set_facecolor(style.color_for(i))
                box.set_alpha(0.5)
                box.set_edgecolor("black")
                box.set_linewidth(style.spine_width_pt)
            for element in ("whiskers", "caps"):
                for artist in bp[element]:
                    artist.set_color("black")
                    artist.set_linewidth(style.spine_width_pt)

        if show_points:
            for i, vals in enumerate(data):
                jitter = rng.uniform(-0.12, 0.12, size=len(vals))
                ax.scatter(np.full(len(vals), positions[i]) + jitter, vals,
                           s=8, color=style.color_for(i), edgecolors="black",
                           linewidths=0.2, alpha=0.8, zorder=3)

        ax.set_xticks(positions)
        ax.set_xticklabels([str(g) for g in groups])
        ax.set_xlabel(spec.get("layout", {}).get("x_label", x))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", y))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[x, y])
    meta["kind"] = kind
    meta["groups"] = [str(g) for g in groups]
    meta["group_n"] = {str(g): int(len(d)) for g, d in zip(groups, data)}
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
