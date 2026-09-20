"""Circos-style chord diagram: flows between categories as ribbons around a ring.

Answers "how much flow connects each pair of categories, and which categories carry the most?"
for many-to-many relationships that share ONE category set (cell-cell interactions, migration or
transition counts, co-occurrence, trade between regions). Input is an edge list with one row per
link: a ``source`` category, a ``target`` category, an optional numeric ``value`` (link weight;
every link weighs 1 when absent) and an optional ``group`` column that classifies categories.
Marks: an outer ring of segments, one per category, whose arc length is proportional to the
category's total flow; ribbons between segments whose width at each end is proportional to the
link value; labels outside the ring; optionally tick marks along each segment and a thin outer
band that shows the group of each category. No inferential statistics apply to this plot.

Contract (references/renderer-contract.md): roles and options are read only through
``get_mapping``; ``df`` is never mutated; every aesthetic comes from ``StyleProfile`` tokens or a
declared option; the figure is drawn inside ``with style.apply():``.

Ring geometry uses named radii (``_R_*``) so further tracks (heatmap or histogram rings) can be
added outside the segment ring in a later version without changing the ribbon layout.
"""
from __future__ import annotations

import math
import textwrap
from typing import Any, Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch, PathPatch, Wedge
from matplotlib.path import Path

from make_my_figure_core.plots._v04_shared import ordered_unique
from make_my_figure_core.plots.base import (
    RenderError,
    RenderResult,
    base_metadata,
    figure_size,
    get_mapping,
    place_legend,
    require_columns,
    resolve_legend_location,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "chord_diagram"

# Option vocabularies (declared in ui_hints.OPTIONS with explicit scopes).
SEGMENT_ORDERS = ("input", "alphabetical", "by_total_flow")
RIBBON_COLOR_BY = ("source", "target", "group")
LABEL_PLACEMENTS = ("radial", "tangential")

# Ring geometry in axis units (ribbons end at _R_IN; the segment ring spans _R_IN.._R_OUT; the
# group band and any future tracks sit outside _R_OUT; labels start at _R_LABEL).
_R_IN = 1.00
_R_OUT = 1.07
_R_BAND_IN = 1.09
_R_BAND_OUT = 1.13
_R_TICK_LEN = 0.035
_R_LABEL_PAD = 0.05
# Directed ribbons taper to this fraction of the target slice, centred in the slice.
_DIRECTED_TAPER = 0.2
# Neutral group-band shades (alphas of the style text colour) when ribbons are not coloured by group.
_BAND_ALPHAS = (0.85, 0.55, 0.32, 0.18)
_MAX_LABELLED_SEGMENTS = 24
# Labels longer than this (characters) are wrapped at a space so the ring keeps its size.
_LABEL_WRAP_CHARS = 14


def _choice(value: Any, allowed: Sequence[str], default: str) -> str:
    v = str(value).strip().lower().replace(" ", "_") if value not in (None, "") else default
    return v if v in allowed else default


def _number(value: Any, default: float, *, lo: float, hi: float) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(v):
        return default
    return min(max(v, lo), hi)


def _bool(value: Any, default: bool) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _nice_step(span: float, target_ticks: int = 5) -> float:
    """A 1/2/5 x 10^k step giving roughly ``target_ticks`` ticks over ``span``."""
    if span <= 0:
        return 1.0
    raw = span / max(1, target_ticks)
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def _fmt(v: float) -> str:
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v)):,}"
    return f"{v:.3g}"


def _polar(r: float, theta_deg: float) -> Tuple[float, float]:
    t = math.radians(theta_deg)
    return r * math.cos(t), r * math.sin(t)


def _arc_vertices(r: float, t0: float, t1: float) -> Tuple[np.ndarray, np.ndarray]:
    """Vertices and codes of a circular arc of radius r from angle t0 to t1 (degrees, any order)."""
    if abs(t1 - t0) < 1e-9:
        v = np.array([_polar(r, t0)])
        return v, np.array([Path.LINETO])
    arc = Path.arc(min(t0, t1), max(t0, t1))
    verts = arc.vertices * r
    codes = arc.codes.copy()
    if t1 < t0:  # Path.arc is counter-clockwise; reverse for a clockwise traversal
        verts = verts[::-1]
        codes = np.concatenate([[Path.MOVETO], codes[1:][::-1]]) if len(codes) > 1 else codes
    codes[0] = Path.LINETO
    return verts, codes


