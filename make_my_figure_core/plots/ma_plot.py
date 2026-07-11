"""MA plot for differential expression (RNA-seq / proteomics).

x-axis: average abundance/expression (A). y-axis: log fold change (M). Points
are colored by significance using a p-value/FDR column read **verbatim** — the
app never recomputes statistics. Optionally labels the top features by absolute
fold change among the significant hits.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots._v04_shared import pick_column
from make_my_figure_core.plots.base import (
    RenderError,
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

PLOT_TYPE = "ma_plot"

_X_ALIASES = ["AveExpr", "baseMean", "logCPM", "mean_expression", "abundance", "avgexpr",
              "average_expression"]
_Y_ALIASES = ["logFC", "log2FoldChange", "log2FC", "LFC", "log2_fold_change"]
_P_ALIASES = ["adj.P.Val", "padj", "FDR", "qvalue", "adjusted_p_value", "P.Value", "pvalue", "p_value"]
_LABEL_ALIASES = ["geneSymbol", "symbol", "gene", "gene_id", "gene_symbol", "feature"]


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", None) or pick_column(df, _X_ALIASES)
    y = get_mapping(spec, "y", None) or pick_column(df, _Y_ALIASES)
    p = get_mapping(spec, "p", None) or pick_column(df, _P_ALIASES)
    label_col = get_mapping(spec, "label", None) or pick_column(df, _LABEL_ALIASES)
    p_cutoff = float(get_mapping(spec, "p_cutoff", 0.05))
    label_top_n = int(get_mapping(spec, "label_top_n", 8))

    if not x or not y:
        raise RenderError(
            f"{PLOT_TYPE}: could not find average-expression and log-fold-change columns. "
            f"Map 'x' (e.g. AveExpr/baseMean/logCPM) and 'y' (e.g. logFC/log2FoldChange). "
            f"Available columns: {list(df.columns)}")
    require_columns(df, [x, y], context=PLOT_TYPE)

    work = df.copy()
    work[x] = coerce_numeric(work, x, context=PLOT_TYPE)
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)
    warnings: List[str] = []

    xs = work[x].to_numpy(float)
    ys = work[y].to_numpy(float)
    if p and p in work.columns:
        pv = coerce_numeric(work, p, context=PLOT_TYPE).to_numpy(float)
    else:
        pv = np.full(len(work), np.nan)
        warnings.append("No p-value/FDR column found; all points shown as non-significant.")

    sig = np.isfinite(pv) & (pv <= p_cutoff)
    up = sig & (ys > 0)
    down = sig & (ys < 0)
    ns = ~sig

    mk = dict(s=style.marker_size, edgecolors="white",
              linewidths=style.marker_edge_width, alpha=style.marker_alpha)
    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.72))
        ax.axhline(0.0, color=style.text_color, lw=style.spine_width_pt, zorder=1)
        if ns.any():
            ax.scatter(xs[ns], ys[ns], color="#B8B8B8", label="Not sig.", zorder=2, **mk)
        if up.any():
            ax.scatter(xs[up], ys[up], color=style.color_for(1), label="Up", zorder=3, **mk)
        if down.any():
            ax.scatter(xs[down], ys[down], color=style.color_for(0), label="Down", zorder=3, **mk)

        # Label the strongest significant hits by |logFC|, dropping labels that
        # would collide so text stays readable.
        if label_col and label_col in work.columns and label_top_n > 0 and sig.any():
            from make_my_figure_core.plots.base import dedupe_labels_by_distance

            sig_idx = np.where(sig)[0]
            order = sig_idx[np.argsort(-np.abs(ys[sig_idx]))][:label_top_n]
            xr = float(np.nanmax(xs) - np.nanmin(xs)) or 1.0
            yr = float(np.nanmax(ys) - np.nanmin(ys)) or 1.0
            candidates = []
            for i in order:
                txt = str(work[label_col].iloc[i]).strip()
                if txt and txt.lower() != "nan":
                    candidates.append((float(xs[i]), float(ys[i]), txt))
            for x_i, y_i, txt in dedupe_labels_by_distance(
                    candidates, min_dx=0.05 * xr, min_dy=0.07 * yr):
                ax.annotate(txt, (x_i, y_i), fontsize=style.annotation_pt,
                            xytext=(3, 3), textcoords="offset points")

        ax.set_xlabel(spec.get("layout", {}).get("x_label", "Average expression"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", "log2 fold change"))
        ax.margins(0.05)
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)
        place_legend(ax, style, title="Significance", force_outside=True)

    meta = base_metadata(spec, style, work, used_columns=[x, y, p, label_col])
    meta["n_up"] = int(up.sum())
    meta["n_down"] = int(down.sum())
    meta["n_ns"] = int(ns.sum())
    meta["p_cutoff"] = p_cutoff
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
