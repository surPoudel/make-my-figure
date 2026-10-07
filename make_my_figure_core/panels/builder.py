"""Compose panels into a labelled multi-panel figure and export it.

Panels are rendered (from their PlotSpec if not pre-rendered) and embedded as
high-resolution images in a clean grid, with bold vector panel labels drawn on
the composite. Each individual panel remains independently exportable as vector
(SVG/PDF) from its own PlotSpec; the composite embeds panel *content* as
``panel_dpi`` raster while keeping labels/titles as editable vector text. This
is a deliberate, documented trade-off that always produces a correct, aligned
figure without a fragile SVG-splicing step.

**Alignment is measured, not assumed.** A panel is a picture of a plot with its
own y-axis label, tick numbers, legend and colourbar wrapped around it, and
those decorations are a different width in every panel. Laying the *pictures*
out in a tidy grid therefore leaves the *plots* inside them out of line, and
changing one panel's width moves its neighbours' plots sideways. So every panel
is drawn once and measured - where does its plotting frame sit inside its own
picture? - and then placed so that the frames share one left edge down each
column and one top edge across each row. That is the only placement rule in
here, and it is what makes a panel's width a local change.
"""

from __future__ import annotations

import io
import json
import math
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.transforms import Bbox

from make_my_figure_core.panels.models import FigureLayout, MultiPanelFigure, Panel
from make_my_figure_core.styles.engine import mm_to_inches

_VECTOR_TEXT_RC = {"svg.fonttype": "none", "pdf.fonttype": 42, "ps.fonttype": 42}


def _render_panel_figure(panel: Panel, font_overrides: Optional[Dict[str, Any]] = None,
                         size_in: Optional[Tuple[float, Optional[float]]] = None,
                         typo_scale: Optional[float] = None) -> Figure:
    """Return the panel's Figure, rendering from its PlotSpec if needed.

    ``font_overrides`` (figure-level font sizes) are merged into the panel's
    style overrides so the whole composite stays typographically consistent.
    A pre-rendered figure is returned as-is (fonts were fixed at render time).

    ``size_in`` is ``(width, height)`` in inches for the panel's own canvas. It
    is the mechanism behind the per-panel size controls: a panel asked to be
    taller is *drawn* taller (pinned ``layout.width_mm``/``height_mm``, which
    every renderer already honours) rather than having its finished image
    stretched, so the axes grow and nothing in the plot is distorted. A ``None``
    height pins the width alone and lets the plot keep its own proportions,
    which is how a panel added to a figure arrives at exactly the shape it was
    finalized with. Render warnings from a size the plot type had to correct are
    stashed on the figure for the caller to surface; they are the user's only
    clue that a request was adjusted.
    """
    if panel.figure is not None:
        return panel.figure
    if panel.plot_spec is None or panel.table is None:
        raise ValueError(f"Panel '{panel.label}' has neither a figure nor a plot_spec+table.")
    from make_my_figure_core.plots.registry import render

    spec = dict(panel.plot_spec)
    if panel.stats_spec is not None and "statistics" not in spec:
        spec["statistics"] = panel.stats_spec
    if font_overrides:
        # Figure-level fonts win over the panel's own so panels match; a panel
        # that set a token explicitly still keeps anything not overridden here.
        spec["style"] = {**(spec.get("style") or {}), **font_overrides}
    if size_in is not None:
        w_in = float(size_in[0])
        h_in = None if size_in[1] is None else float(size_in[1])
        if w_in > 0:
            lay = {**(spec.get("layout") or {}), "width_mm": w_in * 25.4}
            if h_in is not None and h_in > 0:
                lay["height_mm"] = h_in * 25.4
            else:
                # Pinning the width alone: drop the height the panel was
                # finalized at so the plot type recomputes its own proportions
                # for this width instead of being squeezed into the old one.
                lay.pop("height_mm", None)
            spec["layout"] = lay
    if font_overrides:
        # The figure-level font sizes are a choice about the whole composite, so
        # they must land on the page as the same points in every panel. Letting
        # each panel scale type to its own canvas is what produced a 1.42x spread
        # between panels asked to share one setting.
        spec["layout"] = {**(spec.get("layout") or {}), "scale_typography": False}
    elif typo_scale is not None and typo_scale > 0:
        # Same reasoning, one step earlier: without explicit sizes the panels
        # still have to share ONE type hierarchy, so the composite works out a
        # single factor for the whole figure and every panel is scaled by it.
        # Per-canvas scaling put 12 pt axis labels next to 10.2 pt ones.
        spec["layout"] = {**(spec.get("layout") or {}),
                          "typography_scale": float(typo_scale)}
    aux = panel.aux or None
    result = render(spec, panel.table, aux=aux)
    fig = result.figure
    fig._mmf_render_warnings = list(result.warnings)  # type: ignore[attr-defined]
    return fig


def _can_resize(panel: Panel) -> bool:
    """True when the panel can be *re-drawn* at a requested size.

    Only a panel that still carries its PlotSpec + table can honour a size by
    rendering at it. A pre-rendered figure or an imported image has a fixed
    aspect, so for those a requested height can only scale the finished picture.
    """
    return (not panel.is_external and panel.figure is None
            and panel.plot_spec is not None and panel.table is not None)


# ---------------------------------------------------------------------------
# Measuring a panel
# ---------------------------------------------------------------------------

# Axes that are decoration rather than a plotting frame. A colourbar is part of
# the panel's picture but it is not the thing that has to line up with the bar
# chart next door - it belongs in the margin, like a legend.
_DECORATION_AXES_LABELS = ("<colorbar>",)


def _is_decoration_axes(ax: Any) -> bool:
    return (getattr(ax, "_colorbar", None) is not None
            or str(ax.get_label()) in _DECORATION_AXES_LABELS)


def _data_axes(fig: Figure) -> List[Any]:
    return [ax for ax in fig.axes if ax.get_visible() and not _is_decoration_axes(ax)]


