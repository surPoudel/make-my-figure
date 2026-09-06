"""Histogram: binned counts of one numeric column, optionally split by group.

A density plot (``ridge.py``) smooths a distribution; a histogram counts it. The two answer
different questions, and for a distribution that is not unimodal the difference matters - a kernel
density estimate with a wide bandwidth can turn two modes into one shoulder, while bins show what
was actually measured. This renderer therefore never smooths: what is drawn is a count (or a
percentage, or a density normalised so the bars integrate to 1) of the values in each bin.

Two arrangements:

``panel_mode="panels"`` (the default when there is a group) gives each group its own panel, which is
the form used when the groups have different sample sizes - each panel is honest about its own n.
``panel_mode="overlay"`` puts them on one axes with transparency, which reads better for two similar
distributions but is misleading with unequal n unless the counts are normalised, so that case is
warned about rather than left to the reader to notice.

**Bins are always computed from the pooled data and shared by every group.** Per-group bins would
put different bars over different value ranges and the comparison would be meaningless. This is the
one thing about a grouped histogram that is easy to get wrong and impossible to see afterwards.

Two input shapes are accepted, because a distribution is as often recorded one way as the other:

* **long** - ``x`` is the numeric column and ``group`` (optional) says which group each row is in.
* **wide** - ``value_columns`` lists one column per group, which is what a spreadsheet of
  "one column per condition" already looks like. Each column becomes one group named after it, and
  the columns may be different lengths: blanks are dropped per column rather than padded, so the
  common case of unequal group sizes needs no preparation at all.

``input_form`` selects between them, the same way the survival renderer does, rather than the
renderer guessing: deciding unprompted whether a second numeric column is another group or an
unrelated variable is exactly the kind of guess that produces a confidently wrong figure. The one
inference that is safe - no ``x`` chosen but columns listed - is made, and said so in a warning.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from make_my_figure_core.plots.base import (
    RenderError,
    RenderResult,
    apply_axis_overrides,
    apply_publication_layout,
    autorotate_xticklabels,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    place_legend,
    require_columns,
    resolve_legend_location,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "histogram_distribution"

INPUT_FORMS = ("long", "wide")
PANEL_MODES = ("panels", "overlay")

# What the y axis counts. "count" is the absolute frequency (how many observations); "frequency" is
# the relative frequency (the fraction of that group, summing to 1); "percent" is the same thing on
# a 0-100 scale; "density" divides by the bin width as well, so the bars integrate to 1 and remain
# comparable when the bin width changes.
NORMALIZE_MODES = ("count", "frequency", "percent", "density")

# How each distribution is drawn. "line" is a frequency polygon: the bin heights joined at their
# midpoints and closed to zero half a bin beyond each end, which is the classical form and keeps the
# area under the line equal to the area of the bars it replaces.
DRAW_STYLES = ("bars", "line", "both")

# Above this ratio of largest to smallest group n, an overlay of raw counts is dominated by the
# bigger group and the shapes are no longer comparable. 1.1 is deliberately strict: it is easier to
# ignore a warning than to notice a distorted comparison.
_UNEQUAL_N_RATIO = 1.1

# Panels are laid out in a row up to this many columns, then wrapped.
_MAX_PANEL_COLS = 3

# Above this many bins a marker per vertex turns the polygon into a solid band of dots, so the
# vertices are left implicit and only the line is drawn.
_MAX_MARKED_VERTICES = 25

_Y_LABELS = {"count": "Count", "frequency": "Relative frequency",
             "percent": "Percentage of group (%)", "density": "Density"}
_CUMULATIVE_Y_LABELS = {"count": "Cumulative count", "frequency": "Cumulative frequency",
                        "percent": "Cumulative percentage (%)",
                        "density": "Cumulative probability"}


def _resolve_bins(values: np.ndarray, bins: Optional[Any], bin_width: Optional[Any]) -> tuple:
    """Return ``(edges, note)``: the shared bin edges plus how they were chosen.

    ``bins`` and ``bin_width`` are two ways of saying the same thing, so setting both is refused
    rather than resolved by precedence - a silent winner here changes every bar in the figure.
    """
    lo, hi = float(np.min(values)), float(np.max(values))
    if not math.isfinite(lo) or not math.isfinite(hi):
        raise RenderError(f"{PLOT_TYPE}: the values contain no finite numbers to bin.")
    if hi == lo:
        # A single distinct value cannot be binned meaningfully; give it one bin around itself
        # rather than raising, so a degenerate group in an otherwise fine figure still draws.
        pad = abs(lo) * 0.005 or 0.5
        return np.array([lo - pad, hi + pad]), "single distinct value; one bin"

    if bins is not None and bin_width is not None:
        raise RenderError(
            f"{PLOT_TYPE}: set either 'bins' (a number of bins) or 'bin_width' (the width of one "
            "bin), not both - they contradict each other. Leave the other on auto.")

    if bin_width is not None:
        width = float(bin_width)
        if not math.isfinite(width) or width <= 0:
            raise RenderError(f"{PLOT_TYPE}: bin_width must be a positive number, got {bin_width!r}.")
        if width > (hi - lo):
            raise RenderError(
                f"{PLOT_TYPE}: bin_width {width:g} is wider than the data range "
                f"[{lo:g}, {hi:g}], which would collapse the histogram into one bar. "
                "Use a smaller width.")
        # Start on a round multiple of the width so the edges read as 10, 12, 14 rather than
        # 10.05, 12.05 - the axis is then interpretable without reading the bar boundaries.
        start = math.floor(lo / width) * width
        n = int(math.ceil((hi - start) / width))
        edges = start + np.arange(n + 1) * width
        return edges, f"bin_width={width:g}"

    if bins is not None:
        count = int(round(float(bins)))
        if count < 1:
            raise RenderError(f"{PLOT_TYPE}: bins must be at least 1, got {bins!r}.")
        return np.linspace(lo, hi, count + 1), f"bins={count}"

    # Freedman-Diaconis, which adapts to spread and sample size, falling back to Sturges when the
    # IQR is zero (a heavily tied distribution).
    q75, q25 = np.percentile(values, [75, 25])
    iqr = float(q75 - q25)
    if iqr > 0:
        width = 2.0 * iqr / (values.size ** (1.0 / 3.0))
        count = max(1, min(200, int(math.ceil((hi - lo) / width))))
        note = "auto (Freedman-Diaconis)"
    else:
        count = max(1, min(200, int(math.ceil(math.log2(values.size) + 1))))
        note = "auto (Sturges; zero IQR)"
    return np.linspace(lo, hi, count + 1), note


def _heights(values: np.ndarray, edges: np.ndarray, normalize: str,
             cumulative: bool = False) -> np.ndarray:
    counts, _ = np.histogram(values, bins=edges)
    total = counts.sum()
    if cumulative:
        # A cumulative density is a distribution function, so it rises to 1 rather than being
        # divided by the bin width - dividing twice would make the last value depend on the bins.
        running = np.cumsum(counts).astype(float)
        if normalize == "count" or not total:
            return running
        if normalize == "percent":
            return running * (100.0 / total)
        return running / total
    if normalize == "count" or not total:
        return counts.astype(float)
    if normalize == "frequency":
        return counts / total
    if normalize == "percent":
        return counts * (100.0 / total)
    return counts / (total * np.diff(edges))


def _polygon(heights: np.ndarray, edges: np.ndarray) -> tuple:
    """Frequency-polygon vertices: bin midpoints, closed to zero half a bin past each end."""
    mids = (edges[:-1] + edges[1:]) / 2.0
    first, last = float(np.diff(edges)[0]), float(np.diff(edges)[-1])
    xs = np.concatenate([[mids[0] - first], mids, [mids[-1] + last]])
    ys = np.concatenate([[0.0], heights, [0.0]])
    return xs, ys


def _resolve_input(spec: Dict[str, Any], df, notes: List[str]) -> tuple:
    """Return ``(long_frame, value_col, group_col, input_form)``.

    The wide form is melted here rather than in the caller so the rest of the renderer only ever
    sees one shape. ``df`` is never modified: the melt builds a new frame.
    """
    x = get_mapping(spec, "x", None)
    group = get_mapping(spec, "group", None)
    columns = get_mapping(spec, "value_columns", None)
    if isinstance(columns, str):
        columns = [columns]
    columns = [c for c in (columns or []) if c not in (None, "")]

    form = str(get_mapping(spec, "input_form", "long") or "long").lower()
    if form not in INPUT_FORMS:
        raise RenderError(f"{PLOT_TYPE}: input_form must be one of {INPUT_FORMS}, got {form!r}.")

    if form == "wide":
        if not columns:
            raise RenderError(
                f"{PLOT_TYPE}: the input form is 'wide', so list one column per group in "
                "'value_columns'. To plot a single numeric column split by a group column "
                "instead, set the input form to 'long'.")
    elif not x and columns:
        # A frontend prefills 'x' from a combo box that cannot be empty, so an empty 'x' together
        # with chosen columns is an unambiguous statement of intent, not a case worth refusing.
        notes.append(
            f"No single value column was chosen but {len(columns)} column(s) were listed, so the "
            "table was read in its wide form - one histogram per column. Set the input form to "
            "'wide' to make that explicit.")
        form = "wide"
    elif x and columns:
        notes.append(
            f"The input form is 'long', so '{x}' was plotted and the {len(columns)} column(s) "
            "listed in 'value_columns' were ignored. Switch the input form to 'wide' to plot one "
            "histogram per column instead.")
        columns = []
    elif not x:
        raise RenderError(
            f"{PLOT_TYPE}: choose 'x' - a single numeric column, with an optional 'group' column - "
            "or set the input form to 'wide' and list one column per group in 'value_columns'.")

    if not columns:
        require_columns(df, [x], context=PLOT_TYPE)
        work = df.copy()
        work[x] = coerce_numeric(work, x, context=PLOT_TYPE)
        return work, x, (group if group and group in work.columns else None), "long"

    require_columns(df, columns, context=PLOT_TYPE)
    if len(columns) != len(set(columns)):
        raise RenderError(f"{PLOT_TYPE}: 'value_columns' lists the same column twice: {columns}.")
    frames = []
    for column in columns:
        values = coerce_numeric(df, column, context=PLOT_TYPE).dropna()
        # Columns of different lengths are the norm for this shape - one condition simply had more
        # observations - so the shorter ones are trimmed to their own values, not padded.
        frames.append(pd.DataFrame({"value": values.to_numpy(dtype=float),
                                    "group": str(column)}))
    return pd.concat(frames, ignore_index=True), "value", "group", "wide"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    normalize = str(get_mapping(spec, "normalize", "count") or "count").lower()
    if normalize not in NORMALIZE_MODES:
        raise RenderError(
            f"{PLOT_TYPE}: normalize must be one of {NORMALIZE_MODES}, got {normalize!r}.")
    bins = get_mapping(spec, "bins", None)
    bin_width = get_mapping(spec, "bin_width", None)
    draw_style = str(get_mapping(spec, "draw_style", "bars") or "bars").lower()
    if draw_style not in DRAW_STYLES:
        raise RenderError(
            f"{PLOT_TYPE}: draw_style must be one of {DRAW_STYLES}, got {draw_style!r}.")
    cumulative = bool(get_mapping(spec, "cumulative", False))
    log_y = bool(get_mapping(spec, "log_y", False))
    show_median = bool(get_mapping(spec, "show_median", False))
    show_mean = bool(get_mapping(spec, "show_mean", False))
    x_tick_rotation = str(get_mapping(spec, "x_tick_rotation", "auto") or "auto").lower()
    share_axes = bool(get_mapping(spec, "share_axes", True))
    bar_alpha = get_mapping(spec, "bar_alpha", None)
    if bar_alpha is not None:
        bar_alpha = float(bar_alpha)
        if not 0.0 < bar_alpha <= 1.0:
            raise RenderError(
                f"{PLOT_TYPE}: bar_alpha must be greater than 0 and at most 1, got {bar_alpha:g}.")

    warnings: List[str] = []
    work, x, group, input_form = _resolve_input(spec, df, warnings)
    if group:
        groups: List[Any] = list(dict.fromkeys(work[group].dropna().tolist()))
        if not groups:
            raise RenderError(f"{PLOT_TYPE}: the group column '{group}' has no values.")
    else:
        groups = ["all"]

    panel_mode = get_mapping(spec, "panel_mode", None)
    if panel_mode in (None, "", "auto"):
        # One group is a single histogram either way; several groups default to their own panels,
        # because unequal sample sizes are the common case and panels stay honest about them.
        panel_mode = "overlay" if group is None else "panels"
    panel_mode = str(panel_mode).lower()
    if panel_mode not in PANEL_MODES:
        raise RenderError(
            f"{PLOT_TYPE}: panel_mode must be one of {PANEL_MODES}, got {panel_mode!r}.")

    per_group: Dict[str, np.ndarray] = {}
    for g in groups:
        vals = (work if group is None else work[work[group] == g])[x].dropna().to_numpy(dtype=float)
        vals = vals[np.isfinite(vals)]
        if vals.size == 0:
            warnings.append(f"Group '{g}' has no finite values in '{x}' and was left out.")
            continue
        per_group[str(g)] = vals
    if not per_group:
        raise RenderError(f"{PLOT_TYPE}: no finite numeric values in '{x}'.")
    groups = [g for g in map(str, groups) if g in per_group]

    pooled = np.concatenate(list(per_group.values()))
    edges, bin_note = _resolve_bins(pooled, bins, bin_width)

    sizes = {g: int(v.size) for g, v in per_group.items()}
    if len(sizes) > 1 and panel_mode == "overlay" and normalize == "count":
        ratio = max(sizes.values()) / max(1, min(sizes.values()))
        if ratio > _UNEQUAL_N_RATIO:
            big = max(sizes, key=sizes.get)
            small = min(sizes, key=sizes.get)
            warnings.append(
                f"Group sizes differ ({small}: n={sizes[small]}, {big}: n={sizes[big]}), so "
                "overlaid raw counts are taller for the larger group whatever its shape. Set "
                "normalize to 'percent' to compare the distributions, or use separate panels.")

    # ``style.marker_size`` is a scatter size in points SQUARED; ``plot(markersize=...)`` wants
    # points. Passing it straight through drew 20-point blobs that hid the curve.
    marker_pt = float(np.sqrt(max(style.marker_size, 1.0))) * 0.8

    labels = _CUMULATIVE_Y_LABELS if cumulative else _Y_LABELS
    y_label = (spec.get("layout", {}) or {}).get("y_label") or labels[normalize]
    x_label = (spec.get("layout", {}) or {}).get("x_label") or x
    title = (spec.get("layout", {}) or {}).get("title")
    legend_location = resolve_legend_location(spec, style)

    with style.apply():
        if panel_mode == "overlay":
            fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.78))
            axes = [ax]
            for i, g in enumerate(groups):
                heights = _heights(per_group[g], edges, normalize, cumulative)
                col = style.color_for(i)
                label = f"{g} (n={sizes[g]})" if group else None
                if draw_style in ("bars", "both"):
                    fill_alpha = bar_alpha if bar_alpha is not None else (
                        0.45 if draw_style == "bars" else 0.25)
                    ax.stairs(heights, edges, fill=True, color=col, alpha=fill_alpha,
                              linewidth=0, zorder=2)
                    ax.stairs(heights, edges, fill=False, color=col,
                              linewidth=style.line_width_pt,
                              label=label if draw_style == "bars" else None, zorder=3)
                if draw_style in ("line", "both"):
                    xs, ys = _polygon(heights, edges)
                    # Vertex markers only help when the bins are few and the line is alone;
                    # alongside bars, or over many bins, they obscure what they mark.
                    marked = draw_style == "line" and len(heights) <= _MAX_MARKED_VERTICES
                    ax.plot(xs, ys, color=col, lw=style.line_width_pt,
                            marker="o" if marked else "None", markersize=marker_pt,
                            label=label, zorder=5)
                if show_median:
                    ax.axvline(float(np.median(per_group[g])), color=col,
                               lw=style.line_width_pt, ls="--", alpha=0.9, zorder=4)
                if show_mean:
                    ax.axvline(float(np.mean(per_group[g])), color=col,
                               lw=style.line_width_pt, ls=":", alpha=0.9, zorder=4)
            ax.set_ylim(bottom=0.0)
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            if group is not None:
                place_legend(ax, style, title=str(group), location=legend_location)
            if title:
                ax.set_title(title)
        else:
            ncols = min(len(groups), _MAX_PANEL_COLS)
            nrows = int(math.ceil(len(groups) / ncols))
            width, height = figure_size(spec, style, aspect=0.78)
            # Keep the figure's overall width - that is the journal column width the style
            # resolved - and grow only the height for extra rows, so a two-panel figure still
            # fits the column it was sized for. Pick a wider column_width for roomier panels.
            fig, grid = plt.subplots(nrows, ncols, figsize=(width, height * nrows * 0.72),
                                     sharex=share_axes, sharey=share_axes, squeeze=False)
            axes = [a for row in grid for a in row]
            for i, g in enumerate(groups):
                a = axes[i]
                heights = _heights(per_group[g], edges, normalize, cumulative)
                col = style.color_for(i)
                if draw_style in ("bars", "both"):
                    fill_alpha = bar_alpha if bar_alpha is not None else (
                        1.0 if draw_style == "bars" else 0.35)
                    # White separators read well on solid bars, but under a polygon they erase the
                    # step outline and the bars stop looking like bars. Outline them in their own
                    # colour instead, so "both" shows both.
                    a.stairs(heights, edges, fill=True, color=col, alpha=fill_alpha,
                             linewidth=style.spine_width_pt,
                             edgecolor="white" if draw_style == "bars" else col, zorder=2)
                if draw_style in ("line", "both"):
                    xs, ys = _polygon(heights, edges)
                    marked = draw_style == "line" and len(heights) <= _MAX_MARKED_VERTICES
                    a.plot(xs, ys, color=col, lw=style.line_width_pt,
                           marker="o" if marked else "None", markersize=marker_pt, zorder=5)
                if show_median:
                    a.axvline(float(np.median(per_group[g])), color=style.text_color,
                              lw=style.line_width_pt, ls="--", alpha=0.9, zorder=4)
                if show_mean:
                    a.axvline(float(np.mean(per_group[g])), color=style.text_color,
                              lw=style.line_width_pt, ls=":", alpha=0.9, zorder=4)
                a.set_ylim(bottom=0.0)
                # Panel headings sit below the figure title in the hierarchy, so they are not
                # also bold - otherwise they compete with it for the reader's eye.
                a.set_title(f"{g} (n={sizes[g]})", fontsize=style.axis_font_pt,
                            fontweight="normal")
                a.set_xlabel(x_label)
                if i % ncols == 0:
                    a.set_ylabel(y_label)
            for a in axes[len(groups):]:
                a.set_visible(False)
            if title:
                # The profile sets axes.titleweight to bold; a suptitle does not inherit that, so
                # it is set here or the figure title would be lighter than its own panels.
                fig.suptitle(title, fontsize=style.title_font_pt, fontweight=getattr(style, "title_font_weight", "bold"))

        drawn_heights = np.concatenate(
            [_heights(v, edges, normalize, cumulative) for v in per_group.values()])
        positive = drawn_heights[drawn_heights > 0]
        if log_y:
            if positive.size == 0:
                raise RenderError(
                    f"{PLOT_TYPE}: a logarithmic y axis needs at least one non-empty bin.")
            floor = float(positive.min()) / 2.0
            empty = int(np.sum(drawn_heights <= 0))
            if empty:
                warnings.append(
                    f"{empty} empty bin(s) cannot be drawn on a logarithmic y axis - a count of "
                    "zero has no position on a log scale. Those bins appear blank, not as zero.")
        for a in axes:
            if not a.get_visible():
                continue
            if log_y:
                a.set_yscale("log")
                a.set_ylim(bottom=floor)
            style_axes(a, style)
            # The x axis is numeric, so the automatic angle-picking meant for long category
            # names would slant "10", "20", "30" for no reason. Only an explicit angle applies.
            if x_tick_rotation != "auto":
                autorotate_xticklabels(a, style, rotation=x_tick_rotation)
        # The drawn span is the bin range, not the value range: the outermost bins can extend past
        # the data when the edges were rounded to a whole bin_width. Passing it explicitly means an
        # x-range that would cut a bar off is refused rather than silently clipping it.
        extent = (float(edges[0]), float(edges[-1]))
        if draw_style in ("line", "both"):
            # The polygon closes half a bin beyond each end, so it is drawn wider than the bins.
            widths = np.diff(edges)
            extent = (float(edges[0] - widths[0] / 2.0), float(edges[-1] + widths[-1] / 2.0))
        y_extent = (0.0 if not log_y else float(positive.min()), float(drawn_heights.max()))
        applied_axis = {}
        for a in axes:
            if a.get_visible():
                applied_axis = (apply_axis_overrides(a, spec, x_extent=extent,
                                                     y_extent=y_extent) or applied_axis)
        # The registry applies the shared publication layout to the FIRST axes only, which would
        # leave every panel but one un-rotated and un-padded. Apply it to each panel here.
        for a in axes:
            if a.get_visible():
                apply_publication_layout(fig, a, spec, style)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[x, group])
    meta["input_form"] = input_form
    meta["panel_mode"] = panel_mode
    meta["draw_style"] = draw_style
    meta["cumulative"] = cumulative
    meta["log_y"] = log_y
    if show_median:
        meta["median_by_group"] = {g: float(np.median(v)) for g, v in per_group.items()}
    if show_mean:
        meta["mean_by_group"] = {g: float(np.mean(v)) for g, v in per_group.items()}
    meta["normalize"] = normalize
    meta["groups"] = list(groups)
    meta["n_by_group"] = sizes
    meta["n_bins"] = int(len(edges) - 1)
    meta["bin_width"] = float(np.diff(edges)[0])
    meta["bin_range"] = [float(edges[0]), float(edges[-1])]
    meta["bin_selection"] = bin_note
    meta["shared_bins"] = True
    if applied_axis:
        meta["axis_overrides"] = applied_axis
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
