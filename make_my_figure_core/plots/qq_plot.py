"""Q-Q plot: observed vs expected quantiles.

Two modes:
- ``pvalue`` (default): GWAS-style -log10(observed p) vs -log10(expected uniform
  p), with the genomic inflation factor lambda reported.
- ``quantile``: sample quantiles of a numeric column vs theoretical normal
  quantiles (a distribution/normality check).

Both draw the y = x reference line.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots._v04_shared import neg_log10, pick_column
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

PLOT_TYPE = "qq_plot"

_P_ALIASES = ["P.Value", "pvalue", "p_value", "pval", "p", "adj.P.Val", "padj", "FDR"]


def _lambda_gc(pvals: np.ndarray) -> float:
    """Genomic inflation factor from p-values (median chi-square, 1 df)."""
    from scipy.stats import chi2

    p = pvals[np.isfinite(pvals) & (pvals > 0) & (pvals <= 1)]
    if p.size == 0:
        return float("nan")
    obs = chi2.isf(np.median(p), 1)
    return float(obs / chi2.ppf(0.5, 1))


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    mode = str(get_mapping(spec, "mode", "pvalue")).lower()
    if mode not in ("pvalue", "quantile"):
        mode = "pvalue"
    warnings: List[str] = []
    meta_extra: Dict[str, Any] = {}

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.92))

        if mode == "pvalue":
            p = get_mapping(spec, "p", None) or pick_column(df, _P_ALIASES)
            if not p:
                raise RenderError(
                    f"{PLOT_TYPE}: no p-value column found; map 'p'. Columns: {list(df.columns)}")
            require_columns(df, [p], context=PLOT_TYPE)
            work = df.copy()
            pv = coerce_numeric(work, p, context=PLOT_TYPE).to_numpy(float)
            pv = pv[np.isfinite(pv)]
            n = pv.size
            if n < 2:
                raise RenderError(f"{PLOT_TYPE}: need >= 2 valid p-values (got {n}).")
            obs = np.sort(neg_log10(pv))[::-1]           # largest -log10 first
            expected_p = (np.arange(1, n + 1) - 0.5) / n
            exp = -np.log10(expected_p)                  # also largest first
            ax.scatter(exp, obs, s=max(8.0, style.marker_size * 0.4), color=style.color_for(0),
                       edgecolors="none", alpha=style.marker_alpha, zorder=3)
            lam = _lambda_gc(pv)
            meta_extra["lambda_gc"] = lam
            meta_extra["n_points"] = int(n)
            if np.isfinite(lam):
                ax.annotate(f"$\\lambda_{{GC}}$ = {lam:.3f}", xy=(0.04, 0.92),
                            xycoords="axes fraction", fontsize=style.annotation_pt)
            x_label = "Expected  -log10(p)"
            y_label = "Observed  -log10(p)"
            lim = max(float(exp.max()), float(obs.max())) * 1.05
            lo = 0.0
            used = [p]
        else:
            obs_col = get_mapping(spec, "observed", None) or get_mapping(spec, "x", None)
            if not obs_col:
                # fall back to first numeric column
                for c in df.columns:
                    if coerce_numeric_safe(df, c):
                        obs_col = c
                        break
            if not obs_col:
                raise RenderError(f"{PLOT_TYPE}: map 'observed' to a numeric column.")
            require_columns(df, [obs_col], context=PLOT_TYPE)
            work = df.copy()
            vals = coerce_numeric(work, obs_col, context=PLOT_TYPE).to_numpy(float)
            vals = np.sort(vals[np.isfinite(vals)])
            n = vals.size
            if n < 2:
                raise RenderError(f"{PLOT_TYPE}: need >= 2 valid values (got {n}).")
            from scipy.stats import norm

            probs = (np.arange(1, n + 1) - 0.5) / n
            # Standardize theoretical quantiles to the data's scale for a fair line.
            theo = norm.ppf(probs)
            mu, sd = float(np.mean(vals)), float(np.std(vals) or 1.0)
            theo_scaled = mu + sd * theo
            ax.scatter(theo_scaled, vals, s=max(8.0, style.marker_size * 0.4),
                       color=style.color_for(0), edgecolors="white",
                       linewidths=style.marker_edge_width, alpha=style.marker_alpha, zorder=3)
            meta_extra["n_points"] = int(n)
            x_label = "Theoretical quantiles (normal)"
            y_label = f"Observed quantiles ({obs_col})"
            lim = max(float(theo_scaled.max()), float(vals.max()))
            lo = min(float(theo_scaled.min()), float(vals.min()))
            used = [obs_col]

        # y = x reference line.
        ax.plot([lo, lim], [lo, lim], color=style.text_color, ls="--",
                lw=style.line_width_pt, zorder=2, label="y = x")
        ax.set_xlabel(spec.get("layout", {}).get("x_label", x_label))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", y_label))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)
        fig.tight_layout()

    meta = base_metadata(spec, style, df, used_columns=used)
    meta["mode"] = mode
    meta.update(meta_extra)
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)


def coerce_numeric_safe(df, col) -> bool:
    import pandas as pd

    return pd.to_numeric(df[col], errors="coerce").notna().any()
