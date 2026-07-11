"""Calibration (reliability) plot for clinical risk / prediction models.

Two input modes: (a) true labels (0/1) + predicted probabilities — predictions
are grouped into equal-width bins and the observed event rate is computed per
bin here; or (b) a precomputed table of predicted vs observed probabilities.
A diagonal reference marks perfect calibration. When labels + probabilities are
provided, the Brier score is reported in metadata (it is NOT drawn on the plot,
to avoid overstating model diagnostics).
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots.base import (
    RenderError,
    RenderResult,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    require_columns,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "calibration_plot"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    label_col = get_mapping(spec, "label", None)
    prob_col = get_mapping(spec, "prob", None)
    pred_col = get_mapping(spec, "predicted", None)
    obs_col = get_mapping(spec, "observed", None)
    try:
        n_bins = int(get_mapping(spec, "n_bins", 10))
    except (TypeError, ValueError):
        n_bins = 10
    n_bins = max(3, min(n_bins, 20))

    warnings: List[str] = []
    brier = None
    used: List[str] = []
    work = df.copy()

    from_labels = bool(label_col and prob_col and label_col in work.columns and prob_col in work.columns)
    precomputed = bool(pred_col and obs_col and pred_col in work.columns and obs_col in work.columns)
    if not from_labels and not precomputed:
        require_columns(work, [label_col or "label", prob_col or "prob"], context=PLOT_TYPE)

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=1.0))
        # Perfect-calibration reference.
        ax.plot([0, 1], [0, 1], ls="--", color="0.6", lw=style.spine_width_pt,
                label="perfect calibration")

        if from_labels:
            work[label_col] = coerce_numeric(work, label_col, context=PLOT_TYPE)
            work[prob_col] = coerce_numeric(work, prob_col, context=PLOT_TYPE)
            sub = work[[label_col, prob_col]].dropna()
            y = (sub[label_col].to_numpy() == 1).astype(float)
            p = sub[prob_col].to_numpy(dtype=float)
            if p.size == 0:
                raise RenderError(f"{PLOT_TYPE}: no valid label/probability pairs.")
            brier = float(np.mean((p - y) ** 2))
            edges = np.linspace(0.0, 1.0, n_bins + 1)
            binidx = np.clip(np.digitize(p, edges[1:-1]), 0, n_bins - 1)
            mean_pred, obs_rate, counts = [], [], []
            for b in range(n_bins):
                sel = binidx == b
                if sel.any():
                    mean_pred.append(float(np.mean(p[sel])))
                    obs_rate.append(float(np.mean(y[sel])))
                    counts.append(int(sel.sum()))
            mean_pred = np.array(mean_pred); obs_rate = np.array(obs_rate)
            counts = np.array(counts, dtype=float)
            sizes = style.marker_size * (0.6 + 0.9 * counts / counts.max()) if counts.size else style.marker_size
            ax.plot(mean_pred, obs_rate, color=style.color_for(0), lw=style.line_width_pt, zorder=2)
            ax.scatter(mean_pred, obs_rate, s=sizes, color=style.color_for(0), edgecolors="white",
                       linewidths=style.marker_edge_width, zorder=3,
                       label=f"model (Brier={brier:.3f})")
            used = [label_col, prob_col]
            meta_bins = int(len(mean_pred))
        else:
            work[pred_col] = coerce_numeric(work, pred_col, context=PLOT_TYPE)
            work[obs_col] = coerce_numeric(work, obs_col, context=PLOT_TYPE)
            sub = work[[pred_col, obs_col]].dropna().sort_values(pred_col)
            mp = sub[pred_col].to_numpy(float); ob = sub[obs_col].to_numpy(float)
            ax.plot(mp, ob, color=style.color_for(0), lw=style.line_width_pt, zorder=2)
            ax.scatter(mp, ob, s=style.marker_size, color=style.color_for(0), edgecolors="white",
                       linewidths=style.marker_edge_width, zorder=3, label="observed")
            used = [pred_col, obs_col]
            meta_bins = int(len(mp))

        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.02, 1.02)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel(spec.get("layout", {}).get("x_label", "Predicted probability"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", "Observed probability"))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        ax.legend(frameon=False, loc="upper left", fontsize=max(7.0, style.legend_pt - 1))
        style_axes(ax, style)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=used)
    meta["n_bins"] = meta_bins
    if brier is not None:
        meta["brier"] = round(brier, 4)
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
