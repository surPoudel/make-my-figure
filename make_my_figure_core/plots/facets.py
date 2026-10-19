"""Facet grids: one panel per level of a row and/or column variable.

A 2 x 2 x 3 design measured over time (species x initial age x nitrogen, four
sampling months) is read as small multiples: one panel per species and age, the
nitrogen levels coloured inside each, months along x - ggplot's
``facet_grid(Age ~ Species)``. This module builds that grid once for every
renderer that offers it, so the panels look and behave alike:

* the same category order, the same colour per level and the same value axis in
  every panel, so panels can be compared by eye;
* strip labels above the columns and beside the rows (``Species: Species_A``);
* one shared x label, one shared y label, one title and one legend for the whole
  grid, carried by an invisible *host* axes that spans the panels.

The host is a real axes, so every shared control acts on the grid exactly as it
acts on a single plot: legend location, legend outside, legend geometry, axis
label padding and visibility, title. It and the strips position themselves at
draw time (``axes_locator``), so whatever later moves the panels - a legend
reserving room, the canvas fitting pass - they follow.

The renderer draws the data; this module owns the grid. A renderer asked for no
facets never reaches this code, so an untouched figure renders exactly as before.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from matplotlib.transforms import Bbox

from make_my_figure_core.plots.base import (
    RenderError,
    figure_size,
    pinned_dimension,
    register_refit,
    requested_width,
    style_axes,
)

FACET_FIELDS = ("facet_row", "facet_col")
FACET_HOST_LABEL = "<facet-host>"
FACET_STRIP_LABEL = "<facet-strip>"
LABEL_STYLES = ("column: value", "value")
MAX_FACET_LEVELS = 12
# Strip thickness in points: lines x line height + padding, in strip font sizes.
_STRIP_LINE = 1.2
_STRIP_PAD = 0.55
_STRIP_GAP_PT = 0.0
# An automatic figure never grows past this; past it the panels shrink instead and
# the renderer says so. 8 facet columns at the single-plot panel width came to
# 26.9 in, which no page holds.
MAX_AUTO_WIDTH_IN = 10.0
MAX_AUTO_HEIGHT_IN = 10.0
# Below this panel width the tick labels of a four-level category axis collide.
MIN_COMFORTABLE_PANEL_IN = 1.3
# Gap between an outside legend and the grid's outermost label, in points.
_LEGEND_LABEL_GAP_PT = 6.0


def facet_columns(spec: Dict[str, Any], df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """``(row, col)`` facet variables named in the mapping (None when unset)."""
    mapping = (spec or {}).get("mapping") or {}
    out = []
    for key in FACET_FIELDS:
        v = mapping.get(key)
        v = None if v in (None, "", "(none)") else str(v)
        if v is not None and v not in df.columns:
            raise RenderError(f"{key} column {v!r} is not in the table.")
        out.append(v)
    row, col = out
    if row is not None and row == col:
        raise RenderError("Facet rows and facet columns must be different columns.")
    return row, col


def wants_facets(spec: Dict[str, Any]) -> bool:
    mapping = (spec or {}).get("mapping") or {}
    return any(mapping.get(k) not in (None, "", "(none)") for k in FACET_FIELDS)


def facet_levels(series: pd.Series) -> List[Any]:
    """Levels in a stable, meaningful order: numbers ascending, text as first seen."""
    values = list(dict.fromkeys(series.dropna().tolist()))
    if values and all(isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool)
                      for v in values):
        return sorted(values)
    return values


def strip_text(variable: str, level: Any, label_style: str) -> str:
    level = _fmt_level(level)
    return level if label_style == "value" else f"{variable}: {level}"


def _fmt_level(v: Any) -> str:
    if isinstance(v, (float, np.floating)) and float(v).is_integer():
        return str(int(v))
    return str(v)


@dataclass
class FacetPanel:
    row: Any
    col: Any
    r: int
    c: int
    ax: Any
    data: pd.DataFrame
    label: str


@dataclass
class FacetGrid:
    fig: Any
    host: Any
    panels: List[FacetPanel]
    row_var: Optional[str]
    col_var: Optional[str]
    rows: List[Any]
    cols: List[Any]
    strips: List[Any] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    free_axes: Dict[str, bool] = field(default_factory=dict)    # {"x": True} = x not shared
    style: Any = None

    @property
    def axes(self) -> List[Any]:
        return [p.ax for p in self.panels]

    def bottom_row(self) -> List[Any]:
        last = max(p.r for p in self.panels)
        return [p.ax for p in self.panels if p.r == last]

    def left_column(self) -> List[Any]:
        return [p.ax for p in self.panels if p.c == 0]


def _union_locator(fig, panel_axes, strip_axes):
    """Host position = union of panels and strips, recomputed at every draw."""
    def locate(ax, renderer):
        boxes = [a.get_position() for a in panel_axes]
        boxes += [s.get_position() for s in strip_axes if s.get_visible()]
        u = Bbox.union(boxes)
        _fit_host_labelpads(ax, panel_axes, renderer)
        return u
    return locate


def _fit_host_labelpads(host, panel_axes, renderer) -> None:
    """Shared axis labels sit clear of the outer panels' tick labels."""
    try:
        fig = host.figure
        to_pt = 72.0 / fig.dpi
        bottoms = [a for a in panel_axes if a.xaxis.get_ticklabels() and any(
            t.get_visible() and t.get_text() for t in a.xaxis.get_ticklabels())]
        lefts = [a for a in panel_axes if any(
            t.get_visible() and t.get_text() for t in a.yaxis.get_ticklabels())]
        gap_x = 0.0
        for a in bottoms:
            tb = a.xaxis.get_tightbbox(renderer)
            if tb is not None:
                gap_x = max(gap_x, (a.bbox.y0 - tb.y0) * to_pt)
        gap_y = 0.0
        for a in lefts:
            tb = a.yaxis.get_tightbbox(renderer)
            if tb is not None:
                gap_y = max(gap_y, (a.bbox.x0 - tb.x0) * to_pt)
        host.xaxis.labelpad = gap_x + float(getattr(host, "_mmf_user_xpad", 4.0))
        host.yaxis.labelpad = gap_y + float(getattr(host, "_mmf_user_ypad", 4.0))
    except Exception:  # noqa: BLE001 - a nicety, never break a draw
        pass


