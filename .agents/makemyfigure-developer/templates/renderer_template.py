"""__DISPLAY_NAME__: __ONE_LINE_PURPOSE__.

__WHAT_THE_PLOT_ANSWERS__ (2-4 sentences: what scientific question the plot answers, the input
data shape it expects, and what marks encode what). Keep this docstring honest: the related-renderer
finder and the manual catalogue read it.

Contract (references/renderer-contract.md). Canonical renderers to copy from: barplot.py and
box_violin.py (older renderers may predate parts of the contract).
* read column roles and options ONLY through ``get_mapping``/``spec["mapping"]``; never read
  ``spec["style"]`` or ``spec["statistics"]`` directly (registry.render and run_and_annotate do);
* never mutate ``df`` (work on a copy), never compute inferential statistics here;
* draw inside ``with style.apply():``, size with ``figure_size``, use style tokens for every
  aesthetic (``style.color_for``, ``style.marker_size``, ``style.marker_edge_width``,
  ``style.line_width_pt``); no literal colours or sizes a user cannot change;
* order: draw -> axes/legend -> ``apply_axis_overrides`` -> ``fig.tight_layout()`` -> statistics
  (``run_and_annotate`` needs the final axes geometry) -> metadata;
* return ``RenderResult(figure, metadata, warnings)`` with scientific metadata (n per group,
  summary/error definitions, category order) so exports and sidecars can report them.
"""
from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots.base import (
    RenderError,
    RenderResult,
    apply_axis_overrides,
    autorotate_xticklabels,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    place_legend,
    require_columns,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "__PLOT_TYPE__"

# Presentation choices exposed as options (declare them in ui_hints.OPTIONS with scope="style"
# when they only change appearance, scope="config" when they change what is computed/shown).
ORIENTATIONS = ("vertical", "horizontal")


def _choice(value: Any, allowed: tuple, default: str) -> str:
    v = str(value).lower() if value not in (None, "") else default
    return v if v in allowed else default


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    # ---- 1. column roles (required roles raise RenderError with a clear message) -------------
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    group = get_mapping(spec, "group")                      # optional role
    require_columns(df, [c for c in (x, y, group) if c], context=PLOT_TYPE)

    # ---- 2. options (presentation only; defaults are the publication-ready look) --------------
    orientation = _choice(get_mapping(spec, "orientation"), ORIENTATIONS, "vertical")
    show_points = bool(get_mapping(spec, "points", True))

    # ---- 3. data preparation on a COPY; record what was dropped -----------------------------
    work = df.copy()
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)
    n_before = len(work)
    work = work[np.isfinite(work[y])]
    warnings: List[str] = []
    if len(work) < n_before:
        warnings.append(f"{n_before - len(work)} row(s) with missing/non-numeric {y!r} were not drawn.")
    if work.empty:
        raise RenderError(f"{PLOT_TYPE}: no finite values in {y!r}.")
    categories = list(dict.fromkeys(work[x].astype(str)))    # order of first appearance
    n_by_group = {c: int((work[x].astype(str) == c).sum()) for c in categories}
    positions = {c: float(i) for i, c in enumerate(categories)}
    tops: Dict[str, float] = {}

    # ---- 4. draw ----------------------------------------------------------------------------
    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.75))
        for i, cat in enumerate(categories):
            vals = work.loc[work[x].astype(str) == cat, y].to_numpy(float)
            color = style.color_for(i)
            tops[cat] = float(np.nanmax(vals))
            # TODO: replace with the plot's marks. Keep every observation visible when show_points.
            xs, ys = (vals, np.full(vals.size, i)) if orientation == "horizontal" else (np.full(vals.size, i), vals)
            ax.scatter(xs, ys, s=style.marker_size, color=color, edgecolors=style.text_color,
                       linewidths=style.marker_edge_width, zorder=3)
        if orientation == "horizontal":
            ax.set_yticks(range(len(categories)), categories)
            ax.set_xlabel(y); ax.set_ylabel(x)
        else:
            ax.set_xticks(range(len(categories)), categories)
            ax.set_xlabel(x); ax.set_ylabel(y)
            autorotate_xticklabels(ax, style)
        style_axes(ax, style)
        if group:
            place_legend(ax, style, title=str(group))
        apply_axis_overrides(ax, spec)
        fig.tight_layout()

        # ---- 5. statistics: ONLY through the shared engine, after layout ---------------------
        # Brackets need category positions and the top of what was drawn per category (vertical only).
        from make_my_figure_core.plots.stats_integration import run_and_annotate
        stats_report = run_and_annotate(spec, work, style, PLOT_TYPE, ax=ax,
                                        positions=positions if orientation == "vertical" else None,
                                        tops=tops if orientation == "vertical" else None,
                                        mode="bracket" if orientation == "vertical" else "corner")

    # ---- 6. metadata: what a reader of the sidecar needs to trust the figure ----------------
    meta = base_metadata(spec, style, work, used_columns=[x, y, group])
    meta.update({"n_by_group": n_by_group, "category_order": categories,
                 "orientation": orientation, "points": show_points})
    return RenderResult(figure=fig, metadata=meta, warnings=warnings, stats_report=stats_report)