@dataclass(frozen=True)
class _PanelGeometry:
    """Where a rendered panel's plotting frame sits inside its own picture.

    ``box`` is the region that gets saved as the panel image and ``axes`` the
    union of its data axes, both in inches in the panel canvas's coordinates
    (origin bottom-left). Everything the compositor does with a panel is a
    function of the two pads below: a panel is placed by its frame, so a wide
    y-axis label pushes the picture left instead of pushing the plot right.
    """

    box: Bbox
    axes: Bbox
    overflow: float = 0.0          # inches of content that spilled off the canvas
    ink: Optional[Bbox] = None     # the drawn content, without the canvas margin

    @property
    def pad_left(self) -> float:
        return float(self.axes.x0 - self.box.x0)

    @property
    def pad_top(self) -> float:
        return float(self.box.y1 - self.axes.y1)

    @property
    def width(self) -> float:
        return float(self.box.width)

    @property
    def height(self) -> float:
        return float(self.box.height)

    def scaled(self, factor: float) -> "_PanelGeometry":
        """The same geometry for a picture scaled by ``factor``.

        Used for a panel that cannot be re-drawn: scaling the finished picture
        scales its margins with it, so its frame still lands where it should.
        """
        def _mul(b: Bbox) -> Bbox:
            return Bbox([[b.x0 * factor, b.y0 * factor], [b.x1 * factor, b.y1 * factor]])

        return _PanelGeometry(box=_mul(self.box), axes=_mul(self.axes),
                              overflow=self.overflow * factor,
                              ink=_mul(self.ink) if self.ink is not None else None)


def _measure_panel(fig: Figure) -> _PanelGeometry:
    """Measure a rendered panel: its image box and its plotting frame.

    The image box is the canvas *plus* anything drawn outside it. Trimming to
    the canvas is what cut "(mean +/- SEM)" off the end of a y-axis label: a
    renderer that could not fit a label in the width it was given leaves it
    hanging over the edge, and the composite must show that rather than crop it
    (the overflow is reported so the user can widen the panel).
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    w_in, h_in = (float(v) for v in fig.get_size_inches())
    canvas = Bbox([[0.0, 0.0], [w_in, h_in]])
    try:
        tight = fig.get_tightbbox(renderer)
    except Exception:  # noqa: BLE001 - a measurement must never break a build
        tight = None
    box = Bbox.union([canvas, tight]) if tight is not None else canvas
    overflow = 0.0
    if tight is not None:
        overflow = max(canvas.x0 - tight.x0, tight.x1 - canvas.x1,
                       canvas.y0 - tight.y0, tight.y1 - canvas.y1, 0.0)
    boxes = []
    for ax in _data_axes(fig):
        try:
            ext = ax.get_window_extent(renderer)
        except Exception:  # noqa: BLE001
            continue
        boxes.append(Bbox([[ext.x0 / fig.dpi, ext.y0 / fig.dpi],
                           [ext.x1 / fig.dpi, ext.y1 / fig.dpi]]))
    axes = Bbox.union(boxes) if boxes else box
    return _PanelGeometry(box=box, axes=axes, overflow=overflow,
                          ink=tight if tight is not None else box)


# Breathing room left around a panel's content when its margins are fitted, in
# inches. Not zero: a frame line is drawn ON the axes boundary, and a hairline
# of white keeps it from touching the neighbouring panel.
DEFAULT_PANEL_PAD_IN = 0.02

# How much plotting room fitting the margins may cost, in inches. Fitting
# normally GIVES room; it takes a little back when the renderer's own margin was
# a hair too small for its longest label, and that is worth having. Anything
# more means the renderer was holding space on purpose.
MAX_FIT_GIVEBACK_IN = 0.03

# A panel whose decorations would leave the plot less than this fraction of its
# canvas is not fitted - something unusual is going on in that figure and the
# renderer's own layout is the better guess.
_MIN_FITTED_SPAN = 0.2


def _fit_panel_margins(fig: Figure, pad_in: float = DEFAULT_PANEL_PAD_IN) -> bool:
    """Give the plot the room the panel's own margin was holding.

    A renderer sizes its margins as a FRACTION of its canvas, so a panel drawn
    bigger gets a proportionally bigger margin even though its axis labels need
    the same inches. In a composite that costs twice: the plot is smaller than
    the panel it was given (a 3.2 in panel drew a 2.38 in plot), and the margin
    GROWS when the panel is widened - which moves the column's alignment line,
    so widening one panel nudged its neighbours' plots. Re-setting the margins
    to what the decorations actually measure fixes both, and is what makes the
    panel's white space the user's to spend rather than the renderer's.

    Returns False, leaving the figure untouched, when the figure is not laid out
    in a way this can safely change.
    """
    try:
        engine = fig.get_layout_engine()
        # ``adjust_compatible`` is matplotlib's own answer to "may I call
        # subplots_adjust on this figure?". It is False for constrained layout,
        # which owns the margins; it is True for the placeholder engine a
        # finished ``tight_layout`` leaves behind, which does not.
        if engine is not None and not getattr(engine, "adjust_compatible", True):
            return False
    except AttributeError:         # pragma: no cover - older matplotlib
        pass
    axes = _data_axes(fig)
    if not axes or any(ax.get_subplotspec() is None for ax in axes):
        return False               # add_axes() panels: subplots_adjust cannot move them
    before = {ax: ax.get_position().frozen() for ax in axes}
    pars = fig.subplotpars
    saved = {k: getattr(pars, k) for k in ("left", "right", "bottom", "top")}
    try:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        w_in, h_in = (float(v) for v in fig.get_size_inches())
        tight = fig.get_tightbbox(renderer)
        frame = Bbox.union([Bbox([[a.get_window_extent(renderer).x0 / fig.dpi,
                                   a.get_window_extent(renderer).y0 / fig.dpi],
                                  [a.get_window_extent(renderer).x1 / fig.dpi,
                                   a.get_window_extent(renderer).y1 / fig.dpi]])
                            for a in axes])
        if tight is None or w_in <= 0 or h_in <= 0:
            return False
        # What the decorations on each side actually measure, in inches.
        need = (frame.x0 - tight.x0, tight.x1 - frame.x1,
                frame.y0 - tight.y0, tight.y1 - frame.y1)
        if any(v < -1e-6 for v in need):
            return False
        left = (need[0] + pad_in) / w_in
        right = 1.0 - (need[1] + pad_in) / w_in
        bottom = (need[2] + pad_in) / h_in
        top = 1.0 - (need[3] + pad_in) / h_in
        if (right - left) < _MIN_FITTED_SPAN or (top - bottom) < _MIN_FITTED_SPAN:
            return False
        # Never takes a meaningful amount of room AWAY from the plot: a renderer
        # that deliberately left space for something this cannot see keeps the
        # layout it chose. The threshold is a hundredth of an inch rather than
        # zero because most renderers have already fitted their margins to
        # within a hairline - and sometimes a hairline the wrong way, with the
        # longest legend label over the canvas edge by 0.02 in. Refusing those
        # panels over a rounding difference was what left their pads a fraction
        # of the canvas instead of a measurement in inches, and so let the
        # column's alignment line drift when a panel was drawn wider.
        # Room reclaimed from a side whose content is currently hanging off the
        # canvas is not a giveback - it is the fix. Only room taken from a side
        # that already fitted counts against the budget.
        spills = (max(0.0, -tight.x0), max(0.0, tight.x1 - w_in),
                  max(0.0, -tight.y0), max(0.0, tight.y1 - h_in))
        givebacks = ((left - saved["left"]) * w_in, (saved["right"] - right) * w_in,
                     (bottom - saved["bottom"]) * h_in, (saved["top"] - top) * h_in)
        if max(g - s for g, s in zip(givebacks, spills)) > MAX_FIT_GIVEBACK_IN:
            return False
        fig.subplots_adjust(left=left, right=right, bottom=bottom, top=top)
        fig.canvas.draw()
        moved = any(before[ax] != ax.get_position() for ax in axes)
        after = fig.get_tightbbox(fig.canvas.get_renderer())
        spill = max(0.0 - after.x0, after.x1 - w_in, 0.0 - after.y0, after.y1 - h_in, 0.0)
        if not moved or spill > pad_in + 0.02:
            fig.subplots_adjust(**saved)      # no better, or now hanging off the edge
            return False
        return True
    except Exception:  # noqa: BLE001 - a layout nicety must never break a build
        try:
            fig.subplots_adjust(**saved)
        except Exception:  # noqa: BLE001
            pass
        return False


def _figure_to_image(fig: Figure, dpi: int, box: Optional[Bbox] = None, *,
                     keep_canvas: bool = False) -> np.ndarray:
    """Rasterize a figure to an RGBA image array.

    ``box`` is the region to save, in inches on the panel canvas, as measured by
    :func:`_measure_panel`; the compositor places exactly this box, so the two
    have to agree. Without one, the figure is trimmed to its content (the old
    behaviour) or saved whole with ``keep_canvas``.
    """
    buf = io.BytesIO()
    if box is None:
        box = None if keep_canvas else "tight"
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches=box,
                facecolor=fig.get_facecolor())
    buf.seek(0)
    img = plt.imread(buf)
    buf.close()
    return img


def _external_panel_image(panel: Panel) -> Tuple[np.ndarray, List[str]]:
    """Load + process an imported external panel's asset into an RGBA array."""
    from make_my_figure_core import figure_import as fi

    if not panel.image_path:
        raise ValueError(f"Panel '{panel.label}' is external but has no image_path.")
    dpi = int(panel.image_meta.get("rasterization_dpi") or fi.DEFAULT_RASTER_DPI)
    res = fi.import_asset(panel.image_path, os.path.dirname(panel.image_path) or ".",
                          rasterize_dpi=dpi, pdf_page=int(panel.image_meta.get("page", 0)))
    if res.error:
        raise ValueError(f"Panel '{panel.label}': {res.error}")
    arr = fi.process_image(res.image, crop=panel.crop or None, rotate=panel.rotate,
                           flip_h=panel.flip_h, flip_v=panel.flip_v,
                           auto_trim=panel.auto_trim, background=panel.background)
    warns = list(res.warnings) + fi.resolution_warnings(res.metadata, panel.width_in)
    return arr, warns


