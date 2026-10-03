"""Geometry checks on a rendered figure: text overlap, clipping, legend collision, physical size.

These checks look at the *drawn* figure - the text bounding boxes matplotlib actually produced -
rather than at the spec. They exist for the preset library QC ("does this preset, on this plot
type, at this width, still produce readable text?") and for the preview dialog, which can warn
before the user applies.

The rule of the preset QC is fixed here in code: overlap is reported as a problem and never
"solved" by shrinking text. The checks only measure; the fix is a layout decision (more height,
fewer ticks, legend outside, rotated labels) that the preset author or the user makes.

All sizes are absolute. Font sizes are in points as drawn; when the figure is exported with a
tight bounding box its physical width can differ from the requested width, so
``effective_min_font_pt`` rescales the smallest font to the size it would have once the figure is
scaled to ``target_width_mm``. That is the number to compare with a publisher's minimum.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import matplotlib
from matplotlib.figure import Figure
from matplotlib.text import Text
from matplotlib.transforms import Bbox

MM_PER_INCH = 25.4


@dataclass
class TextBox:
    text: str
    bbox: Bbox
    fontsize_pt: float
    role: str            # 'tick' | 'label' | 'title' | 'legend' | 'annotation' | 'other'
    axes_index: int      # -1 for figure-level text


@dataclass
class LayoutQC:
    n_text: int = 0
    n_overlapping_pairs: int = 0
    overlapping_pairs: List[Tuple[str, str, float]] = field(default_factory=list)  # (a, b, px)
    n_clipped: int = 0
    clipped: List[str] = field(default_factory=list)
    legend_overlaps_data: bool = False
    legend_overlap_fraction: float = 0.0
    min_font_pt: Optional[float] = None
    min_font_role: str = ""
    effective_min_font_pt: Optional[float] = None
    drawn_width_mm: Optional[float] = None
    drawn_height_mm: Optional[float] = None
    tight_width_mm: Optional[float] = None
    tight_height_mm: Optional[float] = None
    target_width_mm: Optional[float] = None
    width_deviation_pct: Optional[float] = None
    tick_label_counts: Dict[str, int] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.issues

    def as_row(self) -> Dict[str, Any]:
        return {
            "n_text": self.n_text,
            "overlapping_text_pairs": self.n_overlapping_pairs,
            "clipped_text": self.n_clipped,
            "legend_overlaps_data": self.legend_overlaps_data,
            "legend_overlap_fraction": round(self.legend_overlap_fraction, 3),
            "min_font_pt": self.min_font_pt,
            "min_font_role": self.min_font_role,
            "effective_min_font_pt": self.effective_min_font_pt,
            "drawn_width_mm": self.drawn_width_mm,
            "tight_width_mm": self.tight_width_mm,
            "tight_height_mm": self.tight_height_mm,
            "target_width_mm": self.target_width_mm,
            "width_deviation_pct": self.width_deviation_pct,
            "max_tick_labels_on_one_axis": max(self.tick_label_counts.values(), default=0),
            "issues": "; ".join(self.issues),
        }


def _visible_texts(fig: Figure, renderer) -> List[TextBox]:
    boxes: List[TextBox] = []

    def add(t: Text, role: str, ax_i: int) -> None:
        if not isinstance(t, Text) or not t.get_visible():
            return
        s = t.get_text()
        if not s or not s.strip():
            return
        try:
            bb = t.get_window_extent(renderer=renderer)
        except Exception:  # noqa: BLE001 - an artist that cannot report an extent is skipped
            return
        if bb.width <= 0 or bb.height <= 0:
            return
        boxes.append(TextBox(s, bb, float(t.get_fontsize()), role, ax_i))

    for i, ax in enumerate(fig.axes):
        for t in ax.get_xticklabels() + ax.get_yticklabels():
            add(t, "tick", i)
        for t in ax.get_xticklabels(minor=True) + ax.get_yticklabels(minor=True):
            add(t, "tick", i)
        add(ax.xaxis.label, "label", i)
        add(ax.yaxis.label, "label", i)
        add(ax.title, "title", i)
        add(ax._left_title, "title", i)   # noqa: SLF001
        add(ax._right_title, "title", i)  # noqa: SLF001
        leg = ax.get_legend()
        if leg is not None and leg.get_visible():
            for t in leg.get_texts():
                add(t, "legend", i)
            if leg.get_title() is not None:
                add(leg.get_title(), "legend", i)
        for t in ax.texts:
            add(t, "annotation", i)
    for t in fig.texts:
        add(t, "other", -1)
    for leg in getattr(fig, "legends", []):
        for t in leg.get_texts():
            add(t, "legend", -1)
    return boxes


def _intersection_area(a: Bbox, b: Bbox) -> float:
    x0, y0 = max(a.x0, b.x0), max(a.y0, b.y0)
    x1, y1 = min(a.x1, b.x1), min(a.y1, b.y1)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return (x1 - x0) * (y1 - y0)


def _legend_data_collision(ax, legend_bbox: Bbox, renderer) -> float:
    """Fraction of the legend box that sits on drawn data marks.

    A bounding-box test is useless for a line that spans the axes (its box *is* the axes), so
    lines and scatter collections are tested by their actual vertices: the fraction of a coarse
    grid of legend-box cells that contain at least one data vertex. Bars, boxes and images are
    tested by area intersection.
    """
    import numpy as np

    if legend_bbox.width <= 0 or legend_bbox.height <= 0:
        return 0.0
    # collect data vertices in display coordinates
    pts = []
    for line in ax.lines:
        if not line.get_visible():
            continue
        xy = line.get_xydata()
        if len(xy) == 0:
            continue
        disp = line.get_transform().transform(xy)
        pts.append(disp[np.isfinite(disp).all(axis=1)])
        # a polyline also covers the segments between vertices - sample them
        if len(disp) > 1:
            seg = np.linspace(0.0, 1.0, 8)[1:-1]
            a, b = disp[:-1], disp[1:]
            inter = (a[:, None, :] * (1 - seg)[None, :, None] + b[:, None, :] * seg[None, :, None])
            inter = inter.reshape(-1, 2)
            pts.append(inter[np.isfinite(inter).all(axis=1)])
    for coll in ax.collections:
        if not coll.get_visible():
            continue
        offs = coll.get_offsets()
        if offs is not None and len(offs):
            disp = coll.get_offset_transform().transform(np.asarray(offs, dtype=float))
            pts.append(disp[np.isfinite(disp).all(axis=1)])
    area_cover = 0.0
    for art in list(ax.patches) + list(ax.images):
        if not art.get_visible():
            continue
        try:
            bb = art.get_window_extent(renderer=renderer)
        except Exception:  # noqa: BLE001
            continue
        if bb.width > 0 and bb.height > 0:
            area_cover += _intersection_area(legend_bbox, bb)
    area_frac = min(1.0, area_cover / (legend_bbox.width * legend_bbox.height))
    if not pts:
        return area_frac
    allpts = np.vstack(pts)
    inside = allpts[(allpts[:, 0] >= legend_bbox.x0) & (allpts[:, 0] <= legend_bbox.x1)
                    & (allpts[:, 1] >= legend_bbox.y0) & (allpts[:, 1] <= legend_bbox.y1)]
    if len(inside) == 0:
        return area_frac
    nx, ny = 6, 4
    cx = np.minimum(((inside[:, 0] - legend_bbox.x0) / legend_bbox.width * nx).astype(int), nx - 1)
    cy = np.minimum(((inside[:, 1] - legend_bbox.y0) / legend_bbox.height * ny).astype(int), ny - 1)
    cells = len(set(zip(cx.tolist(), cy.tolist())))
    return max(area_frac, cells / float(nx * ny))


def check_text_layout(fig: Figure, *, target_width_mm: Optional[float] = None,
                      min_font_pt: Optional[float] = None,
                      overlap_tolerance_px: float = 1.0,
                      ignore_same_role_pairs: Sequence[str] = ()) -> LayoutQC:
    """Measure text overlap, clipping, legend collision and physical size of a drawn figure.

    ``target_width_mm``: the width the figure is meant to occupy on the page. When given, the
    tight-bbox width is compared with it and ``effective_min_font_pt`` is computed.
    ``min_font_pt``: a required minimum (for example a publisher's stated minimum). When given,
    an effective size below it becomes an issue.
    """
    canvas = fig.canvas
    if canvas is None or not hasattr(canvas, "get_renderer"):
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        FigureCanvasAgg(fig)
        canvas = fig.canvas
    fig.canvas.draw()
    renderer = canvas.get_renderer()
    qc = LayoutQC(target_width_mm=target_width_mm)

    boxes = _visible_texts(fig, renderer)
    qc.n_text = len(boxes)

    # --- overlap ---------------------------------------------------------------------------
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            if a.role in ignore_same_role_pairs and a.role == b.role:
                continue
            area = _intersection_area(a.bbox, b.bbox)
            if area <= 0:
                continue
            # tolerance: a hairline touch is not an overlap
            x_over = min(a.bbox.x1, b.bbox.x1) - max(a.bbox.x0, b.bbox.x0)
            y_over = min(a.bbox.y1, b.bbox.y1) - max(a.bbox.y0, b.bbox.y0)
            if x_over <= overlap_tolerance_px or y_over <= overlap_tolerance_px:
                continue
            qc.overlapping_pairs.append((a.text, b.text, round(min(x_over, y_over), 1)))
    qc.n_overlapping_pairs = len(qc.overlapping_pairs)

    # --- clipping (text outside the figure canvas; tight export cannot recover negative) ---
    # Tight-bbox export expands the canvas to include text at the figure edge, so the only real
    # clipping is an annotation with clip_on that extends beyond its axes box.
    for i, ax in enumerate(fig.axes):
        ax_bb = ax.get_window_extent(renderer=renderer)
        for t in ax.texts:
            if not t.get_visible() or not t.get_text().strip() or not t.get_clip_on():
                continue
            bb = t.get_window_extent(renderer=renderer)
            if bb.x0 < ax_bb.x0 - 0.5 or bb.x1 > ax_bb.x1 + 0.5 or bb.y0 < ax_bb.y0 - 0.5 or bb.y1 > ax_bb.y1 + 0.5:
                qc.clipped.append(t.get_text())
    qc.n_clipped = len(qc.clipped)

    # --- legend over data ------------------------------------------------------------------
    worst = 0.0
    for ax in fig.axes:
        leg = ax.get_legend()
        if leg is None or not leg.get_visible():
            continue
        lbb = leg.get_window_extent(renderer=renderer)
        if lbb.width <= 0 or lbb.height <= 0:
            continue
        worst = max(worst, _legend_data_collision(ax, lbb, renderer))
    qc.legend_overlap_fraction = float(worst)
    # a collision is when a meaningful part of the legend box sits on data marks
    qc.legend_overlaps_data = bool(worst > 0.15)

    # --- fonts -----------------------------------------------------------------------------
    if boxes:
        smallest = min(boxes, key=lambda b: b.fontsize_pt)
        qc.min_font_pt = round(smallest.fontsize_pt, 2)
        qc.min_font_role = smallest.role

    # --- physical size ---------------------------------------------------------------------
    w_in, h_in = fig.get_size_inches()
    qc.drawn_width_mm = round(float(w_in) * MM_PER_INCH, 1)
    qc.drawn_height_mm = round(float(h_in) * MM_PER_INCH, 1)
    try:
        tight = fig.get_tightbbox(renderer)
        qc.tight_width_mm = round(float(tight.width) * MM_PER_INCH, 1)
        qc.tight_height_mm = round(float(tight.height) * MM_PER_INCH, 1)
    except Exception:  # noqa: BLE001
        qc.tight_width_mm = qc.drawn_width_mm
        qc.tight_height_mm = qc.drawn_height_mm
    if target_width_mm and qc.tight_width_mm:
        qc.width_deviation_pct = round(float(100.0 * (qc.tight_width_mm - target_width_mm) / target_width_mm), 1)
        if qc.min_font_pt is not None:
            qc.effective_min_font_pt = round(float(qc.min_font_pt * target_width_mm / qc.tight_width_mm), 2)
    elif qc.min_font_pt is not None:
        qc.effective_min_font_pt = qc.min_font_pt

    # --- tick counts -----------------------------------------------------------------------
    for i, ax in enumerate(fig.axes):
        nx = len([t for t in ax.get_xticklabels() if t.get_visible() and t.get_text().strip()])
        ny = len([t for t in ax.get_yticklabels() if t.get_visible() and t.get_text().strip()])
        qc.tick_label_counts[f"ax{i}.x"] = nx
        qc.tick_label_counts[f"ax{i}.y"] = ny

    # --- issues ----------------------------------------------------------------------------
    if qc.n_overlapping_pairs:
        qc.issues.append(f"{qc.n_overlapping_pairs} overlapping text pair(s)")
    if qc.n_clipped:
        qc.issues.append(f"{qc.n_clipped} clipped annotation(s)")
    if qc.legend_overlaps_data:
        qc.issues.append(f"legend covers data ({qc.legend_overlap_fraction:.0%} of legend box)")
    if min_font_pt is not None and qc.effective_min_font_pt is not None \
            and qc.effective_min_font_pt < min_font_pt - 0.05:
        qc.issues.append(
            f"smallest text {qc.effective_min_font_pt} pt at {target_width_mm} mm "
            f"(minimum {min_font_pt} pt; role {qc.min_font_role})")
    if qc.width_deviation_pct is not None and abs(qc.width_deviation_pct) > 15:
        qc.issues.append(
            f"exported width {qc.tight_width_mm} mm deviates {qc.width_deviation_pct:+.0f}% "
            f"from target {target_width_mm} mm")
    return qc