def _strip_size_pt(strip) -> float:
    font_pt = float(getattr(strip, "_mmf_font_pt", 9.0))
    lines = int(getattr(strip, "_mmf_lines", 1))
    return font_pt * (_STRIP_LINE * lines + _STRIP_PAD)


def _strip_locator(panel, side: str):
    def locate(ax, renderer):
        fig = panel.figure
        pos = panel.get_position()
        w_in, h_in = fig.get_size_inches()
        size_pt = _strip_size_pt(ax)
        if side == "top":
            h = size_pt / 72.0 / h_in
            g = _STRIP_GAP_PT / 72.0 / h_in
            return Bbox.from_bounds(pos.x0, pos.y1 + g, pos.width, h)
        w = size_pt / 72.0 / w_in
        g = _STRIP_GAP_PT / 72.0 / w_in
        return Bbox.from_bounds(pos.x1 + g, pos.y0, w, pos.height)
    return locate


def _add_strip(fig, panel_ax, text: str, side: str, style) -> Any:
    font_pt = float(style.tick_label_pt)
    s = fig.add_axes([0, 0, 0.01, 0.01], label=FACET_STRIP_LABEL)
    s._mmf_font_pt = font_pt
    s._mmf_lines = 1
    s._mmf_full_text = text
    s.set_axes_locator(_strip_locator(panel_ax, side))
    s.set_xticks([])
    s.set_yticks([])
    s.set_facecolor("#e6e6e6")
    for sp in s.spines.values():
        sp.set_color("#4d4d4d")
        sp.set_linewidth(float(style.spine_width_pt) * 0.8)
    s.set_navigate(False)
    s.text(0.5, 0.5, text, transform=s.transAxes, ha="center", va="center",
           rotation=(270 if side == "right" else 0), fontsize=font_pt, fontweight="bold",
           color=getattr(style, "text_color", "black"))
    s._mmf_facet_strip = side
    return s


