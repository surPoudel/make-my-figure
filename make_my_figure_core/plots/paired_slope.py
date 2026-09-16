"""Paired dot plot / slopegraph for matched observations.

For before/after designs, matched samples, paired treatments, or repeated
measures: one line per subject connects that subject's value across the
conditions/timepoints, so within-subject change is visible directly. An
optional group column colors the lines.

Statistics: when ``spec["statistics"]["enabled"]`` is true the paired tests in
the engine (paired t-test, Wilcoxon signed-rank; repeated-measures ANOVA as the
omnibus) run with the ``subject`` column as the pair ID and the ``condition``
column as the grouping factor, and the results are drawn as brackets between
the conditions by the shared bracket engine. The points here are the line
markers of each subject's path, so the shared observation engine (jitter /
beeswarm arrangements) is deliberately not used: moving a marker would detach
it from its line.
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
from make_my_figure_core.plots.stats_integration import run_and_annotate
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "paired_slopegraph"


def _stats_view(spec: Dict[str, Any], *, subject: str, condition: str, value: str) -> Dict[str, Any]:
    """The spec as the statistics engine expects it: ``x``/``y`` aliases for condition/value and
    the subject column as the pair ID unless the StatsSpec names its own columns."""
    mapping = dict(spec.get("mapping", {}) or {})
    mapping.setdefault("x", condition)
    mapping.setdefault("y", value)
    stats = dict(spec.get("statistics", {}) or {})
    if not stats.get("subject_column") and not stats.get("paired_id_column"):
        stats["subject_column"] = subject
    if not stats.get("group_column"):
        stats["group_column"] = condition
    if not stats.get("value_column"):
        stats["value_column"] = value
    return {**spec, "mapping": mapping, "statistics": stats}


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    subject = get_mapping(spec, "subject", required=True, context=PLOT_TYPE)
    condition = get_mapping(spec, "condition", required=True, context=PLOT_TYPE)
    value = get_mapping(spec, "value", required=True, context=PLOT_TYPE)
    color_by = get_mapping(spec, "color", None)

    require_columns(df, [subject, condition, value], context=PLOT_TYPE)
    work = df.copy()
    work[value] = coerce_numeric(work, value, context=PLOT_TYPE)

    conditions = ordered_unique(work[condition].tolist())
    cond_x = {c: i for i, c in enumerate(conditions)}
    subjects = ordered_unique(work[subject].tolist())
    has_color = bool(color_by and color_by in work.columns)
    color_levels = ordered_unique(work[color_by].tolist()) if has_color else []
    warnings: List[str] = []
    # Highest drawn value per condition (what a bracket must clear), keyed by str(condition).
    tops: Dict[str, float] = {}

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.85))
        seen_levels = set()
        for subj in subjects:
            sub = work[work[subject] == subj]
            # Keep one value per condition (mean if duplicated), in condition order.
            pts = []
            for c in conditions:
                cell = sub[sub[condition] == c][value]
                vals = cell.to_numpy(float)
                vals = vals[np.isfinite(vals)]
                if vals.size:
                    drawn = float(vals.mean())
                    pts.append((cond_x[c], drawn))
                    key = str(c)
                    tops[key] = max(tops.get(key, -np.inf), drawn)
            if len(pts) < 1:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if has_color:
                lvl = str(sub[color_by].iloc[0])
                ci = color_levels.index(sub[color_by].iloc[0]) if sub[color_by].iloc[0] in color_levels else 0
                col = style.color_for(ci)
                label = lvl if lvl not in seen_levels else None
                seen_levels.add(lvl)
            else:
                col = style.color_for(0)
                label = None
            # Line and point colors are independently controllable — an explicit
            # line_color / point_color overrides the group color for that element.
            _lc = get_mapping(spec, "line_color", None)
            _pc = get_mapping(spec, "point_color", None)
            line_col = _lc if (_lc and str(_lc) != "(group)") else col
            point_col = _pc if (_pc and str(_pc) != "(group)") else col
            lw = float(get_mapping(spec, "line_width", None) or style.line_width_pt)
            lalpha = float(get_mapping(spec, "line_alpha", None)
                           or (0.55 if not has_color else 0.75))
            psize = float(get_mapping(spec, "point_size", None)
                          or max(3.0, style.marker_size ** 0.5))
            ax.plot(xs, ys, color=line_col, lw=lw, alpha=lalpha, zorder=2, label=label,
                    marker="o", markersize=psize, markerfacecolor=point_col,
                    markeredgecolor="white", markeredgewidth=style.marker_edge_width)

        ax.set_xticks(range(len(conditions)))
        ax.set_xticklabels([str(c) for c in conditions])
        ax.set_xlim(-0.35, len(conditions) - 0.65)
        ax.set_xlabel(spec.get("layout", {}).get("x_label", str(condition)))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", str(value)))
        ax.margins(y=0.08)
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)
        if has_color:
            place_legend(ax, style, title=str(color_by), force_outside=True)
        else:
            fig.tight_layout()

        # Statistics: disabled unless spec["statistics"]["enabled"]. Paired tests use the subject
        # column as the pair ID; brackets sit between the compared conditions.
        positions_map = {str(c): float(i) for c, i in cond_x.items()}
        stats_report = run_and_annotate(
            _stats_view(spec, subject=subject, condition=condition, value=value), work, style,
            PLOT_TYPE, ax=ax, positions=positions_map, tops=tops, mode="bracket")

    meta = base_metadata(spec, style, work, used_columns=[subject, condition, value, color_by])
    meta["n_subjects"] = len(subjects)
    meta["conditions"] = [str(c) for c in conditions]
    if stats_report is not None:
        meta["statistics_report"] = stats_report.to_dict()
    return RenderResult(figure=fig, metadata=meta, warnings=warnings, stats_report=stats_report)
