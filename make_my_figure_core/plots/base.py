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

from make_my_figure_core.styles.engine import StyleProfile, mm_to_inches


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
    if width not in _WIDTH_ALIASES:
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


def _pinned_dimension(spec: Dict[str, Any], key: str) -> "float | None":
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
    return name if name in CHOSEN_WIDTH_PRESETS else None


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
    w_in, h_in = _pinned_dimension(spec, "width_mm"), _pinned_dimension(spec, "height_mm")
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
    pinned_w, pinned_h = _pinned_dimension(spec, "width_mm"), _pinned_dimension(spec, "height_mm")
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


def place_legend(ax, style, *, title=None, handles=None, labels=None,
                 force_outside: bool = False, loc: str = None, location=None):
    """Place a legend without overlapping data.

    ``location`` is a resolved ``(loc, bbox_to_anchor, outside_side)`` tuple (see
    ``resolve_legend_location``) and, when given, fully controls placement —
    reserving figure margin for whichever outside side is used so the legend is
    never clipped on export. Otherwise falls back to outside-right (when the profile
    / ``force_outside`` requests it) or the profile's preferred location."""
    kw = dict(frameon=getattr(style, "legend_frameon", False),
              ncol=max(1, getattr(style, "legend_ncol", 1)), title=title)
    args = ()
    if handles is not None:
        args = (handles,) if labels is None else (handles, labels)

    if location is not None:
        lloc, bbox, side = location
        if bbox is not None:
            leg = ax.legend(*args, loc=lloc, bbox_to_anchor=bbox, **kw)
        else:
            leg = ax.legend(*args, loc=lloc, **kw)
        # Reserve room for an outside legend so it isn't clipped on export.
        reserve = {"right": {"right": 0.75}, "left": {"left": 0.28},
                   "top": {"top": 0.82}, "bottom": {"bottom": 0.22}}.get(side)
        if reserve:
            try:
                ax.figure.subplots_adjust(**reserve)
            except Exception:  # noqa: BLE001
                pass
        return leg

    outside = force_outside or getattr(style, "legend_outside", False)
    if outside:
        leg = ax.legend(*args, loc="center left", bbox_to_anchor=(1.02, 0.5), **kw)
        ax.figure.subplots_adjust(right=0.75)
    else:
        leg = ax.legend(*args, loc=loc or getattr(style, "legend_loc", "best"), **kw)
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
