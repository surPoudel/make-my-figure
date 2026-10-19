"""Line / time-course plot with a centre line and an error band.

Band methods: ``sem``/``sd``/``ci95`` (mean-centred, symmetric), ``iqr`` and ``range``
(median-centred order statistics, for replicate measurements), or ``none``.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots.base import (
    RenderResult,
    apply_publication_layout,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    place_legend,
    resolve_legend_location,
    require_columns,
    style_axes,
    summarize_band,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "lineplot_timecourse_with_error_band"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    from make_my_figure_core.plots.facets import wants_facets

    if wants_facets(spec):
        return _render_facets(spec, df, style)
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    color_by = get_mapping(spec, "color", None)
    error_method = str(get_mapping(spec, "error", "sem"))
    error_display = str(get_mapping(spec, "error_display", "band") or "band")

    require_columns(df, [x, y], context=PLOT_TYPE)
    work = df.copy()
    work[x] = coerce_numeric(work, x, context=PLOT_TYPE)
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)

    # Optional second grouping: ``style_by`` varies line style and marker within each colour
    # level (e.g. colour = workload, style = platform), so series stay distinguishable in
    # greyscale. Legend entries read "<colour level>, <style level>".
    style_by = get_mapping(spec, "style_by", None)
    if style_by and style_by not in work.columns:
        style_by = None
    if color_by and color_by in work.columns:
        color_levels = list(dict.fromkeys(work[color_by].tolist()))
    else:
        color_levels = [None]
    style_levels = list(dict.fromkeys(work[style_by].tolist())) if style_by else [None]
    series = [(c, st) for c in color_levels for st in style_levels]
    _LS = ["-", "--", ":", "-."]
    _MK = ["o", "s", "^", "D"]
    warnings: List[str] = []

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.7))
        for (c, st) in series:
            ci = color_levels.index(c)
            sti = style_levels.index(st)
            s = c
            sub = work if c is None else work[work[color_by] == c]
            if st is not None:
                sub = sub[sub[style_by] == st]
            if sub.empty:
                continue
            xs = sorted(sub[x].dropna().unique())
            means, lows, highs = [], [], []
            for xv in xs:
                vals = sub.loc[sub[x] == xv, y].to_numpy()
                c, lo, hi = summarize_band(vals, error_method)
                means.append(c)
                lows.append(lo)
                highs.append(hi)
            xs = np.asarray(xs, dtype=float)
            means = np.asarray(means, dtype=float)
            lows = np.asarray(lows, dtype=float)
            highs = np.asarray(highs, dtype=float)
            col = style.color_for(ci)
            label = None if s is None else (f"{s}, {st}" if st is not None else str(s))
            ax.plot(xs, means, color=col, lw=style.line_width_pt, label=label,
                    marker=_MK[sti % len(_MK)], linestyle=_LS[sti % len(_LS)],
                    markersize=max(3.0, style.line_width_pt * 2.2))
            if error_method.lower() != "none":
                if error_display == "bars":
                    _error_bars(ax, xs, means, lows, highs, col, style, group=label)
                else:
                    band = ax.fill_between(xs, lows, highs, color=col, alpha=0.2, linewidth=0)
                    band._mmf_group = label

        ax.set_xlabel(spec.get("layout", {}).get("x_label", x))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", y))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        if series != [(None, None)]:
            place_legend(ax, style, title=(str(color_by) or None) if str(color_by).strip() else None,
                         location=resolve_legend_location(spec, style))
        style_axes(ax, style)
        fig.tight_layout()
        apply_publication_layout(fig, ax, spec, style)

    meta = base_metadata(spec, style, work, used_columns=[x, y, color_by])
    meta["error_method"] = error_method
    meta["series"] = [f"{c}, {st}" if st is not None else str(c) for c, st in series if c is not None]
    meta["style_by"] = style_by
    if error_display == "bars":
        meta["error_display"] = "bars"
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)


_LS = ["-", "--", ":", "-."]
_MK = ["o", "s", "^", "D"]


def _error_bars(ax, xs, means, lows, highs, color, style, group=None) -> None:
    """Mean +/- error as bars with caps (the band's numbers, drawn as bars)."""
    ok = np.isfinite(lows) & np.isfinite(highs) & np.isfinite(means)
    if not ok.any():
        return
    container = ax.errorbar(xs[ok], means[ok], yerr=[means[ok] - lows[ok], highs[ok] - means[ok]], fmt="none",
                            ecolor=color, elinewidth=max(0.6, style.line_width_pt * 0.6),
                            capsize=max(1.5, style.line_width_pt * 1.6),
                            capthick=max(0.6, style.line_width_pt * 0.6), zorder=2)
    # tag every piece (bar lines and caps) with its series: a colour override by
    # level name recoloured the line and marker but left these palette-coloured
    for part in list(container[1]) + list(container[2]):
        part._mmf_group = group


def _series_stats(sub, x, y, error_method):
    xs = sorted(sub[x].dropna().unique())
    means, lows, highs = [], [], []
    for xv in xs:
        c, lo, hi = summarize_band(sub.loc[sub[x] == xv, y].to_numpy(), error_method)
        means.append(c)
        lows.append(lo)
        highs.append(hi)
    return (np.asarray(xs, dtype=float), np.asarray(means, dtype=float),
            np.asarray(lows, dtype=float), np.asarray(highs, dtype=float))


def _render_facets(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    """One panel per facet level; same series, colours, line styles and axes in each."""
    from make_my_figure_core.plots.facets import (
        empty_panel_note, facet_columns, facet_metadata, finish_facet_grid, make_facet_grid)

    layout = spec.get("layout", {}) or {}
    x = get_mapping(spec, "x", required=True, context=PLOT_TYPE)
    y = get_mapping(spec, "y", required=True, context=PLOT_TYPE)
    color_by = get_mapping(spec, "color", None)
    error_method = str(get_mapping(spec, "error", "sem"))
    error_display = str(get_mapping(spec, "error_display", "band") or "band")
    share_y = bool(get_mapping(spec, "facet_share_y", True))
    row, col = facet_columns(spec, df)
    warnings: List[str] = []
    for name, var in (("facet rows", row), ("facet columns", col)):
        if var is not None and var in (x, color_by):
            warnings.append(f"{var!r} is mapped to both {name} and {'x' if var == x else 'color'}; "
                            "each panel then holds a single level of it.")

    require_columns(df, [x, y], context=PLOT_TYPE)
    work = df.copy()
    work[x] = coerce_numeric(work, x, context=PLOT_TYPE)
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)
    style_by = get_mapping(spec, "style_by", None)
    if style_by and style_by not in work.columns:
        style_by = None
    color_levels = list(dict.fromkeys(work[color_by].tolist())) if color_by and color_by in work.columns \
        else [None]
    style_levels = list(dict.fromkeys(work[style_by].tolist())) if style_by else [None]
    series = [(c, st) for c in color_levels for st in style_levels]
    panel_series = {}

    with style.apply():
        grid = make_facet_grid(spec, work, style, row=row, col=col, aspect=0.7,
                               share_x=True, share_y=share_y)
        warnings.extend(w for w in grid.warnings if w not in warnings)
        for panel in grid.panels:
            ax, sub_all = panel.ax, panel.data
            if sub_all.empty:
                empty_panel_note(ax, style)
                continue
            drawn = 0
            for (c, st) in series:
                ci, sti = color_levels.index(c), style_levels.index(st)
                sub = sub_all if c is None else sub_all[sub_all[color_by] == c]
                if st is not None:
                    sub = sub[sub[style_by] == st]
                if sub.empty:
                    continue
                xs, means, lows, highs = _series_stats(sub, x, y, error_method)
                colr = style.color_for(ci)
                label = None if c is None else (f"{c}, {st}" if st is not None else str(c))
                ax.plot(xs, means, color=colr, lw=style.line_width_pt, label=label,
                        marker=_MK[sti % len(_MK)], linestyle=_LS[sti % len(_LS)],
                        markersize=max(3.0, style.line_width_pt * 2.2))
                if error_method.lower() != "none":
                    if error_display == "bars":
                        _error_bars(ax, xs, means, lows, highs, colr, style, group=label)
                    else:
                        band = ax.fill_between(xs, lows, highs, color=colr, alpha=0.2, linewidth=0)
                        band._mmf_group = label
                drawn += 1
            panel_series[panel.label] = drawn
        # Ticks at the sampled times when there are few of them: months 4, 6, 8, 10
        # were sampled, and an axis reading 4, 5, 6 ... 10 suggests months that were not.
        sampled = sorted(work[x].dropna().unique())
        if 2 <= len(sampled) <= 8 and all(float(v).is_integer() for v in sampled):
            for panel in grid.panels:
                panel.ax.set_xticks([float(v) for v in sampled])
        finish_facet_grid(grid, spec, style, x_label=layout.get("x_label", x), y_label=layout.get("y_label", y))
        if series != [(None, None)]:
            handles, labels = [], []
            for (c, st) in series:
                ci, sti = color_levels.index(c), style_levels.index(st)
                from matplotlib.lines import Line2D

                handles.append(Line2D([], [], color=style.color_for(ci), lw=style.line_width_pt,
                                      marker=_MK[sti % len(_MK)], linestyle=_LS[sti % len(_LS)],
                                      markersize=max(3.0, style.line_width_pt * 2.2)))
                labels.append(f"{c}, {st}" if st is not None else str(c))
            # A legend "best"-placed inside a grid lands over a panel; the grid's
            # default is beside it, as for the box grid. A chosen location wins.
            location = resolve_legend_location(spec, style)
            if not str(layout.get("legend_location", "")).strip() and not getattr(style, "legend_outside", False):
                from make_my_figure_core.plots.base import LEGEND_LOCATIONS

                location = LEGEND_LOCATIONS["outside right"]
            place_legend(grid.host, style, title=(str(color_by) if color_by else None), handles=handles,
                         labels=labels, location=location)
        from make_my_figure_core.plots.facets import refit_strips

        grid._mmf_reported = list(grid.warnings)
        refit_strips(grid.fig)      # the legend's margin narrowed the panels

    warnings.extend(w for w in grid.warnings if w not in warnings)
    meta = base_metadata(spec, style, work, used_columns=[x, y, color_by, row, col])
    meta["error_method"] = error_method
    meta["series"] = [f"{c}, {st}" if st is not None else str(c) for c, st in series if c is not None]
    meta["style_by"] = style_by
    meta["facets"] = facet_metadata(grid)
    if error_display == "bars":
        meta["error_display"] = "bars"
    return RenderResult(figure=grid.fig, metadata=meta, warnings=warnings)
