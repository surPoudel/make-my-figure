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
from make_my_figure_core.statistics.models import StatsError
from make_my_figure_core.statistics.runner import run_statistics
from make_my_figure_core.statistics.schemas import normalize_stats_spec


def _clear_corner_panel(ax, gap_px: float = 3.0, max_rounds: int = 8) -> None:
    """Raise the value axis until the omnibus text panel clears every bracket and label.

    The headroom above was a guess (8.5 % of the range per line). Bracket labels
    with an effect size, or a panel wrapped onto more lines in a narrow facet,
    outgrew it: the ANOVA panel sat over the "****, g = -2.7" labels of a
    two-way ANOVA with post-hoc pairs. Measured here instead, in display pixels.
    """
    fig = ax.figure
    panel = next((t for t in reversed(ax.texts) if t.get_zorder() == 8 and t.get_transform() == ax.transAxes),
                 None)
    if panel is None:
        return
    for _ in range(max_rounds):
        try:
            fig.canvas.draw()
            r = fig.canvas.get_renderer()
            box = panel.get_window_extent(r)
            if panel.get_bbox_patch() is not None:
                box = panel.get_bbox_patch().get_window_extent(r)
        except Exception:  # noqa: BLE001
            return
        top = -float("inf")
        for a in list(ax.texts) + list(ax.lines) + list(ax.collections):
            if a is panel or not a.get_visible():
                continue
            try:
                bb = a.get_window_extent(r)
            except Exception:  # noqa: BLE001
                continue
            if bb.width <= 0 and bb.height <= 0:
                continue
            if bb.x1 < box.x0 or bb.x0 > box.x1 or bb.y0 > box.y1:
                continue
            top = max(top, bb.y1)
        overlap = top + gap_px - box.y0
        if overlap <= 0.5:
            return
        frame = ax.get_window_extent(r)
        span = max(1.0, box.y0 - frame.y0)
        y0, y1 = ax.get_ylim()
        # Data heights scale by (y1 - y0): shrink them until the tallest mark ends at the panel.
        ax.set_ylim(y0, y0 + (y1 - y0) * (top - frame.y0 + gap_px) / span)


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
    orientation: str = "vertical",
):
    """Run stats for ``spec`` and (optionally) annotate ``ax``.

    ``positions``/``tops`` are keyed by ``str(category)`` for simple grouped
    plots, or by ``(str(x_level), str(group))`` for within-x grouped plots.
    ``tops`` should be the highest *drawn* value per group (points, error bar,
    whisker, ...): a bracket clears every group it spans, not just the two it
    compares. ``orientation="horizontal"`` lays brackets along x for horizontal
    bars/boxes (categories on y); ``above_bar`` placement stays vertical-only
    and falls back to brackets in that case.
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

        placement = str(ann_cfg.get("placement", "bracket") or "bracket").lower()
        if placement not in ("bracket", "above_bar"):
            raise StatsError(
                f"annotation placement must be 'bracket' or 'above_bar', got {placement!r}."
            )

        horizontal = str(orientation or "vertical").lower().startswith("h")
        info: Dict[str, Any]
        if placement == "above_bar" and not horizontal:
            # One label per compared bar, for comparisons that all share a reference group.
            flat_tops = {k: v for k, v in (tops or {}).items() if not isinstance(k, tuple)}
            info = stats_overlay.annotate_above(
                ax, items, {k: v for k, v in positions.items() if not isinstance(k, tuple)},
                flat_tops, style=style, cfg=ann_cfg,
                reference=stats_spec.get("reference_group"))
            leftover = info.get("unplaced") or []
            if leftover:
                # A label above one bar cannot describe a comparison between two non-reference
                # groups, so those fall back to brackets rather than being dropped silently.
                info["bracket_fallback"] = stats_overlay.annotate_pairwise(
                    ax, leftover, pos_lookup, style=style, cfg=ann_cfg,
                    top_lookup=top_lookup, positions=positions, tops=tops)
        else:
            info = stats_overlay.annotate_pairwise(
                ax, items, pos_lookup, style=style, cfg=ann_cfg, top_lookup=top_lookup,
                positions=positions, tops=tops, orientation=orientation)
            if placement == "above_bar" and horizontal:
                info["note"] = "above_bar placement is vertical-only; brackets were drawn instead."
        report.config = dict(report.config or {})
        report.config["_annotation_info"] = info
        # Omnibus (ANOVA / Kruskal) and other non-pairwise results have no bracket
        # between two bars, so surface their p-values as a corner panel — otherwise
        # a user who selects (or auto-gets) an ANOVA sees nothing on the figure.
        panel_lines = stat_text_panel(
            [r for r in report.results if r.comparison_type != "two_group"],
            digits=int(ann_cfg.get("digits", 3)), cfg=ann_cfg)
        if panel_lines:
            # Reserve headroom so the panel sits above the data rather than over it.
            y0, y1 = ax.get_ylim()
            ax.set_ylim(y0, y1 + (0.085 * len(panel_lines) + 0.04) * (y1 - y0))
            stats_overlay.annotate_corner(ax, panel_lines, style=style, loc="upper left",
                                          cfg=ann_cfg)
            _clear_corner_panel(ax)
    elif mode == "corner":
        lines = stat_text_panel(report.results, digits=int(ann_cfg.get("digits", 3)), cfg=ann_cfg)
        stats_overlay.annotate_corner(ax, lines, style=style, loc=corner_loc, cfg=ann_cfg)
    elif mode == "survival":
        lines = stat_text_panel(report.results, digits=int(ann_cfg.get("digits", 3)))
        # Placement is user-configurable (annotation block 'location'); lower left by default.
        stats_overlay.annotate_corner(ax, lines, style=style, cfg=ann_cfg,
                                      loc=str(ann_cfg.get("location", "lower left")).lower())

    return report
