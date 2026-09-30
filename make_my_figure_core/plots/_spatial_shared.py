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

ORIENTATIONS = ("y_up", "y_down")
UNITS = ("pixel", "micrometre", "millimetre", "arbitrary")
UNIT_LABELS = {"pixel": "px", "micrometre": "µm", "millimetre": "mm", "arbitrary": ""}

# Above this many marks, scatter is rasterised inside vector output. Text, axes,
# legends and scale bars stay vector, so the figure remains publication quality
# without embedding a path per cell.
RASTER_THRESHOLD = 20_000


def spatial_block(spec: Dict[str, Any]) -> Dict[str, Any]:
    """The PlotSpec ``spatial`` block, with the declared defaults filled in."""
    block = dict(spec.get("spatial") or {})
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


def finish_spatial_axes(ax, block: Dict[str, Any], *, show_axes: bool = False) -> None:
    """Apply aspect, orientation and axis visibility. Call once per axes."""
    if block.get("equal_aspect", True):
        ax.set_aspect("equal", adjustable="datalim")
    if block["orientation"] == "y_down" and not ax.yaxis_inverted():
        ax.invert_yaxis()
    if not show_axes:
        ax.set_xticks([]); ax.set_yticks([])
        for side in ("top", "right", "bottom", "left"):
            ax.spines[side].set_visible(False)
        ax.set_xlabel(""); ax.set_ylabel("")


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
        colours[lv] = palette[i % len(palette)] if palette else style.color_for(i)
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
