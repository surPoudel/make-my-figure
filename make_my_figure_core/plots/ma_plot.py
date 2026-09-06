"""MA plot for differential expression (RNA-seq / proteomics).

x-axis: average abundance/expression (A). y-axis: log fold change (M). Points
are colored by significance using a p-value/FDR column read **verbatim** — the
app never recomputes statistics. Optionally labels the top features by absolute
fold change among the significant hits.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots._v04_shared import pick_column
from make_my_figure_core.plots.base import (
    RenderError,
    RenderResult,
    apply_publication_layout,
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

PLOT_TYPE = "ma_plot"

_X_ALIASES = ["AveExpr", "baseMean", "logCPM", "mean_expression", "abundance", "avgexpr",
              "average_expression"]
_Y_ALIASES = ["logFC", "log2FoldChange", "log2FC", "LFC", "log2_fold_change"]
_P_ALIASES = ["adj.P.Val", "padj", "FDR", "qvalue", "adjusted_p_value", "P.Value", "pvalue", "p_value"]
_LABEL_ALIASES = ["geneSymbol", "symbol", "gene", "gene_id", "gene_symbol", "feature"]


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", None) or pick_column(df, _X_ALIASES)
    y = get_mapping(spec, "y", None) or pick_column(df, _Y_ALIASES)
    p = get_mapping(spec, "p", None) or pick_column(df, _P_ALIASES)
    label_col = get_mapping(spec, "label", None) or pick_column(df, _LABEL_ALIASES)
    id_col = get_mapping(spec, "id_col", None) or pick_column(df, ["feature_id", "peptide_id", "transcript_id", "probe_id"])
    p_cutoff = float(get_mapping(spec, "p_cutoff", 0.05))
    # Optional |log fold change| cutoff (0 = significance by p/FDR alone, the historical default).
    # Lets an MA plot follow a published definition such as "padj < 0.05 and |FC| > 1.5".
    lfc_cutoff = float(get_mapping(spec, "lfc_cutoff", 0.0) or 0.0)
    label_top_n = int(get_mapping(spec, "label_top_n", 8))

    # Duplicate-label handling (shared with the volcano plot).
    from make_my_figure_core.plots import label_policy as lp
    dup_policy = lp.normalize_policy(get_mapping(spec, "duplicate_label_policy", "all"))
    dup_rule = lp.normalize_rule(get_mapping(spec, "duplicate_label_representative_rule", "pvalue"))
    dup_show_count = bool(get_mapping(spec, "duplicate_label_show_count", False))
    selected_points = [str(s) for s in (get_mapping(spec, "selected_points", None) or [])]
    adj_col = get_mapping(spec, "adj_p", None) or get_mapping(spec, "padj", None)
    stat_col = get_mapping(spec, "statistic", None) or get_mapping(spec, "stat", None)

    if not x or not y:
        raise RenderError(
            f"{PLOT_TYPE}: could not find average-expression and log-fold-change columns. "
            f"Map 'x' (e.g. AveExpr/baseMean/logCPM) and 'y' (e.g. logFC/log2FoldChange). "
            f"Available columns: {list(df.columns)}")
    require_columns(df, [x, y], context=PLOT_TYPE)

    work = df.copy()
    work[x] = coerce_numeric(work, x, context=PLOT_TYPE)
    work[y] = coerce_numeric(work, y, context=PLOT_TYPE)
    warnings: List[str] = []

    xs = work[x].to_numpy(float)
    ys = work[y].to_numpy(float)
    if p and p in work.columns:
        pv = coerce_numeric(work, p, context=PLOT_TYPE).to_numpy(float)
    else:
        pv = np.full(len(work), np.nan)
        warnings.append("No p-value/FDR column found; all points shown as non-significant.")

    sig = np.isfinite(pv) & (pv <= p_cutoff)
    if lfc_cutoff > 0:
        sig = sig & (np.abs(ys) >= lfc_cutoff)
    up = sig & (ys > 0)
    down = sig & (ys < 0)
    ns = ~sig

    mk = dict(s=style.marker_size, edgecolors="white",
              linewidths=style.marker_edge_width, alpha=style.marker_alpha)
    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.72))
        ax.axhline(0.0, color=style.text_color, lw=style.spine_width_pt, zorder=1)
        if ns.any():
            ns_color = str(get_mapping(spec, "color_ns", "#B8B8B8") or "#B8B8B8")
            ax.scatter(xs[ns], ys[ns], color=ns_color, label="Not sig.", zorder=2, **mk)
        if up.any():
            ax.scatter(xs[up], ys[up], color=style.color_for(1), label="Up", zorder=3, **mk)
        if down.any():
            ax.scatter(xs[down], ys[down], color=style.color_for(0), label="Down", zorder=3, **mk)

        # Labels: explicit click-selected points, then legacy text selections, then the
        # strongest significant hits by |logFC| — all routed through the shared
        # duplicate-label policy so rows sharing a gene symbol stay independent.
        selected_set = {str(s).strip().lower() for s in
                        (get_mapping(spec, "selected_labels", None) or [])}
        n_labeled = 0
        if label_col and label_col in work.columns and sig.any():
            import pandas as pd

            sig_series = pd.Series(sig, index=work.index)
            label_series = work[label_col].astype(str).str.strip()
            has_text = (label_series.ne("") & label_series.str.lower().ne("nan")
                        & work[label_col].notna())

            def _text_fn(i):
                return str(work.at[i, label_col]).strip()

            rep_columns = {"pvalue": p, "padj": adj_col, "effect": y, "statistic": stat_col}
            total_counts = lp.total_label_counts(work.loc[has_text, label_col])

            def _pts(ranked, *, policy, limit=None):
                return lp.build_label_points(
                    work, ranked, label_series=label_series, text_fn=_text_fn,
                    x_col=x, y_col=y, id_col=id_col, policy=policy,
                    representative_rule=dup_rule, show_count=dup_show_count,
                    rep_columns=rep_columns, limit=limit, total_counts=total_counts)

            explicit_pts: List = []
            if selected_points:
                want = set(selected_points)
                sel_idx = [work.index[k] for k in range(len(work))
                           if lp.point_id_for(work, work.index[k], id_col) in want]
                explicit_pts = _pts(sel_idx, policy="all")

            text_pts: List = []
            if selected_set:
                sel = work[label_series.str.lower().isin(selected_set) & has_text]
                ranked = list(sel.reindex(sel[y].abs().sort_values(ascending=False).index).index)
                text_pts = _pts(ranked, policy=dup_policy)

            mode_pts: List = []
            if not selected_set and not selected_points and label_top_n > 0:
                sig_frame = work[sig_series & has_text]
                ranked = list(sig_frame.reindex(
                    sig_frame[y].abs().sort_values(ascending=False).index).index)
                mode_pts = _pts(ranked, policy=dup_policy, limit=label_top_n)

            label_points: List = []
            seen_pid: set = set()
            for pt in (explicit_pts + text_pts + mode_pts):
                if pt.point_id in seen_pid:
                    continue
                seen_pid.add(pt.point_id)
                label_points.append(pt)

            point_offsets = lp.parse_offsets(get_mapping(spec, "point_offsets", None))
            legacy_offsets = lp.parse_offsets(get_mapping(spec, "label_offsets", None))
            for pt in label_points:
                off = point_offsets.get(pt.point_id)
                if off is None:
                    off = (legacy_offsets.get(pt.label_text)
                           or legacy_offsets.get(str(pt.label_text).lower()) or (4, 4))
                dx, dy = float(off[0]), float(off[1])
                ax.annotate(pt.label_text, (pt.anchor_x, pt.anchor_y),
                            fontsize=style.annotation_pt,
                            xytext=(dx, dy), textcoords="offset points",
                            arrowprops=dict(arrowstyle="-", color="0.6", lw=0.5)
                            if (abs(dx) > 12 or abs(dy) > 12) else None)
            n_labeled = len(label_points)

        ax.set_xlabel(spec.get("layout", {}).get("x_label", "Average expression"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", "log2 fold change"))
        ax.margins(0.05)
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)
        place_legend(ax, style, title="Significance",
                     location=resolve_legend_location(spec, style)
                     if spec.get("layout", {}).get("legend_location") else None,
                     force_outside=not spec.get("layout", {}).get("legend_location"))
        apply_publication_layout(fig, ax, spec, style)

    meta = base_metadata(spec, style, work, used_columns=[x, y, p, label_col])
    meta["n_up"] = int(up.sum())
    meta["n_down"] = int(down.sum())
    meta["n_ns"] = int(ns.sum())
    meta["p_cutoff"] = p_cutoff
    meta["lfc_cutoff"] = lfc_cutoff
    meta["n_labeled"] = n_labeled
    meta["duplicate_label_policy"] = dup_policy
    meta["duplicate_label_representative_rule"] = dup_rule
    meta["duplicate_label_show_count"] = dup_show_count
    # Click-identify support (parity with volcano): map a canvas click back to a point.
    try:
        from make_my_figure_core.plots.base import (
            build_pickable_points, choose_label_column, resolve_point_labels)

        pick_col = choose_label_column(work, [label_col, "gene", "gene_symbol", "symbol", id_col])
        point_ids = [lp.point_id_for(work, idx, id_col) for idx in work.index]
        meta["pickable_points"] = build_pickable_points(
            xs, ys, resolve_point_labels(work, pick_col), point_ids=point_ids)
        meta["pick_label_key"] = "selected_points"
        meta["pick_offset_key"] = "point_offsets"
        meta["pick_label_column"] = pick_col
    except Exception as exc:  # noqa: BLE001
        meta["pickable_points"] = []
        warnings.append(f"Click-identify data unavailable: {exc}")
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
