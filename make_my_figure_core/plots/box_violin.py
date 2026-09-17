"""Box or violin plot with overlaid observations.

Publication options (all read from ``spec["mapping"]``; see ``ui_hints.OPTIONS`` for scopes and
defaults):

* observations through the shared engine (``plots/observations.py``): ``points`` (legacy toggle),
  ``point_arrangement``, ``point_jitter_width``, ``point_size`` (0 = adaptive; an explicit legacy
  size is honoured exactly), ``point_marker``, ``point_fill``, ``point_edge``, ``point_edge_width``,
  ``point_alpha``. Every observation in the data is drawn; n is never a parameter.
* box / violin styling: ``kind`` (box | violin | box+violin | summary), ``box_width``, ``box_fill``
  (light | filled | outline), ``box_line_width``, ``median_line_width``, ``whisker_cap_width``,
  ``show_outliers`` (unset = only when points are hidden, the historical coupling), ``violin_alpha``.
* layout: ``orientation`` (vertical | horizontal), ``group_spacing``, ``category_order`` (config
  scope: data | alphabetical | median_ascending | median_descending), ``show_n`` (none | below |
  above | legend).
* an optional second grouping column ``hue`` draws dodged boxes per hue level within each x
  category with a legend; statistics are keyed by ``(str(x_level), str(hue))`` so the existing
  within-x comparisons (StatsSpec ``subgroup_column``) draw brackets over the dodged pair.

A spec that carries only ``x``/``y`` (plus the legacy ``kind`` / ``points`` / ``point_size`` /
``x_tick_rotation`` keys) renders as it always did: boxes 0.5 wide at positions 1..n, palette fill at
0.5 alpha, black edges, median at ``style.line_width_pt``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import inspect
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

from make_my_figure_core.plots.base import (
    LEGEND_LOCATIONS,
    RenderResult,
    apply_axis_overrides,
    autorotate_xticklabels,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    place_legend,
    require_columns,
    resolve_legend_location,
    style_axes,
)
from make_my_figure_core.plots.observations import ObservationStyle, add_n_labels, draw_observations
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "boxplot_or_violin_with_points"

KINDS = ("box", "violin", "box+violin", "summary")
BOX_FILLS = ("light", "filled", "outline")
ORIENTATIONS = ("vertical", "horizontal")
CATEGORY_ORDERS = ("data", "alphabetical", "median_ascending", "median_descending")
SHOW_N = ("none", "below", "above", "legend")

_HUE_CLUSTER_WIDTH = 0.8      # fraction of the category spacing a dodged cluster occupies
_INNER_BOX_FRACTION = 0.25    # width of the box drawn inside a violin (kind = box+violin)
_VALUE_PAD_FRACTION = 0.04    # head/foot room kept around the drawn marks on the value axis


@dataclass
class _Element:
    """One drawn distribution: an x category, or one hue level inside an x category."""

    x_level: Any
    hue: Optional[Any]
    position: float
    width: float
    color: str
    values: np.ndarray
    key: Any                              # str(x) | (str(x), str(hue)) - the statistics key
    top: float = float("nan")             # highest drawn mark (whisker / violin / point / outlier)
    bottom: float = float("nan")
    stats: Dict[str, float] = field(default_factory=dict)

    @property
    def n(self) -> int:
        return int(len(self.values))


# --- option parsing -------------------------------------------------------------------------

def _choice(value: Any, choices: Sequence[str], default: str) -> str:
    if value in (None, ""):
        return default
    text = str(value).strip().lower().replace(" ", "")
    return text if text in choices else default


def _number(value: Any, default: float, lo: Optional[float] = None, hi: Optional[float] = None) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(out):
        return default
    if lo is not None:
        out = max(lo, out)
    if hi is not None:
        out = min(hi, out)
    return out


def _box_stats(vals: np.ndarray) -> Dict[str, float]:
    """Quartiles and Tukey whisker ends (1.5 x IQR, the matplotlib default) for one group."""
    q1, med, q3 = (float(v) for v in np.percentile(vals, [25, 50, 75]))
    iqr = q3 - q1
    inside = vals[(vals >= q1 - 1.5 * iqr) & (vals <= q3 + 1.5 * iqr)]
    return {"q1": q1, "median": med, "q3": q3,
            "whisker_lo": float(inside.min()) if len(inside) else q1,
            "whisker_hi": float(inside.max()) if len(inside) else q3}


def _order_levels(levels: List[Any], medians: Dict[Any, float], order: str) -> List[Any]:
    if order == "alphabetical":
        return sorted(levels, key=lambda g: str(g))
    if order in ("median_ascending", "median_descending"):
        finite = [g for g in levels if np.isfinite(medians.get(g, float("nan")))]
        missing = [g for g in levels if g not in finite]
        finite.sort(key=lambda g: medians[g], reverse=(order == "median_descending"))
        return finite + missing
    return list(levels)


# --- drawing --------------------------------------------------------------------------------

def _face_alpha(box_fill: str) -> float:
    return 0.5 if box_fill == "light" else 1.0


def _orientation_kwargs(method, orientation: str) -> dict:
    """Return the keyword that selects the orientation for ``ax.boxplot`` / ``ax.violinplot``.

    matplotlib 3.10 introduced ``orientation=`` and deprecated the boolean ``vert=``; older
    releases (the ``>=3.6`` lower bound of this package) only know ``vert=``. The signature is
    inspected once per call so the renderer works on both without emitting deprecation warnings.
    """
    try:
        params = inspect.signature(method).parameters
    except (TypeError, ValueError):  # pragma: no cover - C-implemented or wrapped callables
        params = {}
    if "orientation" in params:
        return {"orientation": orientation}
    return {"vert": orientation != "horizontal"}


def _draw_boxes(ax, elements: List[_Element], *, orientation: str, box_fill: str, box_lw: float,
                median_lw: float, cap_frac: float, show_outliers: bool, inner: bool) -> None:
    if not elements:
        return
    widths = [e.width * (_INNER_BOX_FRACTION if inner else 1.0) for e in elements]
    bp = ax.boxplot([e.values for e in elements], positions=[e.position for e in elements],
                    widths=widths, capwidths=[w * cap_frac for w in widths], patch_artist=True,
                    showfliers=bool(show_outliers and not inner), manage_ticks=False,
                    **_orientation_kwargs(ax.boxplot, orientation),
                    medianprops={"color": "black", "linewidth": median_lw},
                    whiskerprops={"linewidth": box_lw}, capprops={"linewidth": box_lw},
                    flierprops={"marker": "o", "markersize": 3.5, "markerfacecolor": "none",
                                "markeredgewidth": max(0.5, box_lw * 0.6)})
    for i, (e, box) in enumerate(zip(elements, bp["boxes"])):
        outline = box_fill == "outline" and not inner
        edge = e.color if outline else "black"
        if inner:
            box.set_facecolor("white")
            box.set_alpha(1.0)
        elif outline:
            box.set_facecolor("none")
        else:
            box.set_facecolor(e.color)
            box.set_alpha(_face_alpha(box_fill))
        box.set_edgecolor(edge)
        box.set_linewidth(box_lw)
        for artist in bp["whiskers"][2 * i:2 * i + 2] + bp["caps"][2 * i:2 * i + 2]:
            artist.set_color(edge)
            artist.set_linewidth(box_lw)
        if bp["fliers"]:
            bp["fliers"][i].set_markeredgecolor(edge)


def _draw_violins(ax, elements: List[_Element], *, orientation: str, alpha: float, box_lw: float,
                  median_lw: float, show_medians: bool, warnings: List[str]) -> None:
    for e in elements:
        if e.n < 2 or float(np.ptp(e.values)) == 0.0:
            warnings.append(f"{e.key!s}: a violin needs at least two distinct values (n = {e.n}); "
                            "only the observations are drawn for this group.")
            continue
        parts = ax.violinplot([e.values], positions=[e.position], widths=[e.width], showmeans=False,
                              showmedians=show_medians, showextrema=False,
                              **_orientation_kwargs(ax.violinplot, orientation))
        for body in parts["bodies"]:
            body.set_facecolor(e.color)
            body.set_alpha(alpha)
            body.set_edgecolor("black")
            body.set_linewidth(box_lw)
        if "cmedians" in parts:
            parts["cmedians"].set_color("black")
            parts["cmedians"].set_linewidth(median_lw)


def _draw_summary(ax, elements: List[_Element], *, orientation: str, box_fill: str, box_lw: float,
                  median_lw: float) -> None:
    """Median line plus an interquartile bar - the box without its outline."""
    horizontal = orientation == "horizontal"
    for e in elements:
        s = e.stats
        half = e.width / 2.0
        bar_lw = box_lw * 1.5 if box_fill == "outline" else max(box_lw * 3.0, 2.5)
        bar_alpha = _face_alpha(box_fill)
        if horizontal:
            ax.plot([s["q1"], s["q3"]], [e.position, e.position], color=e.color, lw=bar_lw,
                    alpha=bar_alpha, solid_capstyle="butt", zorder=2)
            ax.plot([s["median"], s["median"]], [e.position - half, e.position + half], color="black",
                    lw=median_lw, solid_capstyle="butt", zorder=2.5)
        else:
            ax.plot([e.position, e.position], [s["q1"], s["q3"]], color=e.color, lw=bar_lw,
                    alpha=bar_alpha, solid_capstyle="butt", zorder=2)
            ax.plot([e.position - half, e.position + half], [s["median"], s["median"]], color="black",
                    lw=median_lw, solid_capstyle="butt", zorder=2.5)


def _legend_handle(color: str, box_fill: str, kind: str, violin_alpha: float) -> Patch:
    if kind == "violin":
        return Patch(facecolor=color, edgecolor="black", alpha=violin_alpha)
    if box_fill == "outline":
        return Patch(facecolor="white", edgecolor=color)
    return Patch(facecolor=color, edgecolor="black", alpha=_face_alpha(box_fill))


def _points_offset_in_data(ax, points: float, *, horizontal: bool) -> float:
    """Convert a length in points to data units along the value axis (for n-label headroom)."""
    bbox = ax.get_window_extent()
    px = points * ax.figure.dpi / 72.0
    if horizontal:
        lo, hi = ax.get_xlim()
        extent = bbox.width
    else:
        lo, hi = ax.get_ylim()
        extent = bbox.height
    return float(px / extent * abs(hi - lo)) if extent else 0.0


def _corner_panel(ax, spec: Dict[str, Any], report, style) -> None:
    """Every statistics result as one text line in a corner panel (horizontal orientation)."""
    from make_my_figure_core.plots import stats_overlay
    from make_my_figure_core.statistics.annotations import build_pairwise_annotations, stat_text_panel
    from make_my_figure_core.statistics.schemas import normalize_stats_spec

    stats_spec = normalize_stats_spec(spec.get("statistics"))
    if not stats_spec.get("annotate", True):
        return
    ann_cfg = stats_spec.get("annotation", {}) or {}
    lines: List[str] = []
    for item in build_pairwise_annotations(report.results, ann_cfg):
        prefix = f"{item.x_level}: " if item.within_x and item.x_level else ""
        lines.append(f"{prefix}{item.group_a} vs {item.group_b}: {item.text}".replace("\n", ", "))
    lines += stat_text_panel([r for r in report.results if r.comparison_type != "two_group"],
                             digits=int(ann_cfg.get("digits", 3)))
    if not lines:
        return
    lo, hi = ax.get_xlim()
    ax.set_xlim(lo, hi + 0.45 * (hi - lo))          # whitespace for the panel, never over the marks
    stats_overlay.annotate_corner(ax, lines, style=style, loc="upper right")
    report.config = dict(report.config or {})
    report.config["_annotation_info"] = {"mode": "corner_panel", "n_lines": len(lines)}


# --- renderer -------------------------------------------------------------------------------

def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    mapping = spec.get("mapping", {}) or {}
    layout = spec.get("layout", {}) or {}
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    hue = get_mapping(spec, "hue") or None
    warnings: List[str] = []
    if hue is not None and str(hue) == str(x):
        warnings.append("The hue column is the same as the x column; it was ignored.")
        hue = None

    kind = _choice(get_mapping(spec, "kind", "box"), KINDS, "box")
    show_points = bool(get_mapping(spec, "points", True))
    obs = ObservationStyle.from_mapping(mapping)
    box_width = _number(mapping.get("box_width"), 0.5, 0.2, 0.9)
    box_fill = _choice(mapping.get("box_fill"), BOX_FILLS, "light")
    box_lw = _number(mapping.get("box_line_width"), 0.0, 0.0, None) or float(style.spine_width_pt)
    median_lw = _number(mapping.get("median_line_width"), 0.0, 0.0, None) or float(style.line_width_pt)
    cap_frac = _number(mapping.get("whisker_cap_width"), 0.5, 0.0, 1.0)
    raw_outliers = mapping.get("show_outliers")
    show_outliers = (not show_points) if raw_outliers in (None, "") else bool(raw_outliers)
    violin_alpha = _number(mapping.get("violin_alpha"), 0.45, 0.05, 1.0)
    orientation = _choice(mapping.get("orientation"), ORIENTATIONS, "vertical")
    horizontal = orientation == "horizontal"
    group_spacing = _number(mapping.get("group_spacing"), 1.0, 0.5, 2.0)
    order = _choice(mapping.get("category_order"), CATEGORY_ORDERS, "data")
    show_n = _choice(mapping.get("show_n"), SHOW_N, "none")

    require_columns(df, [x, y] + ([hue] if hue else []), context=PLOT_TYPE)
    work = df.copy()
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)

    x_levels: List[Any] = list(dict.fromkeys(work[x].tolist()))
    medians = {}
    for g in x_levels:
        vals = work.loc[work[x] == g, y].dropna().to_numpy(dtype=float)
        medians[g] = float(np.median(vals)) if len(vals) else float("nan")
    x_levels = _order_levels(x_levels, medians, order)
    hue_levels: List[Any] = list(dict.fromkeys(work[hue].tolist())) if hue else []

    centres = [1.0 + i * group_spacing for i in range(len(x_levels))]
    elements: List[_Element] = []
    if hue:
        k = max(len(hue_levels), 1)
        slot = _HUE_CLUSTER_WIDTH * group_spacing / k
        width = slot * min(0.92, box_width * 1.6)
        for xi, xl in enumerate(x_levels):
            for hi_, h in enumerate(hue_levels):
                vals = work.loc[(work[x] == xl) & (work[hue] == h), y].dropna().to_numpy(dtype=float)
                pos = centres[xi] + (hi_ - (k - 1) / 2.0) * slot
                elements.append(_Element(xl, h, pos, width, style.color_for(hi_), vals, (str(xl), str(h))))
    else:
        for xi, xl in enumerate(x_levels):
            vals = work.loc[work[x] == xl, y].dropna().to_numpy(dtype=float)
            elements.append(_Element(xl, None, centres[xi], box_width, style.color_for(xi), vals, str(xl)))

    drawn = [e for e in elements if e.n > 0]
    for e in elements:
        if e.n == 0:
            warnings.append(f"No observations for {e.key!s}; the position is kept empty.")
    for e in drawn:
        e.stats = _box_stats(e.values)
        vmin, vmax = float(e.values.min()), float(e.values.max())
        if kind == "summary":
            e.bottom, e.top = e.stats["q1"], e.stats["q3"]
        elif kind == "box":
            e.bottom, e.top = e.stats["whisker_lo"], e.stats["whisker_hi"]
        else:                                   # a violin body spans the data
            e.bottom, e.top = vmin, vmax
        if show_points or (show_outliers and kind in ("box", "box+violin")):
            e.bottom, e.top = min(e.bottom, vmin), max(e.top, vmax)

    rng = np.random.default_rng(obs.seed)
    stats_mode = "bracket"
    legend_placed = False

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.8))

        if kind in ("violin", "box+violin"):
            _draw_violins(ax, drawn, orientation=orientation, alpha=violin_alpha, box_lw=box_lw,
                          median_lw=median_lw, show_medians=(kind == "violin"), warnings=warnings)
        if kind in ("box", "box+violin"):
            _draw_boxes(ax, drawn, orientation=orientation, box_fill=box_fill, box_lw=box_lw,
                        median_lw=median_lw, cap_frac=cap_frac, show_outliers=show_outliers,
                        inner=(kind == "box+violin"))
        if kind == "summary":
            _draw_summary(ax, drawn, orientation=orientation, box_fill=box_fill, box_lw=box_lw,
                          median_lw=median_lw)

        # Category axis: half a spacing beyond the outer categories (what a managed box plot does).
        cat_lo = min(centres) - 0.5 * group_spacing if centres else 0.5
        cat_hi = max(centres) + 0.5 * group_spacing if centres else 1.5
        if horizontal:
            ax.set_ylim(cat_lo, cat_hi)
        else:
            ax.set_xlim(cat_lo, cat_hi)

        observation_sizes: Dict[str, float] = {}
        if show_points:
            for e in drawn:
                info = draw_observations(ax, e.position, e.values, color=e.color, style=style, obs=obs,
                                         orientation=orientation, rng=rng, base_size=style.marker_size)
                observation_sizes[str(e.key)] = info["size"]
                e.top = max(e.top, info["max"])
                e.bottom = min(e.bottom, info["min"])
                if info.get("suggestion") and info["suggestion"] not in warnings:
                    warnings.append(info["suggestion"])

        labels = [str(g) for g in x_levels]
        x_label = layout.get("x_label", x)
        y_label = layout.get("y_label", y)
        if horizontal:
            ax.set_yticks(centres)
            ax.set_yticklabels(labels)
            ax.set_xlabel(y_label)
            ax.set_ylabel(x_label)
            ax.invert_yaxis()                   # first category at the top, as it reads in a table
        else:
            ax.set_xticks(centres)
            ax.set_xticklabels(labels)
            autorotate_xticklabels(ax, style, rotation=get_mapping(spec, "x_tick_rotation", "auto"))
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
        title = layout.get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)

        # Value axis: never crop a drawn mark; do not force a zero baseline.
        finite_tops = [e.top for e in drawn if np.isfinite(e.top)]
        finite_bottoms = [e.bottom for e in drawn if np.isfinite(e.bottom)]
        v_lo = min(finite_bottoms) if finite_bottoms else float("nan")
        v_hi = max(finite_tops) if finite_tops else float("nan")
        if np.isfinite(v_lo) and np.isfinite(v_hi):
            pad = _VALUE_PAD_FRACTION * ((v_hi - v_lo) or abs(v_hi) or 1.0)
            if horizontal:
                lo, hi = ax.get_xlim()
                ax.set_xlim(min(lo, v_lo - pad), max(hi, v_hi + pad))
            else:
                lo, hi = ax.get_ylim()
                ax.set_ylim(min(lo, v_lo - pad), max(hi, v_hi + pad))
        value_extent = (v_lo, v_hi) if np.isfinite(v_lo) and np.isfinite(v_hi) else None
        category_extent = (cat_lo, cat_hi)
        axis_applied = apply_axis_overrides(
            ax, spec,
            x_extent=value_extent if horizontal else category_extent,
            y_extent=category_extent if horizontal else value_extent)
        if horizontal and "y_limits" in axis_applied:
            lo, hi = sorted(axis_applied["y_limits"])
            ax.set_ylim(hi, lo)                 # keep the category axis inverted

        # Sample-size labels.
        n_label_headroom_pt = 0.0
        if show_n in ("below", "above"):
            if horizontal and show_n == "below":
                # Left of the category names: fold n into the tick label (the shared helper anchors
                # "below" at value 0, which is not the axis edge of a horizontal plot).
                counts_by_x = {g: sum(e.n for e in elements if e.x_level == g) for g in x_levels}
                ax.set_yticklabels([f"{lab}\n(n = {counts_by_x[g]})" for lab, g in zip(labels, x_levels)])
            else:
                add_n_labels(ax, [e.position for e in drawn], [e.n for e in drawn], where=show_n,
                             style=style, orientation=orientation, tops=[e.top for e in drawn])
                if show_n == "below":
                    # room between the axis line and the category names for the n row
                    ax.tick_params(axis="x", pad=3.5 + float(style.annotation_pt) * 1.25)
                else:
                    n_label_headroom_pt = float(style.annotation_pt) * 1.7

        # Legend: hue levels, or the categories when n is requested in the legend.
        location = resolve_legend_location(spec, style)
        if not str(layout.get("legend_location", "")).strip():
            location = LEGEND_LOCATIONS["outside right"]
        if hue:
            n_by_hue = {h: sum(e.n for e in elements if e.hue == h) for h in hue_levels}
            leg_labels = [f"{h} (n = {n_by_hue[h]})" if show_n == "legend" else str(h) for h in hue_levels]
            handles = [_legend_handle(style.color_for(i), box_fill, kind, violin_alpha)
                       for i in range(len(hue_levels))]
            place_legend(ax, style, title=str(hue), handles=handles, labels=leg_labels, location=location)
            legend_placed = True
        elif show_n == "legend":
            handles = [_legend_handle(e.color, box_fill, kind, violin_alpha) for e in elements]
            leg_labels = [f"{e.x_level} (n = {e.n})" for e in elements]
            place_legend(ax, style, title=None, handles=handles, labels=leg_labels, location=location)
            legend_placed = True
        if not legend_placed:
            fig.tight_layout()

        # Statistics: tops are the highest drawn mark per group (points, whiskers, violins).
        from make_my_figure_core.plots.stats_integration import run_and_annotate
        from make_my_figure_core.statistics.schemas import normalize_stats_spec

        stats_enabled = bool(normalize_stats_spec(spec.get("statistics")).get("enabled", False))
        headroom = _points_offset_in_data(ax, n_label_headroom_pt, horizontal=horizontal) \
            if (stats_enabled and n_label_headroom_pt) else 0.0
        positions_map: Dict[Any, float] = {}
        tops_map: Dict[Any, float] = {}
        for xi, xl in enumerate(x_levels):
            positions_map[str(xl)] = centres[xi]
            cluster = [e.top for e in elements if e.x_level == xl and np.isfinite(e.top)]
            tops_map[str(xl)] = (max(cluster) + headroom) if cluster else float("nan")
        if hue:
            for e in elements:
                positions_map[e.key] = e.position
                if np.isfinite(e.top):
                    tops_map[e.key] = e.top + headroom
        if stats_enabled and horizontal:
            # The bracket engine stacks brackets along y only; drawing it on a horizontal plot
            # would put brackets between the wrong marks. Run the statistics without annotating,
            # then report every comparison in a corner text panel.
            stats_mode = "corner"
            warnings.append("Significance brackets are drawn for the vertical orientation only; the "
                            "horizontal figure reports the statistics in a text panel instead.")
            stats_report = run_and_annotate(spec, work, style, PLOT_TYPE, ax=None)
            if stats_report is not None:
                _corner_panel(ax, spec, stats_report, style)
        else:
            stats_report = run_and_annotate(spec, work, style, PLOT_TYPE, ax=ax, positions=positions_map,
                                            tops=tops_map, mode=stats_mode)

    meta = base_metadata(spec, style, work, used_columns=[x, y, hue])
    meta["kind"] = kind
    meta["orientation"] = orientation
    meta["groups"] = [str(g) for g in x_levels]
    meta["group_n"] = {str(g): int(sum(e.n for e in elements if e.x_level == g)) for g in x_levels}
    meta["category_order"] = order
    if hue:
        meta["hue"] = str(hue)
        meta["hue_levels"] = [str(h) for h in hue_levels]
        meta["group_n_by_hue"] = {f"{e.x_level}|{e.hue}": e.n for e in elements}
    meta["summary"] = {
        "center": "median",
        "box": "interquartile range" if kind != "violin" else None,
        "whiskers": "1.5 x IQR (Tukey)" if kind in ("box", "box+violin") else None,
        "violin": "kernel density over the observed range" if kind in ("violin", "box+violin") else None,
    }
    # Appearance record (resolved visual options): allowed to change under a style preset, unlike
    # everything above, which comes from the data.
    meta["style"] = {
        "points": show_points, "box_width": box_width, "box_fill": box_fill,
        "box_line_width_pt": box_lw, "median_line_width_pt": median_lw, "whisker_cap_width": cap_frac,
        "show_outliers": show_outliers, "violin_alpha": violin_alpha, "group_spacing": group_spacing,
        "show_n": show_n, "observations": asdict(obs), "observation_marker_sizes": observation_sizes,
    }
    if axis_applied:
        meta["axis_overrides"] = axis_applied
    if stats_report is not None:
        meta["statistics_report"] = stats_report.to_dict()
        meta["statistics_annotation"] = stats_mode
    return RenderResult(figure=fig, metadata=meta, warnings=warnings, stats_report=stats_report)
