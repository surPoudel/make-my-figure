"""Bridge between renderers and the statistics engine.

A renderer computes the geometry it already knows (per-category x positions and
data tops) and calls :func:`run_and_annotate`. This helper runs the configured
statistics once, draws the appropriate annotations (brackets for categorical
comparisons, a corner panel for correlation, a text line for survival), and
returns the :class:`StatsReport` so the registry can attach it to metadata and
write the StatsSpec sidecar.

Keeping this in one place means brackets, p-value formatting, and the
"every label is backed by a stored result" guarantee are identical across every
plot type.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from make_my_figure_core.plots import stats_overlay
from make_my_figure_core.statistics.annotations import (
    build_pairwise_annotations,
    stat_text_panel,
)
from make_my_figure_core.statistics.runner import run_statistics
from make_my_figure_core.statistics.schemas import normalize_stats_spec


def run_and_annotate(
    spec: Dict[str, Any],
    df,
    style,
    plot_type: str,
    *,
    ax=None,
    positions: Optional[Dict[Any, float]] = None,
    tops: Optional[Dict[Any, float]] = None,
    mode: str = "bracket",
    corner_loc: str = "upper left",
):
    """Run stats for ``spec`` and (optionally) annotate ``ax``.

    ``positions``/``tops`` are keyed by ``str(category)`` for simple grouped
    plots, or by ``(str(x_level), str(group))`` for within-x grouped plots.
    Returns the :class:`StatsReport` (or ``None`` when statistics are disabled).
    """
    raw = spec.get("statistics")
    stats_spec = normalize_stats_spec(raw)
    if not stats_spec.get("enabled", False):
        return None

    mapping = spec.get("mapping", {}) or {}
    report = run_statistics(df, stats_spec, plot_type=plot_type, mapping=mapping)

    if ax is None or not stats_spec.get("annotate", True):
        return report

    ann_cfg = stats_spec.get("annotation", {}) or {}
    if mode == "bracket" and positions:
        items = build_pairwise_annotations(report.results, ann_cfg)

        def pos_lookup(item) -> Optional[Tuple[float, float]]:
            if item.within_x:
                ka = (str(item.x_level), str(item.group_a))
                kb = (str(item.x_level), str(item.group_b))
            else:
                ka, kb = str(item.group_a), str(item.group_b)
            if ka in positions and kb in positions:
                return positions[ka], positions[kb]
            return None

        def top_lookup(item) -> Optional[float]:
            if not tops:
                return None
            if item.within_x:
                ka = (str(item.x_level), str(item.group_a))
                kb = (str(item.x_level), str(item.group_b))
            else:
                ka, kb = str(item.group_a), str(item.group_b)
            vals = [tops[k] for k in (ka, kb) if k in tops]
            return max(vals) if vals else None

        info = stats_overlay.annotate_pairwise(
            ax, items, pos_lookup, style=style, cfg=ann_cfg, top_lookup=top_lookup)
        report.config = dict(report.config or {})
        report.config["_annotation_info"] = info
        # Omnibus (ANOVA / Kruskal) and other non-pairwise results have no bracket
        # between two bars, so surface their p-values as a corner panel — otherwise
        # a user who selects (or auto-gets) an ANOVA sees nothing on the figure.
        panel_lines = stat_text_panel(
            [r for r in report.results if r.comparison_type != "two_group"],
            digits=int(ann_cfg.get("digits", 3)))
        if panel_lines:
            # Reserve headroom so the panel sits above the data rather than over it.
            y0, y1 = ax.get_ylim()
            ax.set_ylim(y0, y1 + (0.085 * len(panel_lines) + 0.04) * (y1 - y0))
            stats_overlay.annotate_corner(ax, panel_lines, style=style, loc="upper left")
    elif mode == "corner":
        lines = stat_text_panel(report.results, digits=int(ann_cfg.get("digits", 3)))
        stats_overlay.annotate_corner(ax, lines, style=style, loc=corner_loc)
    elif mode == "survival":
        lines = stat_text_panel(report.results, digits=int(ann_cfg.get("digits", 3)))
        stats_overlay.annotate_corner(ax, lines, style=style, loc="lower left")

    return report
