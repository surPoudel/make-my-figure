"""Geometry, orientation, scale bars and cropping shared by the spatial renderers.

Three rules are enforced here rather than left to each renderer:

* **Equal aspect by default.** Tissue is not rescalable; a stretched section is a
  wrong picture, not a styling choice.
* **Orientation is declared, never guessed.** Imaging platforms write y downward,
  Cartesian plots read y upward. The renderer flips only when told to, so a
  tissue is never silently mirrored.
* **A scale bar needs real units.** With ``arbitrary`` units no bar is drawn,
  because a bar implies a physical length the data does not carry.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from make_my_figure_core.plots.base import RenderError
from make_my_figure_core.styles.engine import StyleProfile

ORIENTATIONS = ("y_up", "y_down")
UNITS = ("pixel", "micrometre", "millimetre", "arbitrary")
UNIT_LABELS = {"pixel": "px", "micrometre": "µm", "millimetre": "mm", "arbitrary": ""}

# Above this many marks, scatter is rasterised inside vector output. Text, axes,
# legends and scale bars stay vector, so the figure remains publication quality
# without embedding a path per cell.
RASTER_THRESHOLD = 20_000


# Appearance settings a spatial renderer reads from its ``spatial`` block that the
# user may also set from the GUI. A GUI value is the more recent, more specific
# intent, so it wins over whatever the saved spec or the bundled example carried -
# without this a worked example that pins ``cmap`` makes the Palette and colormap
# controls look broken, because nothing the user picks can ever take effect.
GUI_SETTABLE_SPATIAL_KEYS = (
    "cmap", "color_scale", "center", "vmin", "vmax", "percentile_clip", "transform",
    "alpha", "marker", "marker_size", "marker_edgecolor", "missing_color",
    "show_axes", "grid", "legend", "legend_columns", "colorbar", "colorbar_label",
    "palette", "facet_columns", "max_point_area", "size_legend", "scale_bar",
    # ROI appearance. These existed in the renderer but were not listed here, so
    # they could not be set from either frontend - not even by hand-editing the
    # mapping - which is why every ROI came out as a near-black wireframe.
    "roi_edgecolor", "roi_fill_alpha", "roi_linewidth",
)


# Numeric controls whose "nothing chosen" value is 0, not absence.
AUTO_WHEN_ZERO_KEYS = frozenset({
    "marker_size", "facet_columns", "max_point_area", "percentile_clip",
    "legend_columns",
})


def _is_zero(value) -> bool:
    try:
        return float(value) == 0.0
    except (TypeError, ValueError):
        return False


def spatial_block(spec: Dict[str, Any]) -> Dict[str, Any]:
    """The PlotSpec ``spatial`` block, with the declared defaults filled in.

    Appearance keys set from the GUI (which land in ``mapping``) are overlaid on
    top of the saved ``spatial`` block, so a control the user just changed takes
    effect rather than being silently outranked by the file it came from.
    """
    block = dict(spec.get("spatial") or {})
    mapping = (spec or {}).get("mapping") or {}
    for key in GUI_SETTABLE_SPATIAL_KEYS:
        value = mapping.get(key)
        if value is None or value == "":
            continue
        # For the numeric controls labelled "0 = auto", zero is the spinner's
        # resting position, not a choice. Overlaying it would wipe a size the
        # example or the saved file had deliberately pinned, just because the
        # user never touched that control.
        if key in AUTO_WHEN_ZERO_KEYS and _is_zero(value):
            continue
        block[key] = value
    units = block.get("coordinate_units", "arbitrary")
    if units not in UNITS:
        raise RenderError(f"spatial.coordinate_units must be one of {UNITS}, got {units!r}")
    orientation = block.get("orientation", "y_up")
    if orientation not in ORIENTATIONS:
        raise RenderError(f"spatial.orientation must be one of {ORIENTATIONS}, "
                          f"got {orientation!r}")
    block["coordinate_units"] = units
    block["orientation"] = orientation
    block.setdefault("equal_aspect", True)
    return block


def finish_spatial_axes(ax, block: Dict[str, Any], *, show_axes: bool = False,
                        x_label: Optional[str] = None,
                        y_label: Optional[str] = None) -> None:
    """Apply aspect, orientation, axis visibility and - when shown - axis labels.

    Call once per axes. ``x_label``/``y_label`` are the coordinate column names;
    they are only used when the axes are visible.
    """
    if block.get("equal_aspect", True):
        ax.set_aspect("equal", adjustable="datalim")
    if block["orientation"] == "y_down" and not ax.yaxis_inverted():
        ax.invert_yaxis()
    if not show_axes:
        ax.set_xticks([]); ax.set_yticks([])
        for side in ("top", "right", "bottom", "left"):
            ax.spines[side].set_visible(False)
        ax.set_xlabel(""); ax.set_ylabel("")
        return

    # Axes the reader can actually see have to say what they measure. Bare tick
    # numbers leave it open whether 12000 is a pixel, a micrometre or an
    # arbitrary coordinate - and with no axis label drawn, the axis-label
    # typography control has nothing to size, so it reads as a dead control.
    unit = UNIT_LABELS.get(block["coordinate_units"], "")
    suffix = f" ({unit})" if unit else ""
    if not ax.get_xlabel() and (block.get("x_label") or x_label):
        ax.set_xlabel(str(block.get("x_label") or f"{x_label}{suffix}"))
    if not ax.get_ylabel() and (block.get("y_label") or y_label):
        ax.set_ylabel(str(block.get("y_label") or f"{y_label}{suffix}"))
    # A grid on a spatial map only means anything once the ticks it hangs from
    # are visible, so the per-plot setting is applied here rather than earlier.
    # Left alone, the axes keep whatever the style profile's grid setting put on
    # them when they were created.
    if block.get("grid") is not None:
        ax.grid(bool(block["grid"]))


def apply_crop(ax, block: Dict[str, Any]) -> None:
    """Explicit x/y crop. Respects an already-inverted y axis."""
    xlim, ylim = block.get("xlim"), block.get("ylim")
    if xlim:
        ax.set_xlim(float(xlim[0]), float(xlim[1]))
    if ylim:
        lo, hi = float(ylim[0]), float(ylim[1])
        ax.set_ylim((hi, lo) if block["orientation"] == "y_down" else (lo, hi))


def _nice_length(span: float) -> float:
    """A round bar length near one fifth of the visible span."""
    if not np.isfinite(span) or span <= 0:
        return 1.0
    raw = span / 5.0
    mag = 10 ** np.floor(np.log10(raw))
    for mult in (1, 2, 5, 10):
        if raw <= mult * mag:
            return float(mult * mag)
    return float(10 * mag)


def add_scale_bar(ax, block: Dict[str, Any], style) -> Optional[Dict[str, Any]]:
    """Draw a scale bar when units are physical. Returns a provenance record, or None."""
    if not block.get("scale_bar"):
        return None
    units = block["coordinate_units"]
    if units == "arbitrary":
        # Refusing here is the point: a bar would assert a physical length that
        # the coordinates do not have.
        return {"drawn": False,
                "reason": "coordinate units are 'arbitrary'; no physical scale bar was drawn"}

    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    length = block.get("scale_bar_length") or _nice_length(abs(x1 - x0))
    length = float(length)

    # Open a clear band below the data and put the bar in it. Drawing inside the
    # data area lets the bar land on top of cells or glyphs, which is both ugly
    # and ambiguous about what the bar is measuring.
    span_y = abs(y1 - y0) or 1.0
    band = float(block.get("scale_bar_band", 0.12)) * span_y
    if ax.yaxis_inverted():
        ax.set_ylim(max(y0, y1) + band, min(y0, y1))
    else:
        ax.set_ylim(min(y0, y1) - band, max(y0, y1))
    y0, y1 = ax.get_ylim()

    pad_x = 0.04 * abs(x1 - x0)
    xs = min(x0, x1) + pad_x
    ys = (min(y0, y1) + 0.35 * band) if not ax.yaxis_inverted() \
        else (max(y0, y1) - 0.35 * band)

    colour = block.get("scale_bar_color", "black")
    ax.plot([xs, xs + length], [ys, ys], color=colour,
            linewidth=block.get("scale_bar_linewidth", 2.5),
            solid_capstyle="butt", zorder=6, clip_on=False)
    label = block.get("scale_bar_label") or f"{length:g} {UNIT_LABELS[units]}".strip()
    ax.text(xs + length / 2.0, ys, label, color=colour,
            ha="center", va="top" if ax.yaxis_inverted() else "bottom",
            fontsize=getattr(style, "tick_label_size", 8), zorder=6)
    return {"drawn": True, "length": length, "units": units, "label": label}


def draw_background_image(ax, block: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Place a background image using an explicitly declared extent."""
    path = block.get("background_image")
    if not path:
        return None
    extent = block.get("background_extent")
    if not extent or len(extent) != 4:
        raise RenderError(
            "spatial.background_image requires spatial.background_extent "
            "[xmin, xmax, ymin, ymax] in data coordinates. Without it the image cannot be "
            "aligned to the cells, and guessing the extent would misplace the tissue.")
    import hashlib
    import matplotlib.image as mpimg
    img = mpimg.imread(path)
    xmin, xmax, ymin, ymax = (float(v) for v in extent)
    ax.imshow(img, extent=(xmin, xmax, ymin, ymax),
              alpha=float(block.get("background_alpha", 1.0)),
              origin="upper" if block["orientation"] == "y_down" else "lower",
              zorder=0, interpolation="nearest")
    try:
        digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
    except OSError:
        digest = None
    return {"path": str(path), "sha256": digest, "extent": [xmin, xmax, ymin, ymax],
            "alpha": float(block.get("background_alpha", 1.0)),
            "shape": list(getattr(img, "shape", []))}


