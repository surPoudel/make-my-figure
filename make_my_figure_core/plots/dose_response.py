"""Dose-response curve with an optional 4-parameter logistic (4PL) fit.

For drug screens / assay readouts. The x-axis (concentration) is log-scaled by
default. When fitting is enabled the renderer fits a 4PL model per group and
reports EC50/IC50; if the fit does not converge it is skipped (never faked) and
a TODO is recorded so the user knows the curve is observed points only.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots._v04_shared import ordered_unique
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

PLOT_TYPE = "dose_response_curve"


def _four_pl(x, bottom, top, ec50, hill):
    """4-parameter logistic: bottom + (top-bottom)/(1+(x/ec50)**hill)."""
    return bottom + (top - bottom) / (1.0 + (x / ec50) ** hill)


def _fit_group(x: np.ndarray, y: np.ndarray):
    """Return a dict of 4PL params or a reason string if the fit is skipped."""
    from scipy.optimize import curve_fit

    if x.size < 4:
        return "insufficient points for a 4PL fit (need >= 4)"
    try:
        p0 = [float(np.min(y)), float(np.max(y)), float(np.median(x)), 1.0]
        bounds = ([-np.inf, -np.inf, x.min() * 1e-3, 0.1],
                  [np.inf, np.inf, x.max() * 1e3, 10.0])
        popt, _ = curve_fit(_four_pl, x, y, p0=p0, bounds=bounds, maxfev=10000)
        bottom, top, ec50, hill = (float(v) for v in popt)
        if not np.isfinite(ec50) or ec50 <= 0:
            return "fit returned a non-physical EC50"
        return {"bottom": bottom, "top": top, "ec50": ec50, "hill": hill}
    except (RuntimeError, ValueError) as exc:
        return f"fit did not converge ({exc})"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    dose = get_mapping(spec, "dose", required=True, context=PLOT_TYPE)
    response = get_mapping(spec, "response", required=True, context=PLOT_TYPE)
    group_col = get_mapping(spec, "group", None)
    do_fit = bool(get_mapping(spec, "fit", True))

    require_columns(df, [dose, response], context=PLOT_TYPE)
    work = df.copy()
    work[dose] = coerce_numeric(work, dose, context=PLOT_TYPE)
    work[response] = coerce_numeric(work, response, context=PLOT_TYPE)

    warnings: List[str] = []
    n_nonpos = int((work[dose] <= 0).sum())
    if n_nonpos:
        warnings.append(f"Dropped {n_nonpos} row(s) with non-positive dose (log x-axis).")
    work = work[work[dose] > 0]
    if work.empty:
        from make_my_figure_core.plots.base import RenderError

        raise RenderError(f"{PLOT_TYPE}: no rows with a positive dose to plot on a log axis.")

    has_group = bool(group_col and group_col in work.columns)
    groups = ordered_unique(work[group_col].tolist()) if has_group else ["all"]
    fits: Dict[str, Any] = {}
    fit_skipped: Dict[str, str] = {}

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.72))
        ax.set_xscale("log")
        for gi, g in enumerate(groups):
            sub = work if not has_group else work[work[group_col] == g]
            x = sub[dose].to_numpy(float)
            y = sub[response].to_numpy(float)
            m = np.isfinite(x) & np.isfinite(y)
            x, y = x[m], y[m]
            color = style.color_for(gi)
            ax.scatter(x, y, color=color, s=style.marker_size, edgecolors="white",
                       linewidths=style.marker_edge_width, alpha=style.marker_alpha,
                       zorder=3, label=str(g) if has_group else None)
            if do_fit:
                res = _fit_group(x, y)
                if isinstance(res, dict):
                    xline = np.logspace(np.log10(x.min()), np.log10(x.max()), 200)
                    ax.plot(xline, _four_pl(xline, res["bottom"], res["top"],
                                            res["ec50"], res["hill"]),
                            color=color, lw=style.line_width_pt, zorder=2)
                    fits[str(g)] = res
                else:
                    fit_skipped[str(g)] = res
                    warnings.append(f"{g}: {res}")

        ax.set_xlabel(spec.get("layout", {}).get("x_label", "Concentration (log scale)"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", "Response"))
        ax.margins(y=0.08)
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)
        if has_group:
            place_legend(ax, style, title=str(group_col), force_outside=True)
        else:
            fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[dose, response, group_col])
    meta["fit_enabled"] = do_fit
    meta["fits"] = fits  # per-group {bottom, top, ec50/ic50, hill}
    if fit_skipped:
        meta["fit_skipped"] = fit_skipped
        meta["todo"] = ("Some groups could not be fit with a 4PL model; those show observed "
                        "points only. Provide more dose levels spanning the response, or supply "
                        "pre-fitted values. IC50/EC50 is reported only for converged fits.")
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