def make_facet_grid(spec: Dict[str, Any], work: pd.DataFrame, style, *, row: Optional[str],
                    col: Optional[str], aspect: float, share_x: bool = True,
                    share_y: bool = True) -> FacetGrid:
    """Create the figure, the panels, the strips and the host. Draws no data."""
    import matplotlib.pyplot as plt

    mapping = (spec or {}).get("mapping") or {}
    label_style = str(mapping.get("facet_labels") or "column: value")
    if label_style not in LABEL_STYLES:
        label_style = "column: value"
    rows = facet_levels(work[row]) if row else [None]
    cols = facet_levels(work[col]) if col else [None]
    for var, lv in ((row, rows), (col, cols)):
        if var and len(lv) > MAX_FACET_LEVELS:
            raise RenderError(f"{var!r} has {len(lv)} levels; facets are limited to {MAX_FACET_LEVELS} "
                              "per direction (a figure with more panels is unreadable).")
    nr, nc = len(rows), len(cols)

    # Size: a single-plot figure is one panel; a grid grows with its panels unless
    # the author pinned the size, in which case the panels share what was asked for.
    w_in, h_in = figure_size(spec, style, aspect=aspect)
    pinned_w = requested_width(spec) is not None
    pinned_h = pinned_dimension(spec, "height_mm") is not None
    size_notes: List[str] = []
    extra_w = 1.1 + (0.3 if row else 0.0)
    extra_h = 1.0 + (0.3 if col else 0.0)
    panel_w = w_in * 0.62
    if not pinned_w:
        w_in = panel_w * nc + extra_w
        if w_in > MAX_AUTO_WIDTH_IN:
            w_in = MAX_AUTO_WIDTH_IN
            panel_w = (w_in - extra_w) / nc
    else:
        panel_w = (w_in - extra_w) / nc
    if not pinned_h:
        h_in = panel_w * aspect * nr + extra_h
        if h_in > MAX_AUTO_HEIGHT_IN:
            h_in = MAX_AUTO_HEIGHT_IN
    panel_h = (h_in - extra_h) / nr
    # (the narrow-panel note is measured on the final layout: refit_strips)

    fig = plt.figure(figsize=(w_in, h_in))
    gs = fig.add_gridspec(nr, nc, wspace=0.08 if share_y else 0.28, hspace=0.10 if share_x else 0.32)
    panels: List[FacetPanel] = []
    first = None
    for r, rl in enumerate(rows):
        for c, cl in enumerate(cols):
            kw = {}
            if first is not None:
                if share_x:
                    kw["sharex"] = first
                if share_y:
                    kw["sharey"] = first
            ax = fig.add_subplot(gs[r, c], **kw)
            first = first or ax
            sel = pd.Series(True, index=work.index)
            if row:
                sel &= work[row] == rl
            if col:
                sel &= work[col] == cl
            parts = []
            if row:
                parts.append(strip_text(row, rl, label_style))
            if col:
                parts.append(strip_text(col, cl, label_style))
            panels.append(FacetPanel(rl, cl, r, c, ax, work.loc[sel], " | ".join(parts)))
    strips = []
    for p in panels:
        if col and p.r == 0:
            strips.append(_add_strip(fig, p.ax, strip_text(col, p.col, label_style), "top", style))
        if row and p.c == nc - 1:
            strips.append(_add_strip(fig, p.ax, strip_text(row, p.row, label_style), "right", style))
    host = fig.add_axes([0, 0, 1, 1], label=FACET_HOST_LABEL)
    host.set_axes_locator(_union_locator(fig, [p.ax for p in panels], strips))
    host.patch.set_visible(False)
    for sp in host.spines.values():
        sp.set_visible(False)
    host.tick_params(axis="both", which="both", bottom=False, left=False, top=False, right=False,
                     labelbottom=False, labelleft=False)
    host.set_navigate(False)
    # Above the panels: a legend placed inside the grid must be visible. The host
    # has no face and no frame, so it hides nothing; it cannot be navigated, so
    # zoom and pan still reach the panel under the pointer.
    host.set_zorder(5)
    fig.subplots_adjust(left=0.13, right=0.95 if row else 0.97, bottom=0.12, top=0.92 if col else 0.95)
    grid = FacetGrid(fig, host, panels, row, col, rows, cols, strips,
                     free_axes={"x": not share_x, "y": not share_y}, style=style)
    grid.warnings.extend(size_notes)
    fig._mmf_facets = grid
    register_refit(fig, lambda: _fit_strips(grid))
    return grid


