"""Shared helpers and result type for plot renderers.

Every renderer receives a validated ``spec`` (PlotSpec dict), a loaded
``pandas.DataFrame``, and a resolved :class:`StyleProfile`, and returns a
:class:`RenderResult` carrying the figure plus a metadata record. Renderers
never mutate their input DataFrame in place (acceptance criterion: "no
renderer mutates input data silently").
"""

from __future__ import annotations

import math

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from make_my_figure_core.styles.engine import (
    StyleProfile, mm_to_inches, resolve_width_mm)


# Smallest figure dimension that can carry anything legible. Below this a
# figure is not "small", it is broken: axis labels, ticks and a colourbar cannot
# be laid out at all, and matplotlib starts emitting layout failures. Requests
# below the floor are raised to it and reported, rather than honoured into
# something unusable.
MIN_FIGURE_MM = 20.0


class RenderError(Exception):
    """Raised when a spec/data combination cannot be rendered."""


@dataclass
class RenderResult:
    """A rendered figure plus a reproducibility/metadata record."""

    figure: Figure
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    # Optional StatsReport (make_my_figure_core.statistics.StatsReport) when the
    # spec requested statistics; carried out-of-band so the registry can write a
    # StatsSpec sidecar and merge a serialized copy into metadata.
    stats_report: Any = None


# --- small validation helpers ------------------------------------------------

def require_columns(df: pd.DataFrame, columns: List[str], *, context: str) -> None:
    missing = [c for c in columns if c and c not in df.columns]
    if missing:
        raise RenderError(
            f"{context}: missing required column(s) {missing}. "
            f"Available columns: {list(df.columns)}"
        )


def get_mapping(spec: Dict[str, Any], key: str, default: Any = None,
                *, required: bool = False, context: str = "mapping") -> Any:
    mapping = spec.get("mapping", {}) or {}
    value = mapping.get(key, default)
    if required and (value is None or value == ""):
        raise RenderError(f"{context}: mapping '{key}' is required.")
    return value


def coerce_numeric(df: pd.DataFrame, column: str, *, context: str) -> pd.Series:
    """Return a numeric copy of a column, raising if nothing is numeric."""
    series = pd.to_numeric(df[column], errors="coerce")
    if series.notna().sum() == 0:
        raise RenderError(f"{context}: column '{column}' has no numeric values.")
    return series


# --- statistics helpers ------------------------------------------------------

def summarize_error(values: np.ndarray, method: str) -> tuple[float, float]:
    """Return ``(center, error)`` for an array given an error method.

    ``method`` is one of ``sem``, ``sd``/``std``, ``ci95``, or ``none``.
    Center is always the mean. NaNs are dropped.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        return (np.nan, 0.0)
    mean = float(np.mean(arr))
    method = (method or "sem").lower()
    if arr.size < 2 or method == "none":
        return (mean, 0.0)
    sd = float(np.std(arr, ddof=1))
    if method in ("sd", "std"):
        return (mean, sd)
    sem = sd / np.sqrt(arr.size)
    if method == "sem":
        return (mean, sem)
    if method in ("ci", "ci95", "ci_95"):
        # Normal approximation 95% CI half-width.
        return (mean, 1.96 * sem)
    # Unknown -> default to SEM.
    return (mean, sem)


def summarize_band(values: np.ndarray, method: str) -> tuple[float, float, float]:
    """Return ``(center, low, high)`` for an array given a band method.

    Symmetric methods (``sem``, ``sd``, ``ci95``, ``none``) delegate to
    :func:`summarize_error` and centre on the mean. Two order-statistic methods
    are added for replicate measurements such as benchmark timings: ``iqr``
    (median with the 25th-75th percentile band) and ``range`` (median with the
    min-max band). NaNs are dropped.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    m = (method or "sem").lower()
    if m in ("iqr", "range"):
        if arr.size == 0:
            return (np.nan, np.nan, np.nan)
        med = float(np.median(arr))
        if arr.size < 2:
            return (med, med, med)
        if m == "iqr":
            lo, hi = np.percentile(arr, [25, 75])
            return (med, float(lo), float(hi))
        return (med, float(np.min(arr)), float(np.max(arr)))
    c, e = summarize_error(arr, m)
    return (c, c - e, c + e)


_WIDTH_ALIASES = {"single", "onehalf", "double", "default"}


def figure_size(spec: Dict[str, Any], style: StyleProfile, *, aspect: float) -> tuple[float, float]:
    """Resolve figure size from the spec.

    Three levels, most specific first:

    * ``layout['width_mm']`` / ``layout['height_mm']`` — explicit millimetres.
      Either may be given alone: a width without a height keeps the renderer's
      aspect, and a height without a width keeps the preset width. This exists
      because a column preset times a fixed aspect cannot describe every figure —
      a 9x28 dot matrix is wide and short, and no preset says that.
    * ``layout['aspect']`` — a numeric height/width ratio.
    * ``layout['column_width']`` — ``default``, ``single``, ``onehalf``, ``double``.

    A non-positive or unparseable value is ignored rather than producing a
    zero-sized figure.
    """
    layout = spec.get("layout", {}) or {}
    width = str(layout.get("column_width", "default")).lower()
    if width not in _WIDTH_ALIASES and resolve_width_mm(width) is None:
        width = "default"
    try:
        aspect = float(layout.get("aspect", aspect))
    except (TypeError, ValueError):
        pass

    def _mm(key):
        try:
            v = float(layout.get(key))
        except (TypeError, ValueError):
            return None
        if v <= 0:
            return None
        return max(v, MIN_FIGURE_MM)      # never return an unusable dimension

    w_mm, h_mm = _mm("width_mm"), _mm("height_mm")
    w_in, h_in = style.figure_size_inches(width, aspect=aspect)
    if w_mm is not None:
        w_in = mm_to_inches(w_mm)
        if h_mm is None:
            h_in = w_in * float(aspect)
    if h_mm is not None:
        h_in = mm_to_inches(h_mm)
    return (w_in, h_in)



def figure_size_adjustments(spec: Dict[str, Any]) -> List[str]:
    """Human-readable notes about size requests that had to be corrected."""
    layout = (spec or {}).get("layout", {}) or {}
    notes = []
    for key, axis in (("width_mm", "width"), ("height_mm", "height")):
        raw = layout.get(key)
        if raw is None:
            continue
        try:
            v = float(raw)
        except (TypeError, ValueError):
            notes.append(f"Figure {axis} {raw!r} is not a number and was ignored.")
            continue
        if v <= 0:
            continue                      # 0 means "auto"; not an error
        if v < MIN_FIGURE_MM:
            notes.append(
                f"Figure {axis} of {v:g} mm is too small to lay out - raised to "
                f"{MIN_FIGURE_MM:g} mm. Set 0 for automatic sizing.")
    return notes


def pinned_dimension(spec: Dict[str, Any], key: str) -> "float | None":
    """One pinned ``layout`` dimension in inches, or ``None`` if not asked for.

    ``0`` is the documented way to say "automatic", and an unparseable value is
    ignored rather than producing a zero-sized figure (it is reported separately
    by :func:`figure_size_adjustments`). The ``MIN_FIGURE_MM`` floor is applied
    here so every caller gets a dimension matplotlib can actually lay out.
    """
    layout = (spec or {}).get("layout", {}) or {}
    try:
        v = float(layout.get(key))
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    return mm_to_inches(max(v, MIN_FIGURE_MM))


# The width presets a user can pick deliberately. "default" is the automatic
# choice, so it is not in here.
CHOSEN_WIDTH_PRESETS = ("single", "onehalf", "double")


def requested_width(spec: Dict[str, Any]) -> "float | None":
    """The width the user asked for, in inches, or ``None`` for automatic.

    ``layout.width_mm`` is the explicit form, but the common one is
    ``layout.column_width``: picking "single" is how you say "this goes in a
    journal's single column", and an experimental preset pins a target width the
    same way. Both are instructions about the finished figure, so both have to
    stop the fitting pass from growing the canvas - otherwise asking for a 57 mm
    column and getting 104 mm back because a legend did not fit defeats the point
    of asking. The canvas is held and the plotting area gives up the room instead.

    "default" is the automatic choice and is deliberately not a request.
    """
    pinned = pinned_dimension(spec, "width_mm")
    if pinned is not None:
        return pinned
    name = chosen_column_width(spec)
    if name is None:
        return None
    mm = resolve_width_mm(name)
    return None if mm is None else mm_to_inches(max(float(mm), MIN_FIGURE_MM))


# How many passes the label-overlap solver gets.
#
# ``adjust_text`` defaults to a one-SECOND wall-clock budget when neither limit is
# given, and iterates until the timer expires. The number of passes therefore
# depends on how fast and how loaded the machine is, which made three plot types
# - volcano, network graph and lollipop - render differently every single time,
# from identical input. That is not a seeding problem and no seed fixes it: the
# library's own RNG is already pinned at 42. An iteration budget replaces the
# clock with something reproducible.
#
# 60 is well past convergence: on a 30-label scatter the solver reaches zero
# overlapping pairs by 30 passes, and 400 is no better. It is also faster than
# the second it used to spend.
LABEL_ADJUST_ITERATIONS = 60

# A figure will not be grown past this, however much its legend wants.
MAX_FIT_GROWTH_IN = 4.0

# Content hanging off by less than this is left alone. A few hundredths of an
# inch is antialiasing and rounding in the text metrics, not a clipped label, and
# resizing a figure to chase it only produces a warning about a change nobody can
# see. Matches the tolerance the tests use for "is this clipped".
FIT_TOLERANCE_IN = 0.035


def content_overflow_inches(figure) -> tuple:
    """``(left, right, bottom, top)`` inches of drawn content outside the canvas.

    Uses matplotlib's own tight bounding box, which counts only what is actually
    drawn - an axis keeps label objects for ticks outside the view limits, parked
    off-canvas and never rendered, and counting those reports overflow on figures
    that are clean.
    """
    try:
        renderer = figure.canvas.get_renderer()
    except AttributeError:
        return (0.0, 0.0, 0.0, 0.0)
    figure.canvas.draw()
    dpi = figure.dpi
    width_px, height_px = [v * dpi for v in figure.get_size_inches()]
    box = figure.get_tightbbox(renderer)
    return (max(0.0, -box.x0), max(0.0, box.x1 - width_px / dpi),
            max(0.0, -box.y0), max(0.0, box.y1 - height_px / dpi))


def register_refit(figure, callback) -> None:
    """Ask for ``callback`` to be re-run whenever the layout pass moves the axes.

    Text sized or wrapped to fit its axes is only correct for the axes it was
    measured against. The fitting pass then narrows those axes to bring a legend
    back on canvas, and the text that fitted a moment ago no longer does - which
    is how a regression-stats box ended up hanging off the left of a pinned 4 x 2
    in figure after the pass that was supposed to tidy it up.
    """
    try:
        figure._mmf_text_refit = list(getattr(figure, "_mmf_text_refit", ())) + [callback]
    except Exception:  # noqa: BLE001
        pass


def _refit_text(figure) -> None:
    """Run the registered re-fits; a failing one must never break a render."""
    for callback in getattr(figure, "_mmf_text_refit", ()):
        try:
            callback()
        except Exception:  # noqa: BLE001
            continue


