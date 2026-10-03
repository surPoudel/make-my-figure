"""Central statistical-annotation layout engine for renderers.

Renderers must not reinvent bracket placement. They:

1. compute per-category x positions and a "data top" per category,
2. hand the list of :class:`AnnotationItem` objects + a position lookup here,

and this module draws non-overlapping significance brackets (auto-stacked),
places the p-value/star text, and expands the value axis so nothing is clipped.
It also renders corner text panels for correlation/survival/omnibus stats.

Bracket placement (:func:`annotate_pairwise`): every bracket starts above the
highest drawn element among the groups it *spans* (using the renderer's
per-group tops), stacks only over brackets it overlaps, and uses point-based
geometry derived from the annotation font (legacy ``*_frac`` keys still honoured).
Vertical (categories on x) and horizontal (categories on y) layouts are supported.

Every label drawn here comes from an AnnotationItem, which is derived from a
stored StatResult - so no p-value is ever a decorative, unbacked label.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from make_my_figure_core.statistics.annotations import AnnotationItem


def _data_top(ax, *, horizontal: bool = False) -> float:
    """Best estimate of the top of the drawn data along the value axis, in data coordinates."""
    lo, hi = ax.get_xlim() if horizontal else ax.get_ylim()
    top = hi
    # Consider explicit artists (bars, lines, collections) if available.
    try:
        dl = ax.dataLim
        dmax = dl.xmax if horizontal else dl.ymax
        if np.isfinite(dmax):
            top = max(top, dmax)
    except Exception:
        pass
    return top


def _num(value) -> Optional[float]:
    """A finite float, or ``None`` for unset / blank / non-numeric."""
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if np.isfinite(out) else None


def _text_extent_px(fig, renderer, text: str, fontsize: float) -> Tuple[float, float]:
    """``(width_px, height_px)`` of a (possibly multi-line) label, independent of axis limits."""
    from matplotlib.text import Text

    probe = Text(0.0, 0.0, text, fontsize=fontsize, figure=fig)
    bb = probe.get_window_extent(renderer=renderer)
    return float(bb.width), float(bb.height)


def _data_per_pt(ax, *, value_range: float, horizontal: bool = False) -> float:
    """Data units per typographic point along the value axis, for a given value range."""
    fig = ax.figure
    w_in, h_in = fig.get_size_inches()
    pos = ax.get_position()
    extent_in = (pos.width * w_in) if horizontal else (pos.height * h_in)
    extent_pt = max(float(extent_in) * 72.0, 1.0)
    return (float(value_range) or 1.0) / extent_pt


def bracket_geometry(style, cfg: Dict[str, Any], *, value_range: float) -> Dict[str, Any]:
    """Resolve the bracket geometry for ``cfg`` (a StatsSpec ``annotation`` block).

    Tick height, gap, label offset and top margin are point-based by default, derived from the
    annotation font size and the bracket line width, so a bracket looks the same at any y-range or
    panel size. Explicit ``*_pt`` keys override the derived points. The legacy ``*_frac`` keys
    (fractions of the value range) are honoured when a spec sets them, so older specs render as
    they did; a ``None`` there means "use points".
    """
    cfg = cfg or {}
    fs = _num(cfg.get("font_size")) or float(getattr(style, "annotation_pt", 9.5))
    lw = _num(cfg.get("line_width")) or float(getattr(style, "spine_width_pt", 1.1))
    vr = float(value_range) or 1.0

    tick_frac, gap_frac, margin_frac = (_num(cfg.get("bracket_height_frac")), _num(cfg.get("gap_frac")),
                                        _num(cfg.get("top_margin_frac")))
    tick_pt = _num(cfg.get("bracket_height_pt")) or max(2.0, 0.40 * fs)
    gap_pt = _num(cfg.get("gap_pt")) or (0.60 * fs + lw)
    label_offset_pt = _num(cfg.get("label_offset_pt")) or (0.20 * fs + 0.5 * lw)
    margin_pt = _num(cfg.get("top_margin_pt")) or 0.50 * fs
    return {
        "font_size": fs, "line_width": lw,
        "tick_pt": tick_pt, "gap_pt": gap_pt, "label_offset_pt": label_offset_pt, "margin_pt": margin_pt,
        # legacy fractions (data units) when a spec pins them; None -> use the point values
        "tick_data": (tick_frac * vr) if tick_frac is not None else None,
        "gap_data": (gap_frac * vr) if gap_frac is not None else None,
        "margin_data": (margin_frac * vr) if margin_frac is not None else None,
        "point_based": tick_frac is None and gap_frac is None,
    }


def annotate_pairwise(
    ax,
    items: List[AnnotationItem],
    position_lookup: Callable[[AnnotationItem], Optional[Tuple[float, float]]],
    *,
    style,
    cfg: Dict[str, Any],
    top_lookup: Optional[Callable[[AnnotationItem], Optional[float]]] = None,
    positions: Optional[Dict[Any, float]] = None,
    tops: Optional[Dict[Any, float]] = None,
    orientation: str = "vertical",
) -> Dict[str, Any]:
    """Draw significance brackets for pairwise comparison items.

    ``position_lookup`` maps an item to its ``(pos_a, pos_b)`` along the category axis (data
    coordinates; ``None`` skips the item). ``top_lookup`` maps an item to the value its bracket must
    clear for the two compared groups. ``positions``/``tops`` are the renderer's per-group maps (any
    keys, matching each other): when given, every group whose position lies between the two compared
    positions is checked too, so a bracket from A to C also clears B's points, error bars or whiskers.

    Placement: each bracket starts a gap above the highest drawn element it spans - not above the
    global maximum - and is stacked only over brackets whose extent (bracket span or label width)
    it overlaps, narrowest span first. Geometry is point-based (see :func:`bracket_geometry`); the
    value axis is expanded so the topmost label fits with a small margin and is never shrunk, so no
    observation is cropped. Which comparisons are drawn and how their labels read is decided before
    this call (the items); nothing here changes that.

    ``orientation="horizontal"`` draws brackets along x for horizontal bars/boxes (categories on y):
    the bracket opens to the right of the data and the label sits to its right.

    Returns a JSON-safe dict (bracket count, stacking depth, final axis top, resolved geometry).
    """
    cfg = cfg or {}
    horizontal = str(orientation or "vertical").lower().startswith("h")
    if horizontal:
        v0, v1 = ax.get_xlim()
    else:
        v0, v1 = ax.get_ylim()
    vr = (v1 - v0) or 1.0
    geo = bracket_geometry(style, cfg, value_range=vr)
    fs, lw = geo["font_size"], geo["line_width"]
    text_color = getattr(style, "text_color", "#1a1a1a")

    # --- resolve the start (value the bracket must clear) for each drawable item -------------
    base_top = _data_top(ax, horizontal=horizontal)
    specs: List[Dict[str, Any]] = []
    for it in items:
        cs = position_lookup(it)
        if cs is None:
            continue
        c1, c2 = sorted(float(c) for c in cs)
        start = None
        if top_lookup is not None:
            t = _num(top_lookup(it))
            if t is not None:
                start = t
        if positions and tops:
            # every group between (and including) the two compared positions
            for key, pos in positions.items():
                if pos is None or key not in tops:
                    continue
                if c1 - 1e-9 <= float(pos) <= c2 + 1e-9:
                    t = _num(tops[key])
                    if t is not None:
                        start = t if start is None else max(start, t)
        if start is None:
            start = base_top
        specs.append({"c1": c1, "c2": c2, "mid": 0.5 * (c1 + c2), "text": it.text, "start": float(start),
                      "groups": [str(it.group_a), str(it.group_b)]})

    if not specs:
        return {"n_brackets": 0, "levels": 0, "top": float(v1), "orientation": orientation,
                "geometry": {k: geo[k] for k in ("tick_pt", "gap_pt", "label_offset_pt", "margin_pt", "point_based")}}

    # --- measure: label extents (px) and the axes box, independent of the value limits ----------
    fig = ax.figure
    dpi = float(fig.dpi)
    px_per_pt = dpi / 72.0
    renderer = None
    try:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bb_ax = ax.get_window_extent(renderer=renderer)
        val_extent_px = float(bb_ax.width if horizontal else bb_ax.height)
        cat_extent_px = float(bb_ax.height if horizontal else bb_ax.width)
    except Exception:
        renderer = None
        # fall back to the figure size and axes fraction
        w_in, h_in = fig.get_size_inches()
        pos = ax.get_position()
        val_extent_px = float((pos.width * w_in if horizontal else pos.height * h_in) * dpi)
        cat_extent_px = float((pos.height * h_in if horizontal else pos.width * w_in) * dpi)
    val_extent_px = val_extent_px or 1.0
    cat_extent_px = cat_extent_px or 1.0

    if horizontal:
        cat0, cat1 = ax.get_ylim()
    else:
        cat0, cat1 = ax.get_xlim()
    cat_range = abs(cat1 - cat0) or 1.0
    cat_per_px = cat_range / cat_extent_px
    pad_cat = 0.03 * cat_range

    n_lines_default = 1.2 * fs * px_per_pt   # px per text line when measuring is unavailable
    for s in specs:
        w_px = h_px = None
        if renderer is not None:
            try:
                w_px, h_px = _text_extent_px(fig, renderer, s["text"], fs)
            except Exception:
                w_px = h_px = None
        if w_px is None:
            lines = s["text"].split("\n")
            w_px = 0.6 * fs * px_per_pt * max(len(ln) for ln in lines)
            h_px = n_lines_default * len(lines)
        # extent along the value axis (stacking) and along the category axis (collision), in pt
        s["label_val_pt"] = (w_px if horizontal else h_px) / px_per_pt
        s["label_cat_data"] = (h_px if horizontal else w_px) * cat_per_px * 1.12
        half = max(0.5 * (s["c2"] - s["c1"]), 0.5 * s["label_cat_data"])
        s["eff1"] = s["mid"] - half - pad_cat
        s["eff2"] = s["mid"] + half + pad_cat

    # --- stack: narrowest span first; a bracket only rises over brackets whose extent it overlaps
    order = sorted(specs, key=lambda s: (s["c2"] - s["c1"], s["eff2"] - s["eff1"], s["start"], s["mid"]))

    def _layout(k_data_per_pt: float) -> float:
        """Place every bracket for the given data-per-point scale; return the required axis top."""
        tick = geo["tick_data"] if geo["tick_data"] is not None else geo["tick_pt"] * k_data_per_pt
        gap = geo["gap_data"] if geo["gap_data"] is not None else geo["gap_pt"] * k_data_per_pt
        offset = geo["label_offset_pt"] * k_data_per_pt
        margin = geo["margin_data"] if geo["margin_data"] is not None else geo["margin_pt"] * k_data_per_pt
        placed: List[Dict[str, Any]] = []
        highest = v0
        for s in order:
            base = s["start"] + gap
            depth = 0
            for p in placed:
                if s["eff1"] < p["eff2"] - 1e-9 and s["eff2"] > p["eff1"] + 1e-9:
                    base = max(base, p["label_top"] + gap)
                    depth = max(depth, p["depth"] + 1)
            s["base"] = base
            s["tick_top"] = base + tick
            s["label_bottom"] = s["tick_top"] + offset
            s["label_top"] = s["label_bottom"] + s["label_val_pt"] * k_data_per_pt
            s["depth"] = depth
            placed.append(s)
            highest = max(highest, s["label_top"])
        return highest + margin

    # The data-per-point scale depends on the final value range, which depends on the layout:
    # iterate to the fixed point (a contraction as long as the stack is shorter than the axes).
    new_v1 = float(v1)
    for _ in range(8):
        k = ((new_v1 - v0) or 1.0) / (val_extent_px / px_per_pt)
        needed = _layout(k)
        candidate = max(float(v1), needed)
        if abs(candidate - new_v1) <= 1e-9 * max(1.0, abs(new_v1)):
            new_v1 = candidate
            break
        new_v1 = candidate
    k = ((new_v1 - v0) or 1.0) / (val_extent_px / px_per_pt)
    _layout(k)
    # Expand the value axis (never shrink it) before drawing so text is measured against the
    # final transform. clip_on=False keeps every artist visible even if a later layout pass nudges it.
    if horizontal:
        ax.set_xlim(v0, new_v1)
    else:
        ax.set_ylim(v0, new_v1)

    for s in specs:
        if horizontal:
            ax.plot([s["base"], s["tick_top"], s["tick_top"], s["base"]],
                    [s["c1"], s["c1"], s["c2"], s["c2"]], lw=lw, c=text_color,
                    solid_capstyle="butt", clip_on=False, zorder=6)
            ax.text(s["label_bottom"], s["mid"], s["text"], ha="left", va="center", fontsize=fs,
                    color=text_color, zorder=7, clip_on=False)
        else:
            ax.plot([s["c1"], s["c1"], s["c2"], s["c2"]],
                    [s["base"], s["tick_top"], s["tick_top"], s["base"]], lw=lw, c=text_color,
                    solid_capstyle="butt", clip_on=False, zorder=6)
            ax.text(s["mid"], s["label_bottom"], s["text"], ha="center", va="bottom", fontsize=fs,
                    color=text_color, zorder=7, clip_on=False)

    n_levels = 1 + max(s["depth"] for s in specs)
    return {
        "n_brackets": len(specs), "levels": int(n_levels), "top": float(new_v1),
        "orientation": "horizontal" if horizontal else "vertical",
        "geometry": {k: geo[k] for k in ("tick_pt", "gap_pt", "label_offset_pt", "margin_pt", "point_based")},
        "brackets": [{"groups": s["groups"], "span": [s["c1"], s["c2"]], "start": s["start"],
                      "base": float(s["base"]), "label_top": float(s["label_top"]), "level": int(s["depth"])}
                     for s in specs],
    }


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

    fs = _num(cfg.get("font_size")) or float(getattr(style, "annotation_pt", 9.5))
    text_color = getattr(style, "text_color", "#1a1a1a")
    y0, y1 = ax.get_ylim()
    yr = (y1 - y0) or 1.0
    pad_frac = _num(cfg.get("above_bar_pad_frac"))
    pad = (pad_frac if pad_frac is not None else 0.02) * yr

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
        # headroom for the tallest label plus a small margin, so nothing is clipped
        margin_frac = _num(cfg.get("top_margin_frac"))
        if margin_frac is not None:
            needed = highest + margin_frac * yr                      # legacy fraction of the y-range
        else:
            n_lines = max(1 + item.text.count("\n") for item in items)
            geo = bracket_geometry(style, cfg, value_range=yr)
            head_pt = 1.2 * fs * n_lines + geo["margin_pt"]
            needed = y1
            for _ in range(4):                                        # fixed point on the data-per-pt scale
                k = _data_per_pt(ax, value_range=(max(needed, y1) - y0))
                needed = highest + head_pt * k
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
        "center right": (0.97, 0.50, "right", "center"),
        "center left": (0.03, 0.50, "left", "center"),
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
