"""Central statistical-annotation layout engine for renderers.

Renderers must not reinvent bracket placement. They:

1. compute per-category x positions and a "data top" per category,
2. hand the list of :class:`AnnotationItem` objects + a position lookup here,

and this module draws non-overlapping significance brackets (auto-stacked),
places the p-value/star text, and expands the y-axis so nothing is clipped. It
also renders corner text panels for correlation/survival/omnibus stats.

Every label drawn here comes from an AnnotationItem, which is derived from a
stored StatResult - so no p-value is ever a decorative, unbacked label.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from make_my_figure_core.statistics.annotations import AnnotationItem


def _data_top(ax) -> float:
    """Best estimate of the top of the drawn data in data coordinates."""
    ymin, ymax = ax.get_ylim()
    top = ymax
    # Consider explicit artists (bars, lines, collections) if available.
    try:
        dl = ax.dataLim
        if np.isfinite(dl.ymax):
            top = max(top, dl.ymax)
    except Exception:
        pass
    return top


def annotate_pairwise(
    ax,
    items: List[AnnotationItem],
    position_lookup: Callable[[AnnotationItem], Optional[Tuple[float, float]]],
    *,
    style,
    cfg: Dict[str, Any],
    top_lookup: Optional[Callable[[AnnotationItem], Optional[float]]] = None,
) -> Dict[str, Any]:
    """Draw significance brackets for pairwise comparison items.

    ``position_lookup`` maps an item to its ``(x_left, x_right)`` in data
    coordinates (or ``None`` to skip). ``top_lookup`` optionally maps an item to
    the y-value its bracket should clear (e.g. top of the two compared bars +
    error bars); when absent a shared data top is used.

    Returns a small dict describing how many brackets were drawn and the final
    top, for metadata.
    """
    cfg = cfg or {}
    ylim0, ylim1 = ax.get_ylim()
    yr = (ylim1 - ylim0) or 1.0
    tick_h = float(cfg.get("bracket_height_frac", 0.03)) * yr
    gap = float(cfg.get("gap_frac", 0.06)) * yr
    top_margin = float(cfg.get("top_margin_frac", 0.12))
    fs = cfg.get("font_size") or getattr(style, "annotation_pt", 9.5)
    lw = cfg.get("line_width") or getattr(style, "spine_width_pt", 1.1)
    text_color = getattr(style, "text_color", "#1a1a1a")

    # Resolve geometry for each drawable item.
    specs: List[Dict[str, Any]] = []
    base_top = _data_top(ax)
    for it in items:
        xs = position_lookup(it)
        if xs is None:
            continue
        x1, x2 = sorted(xs)
        local_top = base_top
        if top_lookup is not None:
            t = top_lookup(it)
            if t is not None and np.isfinite(t):
                local_top = t
        specs.append({"x1": x1, "x2": x2, "text": it.text, "start": local_top,
                      "sig": it.significant})

    if not specs:
        return {"n_brackets": 0, "top": ylim1}

    # Greedy leveling: assign each bracket the lowest level whose x-span does not
    # overlap an already-placed bracket at that level.
    specs.sort(key=lambda s: (s["x2"] - s["x1"], s["x1"]))
    levels: List[List[Tuple[float, float]]] = []
    for s in specs:
        placed = False
        for li, spans in enumerate(levels):
            if all(s["x2"] < a - 1e-9 or s["x1"] > b + 1e-9 for a, b in spans):
                spans.append((s["x1"], s["x2"]))
                s["level"] = li
                placed = True
                break
        if not placed:
            s["level"] = len(levels)
            levels.append([(s["x1"], s["x2"])])

    # Draw. Level height is relative to the max start among all brackets so a
    # cluster of stacked brackets shares a clean baseline.
    global_start = max(s["start"] for s in specs)
    line_step = tick_h + gap + 0.06 * yr
    max_y = ylim1
    for s in specs:
        y = global_start + gap + s["level"] * line_step
        y_tick = y + tick_h
        ax.plot([s["x1"], s["x1"], s["x2"], s["x2"]],
                [y, y_tick, y_tick, y], lw=lw, c=text_color,
                solid_capstyle="butt", clip_on=False, zorder=6)
        ax.text((s["x1"] + s["x2"]) / 2.0, y_tick + 0.01 * yr, s["text"],
                ha="center", va="bottom", fontsize=fs, color=text_color,
                zorder=7, clip_on=False)
        # Approximate text height allowance (2 lines max).
        text_lines = 1 + s["text"].count("\n")
        max_y = max(max_y, y_tick + (0.05 + 0.05 * text_lines) * yr)

    new_top = max(ylim1, max_y + top_margin * yr)
    ax.set_ylim(ylim0, new_top)
    return {"n_brackets": len(specs), "levels": len(levels), "top": new_top}


def annotate_corner(ax, lines: List[str], *, style, loc: str = "upper left",
                    fontsize: Optional[float] = None) -> None:
    """Place a small multi-line stats panel in a plot corner without overlap."""
    if not lines:
        return
    fs = fontsize or getattr(style, "annotation_pt", 9.5)
    text_color = getattr(style, "text_color", "#1a1a1a")
    positions = {
        "upper left": (0.03, 0.97, "left", "top"),
        "upper right": (0.97, 0.97, "right", "top"),
        "lower left": (0.03, 0.03, "left", "bottom"),
        "lower right": (0.97, 0.03, "right", "bottom"),
    }
    x, y, ha, va = positions.get(loc, positions["upper left"])
    ax.text(x, y, "\n".join(lines), transform=ax.transAxes, ha=ha, va=va,
            fontsize=fs, color=text_color,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.75),
            zorder=8)


def annotate_text_below_legend(ax, text: str, *, style, y: float = -0.02) -> None:
    """Place stats text just under the axes (e.g. log-rank p for survival)."""
    if not text:
        return
    fs = getattr(style, "annotation_pt", 9.5)
    ax.text(0.02, 0.04, text, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=fs, color=getattr(style, "text_color", "#1a1a1a"), zorder=8,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="0.8", alpha=0.85))