def fit_content_to_canvas(figure, *, may_grow_x: bool = True,
                          may_grow_y: bool = True, rounds: int = 5) -> list:
    """Bring anything drawn outside the canvas back inside it.

    An outside legend is placed relative to the axes, so a long label - "Non
    responder", "CD68+CD163+ macrophages" - hangs off the edge of a fixed canvas.
    Exporting with a tight bounding box hides it, which is exactly why it survived
    so long: the saved file looks right and the preview, and any export at a
    declared size, is where it shows.

    Two strategies, because the right one depends on whether the size is the
    user's choice:

    * free to grow - add canvas and hold the axes at their original inches, so the
      plot area is not sacrificed to make room for a key.
    * pinned - pull the subplot area in, because a figure fitted to a journal
      column cannot be widened and a slightly smaller plot beats a clipped legend.

    Decided per axis. Pinning only a width is the usual way to fit a journal
    column, and growing the figure to hold a legend would hand back a width the
    user did not ask for - while the height, which nobody pinned, is still free to
    grow.

    Returns a note when the figure had to change, so it never comes back
    re-laid-out in silence.
    """
    notes = []
    before = content_overflow_inches(figure)
    if max(before) <= FIT_TOLERANCE_IN:
        return notes
    # A figure on constrained layout places its own axes and refuses
    # subplots_adjust; it already measures its decorations, so leave it be.
    # Specifically constrained layout: calling tight_layout() leaves a
    # PlaceHolderLayoutEngine behind, which is not None, and testing for "any
    # engine" silently skipped this pass on nearly every figure in the project.
    try:
        from matplotlib.layout_engine import ConstrainedLayoutEngine

        if isinstance(figure.get_layout_engine(), ConstrainedLayoutEngine):
            return notes
    except (AttributeError, ImportError):
        pass
    start_w, start_h = (float(v) for v in figure.get_size_inches())

    for _ in range(rounds):
        left, right, bottom, top = content_overflow_inches(figure)
        if max(left, right, bottom, top) <= FIT_TOLERANCE_IN:
            break
        pars = figure.subplotpars
        width_in, height_in = (float(v) for v in figure.get_size_inches())
        # What this round has to beat, and enough state to put the figure back
        # if it does not. Squeezing the plot area is the right move for a legend
        # anchored outside the axes and the wrong one for a wide annotation
        # centred *inside* them - a narrower axes carries that text further off
        # the canvas, not nearer it. Measuring instead of assuming covers both.
        # Judged on the total content outside, not the worst single edge: one
        # round here cleared three edges and lifted the fourth by a fraction,
        # which a worst-edge test calls a regression and throws away along with
        # the three genuine fixes.
        _before = left + right + bottom + top
        _snap = dict(left=pars.left, right=pars.right,
                     bottom=pars.bottom, top=pars.top)
        _snap_size = (width_in, height_in)
        # An edge hanging over by less than the tolerance is not worth moving the
        # figure for. Zeroed per edge, not just overall: the loop runs while ANY
        # edge is over, and without this a real overhang on one axis dragged a
        # hairline on the other along with it, resizing a dimension the user had
        # deliberately left alone.
        left = left if left > FIT_TOLERANCE_IN else 0.0
        right = right if right > FIT_TOLERANCE_IN else 0.0
        bottom = bottom if bottom > FIT_TOLERANCE_IN else 0.0
        top = top if top > FIT_TOLERANCE_IN else 0.0
        # Grow the axis that is free; squeeze the one that is pinned.
        grow_l, grow_r = (left, right) if may_grow_x else (0.0, 0.0)
        grow_b, grow_t = (bottom, top) if may_grow_y else (0.0, 0.0)
        new_w = min(width_in + grow_l + grow_r, start_w + MAX_FIT_GROWTH_IN)
        new_h = min(height_in + grow_b + grow_t, start_h + MAX_FIT_GROWTH_IN)
        shift_x = grow_l if new_w > width_in else 0.0
        shift_y = grow_b if new_h > height_in else 0.0
        squeeze_l = 0.0 if may_grow_x else left
        squeeze_r = 0.0 if may_grow_x else right
        squeeze_b = 0.0 if may_grow_y else bottom
        squeeze_t = 0.0 if may_grow_y else top
        if (new_w <= width_in and new_h <= height_in
                and not max(squeeze_l, squeeze_r, squeeze_b, squeeze_t)):
            break
        try:
            if new_w > width_in or new_h > height_in:
                # Keep the axes the same absolute size; the new canvas is what
                # the overhanging artist moves into.
                figure.set_size_inches(new_w, new_h)
            figure.subplots_adjust(
                left=min(0.45, (pars.left * width_in + shift_x) / new_w
                         + squeeze_l / new_w + (0.004 if squeeze_l else 0.0)),
                right=max(0.55, (pars.right * width_in + shift_x) / new_w
                          - squeeze_r / new_w - (0.004 if squeeze_r else 0.0)),
                bottom=min(0.45, (pars.bottom * height_in + shift_y) / new_h
                           + squeeze_b / new_h + (0.004 if squeeze_b else 0.0)),
                top=max(0.55, (pars.top * height_in + shift_y) / new_h
                        - squeeze_t / new_h - (0.004 if squeeze_t else 0.0)))
        except Exception:  # noqa: BLE001
            break
        _refit_text(figure)
        if sum(content_overflow_inches(figure)) > _before + 1e-6:
            figure.set_size_inches(*_snap_size)
            figure.subplots_adjust(**_snap)
            _refit_text(figure)
            break

    remaining = content_overflow_inches(figure)
    if max(remaining) > FIT_TOLERANCE_IN:
        # Axes placed by a divider (a colourbar appended beside the plot) ignore
        # subplotpars entirely, so the loop above cannot move them. tight_layout
        # with a reserved rect can.
        _was = sum(remaining)
        _pars = figure.subplotpars
        _snap = dict(left=_pars.left, right=_pars.right,
                     bottom=_pars.bottom, top=_pars.top)
        try:
            _l, _r, _b, _t = remaining
            width_in, height_in = (float(v) for v in figure.get_size_inches())
            figure.tight_layout(rect=(_l / width_in, _b / height_in,
                                      1.0 - _r / width_in, 1.0 - _t / height_in))
        except Exception:  # noqa: BLE001
            pass
        _refit_text(figure)
        remaining = content_overflow_inches(figure)
        if sum(remaining) > _was + 1e-6:
            # tight_layout reports that it could not honour the rect and lays the
            # figure out anyway; the result can be worse than what it replaced.
            figure.subplots_adjust(**_snap)
            _refit_text(figure)
            remaining = content_overflow_inches(figure)

    end_w, end_h = (float(v) for v in figure.get_size_inches())
    wider, taller = end_w - start_w > 0.01, end_h - start_h > 0.01
    if wider or taller:
        # Name the dimension that actually changed. Saying "widened" when only the
        # height moved sent people looking for a width problem that was not there,
        # and it reads as a contradiction on a figure whose width was pinned and
        # honoured - which is now every figure with a column width set.
        what = ("widened and made taller" if wider and taller
                else "widened" if wider else "made taller")
        notes.append(
            f"The figure was {what} to {end_w:.2f} x {end_h:.2f} in so the legend "
            f"fits on the canvas. Set a figure size explicitly to keep it fixed.")
    elif max(remaining) <= FIT_TOLERANCE_IN:
        notes.append(
            "The plot area was reduced slightly so the legend fits inside the "
            "figure size you set.")
    elif max(remaining) > FIT_TOLERANCE_IN:
        notes.append(
            f"About {max(remaining) * 72:.0f} pt of the legend or axis labels "
            f"still falls outside the figure. Widen the figure, shorten the "
            f"labels, or move the legend inside the axes.")
    return notes


# How many times a crowded set of labels may be redrawn a point smaller, and the
# step it goes down by. Three steps off a 9.5 pt default reaches 6.5 pt, which is
# still a readable label; past that the figure is too small for the number of
# labels asked for and shrinking further only trades one unreadable result for
# another.
LABEL_SHRINK_STEPS = 3
LABEL_SHRINK_PT = 1.0

# Labels never shrink below this fraction of the size they were asked to be. A
# label two thirds the size of its neighbours is already conspicuous; smaller
# than that and the figure needs fewer labels or more room, which is a decision
# for the person making it.
LABEL_MIN_SHRINK_FRACTION = 0.65


def _keep_labels_inside_axes(ax, texts) -> None:
    """Move any label the solver pushed out of the plot area back inside it.

    ``adjust_text`` separates labels without knowing where the axes ends, and a
    point label is drawn with clipping on, so a label that lands past the edge is
    not merely ugly - matplotlib cuts it in half. On the MA plot two gene names
    came out truncated, one 35 px beyond the right spine, which is the worst kind
    of defect here: the label the author deliberately picked is the one destroyed.

    A point label belongs inside the plot area, so it is shifted back by exactly
    the overhang rather than being re-solved from scratch - the solver's spacing
    is still the best available, and this is the smallest correction that makes it
    drawable.
    """
    figure = ax.figure
    try:
        renderer = figure.canvas.get_renderer()
        box = ax.get_window_extent(renderer)
    except Exception:  # noqa: BLE001
        return
    for text in texts:
        try:
            bb = text.get_window_extent(renderer)
        except Exception:  # noqa: BLE001
            continue
        dx = (box.x0 - bb.x0) if bb.x0 < box.x0 else (box.x1 - bb.x1 if bb.x1 > box.x1 else 0.0)
        dy = (box.y0 - bb.y0) if bb.y0 < box.y0 else (box.y1 - bb.y1 if bb.y1 > box.y1 else 0.0)
        if not dx and not dy:
            continue
        try:
            px, py = ax.transData.transform(text.get_position())
            text.set_position(ax.transData.inverted().transform((px + dx, py + dy)))
        except Exception:  # noqa: BLE001
            continue


def _overlap_count(texts, renderer) -> int:
    boxes = [t.get_window_extent(renderer) for t in texts]
    return sum(1 for i in range(len(boxes)) for j in range(i + 1, len(boxes))
               if boxes[i].overlaps(boxes[j]))


def _shrink_until_separated(ax, texts, points, adjust_text, *, arrowprops, kw,
                            floor_pt=None) -> None:
    """Step the label type down until the repeller can separate them.

    The solver can only move labels into room that exists. Fourteen picked points
    at 9.5 pt fit a 180 mm figure and do not fit a 110 mm one, and since a
    requested width is no longer negotiable the type is what has to give - the
    same trade a person makes by hand. Labels are reset to their points and
    re-solved at each size, because the solver's output is only meaningful for
    the size it was run at.

    Bounded, deterministic, and guarded: a failure here leaves the first
    (overlapping but drawn) result exactly as it was.
    """
    from make_my_figure_core.styles.typography import ABSOLUTE_MIN_PT

    floor = max(float(floor_pt or 0.0), ABSOLUTE_MIN_PT)
    figure = ax.figure
    try:
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        if _overlap_count(texts, renderer) == 0:
            return
    except Exception:  # noqa: BLE001
        return

    kept_texts, kept_patches = list(ax.texts), list(ax.patches)
    size = float(texts[0].get_fontsize())
    if size <= floor:
        return
    for _ in range(LABEL_SHRINK_STEPS):
        size = max(floor, size - LABEL_SHRINK_PT)
        if size <= floor:
            return
        try:
            # Drop the connectors the last pass drew, put every label back on its
            # own point, and solve again at the smaller size.
            for artist in list(ax.patches):
                if artist not in kept_patches:
                    artist.remove()
            for artist in list(ax.texts):
                if artist not in kept_texts:
                    artist.remove()
            for text, (lx, ly, _label) in zip(texts, points):
                text.set_position((lx, ly))
                text.set_fontsize(size)
            adjust_text(texts, ax=ax, arrowprops=arrowprops,
                        iter_lim=LABEL_ADJUST_ITERATIONS, **kw)
            _keep_labels_inside_axes(ax, texts)
            figure.canvas.draw()
            if _overlap_count(texts, figure.canvas.get_renderer()) == 0:
                return
        except Exception:  # noqa: BLE001
            return