def _auto_grid(n: int, layout: FigureLayout) -> Tuple[int, int]:
    if layout.ncols and layout.ncols > 0:
        ncols = int(layout.ncols)
    else:
        ncols = max(1, int(math.ceil(math.sqrt(n))))
    nrows = layout.nrows if (layout.nrows and layout.nrows > 0) else int(math.ceil(n / ncols))
    return nrows, ncols


def _measured_typography(fig: Figure) -> Dict[str, float]:
    """The type sizes a drawn panel actually carries, in points.

    This is what "the default is what you pushed in" needs to be a measurement
    rather than a guess. The composite's font controls replace a panel's whole
    type hierarchy, so they have to open showing the hierarchy that is already
    on the page - otherwise ticking the box restyles every panel before the user
    has changed anything, which is the whole of the "I have to format the plot
    again" report.
    """
    out: Dict[str, float] = {}
    axes = _data_axes(fig)
    if not axes:
        return out
    ax = axes[0]
    for key, label in (("axis_font_pt", ax.yaxis.label), ("axis_font_pt", ax.xaxis.label)):
        if key not in out and label.get_text().strip():
            out[key] = float(label.get_fontsize())
    ticks = [t for t in (list(ax.get_yticklabels()) + list(ax.get_xticklabels()))
             if t.get_visible() and t.get_text().strip()]
    if ticks:
        out["tick_label_pt"] = float(ticks[0].get_fontsize())
    if ax.title.get_text().strip():
        out["title_font_pt"] = float(ax.title.get_fontsize())
    leg = ax.get_legend()
    if leg is not None:
        texts = [t for t in leg.get_texts() if t.get_text().strip()]
        if texts:
            out["legend_pt"] = float(texts[0].get_fontsize())
        if leg.get_title().get_text().strip():
            out["legend_title_pt"] = float(leg.get_title().get_fontsize())
    notes = sorted(float(t.get_fontsize()) for t in ax.texts
                   if t.get_visible() and t.get_text().strip())
    if notes:
        out["annotation_pt"] = notes[len(notes) // 2]
    # "Text (general)" is the body size the rest of the hierarchy is built from;
    # the annotation size is the closest thing a drawn figure has to it.
    if "annotation_pt" in out:
        out["base_font_pt"] = out["annotation_pt"]
    elif "tick_label_pt" in out:
        out["base_font_pt"] = out["tick_label_pt"]
    return out


class _PanelDraw:
    """One panel, drawn and measured, ready to be placed."""

    __slots__ = ("image", "geometry", "figure", "margins_fitted", "typography")

    def __init__(self, image: Optional[np.ndarray], geometry: _PanelGeometry,
                 figure: Optional[Figure] = None, margins_fitted: bool = False,
                 typography: Optional[Dict[str, float]] = None):
        self.image = image
        self.geometry = geometry
        self.figure = figure
        self.typography = typography or {}
        # True when the panel's margins were fitted to its decorations, which
        # makes its pads a measurement in inches rather than a fraction of the
        # canvas - and so stable when the panel is drawn at another size.
        self.margins_fitted = margins_fitted

    @property
    def aspect(self) -> float:
        g = self.geometry
        return g.height / g.width if g.width else 1.0


def _draw_panel(panel: Panel, font_overrides: Dict[str, Any],
                size_in: Optional[Tuple[float, Optional[float]]], dpi: int, *,
                rasterize: bool, warns: List[str],
                image_cache: Dict[int, Tuple[np.ndarray, float]],
                pad_in: float = DEFAULT_PANEL_PAD_IN,
                typo_scale: Optional[float] = None) -> _PanelDraw:
    """Draw one panel at ``size_in`` and measure where its plotting frame sits.

    ``size_in`` is ``(width_in, height_in)``; a ``None`` height means "the shape
    the plot makes for itself at this width", and ``size_in=None`` altogether
    means "the size the plot was finalized at" - the measuring pass, which is
    how the composite learns the shape it has to reproduce. ``rasterize=False``
    skips the expensive image for a panel that is about to be re-drawn.
    """
    want_w = 1.0 if size_in is None else float(size_in[0])
    want_h = None if size_in is None else size_in[1]

    if panel.is_external:
        # An imported picture has no axes of its own, so the whole image is
        # treated as the plotting frame and aligns flush with its cell.
        if id(panel) in image_cache:
            img, px_aspect = image_cache[id(panel)]
        else:
            img, w = _external_panel_image(panel)
            warns.extend(f"[{panel.label}] {m}" for m in w)
            px_aspect = (img.shape[0] / img.shape[1]) if img.shape[1] else 1.0
            image_cache[id(panel)] = (img, px_aspect)
        height = float(want_h) if want_h else want_w * px_aspect
        box = Bbox([[0.0, 0.0], [want_w, height]])
        return _PanelDraw(img, _PanelGeometry(box=box, axes=box, ink=box))

    if panel.figure is not None:
        # A pre-rendered figure has one shape; it is scaled, never re-drawn.
        fig = panel.figure
        geo = _measure_panel(fig)
        img = _figure_to_image(fig, dpi, geo.box)
        factor = want_w / geo.width if geo.width else 1.0
        return _PanelDraw(img, geo.scaled(factor))

    fig = _render_panel_figure(panel, font_overrides,
                               size_in=None if size_in is None else (want_w, want_h),
                               typo_scale=typo_scale)
    fitted = _fit_panel_margins(fig, pad_in)
    geo = _measure_panel(fig)
    img = _figure_to_image(fig, dpi, geo.box) if rasterize else None
    warns.extend(f"[{panel.label}] {w}" for w in getattr(fig, "_mmf_render_warnings", []))
    return _PanelDraw(img, geo, figure=fig, margins_fitted=fitted,
                      typography=_measured_typography(fig))


# The most a y-axis label may be pushed out to make a column's left edges
# flush, in inches. Past this the two panels are not comparable - a plot with no
# decoration at all beside a heatmap with 20-character row labels - and leaving
# the block edge ragged is better than throwing the label halfway across the
# figure to hide it.
MAX_LABEL_LEAD_PUSH_IN = 0.75


def _leftmost_data_axes(fig: Figure):
    """The data axes nearest the left edge, or ``None``."""
    axes = _data_axes(fig)
    if not axes:
        return None
    return min(axes, key=lambda a: a.get_position().x0)


def _push_axis_label_out(fig: Figure, inches: float) -> bool:
    """Move the y-axis label ``inches`` further from its axes. False if it has none.

    ``labelpad`` is points of white space between the tick labels and the axis
    label, so this moves the label and nothing else: the axes does not move, the
    plot keeps its width, and the space opens up in the gap between two pieces
    of text where no reader can see it.
    """
    ax = _leftmost_data_axes(fig)
    if ax is None or not ax.yaxis.label.get_text().strip():
        return False
    try:
        ax.yaxis.labelpad = float(ax.yaxis.labelpad) + inches * 72.0
    except Exception:  # noqa: BLE001
        return False
    return True


def _label_padding(layout: FigureLayout, n: int) -> Tuple[float, float]:
    """Room to reserve for the panel letters, in inches (left, top).

    The letters are drawn outside the panels, so the grid has to start inboard
    of the figure edge or the first column's letter falls off the canvas.
    """
    if n <= 0:
        return 0.0, 0.0
    em = float(layout.label_size) / 72.0
    return em * 1.1, em * 1.3


def build_figure(mpf: MultiPanelFigure) -> Figure:
    """Render and compose all panels into a single labelled Figure.

    Three steps, because alignment is a measurement:

    1. Draw every panel at the size it was finalized at, to learn the shape the
       composite has to reproduce and roughly how much room its axis labels need.
    2. Draw each one again at the size it will occupy, and measure where its
       plotting frame really sits inside its picture.
    3. Build the grid from those measurements and place each panel by its frame,
       so the frames share one left edge down each column and one top edge
       across each row.

    The second measurement is what makes the alignment exact rather than
    predicted: a panel drawn smaller may wrap its title onto a second line or
    drop a tick, and the first pass cannot know that.
    """
    layout = mpf.layout
    panels = list(mpf.panels)
    if not panels:
        raise ValueError("Cannot build a multi-panel figure with no panels.")
    mpf.autolabel()

    font_overrides = layout.font_overrides()
    from make_my_figure_core.styles.engine import load_profile

    _ann_style = load_profile("publication")   # for per-panel annotation defaults

    n = len(panels)
    nrows, ncols = _auto_grid(n, layout)
    warns: List[str] = []
    own_figs: List[Figure] = []
    image_cache: Dict[int, Tuple[np.ndarray, float]] = {}
    pad_in = (DEFAULT_PANEL_PAD_IN if layout.panel_pad_mm is None
              else max(0.0, mm_to_inches(layout.panel_pad_mm)))

    def _col(c):
        return range(c, n, ncols)

    def _row(r):
        return range(r * ncols, min((r + 1) * ncols, n))

    rc = [divmod(i, ncols) for i in range(n)]

    # Effective per-panel WIDTH in inches. An unset width defaults to an even
    # share of the figure width, so old specs keep their overall width.
    default_w = mm_to_inches(layout.fig_width_mm) / ncols
    panel_w = [float(p.width_in) if p.width_in else default_w for p in panels]

    # --- step 1: draw every panel as it was finalized, and measure it -------
    #
    # At its OWN size, not at the panel width. A panel has to arrive in the
    # figure as the plot the user approved, reduced to fit - so the shape to
    # reproduce is the shape it has on its own canvas. Re-deriving it from the
    # panel width instead gives a different figure: a 26-row heatmap, whose
    # height is a fixed number of inches per row, comes back twice as tall as
    # it is wide when only its width is pinned.
    first: List[_PanelDraw] = []
    for i, panel in enumerate(panels):
        draw = _draw_panel(panel, font_overrides, None, layout.panel_dpi,
                           rasterize=not _can_resize(panel), warns=warns,
                           image_cache=image_cache, pad_in=pad_in)
        if draw.figure is not None and panel.figure is None:
            own_figs.append(draw.figure)
        first.append(draw)

    # Effective per-panel HEIGHT in inches: the height the panel is really DRAWN
    # at. For a panel that can be re-drawn that is the height it asked for, or
    # the one its own proportions give at this width. For a pre-rendered figure
    # or an imported image there is only one possible height at this width, so a
    # request to be SHORTER scales the picture down and a request to be TALLER
    # is capped - growing the row to a height the picture cannot fill only
    # manufactures the white space the user was trying to get rid of.
    panel_h: List[float] = []
    for i, p in enumerate(panels):
        g = first[i].geometry
        natural = panel_w[i] * (g.height / g.width if g.width else 1.0)
        requested = float(p.height_in) if p.height_in else 0.0
        if requested and not _can_resize(p):
            panel_h.append(min(requested, natural))
            if requested > natural * 1.01:
                warns.append(
                    f"[{p.label}] keeps its own proportions, so at {panel_w[i]:.2f} in wide it is "
                    f"{natural:.2f} in tall and cannot be made {requested:.2f} in tall. Make it "
                    f"wider, or set it to fill its cell to use the whole space.")
        else:
            panel_h.append(requested if requested else natural)

    # One type hierarchy for the whole figure, scaled to the SMALLEST panel.
    #
    # One hierarchy, because a figure has one: scaling each panel to its own
    # canvas put 12 pt axis labels beside 10.2 pt ones in the same figure. The
    # smallest panel sets it, because that is the panel the type has to stay
    # legible in - and because it makes the control predictable. Taking the
    # median instead meant widening one panel restyled the whole figure, which
    # grew another panel's legend until it no longer fitted beside its plot:
    # widening C made C's plot narrower. Making a panel BIGGER now never
    # changes the type; making one smaller than anything else does, which is
    # exactly "diminish the heatmap and the fonts decrease accordingly".
    #
    # Skipped entirely when the user has set the sizes explicitly: those are
    # literal points, which is the whole purpose of asking for them.
    typo_scale = None
    if not font_overrides:
        from make_my_figure_core.styles.typography import typography_scale

        smallest = min(panel_w[i] * panel_h[i] for i in range(n))
        side = math.sqrt(smallest) if smallest > 0 else 1.0
        typo_scale = typography_scale(side, side,
                                      tuple(_ann_style.figure_size_inches()),
                                      dead_band=False)

    # Room to reserve for each panel's axis decorations when it is drawn at its
    # panel size, from the pads measured in step 1.
    #
    # A fitted panel's pads are inches of axis label and tick numbers, so they
    # follow the TYPE, not the canvas - and step 1 measured them at the plot's
    # own type size, which the composite is about to scale. A panel that is
    # scaled bodily instead (a pre-rendered figure, an imported picture) has
    # pads that follow the picture. Getting this wrong only costs precision, not
    # alignment: a panel drawn too wide for the room its neighbour's label needs
    # pushes its column wider rather than losing the alignment, so the figure
    # came out 5% wider than the widths that were asked for.
    reserve = []
    for i in range(n):
        g = first[i].geometry
        if first[i].margins_fitted:
            k = typo_scale or 1.0
        else:
            k = panel_w[i] / g.width if g.width else 1.0
        reserve.append((g.pad_left * k, g.pad_top * k))

    # --- step 2: draw each panel at the size it will occupy -----------------
    # The cell sizes here are a prediction (widest/tallest panel in the column /
    # row, plus the room the alignment shift needs); the grid itself is built
    # afterwards from what the drawn panels actually measure, so a panel can
    # never end up bigger than the cell it is placed in.
    est_left = [max((reserve[i][0] for i in _col(c)), default=0.0) for c in range(ncols)]
    est_top = [max((reserve[i][1] for i in _row(r)), default=0.0) for r in range(nrows)]
    est_col_w = [max((panel_w[i] for i in _col(c)), default=default_w) for c in range(ncols)]
    est_row_h = [max((panel_h[i] + max(0.0, est_top[rc[i][0]] - reserve[i][1])
                      for i in _row(r)), default=1.0) for r in range(nrows)]
    if layout.width_ratios and len(layout.width_ratios) == ncols:
        est_col_w = [float(v) for v in layout.width_ratios]
    if layout.height_ratios and len(layout.height_ratios) == nrows:
        est_row_h = [float(v) for v in layout.height_ratios]

    final: List[_PanelDraw] = []
    for i, panel in enumerate(panels):
        r, c = rc[i]
        cell_w, cell_h = est_col_w[c], est_row_h[r]
        dx = max(0.0, est_left[c] - reserve[i][0])
        dy = max(0.0, est_top[r] - reserve[i][1])
        fill = panel.fill_cell or (panel.is_external
                                   and panel.fit_mode in ("fill", "stretch"))
        if fill:
            # Use the whole cell. The honest way is to re-draw the plot ON a
            # canvas that size, so the axes grow and the type keeps its points;
            # only a panel that has lost its PlotSpec has to be stretched, and
            # that is reported.
            want_w = max(0.2, cell_w - dx)
            want_h: Optional[float] = max(0.2, cell_h - dy)
        else:
            want_w = max(0.2, min(panel_w[i], cell_w) - dx)
            want_h = max(0.2, min(panel_h[i], cell_h - dy))
        if not _can_resize(panel):
            g0 = first[i].geometry
            scale = min(want_w / g0.width,
                        (want_h / g0.height) if (want_h and not fill) else float("inf"))
            final.append(_PanelDraw(first[i].image, g0.scaled(scale)))
            if fill:
                warns.append(
                    f"[{panel.label}] stretched non-proportionally; may distort the figure.")
            continue
        draw = _draw_panel(panel, font_overrides, (want_w, want_h), layout.panel_dpi,
                           rasterize=True, warns=warns, image_cache=image_cache,
                           pad_in=pad_in, typo_scale=typo_scale)
        if draw.figure is not None:
            own_figs.append(draw.figure)
        final.append(draw)

    # Optional: one PLOT height per row, so the frames line up along the bottom
    # as well as the top. Panels in a row are already drawn the same height; what
    # differs is how much of it goes below the axes - a bar chart with rotated
    # category labels spends 0.5 in there and a heatmap 0.3 in - so the plots end
    # at different places. Equalizing means re-drawing the shorter ones on a
    # taller canvas, which is why it is a choice rather than the default.
    if layout.match_plot_heights:
        for r in range(nrows):
            target = max((final[i].geometry.axes.height for i in _row(r)), default=0.0)
            for i in _row(r):
                short = target - final[i].geometry.axes.height
                if short <= 0.01 or not _can_resize(panels[i]):
                    continue
                draw = _draw_panel(panels[i], font_overrides,
                                   (final[i].geometry.width,
                                    final[i].geometry.height + short),
                                   layout.panel_dpi, rasterize=True, warns=warns,
                                   image_cache=image_cache, pad_in=pad_in,
                                   typo_scale=typo_scale)
                if draw.figure is not None:
                    own_figs.append(draw.figure)
                final[i] = draw

    # Flush the left edge of the panel BLOCKS as well as the plots inside them.
    #
    # Aligning the plotting frames leaves the panels ragged on the outside,
    # because one panel's row labels are wider than another's tick numbers:
    # measured 3 mm between a box plot and a heatmap in the same column, which
    # reads as the heatmap sticking out past its neighbour. Both edges can be
    # true at once. A y-axis label is positioned by a pad rather than by the
    # data, so pushing the narrower panel's label out until its leading
    # decoration measures the same as its neighbour's puts the block edges flush
    # AND keeps the frames aligned - and the white space it adds falls between
    # the tick numbers and the label, where there is nothing to see.
    def _ink_lead(g: _PanelGeometry) -> float:
        """Inches from the leftmost thing the panel draws to its plotting frame."""
        return float(g.axes.x0 - (g.ink if g.ink is not None else g.box).x0)

    for c in range(ncols):
        target = max((_ink_lead(final[i].geometry) for i in _col(c)), default=0.0)
        for i in _col(c):
            short = target - _ink_lead(final[i].geometry)
            fig = final[i].figure
            if (short <= 0.01 or short > MAX_LABEL_LEAD_PUSH_IN or fig is None
                    or not _push_axis_label_out(fig, short)):
                continue
            geo = _measure_panel(fig)
            final[i] = _PanelDraw(_figure_to_image(fig, layout.panel_dpi, geo.box),
                                  geo, figure=fig,
                                  margins_fitted=final[i].margins_fitted,
                                  typography=final[i].typography)

    # --- step 3: the grid, from what the drawn panels measure ---------------
    align_left = [max((final[i].geometry.pad_left for i in _col(c)), default=0.0)
                  for c in range(ncols)]
    align_top = [max((final[i].geometry.pad_top for i in _row(r)), default=0.0)
                 for r in range(nrows)]
    shift_x = [max(0.0, align_left[rc[i][1]] - final[i].geometry.pad_left) for i in range(n)]
    shift_y = [max(0.0, align_top[rc[i][0]] - final[i].geometry.pad_top) for i in range(n)]
    # Image box sizes, taken from the rasterized pixels: a rasterizer rounds to
    # whole pixels, and matplotlib would quietly shrink an axes whose box
    # disagreed with its image's aspect - moving the panel, which is the one
    # thing this must not do.
    box_w, box_h = [], []
    for i in range(n):
        g = final[i].geometry
        img = final[i].image
        aspect = (img.shape[0] / img.shape[1] if (img is not None and img.shape[1])
                  else (g.height / g.width if g.width else 1.0))
        box_w.append(g.width)
        box_h.append(g.width * aspect)

    # A column keeps the width its panels asked for: the figure's overall width
    # is the number a journal cares about, so a panel shifted right to meet the
    # alignment gives up the difference from its own plotting width. A row
    # GROWS to hold a panel pushed down by a neighbour's two-line title - the
    # alternative is cropping a panel that asked for that height.
    col_w = [max([est_col_w[c]] + [box_w[i] + shift_x[i] for i in _col(c)])
             for c in range(ncols)]
    row_h = [max([est_row_h[r]] + [box_h[i] + shift_y[i] for i in _row(r)])
             for r in range(nrows)]

    # Figure size, computed so that a cell is EXACTLY the inches its panel asked
    # for. The gutters are matplotlib's relative wspace/hspace (a fraction of the
    # mean cell size) and the grid is pinned to the figure edges, less the room
    # the panel letters need. Before this, the grid sat inside matplotlib's
    # default subplot margins, so a panel asked for 3.2 in was drawn 2.68 in -
    # the "comes out around 0.85x the number you type" the help text had to
    # apologise for.
    pad_l, pad_t = _label_padding(layout, n)
    gut_w = layout.wspace * (sum(col_w) / ncols)
    gut_h = layout.hspace * (sum(row_h) / nrows)
    grid_w = sum(col_w) + (ncols - 1) * gut_w
    grid_h = sum(row_h) + (nrows - 1) * gut_h
    fig_w_in = pad_l + grid_w
    fig_h_in = (mm_to_inches(layout.fig_height_mm) if layout.fig_height_mm
                else max(pad_t + grid_h, 1.5))

    frames: List[Dict[str, Any]] = []
    with plt.rc_context({**_VECTOR_TEXT_RC, "font.family": list(_ann_style.font_family)}):
        comp = plt.figure(figsize=(fig_w_in, fig_h_in), facecolor=layout.background)
        gs = comp.add_gridspec(
            nrows, ncols, wspace=layout.wspace, hspace=layout.hspace,
            width_ratios=col_w, height_ratios=row_h,
            left=pad_l / fig_w_in, right=1.0,
            bottom=0.0, top=max(0.05, 1.0 - pad_t / fig_h_in),
        )
        for i, panel in enumerate(panels):
            r, c = rc[i]
            cell = gs[r, c].get_position(comp)
            geo = final[i].geometry
            ink = geo.ink if geo.ink is not None else geo.box
            img = final[i].image
            ax = comp.add_subplot(gs[r, c])
            x0 = cell.x0 * fig_w_in + shift_x[i]
            y1 = cell.y1 * fig_h_in - shift_y[i]
            ax.set_position([x0 / fig_w_in, (y1 - box_h[i]) / fig_h_in,
                             box_w[i] / fig_w_in, box_h[i] / fig_h_in])
            # Anchor north-west: if anything ever does adjust this box, it must
            # give up space at the bottom-right and keep the aligned edges.
            ax.set_anchor("NW")
            if img is not None:
                ax.imshow(img, interpolation="antialiased")
            # Record where this panel's plotting frame landed on the page, in
            # inches. Alignment is the headline promise of a panel grid and it
            # is invisible to a "does it render?" check - this is what makes it
            # measurable, by the tests and by anyone debugging a layout.
            frames.append({
                "label": panel.label, "row": r, "col": c,
                "x0": x0 + (geo.axes.x0 - geo.box.x0),
                "x1": x0 + (geo.axes.x1 - geo.box.x0),
                "y1": y1 - (geo.box.y1 - geo.axes.y1),
                "y0": y1 - (geo.box.y1 - geo.axes.y0),
                # The panel BLOCK - the leftmost and rightmost thing it
                # actually draws, axis label included, rather than the edge of
                # its canvas. Panels in a column share "block_x0" as well as
                # "x0"; that is what stops a heatmap's row labels hanging out
                # past the box plot above it.
                "block_x0": x0 + (ink.x0 - geo.box.x0),
                "block_x1": x0 + (ink.x1 - geo.box.x0),
            })
            if geo.overflow > 0.02:
                warns.append(
                    f"[{panel.label}] {geo.overflow:.2f} in of the plot does not fit the panel "
                    f"and hangs over its edge. Make the panel bigger, or shorten the longest "
                    f"label.")
            ax.set_xticks([]); ax.set_yticks([])
            show_border = bool(panel.is_external and panel.border)
            for spine in ax.spines.values():
                spine.set_visible(show_border)
                if show_border:
                    spine.set_linewidth(panel.border_width)
                    spine.set_edgecolor("#000000")
            if layout.show_titles and panel.title:
                ax.set_title(panel.title, fontsize=layout.label_size * 0.8)
            # Per-panel manual annotations (imported panels use normalized 0..1
            # coords => 'axes' transform, so they reproduce at any panel size).
            if panel.annotations:
                from make_my_figure_core.annotations import apply_annotations, parse_annotations

                anns = parse_annotations(panel.annotations)
                for a in anns:
                    if panel.is_external and a.coords == "data":
                        a.coords = "axes"
                apply_annotations(comp, ax, anns, _ann_style)
            # Bold panel label, outside the panel's top-left corner: a hair
            # left of everything the panel draws, with the block starting just
            # below it. Hung off the CELL rather than off the picture, because
            # the pictures in a row start at different heights (one has a title,
            # another does not) and that put A and B at different heights on the
            # page; and off the block's left edge rather than the plot's, so the
            # letter is the leftmost thing in its panel rather than sitting over
            # the y-axis label.
            # ``label_dx`` is taken against the COLUMN's width, not this panel's
            # own plot width: the letters hang off the cell now, and scaling the
            # offset by each panel's plot made A sit 0.03 in further out than C
            # in the same column, which is visible as a ragged left edge.
            label_x = cell.x0 * fig_w_in + layout.label_dx * col_w[c]
            label_y = cell.y1 * fig_h_in + (layout.label_dy - 1.0) * (cell.height * fig_h_in)
            comp.text(label_x / fig_w_in, label_y / fig_h_in, panel.label,
                      ha="left", va="bottom", fontsize=layout.label_size,
                      fontweight=layout.label_weight, color="#000000")
        # Hide any unused trailing cells.
        for j in range(n, nrows * ncols):
            r, c = divmod(j, ncols)
            ax = comp.add_subplot(gs[r, c])
            ax.axis("off")

    for f in own_figs:
        plt.close(f)
    # Surface imported-panel warnings (resolution/DPI/stretch/rasterization) to
    # the caller without changing the return type.
    seen: List[str] = []
    for w in warns:
        if w not in seen:
            seen.append(w)
    comp._mmf_panel_warnings = seen  # type: ignore[attr-defined]
    comp._mmf_panel_frames = frames  # type: ignore[attr-defined]
    comp._mmf_panel_typography = [dict(d.typography) for d in final]  # type: ignore[attr-defined]
    return comp



def panel_warnings(fig: Figure) -> List[str]:
    """Imported-panel publication warnings collected during the last build."""
    return list(getattr(fig, "_mmf_panel_warnings", []))


def panel_typography(fig: Figure) -> List[Dict[str, float]]:
    """The type sizes each panel of the last build actually carries, in points.

    One dict per panel, keyed by the same names as ``FigureLayout``'s font
    tokens. The Figure Builder's font controls open on these, so turning them on
    changes nothing until the user moves one.
    """
    return [dict(d) for d in getattr(fig, "_mmf_panel_typography", [])]


def panel_frames(fig: Figure) -> List[Dict[str, Any]]:
    """Where each panel's plotting frame sits on the composite, in inches.

    One dict per panel: ``label``, ``row``, ``col``, the frame's ``x0``, ``x1``,
    ``y0``, ``y1``, and the panel block's ``block_x0`` / ``block_x1``. Panels in
    a column share ``x0`` AND ``block_x0``; panels in a row share ``y1``. That
    is the alignment contract, and this is how to check it.
    """
    return [dict(f) for f in getattr(fig, "_mmf_panel_frames", [])]


def import_external_panel(src_path: str, assets_dir: str, *, label: str = "", title: str = "",
                          width_in: Optional[float] = None, rasterize_dpi: int = 300,
                          pdf_page: int = 0, **transform: Any):
    """Import an external figure file and return ``(Panel, ImportedAsset)``.

    The file is copied into ``assets_dir``; the Panel references the stored asset
    (relative basename in its FigureSpec). Returns the asset too so the caller can
    show a preview / any import error before adding the panel. On import error the
    Panel is ``None``.
    """
    from make_my_figure_core import figure_import as fi

    asset = fi.import_asset(src_path, assets_dir, rasterize_dpi=rasterize_dpi, pdf_page=pdf_page)
    if asset.error:
        return None, asset
    meta = dict(asset.metadata)
    meta["warnings"] = list(asset.warnings)
    allowed = {"fit_mode", "preserve_aspect", "crop", "rotate", "flip_h", "flip_v",
               "auto_trim", "background", "border", "border_width", "annotations",
               "fill_cell"}
    kw = {k: v for k, v in transform.items() if k in allowed}
    panel = Panel(label=label, title=title, width_in=width_in,
                  image_path=os.path.join(assets_dir, meta["stored_asset"]),
                  image_meta=meta, source_name=meta.get("original_filename", ""), **kw)
    return panel, asset


def panel_from_dict(d: Dict[str, Any], assets_dir: Optional[str] = None) -> Panel:
    """Reconstruct a Panel from a FigureSpec panel dict (round-trip).

    For imported panels, the asset is resolved as ``assets_dir/<image_path>`` so a
    shared FigureSpec + assets folder reload without absolute paths.
    """
    kind = d.get("panel_kind")
    img_rel = d.get("image_path")
    image_path = None
    if img_rel:
        image_path = os.path.join(assets_dir, img_rel) if assets_dir else img_rel
    return Panel(
        label=d.get("label", ""), title=d.get("title", ""), caption=d.get("caption", ""),
        plot_spec=d.get("plot_spec"), stats_spec=d.get("stats_spec"),
        source_name=d.get("source_name", ""),
        source_workbook=d.get("source_workbook", ""), source_sheet=d.get("source_sheet", ""),
        width_in=d.get("width_in"), height_in=d.get("height_in"),
        # Missing in layouts saved before fill_cell existed -> keep proportions.
        fill_cell=bool(d.get("fill_cell", False)),
        image_path=image_path, image_meta=d.get("image_meta", {}) or {},
        fit_mode=d.get("fit_mode", "contain"), preserve_aspect=d.get("preserve_aspect", True),
        crop=d.get("crop", {}) or {}, rotate=int(d.get("rotate", 0)),
        flip_h=bool(d.get("flip_h", False)), flip_v=bool(d.get("flip_v", False)),
        auto_trim=bool(d.get("auto_trim", False)), background=d.get("background", "white"),
        border=bool(d.get("border", False)), border_width=float(d.get("border_width", 0.8)),
        annotations=d.get("annotations", []) or [],
    )


def export_multipanel(fig: Figure, base_path: str, formats: List[str], dpi: int = 300) -> List[str]:
    """Save the composite figure in each requested format."""
    import matplotlib as mpl

    valid = {"svg", "png", "pdf", "tiff", "eps"}
    written: List[str] = []
    os.makedirs(os.path.dirname(os.path.abspath(base_path)) or ".", exist_ok=True)
    with mpl.rc_context(_VECTOR_TEXT_RC):
        for fmt in formats:
            fmt = fmt.lower()
            if fmt not in valid:
                continue
            out = f"{base_path}.{fmt}"
            # Pass dpi for EVERY format: the panels are embedded as raster images,
            # so vector outputs (pdf/svg/eps) also need a high dpi or the panels
            # look blurry — text stays vector via _VECTOR_TEXT_RC regardless.
            kwargs: Dict[str, Any] = {"bbox_inches": "tight", "facecolor": fig.get_facecolor(),
                                      "dpi": dpi}
            if fmt == "tiff":
                kwargs["pil_kwargs"] = {"compression": "tiff_lzw"}
            fig.savefig(out, format=fmt, **kwargs)
            written.append(out)
    return written


def draft_legend(mpf: MultiPanelFigure) -> str:
    """Generate a *draft* figure legend from panel titles, variables, and stats
    method reports. Draft only - it never fabricates biological interpretation.
    """
    parts = [f"{mpf.name}."]
    for panel in mpf.panels:
        bits = [f"({panel.label})"]
        desc = panel.title or _panel_plot_phrase(panel)
        if desc:
            bits.append(desc + ".")
        method = _panel_method_sentence(panel)
        if method:
            bits.append(method)
        parts.append(" ".join(bits))
    parts.append("[DRAFT auto-generated legend - verify all descriptions and add "
                 "biological interpretation before publication.]")
    return " ".join(parts)


def _panel_plot_phrase(panel: Panel) -> str:
    spec = panel.plot_spec or {}
    pt = spec.get("plot_type", "")
    mapping = spec.get("mapping", {}) or {}
    y = mapping.get("y"); x = mapping.get("x")
    if y and x:
        return f"{y} by {x}"
    return pt.replace("_", " ")


def _panel_method_sentence(panel: Panel) -> str:
    ss = panel.stats_spec or (panel.plot_spec or {}).get("statistics")
    if not ss or not ss.get("enabled"):
        return ""
    return "Statistics were computed as recorded in the panel StatsSpec."


def multipanel_sidecar(mpf: MultiPanelFigure, base_path: str) -> str:
    """Write ``base_path.figure_spec.json`` describing the composite."""
    out = f"{base_path}.figure_spec.json"
    payload = {
        "figure": mpf.to_dict(),
        "draft_legend": mpf.legend_text or draft_legend(mpf),
        "disclaimer": (
            "Multi-panel composite generated by Make My Figure. Panel content is embedded "
            "at the configured DPI; panel labels and titles are vector text. Auto-generated "
            "legend text is a draft and must be verified before publication."
        ),
    }
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return out