def _ribbon_path(a: Tuple[float, float], b: Tuple[float, float], r: float) -> Path:
    """Closed ribbon between arc ``a`` and arc ``b`` (angle pairs in degrees) at radius ``r``.

    Path: arc a (a0 -> a1) -> quadratic curve through the centre to b0 -> arc b (b0 -> b1)
    -> quadratic curve through the centre back to a0. For a self-link pass ``b = a``; the ribbon
    then becomes a lens returning to its own slice.
    """
    a0, a1 = a
    b0, b1 = b
    verts: List[Tuple[float, float]] = []
    codes: List[int] = []
    va, ca = _arc_vertices(r, a0, a1)
    verts.extend(map(tuple, va))
    codes.extend(ca)
    codes[0] = Path.MOVETO
    if abs(a0 - b0) < 1e-9 and abs(a1 - b1) < 1e-9:
        # self-link: a shallow bump back from a1 to a0; its depth grows with the slice width so a
        # small self-link is a visible cap rather than a spike into the centre.
        width_deg = abs(a1 - a0)
        depth = min(max(1.0 - width_deg / 40.0, 0.35), 0.9)
        verts.extend([_polar(r * depth, a1), _polar(r * depth, a0), _polar(r, a0)])
        codes.extend([Path.CURVE4, Path.CURVE4, Path.CURVE4])
    else:
        verts.extend([(0.0, 0.0), _polar(r, b0)])
        codes.extend([Path.CURVE3, Path.CURVE3])
        vb, cb = _arc_vertices(r, b0, b1)
        verts.extend(map(tuple, vb[1:]))
        codes.extend(cb[1:])
        verts.extend([(0.0, 0.0), _polar(r, a0)])
        codes.extend([Path.CURVE3, Path.CURVE3])
    verts.append(verts[0])
    codes.append(Path.CLOSEPOLY)
    return Path(np.asarray(verts, dtype=float), np.asarray(codes, dtype=np.uint8))


def _prepare_links(df, src: str, tgt: str, val: Optional[str], *, min_value: float,
                   directed: bool, draw_self_links: bool, warnings: List[str]):
    """Clean and aggregate the edge list. Returns (links DataFrame, drop counts dict)."""
    cols = [src, tgt] + ([val] if val else [])
    work = df[cols].copy()
    dropped: Dict[str, int] = {}

    blank = work[src].isna() | work[tgt].isna() | (work[src].astype(str).str.strip() == "") \
        | (work[tgt].astype(str).str.strip() == "")
    if int(blank.sum()):
        dropped["blank_category"] = int(blank.sum())
        work = work[~blank]
    work = work.assign(**{src: work[src].astype(str).str.strip(), tgt: work[tgt].astype(str).str.strip()})

    if val:
        numeric = pd.to_numeric(work[val], errors="coerce")
        if numeric.notna().sum() == 0 and len(work):
            raise RenderError(f"{PLOT_TYPE}: column '{val}' has no numeric values.")
        bad = numeric.isna()
        if int(bad.sum()):
            dropped["missing_or_non_numeric_value"] = int(bad.sum())
        neg = numeric < 0
        if int(neg.sum()):
            dropped["negative_value"] = int(neg.sum())
        work = work.assign(__value=numeric)[~bad & ~neg]
    else:
        work = work.assign(__value=1.0)

    zero = work["__value"] <= 0
    if int(zero.sum()):
        dropped["zero_value"] = int(zero.sum())
        work = work[~zero]

    if min_value > 0:
        below = work["__value"] < min_value
        if int(below.sum()):
            dropped["below_min_value"] = int(below.sum())
            work = work[~below]

    self_mask = work[src] == work[tgt]
    if not draw_self_links and int(self_mask.sum()):
        dropped["self_link_hidden"] = int(self_mask.sum())
        work = work[~self_mask]

    if not directed:
        # Undirected reading: A->B and B->A are the same link; merge them into one ribbon.
        lo = np.where(work[src] <= work[tgt], work[src], work[tgt])
        hi = np.where(work[src] <= work[tgt], work[tgt], work[src])
        first_seen = {}
        for s, t in zip(work[src], work[tgt]):
            key = (min(s, t), max(s, t))
            first_seen.setdefault(key, (s, t))
        work = work.assign(__lo=lo, __hi=hi)
        agg = work.groupby(["__lo", "__hi"], sort=False)["__value"].sum().reset_index()
        agg[src] = [first_seen[(a, b)][0] for a, b in zip(agg["__lo"], agg["__hi"])]
        agg[tgt] = [first_seen[(a, b)][1] for a, b in zip(agg["__lo"], agg["__hi"])]
        links = agg[[src, tgt, "__value"]]
    else:
        links = work.groupby([src, tgt], sort=False)["__value"].sum().reset_index()

    if dropped:
        parts = ", ".join(f"{n} {k.replace('_', ' ')}" for k, n in dropped.items())
        warnings.append(f"{sum(dropped.values())} link row(s) not drawn ({parts}).")
    return links, dropped