def repel_labels(ax, points, style, *, show_arrows=True, box=False, color=None,
                  font_size=None, repel=None, shrink_to_fit=None):
    """Draw point labels with overlap avoidance. Returns how many were drawn.

    Lives here, not in one renderer, because every plot that labels individual
    points has the same problem: a fixed offset puts two labels on top of each
    other the moment two points are close. The volcano had this; the scatter's
    click-to-label did not, and picking several nearby points produced a pile of
    overlapping names.

    Uses ``adjustText`` when installed (with optional subtle connector arrows);
    otherwise falls back to a distance offset. Never fails a render.
    """
    color = color or style.text_color
    fs = font_size or style.annotation_pt
    bbox = dict(boxstyle="round,pad=0.2", fc="white", ec=color, lw=0.5,
                alpha=0.85) if box else None
    texts = []
    for lx, ly, txt in points:
        texts.append(ax.text(lx, ly, txt, fontsize=fs, color=color, zorder=5, bbox=bbox))
    if not texts:
        return 0
    try:
        from adjustText import adjust_text  # type: ignore

        arrowprops = dict(arrowstyle="-", color="0.5", lw=0.5) if show_arrows else None
        kw = {}
        if repel is not None:
            try:
                kw["force_text"] = (float(repel), float(repel))
            except (TypeError, ValueError):
                pass
        adjust_text(texts, ax=ax, arrowprops=arrowprops,
                    iter_lim=LABEL_ADJUST_ITERATIONS, **kw)
        # Keeping a label inside the plot area and re-separating it after the
        # layout moves are corrections that do not change the type size, so they
        # apply however the size was chosen. Only *shrinking* needs permission:
        # a size the caller passed may be the user's own choice, and overriding
        # that would be the control not working.
        #
        # Deciding all three on `font_size is None` was wrong, and measurably so.
        # The lollipop and the network graph compute a default size and pass it,
        # so they were excluded from every correction - and both came out of this
        # release line with more overlapping labels than v1.1.1 had, because the
        # iteration budget that made rendering reproducible also does fewer passes
        # than the old one-second budget managed on a fast machine. They get the
        # corrections now; a size the user actually set is still respected.
        _floor = max(fs * LABEL_MIN_SHRINK_FRACTION, 0.0)
        _may_shrink = (font_size is None) if shrink_to_fit is None else bool(shrink_to_fit)
        _keep_labels_inside_axes(ax, texts)
        if _may_shrink:
            _shrink_until_separated(ax, texts, points, adjust_text,
                                    arrowprops=arrowprops, kw=kw, floor_pt=_floor)

        def _refit(ax=ax, texts=texts, points=points, floor=_floor, shrink=_may_shrink):
            _keep_labels_inside_axes(ax, texts)
            if shrink:
                _shrink_until_separated(ax, texts, points, adjust_text,
                                        arrowprops=arrowprops, kw=kw, floor_pt=floor)
                _keep_labels_inside_axes(ax, texts)

        register_refit(ax.figure, _refit)
        return len(texts)
    except Exception:
        for t in texts:
            t.remove()
        arrowprops = dict(arrowstyle="-", color="0.5", lw=0.5) if show_arrows else None
        for lx, ly, txt in points:
            ax.annotate(txt, (lx, ly), fontsize=fs, color=color, xytext=(4, 4),
                        textcoords="offset points", zorder=5, bbox=bbox,
                        arrowprops=arrowprops)
        return len(points)


def polish_repelled_labels(ax, texts, anchors, adjust_text, *, adjust_kwargs=None,
                           may_shrink=True) -> None:
    """Apply the shared label corrections to labels a renderer solved itself.

    Two renderers - the lollipop and the network graph - call ``adjust_text``
    directly with their own tuning rather than going through :func:`repel_labels`,
    and that tuning is worth keeping. What they were missing is everything that
    happens *after* the solve: pulling a label back inside the plot area, and
    re-separating once the layout pass has moved the axes.

    They are the two plot types that came out of this release line with more
    overlapping labels than v1.1.1 had. The cause was not their tuning but the
    iteration budget that replaced ``adjustText``'s one-second wall clock to make
    rendering reproducible: a fixed 60 passes is less than a fast machine used to
    fit into a second, so a solve that used to converge now sometimes stops short.
    The corrections cover that difference without giving up reproducibility.

    ``anchors`` are the label positions *before* the solve, in data coordinates,
    so a re-solve can start from the points rather than from wherever the last
    pass left things.
    """
    if not texts:
        return
    kwargs = dict(adjust_kwargs or {})
    arrowprops = kwargs.pop("arrowprops", None)
    kwargs.pop("iter_lim", None)
    points = [(float(ax_), float(ay_), t.get_text())
              for (ax_, ay_), t in zip(anchors, texts)]
    floor = max(float(texts[0].get_fontsize()) * LABEL_MIN_SHRINK_FRACTION, 0.0)

    _keep_labels_inside_axes(ax, texts)
    if may_shrink:
        _shrink_until_separated(ax, texts, points, adjust_text,
                                arrowprops=arrowprops, kw=kwargs, floor_pt=floor)

    def _refit():
        _keep_labels_inside_axes(ax, texts)
        if may_shrink:
            _shrink_until_separated(ax, texts, points, adjust_text,
                                    arrowprops=arrowprops, kw=kwargs, floor_pt=floor)
            _keep_labels_inside_axes(ax, texts)

    register_refit(ax.figure, _refit)


# Dash patterns a reference line may use, as the UI offers them.
REFERENCE_LINE_STYLES = {
    "dashed": "--", "dotted": ":", "dash-dot": "-.", "solid": "-",
}


def reference_line_kwargs(spec: Dict[str, Any], style, *, default_style="dashed",
                          default_color="0.5") -> Dict[str, Any]:
    """Styling for a threshold, identity or reference line.

    Ten plot types draw one - a volcano's fold-change cutoffs, a ROC diagonal, a
    Bland-Altman limit of agreement, a waterfall's response thresholds - and each
    had the dash pattern and the grey hard-coded. They are the lines an author is
    most likely to want to restyle or tone down for print, so they get one shared
    control rather than ten different ones or none.
    """
    layout = (spec or {}).get("layout", {}) or {}
    mapping = (spec or {}).get("mapping", {}) or {}
    name = str(mapping.get("reference_line_style")
               or layout.get("reference_line_style") or default_style).lower()
    colour = (mapping.get("reference_line_color")
              or layout.get("reference_line_color") or default_color)
    dash = REFERENCE_LINE_STYLES.get(name, REFERENCE_LINE_STYLES[default_style])
    return {"ls": dash, "color": str(colour), "lw": style.spine_width_pt}


def marker_edge_color(spec: Dict[str, Any], default: str) -> str:
    """The outline colour for point markers, or the plot's own default.

    "auto" is not a colour, it is "whatever this plot was already doing" - white
    to separate overlapping points, black to weight an estimate - so a plot keeps
    its considered default until an author overrides it.
    """
    mapping = (spec or {}).get("mapping", {}) or {}
    chosen = str(mapping.get("marker_edge_color", "auto") or "auto").lower()
    return default if chosen in ("", "auto") else chosen


def role_color(spec: Dict[str, Any], key: str, default: str) -> str:
    """The colour chosen for one named artist, or that artist's own default.

    Plots that are scientifically a single colour were given a categorical palette
    control, which is the wrong instrument: a Q-Q plot has points and a reference
    line, not categories, so the palette appeared to do almost nothing. The honest
    control is one picker per artist the plot actually draws - the way the volcano
    already exposes its up / down / not-significant classes.

    Follows :func:`marker_edge_color` exactly: "(auto)" means "whatever this plot
    was already doing", so a figure made before the control existed is unchanged.
    """
    mapping = (spec or {}).get("mapping", {}) or {}
    chosen = str(mapping.get(key, "") or "").strip()
    return default if chosen.lower() in ("", "auto", "(auto)") else chosen


def bar_thickness(spec: Dict[str, Any], default: float) -> float:
    """How much of its slot a bar fills; ``0`` keeps the plot's own default.

    Each bar-shaped plot picked its own number - 0.6 for an UpSet's matrix,
    0.85 for a waterfall - and those are considered choices, not accidents, so
    the control starts at "leave it alone" rather than imposing one value on all
    of them.
    """
    mapping = (spec or {}).get("mapping", {}) or {}
    try:
        chosen = float(mapping.get("bar_width", 0) or 0)
    except (TypeError, ValueError):
        return default
    return chosen if 0 < chosen <= 1.0 else default


def colorbar_geometry(spec: Dict[str, Any], *, default_fraction: float,
                      default_pad: float) -> Dict[str, float]:
    """``fraction``/``pad`` for a colourbar, from the spec or the plot's default.

    The clustered heatmap has had these controls for a while; four other plots
    that draw a colourbar had the numbers baked in, so the bar's distance from
    the axes - the first thing to adjust when it crowds the tick labels - was
    unreachable. Same option names, so there is one vocabulary.
    """
    layout = (spec or {}).get("layout", {}) or {}
    mapping = (spec or {}).get("mapping", {}) or {}

    def _num(key, fallback):
        value = mapping.get(key, layout.get(key))
        try:
            value = float(value)
        except (TypeError, ValueError):
            return fallback
        return value if value > 0 else fallback

    return {"fraction": _num("colorbar_fraction", default_fraction),
            "pad": _num("colorbar_pad", default_pad)}


def chosen_column_width(spec: Dict[str, Any]) -> "str | None":
    """The width preset the user actually picked, or ``None`` for automatic.

    Several renderers apply a legibility floor to the width they compute - a dot
    matrix needs about 0.3 inch per column before the labels collide. That floor
    is right for the automatic size and wrong as an answer to a direct request:
    on a 28-column matrix it came to 11.4 inches, which is wider than every
    preset, so picking single, onehalf or double all produced the same figure and
    the control looked broken. Asking for a width is an instruction; the renderer
    should obey it and say the labels will be tight, not quietly refuse.
    """
    layout = (spec or {}).get("layout", {}) or {}
    name = str(layout.get("column_width", "") or "").strip().lower()
    if name in CHOSEN_WIDTH_PRESETS:
        return name
    # A measurement - "174mm", or the target an experimental preset pins - is as
    # deliberate a request as picking "single", and is returned so the caller can
    # pass it straight back to ``figure_size_inches``. Treating it as automatic
    # instead let a renderer's legibility floor overrule it, which is how a 174 mm
    # preset came back 50 mm wide of its target.
    if name and name not in ("default", "auto") and resolve_width_mm(name) is not None:
        return name
    return None


