"""Kaplan-Meier survival curves (per group), implemented without lifelines."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots.base import (
    RenderResult,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    require_columns,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "kaplan_meier_survival_curve"


def _km_estimate(times: np.ndarray, events: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Return step coordinates (t, S(t)) for the Kaplan-Meier estimator.

    ``events`` is 1 for an event and 0 for censored. Curve starts at (0, 1).
    """
    order = np.argsort(times)
    times, events = times[order], events[order]
    n = len(times)
    unique_t = np.unique(times)
    surv = 1.0
    ts, ss = [0.0], [1.0]
    at_risk = n
    for t in unique_t:
        d = int(np.sum((times == t) & (events == 1)))  # events at t
        c = int(np.sum(times == t))                     # total leaving risk set at t
        if at_risk > 0 and d > 0:
            surv *= (1.0 - d / at_risk)
        ts.append(float(t))
        ss.append(surv)
        at_risk -= c
    return np.asarray(ts), np.asarray(ss)


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    time_col = get_mapping(spec, "time", "time_months")
    event_col = get_mapping(spec, "event", "event")
    group_col = get_mapping(spec, "group", None)

    require_columns(df, [time_col, event_col], context=PLOT_TYPE)
    work = df.copy()
    work[time_col] = coerce_numeric(work, time_col, context=PLOT_TYPE)
    work[event_col] = coerce_numeric(work, event_col, context=PLOT_TYPE)

    if group_col and group_col in work.columns:
        groups: List[Any] = list(dict.fromkeys(work[group_col].tolist()))
    else:
        groups = ["all"]
        group_col = None

    warnings: List[str] = []
    summaries: Dict[str, Any] = {}

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.8))
        for gi, g in enumerate(groups):
            sub = work if group_col is None else work[work[group_col] == g]
            t = sub[time_col].to_numpy(dtype=float)
            e = sub[event_col].to_numpy(dtype=float)
            mask = ~(np.isnan(t) | np.isnan(e))
            t, e = t[mask], e[mask]
            if t.size == 0:
                warnings.append(f"Group '{g}' has no valid rows.")
                continue
            ts, ss = _km_estimate(t, e)
            col = style.color_for(gi)
            ax.step(ts, ss, where="post", color=col, lw=style.line_width_pt,
                    label=None if group_col is None else str(g))
            # Censoring ticks.
            cens_t = t[e == 0]
            if cens_t.size:
                cens_s = np.array([ss[np.searchsorted(ts, ct, side="right") - 1] for ct in cens_t])
                ax.plot(cens_t, cens_s, "|", color=col, markersize=5,
                        markeredgewidth=style.line_width_pt)
            summaries[str(g)] = {"n": int(t.size), "events": int(np.sum(e == 1))}

        ax.set_ylim(0, 1.02)
        ax.set_xlabel(spec.get("layout", {}).get("x_label", time_col))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", "Survival probability"))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        if group_col is not None:
            ax.legend(title=str(group_col), frameon=False, loc="best")
        style_axes(ax, style)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[time_col, event_col, group_col])
    meta["groups"] = summaries
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