def _category_groups(df, src: str, tgt: str, group: str, categories: List[str],
                     warnings: List[str]) -> Dict[str, Optional[str]]:
    """Group of each category, looked up on rows where it is the source, else the target."""
    groups: Dict[str, Optional[str]] = {}
    conflicts: List[str] = []
    g = df[group].astype(object)
    src_s = df[src].astype(str).str.strip()
    tgt_s = df[tgt].astype(str).str.strip()
    for cat in categories:
        found = None
        for mask in (src_s == cat, tgt_s == cat):
            vals = ordered_unique(g[mask].tolist())
            if vals:
                found = str(vals[0])
                if len(vals) > 1:
                    conflicts.append(cat)
                break
        groups[cat] = found
    if conflicts:
        warnings.append(f"Category(ies) assigned to more than one group; first-seen group kept: "
                        f"{', '.join(conflicts)}.")
    if any(v is None for v in groups.values()):
        missing = [c for c, v in groups.items() if v is None]
        warnings.append(f"No group found for: {', '.join(missing)}.")
    return groups


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    # ---- 1. roles ------------------------------------------------------------------------
    src = get_mapping(spec, "source", required=True, context=PLOT_TYPE)
    tgt = get_mapping(spec, "target", required=True, context=PLOT_TYPE)
    val = get_mapping(spec, "value") or None
    group = get_mapping(spec, "group") or None
    require_columns(df, [c for c in (src, tgt, val, group) if c], context=PLOT_TYPE)

    # ---- 2. options ----------------------------------------------------------------------
    order = _choice(get_mapping(spec, "segment_order"), SEGMENT_ORDERS, "input")
    gap_deg = _number(get_mapping(spec, "gap_degrees"), 3.0, lo=0.0, hi=30.0)
    start_angle = _number(get_mapping(spec, "start_angle"), 90.0, lo=-360.0, hi=360.0)
    color_by = _choice(get_mapping(spec, "ribbon_color_by"), RIBBON_COLOR_BY, "source")
    alpha = _number(get_mapping(spec, "ribbon_alpha"), 0.65, lo=0.05, hi=1.0)
    min_value = _number(get_mapping(spec, "min_value"), 0.0, lo=0.0, hi=float("inf"))
    directed = _bool(get_mapping(spec, "directed"), False)
    show_labels = _bool(get_mapping(spec, "show_labels"), True)
    label_placement = _choice(get_mapping(spec, "label_placement"), LABEL_PLACEMENTS, "radial")
    show_ticks = _bool(get_mapping(spec, "show_ticks"), False)
    draw_self = _bool(get_mapping(spec, "draw_self_links"), True)
    show_legend = _bool(get_mapping(spec, "show_legend"), True)

    warnings: List[str] = []
    if color_by == "group" and not group:
        warnings.append("ribbon_color_by='group' needs a group column; ribbons coloured by source.")
        color_by = "source"

    # ---- 3. data -------------------------------------------------------------------------
    links, dropped = _prepare_links(df, src, tgt, val, min_value=min_value, directed=directed,
                                    draw_self_links=draw_self, warnings=warnings)
    if links.empty:
        raise RenderError(f"{PLOT_TYPE}: no links left to draw after cleaning "
                          f"(check '{src}', '{tgt}'" + (f", '{val}'" if val else "") + ").")

    # Category order: first appearance scanning each row's source then target.
    seen: List[str] = []
    for s, t in zip(links[src], links[tgt]):
        for c in (s, t):
            if c not in seen:
                seen.append(c)
    totals: Dict[str, float] = {c: 0.0 for c in seen}
    for s, t, v in zip(links[src], links[tgt], links["__value"]):
        totals[s] += float(v)
        if t != s:
            totals[t] += float(v)
    if order == "alphabetical":
        categories = sorted(seen, key=lambda c: c.lower())
    elif order == "by_total_flow":
        categories = sorted(seen, key=lambda c: (-totals[c], seen.index(c)))
    else:
        categories = list(seen)
    n_cat = len(categories)
    pos = {c: i for i, c in enumerate(categories)}

    cat_groups: Dict[str, Optional[str]] = {}
    group_levels: List[str] = []
    if group:
        cat_groups = _category_groups(df, src, tgt, group, categories, warnings)
        group_levels = ordered_unique([cat_groups[c] for c in categories if cat_groups[c] is not None])

    # ---- 4. angular layout (clockwise from start_angle, Circos convention) ----------------
    grand_total = sum(totals.values())
    if n_cat * gap_deg >= 360.0:
        gap_deg = max(0.0, 300.0 / n_cat)
        warnings.append(f"Gap reduced to {gap_deg:.1f} degrees so {n_cat} segments fit.")
    usable = 360.0 - n_cat * gap_deg
    deg_per_unit = usable / grand_total
    seg_span: Dict[str, Tuple[float, float]] = {}      # category -> (start_deg, end_deg), start > end
    cursor = start_angle
    for c in categories:
        span = totals[c] * deg_per_unit
        seg_span[c] = (cursor, cursor - span)
        cursor -= span + gap_deg

    # Slices within each segment: partners in ring order (outgoing first when directed).
    links = links.assign(__src_pos=[pos[s] for s in links[src]], __tgt_pos=[pos[t] for t in links[tgt]])
    slice_cursor = {c: seg_span[c][0] for c in categories}
    src_slice: Dict[int, Tuple[float, float]] = {}
    tgt_slice: Dict[int, Tuple[float, float]] = {}

    def _take(cat: str, v: float) -> Tuple[float, float]:
        a0 = slice_cursor[cat]
        a1 = a0 - v * deg_per_unit
        slice_cursor[cat] = a1
        return a0, a1

    for c in categories:
        out_mask = links[src] == c
        in_mask = (links[tgt] == c) & (links[src] != c)
        out_rows = links[out_mask].sort_values("__tgt_pos", kind="stable")
        in_rows = links[in_mask].sort_values("__src_pos", kind="stable")
        if directed:
            for idx, row in out_rows.iterrows():
                src_slice[idx] = _take(c, float(row["__value"]))
                if row[src] == row[tgt]:
                    tgt_slice[idx] = src_slice[idx]
            for idx, row in in_rows.iterrows():
                tgt_slice[idx] = _take(c, float(row["__value"]))
        else:
            rows = pd.concat([out_rows, in_rows])
            rows = rows.assign(__partner=np.where(rows[src] == c, rows["__tgt_pos"], rows["__src_pos"]))
            rows = rows.sort_values("__partner", kind="stable")
            for idx, row in rows.iterrows():
                sl = _take(c, float(row["__value"]))
                if row[src] == c:
                    src_slice[idx] = sl
                    if row[tgt] == c:
                        tgt_slice[idx] = sl
                else:
                    tgt_slice[idx] = sl

    # ---- 5. colours ----------------------------------------------------------------------
    group_color = {g: style.color_for(j) for j, g in enumerate(group_levels)}
    if color_by == "group":
        seg_color = {c: group_color.get(cat_groups.get(c), style.color_for(i)) for i, c in enumerate(categories)}
        band_color = seg_color
    else:
        seg_color = {c: style.color_for(i) for i, c in enumerate(categories)}
        band_color = {}
        for c in categories:
            g = cat_groups.get(c)
            if g is None:
                band_color[c] = None
            else:
                j = group_levels.index(g)
                band_color[c] = (style.text_color, _BAND_ALPHAS[j % len(_BAND_ALPHAS)])

    def _ribbon_color(row) -> Any:
        if color_by == "target":
            return seg_color[row[tgt]]
        if color_by == "group":
            return group_color.get(cat_groups.get(row[src]), seg_color[row[src]])
        return seg_color[row[src]]

    # ---- 6. labels and limits ------------------------------------------------------------
    tick_step = _nice_step(max(totals.values())) if show_ticks else None
    labels = {}
    for c in categories:
        text = f"{c} ({_fmt(totals[c])})" if show_ticks else c
        if len(text) > _LABEL_WRAP_CHARS:
            text = "\n".join(textwrap.wrap(text, _LABEL_WRAP_CHARS, break_long_words=False) or [text])
        labels[c] = text
    if show_labels and n_cat > _MAX_LABELLED_SEGMENTS:
        warnings.append(f"{n_cat} segments: labels may overlap; consider radial placement, "
                        f"'show_labels' off or fewer categories.")
    r_label_base = (_R_BAND_OUT if group else _R_OUT) + _R_LABEL_PAD
    fig_w_in, fig_h_in = figure_size(spec, style, aspect=1.0)
    fig_pt = min(fig_w_in, fig_h_in) * 72.0
    if show_labels:
        longest = max(len(line) for l in labels.values() for line in l.split("\n"))
        n_lines = max(l.count("\n") + 1 for l in labels.values())
        if label_placement == "radial":
            label_pt = longest * style.tick_label_pt * 0.58
        else:
            label_pt = style.tick_label_pt * 1.3 * n_lines
    else:
        label_pt = 0.0
    # Solve r_lim = r_label + label_pt / (pt per axis unit); pt per unit = 0.92 * fig_pt / (2 r_lim).
    frac = min(2.0 * label_pt / (0.92 * fig_pt), 0.6)
    if frac >= 0.6:
        warnings.append("Very long category labels: the ring is shrunk to keep them inside the figure; "
                        "shorten the labels or use a wider column width.")
    r_lim = r_label_base / (1.0 - frac) + 0.02

    # Legend: by default one row under the ring (the corners are where the labels go); an explicit
    # layout.legend_location or the style's legend_outside preference is honoured instead.
    draw_legend = bool(group and show_legend and group_levels)
    layout_block = spec.get("layout", {}) or {}
    legend_below = draw_legend and not str(layout_block.get("legend_location", "")).strip() \
        and not getattr(style, "legend_outside", False)
    legend_rows = int(math.ceil(len(group_levels) / 4.0)) if legend_below else 0
    legend_frac = 0.075 * legend_rows + (0.035 if legend_below else 0.0)
    title = layout_block.get("title")
    top_frac = 0.08 if title else 0.0
    fig_h_in = fig_h_in * (1.0 + legend_frac + top_frac)

    # ---- 7. draw -------------------------------------------------------------------------
    with style.apply():
        fig, ax = plt.subplots(figsize=(fig_w_in, fig_h_in))
        ax.set_aspect("equal")
        ax.set_xlim(-r_lim, r_lim)
        ax.set_ylim(-r_lim, r_lim)
        ax.axis("off")
        ax._colorbar = True  # diagram without axes: skip the axis-label QA check (Sankey/network precedent)

        # Ribbons (below the ring).
        for idx, row in links.iterrows():
            a = src_slice[idx]
            b = tgt_slice[idx]
            if directed and row[src] != row[tgt]:
                mid = (b[0] + b[1]) / 2.0
                half = abs(b[0] - b[1]) * _DIRECTED_TAPER / 2.0
                b = (mid + half, mid - half)
            path = _ribbon_path(a, b, _R_IN)
            col = _ribbon_color(row)
            ax.add_patch(PathPatch(path, facecolor=col, edgecolor="none", alpha=alpha, zorder=2))

        # Segment ring.
        for c in categories:
            t0, t1 = seg_span[c]
            if abs(t0 - t1) < 1e-9:
                continue
            ax.add_patch(Wedge((0, 0), _R_OUT, t1, t0, width=_R_OUT - _R_IN, facecolor=seg_color[c],
                               edgecolor="none", zorder=4))
            if group and band_color.get(c) is not None:
                bc = band_color[c]
                if isinstance(bc, tuple):
                    fc, a_ = bc
                else:
                    fc, a_ = bc, 1.0
                ax.add_patch(Wedge((0, 0), _R_BAND_OUT, t1, t0, width=_R_BAND_OUT - _R_BAND_IN,
                                   facecolor=fc, alpha=a_, edgecolor="none", zorder=4))

        # Tick marks along each segment (nice step in flow units).
        if show_ticks and tick_step:
            r0 = _R_BAND_OUT if group else _R_OUT
            for c in categories:
                t0, _ = seg_span[c]
                v = 0.0
                while v <= totals[c] + 1e-9:
                    ang = t0 - v * deg_per_unit
                    x0, y0 = _polar(r0, ang)
                    x1, y1 = _polar(r0 + _R_TICK_LEN, ang)
                    ax.plot([x0, x1], [y0, y1], color=style.text_color,
                            lw=style.spine_width_pt * 0.7, solid_capstyle="butt", zorder=5)
                    v += tick_step
            unit = f" ({val})" if val else " (links)"
            ax.text(-r_lim, -r_lim, f"ticks every {_fmt(tick_step)}{unit}",
                    ha="left", va="bottom", fontsize=style.annotation_pt, color=style.text_color)

        # Labels outside the ring.
        if show_labels:
            r_lab = r_label_base + (_R_TICK_LEN if show_ticks else 0.0)
            for c in categories:
                t0, t1 = seg_span[c]
                mid = (t0 + t1) / 2.0
                m = mid % 360.0
                x, y = _polar(r_lab, mid)
                if label_placement == "radial":
                    flip = 90.0 < m < 270.0
                    rot = mid + 180.0 if flip else mid
                    ha = "right" if flip else "left"
                    ax.text(x, y, labels[c], rotation=rot, rotation_mode="anchor", ha=ha, va="center",
                            fontsize=style.tick_label_pt, color=style.text_color, zorder=6)
                else:
                    flip = 180.0 < m < 360.0
                    rot = mid + 90.0 if flip else mid - 90.0
                    va = "top" if flip else "bottom"
                    ax.text(x, y, labels[c], rotation=rot, rotation_mode="anchor", ha="center", va=va,
                            fontsize=style.tick_label_pt, color=style.text_color, zorder=6)

        # Group legend.
        if draw_legend:
            handles = []
            for j, g in enumerate(group_levels):
                if color_by == "group":
                    handles.append(Patch(facecolor=group_color[g], edgecolor="none", label=g))
                else:
                    handles.append(Patch(facecolor=style.text_color, alpha=_BAND_ALPHAS[j % len(_BAND_ALPHAS)],
                                         edgecolor="none", label=g))
            if legend_below:
                row_style = style.with_overrides({"legend_ncol": min(4, len(group_levels))})
                place_legend(ax, row_style, title=str(group), handles=handles, labels=list(group_levels),
                             location=("upper center", (0.5, -0.01), None))
            else:
                place_legend(ax, style, title=str(group), handles=handles, labels=list(group_levels),
                             location=resolve_legend_location(spec, style))

        if title:
            ax.set_title(str(title), fontsize=style.title_font_pt,
                         fontweight=getattr(style, "title_font_weight", "bold"))
        total_h = 1.0 + legend_frac + top_frac
        fig.subplots_adjust(left=0.02, right=0.98, bottom=(legend_frac + 0.02) / total_h,
                            top=1.0 - (top_frac + 0.02) / total_h)

    # ---- 8. metadata ---------------------------------------------------------------------
    meta = base_metadata(spec, style, df, used_columns=[c for c in (src, tgt, val, group) if c])
    meta.update({
        "categories": categories,
        "category_totals": {c: round(float(totals[c]), 6) for c in categories},
        "category_groups": {c: cat_groups.get(c) for c in categories} if group else None,
        "group_levels": group_levels,
        "n_categories": n_cat,
        "n_links_drawn": int(len(links)),
        "n_self_links": int((links[src] == links[tgt]).sum()),
        "n_rows_dropped": dropped,
        "value_column": val or None,
        "weights": "value column" if val else "equal (no value column)",
        "directed": directed,
        "segment_order": order,
        "gap_degrees": gap_deg,
        "start_angle": start_angle,
        "ribbon_color_by": color_by,
        "ribbon_alpha": alpha,
        "min_value": min_value,
        "draw_self_links": draw_self,
        "label_placement": label_placement if show_labels else None,
        "tick_step": tick_step,
        "segment_spans_deg": {c: [round(seg_span[c][0], 4), round(seg_span[c][1], 4)] for c in categories},
        "statistics_note": "No inferential statistics apply to a chord diagram; it summarises flows.",
    })
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
