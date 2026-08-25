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
    top_margin = float(cfg.get("top_margin_frac", 0.10))
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
        specs.append({"x1": x1, "x2": x2, "text": it.text, "start": local_top})

    if not specs:
        return {"n_brackets": 0, "top": ylim1}

    for s in specs:
        s["mid"] = 0.5 * (s["x1"] + s["x2"])

    # Set up a renderer so we can measure real label extents (width for
    # horizontal leveling, height for vertical stacking).
    fig = ax.figure
    measure = True
    renderer = None
    try:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        inv = ax.transData.inverted()
    except Exception:
        measure = False

    # Effective x-span of each bracket = max(bracket span, label width centered
    # on the midpoint), so a label wider than its bracket still forces a stagger.
    x0, x1lim = ax.get_xlim()
    xr = abs(x1lim - x0) or 1.0
    pad_x = 0.03 * xr
    fp = None
    if measure:
        try:
            from matplotlib.font_manager import FontProperties

            fp = FontProperties(size=fs)

            def _label_width_data(text):
                w_px, _, _ = renderer.get_text_width_height_descent(text, fp, False)
                xa = inv.transform((0.0, 0.0))[0]
                xb = inv.transform((float(w_px), 0.0))[0]
                return abs(xb - xa)
        except Exception:
            measure = False
    for s in specs:
        half = 0.5 * (s["x2"] - s["x1"])
        if measure:
            try:
                # multi-line: widest line. Inflate a little to absorb any minor
                # axes-geometry change (e.g. tight_layout) after measurement.
                lw_data = max(_label_width_data(ln) for ln in s["text"].split("\n"))
                half = max(half, 0.5 * lw_data * 1.12)
            except Exception:
                pass
        s["eff_x1"] = s["mid"] - half - pad_x
        s["eff_x2"] = s["mid"] + half + pad_x

    # Greedy leveling on the effective spans (narrowest first).
    specs.sort(key=lambda s: (s["eff_x2"] - s["eff_x1"], s["mid"]))
    levels: List[List[Tuple[float, float]]] = []
    for s in specs:
        placed = False
        for li, spans in enumerate(levels):
            if all(s["eff_x2"] < a - 1e-9 or s["eff_x1"] > b + 1e-9 for a, b in spans):
                spans.append((s["eff_x1"], s["eff_x2"]))
                s["level"] = li
                placed = True
                break
        if not placed:
            s["level"] = len(levels)
            levels.append([(s["eff_x1"], s["eff_x2"])])
    n_levels = len(levels)

    # Expand the y-axis FIRST (generously) so the drawing transform is fixed
    # while we place and measure labels.
    n_lines = max((1 + s["text"].count("\n")) for s in specs)
    est_level = tick_h + gap + n_lines * 0.06 * yr
    global_start = max(s["start"] for s in specs)
    pre_top = max(ylim1, global_start + n_levels * est_level * 1.35 + top_margin * yr)
    ax.set_ylim(ylim0, pre_top)

    if measure:
        try:
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            inv = ax.transData.inverted()

            def _disp_top_to_data(txt):
                bb = txt.get_window_extent(renderer=renderer)
                return inv.transform((bb.x0, bb.y1))[1]
        except Exception:
            measure = False

    by_level: Dict[int, List[Dict[str, Any]]] = {}
    for s in specs:
        by_level.setdefault(s["level"], []).append(s)

    current_base = global_start + gap
    max_y = current_base
    for lvl in sorted(by_level):
        y = current_base
        y_tick = y + tick_h
        level_tops = []
        for s in by_level[lvl]:
            ax.plot([s["x1"], s["x1"], s["x2"], s["x2"]],
                    [y, y_tick, y_tick, y], lw=lw, c=text_color,
                    solid_capstyle="butt", clip_on=False, zorder=6)
            txt = ax.text((s["x1"] + s["x2"]) / 2.0, y_tick + 0.006 * yr, s["text"],
                          ha="center", va="bottom", fontsize=fs, color=text_color,
                          zorder=7, clip_on=False)
            if measure:
                try:
                    level_tops.append(_disp_top_to_data(txt))
                except Exception:
                    level_tops.append(y_tick + n_lines * 0.06 * yr)
            else:
                level_tops.append(y_tick + n_lines * 0.06 * yr)
        # Next level starts a gap above the tallest label on this level.
        current_base = max(level_tops) + gap
        max_y = max(max_y, current_base)

    new_top = max(pre_top, max_y + top_margin * yr)
    ax.set_ylim(ylim0, new_top)
    return {"n_brackets": len(specs), "levels": n_levels, "top": new_top}


def infer_reference_group(items) -> Optional[str]:
    """The group every comparison shares, when there is exactly one.

    A set of comparisons produced against a single control all name that control, so it can be
    recovered from the items themselves without the caller restating it. Returns ``None`` when the
    comparisons do not share exactly one common group - all-pairs comparisons, for instance - so the
    caller can fall back to brackets rather than guessing which bar a label belongs to.
    """
    if len(items) < 2:
        return None
    common = None
    for item in items:
        pair = {str(item.group_a), str(item.group_b)}
        common = pair if common is None else (common & pair)
        if not common:
            return None
    return next(iter(common)) if len(common) == 1 else None


def annotate_above(
    ax,
    items,
    positions: Dict[Any, float],
    tops: Dict[Any, float],
    *,
    style,
    cfg: Dict[str, Any],
    reference: Optional[str] = None,
) -> Dict[str, Any]:
    """Draw each comparison's label directly above the bar it refers to.

    This is the convention used when every condition in a screen is tested against one control: the
    marker sits on the bar whose comparison it describes, and the control bar carries none. Drawing
    the same comparisons as brackets stacks one bracket per condition, so with eight groups the
    brackets take two thirds of the panel height and compress the bars into the remainder.

    Only comparisons that involve ``reference`` are placed; anything else is left for the caller,
    since a label above a single bar cannot say which of two non-reference groups it compared.
    Returns a summary including the items that could not be placed.
    """
    if not items or not positions:
        return {"n_labels": 0, "unplaced": list(items), "top": ax.get_ylim()[1]}

    ref = reference if reference is not None else infer_reference_group(items)
    if ref is None:
        return {"n_labels": 0, "unplaced": list(items), "top": ax.get_ylim()[1]}
    ref = str(ref)

    fs = cfg.get("font_size") or getattr(style, "annotation_pt", 9.5)
    text_color = getattr(style, "text_color", "#1a1a1a")
    y0, y1 = ax.get_ylim()
    yr = (y1 - y0) or 1.0
    pad = float(cfg.get("above_bar_pad_frac", 0.02)) * yr

    placed, unplaced, highest = [], [], y0
    for item in items:
        a, b = str(item.group_a), str(item.group_b)
        if a == ref:
            target = b
        elif b == ref:
            target = a
        else:
            unplaced.append(item)
            continue
        if target not in positions:
            unplaced.append(item)
            continue
        x = positions[target]
        base = tops.get(target)
        if base is None:
            base = _data_top(ax)
        y = base + pad
        ax.text(x, y, item.text, ha="center", va="bottom", fontsize=fs,
                color=text_color, zorder=8, clip_on=False)
        placed.append(target)
        highest = max(highest, y)

    if placed:
        # one text line of headroom above the tallest label, so nothing is clipped
        needed = highest + (float(cfg.get("top_margin_frac", 0.10)) * yr)
        if needed > y1:
            ax.set_ylim(y0, needed)

    return {"n_labels": len(placed), "placed": placed, "unplaced": unplaced,
            "reference": ref, "top": ax.get_ylim()[1]}

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