def width_floor_note(plot_type: str, requested_in: float, floor_in: float) -> str:
    """The warning that goes with honouring a width below the legibility floor."""
    return (f"The figure was set to {requested_in:.2f} in wide, which is narrower "
            f"than the {floor_in:.2f} in this {plot_type.replace('_', ' ')} needs "
            f"for its labels to stay clear. The width you asked for has been used; "
            f"expect crowding, or choose a wider preset.")


def explicit_figure_size(spec: Dict[str, Any]) -> "tuple[float, float] | None":
    """``(width_in, height_in)`` when the user has pinned both, else ``None``.

    Several renderers size themselves from the data - a heatmap grows with its
    rows, a dendrogram with its leaves - which is the right default but leaves
    the user unable to fit a figure to a column. They call this first and yield
    to it when it returns a size, so an explicit request always wins over a
    computed one, and the computed one still applies when nothing was asked for.

    Prefer :func:`resolve_figure_size` in a renderer: this function deliberately
    answers only the all-or-nothing question (the registry asks it to decide
    whether a canvas was pinned firmly enough to rescale the type hierarchy), so
    a renderer using it alone silently drops a half-pinned size.
    """
    w_in, h_in = pinned_dimension(spec, "width_mm"), pinned_dimension(spec, "height_mm")
    if w_in is None or h_in is None:
        return None
    return (w_in, h_in)


def resolve_figure_size(spec: Dict[str, Any],
                        computed: "tuple[float, float]") -> tuple[float, float]:
    """A renderer's data-driven ``computed`` size with any pinned dimension substituted.

    The same contract as :func:`explicit_figure_size` - an explicit request wins,
    the computed size applies when nothing was asked for - extended to the case
    where only one dimension was pinned. Pinning a width alone is the common way
    to fit a figure to a journal column, and all-or-nothing handling silently
    threw it away.

    The *unpinned* dimension keeps the renderer's computed value rather than being
    rescaled to preserve an aspect ratio (which is what :func:`figure_size` does
    for the preset-sized plot types). For these renderers the computed dimension
    is an absolute legibility requirement - a height of so many inches per row -
    not a ratio, so stretching it along with the width would turn a wide heatmap
    into an unreadably tall one.
    """
    w_in, h_in = float(computed[0]), float(computed[1])
    pinned_w, pinned_h = pinned_dimension(spec, "width_mm"), pinned_dimension(spec, "height_mm")
    return (w_in if pinned_w is None else pinned_w,
            h_in if pinned_h is None else pinned_h)


def apply_axis_overrides(ax, spec: Dict[str, Any], *, axis_min: float = None,
                         axis_max: float = None, tick_values=None,
                         x_extent=None, y_extent=None) -> Dict[str, Any]:
    """Apply optional axis-range and tick overrides from the spec.

    Journals often want a survival or dose axis drawn to a round limit with only the meaningful
    ticks labelled - 0, 50 and 100 on a percent axis - rather than whatever the data happened to
    span and whatever matplotlib chose. Nothing here changes the data: it changes the frame drawn
    around it, and a range that would hide drawn values is refused rather than silently clipping.

    Reads ``mapping['x_min' | 'x_max' | 'y_ticks']`` (the option widgets write into ``mapping``),
    falling back to the same keys in ``layout``. Call this *after* ``style_axes`` so the cosmetics
    do not overwrite it. Returns what was applied, for the metadata record.

    ``x_extent`` / ``y_extent`` are explicit ``(min, max)`` spans of the drawn data. Pass them when
    the renderer knows the span, which is always: the fallback has to infer it from the axes, and an
    artist it does not recognise reads as "no data" - which would turn the refusal below into a
    silent clip.
    """

    def _span(explicit, axis: str):
        """Best available (min, max) of the drawn data on one axis."""
        if explicit is not None:
            lo, hi = (float(v) for v in explicit)
            if math.isfinite(lo) and math.isfinite(hi):
                return lo, hi
        # ``ax.dataLim`` is matplotlib's own union over every artist, so it covers bars and step
        # patches as well as lines. Reading ``ax.lines`` alone missed both.
        interval = ax.dataLim.intervalx if axis == "x" else ax.dataLim.intervaly
        if np.all(np.isfinite(interval)) and interval[1] > interval[0]:
            return float(interval[0]), float(interval[1])
        getter = (lambda ln: ln.get_xdata()) if axis == "x" else (lambda ln: ln.get_ydata())
        drawn = [np.asarray(getter(line), dtype=float) for line in ax.lines if len(getter(line))]
        if drawn:
            finite = np.concatenate([d[np.isfinite(d)] for d in drawn if d.size])
            if finite.size:
                return float(finite.min()), float(finite.max())
        return None
    mapping = spec.get("mapping", {}) or {}
    layout = spec.get("layout", {}) or {}

    def _opt(key):
        value = mapping.get(key, layout.get(key))
        return None if value in (None, "", "auto") else value

    applied: Dict[str, Any] = {}

    x_min, x_max = _opt("x_min"), _opt("x_max")
    if x_min is not None or x_max is not None:
        lo, hi = ax.get_xlim()
        try:
            new_lo = float(x_min) if x_min is not None else lo
            new_hi = float(x_max) if x_max is not None else hi
        except (TypeError, ValueError):
            raise RenderError(
                f"x_min/x_max must be numbers, got {x_min!r} and {x_max!r}."
            )
        if new_hi <= new_lo:
            raise RenderError(
                f"x_max ({new_hi:g}) must be greater than x_min ({new_lo:g})."
            )
        # Refuse a window that would hide plotted points; clipping data silently is the
        # failure this codebase is trying not to repeat.
        span = _span(x_extent, "x")
        if span is not None and (span[0] < new_lo - 1e-9 or span[1] > new_hi + 1e-9):
            raise RenderError(
                f"the requested x range [{new_lo:g}, {new_hi:g}] would hide data spanning "
                f"[{span[0]:g}, {span[1]:g}]. Widen the range, or leave it on auto."
            )
        ax.set_xlim(new_lo, new_hi)
        applied["x_limits"] = [new_lo, new_hi]

    y_min, y_max = _opt("y_min"), _opt("y_max")
    if y_min is not None or y_max is not None:
        lo, hi = ax.get_ylim()
        try:
            new_lo = float(y_min) if y_min is not None else lo
            new_hi = float(y_max) if y_max is not None else hi
        except (TypeError, ValueError):
            raise RenderError(f"y_min/y_max must be numbers, got {y_min!r} and {y_max!r}.")
        if new_hi <= new_lo:
            raise RenderError(f"y_max ({new_hi:g}) must be greater than y_min ({new_lo:g}).")
        span = _span(y_extent, "y")
        if span is not None and (span[0] < new_lo - 1e-9 or span[1] > new_hi + 1e-9):
            raise RenderError(
                f"the requested y range [{new_lo:g}, {new_hi:g}] would hide data spanning "
                f"[{span[0]:g}, {span[1]:g}]. A truncated value axis overstates differences; "
                "widen the range, or leave it on auto."
            )
        ax.set_ylim(new_lo, new_hi)
        applied["y_limits"] = [new_lo, new_hi]

    ticks = _opt("y_ticks")
    if ticks is not None:
        if str(ticks) == "ends_and_midpoint":
            if tick_values is None:
                lo, hi = ax.get_ylim()
                tick_values = [lo, (lo + hi) / 2.0, hi]
            ax.set_yticks(list(tick_values))
            applied["y_ticks"] = list(tick_values)
        else:
            try:
                values = [float(v) for v in str(ticks).replace(";", ",").split(",")
                          if str(v).strip()]
            except ValueError:
                raise RenderError(
                    f"y_ticks must be 'auto', 'ends_and_midpoint', or a comma-separated list of "
                    f"numbers, got {ticks!r}."
                )
            if not values:
                raise RenderError("y_ticks was given no usable numbers.")
            ax.set_yticks(values)
            applied["y_ticks"] = values
    return applied


def style_axes(ax, style: "StyleProfile | None" = None) -> None:
    """Apply common publication axis cosmetics driven by style tokens."""
    if style is not None:
        # ``labelsize`` is set on the Axis itself (not only through rcParams) because
        # matplotlib's automatic tick density (``Axis.get_tick_space``) reads the tick
        # label size at *draw* time. Figures drawn outside the style context -- e.g. the
        # Figure Builder rasterising a panel -- would otherwise be laid out for the
        # default 10 pt and pile large tick labels on top of each other.
        ax.tick_params(direction=style.tick_direction, length=style.tick_length,
                       width=style.tick_width, labelsize=style.tick_label_pt)
        for spine, show in (("top", style.show_top_spine), ("right", style.show_right_spine)):
            if spine in ax.spines:
                ax.spines[spine].set_visible(show)
    else:
        ax.tick_params(direction="out", length=4.0)
        for spine in ("top", "right"):
            if spine in ax.spines:
                ax.spines[spine].set_visible(False)


# A tick label never shrinks below the size the project's own publication check
# requires. Picking a lower number here would mean this helper could quietly turn
# a publication-ready figure into one that fails `publication_check` - which is
# exactly what happened at 5 pt: the heatmap's column labels were taken to 7.5 pt
# and the check reported "Tick labels may be too small". When labels still do not
# fit at this size there are too many of them for the space, and the renderers'
# own "hide the labels" rules are the better answer than illegible text.
def _min_tick_label_pt() -> float:
    try:
        from make_my_figure_core.qa.publication_check import MIN_TICK_PT

        return float(MIN_TICK_PT)
    except Exception:  # noqa: BLE001
        return 8.0


MIN_TICK_LABEL_PT = _min_tick_label_pt()

# The clear space neighbouring tick labels need, as a fraction of their own
# height. Zero would mean "not quite touching", which is what 30 gene labels at
# +0.48 px apart already were, and they were unreadable.
LABEL_GAP_FRACTION = 0.22


def _tick_label_shortfall(ax, axis: str, renderer) -> float:
    """How far the tightest pair of tick labels is from having breathing room, in px.

    Not "do the boxes intersect": consecutive gene labels measured +0.48 px
    apart, which is not an overlap by half a pixel and is unreadable on a slide.
    Text needs a gap proportional to its own size, so the requirement is a
    fraction of the label height rather than zero. Positive means too close.
    """
    getter = ax.get_yticklabels if axis == "y" else ax.get_xticklabels
    labels = [t for t in getter() if t.get_visible() and t.get_text().strip()]
    if len(labels) < 2:
        return 0.0
    boxes = []
    for t in labels:
        try:
            boxes.append(t.get_window_extent(renderer))
        except Exception:  # noqa: BLE001
            return 0.0
    boxes.sort(key=(lambda b: b.y0) if axis == "y" else (lambda b: b.x0))
    height = max(b.height for b in boxes) or 1.0
    needed = max(1.0, LABEL_GAP_FRACTION * height)
    worst = 0.0
    for a, b in zip(boxes, boxes[1:]):
        gap = (b.y0 - a.y1) if axis == "y" else (b.x0 - a.x1)
        worst = min(worst, gap - needed)
    return -worst


