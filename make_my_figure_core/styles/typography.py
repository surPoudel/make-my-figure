"""One typography system, shared by every renderer.

The publication style defines a type hierarchy as absolute points:

    title 13.0 · axis label 12.0 · legend title 11.0 · tick 10.0 · legend 10.0
    · annotation 9.5

Those values are the approved style's own, not invented here, and the ratios
between them are what makes a figure look deliberate rather than assembled. The
problem absolute points create is that they are correct for exactly one canvas:
a 13 pt title is right on the 5.12 x 3.69 inch default and overflows a 2 x 1 inch
panel, which is what produces a clipped title and a "figure is small for the
content" warning on an otherwise valid request.

This module scales the whole hierarchy together with the canvas, so the ratios
above are preserved at any size. It deliberately does nothing near the reference
size: a figure a user has not resized must render exactly as it did before, so
scaling only engages once the canvas is far enough from the reference that fixed
points genuinely stop working.
"""

from __future__ import annotations

import math
import textwrap
from dataclasses import replace
from typing import Optional, Tuple

from make_my_figure_core.styles.engine import StyleProfile

# Typography attributes that make up the hierarchy. Scaled together so their
# ratios survive; anything not listed here is left alone.
TYPE_ATTRS = ("title_font_pt", "axis_font_pt", "tick_label_pt",
              "legend_title_pt", "legend_pt", "annotation_pt")

# Below/above these fractions of the reference area, fixed points stop working.
# Between them the figure renders unchanged, so resizing within a normal range
# never silently restyles a figure.
SHRINK_BELOW = 0.60
GROW_ABOVE = 1.80

# Type never shrinks past the point of legibility, nor grows into a poster.
MIN_SCALE = 0.55
MAX_SCALE = 1.60

# Smallest readable size for the smallest element in the hierarchy.
ABSOLUTE_MIN_PT = 4.5


def typography_scale(width_in: float, height_in: float,
                     reference: Tuple[float, float]) -> float:
    """Scale factor for the type hierarchy on a canvas of this size.

    Uses the square root of the area ratio rather than the width ratio: type is a
    two-dimensional thing on the page, and scaling by width alone makes a short
    wide panel illegible.
    """
    ref_w, ref_h = reference
    if ref_w <= 0 or ref_h <= 0 or width_in <= 0 or height_in <= 0:
        return 1.0
    area_ratio = (width_in * height_in) / (ref_w * ref_h)
    if SHRINK_BELOW <= area_ratio <= GROW_ABOVE:
        return 1.0                       # normal range: leave the figure alone
    edge = SHRINK_BELOW if area_ratio < SHRINK_BELOW else GROW_ABOVE
    # Scale from the edge of the dead band, so the transition is continuous
    # rather than a jump the moment the threshold is crossed.
    return max(MIN_SCALE, min(MAX_SCALE, math.sqrt(area_ratio / edge)))


def scaled_for_canvas(style: StyleProfile, width_in: float, height_in: float,
                      *, reference: Optional[Tuple[float, float]] = None
                      ) -> Tuple[StyleProfile, float]:
    """``(style, scale)`` with the type hierarchy fitted to this canvas.

    Returns the original object when no scaling is needed, so the common case
    costs nothing and cannot drift.
    """
    ref = reference or tuple(style.figure_size_inches())
    scale = typography_scale(width_in, height_in, ref)
    if scale == 1.0:
        return style, 1.0
    changes = {}
    for attr in TYPE_ATTRS:
        value = getattr(style, attr, None)
        if isinstance(value, (int, float)) and value > 0:
            changes[attr] = max(ABSOLUTE_MIN_PT, round(float(value) * scale, 2))
    if not changes:
        return style, 1.0
    try:
        return replace(style, **changes), scale
    except TypeError:
        # Not a dataclass instance (a subclass or a stub): fall back to a shallow
        # copy so a styling nicety can never break a render.
        import copy
        clone = copy.copy(style)
        for attr, value in changes.items():
            setattr(clone, attr, value)
        return clone, scale


def describe(style: StyleProfile) -> dict:
    """The hierarchy as a record of points and ratios.

    Used by the tests to assert the ratios have not drifted, and useful for
    reporting a profile's type scale.
    """
    base = getattr(style, "axis_font_pt", 0) or 1.0
    return {attr: {"pt": getattr(style, attr, None),
                   "ratio_to_axis_label": round(getattr(style, attr, 0) / base, 3)}
            for attr in TYPE_ATTRS}


# --------------------------------------------------------------------------
# Titles that are longer than the figure is wide
# --------------------------------------------------------------------------

