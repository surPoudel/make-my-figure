"""Raincloud plot: half-violin (cloud) + box summary + raw points (rain).

Combines three complementary views of a distribution per group — a density
"cloud" (half-violin), a compact box summary, and the raw points —
so the reader sees the shape, the summary, and the individual observations at
once. Reuses matplotlib's violinplot/boxplot; the rain is drawn by the shared
observation engine (``plots/observations.py``; ``point_*`` options). Statistics
run through the shared bracket engine when enabled.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots._v04_shared import ordered_unique
from make_my_figure_core.plots.base import (
    autorotate_xticklabels,
    RenderResult,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    require_columns,
    style_axes,
)
from make_my_figure_core.plots.observations import ObservationStyle, draw_observations
from make_my_figure_core.plots.stats_integration import run_and_annotate
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "raincloud_plot"

_RAIN_OFFSET = -0.28          # the rain sits left of the group position
# Legacy geometry: uniform jitter in [-0.07, 0.07] -> total spread 0.14 of the category spacing.
_DEFAULT_RAIN_WIDTH = 0.14


def _observation_style(spec: Dict[str, Any], style: StyleProfile) -> ObservationStyle:
    """``point_*`` options with this renderer's historical defaults where the spec is silent."""
    mapping = spec.get("mapping", {}) or {}
    obs = ObservationStyle.from_mapping(mapping)
    if mapping.get("point_arrangement") in (None, ""):
        obs.arrangement = "jitter"
    if mapping.get("point_jitter_width") in (None, ""):
        obs.jitter_width = _DEFAULT_RAIN_WIDTH
    if obs.size is None:
        obs.size = max(8.0, float(style.marker_size) * 0.5)
    if obs.alpha is None:
        obs.alpha = float(style.marker_alpha)
    if mapping.get("point_edge_width") in (None, ""):
        obs.edge_width = float(style.marker_edge_width) * 0.7
    return obs


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)

    require_columns(df, [x, y], context=PLOT_TYPE)
    work = df.copy()
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)

    groups = ordered_unique(work[x].tolist())
    warnings: List[str] = []
    if len(groups) > 6:
        warnings.append("Raincloud reads best with <=6 groups; consider faceting for more.")
    obs = _observation_style(spec, style)

    per_group = []
    for g in groups:
        vals = work[work[x] == g][y].to_numpy(float)
        per_group.append(vals[np.isfinite(vals)])
    finite = [v for v in per_group if v.size]
    lo = min(float(v.min()) for v in finite) if finite else np.nan
    hi = max(float(v.max()) for v in finite) if finite else np.nan

    tops: Dict[str, float] = {}
    group_n: Dict[str, int] = {}
    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.72))
        # Fix the limits first (the beeswarm arrangement measures collisions in pixels). The
        # violin's density is evaluated over the data range and the box never exceeds it, so the
        # points define the extent; 8 % padding matches the former ax.margins(y=0.08).
        ax.set_xlim(-0.6, len(groups) - 0.15)
        if np.isfinite(lo) and np.isfinite(hi):
            pad = 0.08 * ((hi - lo) or (abs(hi) or 1.0))
            ax.set_ylim(lo - pad, hi + pad)
        for gi, (g, vals) in enumerate(zip(groups, per_group)):
            if vals.size == 0:
                continue
            col = style.color_for(gi)
            # (a) Cloud: half-violin shifted to the right of the group position.
            if vals.size > 1 and np.ptp(vals) > 0:
                vp = ax.violinplot([vals], positions=[gi + 0.05], widths=0.9,
                                   showextrema=False, showmeans=False, showmedians=False)
                for body in vp["bodies"]:
                    # Clip to the right half only (the "cloud").
                    verts = body.get_paths()[0].vertices
                    verts[:, 0] = np.clip(verts[:, 0], gi + 0.05, None)
                    body.set_facecolor(col)
                    body.set_edgecolor(col)
                    body.set_alpha(0.35)
            # (b) Box summary just left of center.
            bp = ax.boxplot([vals], positions=[gi - 0.12], widths=0.14, patch_artist=True,
                            showfliers=False, medianprops=dict(color=style.text_color,
                                                               linewidth=style.line_width_pt))
            for patch in bp["boxes"]:
                patch.set_facecolor("white")
                patch.set_edgecolor(col)
                patch.set_linewidth(style.spine_width_pt)
            for element in ("whiskers", "caps"):
                for artist in bp[element]:
                    artist.set_color(col)
                    artist.set_linewidth(style.spine_width_pt)
            # (c) Rain: raw points to the left, via the shared observation engine.
            info = draw_observations(ax, gi + _RAIN_OFFSET, vals, color=col, style=style, obs=obs,
                                     rng=np.random.default_rng(gi + 1))
            if info.get("suggestion") and info["suggestion"] not in warnings:
                warnings.append(info["suggestion"])
            group_n[str(g)] = int(vals.size)
            # Highest drawn element: the points (violin and box stay within the data range).
            tops[str(g)] = float(info["max"])

        ax.set_xticks(range(len(groups)))
        ax.set_xticklabels([str(g) for g in groups])
        autorotate_xticklabels(ax, style, rotation=get_mapping(spec, "x_tick_rotation", "auto"))
        ax.set_xlabel(spec.get("layout", {}).get("x_label", str(x)))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", str(y)))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)
        fig.tight_layout()

        # Statistics: disabled unless spec["statistics"]["enabled"]; brackets clear every spanned group.
        positions_map = {str(g): float(gi) for gi, g in enumerate(groups)}
        stats_report = run_and_annotate(spec, work, style, PLOT_TYPE, ax=ax,
                                        positions=positions_map, tops=tops, mode="bracket")

    meta = base_metadata(spec, style, work, used_columns=[x, y])
    meta["n_groups"] = len(groups)
    meta["groups"] = [str(g) for g in groups]
    meta["group_n"] = group_n
    meta["components"] = ["half_violin", "box", "raw_points"]
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