def _outer_tick_labels(grid: FacetGrid) -> None:
    """Tick labels on the outer panels only for a shared axis; on every panel for a
    free one (a free scale without numbers on each panel cannot be read)."""
    nr = max(p.r for p in grid.panels) + 1
    for p in grid.panels:
        p.ax.tick_params(labelbottom=grid.free_axes.get("x", False) or (p.r == nr - 1),
                         labelleft=grid.free_axes.get("y", False) or (p.c == 0))


def finish_facet_grid(grid: FacetGrid, spec: Dict[str, Any], style, *, x_label: str, y_label: str) -> None:
    """Shared labels, title, outer-only tick labels, publication axes styling."""
    layout = (spec or {}).get("layout") or {}
    for p in grid.panels:
        style_axes(p.ax, style)
        p.ax.set_xlabel("")
        p.ax.set_ylabel("")
    _outer_tick_labels(grid)
    host = grid.host
    host.set_xlabel(x_label, fontsize=float(style.axis_font_pt))
    host.set_ylabel(y_label, fontsize=float(style.axis_font_pt))
    title = layout.get("title")
    if title:
        host.set_title(title, fontsize=float(style.title_font_pt), pad=6.0)
    _fit_strips(grid)
    _keep_margins(grid)


def refit_strips(figure) -> List[str]:
    """Re-fit the strip labels after anything that resized the panels (a legend
    reserving a margin, the layout controls, the canvas fit). The strips were
    fitted at the width the grid had before an outside legend took a quarter of
    it, and a 55-character level name then overflowed by 80 px.

    Returns the grid's notes that are new since the renderer handed its own on:
    the narrow-panel note is measured here, on the final layout, because the
    estimate made before the legend took its share quoted 1.4-1.7x the real width.
    """
    grid = getattr(figure, "_mmf_facets", None)
    if grid is None:
        return []
    _fit_strips(grid)
    try:
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        w = min(p.ax.get_window_extent(renderer).width for p in grid.panels) / figure.dpi
        h = min(p.ax.get_window_extent(renderer).height for p in grid.panels) / figure.dpi
        if w < MIN_COMFORTABLE_PANEL_IN or h < MIN_COMFORTABLE_PANEL_IN * 0.6:
            note = (f"Each of the {len(grid.panels)} panels is about {w:.1f} x {h:.1f} in; labels may collide. "
                    "Facet fewer levels, set a larger figure size, or shorten the tick labels.")
            grid.warnings = [n for n in grid.warnings if "panels is about" not in n] + [note]
    except Exception:  # noqa: BLE001
        pass
    seen = set(getattr(grid, "_mmf_reported", ()))
    new = [n for n in grid.warnings if n not in seen]
    grid._mmf_reported = list(seen | set(grid.warnings))
    return new


