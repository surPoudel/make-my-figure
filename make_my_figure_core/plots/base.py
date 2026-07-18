"""Shared helpers and result type for plot renderers.

Every renderer receives a validated ``spec`` (PlotSpec dict), a loaded
``pandas.DataFrame``, and a resolved :class:`StyleProfile`, and returns a
:class:`RenderResult` carrying the figure plus a metadata record. Renderers
never mutate their input DataFrame in place (acceptance criterion: "no
renderer mutates input data silently").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from make_my_figure_core.styles.engine import StyleProfile


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


_WIDTH_ALIASES = {"single", "onehalf", "double", "default"}


def figure_size(spec: Dict[str, Any], style: StyleProfile, *, aspect: float) -> tuple[float, float]:
    """Resolve figure size, honoring an optional layout['column_width'] preset.

    Presets: ``default`` (comfortable medium — the out-of-box default),
    ``single``, ``onehalf``, ``double``. An explicit numeric ``layout['aspect']``
    overrides the renderer's aspect when provided.
    """
    layout = spec.get("layout", {}) or {}
    width = str(layout.get("column_width", "default")).lower()
    if width not in _WIDTH_ALIASES:
        width = "default"
    try:
        aspect = float(layout.get("aspect", aspect))
    except (TypeError, ValueError):
        pass
    return style.figure_size_inches(width, aspect=aspect)


def style_axes(ax, style: "StyleProfile | None" = None) -> None:
    """Apply common publication axis cosmetics driven by style tokens."""
    if style is not None:
        ax.tick_params(direction=style.tick_direction, length=style.tick_length,
                       width=style.tick_width)
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


def apply_publication_layout(fig, ax, spec: Dict[str, Any],
                             style: "StyleProfile | None" = None) -> None:
    """Apply the shared PublicationLayoutSpec (spec['layout']) to a rendered axes.

    Reads only the keys present, so it is safe to call from any renderer. Handles
    tick rotation/pad, axis-label padding, title padding, and explicit figure
    margins. Called at the END of a renderer (after ticks/labels are set) so it can
    reserve room and prevent clipping. Never changes data — layout only."""
    layout = (spec or {}).get("layout", {}) or {}
    if not layout:
        return

    def _num(key):
        try:
            v = layout.get(key)
            return None if v is None else float(v)
        except (TypeError, ValueError):
            return None

    # Tick rotation + alignment.
    xr = layout.get("x_tick_rotation")
    if xr is not None and xr != "auto":
        try:
            ang = {"horizontal": 0, "vertical": 90}.get(str(xr).lower(), int(xr))
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
            ang = {"horizontal": 0, "vertical": 90}.get(str(yr).lower(), int(yr))
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

    # Explicit figure margins (fractions). Applied last so they win over tight_layout.
    margins = {k: _num(f"margin_{k}") for k in ("left", "right", "top", "bottom")}
    sub = {"left": margins["left"], "right": margins["right"],
           "top": margins["top"], "bottom": margins["bottom"]}
    sub = {k: v for k, v in sub.items() if v is not None}
    if _num("subplot_wspace") is not None:
        sub["wspace"] = _num("subplot_wspace")
    if _num("subplot_hspace") is not None:
        sub["hspace"] = _num("subplot_hspace")
    if sub:
        try:
            fig.subplots_adjust(**sub)
        except Exception:  # noqa: BLE001 - never break a render on a bad margin combo
            pass


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


def build_pickable_points(xs, ys, labels) -> List[Dict[str, Any]]:
    """Return a click-identify table: one record per plotted point.

    Each record is ``{"x", "y", "label", "index"}`` in the axes' data coordinates,
    so a GUI can map a click on the live canvas back to the underlying feature
    (e.g. a gene) without the renderer knowing anything about the GUI. Non-finite
    points are skipped. Used by the desktop "identify / label points" mode.
    """
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    out: List[Dict[str, Any]] = []
    for i in range(min(len(xs), len(ys))):
        xv, yv = xs[i], ys[i]
        if not (np.isfinite(xv) and np.isfinite(yv)):
            continue
        lab = str(labels[i]) if labels is not None and i < len(labels) else str(i)
        out.append({"x": float(xv), "y": float(yv), "label": lab, "index": int(i)})
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
