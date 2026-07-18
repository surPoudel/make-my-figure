"""Swimmer plot: one horizontal timeline bar per patient.

Common in oncology to show time on treatment / follow-up per subject, sorted by
duration, optionally colored by a group (e.g. response category) with event
markers (progression, response, death, censoring, ...) drawn at the bar end.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots._v04_shared import ordered_unique
from make_my_figure_core.plots.base import (
    RenderError,
    RenderResult,
    apply_publication_layout,
    base_metadata,
    coerce_numeric,
    get_mapping,
    place_legend,
    require_columns,
    resolve_legend_location,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "swimmer_plot"

# Distinct marker glyphs cycled per event type.
_EVENT_MARKERS = ["*", "^", "v", "s", "D", "P", "X", "o"]


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    subject = get_mapping(spec, "subject", required=True, context=PLOT_TYPE)
    start_col = get_mapping(spec, "start", None)
    end_col = get_mapping(spec, "end", None)
    duration_col = get_mapping(spec, "duration", None)
    group_col = get_mapping(spec, "group", None)
    event_col = get_mapping(spec, "event", None)

    require_columns(df, [subject], context=PLOT_TYPE)
    work = df.copy()
    warnings: List[str] = []

    # Resolve the timeline start/end for every subject.
    if start_col and start_col in work.columns:
        start = coerce_numeric(work, start_col, context=PLOT_TYPE).to_numpy(float)
    else:
        start = np.zeros(len(work))
    if end_col and end_col in work.columns:
        end = coerce_numeric(work, end_col, context=PLOT_TYPE).to_numpy(float)
    elif duration_col and duration_col in work.columns:
        end = start + coerce_numeric(work, duration_col, context=PLOT_TYPE).to_numpy(float)
    else:
        raise RenderError(
            f"{PLOT_TYPE}: provide an 'end' time column or a 'duration' column "
            "(with an optional 'start'; start defaults to 0).")

    subjects = work[subject].astype(str).to_numpy()
    groups = work[group_col].astype(str).to_numpy() if (group_col and group_col in work.columns) else None

    # One row per subject: aggregate to the min start / max end if duplicated.
    order_idx = np.arange(len(work))
    # Sort by group then by duration (short bars on top reads cleanly bottom-up).
    duration = end - start
    if groups is not None:
        sort_key = list(zip(groups, duration))
    else:
        sort_key = list(zip([""] * len(work), duration))
    order_idx = sorted(order_idx, key=lambda i: (sort_key[i][0], sort_key[i][1]))

    n = len(order_idx)
    y_pos = np.arange(n)
    group_levels = ordered_unique(groups.tolist()) if groups is not None else []
    gcolor = {g: style.color_for(i) for i, g in enumerate(group_levels)}

    # Font/size scaling so many patients stay legible (ticks kept >= 8 pt).
    tick_fs = style.tick_label_pt if n <= 25 else max(8.0, style.tick_label_pt - 2)
    w_in, _ = style.figure_size_inches(
        str(spec.get("layout", {}).get("column_width", "default")).lower(), aspect=1.0)
    h_in = max(2.4, min(22.0, 0.30 * n + 1.2))

    event_levels: List[str] = []
    if event_col and event_col in work.columns:
        event_levels = ordered_unique(work[event_col].tolist())

    with style.apply():
        fig, ax = plt.subplots(figsize=(w_in, h_in))
        for row, i in enumerate(order_idx):
            g = groups[i] if groups is not None else None
            color = gcolor.get(g, style.color_for(0))
            ax.barh(row, duration[i], left=start[i], height=0.62, color=color,
                    edgecolor=style.text_color, linewidth=style.spine_width_pt * 0.6, zorder=2)
        # Event markers at each subject's bar end.
        if event_levels:
            events = work[event_col].astype(str).to_numpy()
            for ei, ev in enumerate(event_levels):
                mk = _EVENT_MARKERS[ei % len(_EVENT_MARKERS)]
                xs, ys = [], []
                for row, i in enumerate(order_idx):
                    if events[i] == str(ev):
                        xs.append(end[i]); ys.append(row)
                if xs:
                    ax.scatter(xs, ys, marker=mk, s=style.marker_size * 1.2,
                               facecolor=style.text_color, edgecolor="white",
                               linewidths=style.marker_edge_width, zorder=4, label=f"event: {ev}")

        ax.set_yticks(y_pos)
        ax.set_yticklabels([subjects[i] for i in order_idx], fontsize=tick_fs)
        ax.set_ylim(-0.7, n - 0.3)
        ax.set_xlabel(spec.get("layout", {}).get("x_label", "Time (months)"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", "Patient"))
        ax.margins(x=0.02)
        # Extra right-side headroom so ongoing-arrows and end-of-follow-up event
        # markers are not clipped at the axes edge (user-adjustable).
        _x0, _x1 = ax.get_xlim()
        _rpad = float(get_mapping(spec, "right_pad_frac", 0.06) or 0.0)
        if _x1 > _x0 and _rpad > 0:
            ax.set_xlim(_x0, _x1 + (_x1 - _x0) * _rpad)
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)

        # Combined legend (group patches + event markers) outside the axes.
        from matplotlib.lines import Line2D
        from matplotlib.patches import Patch

        handles: List[Any] = []
        if group_levels:
            handles += [Patch(facecolor=gcolor[g], edgecolor=style.text_color, label=str(g))
                        for g in group_levels]
        if event_levels:
            handles += [Line2D([0], [0], marker=_EVENT_MARKERS[ei % len(_EVENT_MARKERS)],
                               color="none", markerfacecolor=style.text_color,
                               markeredgecolor="white", markersize=9, label=f"event: {ev}")
                        for ei, ev in enumerate(event_levels)]
        if handles:
            title_txt = str(group_col) if group_levels else "Event"
            place_legend(ax, style, title=title_txt, handles=handles,
                         labels=[h.get_label() for h in handles],
                         location=resolve_legend_location(spec, style)
                         if spec.get("layout", {}).get("legend_location") else None,
                         force_outside=not spec.get("layout", {}).get("legend_location"))
        else:
            fig.tight_layout()
        apply_publication_layout(fig, ax, spec, style)

    meta = base_metadata(spec, style, work,
                         used_columns=[subject, start_col, end_col, duration_col, group_col, event_col])
    meta["n_subjects"] = int(n)
    meta["groups"] = [str(g) for g in group_levels]
    meta["event_types"] = [str(e) for e in event_levels]
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