def _fit_strips(grid: FacetGrid) -> None:
    """Wrap, then shrink, a strip label that is wider than its strip.

    Measured before this: a 120 mm grid printed "Species: SpecSpecies: Species_B"
    across two column strips, and a long level name overflowed by 220 pt.
    Re-run after every layout pass (register_refit), because the pass that makes
    room for a legend narrows the panels and the strips with them.
    """
    import textwrap

    fig = grid.fig
    try:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
    except Exception:  # noqa: BLE001
        return
    for strip in grid.strips:
        if not strip.texts:
            continue
        text = strip.texts[0]
        full = getattr(strip, "_mmf_full_text", text.get_text())
        base_pt = float(getattr(strip, "_mmf_font_pt", 9.0))
        side = getattr(strip, "_mmf_facet_strip", "top")
        box = strip.get_window_extent(renderer)
        room = (box.width if side == "top" else box.height) - 6.0 * fig.dpi / 72.0
        if room <= 0:
            continue

        def width_of(label, pt):
            text.set_text(label)
            text.set_fontsize(pt)
            ext = text.get_window_extent(renderer)
            return ext.width if side == "top" else ext.height

        if width_of(full, base_pt) <= room:
            strip._mmf_lines = 1
            continue
        chars = max(8, int(len(full) * room / max(width_of(full, base_pt), 1.0)))

        def layout(break_words):
            parts = textwrap.wrap(full, chars, break_long_words=break_words)
            text_ = "\n".join(parts[:2])
            return text_[:-1] + "…" if len(parts) > 2 else text_

        # Whole words at a smaller size before a word is broken: "Arabidopsis" at
        # 8 pt reads; "A / rabidopsi…" does not.
        wrapped, pt = layout(False), base_pt
        while width_of(wrapped, pt) > room and pt > base_pt * 0.7:
            pt -= 0.5
        if width_of(wrapped, pt) > room:
            wrapped, pt = layout(True), base_pt
            while width_of(wrapped, pt) > room and pt > base_pt * 0.7:
                pt -= 0.5
        if width_of(wrapped, pt) > room:
            note = (f"The facet label {full!r} does not fit its panel; shorten the level names or "
                    "widen the figure.")
            if note not in grid.warnings:
                grid.warnings.append(note)
        strip._mmf_lines = 2 if "\n" in wrapped else 1


def _label_extent(grid: FacetGrid, renderer, side: str):
    """Pixel extent (min x0 for 'left', min y0 for 'bottom', max y1 for 'top') of the
    grid's outermost labels: the shared axis label, the panels' tick labels, the title."""
    host = grid.host
    vals = []
    if side == "left":
        if host.get_ylabel():
            vals.append(host.yaxis.label.get_window_extent(renderer).x0)
        for p in grid.panels:
            tb = p.ax.yaxis.get_tightbbox(renderer)
            if tb is not None:
                vals.append(tb.x0)
        return min(vals) if vals else None
    if side == "bottom":
        if host.get_xlabel():
            vals.append(host.xaxis.label.get_window_extent(renderer).y0)
        for p in grid.panels:
            tb = p.ax.xaxis.get_tightbbox(renderer)
            if tb is not None:
                vals.append(tb.y0)
        return min(vals) if vals else None
    if side == "top":
        if host.get_title():
            vals.append(host.title.get_window_extent(renderer).y1)
        for st in grid.strips:
            if getattr(st, "_mmf_facet_strip", "") == "top":
                vals.append(st.get_window_extent(renderer).y1)
        return max(vals) if vals else None
    return None


def anchor_host_legend(host, leg, side: Optional[str]) -> None:
    """Move an outside legend clear of the grid's shared labels.

    The legend is anchored to the host, which spans the panels - not the labels
    outside them. Anchored at (-0.02, 0.5) it sat 12 pt over the shared y label;
    at (0.5, -0.18) it overprinted the x label by 4.6 to 50 pt.
    """
    grid = getattr(host.figure, "_mmf_facets", None)
    if grid is None or side not in ("left", "bottom", "top", None):
        return
    try:
        fig = host.figure
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        hb = host.get_window_extent(renderer)
        if side is None:
            # Inside the grid means inside the panels: the host also spans the
            # strips, and "upper left" of it put the key over a column strip.
            boxes = [p.ax.get_window_extent(renderer) for p in grid.panels]
            x0, x1 = min(b.x0 for b in boxes), max(b.x1 for b in boxes)
            y0, y1 = min(b.y0 for b in boxes), max(b.y1 for b in boxes)
            leg.set_bbox_to_anchor(Bbox([[(x0 - hb.x0) / hb.width, (y0 - hb.y0) / hb.height],
                                         [(x1 - hb.x0) / hb.width, (y1 - hb.y0) / hb.height]]),
                                   transform=host.transAxes)
            return
        edge = _label_extent(grid, renderer, side)
        if edge is None or not hb.width or not hb.height:
            return
        gap = _LEGEND_LABEL_GAP_PT * fig.dpi / 72.0
        if side == "left":
            leg.set_bbox_to_anchor((-(hb.x0 - edge + gap) / hb.width, 0.5))
        elif side == "bottom":
            leg.set_bbox_to_anchor((0.5, -(hb.y0 - edge + gap) / hb.height))
        else:
            leg.set_bbox_to_anchor((0.5, (edge - hb.y0 + gap) / hb.height))
        host._mmf_legend_side = side
    except Exception:  # noqa: BLE001 - placement nicety, never break a render
        pass