# A title is treated as fitting while it hangs off the canvas edge by no more than
# this many pixels. At 10 pt and 100 dpi a character is roughly 6 px wide, so a few
# pixels is a sliver of antialiasing rather than a lost letter, and re-laying out a
# title onto three lines to recover 4 px would be a worse figure than the hairline
# clip it fixed.
TITLE_OVERFLOW_TOLERANCE_PX = 4.0

# Wrapping past this many lines means the title is being used as a caption; stop
# rather than push the axes off the figure.
MAX_TITLE_LINES = 4

# The axes may be pushed down to make room for a taller title, but never below
# this fraction of the figure height - a plot squeezed into a sliver under a
# four-line title is worse than being told the title is too long.
MIN_AXES_TOP = 0.55


def _horizontal_overflow(text_obj, figure) -> float:
    """How far ``text_obj`` sticks out past the figure's left and right edges, in px.

    Width alone is not the question. A title is centred on its axes, and the axes
    are inset to leave room for a y-label on the left and perhaps a legend on the
    right, so a title measuring 91% of the figure width can still be clipped at
    both ends. Only the actual bounding box answers it.
    """
    try:
        renderer = figure.canvas.get_renderer()
    except AttributeError:
        return 0.0
    width_px = figure.get_size_inches()[0] * figure.dpi
    if width_px <= 0:
        return 0.0
    box = text_obj.get_window_extent(renderer)
    return max(0.0, -box.x0) + max(0.0, box.x1 - width_px)


def _make_room_above(figure, text_obj) -> bool:
    """Shrink the axes so a title that grew taller still fits on the canvas.

    An axes title is anchored at its bottom edge, so extra lines grow upward and
    off the top of the figure - fixing the horizontal overflow would otherwise
    just move it. Lowering the subplot top pulls the axes, and the title with it,
    back inside.
    """
    try:
        renderer = figure.canvas.get_renderer()
    except AttributeError:
        return False
    height_px = figure.get_size_inches()[1] * figure.dpi
    if height_px <= 0:
        return False
    for _ in range(4):
        overflow = text_obj.get_window_extent(renderer).y1 - height_px
        if overflow <= 0:
            return True
        try:
            top = float(figure.subplotpars.top)
            new_top = max(MIN_AXES_TOP, top - (overflow / height_px) - 0.01)
            if new_top >= top:
                return False
            figure.subplots_adjust(top=new_top)
        except Exception:  # noqa: BLE001
            return False      # constrained layout or a locatable colourbar
    return text_obj.get_window_extent(renderer).y1 <= height_px


def wrap_overlong_titles(figure) -> list:
    """Wrap any title wider than the canvas onto further lines.

    Shrinking is the wrong tool here. A 50-character title on a 4-inch panel needs
    about 3 pt to fit on one line, which is not a title anyone can read, so the
    only honest fix is to use a second line. Does nothing to a title that already
    fits, so figures that were correct are untouched.

    Returns a note per title that had to be wrapped.
    """
    notes = []
    candidates = []
    if getattr(figure, "_suptitle", None) is not None:
        candidates.append(figure._suptitle)
    for ax in figure.axes:
        title = ax.title
        if title is not None and title.get_text().strip():
            candidates.append(title)

    for text_obj in candidates:
        original = text_obj.get_text()
        if not original.strip() or "\n" in original:
            continue            # already laid out deliberately; leave it alone
        if _horizontal_overflow(text_obj, figure) <= TITLE_OVERFLOW_TOLERANCE_PX:
            continue
        # Try successively narrower lines. ``textwrap`` breaks on words, so asking
        # for n lines can yield more than n - the line count has to be checked
        # against the budget rather than inferred from the loop counter.
        fitted, fits = original, False
        for target in range(2, MAX_TITLE_LINES + 1):
            candidate = textwrap.fill(original, width=max(8, len(original) // target),
                                      break_long_words=False)
            if candidate.count("\n") + 1 > MAX_TITLE_LINES:
                break               # narrower would only add more lines
            fitted = candidate
            text_obj.set_text(fitted)
            if _horizontal_overflow(text_obj, figure) <= TITLE_OVERFLOW_TOLERANCE_PX:
                fits = True
                break
        text_obj.set_text(fitted)
        if fitted == original:
            continue
        fits = _make_room_above(figure, text_obj) and fits
        used = fitted.count("\n") + 1
        if fits:
            notes.append(f"The title was too long for the figure width and has been "
                         f"wrapped onto {used} lines.")
        else:
            # Say so plainly rather than stacking lines over the axes.
            notes.append(
                f"The title is too long for this figure width. It has been wrapped "
                f"onto {used} lines and still does not fit; shorten it, or make the "
                f"figure wider.")
    return notes