def facet_grid(n: int, requested_cols: Optional[int] = None) -> Tuple[int, int]:
    """Rows/cols for ``n`` facets, wide rather than tall."""
    if n <= 1:
        return 1, 1
    cols = int(requested_cols) if requested_cols else min(n, int(np.ceil(np.sqrt(n))))
    cols = max(1, min(cols, n))
    return int(np.ceil(n / cols)), cols


def ordered_levels(series: pd.Series, declared: Optional[List[str]]) -> List[str]:
    """Declared order wins; otherwise categorical order; otherwise sorted."""
    present = {str(v) for v in series.dropna().unique()}
    if declared:
        out = [str(v) for v in declared if str(v) in present]
        return out + sorted(present - set(out))
    if isinstance(series.dtype, pd.CategoricalDtype):
        return [str(c) for c in series.cat.categories if str(c) in present]
    return sorted(present)


# The point size a style profile ships with, read from the profile itself so the
# reference below cannot drift away from it.
DEFAULT_STYLE_MARKER_SIZE = float(
    StyleProfile.__dataclass_fields__["marker_size"].default)


def resolve_marker_size(block: Dict[str, Any], *, auto: float, style_size: float) -> float:
    """Point area for one spatial mark, honouring the spec *and* the global control.

    Two intents have to coexist here. A spec - or a bundled example - pins
    ``spatial.marker_size`` because that size suits that tissue: 1.4 pt for
    transcripts, 7 pt for annotated cells. Replacing it with the Publication
    panel's point size would wreck the figure. But a panel control that a plot
    type silently swallows is worse than a missing one, and pinning the size is
    exactly what made the global point size dead on every spatial map.

    So a pinned size is *scaled* by the global control rather than replaced: at
    the profile's own default point size the figure is byte-for-byte what it was,
    and moving the control moves every mark proportionally. With nothing pinned,
    ``auto`` is used as is. ``auto`` is passed separately from ``style_size``
    because a renderer may derive it (a transcript map draws marks a quarter the
    size of a cell map), and the scaling has to be measured against the profile
    default either way.

    A pinned size of zero means "auto" - that is what the GUI's point-size
    spinner sends when the user has not chosen a size.
    """
    try:
        requested = float(block["marker_size"]) if block.get("marker_size") is not None else 0.0
    except (TypeError, ValueError):
        requested = 0.0
    if requested <= 0:
        return float(auto)
    scale = float(style_size) / DEFAULT_STYLE_MARKER_SIZE
    return requested * scale if scale > 0 else requested