def reserve_host_extra(host, side: str) -> None:
    """Add to the figure margin what lies between the host and the legend: the
    row strips on the right, the shared labels on the left. The shared reserve
    measures the legend alone, so a default grid was always "widened to fit"."""
    grid = getattr(host.figure, "_mmf_facets", None)
    if grid is None:
        return
    try:
        fig = host.figure
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        hb = host.get_window_extent(renderer)
        w_px = fig.bbox.width
        pars = fig.subplotpars
        if side == "right":
            right_edge = max([p.ax.get_window_extent(renderer).x1 for p in grid.panels])
            extra = (hb.x1 - right_edge + 0.02 * hb.width) / w_px
            fig.subplots_adjust(right=max(0.55, pars.right - extra))
        elif side == "left":
            edge = _label_extent(grid, renderer, "left")
            if edge is not None:
                extra = (hb.x0 - edge + _LEGEND_LABEL_GAP_PT * fig.dpi / 72.0) / w_px
                fig.subplots_adjust(left=min(0.45, pars.left + extra))
        elif side in ("bottom", "top"):
            # The fixed 22 % / 18 % reserve is right for one figure height and
            # wrong for a one-row grid, where the key still hung 17-22 pt below
            # the canvas: reserve what the key and the labels measure.
            leg = host.get_legend()
            if leg is None:
                return
            h_px = fig.bbox.height
            lb = leg.get_window_extent(renderer)
            gap = _LEGEND_LABEL_GAP_PT * fig.dpi / 72.0
            if side == "bottom":
                edge = _label_extent(grid, renderer, "bottom")
                labels = (hb.y0 - edge) if edge is not None else 0.0
                need = (lb.height + labels + 2 * gap + GRID_MARGIN_IN * fig.dpi) / h_px
                fig.subplots_adjust(bottom=min(0.45, max(pars.bottom, need)))
            else:
                edge = _label_extent(grid, renderer, "top")
                above = (edge - hb.y1) if edge is not None else 0.0
                need = (lb.height + above + 2 * gap + GRID_MARGIN_IN * fig.dpi) / h_px
                fig.subplots_adjust(top=max(0.55, min(pars.top, 1.0 - need)))
    except Exception:  # noqa: BLE001
        pass


# Breathing room between the grid's outermost text and the canvas edge, in inches.
# The canvas-fitting pass only guarantees the content is inside the canvas; the
# desktop preview then draws the figure a little smaller than it was laid out,
# with the text at its fixed point size, and a title 0.007 in from the top edge
# (measured) was cut off there. Ordinary plots get this room from tight_layout.
GRID_MARGIN_IN = 0.10


