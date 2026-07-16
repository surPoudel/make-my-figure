"""Lollipop mutation plot: stem + marker at each protein position.

Publication-style layout: wide aspect, thin stems with clear marker edges,
markers scaled by mutation/sample count, the mutation-type legend placed
*outside* the axes (right or bottom), and top-N mutation labels drawn above the
markers with a vertical margin and simple collision-avoidance staggering so they
never touch markers or get clipped.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

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

PLOT_TYPE = "lollipop_mutation_plot"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", "protein_position")
    y = get_mapping(spec, "y", "sample_count")
    color_by = get_mapping(spec, "color", None)
    label_col = get_mapping(spec, "label", None)
    show_labels = bool(get_mapping(spec, "show_labels", True))
    label_top_n = int(get_mapping(spec, "label_top_n", get_mapping(spec, "max_labels", 6)))
    legend_loc = str(get_mapping(spec, "legend_loc", "right")).lower()
    marker_scale = float(get_mapping(spec, "marker_scale", 16.0))
    y_margin = float(get_mapping(spec, "y_margin", 0.42))

    require_columns(df, [x, y], context=PLOT_TYPE)
    work = df.copy()
    work[x] = coerce_numeric(work, x, context=PLOT_TYPE)
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)
    work = work.dropna(subset=[x, y]).sort_values(x)

    if color_by and color_by in work.columns:
        types = list(dict.fromkeys(work[color_by].astype(str).tolist()))
        color_map = {t: style.color_for(i) for i, t in enumerate(types)}
        point_colors = [color_map[str(t)] for t in work[color_by]]
    else:
        color_map = None
        point_colors = [style.color_for(0)] * len(work)

    warnings: List[str] = []
    xs = work[x].to_numpy(dtype=float)
    ys = work[y].to_numpy(dtype=float)
    ymax = float(np.nanmax(ys)) if len(ys) else 1.0

    with style.apply():
        # Wide aspect suits a protein-position axis.
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.42))

        ax.vlines(xs, 0, ys, color="0.65", linewidth=style.line_width_pt, zorder=1)
        sizes = np.clip(ys * marker_scale, 25, 280)
        ax.scatter(xs, ys, s=sizes, c=point_colors, edgecolors="black",
                   linewidths=style.spine_width_pt, zorder=3, clip_on=False)
        ax.axhline(0, color="black", lw=style.line_width_pt)  # protein backbone

        # --- top-N labels above the markers, de-overlapped with leader lines -
        # Reserve headroom first, then repel the labels (adjustText) so many
        # close hits never overlap or clip — thin leaders tie each label to its
        # marker. Halo keeps them readable over stems/markers.
        head = y_margin + min(0.06 * max(0, label_top_n - 4), 0.5)
        ax.set_ylim(0, ymax * (1.0 + head))
        if show_labels and label_col and label_col in work.columns and label_top_n > 0:
            import matplotlib.patheffects as pe

            top = work.sort_values(y, ascending=False).head(label_top_n)
            label_fs = max(7, style.axis_font_pt - 1)
            base = ymax * 0.05
            texts = []
            for _, r in top.iterrows():
                txt = str(r[label_col]).strip()
                if not txt or txt.lower() == "nan":
                    continue
                texts.append(ax.text(r[x], r[y] + base, txt, fontsize=label_fs,
                                     ha="center", va="bottom", zorder=6,
                                     path_effects=[pe.withStroke(linewidth=2.0,
                                                                 foreground="white")]))
            try:
                from adjustText import adjust_text

                adjust_text(texts, ax=ax, only_move={"text": "xy"},
                            expand_text=(1.05, 1.3),
                            arrowprops=dict(arrowstyle="-", color="0.65", lw=0.6))
            except Exception:
                pass
        ax.set_xlim(xs.min() - 0.02 * (xs.max() - xs.min() or 1),
                    xs.max() + 0.02 * (xs.max() - xs.min() or 1))

        ax.set_xlabel(spec.get("layout", {}).get("x_label", "Protein position"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", y))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)

        # --- legend OUTSIDE the data area -----------------------------------
        if color_map is not None:
            handles = [Patch(facecolor=color_map[t], edgecolor="black", label=str(t))
                       for t in types]
            if legend_loc == "bottom":
                ax.legend(handles=handles, title=str(color_by), frameon=False,
                          loc="upper center", bbox_to_anchor=(0.5, -0.30),
                          ncol=min(len(types), 4))
                fig.subplots_adjust(left=0.1, right=0.97, top=0.92, bottom=0.36)
            else:  # right (default)
                ax.legend(handles=handles, title=str(color_by), frameon=False,
                          loc="center left", bbox_to_anchor=(1.02, 0.5))
                fig.subplots_adjust(left=0.1, right=0.78, top=0.92, bottom=0.16)
        else:
            fig.subplots_adjust(left=0.1, right=0.97, top=0.92, bottom=0.16)

    meta = base_metadata(spec, style, work, used_columns=[x, y, color_by, label_col])
    meta["n_positions"] = int(len(work))
    meta["labels_shown"] = int(min(label_top_n, len(work))) if show_labels else 0
    meta["legend_loc"] = legend_loc if color_map is not None else None
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
