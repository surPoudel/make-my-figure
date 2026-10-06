"""Clustered heatmap from a feature-by-sample matrix.

The first (row-id) column holds row labels; all remaining columns are numeric
sample values. Optional hierarchical clustering reorders rows/columns using
SciPy (via :mod:`make_my_figure_core.clustering`, with selectable distance
metric, linkage method, and scaling); if linkage fails we fall back to original
order and record a warning (never fail silently).

v0.5 additions (all optional, backward-compatible — defaults reproduce the
original euclidean/average, unscaled output):
  * ``scale`` (none/row_zscore/column_zscore/center_rows/log)
  * ``distance_metric`` and ``linkage_method``
  * ``cluster_k_rows`` / ``cluster_k_columns`` — cut the tree into k clusters,
    draw a cluster color strip + legend, and export the assignment table
  * ``sort_by_cluster`` — group rows/columns by cluster
  * ``highlight_rows`` / ``highlight_columns`` — bold+label selected features
    even when labels are otherwise hidden (paste a gene list)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core import clustering as _clust
from make_my_figure_core.plots.base import (
    resolve_figure_size,
    RenderError,
    RenderResult,
    base_metadata,
    clear_axis_label,
    fit_tick_labels,
    get_mapping,
    require_columns,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "heatmap_clustered_matrix"

# Colorblind-aware qualitative palette for annotation categories.
_ANNOT_PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9",
                  "#F0E442", "#999999", "#000000"]


def _order_and_linkage(filled: np.ndarray, axis: str, method: str, metric: str,
                       do_cluster: bool, warnings: List[str]):
    """Return (order, linkage) for one axis; falls back to identity on failure."""
    n = filled.shape[0] if axis == "rows" else filled.shape[1]
    order = list(range(n))
    linkage_z = None
    if do_cluster and n > 2:
        try:
            linkage_z = _clust.compute_linkage(filled, method=method, metric=metric, axis=axis)
            order = _clust.leaf_order(linkage_z)
        except _clust.ClusteringError as exc:
            warnings.append(f"{axis.capitalize()} clustering skipped: {exc}")
        except Exception as exc:  # pragma: no cover - defensive
            warnings.append(f"{axis.capitalize()} clustering skipped: {exc}")
    return order, linkage_z


def _shared_divider(ax):
    """The one divider for this axes, created once and reused.

    ``make_axes_locatable`` builds a fresh divider each call, and two dividers
    managing the same axes do not know about each other: the second one's space
    reservation overwrites the first's. With both a row and a column cluster bar
    the row bar ended up with no gap at all - its pad silently did nothing and it
    sat hard against the heatmap - while the column bar, appended last, worked.
    Each alone was fine, which is what made it look like a row-only bug.
    """
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    divider = getattr(ax, "_mmf_divider", None)
    if divider is None:
        divider = make_axes_locatable(ax)
        ax._mmf_divider = divider
    return divider


def _draw_column_annotations(fig, ax, annotations, ordered_cols, style, warnings) -> None:
    """Draw thin categorical color strips above the heatmap (one per track)."""
    divider = _shared_divider(ax)
    n = len(ordered_cols)
    for track in reversed(annotations):  # append from the top down
        label = str(track.get("label", "annotation"))
        values = track.get("values", {}) or {}
        cats = [str(values.get(c, "")) for c in ordered_cols]
        levels = [c for c in dict.fromkeys(cats) if c != ""]
        cmap_idx = {lv: i for i, lv in enumerate(levels)}
        strip = np.full((1, n), np.nan)
        for j, c in enumerate(cats):
            if c in cmap_idx:
                strip[0, j] = cmap_idx[c]
        cax = divider.append_axes("top", size="5%", pad=0.06)
        cax._colorbar = True  # decorative strip: skip the QA missing-label check
        cax.set_xlim(-0.5, n - 0.5)
        from matplotlib.colors import ListedColormap

        colors = [_ANNOT_PALETTE[i % len(_ANNOT_PALETTE)] for i in range(max(1, len(levels)))]
        cmap = ListedColormap(colors)
        cmap.set_bad("#EEEEEE")
        cax.imshow(strip, aspect="auto", cmap=cmap,
                   vmin=-0.5, vmax=max(0.5, len(levels) - 0.5), interpolation="nearest")
        cax.set_yticks([0]); cax.set_yticklabels([label], fontsize=max(7.0, style.tick_label_pt - 1))
        cax.set_xticks([])
        for spine in cax.spines.values():
            spine.set_visible(False)
        from matplotlib.patches import Patch

        handles = [Patch(facecolor=colors[i % len(colors)], label=lv) for i, lv in enumerate(levels)]
        if handles:
            # Place the category legend above the heatmap (aligned to the strip),
            # not on the right edge where it collides with the colorbar.
            cax.legend(handles=handles, title=label, loc="lower left",
                       bbox_to_anchor=(0.0, 1.3), ncol=min(len(levels), 4),
                       fontsize=max(6.5, style.legend_pt - 2),
                       title_fontsize=max(7.0, style.legend_pt - 1), frameon=False,
                       handlelength=1.0, borderpad=0.2, labelspacing=0.2, columnspacing=1.2)


def _cluster_palette_colors(name: str, style, *, offset_for_columns: bool = False):
    """Colours for the cluster bars: ``None`` keeps the clustering module's default.

    When both axes are clustered the column bars start further along the palette, so
    "Cluster 1" on the rows and "Cluster 1" on the columns are not the same colour -
    which is the only thing that made the two bars distinguishable at a glance.
    """
    from make_my_figure_core.styles.engine import NAMED_PALETTES

    if name in ("", "auto"):
        colors = None
    elif name == "style":
        colors = list(style.palette or [])
    else:
        colors = list(NAMED_PALETTES.get(name) or [])
    if not colors:
        if not offset_for_columns:
            return None
        from make_my_figure_core.clustering import CLUSTER_PALETTE
        colors = list(CLUSTER_PALETTE)
    if offset_for_columns and len(colors) > 3:
        shift = len(colors) // 2
        colors = colors[shift:] + colors[:shift]
    return colors


# Where a cluster legend may be placed, and the anchor each name maps to. Mirrors
# the colourbar's location control so the two behave alike.
# Measured against the example matrix: "left", "top" and "bottom" all put the key
# on top of the tick labels or the colourbar, so they are not offered. Adding them
# back needs the legend-placement work that reserves figure margin for an outside
# legend - see quality_audit/typography.md.
_CLUSTER_LEGEND_ANCHORS = {
    "right": ("upper left", (1.14, 1.0)),
    "right_lower": ("lower left", (1.14, 0.0)),
    "inside": ("best", None),
}


def _draw_cluster_strip(ax, side: str, cluster_ids_in_order: np.ndarray,
                        color_map: Dict[str, str], prefix: str, style, *,
                        legend: bool, legend_title: str = "Clusters",
                        width_pct: float = 4.0, pad: float = 0.06,
                        legend_location: str = "right",
                        legend_anchor_shift: float = 0.0,
                        legend_x_extra: float = 0.0,
                        another_legend_follows: bool = False,
                        labels_share_this_margin: bool = True,
                        show_strip_label: bool = True) -> None:
    """Draw a categorical cluster color strip beside the heatmap (left/top).

    Thickness, padding, colours, the strip's own label and the legend are all
    caller-controlled, so the cluster bars can be tuned the same way the colourbar
    can. Text sizes come from the style rather than from a floor of their own, so
    they follow the shared typography when the figure is resized.
    """
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    ordered_labels = sorted(color_map.keys(), key=lambda s: int(s.split()[-1]))
    idx_of = {lab: i for i, lab in enumerate(ordered_labels)}
    colors = [color_map[lab] for lab in ordered_labels]
    cmap = ListedColormap(colors)
    codes = np.array([idx_of[f"{prefix} {int(c)}"] for c in cluster_ids_in_order])
    divider = _shared_divider(ax)
    label_pt = style.tick_label_pt
    if side in ("left", "right"):
        cax = divider.append_axes(side, size=f"{width_pct:g}%", pad=pad)
        cax.imshow(codes.reshape(-1, 1), aspect="auto", cmap=cmap, interpolation="nearest")
        cax.set_xticks([]); cax.set_yticks([])
        # The divider reserves the space but knows nothing about the row labels,
        # which live in the same margin - so the bar was drawn straight over the
        # end of every gene name ("Gene_26" read as "Gene_ 6"). Push the labels
        # out past the bar and its gap. Both are fractions of the axes width, so
        # this is computed from the axes' own size in points.
        # Mind the units: ``size`` is a percentage of the axes width but ``pad``
        # is in INCHES. Treating both as fractions of the axes over-padded by
        # about 2x and took 71px of heatmap with it, crushing the column labels.
        if labels_share_this_margin:
            _ax_w_pts = ax.get_window_extent().width * 72.0 / ax.figure.dpi
            ax.tick_params(axis="y",
                           pad=(width_pct / 100.0) * _ax_w_pts + pad * 72.0 + 3.0)
        if show_strip_label:
            cax.set_xlabel(prefix, fontsize=label_pt, color=style.text_color)
    else:  # top or bottom
        cax = divider.append_axes(side, size=f"{width_pct:g}%", pad=pad)
        cax.imshow(codes.reshape(1, -1), aspect="auto", cmap=cmap, interpolation="nearest")
        cax.set_xticks([]); cax.set_yticks([])
        if show_strip_label:
            cax.set_ylabel(prefix, rotation=0, ha="right", va="center",
                           fontsize=label_pt)
    cax._colorbar = True
    for spine in cax.spines.values():
        spine.set_visible(False)
    if legend:
        loc, anchor = _CLUSTER_LEGEND_ANCHORS.get(
            legend_location, _CLUSTER_LEGEND_ANCHORS["right"])
        kwargs = {}
        if anchor is not None:
            # Two legends on the same side are stacked rather than drawn on top of
            # each other; legend_x_extra pushes past anything occupying the margin
            # (row labels moved to the right, and the colourbar beyond them).
            kwargs["bbox_to_anchor"] = (anchor[0] + legend_x_extra,
                                        anchor[1] - legend_anchor_shift)
        handles = [Patch(facecolor=color_map[lab], label=lab) for lab in ordered_labels]
        leg = ax.legend(handles=handles, title=legend_title, loc=loc,
                        fontsize=style.legend_pt, title_fontsize=style.legend_title_pt,
                        frameon=False, handlelength=1.0, borderpad=0.3,
                        labelspacing=0.3, **kwargs)
        if another_legend_follows:
            # ax.legend() replaces ax.legend_, which would drop this one; holding it
            # as a standalone artist lets rows and columns both be explained. Only
            # when a second legend follows - doing it unconditionally leaves the
            # legend both in ax.legend_ and in the child list, and it draws twice.
            ax.add_artist(leg)


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    import pandas as pd

    row_id = get_mapping(spec, "row_id", None)
    if not row_id:
        row_id = df.columns[0]
    require_columns(df, [row_id], context=PLOT_TYPE)

    cluster_rows = bool(get_mapping(spec, "cluster_rows", True))
    cluster_cols = bool(get_mapping(spec, "cluster_columns", True))
    color_scale = str(get_mapping(spec, "color_scale", "diverging"))
    scale = str(get_mapping(spec, "scale", "none"))
    metric = str(get_mapping(spec, "distance_metric", "euclidean"))
    method = str(get_mapping(spec, "linkage_method", "average"))
    k_rows = get_mapping(spec, "cluster_k_rows", None)
    k_cols = get_mapping(spec, "cluster_k_columns", None)
    sort_by_cluster = bool(get_mapping(spec, "sort_by_cluster", False))
    prefix = str(get_mapping(spec, "cluster_prefix", "Cluster"))
    # Cluster-bar appearance, deliberately mirroring the colourbar controls so the
    # two annotation elements are tuned the same way.
    cluster_strip_width = float(get_mapping(spec, "cluster_strip_width", 4.0) or 4.0)
    cluster_strip_pad = float(get_mapping(spec, "cluster_strip_pad", 0.06) or 0.0)
    cluster_palette = str(get_mapping(spec, "cluster_palette", "auto")).lower()
    cluster_legend = str(get_mapping(spec, "cluster_legend", "auto")).lower()
    cluster_legend_location = str(
        get_mapping(spec, "cluster_legend_location", "right")).lower()
    # Off by default. The key already says "Rows"/"Columns" above "Cluster 1,
    # 2, 3", so writing "Cluster" beside each bar as well says it a third time -
    # and it lands on top of the axis labels, which is where it was reported from.
    cluster_strip_labels = bool(get_mapping(spec, "cluster_strip_labels", False))
    # Which edge each cluster bar sits on. The row labels already move; the bar
    # should too, so an author can put the bar and the names on opposite sides
    # instead of stacking them in one margin.
    row_bar_side = str(get_mapping(spec, "row_cluster_bar_side", "left")).lower()
    col_bar_side = str(get_mapping(spec, "column_cluster_bar_side", "top")).lower()
    if row_bar_side not in ("left", "right"):
        row_bar_side = "left"
    if col_bar_side not in ("top", "bottom"):
        col_bar_side = "top"
    # Which edge the tick labels sit on. With a row cluster bar on the left, the
    # labels, the bar and the tick marks all compete for the same margin and the
    # marks end up orphaned between the bar and the heatmap. Putting the labels
    # on the right - the usual clustermap arrangement - leaves the bar flush
    # against the data where it belongs.
    row_label_side = str(get_mapping(spec, "row_label_side", "left")).lower()
    col_label_side = str(get_mapping(spec, "column_label_side", "bottom")).lower()
    highlight_rows = {str(s).strip().lower() for s in (get_mapping(spec, "highlight_rows", None) or [])}
    highlight_cols = {str(s).strip().lower() for s in (get_mapping(spec, "highlight_columns", None) or [])}
    show_row_labels = get_mapping(spec, "show_row_labels", None)
    show_col_labels = get_mapping(spec, "show_col_labels", None)
    exclude_cols = {str(c) for c in (get_mapping(spec, "exclude_columns", None) or [])}
    value_columns = get_mapping(spec, "value_columns", None)
    max_features = int(get_mapping(spec, "max_features", _clust.DEFAULT_MAX_CLUSTER_FEATURES))
    # Vertical separators between sample groups (from column_groups mapping or the
    # first column-annotation track). 'auto' = on when groups are known.
    group_separators = get_mapping(spec, "group_separators", None)
    column_groups = get_mapping(spec, "column_groups", None)
    cell_borders = get_mapping(spec, "cell_borders", None)   # None = auto (small matrices)
    # User-controllable cell grid + group-separator styling (catchy publication look).
    cell_border_color = str(get_mapping(spec, "cell_border_color", "white"))
    cell_border_width = float(get_mapping(spec, "cell_border_width", 0.6))
    group_sep_color = str(get_mapping(spec, "group_separator_color", "#222222"))
    group_sep_width = float(get_mapping(spec, "group_separator_width", 1.6))

    work = df.copy()
    row_labels = work[row_id].astype(str).tolist()
    warnings: List[str] = []
    # Sample columns = every non-id column that is numeric and not excluded.
    # RNA-seq matrices often carry annotation columns (geneSymbol/bioType/
    # annotationLevel) before the samples — drop non-numeric ones automatically
    # and let the user exclude numeric-looking annotation columns explicitly.
    from make_my_figure_core.plots._v04_shared import resolve_value_columns

    candidate_cols = [c for c in work.columns if c != row_id and str(c) not in exclude_cols]
    numeric = work[candidate_cols].apply(lambda s: pd.to_numeric(s, errors="coerce"))
    numeric_cols = [c for c in candidate_cols if numeric[c].notna().any()]
    if not numeric_cols:
        raise RenderError(f"{PLOT_TYPE}: no numeric sample columns besides row id '{row_id}'.")
    # Keep only per-sample VALUE columns: drop integer-coded annotation columns
    # (e.g. annotationLevel in {1,2,3}) that are numeric but not measurements,
    # honouring an explicit value-column selection when given.
    sample_cols = resolve_value_columns(work, numeric_cols, value_columns=value_columns,
                                        warnings=warnings)
    dropped = [c for c in work.columns if c != row_id and c not in sample_cols]
    if dropped:
        warnings.insert(0, f"Ignored non-sample column(s): {dropped}.")
    warnings.append(f"Using {len(sample_cols)} value column(s): {list(sample_cols)}. "
                    "If this is wrong, select value columns explicitly (or use 'exclude_columns').")
    raw_matrix = numeric[sample_cols].to_numpy(dtype=float)
    if np.isnan(raw_matrix).any():
        warnings.append("Matrix contains missing/non-numeric values; shown as blank cells.")

    # Memory guard: cap the feature (row) axis before the O(n^2) clustering so a
    # huge matrix (e.g. 55k genes) can't exhaust RAM. Highlighted rows are kept.
    keep_labels = set(highlight_rows)
    raw_matrix, row_labels, _cap_idx = _clust.cap_rows_by_variance(
        raw_matrix, row_labels, max_features, warnings, keep_labels=keep_labels)

    # Nudge: unscaled raw-count-like matrices (large, non-negative, wide dynamic
    # range) render as a washed-out block. Suggest a readable scale.
    if scale == "none":
        finite = raw_matrix[np.isfinite(raw_matrix)]
        if finite.size:
            mx = float(np.nanmax(finite))
            if float(np.nanmin(finite)) >= 0 and mx >= 1000 and mx > 50 * (float(np.nanmedian(finite)) + 1):
                warnings.append(
                    "Large non-negative values with a wide dynamic range (looks like raw "
                    "counts): set Scale to 'log_zscore' (or 'row_zscore' / 'log') for a "
                    "readable heatmap — 'none' will look washed out.")

    # Scaling (default 'none' reproduces the original output).
    matrix, scale_warns = _clust.scale_matrix(raw_matrix, scale)
    warnings.extend(scale_warns)

    col_labels = list(sample_cols)
    filled = np.nan_to_num(matrix, nan=0.0)

    row_order, row_linkage = _order_and_linkage(filled, "rows", method, metric, cluster_rows, warnings)
    col_order, col_linkage = _order_and_linkage(filled, "columns", method, metric, cluster_cols, warnings)

    # --- k-cluster cuts (optional) ---
    row_cluster_ids = col_cluster_ids = None
    row_color_map = col_color_map = None
    meta_extra: Dict[str, Any] = {}
    if k_rows and row_linkage is not None:
        try:
            row_cluster_ids = _clust.cut_k(row_linkage, int(k_rows), raw_matrix.shape[0])
            row_color_map = _clust.cluster_color_map(
                row_cluster_ids, prefix, palette=_cluster_palette_colors(
                    cluster_palette, style))
            tbl = _clust.assignment_table(row_labels, row_cluster_ids, row_order,
                                          id_name="feature",
                                          values=np.nanmean(raw_matrix, axis=1))
            meta_extra["row_assignment"] = tbl.to_dict(orient="records")
            meta_extra["row_clusters"] = _clust.cluster_summary(
                row_cluster_ids, method=method, metric=metric, scale=scale,
                k=int(k_rows), axis="rows", warnings=[])
        except _clust.ClusteringError as exc:
            warnings.append(f"Row k-clustering skipped: {exc}")
    if k_cols and col_linkage is not None:
        try:
            col_cluster_ids = _clust.cut_k(col_linkage, int(k_cols), raw_matrix.shape[1])
            col_color_map = _clust.cluster_color_map(
                col_cluster_ids, prefix, palette=_cluster_palette_colors(
                    cluster_palette, style, offset_for_columns=True))
            tbl = _clust.assignment_table(col_labels, col_cluster_ids, col_order,
                                          id_name="sample")
            meta_extra["column_assignment"] = tbl.to_dict(orient="records")
            meta_extra["column_clusters"] = _clust.cluster_summary(
                col_cluster_ids, method=method, metric=metric, scale=scale,
                k=int(k_cols), axis="columns", warnings=[])
        except _clust.ClusteringError as exc:
            warnings.append(f"Column k-clustering skipped: {exc}")

    # Optionally group by cluster (stable within cluster by dendrogram order).
    if sort_by_cluster and row_cluster_ids is not None:
        pos = {leaf: i for i, leaf in enumerate(row_order)}
        row_order = sorted(range(raw_matrix.shape[0]),
                           key=lambda i: (int(row_cluster_ids[i]), pos.get(i, i)))
    if sort_by_cluster and col_cluster_ids is not None:
        pos = {leaf: i for i, leaf in enumerate(col_order)}
        col_order = sorted(range(raw_matrix.shape[1]),
                           key=lambda j: (int(col_cluster_ids[j]), pos.get(j, j)))

    # Column grouping: order columns by group so groups are contiguous, and record
    # boundaries for vertical separator lines (group source: column_groups mapping
    # or the first column-annotation track). 'auto' turns on when groups exist.
    col_group_boundaries: List[int] = []
    _group_map = None
    if isinstance(column_groups, dict) and column_groups:
        _group_map = {str(k): str(v) for k, v in column_groups.items()}
    else:
        _ann = spec.get("column_annotations") or []
        if _ann and (_ann[0].get("values")):
            _group_map = {str(k): str(v) for k, v in (_ann[0]["values"] or {}).items()}
    # True = always, False = never, None/auto = whenever there is a grouping to
    # show (an explicit map, an annotation track, or a cluster cut).
    _want_sep = (False if group_separators is False
                 else (True if group_separators is True else None))
    if _group_map and _want_sep is not False:
        def _grp(j):
            return _group_map.get(col_labels[j], "")
        seen = list(dict.fromkeys(_grp(j) for j in range(len(col_labels))))
        rank = {g: i for i, g in enumerate(seen)}
        posc = {leaf: i for i, leaf in enumerate(col_order)}
        col_order = sorted(range(len(col_labels)),
                           key=lambda j: (rank.get(_grp(j), 0), posc.get(j, j)))
        og = [_grp(j) for j in col_order]
        col_group_boundaries = [i for i in range(1, len(og)) if og[i] != og[i - 1]]

    # Cutting into k clusters IS a grouping, so it should get the same separator
    # lines an explicit column_groups mapping does. Without this the three
    # separator controls were dead for the common case - clustering on, no
    # annotation track - which is how they were reported: ticked, coloured,
    # widened, and nothing drawn.
    row_group_boundaries: List[int] = []
    if _want_sep is not False:
        if not col_group_boundaries and col_cluster_ids is not None:
            _oc = [int(col_cluster_ids[j]) for j in col_order]
            col_group_boundaries = [i for i in range(1, len(_oc))
                                    if _oc[i] != _oc[i - 1]]
        if row_cluster_ids is not None:
            _orow = [int(row_cluster_ids[i]) for i in row_order]
            row_group_boundaries = [i for i in range(1, len(_orow))
                                    if _orow[i] != _orow[i - 1]]

    ordered = matrix[np.ix_(row_order, col_order)]
    ordered_rows = [row_labels[i] for i in row_order]
    ordered_cols = [col_labels[j] for j in col_order]

    finite = matrix[np.isfinite(matrix)]
    _centering_scale = scale in ("row_zscore", "column_zscore", "center_rows", "log_zscore")
    # A diverging map only makes sense for data centred on zero (z-scores / log
    # ratios). For raw, all-positive values a diverging map washes to one tone —
    # the "monotone heatmap" complaint — so fall back to sequential + robust limits.
    _is_centred = _centering_scale or (finite.size > 0 and finite.min() < 0.0 < finite.max())
    if color_scale == "diverging" and _is_centred:
        cmap = style.diverging_cmap
        vmax = np.nanmax(np.abs(matrix)) if finite.size else 1.0
        vmin, vmax = -vmax, vmax
    else:
        cmap = style.sequential_cmap
        # Robust (2nd–98th percentile) limits so a few extreme cells don't flatten
        # the map. Falls back to full range if the spread is degenerate.
        if finite.size:
            lo, hi = float(np.nanpercentile(finite, 2)), float(np.nanpercentile(finite, 98))
            full_lo, full_hi = float(finite.min()), float(finite.max())
            vmin, vmax = (lo, hi) if hi > lo else (full_lo, full_hi)
            if color_scale == "diverging" and not _is_centred:
                warnings.append("Values are not centred on zero — using a sequential colour "
                                "map with robust limits. Set a scale (e.g. row_zscore) for a "
                                "centred diverging map.")
            elif scale == "none" and hi > lo and (lo > full_lo or hi < full_hi):
                warnings.append("Colour scaled to the 2nd–98th percentile for contrast "
                                "(extreme cells saturate).")
        else:
            vmin, vmax = 0.0, 1.0

    # Explicit publication colormap override (wins over the palette/scale default).
    _explicit_cmap = get_mapping(spec, "colormap", None)
    if _explicit_cmap and str(_explicit_cmap).lower() not in ("", "auto"):
        cmap = str(_explicit_cmap)

    def _label_fs(n: int) -> float:
        if n <= 15:
            return style.tick_label_pt
        if n <= 30:
            return max(7.0, style.tick_label_pt - 1)
        if n <= 60:
            return max(6.0, style.tick_label_pt - 3)
        return 0.0  # hide

    col_fs = _label_fs(len(ordered_cols))
    row_fs = _label_fs(len(ordered_rows))
    # Explicit overrides.
    if show_row_labels is True and row_fs == 0:
        row_fs = max(6.0, style.tick_label_pt - 3)
    if show_row_labels is False:
        row_fs = 0.0
    if show_col_labels is True and col_fs == 0:
        col_fs = max(6.0, style.tick_label_pt - 3)
    if show_col_labels is False:
        col_fs = 0.0
    # Explicit font-size controls (0 = keep auto/hidden decision above).
    _rlf = get_mapping(spec, "row_label_fontsize", None)
    if _rlf:
        row_fs = float(_rlf)
    _clf = get_mapping(spec, "col_label_fontsize", None)
    if _clf:
        col_fs = float(_clf)
    if len(highlight_rows) > 60:
        warnings.append(f"{len(highlight_rows)} highlighted rows requested; consider fewer for legibility.")

    n_c = len(ordered_cols)
    n_r = len(ordered_rows)
    col_annotations = spec.get("column_annotations") or []

    layout = spec.get("layout", {}) or {}
    width_preset = str(layout.get("column_width", "default")).lower()
    w_in, _ = style.figure_size_inches(width_preset, aspect=1.0)
    if n_c > 14:
        w_in *= min(1.5, 1.0 + 0.02 * (n_c - 14))
    if row_fs > 0 and n_r > 12:
        target_h = 1.6 + 0.16 * n_r
    else:
        target_h = w_in * (0.95 if n_c <= 14 else 1.15)
    target_h += 0.5 * len(col_annotations)
    target_h = max(target_h, w_in * 0.6)
    # An explicit numeric layout['aspect'] is an instruction about the panel shape (for
    # example to fit a multi-panel grid) and takes precedence over the row-count heuristic,
    # exactly as figure_size() treats it for the other plot types.
    try:
        _explicit_aspect = float(layout.get("aspect"))
    except (TypeError, ValueError):
        _explicit_aspect = None
    if _explicit_aspect and _explicit_aspect > 0:
        target_h = w_in * _explicit_aspect
    # Cluster bars live in the margin, and the margin is taken out of the axes -
    # so switching them on narrowed the heatmap until its column labels no longer
    # fitted (measured: 268.6 -> 175.3 px wide, dropping vertical label spacing
    # to 14.6 px where 10 pt text needs 15.3). Ask for the extra inches instead,
    # so the bars cost canvas rather than data. The bar is a percentage of the
    # axes; the pad and the label clearance are inches.
    _bar_in = cluster_strip_width / 100.0 * w_in + cluster_strip_pad
    if row_color_map is not None:
        w_in += _bar_in + 0.08
    if col_color_map is not None:
        target_h += _bar_in + 0.08
    figsize = (w_in, min(target_h, 22.0))

    with style.apply():
        figsize = resolve_figure_size(spec, figsize)
        fig, ax = plt.subplots(figsize=figsize)
        im = ax.imshow(ordered, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax,
                       interpolation="nearest")
        # Thin cell separators (auto for small matrices; a clean publication touch).
        show_cells = cell_borders if cell_borders is not None else (n_r <= 40 and n_c <= 40)
        if show_cells and cell_border_width > 0:
            ax.set_xticks(np.arange(-0.5, n_c, 1), minor=True)
            ax.set_yticks(np.arange(-0.5, n_r, 1), minor=True)
            ax.grid(which="minor", color=cell_border_color, linewidth=cell_border_width)
            ax.tick_params(which="minor", length=0)
        # Bolder vertical separators between sample groups (controllable colour/width).
        for b in col_group_boundaries:
            ax.axvline(b - 0.5, color=group_sep_color, linewidth=group_sep_width)
        for b in row_group_boundaries:
            ax.axhline(b - 0.5, color=group_sep_color, linewidth=group_sep_width)
        # Cluster color strips (drawn first so their divider axes sit outside).
        # Which cluster legends to draw. 'auto' explains whichever axes are
        # clustered - with both, each gets its own named legend, because a single
        # "Clusters" legend cannot say whether a colour means a row or a column.
        _both = row_color_map is not None and col_color_map is not None
        if cluster_legend == "auto":
            # One legend by default. Two on the right need more width than the
            # figure has, and squeezing the heatmap to fit them is the worse
            # trade - ask for "both" to get them, and widen the figure to suit.
            _legend_rows = row_color_map is not None
            _legend_cols = col_color_map is not None and row_color_map is None
        else:
            _legend_rows = cluster_legend in ("rows", "both")
            _legend_cols = cluster_legend in ("columns", "both")
        if _both and cluster_legend == "auto":
            warnings.append(
                "Rows and columns are both clustered; only the row cluster key is "
                "shown, because two keys need more width than the figure has. The "
                "column bars use a shifted palette so they are still "
                "distinguishable. Set 'Cluster legend' to 'both' (and widen the "
                "figure) to show both keys.")
        # "Rows"/"Columns" rather than "Row clusters"/"Column clusters": the entries
        # below already say "Cluster 1", and the longer title is wide enough to be
        # clipped at the default figure width.
        _row_title = "Rows" if _both else f"{prefix}s"
        _col_title = "Columns" if _both else f"{prefix}s"
        # With the row labels on the right the key has to clear both them and the
        # colourbar, or it lands on the names - which is what moving the labels
        # was meant to stop.
        _legend_x_extra = 0.0
        if row_label_side == "right" and row_fs > 0:
            _longest_row = max((len(str(r)) for r in ordered_rows), default=6)
            # 0.14 covers the colourbar's own width plus its pad. Not read from
            # cb_pad: that is computed further down, after the strips are drawn.
            _legend_x_extra = min(1.2, _longest_row * 0.6 * row_fs / 72.0
                                  / max(0.6 * w_in, 0.5) + 0.14)
        _stack = 0.0
        if row_color_map is not None:
            _draw_cluster_strip(
                ax, row_bar_side, row_cluster_ids[row_order], row_color_map,
                prefix, style,
                labels_share_this_margin=(row_bar_side == row_label_side),
                legend=_legend_rows, legend_title=_row_title,
                width_pct=cluster_strip_width, pad=cluster_strip_pad,
                legend_location=cluster_legend_location,
                another_legend_follows=_legend_rows and _legend_cols,
                legend_x_extra=_legend_x_extra,
                show_strip_label=cluster_strip_labels)
            if _legend_rows:
                _stack = 0.1 + 0.075 * len(row_color_map)
        if col_color_map is not None:
            _draw_cluster_strip(
                ax, col_bar_side, col_cluster_ids[col_order], col_color_map,
                prefix, style,
                legend=_legend_cols, legend_title=_col_title,
                width_pct=cluster_strip_width, pad=cluster_strip_pad,
                legend_location=cluster_legend_location,
                legend_x_extra=_legend_x_extra,
                legend_anchor_shift=_stack,
                show_strip_label=cluster_strip_labels)
        if col_annotations:
            _draw_column_annotations(fig, ax, col_annotations, ordered_cols, style, warnings)

        # --- row tick labels (+ highlighting) ---
        if row_label_side == "right":
            # Labels and their marks move together; the left margin is then the
            # cluster bar's alone, so the clearance added for it is not needed.
            # Tick labels and their marks move; the AXIS label stays on the left.
            # Sent right with them it ends up behind the colourbar, and it reads
            # perfectly well on the left - which is where every clustermap of this
            # shape puts it.
            ax.yaxis.tick_right()
            # Set the pad HERE, not in the strip helper: this block runs after
            # the strips are drawn and would otherwise overwrite their clearance,
            # which is what put the labels back on top of a right-hand bar.
            _label_pad = 2.0
            if row_color_map is not None and row_bar_side == "right":
                _ax_w_pts = ax.get_window_extent().width * 72.0 / ax.figure.dpi
                _label_pad = ((cluster_strip_width / 100.0) * _ax_w_pts
                              + cluster_strip_pad * 72.0 + 3.0)
            ax.tick_params(axis="y", pad=_label_pad)
        if col_label_side == "top":
            ax.xaxis.tick_top()
            ax.xaxis.set_label_position("top")
        hl_row_pos = [i for i, lab in enumerate(ordered_rows) if lab.lower() in highlight_rows]
        if row_fs > 0:
            ax.set_yticks(range(len(ordered_rows)))
            ax.set_yticklabels(ordered_rows, fontsize=row_fs)
            for i in hl_row_pos:
                ax.get_yticklabels()[i].set_fontweight("bold")
                ax.get_yticklabels()[i].set_color("#B2182B")
        elif hl_row_pos:  # labels hidden globally, but show highlighted ones
            ax.set_yticks(hl_row_pos)
            ax.set_yticklabels([ordered_rows[i] for i in hl_row_pos],
                               fontsize=max(7.0, style.tick_label_pt - 2), fontweight="bold",
                               color="#B2182B")
        else:
            ax.set_yticks([])
            if n_r > 60:
                warnings.append(f"{len(ordered_rows)} rows: row labels hidden for legibility.")

        # --- column tick labels (+ highlighting) ---
        hl_col_pos = [j for j, lab in enumerate(ordered_cols) if lab.lower() in highlight_cols]
        if col_fs > 0:
            ax.set_xticks(range(len(ordered_cols)))
            ax.set_xticklabels(ordered_cols, rotation=90, fontsize=col_fs)
            for j in hl_col_pos:
                ax.get_xticklabels()[j].set_fontweight("bold")
                ax.get_xticklabels()[j].set_color("#B2182B")
        elif hl_col_pos:
            ax.set_xticks(hl_col_pos)
            ax.set_xticklabels([ordered_cols[j] for j in hl_col_pos], rotation=90,
                               fontsize=max(7.0, style.tick_label_pt - 2), fontweight="bold",
                               color="#B2182B")
        else:
            ax.set_xticks([])
            if n_c > 60:
                warnings.append(f"{len(ordered_cols)} columns: labels hidden for legibility.")

        ax.set_xlabel(spec.get("layout", {}).get("x_label", "Sample"))
        _yrot = 0 if str(get_mapping(spec, "y_label_rotation", "vertical")).lower() in ("horizontal", "0") else 90
        ax.set_ylabel(spec.get("layout", {}).get("y_label", str(row_id)),
                      rotation=_yrot, ha=("right" if _yrot == 0 else "center"), va="center")
        # Y-axis-label padding so the label never crowds long row names (user control).
        ax.yaxis.labelpad = float(get_mapping(spec, "y_label_pad",
                                              layout.get("y_label_pad", 6.0)) or 6.0)
        title = spec.get("layout", {}).get("title")
        if title:
            if col_annotations or col_color_map is not None:
                fig.suptitle(title, fontsize=style.title_font_pt,
                             fontweight=getattr(style, "title_font_weight", "bold"))
            else:
                ax.set_title(title)
        # Colorbar position/size are user-configurable (location: right/left/top/bottom).
        cb_loc = str(get_mapping(spec, "colorbar_location", layout.get("colorbar_location", "right"))).lower()
        if cb_loc not in ("right", "left", "top", "bottom"):
            cb_loc = "right"
        cb_frac = float(get_mapping(spec, "colorbar_fraction", layout.get("colorbar_fraction", 0.045)) or 0.045)
        # A colourbar needs a larger default pad whenever tick labels sit on the
        # same edge, or it lands on top of them. Top/bottom bars have always had
        # to clear the column labels; a right-hand bar has to clear the ROW labels
        # once they are moved to the right, which is what that option does.
        _labels_on_cb_edge = (
            (cb_loc in ("bottom", "top") and col_fs > 0)
            or (cb_loc == "right" and row_label_side == "right" and row_fs > 0)
            or (cb_loc == "left" and row_label_side == "left" and row_fs > 0))
        if cb_loc == "right" and row_label_side == "right" and row_fs > 0:
            # Scaled to the longest name rather than a flat guess: "Gene_26" and
            # a 40-character probe id need very different room.
            _longest = max((len(str(r)) for r in ordered_rows), default=6)
            _label_in = _longest * 0.6 * row_fs / 72.0
            # ``pad`` is a fraction of the AXES width, not the figure's - dividing
            # by the figure width left the bar ~40% short and still on the labels.
            # The axes is roughly 60% of the canvas once margins and the colourbar
            # are taken out; good enough for a default the user can override.
            _default_pad = min(0.6, 0.04 + _label_in / max(0.6 * w_in, 0.5))
        else:
            _default_pad = 0.18 if _labels_on_cb_edge else 0.03
        cb_pad = float(get_mapping(spec, "colorbar_pad", layout.get("colorbar_pad", _default_pad)) or _default_pad)
        cb_shrink = float(get_mapping(spec, "colorbar_shrink", layout.get("colorbar_shrink", 1.0)) or 1.0)
        cbar = fig.colorbar(im, ax=ax, location=cb_loc, fraction=cb_frac, pad=cb_pad,
                            shrink=cb_shrink)
        cbar.ax.tick_params(labelsize=style.tick_label_pt, width=style.tick_width,
                            length=style.tick_length)
        cbar.outline.set_linewidth(style.spine_width_pt)
        default_cbar = "z-score" if scale in ("row_zscore", "column_zscore", "log_zscore") else "value"
        cbar.set_label(spec.get("layout", {}).get("colorbar_label", default_cbar),
                       fontsize=style.axis_font_pt)
        for spine in ax.spines.values():
            spine.set_visible(False)
        fig.tight_layout()

        # The label sizes above are chosen from a row/column count, which cannot
        # know how much room a row actually has: at presentation type sizes 30
        # gene labels were set at 13 pt into rows 12 pt tall, so every one
        # overlapped its neighbour and the longest ran under the y axis label.
        # Measure now that the axes are laid out, and shrink only if they really
        # collide. tight_layout runs again so the axis labels clear whatever size
        # the ticks ended up at.
        _before = (row_fs, col_fs)
        if row_fs:
            row_fs = fit_tick_labels(ax, "y") or row_fs
        if col_fs:
            col_fs = fit_tick_labels(ax, "x") or col_fs
        if (row_fs, col_fs) != _before:
            fig.tight_layout()
        # The axis label sits a fixed number of points from the axis, which cannot
        # account for the longest tick label; "gene_symbol" ran under six of them.
        clear_axis_label(ax, "y")
        clear_axis_label(ax, "x")

    meta = base_metadata(spec, style, work, used_columns=[row_id] + sample_cols)
    meta["matrix_shape"] = [int(raw_matrix.shape[0]), int(raw_matrix.shape[1])]
    meta["clustered_rows"] = cluster_rows and row_order != list(range(raw_matrix.shape[0]))
    meta["clustered_columns"] = cluster_cols and col_order != list(range(raw_matrix.shape[1]))
    meta["color_scale"] = color_scale
    meta["scale"] = scale
    meta["distance_metric"] = metric
    meta["linkage_method"] = method
    meta.update(meta_extra)
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