def should_rasterize(n_marks: int, block: Dict[str, Any]) -> bool:
    if "rasterize" in block:
        return bool(block["rasterize"])
    return n_marks > RASTER_THRESHOLD


def coordinate_record(x: str, y: str, block: Dict[str, Any]) -> Dict[str, Any]:
    """The coordinate half of the provenance record."""
    return {"x_column": x, "y_column": y,
            "coordinate_units": block["coordinate_units"],
            "orientation": block["orientation"],
            "equal_aspect": bool(block.get("equal_aspect", True)),
            "xlim": block.get("xlim"), "ylim": block.get("ylim")}


def numeric_coordinates(data: pd.DataFrame, x: str, y: str, *, context: str) -> None:
    """Coerce x/y in place and refuse the frame if any coordinate is unusable.

    Dropping these rows silently would quietly change which cells are analysed,
    so a bad coordinate is an error the user has to resolve.
    """
    for col in (x, y):
        data[col] = pd.to_numeric(data[col], errors="coerce")
    bad = int(data[[x, y]].isna().any(axis=1).sum())
    if bad:
        raise RenderError(
            f"{context}: {bad} row(s) have missing or non-numeric coordinates in "
            f"{x!r}/{y!r}. They are not dropped silently - remove or repair them first.")


def share_facet_limits(axes_used, block: Dict[str, Any]) -> bool:
    """Give every facet the same x/y limits when the sections share a coordinate frame.

    Off by default: separate tissue sections usually have unrelated coordinate
    systems, and forcing a common frame would push them into opposite corners of
    their panels. When it is on, one scale bar would be enough - but each facet
    still gets its own, so a panel is never read against the wrong scale.
    """
    if not block.get("share_facet_limits") or len(axes_used) < 2:
        return False
    xs = [ax.get_xlim() for ax in axes_used]
    ys = [ax.get_ylim() for ax in axes_used]
    xlo, xhi = min(a for a, _ in xs), max(b for _, b in xs)
    inverted = axes_used[0].yaxis_inverted()
    flat = [v for pair in ys for v in pair]
    ylo, yhi = min(flat), max(flat)
    for ax in axes_used:
        ax.set_xlim(xlo, xhi)
        ax.set_ylim((yhi, ylo) if inverted else (ylo, yhi))
    return True