def _keep_margins(grid: FacetGrid) -> None:
    fig = grid.fig
    try:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        tight = fig.get_tightbbox(renderer)
        # The title's width is not a margin problem: an over-long title is
        # wrapped by the shared title pass afterwards, and reacting to it here
        # squeezed the panels to 1 in on a 7.75 in figure.
        title = grid.host.title
        was_visible = title.get_visible()
        title.set_visible(False)
        sides = fig.get_tightbbox(renderer)
        title.set_visible(was_visible)
        w_in, h_in = (float(v) for v in fig.get_size_inches())
        pars = fig.subplotpars
        left, right, bottom, top = pars.left, pars.right, pars.bottom, pars.top
        need_t = min(0.15, max(0.0, tight.y1 - (h_in - GRID_MARGIN_IN)) / h_in)
        need_b = max(0.0, GRID_MARGIN_IN - sides.y0) / h_in
        need_l = max(0.0, GRID_MARGIN_IN - sides.x0) / w_in
        need_r = max(0.0, sides.x1 - (w_in - GRID_MARGIN_IN)) / w_in
        if need_t or need_b or need_l or need_r:
            fig.subplots_adjust(left=min(0.45, left + need_l), right=max(0.55, right - need_r),
                                bottom=min(0.45, bottom + need_b), top=max(0.55, top - need_t))
    except Exception:  # noqa: BLE001 - a margin nicety never breaks a render
        pass


def facet_axes(figure) -> List[Any]:
    """The data panels of a facet figure (empty for an ordinary figure)."""
    grid = getattr(figure, "_mmf_facets", None)
    return list(grid.axes) if grid is not None else []


def facet_host(figure):
    grid = getattr(figure, "_mmf_facets", None)
    return grid.host if grid is not None else None


def apply_facet_layout(figure, spec: Dict[str, Any], style) -> None:
    """The shared layout block, applied to a facet grid.

    Tick angle / padding / visibility and figure margins act on every panel;
    axis-label visibility and padding and the title padding act on the shared
    labels and title, which belong to the host.
    """
    from make_my_figure_core.plots.base import apply_publication_layout

    grid = getattr(figure, "_mmf_facets", None)
    if grid is None:
        return
    layout = dict((spec or {}).get("layout") or {})
    host_keys = ("show_x_label", "show_y_label", "x_label_pad", "y_label_pad", "title_pad", "title",
                 "x_label", "y_label")
    panel_layout = {k: v for k, v in layout.items() if k not in host_keys}
    panel_spec = {**spec, "layout": panel_layout}
    nr = max(p.r for p in grid.panels) + 1
    for p in grid.panels:
        apply_publication_layout(figure, p.ax, panel_spec, style)
        # Shared axes: only the outer panels carry tick labels, whatever else the
        # layout set (hiding them altogether is still honoured above).
        if layout.get("show_x_tick_labels") is not False:
            p.ax.tick_params(labelbottom=grid.free_axes.get("x", False) or (p.r == nr - 1))
        if layout.get("show_y_tick_labels") is not False:
            p.ax.tick_params(labelleft=grid.free_axes.get("y", False) or (p.c == 0))
    host = grid.host
    if layout.get("show_x_label") is False:
        host.set_xlabel("")
    if layout.get("show_y_label") is False:
        host.set_ylabel("")
    for key, attr in (("x_label_pad", "_mmf_user_xpad"), ("y_label_pad", "_mmf_user_ypad")):
        try:
            if layout.get(key) is not None:
                setattr(host, attr, float(layout[key]))
        except (TypeError, ValueError):
            pass
    try:
        if layout.get("title_pad") is not None and host.get_title():
            host.set_title(host.get_title(), pad=float(layout["title_pad"]),
                           fontsize=float(style.title_font_pt))
    except (TypeError, ValueError):
        pass


def shared_value_limits(grid: FacetGrid, lo: float, hi: float, *, axis: str = "y") -> None:
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return
    for p in grid.panels:
        (p.ax.set_ylim if axis == "y" else p.ax.set_xlim)(lo, hi)


def empty_panel_note(ax, style) -> None:
    ax.text(0.5, 0.5, "no observations", transform=ax.transAxes, ha="center", va="center",
            fontsize=float(style.annotation_pt), color="0.45", style="italic")


def facet_metadata(grid: FacetGrid) -> Dict[str, Any]:
    return {"row": grid.row_var, "col": grid.col_var,
            "rows": [_fmt_level(r) for r in grid.rows if r is not None],
            "cols": [_fmt_level(c) for c in grid.cols if c is not None],
            "panels": [{"label": p.label, "n": int(len(p.data))} for p in grid.panels]}