def thin_tick_labels(ax, axis: str = "y", *, max_stride: int = 12) -> int:
    """Hide every nth tick label until the rest can be read. Returns the stride.

    Shrinking has a floor - the publication check's own minimum - and below it
    there is nothing left to give: 26 gene names in a 1.5 in panel have about
    4 pt of row each, so at any legible size they overlap. Printing all 26 as a
    grey smear shows nothing at all; showing every third, legibly, shows where
    you are in the matrix. The stride is returned so the caller can say so
    rather than quietly dropping labels.
    """
    figure = ax.figure
    getter = ax.get_yticklabels if axis == "y" else ax.get_xticklabels
    try:
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
    except Exception:  # noqa: BLE001
        return 1
    labels = [t for t in getter() if t.get_text().strip()]
    if len(labels) < 3 or _tick_label_shortfall(ax, axis, renderer) <= 0.0:
        return 1
    for stride in range(2, min(max_stride, len(labels) // 2) + 1):
        for i, t in enumerate(labels):
            t.set_visible(i % stride == 0)
        try:
            figure.canvas.draw()
            renderer = figure.canvas.get_renderer()
        except Exception:  # noqa: BLE001
            break
        if _tick_label_shortfall(ax, axis, renderer) <= 0.0:
            return stride
    # Even the widest stride tried does not clear them; leave the last attempt
    # rather than putting every label back on top of its neighbour.
    return min(max_stride, max(2, len(labels) // 2))


def fit_tick_labels(ax, axis: str = "y", *, floor_pt: float = MIN_TICK_LABEL_PT) -> float:
    """Shrink tick labels until consecutive ones stop overlapping. Returns the size used.

    Label sizes are usually picked from a count - "30 rows, so one point smaller"
    - which cannot know how much room a row actually has. On a clustered heatmap
    drawn at presentation type sizes, 30 gene labels were set at 13 pt into rows
    12 pt tall: every label overlapped its neighbour, and the longest ran under
    the y axis label as well.

    Measuring is the fix. Nothing happens unless neighbouring labels actually
    collide, so a figure that was already correct is untouched; and the size only
    ever goes down to ``floor_pt``, below which the renderer's own decision to
    hide labels is the better one.
    """
    figure = ax.figure
    getter = ax.get_yticklabels if axis == "y" else ax.get_xticklabels
    try:
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
    except Exception:  # noqa: BLE001
        return 0.0

    def shortfall() -> float:
        return _tick_label_shortfall(ax, axis, renderer)

    labels = [t for t in getter() if t.get_visible() and t.get_text().strip()]
    if not labels:
        return 0.0
    size = float(labels[0].get_fontsize())
    if shortfall() <= 0.0:
        return size

    while size > floor_pt:
        size = max(floor_pt, size - 0.5)
        for t in getter():
            t.set_fontsize(size)
        try:
            figure.canvas.draw()
            renderer = figure.canvas.get_renderer()
        except Exception:  # noqa: BLE001
            break
        if shortfall() <= 0.0:
            break
    return size


# Clear space an axis label keeps from the nearest tick label, in pixels. Zero
# would be "not quite touching", which reads as a collision even when it is not.
AXIS_LABEL_MARGIN_PX = 4.0


def clear_axis_label(ax, axis: str = "y", *, max_pad_pt: float = 48.0) -> float:
    """Push an axis label clear of its tick labels. Returns the pad used.

    ``labelpad`` is a fixed number of points, so it cannot know how far the
    longest tick label reaches. On a clustered heatmap the row labels vary in
    width - "G14" against "G107" - and the six longest ran under the y axis label
    at the shipped 6 pt pad. Measuring the drawn text and stepping the pad out
    until it clears costs nothing on a figure that was already correct.
    """
    figure = ax.figure
    label = ax.yaxis.label if axis == "y" else ax.xaxis.label
    getter = ax.get_yticklabels if axis == "y" else ax.get_xticklabels
    if not label.get_text().strip():
        return 0.0
    axis_obj = ax.yaxis if axis == "y" else ax.xaxis
    pad = float(axis_obj.labelpad)

    def collides() -> bool:
        try:
            figure.canvas.draw()
            renderer = figure.canvas.get_renderer()
            lb = label.get_window_extent(renderer)
        except Exception:  # noqa: BLE001
            return False
        for t in getter():
            if not t.get_visible() or not t.get_text().strip():
                continue
            try:
                tb = t.get_window_extent(renderer)
            except Exception:  # noqa: BLE001
                continue
            if (lb.x0 - AXIS_LABEL_MARGIN_PX < tb.x1
                    and lb.x1 + AXIS_LABEL_MARGIN_PX > tb.x0
                    and lb.y0 - AXIS_LABEL_MARGIN_PX < tb.y1
                    and lb.y1 + AXIS_LABEL_MARGIN_PX > tb.y0):
                return True
        return False

    while collides() and pad < max_pad_pt:
        pad = min(max_pad_pt, pad + 2.0)
        axis_obj.labelpad = pad
    return pad


# An axis label is wrapped or shrunk only once it actually runs off the canvas,
# less this much margin. A label that merely over-runs its own axis is normal
# typography and is left alone.
AXIS_LABEL_EDGE_MARGIN_IN = 0.02

# Wrapping past this many lines means the label is a sentence; stop there and
# shrink instead.
MAX_AXIS_LABEL_LINES = 3


def fit_axis_labels(figure, *, floor_pt: float = MIN_TICK_LABEL_PT) -> List[str]:
    """Wrap or shrink an axis label that runs off the edge of the canvas.

    matplotlib deliberately leaves the ALONG-axis extent of an axis label out of
    every tight bounding box it computes (``Axes.get_tightbbox`` always asks the
    axis ``for_layout_only``), because the label is centred on the axes and is
    normally shorter than it. When it is longer, the label runs off the canvas
    and is cropped - "measurement (mean +/- SEM)" came back as "measurement
    (mean +/- SE" on a 2.6 in panel - and none of the layout passes can see it,
    because the measurement they all share is the one that hides it. This is the
    pass that looks directly at the label.

    Wrapping is tried first: two lines of a rotated y label is ordinary
    typography and keeps the type size. Only a label that still does not fit is
    shrunk, and never below ``floor_pt``. Returns a note per label it had to
    change; a figure whose labels already fit is untouched.
    """
    import textwrap

    notes: List[str] = []
    try:
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
    except Exception:  # noqa: BLE001
        return notes
    width_in, height_in = (float(v) for v in figure.get_size_inches())

    def _line_height_in(label) -> float:
        return float(label.get_fontsize()) * 1.4 / 72.0

    def _perp_slack(figure, renderer, axis_name) -> float:
        """Unused canvas inches ACROSS the axis a label belongs to."""
        try:
            box = figure.get_tightbbox(renderer)
        except Exception:  # noqa: BLE001
            return 0.0
        if axis_name == "y":
            return width_in - float(box.width)
        return height_in - float(box.height)

    def _spill(label, axis_name):
        """Inches of the label hanging off the canvas, along the axis it labels.

        Length alone is not the question. An axis label is centred on its AXES,
        and the axes is rarely centred on the canvas - a bar chart with rotated
        tick labels sits in the top 60% of its panel - so a y label comfortably
        shorter than the canvas is tall can still run off the top of it.
        """
        box = label.get_window_extent(renderer)
        if axis_name == "y":
            limit = height_in * figure.dpi
            return max(0.0, -box.y0, box.y1 - limit) / figure.dpi
        limit = width_in * figure.dpi
        return max(0.0, -box.x0, box.x1 - limit) / figure.dpi

    for ax in figure.axes:
        if not ax.get_visible():
            continue
        for axis_name, label in (("x", ax.xaxis.label), ("y", ax.yaxis.label)):
            text = label.get_text()
            if not text.strip() or "\n" in text:
                continue           # already laid out deliberately; leave it alone
            if _spill(label, axis_name) <= AXIS_LABEL_EDGE_MARGIN_IN:
                continue
            original, size = text, float(label.get_fontsize())
            # Wrapping a label costs room ACROSS the axis it labels - a second
            # line of a rotated y label is a second column of text - so it is
            # only the right tool when the figure has that room to give. On a
            # figure already using its full width it would push the canvas
            # wider, which silently breaks a pinned size; there, shrinking is
            # the honest move.
            may_wrap = _perp_slack(figure, renderer, axis_name) > _line_height_in(label)
            for lines in range(2, (MAX_AXIS_LABEL_LINES if may_wrap else 1) + 1):
                candidate = textwrap.fill(original, width=max(6, len(original) // lines),
                                          break_long_words=False)
                if candidate.count("\n") + 1 > MAX_AXIS_LABEL_LINES:
                    break
                label.set_text(candidate)
                figure.canvas.draw()
                if _spill(label, axis_name) <= AXIS_LABEL_EDGE_MARGIN_IN:
                    break
            while (_spill(label, axis_name) > AXIS_LABEL_EDGE_MARGIN_IN
                   and size > floor_pt):
                size = max(floor_pt, size - 0.5)
                label.set_fontsize(size)
                figure.canvas.draw()
            spill = _spill(label, axis_name)
            axis_word = "y" if axis_name == "y" else "x"
            if spill <= AXIS_LABEL_EDGE_MARGIN_IN:
                notes.append(
                    f"The {axis_word} axis label was longer than the figure and has been "
                    f"laid out on {label.get_text().count(chr(10)) + 1} line(s) at "
                    f"{label.get_fontsize():.1f} pt to fit.")
            else:
                notes.append(
                    f"The {axis_word} axis label is too long for this figure size: it has "
                    f"been wrapped and shrunk as far as is readable and still does not "
                    f"fit. Shorten it, or make the figure bigger.")
    return notes


def autorotate_xticklabels(ax, style: "StyleProfile | None" = None, *,
                           rotation: "str | int" = "auto") -> None:
    """Keep categorical x tick labels readable — rotate + size them sensibly.

    This makes the *default* plot readable without the user touching options: long
    or numerous category labels (e.g. sample names) overlap when drawn horizontally,
    so we rotate them and shrink the font as the category count grows.

    ``rotation``:
      * ``"auto"`` (default) — choose 0 / 45 / 90 from label count + length;
      * ``"horizontal"``/``0``, ``45``, ``"vertical"``/``90`` — force that angle.

    No-op when there are no text tick labels. Call it AFTER setting the tick labels
    and BEFORE ``fig.tight_layout()`` so the layout reserves room for the labels.
    """
    ticklabels = ax.get_xticklabels()
    texts = [t.get_text() for t in ticklabels]
    texts = [t for t in texts if t != ""]
    if not texts:
        return
    n = len(texts)
    maxlen = max(len(t) for t in texts)

    if rotation in ("auto", None):
        if n <= 6 and maxlen <= 6:
            angle = 0
        elif n <= 16 and maxlen <= 12:
            angle = 45
        else:
            angle = 90
    else:
        mapping = {"horizontal": 0, "vertical": 90, "none": 0}
        try:
            angle = int(mapping.get(str(rotation).lower(), rotation))
        except (TypeError, ValueError):
            angle = 0
    ha = "right" if 0 < angle < 90 else "center"

    # Rotation (not font shrinking) is what prevents overlap, so keep the font at
    # or above the publication-readable floor (8pt) even for many categories — only
    # trim slightly when very dense.
    base_fs = getattr(style, "tick_label_pt", 10.0) if style is not None else 10.0
    _FLOOR = 8.0
    if n > 24:
        fs = max(_FLOOR, base_fs - 2)
    elif n > 14:
        fs = max(_FLOOR, base_fs - 1)
    else:
        fs = base_fs

    # A rotated multi-line label draws its lines as parallel slanted strips that run into
    # the neighbouring labels; rotated labels are therefore always single-line. The text is
    # set through the formatter (set_xticklabels) because tick Text objects are refreshed
    # from the formatter at draw time.
    if angle and any("\n" in t.get_text() for t in ticklabels):
        joined = [" ".join(part.strip() for part in t.get_text().split("\n") if part.strip())
                  for t in ticklabels]
        ax.set_xticks(ax.get_xticks())
        ax.set_xticklabels(joined)
        ticklabels = ax.get_xticklabels()

    for t in ticklabels:
        t.set_rotation(angle)
        t.set_horizontalalignment(ha)
        # va="top" keeps rotated labels hanging BELOW the axis. For 90° the "anchor"
        # rotation mode pushes the label up into the plot (overlapping bars), so use
        # the default mode there; keep anchor for slanted (0<angle<90) labels.
        t.set_verticalalignment("top")
        t.set_rotation_mode("anchor" if 0 < angle < 90 else "default")
        t.set_fontsize(fs)


# An outside legend may not cost more than this fraction of the figure width.
# Past it the figure is a key with a picture attached: a two-group scatter's
# legend measured 1.55 in beside a 4.1 in panel, which left the plot 1.9 in wide
# and its own regression-stats box covering a third of that. A legend that
# expensive goes inside instead, where it costs no plotting width at all. The
# threshold is set so a figure at the style's own size keeps the outside legend
# it was designed with, and only a panel too small for one loses it.
MAX_OUTSIDE_LEGEND_WIDTH_FRACTION = 1.0 / 3.0

# Clear space between an outside legend and the plot, in inches.
OUTSIDE_LEGEND_GAP_IN = 0.06

# The most of a figure's width an outside legend may be given. A legend wider
# than this is a figure that needs a different layout, not a thinner plot.
_MAX_LEGEND_RESERVE = 0.62


def _outside_legend_cost(ax, leg) -> float:
    """The fraction of the figure width an outside legend takes (0 if unmeasurable)."""
    figure = ax.figure
    try:
        figure.canvas.draw()
        box = leg.get_window_extent(figure.canvas.get_renderer())
    except Exception:  # noqa: BLE001
        return 0.0
    width_in = float(figure.get_size_inches()[0])
    if width_in <= 0:
        return 0.0
    return (box.width / figure.dpi) / width_in


# How much of the plotted data an inside legend may cover before an expensive
# outside legend is the better trade. Two per cent is "a stray point behind the
# box", which is what matplotlib's own ``loc="best"`` settles for on a figure
# with an empty corner; a dense volcano has no such corner and keeps its legend
# outside however much width that costs.
MAX_LEGEND_DATA_OVERLAP = 0.02


def _legend_data_overlap(ax, leg) -> float:
    """The fraction of the plotted points an inside legend's box covers.

    Returns 1.0 when there is nothing measurable to compare against, so a plot
    type whose data this cannot see keeps the placement its renderer asked for
    rather than being moved on a guess.
    """
    figure = ax.figure
    try:
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        box = leg.get_window_extent(renderer)
    except Exception:  # noqa: BLE001
        return 1.0
    points = []
    for coll in ax.collections:
        try:
            offsets = coll.get_offsets()
        except Exception:  # noqa: BLE001
            continue
        try:
            points.extend(ax.transData.transform(offsets))
        except Exception:  # noqa: BLE001
            continue
    for line in ax.lines:
        try:
            xy = line.get_xydata()
            if len(xy):
                points.extend(ax.transData.transform(xy))
        except Exception:  # noqa: BLE001
            continue
    # A plot that labels its own points has no spare corner, whatever the
    # measurement says at this moment: those labels are positioned in DATA
    # coordinates and are still being repelled apart by later layout passes, so
    # a volcano's upper left is empty when the legend is placed and holds
    # GENE0165 by the time the figure is drawn. Text the renderer pinned to a
    # CORNER (a stats box at axes coordinates) does not move and is measured
    # honestly below.
    for text in ax.texts:
        if not text.get_visible() or not text.get_text().strip():
            continue
        if text.get_transform() is ax.transData:
            return 1.0
        try:
            tb = text.get_window_extent(renderer)
        except Exception:  # noqa: BLE001
            continue
        if not (tb.x1 < box.x0 or tb.x0 > box.x1 or tb.y1 < box.y0 or tb.y0 > box.y1):
            return 1.0
    if not points:
        return 1.0
    inside = sum(1 for px, py in points
                 if box.x0 <= px <= box.x1 and box.y0 <= py <= box.y1)
    return inside / len(points)


def _reserve_for_outside_legend(ax, leg, side: str = "right") -> None:
    """Reserve exactly the room the legend measures, not a fixed fraction.

    ``subplots_adjust(right=0.75)`` is right for one figure size and wrong for
    every other: the same legend is a quarter of a 5 in figure and a half of a
    2.5 in panel, so a fixed reserve either clips the legend or takes plotting
    width that nothing uses.
    """
    cost = _outside_legend_cost(ax, leg)
    if cost <= 0:
        return
    width_in = float(ax.figure.get_size_inches()[0])
    pad = OUTSIDE_LEGEND_GAP_IN / max(width_in, 1e-6)
    try:
        # The floor is low on purpose. Clamping the reserve at half the figure
        # left a legend that needed 55% of the width still over the edge, and
        # the renderer's own tight_layout then went looking for the room - and
        # took it from the left margin, pushing the y tick labels off the
        # canvas. Reserving what the legend actually measures gives a narrow
        # plot, which is honest, instead of a clipped one.
        if side == "left":
            ax.figure.subplots_adjust(left=min(_MAX_LEGEND_RESERVE, cost + pad))
        else:
            ax.figure.subplots_adjust(right=max(1.0 - _MAX_LEGEND_RESERVE,
                                                1.0 - cost - pad))
    except Exception:  # noqa: BLE001
        pass


# Legend geometry the user can ask for, in the shared layout block. Absent means
# "as the plot type drew it", which is how a figure that has never touched these
# renders exactly as before - and is also the reset.
#
# Offsets and the gap are in POINTS (1/72 in), the unit a figure is specified in,
# so an offset means the same thing at any figure size. The four padding keys are
# in matplotlib's own units (multiples of the legend font size), because they are
# passed straight to the legend and inventing a second unit for them would make
# the numbers disagree with every matplotlib reference.
LEGEND_OFFSET_KEYS = ("legend_offset_x", "legend_offset_y", "legend_gap")
LEGEND_PAD_KEYS = {"legend_borderpad": "borderpad",
                   "legend_labelspacing": "labelspacing",
                   "legend_handlelength": "handlelength",
                   "legend_columnspacing": "columnspacing"}
LEGEND_GEOMETRY_KEYS = tuple(LEGEND_OFFSET_KEYS) + tuple(LEGEND_PAD_KEYS)


def legend_geometry(spec: Dict[str, Any]) -> Dict[str, float]:
    """The legend geometry asked for in ``layout``, as floats. Empty when untouched."""
    layout = (spec or {}).get("layout", {}) or {}
    out: Dict[str, float] = {}
    for key in LEGEND_GEOMETRY_KEYS:
        if layout.get(key) is None:
            continue
        try:
            out[key] = float(layout[key])
        except (TypeError, ValueError):
            continue
    return out


def _legend_pad_kwargs(geometry: Dict[str, float]) -> Dict[str, float]:
    return {arg: geometry[key] for key, arg in LEGEND_PAD_KEYS.items() if key in geometry}


def offset_legend(ax, leg, geometry: Dict[str, float], side: Optional[str] = None) -> None:
    """Shift a placed legend by the requested offset, in points.

    The legend keeps whatever anchor it was given - inside a corner, or outside
    on a side - and the whole anchor box is translated. Doing it this way means
    one implementation covers ``loc="best"``, a named corner and an outside
    placement, instead of three special cases that would each drift.

    ``legend_gap`` is the same movement expressed the way a person thinks about
    an outside legend ("a bit further from the plot"), so it is applied along the
    axis that side hangs off and needs no sign.
    """
    dx = float(geometry.get("legend_offset_x", 0.0))
    dy = float(geometry.get("legend_offset_y", 0.0))
    gap = float(geometry.get("legend_gap", 0.0))
    if gap:
        dx += {"right": gap, "left": -gap}.get(side or "", 0.0)
        dy += {"top": gap, "bottom": -gap}.get(side or "", 0.0)
    if not (dx or dy) or leg is None:
        return
    from matplotlib.transforms import ScaledTranslation

    figure = ax.figure
    try:
        anchor = leg.get_bbox_to_anchor()
        inv = ax.transAxes.inverted()
        (x0, y0), (x1, y1) = inv.transform(anchor.get_points())
        shift = ScaledTranslation(dx / 72.0, dy / 72.0, figure.dpi_scale_trans)
        leg.set_bbox_to_anchor((x0, y0, x1 - x0, y1 - y0),
                               transform=ax.transAxes + shift)
    except Exception:  # noqa: BLE001 - a nicety must never break a render
        pass


def current_legend_placement(ax, leg):
    """``(loc, bbox_to_anchor)`` that puts a re-created legend back where this one is.

    Needed because the padding controls cannot be applied to a legend that
    already exists - matplotlib packs the rows once, at construction - so the
    only way to honour them is to build the legend again. Building it again at a
    *resolved* location would move it, and "give the legend more internal
    padding" must not also relocate a legend the plot type deliberately put
    outside the axes. So the current placement is read back and handed in.
    """
    loc = getattr(leg, "_loc", None)
    bbox = None
    try:
        anchor = leg.get_bbox_to_anchor()
        (x0, y0), (x1, y1) = ax.transAxes.inverted().transform(anchor.get_points())
        is_axes_box = (abs(x0) < 1e-6 and abs(y0) < 1e-6
                       and abs(x1 - 1.0) < 1e-6 and abs(y1 - 1.0) < 1e-6)
        if not is_axes_box:
            bbox = (x0, y0, x1 - x0, y1 - y0)
    except Exception:  # noqa: BLE001
        pass
    return loc, bbox


def outside_legend_side(ax, leg) -> Optional[str]:
    """Which side of the axes a legend hangs off, or ``None`` if it is inside."""
    try:
        renderer = ax.figure.canvas.get_renderer()
        lb = leg.get_window_extent(renderer)
        ab = ax.get_window_extent(renderer)
    except Exception:  # noqa: BLE001
        return None
    if lb.x0 >= ab.x1 - 1:
        return "right"
    if lb.x1 <= ab.x0 + 1:
        return "left"
    if lb.y0 >= ab.y1 - 1:
        return "top"
    if lb.y1 <= ab.y0 + 1:
        return "bottom"
    return None


def reapply_legend_geometry(ax, style, geometry: Dict[str, float]) -> bool:
    """Apply legend geometry to the legend that is already there, in place.

    Geometry is not a relocation: asking for "6 pt further left" or "more room
    between the rows" must leave a legend where its plot type put it. Only
    ``legend_location`` moves a legend. Returns False when there is no legend.
    """
    leg = ax.get_legend()
    if leg is None or not geometry:
        return False
    pads = _legend_pad_kwargs(geometry)
    if pads:
        loc, bbox = current_legend_placement(ax, leg)
        handles = list(getattr(leg, "legend_handles",
                               getattr(leg, "legendHandles", [])))
        labels = [t.get_text() for t in leg.get_texts()]
        title = leg.get_title().get_text() or None
        if handles and len(handles) == len(labels):
            kw = dict(frameon=getattr(style, "legend_frameon", False),
                      ncol=max(1, getattr(style, "legend_ncol", 1)),
                      title=title, **pads)
            try:
                if bbox is not None:
                    leg = ax.legend(handles, labels, loc=loc, bbox_to_anchor=bbox, **kw)
                else:
                    leg = ax.legend(handles, labels, loc=loc, **kw)
            except Exception:  # noqa: BLE001 - keep the original legend
                leg = ax.get_legend()
    offset_legend(ax, leg, geometry, outside_legend_side(ax, leg))
    return True


def apply_named_color_overrides(figure, style) -> List[str]:
    """Recolour whichever artists carry a name the author gave a colour for.

    ``color_overrides`` keyed by POSITION is honoured inside ``color_for``, so it
    works on every plot type without a renderer knowing about it. Keyed by NAME -
    "make Drug_B orange", which is how an author actually thinks - needs the
    category's name at the moment the colour is chosen, and 38 renderers do not
    pass one.

    They do, however, label the artist they draw for each group, because that is
    what the legend is built from. So the name is already on the figure: this
    walks the labelled artists and recolours the ones that match. One
    implementation, no renderer edits, and it cannot touch an artist the author
    did not name.
    """
    overrides = {str(k): str(v) for k, v in (getattr(style, "color_overrides", None)
                                             or {}).items() if not str(k).isdigit()}
    if not overrides or figure is None:
        return []
    applied: List[str] = []
    for ax in figure.axes:
        for artist in list(ax.collections) + list(ax.lines) + list(ax.patches):
            label = str(getattr(artist, "get_label", lambda: "")() or "")
            colour = overrides.get(label)
            if not colour or label.startswith("_"):
                continue
            try:
                if hasattr(artist, "set_facecolor") and hasattr(artist, "set_edgecolor"):
                    artist.set_facecolor(colour)
                elif hasattr(artist, "set_color"):
                    artist.set_color(colour)
                applied.append(label)
            except Exception:  # noqa: BLE001 - an unusable colour is reported below
                continue
        # The key is built from the artists, so it has to be rebuilt after them.
        leg = ax.get_legend()
        if leg is not None and applied:
            handles, labels = ax.get_legend_handles_labels()
            if handles:
                title = leg.get_title().get_text() or None
                loc, bbox = current_legend_placement(ax, leg)
                try:
                    if bbox is not None:
                        ax.legend(handles, labels, loc=loc, bbox_to_anchor=bbox,
                                  title=title,
                                  frameon=getattr(style, "legend_frameon", False))
                    else:
                        ax.legend(handles, labels, loc=loc, title=title,
                                  frameon=getattr(style, "legend_frameon", False))
                except Exception:  # noqa: BLE001
                    pass
    missing = sorted(set(overrides) - set(applied))
    if missing:
        return [f"No drawn group is named {', '.join(repr(m) for m in missing)}, so "
                f"that colour was not used. Name a group exactly as it appears in "
                f"the legend, or give the colour by position instead."]
    return []


def legend_axes(figure):
    """The axes whose legend the layout controls should act on, or ``None``.

    Not simply ``axes[0]``: a composition map puts its key on a second axes and a
    clustered heatmap on a divider, and re-creating a legend on the primary axes
    there would leave the original where it was and add a second one.
    """
    for ax in figure.axes:
        if ax.get_legend() is not None:
            return ax
    return figure.axes[0] if figure.axes else None


def place_legend(ax, style, *, title=None, handles=None, labels=None,
                 force_outside: bool = False, loc: str = None, location=None,
                 geometry: Optional[Dict[str, float]] = None):
    """Place a legend without overlapping data.

    ``location`` is a resolved ``(loc, bbox_to_anchor, outside_side)`` tuple (see
    ``resolve_legend_location``) and, when given, fully controls placement —
    reserving figure margin for whichever outside side is used so the legend is
    never clipped on export. Otherwise falls back to outside-right (when the profile
    / ``force_outside`` requests it) or the profile's preferred location."""
    geometry = geometry or {}
    kw = dict(frameon=getattr(style, "legend_frameon", False),
              ncol=max(1, getattr(style, "legend_ncol", 1)), title=title)
    kw.update(_legend_pad_kwargs(geometry))
    args = ()
    if handles is not None:
        args = (handles,) if labels is None else (handles, labels)

    if location is not None:
        lloc, bbox, side = location
        if bbox is not None:
            leg = ax.legend(*args, loc=lloc, bbox_to_anchor=bbox, **kw)
        else:
            leg = ax.legend(*args, loc=lloc, **kw)
        # Reserve room for an outside legend so it isn't clipped on export. A
        # side the user chose explicitly is honoured whatever it costs; only the
        # width is measured rather than guessed.
        if side in ("right", "left"):
            _reserve_for_outside_legend(ax, leg, side)
        else:
            reserve = {"top": {"top": 0.82}, "bottom": {"bottom": 0.22}}.get(side)
            if reserve:
                try:
                    ax.figure.subplots_adjust(**reserve)
                except Exception:  # noqa: BLE001
                    pass
        offset_legend(ax, leg, geometry, side)
        return leg

    outside = force_outside or getattr(style, "legend_outside", False)
    if outside:
        leg = ax.legend(*args, loc="center left", bbox_to_anchor=(1.02, 0.5), **kw)
        if _outside_legend_cost(ax, leg) > MAX_OUTSIDE_LEGEND_WIDTH_FRACTION:
            # Too expensive for this canvas. Inside costs no width at all - but
            # only where the plot has a corner to spare, so the two costs are
            # compared rather than one being assumed: a two-group regression has
            # an empty upper left and moves in; a volcano with 500 points has
            # none and keeps the width it paid for.
            inside = ax.legend(*args, loc=loc or "best", **kw)
            if _legend_data_overlap(ax, inside) <= MAX_LEGEND_DATA_OVERLAP:
                offset_legend(ax, inside, geometry)
                return inside
            leg = ax.legend(*args, loc="center left", bbox_to_anchor=(1.02, 0.5), **kw)
        _reserve_for_outside_legend(ax, leg, "right")
        offset_legend(ax, leg, geometry, "right")
    else:
        leg = ax.legend(*args, loc=loc or getattr(style, "legend_loc", "best"), **kw)
        offset_legend(ax, leg, geometry)
    return leg


# Named legend positions shared by all renderers (the flexible-legend requirement).
# value: (matplotlib loc, bbox_to_anchor or None, outside-side or None).
LEGEND_LOCATIONS: Dict[str, Any] = {
    "auto": ("best", None, None),
    "best": ("best", None, None),
    "inside upper right": ("upper right", None, None),
    "inside upper left": ("upper left", None, None),
    "inside lower right": ("lower right", None, None),
    "inside lower left": ("lower left", None, None),
    "upper right": ("upper right", None, None),
    "upper left": ("upper left", None, None),
    "lower right": ("lower right", None, None),
    "lower left": ("lower left", None, None),
    "outside right": ("center left", (1.02, 0.5), "right"),
    "outside left": ("center right", (-0.02, 0.5), "left"),
    "outside top": ("lower center", (0.5, 1.02), "top"),
    "outside bottom": ("upper center", (0.5, -0.18), "bottom"),
}


def resolve_legend_location(spec: Dict[str, Any], style: "StyleProfile | None" = None):
    """Return (loc, bbox_to_anchor, outside_side) from layout['legend_location'].

    Falls back to the style's outside preference, else 'best'. Shared so every
    legend-capable renderer honors the same flexible location control."""
    layout = (spec or {}).get("layout", {}) or {}
    name = str(layout.get("legend_location", "")).strip().lower()
    if name in LEGEND_LOCATIONS:
        return LEGEND_LOCATIONS[name]
    if style is not None and getattr(style, "legend_outside", False):
        return LEGEND_LOCATIONS["outside right"]
    return LEGEND_LOCATIONS["best"]


_LAYOUT_NOTES: List[str] = []


def drain_layout_notes() -> List[str]:
    """Messages from the last layout application, and clear them."""
    notes = list(_LAYOUT_NOTES)
    _LAYOUT_NOTES.clear()
    return notes


def resolve_x_tick_rotation_option(spec: Dict[str, Any]) -> Any:
    """The per-plot "X-axis label angle" option, wherever the spec carries it.

    ``x_tick_rotation`` is offered twice: once as ``layout['x_tick_rotation']``
    (every axis plot) and once on the option list of the categorical plot types.
    They are the same control, so the option has to reach the same code path.

    Which block holds the option value is not fixed: both frontends write option
    values into ``spec['mapping']``, while the option declares ``scope="style"``
    (that scope is a *preset portability* class, not a block address - see
    ``presets.option_scopes``), so a spec written by anything that reads the scope
    as a destination lands the value in ``spec['style']`` instead. A renderer that
    looks in only one of those blocks silently ignores the control, which is the
    worst outcome: the author changes the angle and nothing moves.

    Returns ``None`` when unset or left on ``"auto"`` - "auto" means "let the
    renderer choose", so there is nothing to force centrally.
    """
    for block in ("mapping", "style"):
        value = ((spec or {}).get(block) or {}).get("x_tick_rotation")
        if value is None or str(value).strip().lower() in ("", "auto"):
            continue
        return value
    return None


def apply_publication_layout(fig, ax, spec: Dict[str, Any],
                             style: "StyleProfile | None" = None) -> None:
    """Apply the shared PublicationLayoutSpec (spec['layout']) to a rendered axes.

    Reads only the keys present, so it is safe to call from any renderer. Handles
    tick rotation/pad, axis-label padding, title padding, and explicit figure
    margins. Called at the END of a renderer (after ticks/labels are set) so it can
    reserve room and prevent clipping. Never changes data — layout only."""
    layout = (spec or {}).get("layout", {}) or {}

    # Fold the per-plot "X-axis label angle" option into the layout block it
    # duplicates, so one implementation serves both controls. An explicit
    # layout['x_tick_rotation'] wins: it is the more specific setting.
    if layout.get("x_tick_rotation") is None:
        _opt_rotation = resolve_x_tick_rotation_option(spec)
        if _opt_rotation is not None:
            layout = {**layout, "x_tick_rotation": _opt_rotation}

    if not layout:
        return

    _LAYOUT_NOTES.clear()

    def _num(key):
        try:
            v = layout.get(key)
            return None if v is None else float(v)
        except (TypeError, ValueError):
            return None

    def _angle(value):
        """0 / 45 / 90 from a number or the words horizontal / vertical; None if unreadable.

        Written as a lookup *then* a conversion: ``d.get(key, int(value))`` evaluates ``int(value)``
        before the lookup, so the words raised ValueError and were silently skipped.
        """
        named = {"horizontal": 0, "vertical": 90}
        key = str(value).strip().lower()
        if key in named:
            return named[key]
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    # Axis scales (``linear`` | ``log`` | ``symlog``). Applied before tick handling
    # so rotated/padded ticks are computed for the final scale. A log axis is
    # skipped when the data include non-positive values (matplotlib would drop them).
    for axis_name, key in (("x", "x_scale"), ("y", "y_scale")):
        scale = layout.get(key)
        if scale is None or str(scale).lower() in ("", "linear", "auto"):
            continue
        scale = str(scale).lower()
        if scale not in ("log", "symlog"):
            continue
        try:
            if scale == "log":
                lo = (ax.get_xlim() if axis_name == "x" else ax.get_ylim())[0]
                data_min = None
                for line in ax.get_lines():
                    d = line.get_xdata() if axis_name == "x" else line.get_ydata()
                    d = np.asarray(d, dtype=float)
                    d = d[np.isfinite(d)]
                    if d.size:
                        data_min = d.min() if data_min is None else min(data_min, d.min())
                if data_min is not None and data_min <= 0:
                    continue
            (ax.set_xscale if axis_name == "x" else ax.set_yscale)(scale)
        except (TypeError, ValueError):
            pass

    # Tick rotation + alignment.
    xr = layout.get("x_tick_rotation")
    if xr is not None and xr != "auto":
        try:
            ang = _angle(xr)
            if ang is None:
                raise ValueError(xr)
            ha = "right" if 0 < ang < 90 else "center"
            for t in ax.get_xticklabels():
                t.set_rotation(ang)
                t.set_horizontalalignment(layout.get("x_tick_horizontal_alignment", ha))
                t.set_verticalalignment(layout.get("x_tick_vertical_alignment", "top"))
                # anchor mode only for slanted labels; 90° uses default so the label
                # hangs below the axis instead of overlapping the plot.
                t.set_rotation_mode("anchor" if 0 < ang < 90 else "default")
        except (TypeError, ValueError):
            pass
    yr = layout.get("y_tick_rotation")
    if yr is not None and yr != "auto":
        try:
            ang = _angle(yr)
            if ang is None:
                raise ValueError(yr)
            for t in ax.get_yticklabels():
                t.set_rotation(ang)
        except (TypeError, ValueError):
            pass

    # Tick padding.
    if _num("x_tick_pad") is not None:
        ax.tick_params(axis="x", pad=_num("x_tick_pad"))
    if _num("y_tick_pad") is not None:
        ax.tick_params(axis="y", pad=_num("y_tick_pad"))
    # Tick labels and axis labels, on or off.
    #
    # One control for every plot type, applied here with the rest of the shared
    # layout, because the need is the same everywhere: a heatmap whose 30 row
    # names will not fit, a panel whose axis is already named by the panel
    # beside it, a figure whose caption says what the x axis is. Hiding tick
    # labels hides their tick marks too. Only the explicit False does anything - the key being absent, or True, leaves the
    # renderer's own decision alone, so no existing figure changes. The reserved
    # margin is not reclaimed here (the layout pass has already run); an export
    # is written with a tight bounding box, so it does not show in the file, and
    # a panel in a composite has its margins re-fitted anyway.
    # The tick MARKS go with their labels. A row of bare dashes down the side of
    # a heatmap, with nothing beside them, reads as a figure someone forgot to
    # finish - the mark is only there to point at the label.
    if layout.get("show_x_tick_labels") is False:
        ax.tick_params(axis="x", which="both", bottom=False, top=False,
                       labelbottom=False, labeltop=False)
    if layout.get("show_y_tick_labels") is False:
        ax.tick_params(axis="y", which="both", left=False, right=False,
                       labelleft=False, labelright=False)
    if layout.get("show_x_label") is False:
        ax.set_xlabel("")
    if layout.get("show_y_label") is False:
        ax.set_ylabel("")
    # Axis-label padding.
    if _num("x_label_pad") is not None:
        ax.xaxis.labelpad = _num("x_label_pad")
    if _num("y_label_pad") is not None:
        ax.yaxis.labelpad = _num("y_label_pad")
    # Title padding (preserve current title + fontsize).
    if _num("title_pad") is not None and ax.get_title():
        ax.set_title(ax.get_title(), pad=_num("title_pad"),
                     fontsize=getattr(style, "title_font_pt", None))

    # Explicit figure margins, as matplotlib edge POSITIONS in figure fractions:
    # left/bottom are measured from the left/bottom edge, right/top are the
    # position of the far edge (so right=0.75 leaves a quarter of the width
    # blank on the right). Applied last so they win over tight_layout.
    #
    # 0 means "leave this edge alone". The control is labelled that way, and
    # passing a literal 0 through produced left >= right, which matplotlib
    # rejects - and the rejection used to be swallowed, so NONE of the margins
    # applied and the user was told nothing.
    sub = {}
    for key in ("left", "right", "top", "bottom"):
        v = _num(f"margin_{key}")
        if v is not None and v != 0:
            sub[key] = v
    for key, spec_key in (("wspace", "subplot_wspace"), ("hspace", "subplot_hspace")):
        v = _num(spec_key)
        if v is not None:
            sub[key] = v
    if sub:
        problems = []
        if "left" in sub and "right" in sub and sub["left"] >= sub["right"]:
            problems.append(f"left margin {sub['left']:g} must be less than right "
                            f"{sub['right']:g} (both are positions from the left edge)")
        if "bottom" in sub and "top" in sub and sub["bottom"] >= sub["top"]:
            problems.append(f"bottom margin {sub['bottom']:g} must be less than top "
                            f"{sub['top']:g} (both are positions from the bottom edge)")
        if problems:
            # Report rather than swallow: silently ignoring every margin because
            # one pair is inverted is the behaviour that made this hard to use.
            _LAYOUT_NOTES.extend(problems)
        else:
            try:
                fig.subplots_adjust(**sub)
            except Exception as exc:  # noqa: BLE001 - never break a render
                _LAYOUT_NOTES.append(f"Figure margins were not applied: {exc}")


def dedupe_labels_by_distance(points, *, min_dx, min_dy):
    """Greedily drop labels too close to an already-kept one (simple de-overlap).

    ``points`` is a list of ``(x, y, payload)``; returns the kept subset in the
    input order. Used to reduce gene/point-label collisions.
    """
    kept = []
    for x, y, payload in points:
        if all(abs(x - kx) > min_dx or abs(y - ky) > min_dy for kx, ky, _ in kept):
            kept.append((x, y, payload))
    return kept


def choose_label_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Pick the best identifier column for click-identify/label.

    Returns the first candidate column that exists and is mostly populated
    (>=50% non-blank), else the first existing candidate, else ``None``. Using a
    single consistent column keeps the identified name and the labelled name the
    same, so click-to-label reliably annotates that point.
    """
    present = [c for c in candidates if c and c in df.columns]
    n = max(len(df), 1)
    for c in present:
        # Pure-Python coercion (never rely on the pandas .str accessor / dtype,
        # which can differ across versions and error on mixed/float columns).
        nonblank = 0
        for v in df[c].tolist():
            s = ("" if v is None else str(v)).strip()
            if s and s.lower() != "nan":
                nonblank += 1
        if nonblank / n >= 0.5:
            return c
    return present[0] if present else None


def resolve_point_labels(df: pd.DataFrame, column: Optional[str]) -> List[str]:
    """Per-row identifier list from ``column`` (blank/NaN rows fall back to index)."""
    n = len(df)
    if not column or column not in df.columns:
        return [str(i) for i in range(n)]
    out = []
    for i, v in enumerate(df[column].tolist()):
        s = ("" if v is None else str(v)).strip()
        out.append(s if (s and s.lower() != "nan") else str(i))
    return out


def build_pickable_points(xs, ys, labels, point_ids=None) -> List[Dict[str, Any]]:
    """Return a click-identify table: one record per plotted point.

    Each record is ``{"x", "y", "label", "index", "point_id"}`` in the axes' data
    coordinates, so a GUI can map a click on the live canvas back to the underlying
    feature (e.g. a specific peptide) without the renderer knowing anything about the
    GUI. ``point_id`` is a **stable per-point identity** (so two rows sharing a gene
    symbol stay distinct); when ``point_ids`` is not supplied it defaults to
    ``row_<positional index>``. Non-finite points are skipped. Used by the desktop
    "identify / label points" mode.
    """
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    out: List[Dict[str, Any]] = []
    for i in range(min(len(xs), len(ys))):
        xv, yv = xs[i], ys[i]
        if not (np.isfinite(xv) and np.isfinite(yv)):
            continue
        lab = str(labels[i]) if labels is not None and i < len(labels) else str(i)
        pid = (str(point_ids[i]) if point_ids is not None and i < len(point_ids)
               else f"row_{i}")
        out.append({"x": float(xv), "y": float(yv), "label": lab, "index": int(i),
                    "point_id": pid})
    return out


def nearest_pickable(points, xd: float, yd: float, xspan: float, yspan: float):
    """Nearest pickable point to a click at ``(xd, yd)`` in data coords.

    Distances are normalized by the axis spans so x/y are comparable. Returns
    ``(point, normalized_distance)`` or ``(None, inf)`` if there are no points.
    A GUI typically ignores hits whose normalized distance exceeds a small
    threshold (a click that missed every point).
    """
    xspan = float(xspan) or 1.0
    yspan = float(yspan) or 1.0
    best, best_d = None, float("inf")
    for p in points or []:
        dx = (float(p["x"]) - xd) / xspan
        dy = (float(p["y"]) - yd) / yspan
        d = (dx * dx + dy * dy) ** 0.5
        if d < best_d:
            best, best_d = p, d
    return best, best_d


def base_metadata(spec: Dict[str, Any], style: StyleProfile, df: pd.DataFrame,
                  *, used_columns: List[str]) -> Dict[str, Any]:
    """Construct the common metadata block recorded for every figure."""
    output = spec.get("output", {}) or {}
    meta = {
        "plot_type": spec.get("plot_type"),
        "style_profile": style.name,
        "data_columns_used": [c for c in used_columns if c],
        "n_rows": int(len(df)),
        "statistics": dict(spec.get("statistics", {}) or {}),
        "export_dimensions": {
            "width_mm": output.get("width_mm"),
            "height_mm": output.get("height_mm"),
            "dpi": output.get("dpi"),
        },
        "disclaimer": (
            "Formatted with the Make My Figure Publication style, a general "
            "manuscript-ready visual style. Not an official journal template; "
            "verify against your target journal's author guidelines."
        ),
    }
    # Echo worksheet provenance when the spec carries it (multi-sheet Excel).
    src = spec.get("source")
    if isinstance(src, dict) and src:
        meta["source"] = dict(src)
    return meta