# Marker shapes used to disambiguate categories once the colour palette wraps.
CATEGORY_MARKERS = ("o", "s", "^", "D", "v", "P", "X", "*")


def categorical_styles(levels, style, palette=None, base_marker="o"):
    """(colour, marker) per level, unique even when the palette runs out.

    The publication palette is colourblind-safe but finite - eight colours. A
    real annotated tissue section can carry sixteen or more cell types, and
    cycling the palette silently gives two different populations the same
    colour. In a tumour section that can mean Tregs and tumour cells rendered
    identically, which is a misreading rather than a cosmetic flaw.

    So once the palette wraps, the marker shape advances with it: every category
    keeps a distinct (colour, shape) pair, and the caller is told it happened.

    Returns ``(colour_by_level, marker_by_level, warning_or_None)``.
    """
    n_colours = len(palette) if palette else 8
    colours, markers = {}, {}
    for i, lv in enumerate(levels):
        # style.color_for even when a palette was passed in: it is where the
        # per-category overrides and the capacity warning are, and indexing the
        # list directly steps around both.
        colours[lv] = (style.color_for(i, str(lv)) if not palette
                       else str((getattr(style, "color_overrides", None) or {}).get(
                           str(lv),
                           (getattr(style, "color_overrides", None) or {}).get(
                               str(i), palette[i % len(palette)]))))
        wrap = i // n_colours
        markers[lv] = (base_marker if wrap == 0
                       else CATEGORY_MARKERS[wrap % len(CATEGORY_MARKERS)])
    warning = None
    if len(levels) > n_colours:
        warning = (
            f"{len(levels)} categories exceed the {n_colours}-colour palette, so marker "
            "shape varies alongside colour to keep every category distinguishable. "
            "Consider grouping rare categories, or set an explicit palette.")
    return colours, markers, warning


# The least of a requested width that is still left for the plot itself once an
# outside legend has taken its share. Past this the figure is a legend with a
# sliver of data next to it, and moving the legend is the better answer.
MIN_AXES_FRACTION = 0.45


def widen_for_outside_legend(base_w: float, labels, style, title: str = "",
                             limit: "float | None" = None) -> tuple:
    """Figure width that actually contains an outside legend, and the layout rect.

    Reserving a fixed fraction of a fixed-size figure does not work: the legend
    is anchored to the axes, so a long label - "CD68+CD163+ macrophages" in a
    real annotated section - runs off the canvas. Exports with a tight bounding
    box still look right, which is exactly why this is easy to miss; the fixed
    preview is where it shows.

    So the figure grows by roughly the width the labels need, and the axes keep
    their original size instead of being squeezed - unless ``limit`` says a width
    was requested, in which case that width is final and the axes are squeezed.

    Returns ``(total_width_in, rect)`` for ``fig.tight_layout(rect=...)``.
    """
    longest = max([len(str(t)) for t in labels] + [len(str(title))], default=0)
    pt = float(getattr(style, "legend_pt", None) or getattr(style, "tick_label_pt", 8.0))
    # ~0.6 em per character, plus the marker, padding and a small margin.
    legend_in = (longest * 0.6 * pt / 72.0) + 0.55
    legend_in = max(1.1, min(legend_in, 4.0))
    if limit and limit > 0:
        # A width was asked for - a journal column, or a preset's target. Growing
        # past it to fit the legend hands back a figure that is not the width
        # that was requested, so the axes give up the room instead.
        axes_w = max(limit - legend_in, limit * MIN_AXES_FRACTION)
        return limit, (0.0, 0.0, axes_w / limit, 1.0)
    total = base_w + legend_in
    return total, (0.0, 0.0, base_w / total, 1.0)
