"""Spider plot: one line per subject tracking a value over time.

Common in oncology for per-patient longitudinal change (e.g. percent change in
tumor burden). This is the clinical "spider plot" — a line-per-subject time
series, not a radar/web chart. Optionally colored by response/treatment group,
with a reference line (default 0% change).
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots._v04_shared import ordered_unique
from make_my_figure_core.plots.base import (
    RenderResult,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    place_legend,
    require_columns,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "spider_plot"

# Above this many subjects we stop drawing a per-subject legend (unreadable).
_MAX_SUBJECT_LEGEND = 10


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    subject = get_mapping(spec, "subject", required=True, context=PLOT_TYPE)
    time = get_mapping(spec, "time", required=True, context=PLOT_TYPE)
    value = get_mapping(spec, "value", required=True, context=PLOT_TYPE)
    group_col = get_mapping(spec, "group", None)
    reference = get_mapping(spec, "reference", 0.0)

    require_columns(df, [subject, time, value], context=PLOT_TYPE)
    work = df.copy()
    work[time] = coerce_numeric(work, time, context=PLOT_TYPE)
    work[value] = coerce_numeric(work, value, context=PLOT_TYPE)

    subjects = ordered_unique(work[subject].tolist())
    has_group = bool(group_col and group_col in work.columns)
    group_levels = ordered_unique(work[group_col].tolist()) if has_group else []
    gcolor = {g: style.color_for(i) for i, g in enumerate(group_levels)}
    warnings: List[str] = []

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.72))
        for si, subj in enumerate(subjects):
            sub = work[work[subject] == subj].sort_values(time)
            xs = sub[time].to_numpy(float)
            ys = sub[value].to_numpy(float)
            mask = np.isfinite(xs) & np.isfinite(ys)
            if mask.sum() < 1:
                continue
            if has_group:
                g = str(sub[group_col].iloc[0])
                color = gcolor.get(g, style.color_for(0))
                label = None
            else:
                color = style.color_for(si % 10)
                label = str(subj) if len(subjects) <= _MAX_SUBJECT_LEGEND else None
            ax.plot(xs[mask], ys[mask], color=color, lw=style.line_width_pt,
                    marker="o", markersize=np.sqrt(style.marker_size) * 0.7,
                    markeredgecolor="white", markeredgewidth=style.marker_edge_width,
                    alpha=0.9, zorder=3, label=label)

        # Reference line (default 0% change).
        if reference is not None:
            try:
                ref = float(reference)
                ax.axhline(ref, ls="--", lw=style.spine_width_pt, color="0.5", zorder=1)
            except (TypeError, ValueError):
                pass

        ax.set_xlabel(spec.get("layout", {}).get("x_label", str(time)))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", "Change (%)"))
        ax.margins(0.05)
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)

        if has_group:
            from matplotlib.lines import Line2D

            handles = [Line2D([0], [0], color=gcolor[g], lw=style.line_width_pt, label=str(g))
                       for g in group_levels]
            place_legend(ax, style, title=str(group_col), handles=handles,
                         labels=[str(g) for g in group_levels], force_outside=True)
        elif len(subjects) <= _MAX_SUBJECT_LEGEND:
            place_legend(ax, style, title=str(subject), force_outside=True)
        else:
            warnings.append(f"{len(subjects)} subjects: per-subject legend omitted for legibility.")
            fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[subject, time, value, group_col])
    meta["n_subjects"] = int(len(subjects))
    meta["groups"] = [str(g) for g in group_levels]
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
