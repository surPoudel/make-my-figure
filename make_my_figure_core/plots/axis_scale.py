"""Axis display scaling — logarithmic axes and tick-label notation.

This is DISPLAY, not data. A log10 axis draws 1, 10, 100, 1000 at equal
spacing; the plotted values, every statistic and every exported table still hold
1, 10, 100, 1000. To analyse log10 values instead, the user transforms the data
(``make_my_figure_core.tabular``), which adds a derived column. Keeping the two
apart is what stops a log being taken twice: a log axis over a log-transformed
column is refused here, and a log transformation of an already-log column is
refused there.

Layout keys (all optional; absent means the renderer's own axis is untouched):

``x_scale`` / ``y_scale``
    ``linear`` | ``log10`` | ``log2`` | ``ln`` (``log`` = ``log10``, and
    ``symlog``, kept for specs written before these existed).
``x_tick_format`` / ``y_tick_format``
    ``auto`` | ``plain`` (1, 10, 100, 1,000) | ``power`` (10⁰, 10¹, …; log axes)
    | ``scientific`` (linear axis: 1, 2, 3 with ×10⁶ at the axis end).
``x_minor_ticks`` / ``y_minor_ticks``
    ``True`` | ``False``.
``x_min`` / ``x_max`` / ``y_min`` / ``y_max``
    Explicit axis range. Refused (and reported) if it would hide a plotted
    value, is inverted, or is not positive on a log axis.

Applied once, centrally, right after the renderer draws and before the label
and canvas fitting passes, so wider log tick labels are fitted like any other.
Only plot types whose capability entry says an axis carries a numeric magnitude
accept a scale; elsewhere the request is reported, never silently dropped.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

SCALE_BASES = {"log10": 10.0, "log": 10.0, "log2": 2.0, "ln": math.e}
SCALE_LABELS = {"linear": "Linear", "log10": "Log10", "log2": "Log2", "ln": "Natural log (ln)"}
TICK_FORMATS = ("auto", "plain", "power", "scientific")
TICK_FORMAT_LABELS = {"auto": "Automatic", "plain": "Plain numbers (1, 10, 1,000)",
                      "power": "Powers (10⁰, 10¹, 10²)", "scientific": "Scientific (×10ⁿ)"}
AXIS_KEYS = tuple(f"{a}_{k}" for a in "xy" for k in ("scale", "tick_format", "minor_ticks"))
LIMIT_KEYS = ("x_min", "x_max", "y_min", "y_max")
_BAR_PLOTS = {"barplot_with_error_bar", "grouped_barplot_with_error_bar"}
# Mapping keys that name the column drawn on each axis (first present wins).
_AXIS_COLUMN_KEYS = {"x": ("x",), "y": ("y", "value", "y_col", "response")}


def _requested(layout: Dict[str, Any], axis: str) -> Tuple[Optional[str], Optional[str], Optional[bool]]:
    scale = layout.get(f"{axis}_scale")
    scale = None if scale in (None, "", "auto") else str(scale).strip().lower()
    fmt = layout.get(f"{axis}_tick_format")
    fmt = None if fmt in (None, "", "auto") else str(fmt).strip().lower()
    minor = layout.get(f"{axis}_minor_ticks")
    return scale, fmt, (None if minor is None else bool(minor))


def _in_data_coords(transform, ax, idx: int) -> bool:
    """Whether ``transform`` places coordinate ``idx`` (0 = x, 1 = y) in data units.

    ``axhline`` is drawn with x in axes units and y in data units; a band or
    annotation can be the reverse. Only data-unit coordinates are plotted values.
    """
    try:
        return bool(transform.contains_branch_seperately(ax.transData)[idx])
    except Exception:  # noqa: BLE001 - non-separable transform
        try:
            return bool(transform.contains_branch(ax.transData))
        except Exception:  # noqa: BLE001
            return False


def plotted_values(ax, axis: str, *, include_bar_base: bool = False) -> np.ndarray:
    """Finite data-unit values drawn on ``axis`` by lines, markers, bands and bars.

    A bar's base is left out by default (on a log axis it is where the bar starts,
    not a value). ``include_bar_base=True`` counts it, for checking a LINEAR range:
    a bar chart whose axis does not start at its base exaggerates the differences."""
    from matplotlib.collections import LineCollection, PathCollection, PolyCollection
    from matplotlib.patches import Rectangle

    idx = 0 if axis == "x" else 1
    vals: List[np.ndarray] = []
    for line in ax.get_lines():
        if _in_data_coords(line.get_transform(), ax, idx):
            vals.append(np.asarray(line.get_xdata() if axis == "x" else line.get_ydata(), dtype=float).ravel())
    for coll in ax.collections:
        try:
            if isinstance(coll, PathCollection):
                off = np.asarray(coll.get_offsets(), dtype=float)
                if off.size and _in_data_coords(coll.get_offset_transform(), ax, idx):
                    vals.append(off[:, idx])
            elif isinstance(coll, (PolyCollection, LineCollection)) and \
                    _in_data_coords(coll.get_transform(), ax, idx):
                for path in coll.get_paths():
                    v = np.asarray(path.vertices, dtype=float)
                    if v.size:
                        vals.append(v[:, idx])
        except Exception:  # noqa: BLE001 - an exotic artist never blocks the check
            continue
    for patch in ax.patches:
        if isinstance(patch, Rectangle) and _in_data_coords(patch.get_data_transform(), ax, idx):
            # A bar's value is its far end; its base (0) is where the bar starts, not a value.
            end = patch.get_y() + patch.get_height() if axis == "y" else patch.get_x() + patch.get_width()
            vals.append(np.array([end], dtype=float))
            if include_bar_base:
                vals.append(np.array([patch.get_y() if axis == "y" else patch.get_x()], dtype=float))
    if not vals:
        return np.array([])
    allv = np.concatenate([v for v in vals if v.size])
    return allv[np.isfinite(allv)]


class _PlainFormatter:
    """Tick labels as ordinary numbers with thousands separators: 1, 10, 1,000, 0.01."""

    def __init__(self):
        from matplotlib.ticker import ScalarFormatter

        self._scalar = ScalarFormatter(useOffset=False)
        self._scalar.set_scientific(False)

    def __call__(self, x, pos=None):
        if not np.isfinite(x):
            return ""
        if abs(x - round(x)) < 1e-9 * max(1.0, abs(x)):
            return f"{int(round(x)):,}".replace("-", "−")
        return f"{x:,.10g}".replace("-", "−")


def _log_limits(values: np.ndarray) -> Optional[Tuple[float, float]]:
    """Data-driven limits for a log axis: the positive plotted range plus 6 % (in log units) each side."""
    v = values[values > 0]
    if not v.size:
        return None
    lo, hi = float(v.min()), float(v.max())
    if hi <= lo:
        lo, hi = lo / 3.0, hi * 3.0
    pad = (hi / lo) ** 0.06
    return lo / pad, hi * pad


def _configure_log_ticks(ax, axis: str, base: float, fmt: str, minor: Optional[bool]) -> None:
    """Readable ticks on a log axis at any range.

    A log axis looks the same whatever its base; the base only decides where
    ticks go. Across several decades the ticks sit on powers of the base. Across
    less than ~1.5 decades - most measured responses - powers of the base give
    one tick or none, so ticks go at 1, 2, 5 x 10^k instead, every one labelled.
    """
    from matplotlib import ticker

    axobj = ax.xaxis if axis == "x" else ax.yaxis
    lo, hi = ax.get_xlim() if axis == "x" else ax.get_ylim()
    lo, hi = min(lo, hi), max(lo, hi)
    decades10 = math.log10(hi / lo) if lo > 0 and hi > lo else 0.0
    n_base_ticks = math.floor(math.log(hi, base)) - math.ceil(math.log(lo, base)) + 1 if lo > 0 else 0
    narrow = decades10 < 1.5 or n_base_ticks < 3
    if fmt == "auto":
        fmt = "power" if (base == math.e and not narrow) or lo < 1e-3 or hi > 1e5 else "plain"
    if narrow:
        axobj.set_major_locator(ticker.LogLocator(base=10.0, subs=(1.0, 2.0, 5.0)))
    else:
        axobj.set_major_locator(ticker.LogLocator(base=base))
    if fmt == "plain":
        axobj.set_major_formatter(ticker.FuncFormatter(_PlainFormatter()))
    elif narrow:
        axobj.set_major_formatter(ticker.FuncFormatter(_power_label))
    else:
        axobj.set_major_formatter(ticker.LogFormatterMathtext(base=base))
    axobj.set_minor_formatter(ticker.NullFormatter())
    if minor is False:
        axobj.set_minor_locator(ticker.NullLocator())
    else:
        axobj.set_minor_locator(ticker.LogLocator(base=10.0 if narrow else base, subs="auto"))


def _make_room_for_labels(ax, axis: str, max_rounds: int = 6) -> None:
    """Widen a refitted log range until data-anchored text (significance stars over
    brackets, n labels) lies inside the axes. Refitting to the plotted values alone
    left the top star of every bracket stack outside the plot on all four group plots
    tested; on the linear axis none were."""
    get_lim = ax.get_ylim if axis == "y" else ax.get_xlim
    set_lim = ax.set_ylim if axis == "y" else ax.set_xlim
    idx = 1 if axis == "y" else 0
    texts = [t for t in ax.texts if t.get_text().strip() and _in_data_coords(t.get_transform(), ax, idx)]
    if not texts:
        return
    for _ in range(max_rounds):
        fig = ax.figure
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        box = ax.get_window_extent(renderer)
        lo, hi = get_lim()
        span_px = box.height if axis == "y" else box.width
        top = max((t.get_window_extent(renderer).y1 if axis == "y" else t.get_window_extent(renderer).x1)
                  for t in texts)
        bottom = min((t.get_window_extent(renderer).y0 if axis == "y" else t.get_window_extent(renderer).x0)
                     for t in texts)
        edge_hi = box.y1 if axis == "y" else box.x1
        edge_lo = box.y0 if axis == "y" else box.x0
        over_hi = max(0.0, top - edge_hi) / span_px
        over_lo = max(0.0, edge_lo - bottom) / span_px
        if over_hi <= 0.002 and over_lo <= 0.002:
            return
        ratio = hi / lo
        set_lim(lo / ratio ** (over_lo + 0.02) if over_lo > 0.002 else lo,
                hi * ratio ** (over_hi + 0.02) if over_hi > 0.002 else hi)


def _power_label(x, pos=None) -> str:
    """Every tick as a power of ten: 10⁶, 2×10⁶, 5×10⁶ (matplotlib's own formatter
    leaves the 2× and 5× ticks unlabelled once a range passes one decade)."""
    if not np.isfinite(x) or x <= 0:
        return ""
    e = math.floor(math.log10(x) + 1e-12)
    m = x / 10.0 ** e
    if abs(m - round(m)) < 1e-6:
        m = round(m)
    if m == 1:
        return f"$\\mathdefault{{10^{{{e}}}}}$"
    return f"$\\mathdefault{{{m:g}\\times10^{{{e}}}}}$"


def _user_limits(layout: Dict[str, Any], mapping: Dict[str, Any], axis: str):
    """(lo, hi) the user typed (None where left on auto); layout first, then a per-plot option."""
    out = []
    for key in (f"{axis}_min", f"{axis}_max"):
        v = layout.get(key, mapping.get(key))
        out.append(None if v in (None, "", "auto") else _num(v))
    return out[0], out[1]


def _apply_one(ax, axis: str, scale: Optional[str], fmt: Optional[str], minor: Optional[bool],
               notes: List[str], *, values: np.ndarray, limits: Tuple[Optional[float], Optional[float]]) -> None:
    from matplotlib import ticker

    axobj = ax.xaxis if axis == "x" else ax.yaxis
    set_scale = ax.set_xscale if axis == "x" else ax.set_yscale
    set_lim = ax.set_xlim if axis == "x" else ax.set_ylim
    get_lim = ax.get_xlim if axis == "x" else ax.get_ylim
    name = "X" if axis == "x" else "Y"
    is_log = scale in SCALE_BASES
    if fmt is not None and fmt not in TICK_FORMATS:
        notes.append(f"{name}-axis tick format {fmt!r} is not recognised; use one of {', '.join(TICK_FORMATS)}.")
        fmt = None
    if scale == "symlog":
        set_scale("symlog")
    elif is_log:
        set_scale("log", base=SCALE_BASES[scale])
        # The renderer's limits were chosen for a linear axis - a bar chart starts
        # at 0, which a log axis cannot show, and the range collapses to nothing.
        fitted = _log_limits(values) if values.size else None
        if fitted is not None:
            set_lim(*fitted)
            if limits == (None, None):
                _make_room_for_labels(ax, axis)

    lo, hi = limits
    if lo is not None or hi is not None:
        cur_lo, cur_hi = get_lim()
        new_lo = cur_lo if lo is None else lo
        new_hi = cur_hi if hi is None else hi
        shown = values if (is_log and values.size) else plotted_values(ax, axis, include_bar_base=not is_log)
        if new_hi <= new_lo:
            notes.append(f"{name}-axis range not applied: the maximum ({new_hi:g}) must be greater than the "
                         f"minimum ({new_lo:g}).")
        elif is_log and new_lo <= 0:
            notes.append(f"{name}-axis range not applied: a logarithmic axis needs a minimum greater than 0.")
        elif shown.size and (shown.min() < new_lo - 1e-12 * abs(new_lo) or shown.max() > new_hi + 1e-12 * abs(new_hi)):
            notes.append(f"{name}-axis range not applied: [{new_lo:g}, {new_hi:g}] would hide plotted values "
                         f"spanning [{shown.min():g}, {shown.max():g}] (bars count from their base). A "
                         "truncated value axis overstates differences; widen it, or leave it on auto.")
        else:
            set_lim(new_lo, new_hi)

    if is_log:
        _configure_log_ticks(ax, axis, SCALE_BASES[scale], "power" if fmt == "scientific" else (fmt or "auto"), minor)
        return
    if fmt == "plain":
        axobj.set_major_formatter(ticker.FuncFormatter(_PlainFormatter()))
    elif fmt == "scientific":
        f = ticker.ScalarFormatter(useMathText=True)
        f.set_scientific(True)
        f.set_powerlimits((0, 0))
        axobj.set_major_formatter(f)
    elif fmt == "power":
        notes.append(f"{name}-axis tick labels as powers (10⁰, 10¹, …) need a logarithmic axis; "
                     "for a linear axis choose Scientific (×10ⁿ).")
    if minor is not None:
        axobj.set_minor_locator(ticker.AutoMinorLocator() if minor else ticker.NullLocator())


def apply_axis_scales(fig, ax, spec: Dict[str, Any], plot_type: str) -> List[str]:
    """Apply the requested axis scale, range and tick notation; return notes for the user."""
    layout = (spec or {}).get("layout") or {}
    if not any(k in layout for k in AXIS_KEYS + LIMIT_KEYS):
        return []
    from make_my_figure_core.styles.capabilities import axis_scale_support
    from make_my_figure_core.tabular.transforms import looks_already_log

    notes: List[str] = []
    mapping = (spec or {}).get("mapping") or {}
    for axis in ("x", "y"):
        scale, fmt, minor = _requested(layout, axis)
        in_layout = [layout.get(k) for k in (f"{axis}_min", f"{axis}_max")]
        has_layout_limits = any(v not in (None, "", "auto") for v in in_layout)
        if scale is None and fmt is None and minor is None and not has_layout_limits:
            continue
        name = "X" if axis == "x" else "Y"
        ok, reason = axis_scale_support(plot_type, axis)
        if not ok:
            raw = str(layout.get(f"{axis}_scale") or "").strip().lower()
            if raw in ("log", "symlog") and fmt is None and minor is None:
                # Specs written before these controls existed set layout y_scale
                # "log"/"symlog" on any plot; keep drawing them exactly as then.
                _legacy_scale(ax, axis, raw)
            elif scale is not None or fmt is not None or minor is not None:
                # A range on these plots is the renderer's own option (applied and
                # checked by apply_axis_overrides); only the scale is refused here.
                notes.append(f"{name}-axis scale and tick notation are not available for this plot: "
                             f"{reason}.")
            continue
        if scale not in (None, "linear", "symlog") and scale not in SCALE_BASES:
            notes.append(f"{name}-axis scale {scale!r} is not recognised; use linear, log10, log2 or ln.")
            scale = None
        values = plotted_values(ax, axis)
        limits = _user_limits(layout, mapping, axis)
        if scale in SCALE_BASES:
            column = next((mapping.get(k) for k in _AXIS_COLUMN_KEYS[axis] if mapping.get(k)), None)
            if column and looks_already_log(str(column)):
                notes.append(f"Log {name.lower()} axis not applied: {column!r} already holds log values, "
                             "and a log axis on top would apply the logarithm twice. Use a linear axis.")
                scale = None
            elif limits[0] is not None and limits[0] <= 0:
                notes.append(f"Log {name.lower()} axis not applied: the axis minimum you set ({limits[0]:g}) "
                             "must be greater than 0 on a logarithmic axis.")
                scale = None
            elif values.size and values.min() <= 0:
                notes.append(f"Log {name.lower()} axis not applied: the plotted values include 0 or negative "
                             f"values (smallest {values.min():g}), which a logarithmic axis cannot show. "
                             "Keep a linear axis, or transform the data with an explicit offset you can "
                             "justify (Data ▸ Prepare table).")
                scale = None
        _apply_one(ax, axis, scale, fmt, minor, notes, values=values,
                   limits=limits if has_layout_limits else (None, None))
        if scale in SCALE_BASES and axis == "y" and plot_type in _BAR_PLOTS:
            notes.append("Bars on a logarithmic axis: a bar's length depends on where the axis starts, "
                         "not on zero, so compare bar tops rather than bar lengths. A dot, strip or box "
                         "plot shows the same values without that ambiguity.")
    return notes


def _legacy_scale(ax, axis: str, scale: str) -> None:
    """The behaviour of layout x_scale/y_scale "log"/"symlog" before these controls existed, unchanged:
    a log scale is skipped when line data include values <= 0."""
    try:
        if scale == "log":
            data = [np.asarray(ln.get_xdata() if axis == "x" else ln.get_ydata(), dtype=float)
                    for ln in ax.get_lines()]
            data = [d[np.isfinite(d)] for d in data if d.size]
            if any(d.size and d.min() <= 0 for d in data):
                return
        (ax.set_xscale if axis == "x" else ax.set_yscale)(scale)
    except (TypeError, ValueError):
        pass


def _num(v) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
