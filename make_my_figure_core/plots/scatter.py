"""Scatter plot with optional per-/overall regression line."""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots.base import (
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
    fit_stats_loc = str(get_mapping(spec, "fit_stats_loc", "lower right")).lower()
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
            for _, row in work.iterrows():
                txt = str(row[label_col]).strip()
                if not txt or txt.lower() == "nan":
                    continue
                if _sel_set and txt.lower() not in _sel_set:
                    continue
                ax.annotate(txt, (row[x], row[y]), fontsize=style.annotation_pt,
                            xytext=(3, 3), textcoords="offset points")

        # Regression-stats annotation (each statistic individually toggleable).
        if fit_line and show_fit_stats and fits:
            txt = _fit_annotation(fits, fit_opts)
            if txt:
                loc_map = {
                    "upper right": (0.97, 0.97, "right", "top"),
                    "upper left": (0.03, 0.97, "left", "top"),
                    "lower right": (0.97, 0.03, "right", "bottom"),
                    "lower left": (0.03, 0.03, "left", "bottom"),
                }
                ax_, ay_, ha_, va_ = loc_map.get(fit_stats_loc, loc_map["lower right"])
                ax.text(ax_, ay_, txt, transform=ax.transAxes, ha=ha_, va=va_,
                        fontsize=max(8.0, style.annotation_pt), color=style.text_color,
                        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="0.7",
                                  lw=0.5, alpha=0.85), zorder=6)

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
