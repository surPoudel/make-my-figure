"""Scatter plot with optional per-/overall regression line."""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots.base import (
    register_refit,
    repel_labels,
    RenderResult,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    place_legend,
    require_columns,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "scatterplot_with_regression"


def _fit_line(ax, xs: np.ndarray, ys: np.ndarray, color: str, style: StyleProfile):
    """Ordinary least-squares fit via ``scipy.stats.linregress``.

    Draws the line and returns a dict of regression statistics (slope, intercept,
    Pearson r, R², two-sided p-value for H0: slope=0, standard errors, n), or None
    if degenerate. p-value/SEs come straight from scipy for exactness."""
    mask = ~(np.isnan(xs) | np.isnan(ys))
    xs, ys = xs[mask], ys[mask]
    n = int(xs.size)
    if n < 2 or np.ptp(xs) == 0:
        return None
    from scipy import stats as _sps
    lr = _sps.linregress(xs, ys)
    slope, intercept = float(lr.slope), float(lr.intercept)
    xline = np.linspace(xs.min(), xs.max(), 100)
    ax.plot(xline, slope * xline + intercept, color=color, lw=style.line_width_pt, zorder=4)
    r = float(lr.rvalue)
    return {"slope": slope, "intercept": intercept, "pearson_r": r,
            "r_squared": float(r * r), "p_value": float(lr.pvalue),
            "slope_stderr": float(lr.stderr),
            "intercept_stderr": float(getattr(lr, "intercept_stderr", float("nan"))),
            "n": n}


def _fmt_p(p: float) -> str:
    if not np.isfinite(p):
        return "n/a"
    return "P < 0.001" if p < 1e-3 else f"P = {p:.3g}"


def _fit_annotation_to_axes(ax, text) -> None:
    """Keep the fit-stats box inside the axes it is anchored to.

    The box is placed in axes coordinates, so a line of statistics wider than the
    axes hangs off the canvas - which is what happens on a single-column figure
    whose legend has been pushed outside, leaving the plot area narrow. Neither
    resizing nor squeezing can help: the text is centred on the axes, so a
    narrower plot area carries it further out, not nearer in.

    Breaking the statistics onto separate lines is what a person does here, and
    it costs nothing but height. If one statistic is still too wide on its own,
    the type steps down to ``ABSOLUTE_MIN_PT`` and no further; past that the
    figure is simply too narrow, and the honest result is a legible box that
    overhangs rather than an illegible one that fits.
    """
    from make_my_figure_core.styles.typography import ABSOLUTE_MIN_PT

    fig = ax.figure
    try:
        fig.canvas.draw()
    except Exception:  # noqa: BLE001
        return

    def too_wide() -> float:
        try:
            box = text.get_window_extent(fig.canvas.get_renderer())
        except Exception:  # noqa: BLE001
            return 0.0
        return box.width - ax.get_window_extent().width

    if too_wide() <= 0:
        return
    if ", " in text.get_text():
        text.set_text(text.get_text().replace(", ", "\n"))
        if too_wide() <= 0:
            return
    size = float(text.get_fontsize())
    while too_wide() > 0 and size > ABSOLUTE_MIN_PT:
        size = max(ABSOLUTE_MIN_PT, size - 0.5)
        text.set_fontsize(size)


# Corners the fit-stats box may occupy, as (x, y, ha, va) in axes coordinates.
_STATS_CORNERS = {
    "upper right": (0.97, 0.97, "right", "top"),
    "upper left": (0.03, 0.97, "left", "top"),
    "lower right": (0.97, 0.03, "right", "bottom"),
    "lower left": (0.03, 0.03, "left", "bottom"),
}


def _emptiest_corner(ax, text) -> str:
    """The corner whose box covers the least drawn content.

    A fixed corner puts the statistics on top of the data whenever the data
    happens to be there: on a two-group regression the box sat over the middle of
    the scatter, hiding the points the slopes were computed from. matplotlib
    solves the same problem for legends with ``loc="best"``; this is that idea for
    the stats box, and it is what "auto" selects.

    Scored by how many drawn points fall inside the candidate rectangle, with the
    legend counted as occupied area too, so the box does not simply move from the
    data onto the key. Ties keep the first corner tried, which makes the choice
    reproducible for a given figure.
    """
    figure = ax.figure
    try:
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        box = text.get_window_extent(renderer)
        axes_box = ax.get_window_extent(renderer)
    except Exception:  # noqa: BLE001
        return "lower right"
    if not axes_box.width or not axes_box.height:
        return "lower right"

    w = box.width / axes_box.width
    h = box.height / axes_box.height

    points = []
    for coll in ax.collections:
        try:
            offsets = coll.get_offsets()
        except Exception:  # noqa: BLE001
            continue
        for px, py in getattr(offsets, "tolist", lambda: offsets)():
            try:
                dx, dy = ax.transData.transform((px, py))
            except Exception:  # noqa: BLE001
                continue
            points.append(((dx - axes_box.x0) / axes_box.width,
                           (dy - axes_box.y0) / axes_box.height))

    blocked = []
    legend = ax.get_legend()
    if legend is not None and legend.get_visible():
        try:
            lb = legend.get_window_extent(renderer)
            blocked.append(((lb.x0 - axes_box.x0) / axes_box.width,
                            (lb.y0 - axes_box.y0) / axes_box.height,
                            (lb.x1 - axes_box.x0) / axes_box.width,
                            (lb.y1 - axes_box.y0) / axes_box.height))
        except Exception:  # noqa: BLE001
            pass

    best, best_score = "lower right", None
    for name, (cx, cy, ha, va) in _STATS_CORNERS.items():
        x0 = cx - w if ha == "right" else cx
        y0 = cy - h if va == "top" else cy
        x1, y1 = x0 + w, y0 + h
        score = sum(1 for px, py in points if x0 <= px <= x1 and y0 <= py <= y1)
        for bx0, by0, bx1, by1 in blocked:
            if not (x1 < bx0 or x0 > bx1 or y1 < by0 or y0 > by1):
                score += max(len(points), 1)     # never trade the data for the key
        if best_score is None or score < best_score:
            best, best_score = name, score
    return best


def _fit_annotation(fits: Dict[str, Any], opts: Dict[str, bool]) -> str:
    """Build the fit-stats annotation from the user's show/hide options."""
    lines: List[str] = []
    multi = len(fits) > 1 or (len(fits) == 1 and "all" not in fits)
    for name, f in fits.items():
        parts: List[str] = []
        if opts["equation"]:
            parts.append(f"y = {f['slope']:.3g}x + {f['intercept']:.3g}")
        elif opts["slope"]:
            parts.append(f"slope = {f['slope']:.3g}")
        if opts["intercept"] and not opts["equation"]:
            parts.append(f"b = {f['intercept']:.3g}")
        if opts["r"]:
            parts.append(f"r = {f['pearson_r']:.3f}")
        if opts["r2"]:
            parts.append(f"R² = {f['r_squared']:.3f}")
        if opts["p"]:
            parts.append(_fmt_p(f["p_value"]))
        if opts["n"]:
            parts.append(f"n = {f['n']}")
        if not parts:
            continue
        prefix = f"{name}: " if multi else ""
        lines.append(prefix + ", ".join(parts))
    return "\n".join(lines)


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    color_by = get_mapping(spec, "color", None)
    fit_line = bool(get_mapping(spec, "fit_line", True))
    label_col = get_mapping(spec, "label", None)
    # Which regression statistics to print on the plot — every one is user-toggleable.
    # Sensible defaults: slope + R² + p shown; r / intercept / n / equation off.
    show_fit_stats = bool(get_mapping(spec, "show_fit_stats", fit_line))
    fit_opts = {
        "slope": bool(get_mapping(spec, "show_slope", True)),
        "intercept": bool(get_mapping(spec, "show_intercept", False)),
        "r": bool(get_mapping(spec, "show_r", False)),
        "r2": bool(get_mapping(spec, "show_r2", True)),
        "p": bool(get_mapping(spec, "show_p", True)),
        "n": bool(get_mapping(spec, "show_n", False)),
        "equation": bool(get_mapping(spec, "show_equation", False)),
    }
    fit_stats_loc = str(get_mapping(spec, "fit_stats_loc", "auto")).lower()
    # When 'selected_labels' is provided (e.g. click-to-label in the desktop app),
    # only those points are annotated; otherwise every labelled point is annotated.
    selected_labels = get_mapping(spec, "selected_labels", None) or []
    _sel_set = {str(s).strip().lower() for s in selected_labels}

    require_columns(df, [x, y], context=PLOT_TYPE)
    work = df.copy()
    work[x] = coerce_numeric(work, x, context=PLOT_TYPE)
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)

    fits: Dict[str, Any] = {}
    warnings: List[str] = []

    mk = dict(s=style.marker_size, edgecolors="white",
              linewidths=style.marker_edge_width, alpha=style.marker_alpha)
    has_groups = bool(color_by and color_by in work.columns)

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.78))

        if has_groups:
            groups = list(dict.fromkeys(work[color_by].tolist()))
            for gi, g in enumerate(groups):
                sub = work[work[color_by] == g]
                col = style.color_for(gi)
                ax.scatter(sub[x], sub[y], color=col, label=str(g), zorder=3, **mk)
                if fit_line:
                    fit = _fit_line(ax, sub[x].to_numpy(float), sub[y].to_numpy(float), col, style)
                    if fit:
                        fits[str(g)] = fit
        else:
            col = style.color_for(0)
            ax.scatter(work[x], work[y], color=col, zorder=3, **mk)
            if fit_line:
                fit = _fit_line(ax, work[x].to_numpy(float), work[y].to_numpy(float), col, style)
                if fit:
                    fits["all"] = fit

        # Optional point labels (all labelled points, or only 'selected_labels').
        if label_col and label_col in work.columns:
            # Collected and placed together, not annotated one at a time with a
            # fixed offset: picking several nearby points that way stacked their
            # names on top of each other, which is what click-to-label is for.
            _pts = []
            for _, row in work.iterrows():
                txt = str(row[label_col]).strip()
                if not txt or txt.lower() == "nan":
                    continue
                if _sel_set and txt.lower() not in _sel_set:
                    continue
                _pts.append((row[x], row[y], txt))
            if _pts:
                repel_labels(ax, _pts, style, show_arrows=len(_pts) > 1)

        # Regression-stats annotation (each statistic individually toggleable).
        if fit_line and show_fit_stats and fits:
            txt = _fit_annotation(fits, fit_opts)
            if txt:
                _auto = fit_stats_loc in ("auto", "best", "")
                _loc = "lower right" if _auto else fit_stats_loc
                ax_, ay_, ha_, va_ = _STATS_CORNERS.get(_loc, _STATS_CORNERS["lower right"])
                _ann = ax.text(ax_, ay_, txt, transform=ax.transAxes, ha=ha_, va=va_,
                               fontsize=style.annotation_pt, color=style.text_color,
                               bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="0.7",
                                         lw=0.5, alpha=0.85), zorder=6)
                def _place(a=ax, t=_ann, auto=_auto):
                    # Shape first, then position. The box is only wrapped once it
                    # is wider than its axes, and the axes are not final until the
                    # layout pass has reserved room for the legend - so at draw
                    # time this box is still one 88%-wide line, and every corner
                    # scores the same. Choosing from that shape is choosing from a
                    # figure that never exists; by the time it is six lines tall
                    # the corners differ by 22 points covered.
                    _fit_annotation_to_axes(a, t)
                    if auto:
                        cx, cy, cha, cva = _STATS_CORNERS[_emptiest_corner(a, t)]
                        t.set_position((cx, cy))
                        t.set_ha(cha)
                        t.set_va(cva)
                        _fit_annotation_to_axes(a, t)

                _place()
                register_refit(ax.figure, _place)

        ax.set_xlabel(spec.get("layout", {}).get("x_label", x))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", y))
        ax.margins(0.05)
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)

        from make_my_figure_core.plots.stats_integration import run_and_annotate

        stats_report = run_and_annotate(spec, work, style, PLOT_TYPE, ax=ax,
                                        mode="corner", corner_loc="upper left")
        if has_groups:
            # Legend outside so it never sits on top of points.
            place_legend(ax, style, title=str(color_by), force_outside=True)
        else:
            fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[x, y, color_by, label_col])
    try:
        from make_my_figure_core.plots.base import (
            build_pickable_points, choose_label_column, resolve_point_labels)

        pick_col = choose_label_column(work, [label_col, "sample_id", "id", "name", "gene"])
        meta["pickable_points"] = build_pickable_points(
            work[x].to_numpy(float), work[y].to_numpy(float),
            resolve_point_labels(work, pick_col))
        meta["pick_label_key"] = "selected_labels"   # GUI appends clicked point labels here
        meta["pick_label_column"] = pick_col         # mapping['label'] set to this when labeling
    except Exception as exc:  # noqa: BLE001
        meta["pickable_points"] = []
        warnings.append(f"Click-identify data unavailable: {exc}")
    meta["fit_line"] = fit_line
    meta["regression"] = fits
    if stats_report is not None:
        meta["statistics_report"] = stats_report.to_dict()
    return RenderResult(figure=fig, metadata=meta, warnings=warnings,
                        stats_report=stats_report)
