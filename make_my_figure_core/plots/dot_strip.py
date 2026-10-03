"""Dot / strip plot: individual observations per group with optional summary.

A publication-friendly alternative to bar plots — it shows every data point
rather than hiding the distribution behind a bar. Points are drawn by the shared
observation engine (``plots/observations.py``: jitter, centred column or
beeswarm; marker, fill, edge and opacity are ``point_*`` options) and an
optional summary overlay (mean/median with SD/SEM/CI) is drawn on top.
Statistics (``spec["statistics"]``) run through the shared bracket engine when
enabled; brackets clear the highest drawn element of every group they span.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots._v04_shared import ordered_unique, summary_stat
from make_my_figure_core.plots.base import (
    autorotate_xticklabels,
    RenderResult,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    apply_publication_layout,
    place_legend,
    require_columns,
    style_axes,
)
from make_my_figure_core.plots.observations import ObservationStyle, draw_observations
from make_my_figure_core.plots.stats_integration import run_and_annotate
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "dot_strip_plot"

_SUMMARY_CHOICES = ("none", "mean", "median", "ci", "sd", "sem")
# Legacy geometry: uniform jitter in [-0.18, 0.18] -> total spread 0.36 of the category spacing.
_DEFAULT_JITTER_WIDTH = 0.36


def _observation_style(spec: Dict[str, Any], style: StyleProfile, *, do_jitter: bool) -> ObservationStyle:
    """``point_*`` options with this renderer's historical defaults where the spec is silent.

    Unset size / opacity / edge width follow the style profile's marker tokens (as the renderer
    always did) rather than the engine's adaptive table, so existing figures keep their look;
    a preset that sets ``point_size`` etc. is honoured exactly.
    """
    mapping = spec.get("mapping", {}) or {}
    obs = ObservationStyle.from_mapping(mapping)
    if mapping.get("point_arrangement") in (None, ""):
        obs.arrangement = "jitter"
    if not do_jitter:
        obs.arrangement = "centered"
    if mapping.get("point_jitter_width") in (None, ""):
        obs.jitter_width = _DEFAULT_JITTER_WIDTH
    if obs.size is None:
        obs.size = float(style.marker_size)
    if obs.alpha is None:
        obs.alpha = float(style.marker_alpha)
    if mapping.get("point_edge_width") in (None, ""):
        obs.edge_width = float(style.marker_edge_width)
    return obs


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    color_by = get_mapping(spec, "color", None)
    do_jitter = bool(get_mapping(spec, "jitter", True))
    summary = str(get_mapping(spec, "summary", "mean")).lower()
    if summary not in _SUMMARY_CHOICES:
        summary = "mean"

    require_columns(df, [x, y], context=PLOT_TYPE)
    work = df.copy()
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)

    groups = ordered_unique(work[x].tolist())
    has_color = bool(color_by and color_by in work.columns and color_by != x)
    color_levels = ordered_unique(work[color_by].tolist()) if has_color else []
    warnings: List[str] = []
    obs = _observation_style(spec, style, do_jitter=do_jitter)

    # Per-group values and the extent the axes must show (points and summary overlays), so the
    # limits can be fixed before the points are drawn - the beeswarm arrangement measures marker
    # collisions in pixels and needs the final data transform.
    per_group: Dict[Any, np.ndarray] = {}
    per_group_labels: Dict[Any, np.ndarray] = {}
    overlays: Dict[Any, tuple] = {}
    lo, hi = np.inf, -np.inf
    for g in groups:
        sub = work[work[x] == g]
        yy = sub[y].to_numpy(float)
        mask = np.isfinite(yy)
        yy = yy[mask]
        if yy.size == 0:
            continue
        per_group[g] = yy
        if has_color:
            per_group_labels[g] = sub[color_by].astype(str).to_numpy()[mask]
        lo, hi = min(lo, float(yy.min())), max(hi, float(yy.max()))
        if summary != "none":
            center, err = summary_stat(yy, summary)
            if np.isfinite(center):
                overlays[g] = (center, err)
                lo, hi = min(lo, center - err), max(hi, center + err)

    tops: Dict[str, float] = {}
    group_n: Dict[str, int] = {}
    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.72))
        ax.set_xlim(-0.6, len(groups) - 0.4)
        if np.isfinite(lo) and np.isfinite(hi):
            pad = 0.08 * ((hi - lo) or (abs(hi) or 1.0))   # matches the former ax.margins(y=0.08)
            ax.set_ylim(lo - pad, hi + pad)
        legend_seen = set()
        for gi, g in enumerate(groups):
            yy = per_group.get(g)
            if yy is None:
                continue
            rng = np.random.default_rng(gi + 1)
            top = -np.inf
            info: Dict[str, Any] = {}
            if has_color:
                clabels = per_group_labels[g]
                for ci, lvl in enumerate(color_levels):
                    sel = clabels == str(lvl)
                    if not sel.any():
                        continue
                    info = draw_observations(ax, gi, yy[sel], color=style.color_for(ci), style=style,
                                             obs=obs, rng=rng)
                    if str(lvl) not in legend_seen and ax.collections:
                        ax.collections[-1].set_label(str(lvl))
                        legend_seen.add(str(lvl))
                    top = max(top, info["max"])
            else:
                info = draw_observations(ax, gi, yy, color=style.color_for(0), style=style, obs=obs, rng=rng)
                top = info["max"]
            if info.get("suggestion") and info["suggestion"] not in warnings:
                warnings.append(info["suggestion"])
            group_n[str(g)] = int(yy.size)
            # Summary overlay (drawn in a dark neutral so it reads over points).
            if g in overlays:
                center, err = overlays[g]
                ax.plot([gi - 0.28, gi + 0.28], [center, center], color=style.text_color,
                        lw=style.line_width_pt * 1.3, zorder=4, solid_capstyle="round")
                if err > 0:
                    ax.errorbar(gi, center, yerr=err, color=style.text_color,
                                lw=style.errorbar_line_width, capsize=style.errorbar_capsize,
                                zorder=4)
                    top = max(top, center + err)
            tops[str(g)] = float(top)

        ax.set_xticks(range(len(groups)))
        ax.set_xticklabels([str(g) for g in groups])
        autorotate_xticklabels(ax, style, rotation=get_mapping(spec, "x_tick_rotation", "auto"))
        ax.set_xlabel(spec.get("layout", {}).get("x_label", str(x)))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", str(y)))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)
        if has_color:
            place_legend(ax, style, title=str(color_by), force_outside=True)
        else:
            fig.tight_layout()

        # Statistics: disabled unless spec["statistics"]["enabled"]; brackets clear every spanned group.
        positions_map = {str(g): float(gi) for gi, g in enumerate(groups)}
        stats_report = run_and_annotate(spec, work, style, PLOT_TYPE, ax=ax,
                                        positions=positions_map, tops=tops, mode="bracket")
        apply_publication_layout(fig, ax, spec, style)

    meta = base_metadata(spec, style, work, used_columns=[x, y, color_by])
    meta["n_groups"] = len(groups)
    meta["groups"] = [str(g) for g in groups]
    meta["group_n"] = group_n
    meta["summary"] = summary
    meta["jitter"] = do_jitter
    # How the observations look is appearance (a style preset may change it), so it is recorded
    # under the metadata "style" block, apart from the numbers (groups, n, summaries, statistics).
    style_block = meta.get("style")
    if not isinstance(style_block, dict):
        style_block = meta["style"] = {}
    style_block["observations"] = {"arrangement": obs.arrangement, "jitter_width": obs.jitter_width,
                             "marker": obs.marker, "fill": obs.fill, "edge": obs.edge,
                             "size": obs.size, "alpha": obs.alpha}
    if stats_report is not None:
        meta["statistics_report"] = stats_report.to_dict()
    return RenderResult(figure=fig, metadata=meta, warnings=warnings, stats_report=stats_report)
