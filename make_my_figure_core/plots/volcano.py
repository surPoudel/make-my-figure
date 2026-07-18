"""Volcano plot for differential-analysis results.

x = log2 fold change, y = -log10(p or adjusted p). Points are colored Up / Down /
Not significant. Classification either comes from a precomputed ``class_col``
(so the figure matches the DE result's own thresholds exactly) or is derived from
fold-change and p-value cutoffs. p-values are read from the table, never
recomputed.

v0.5 annotation controls (all optional, mapping-driven):
  annotate (master on/off), label_mode (top_fdr | top_lfc | top_up_down |
  selected | pasted | significant_all), top_n / top_n_up / top_n_down,
  label_by (symbol | id | both, needs id_col), show_arrows, label_box,
  label_color, label_font_size, repel_strength, label_list (pasted genes),
  max_labels_warn, auto_subtitle. Labels avoid overlap via ``adjustText`` when
  present (with subtle connector arrows), otherwise a distance-based fallback.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots.base import (
    RenderResult,
    base_metadata,
    coerce_numeric,
    dedupe_labels_by_distance,
    figure_size,
    get_mapping,
    place_legend,
    require_columns,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "volcano_plot"

# Strong, colorblind-aware volcano colors (down=blue, up=red, n.s.=grey).
_NS_COLOR = "#BBBBBB"
_DOWN_COLOR = "#2166AC"
_UP_COLOR = "#B2182B"

_LABEL_MODES = ("top_fdr", "top_lfc", "top_up_down", "selected", "pasted", "significant_all")


def _repel_labels(ax, points, style, *, show_arrows=True, box=False, color=None,
                  font_size=None, repel=None):
    """Draw point labels with overlap avoidance.

    Uses ``adjustText`` when installed (with optional subtle connector arrows);
    otherwise a distance-offset fallback. Never fails the render.
    """
    color = color or style.text_color
    fs = font_size or style.annotation_pt
    bbox = dict(boxstyle="round,pad=0.2", fc="white", ec=color, lw=0.5,
                alpha=0.85) if box else None
    texts = []
    for lx, ly, txt in points:
        texts.append(ax.text(lx, ly, txt, fontsize=fs, color=color, zorder=5, bbox=bbox))
    if not texts:
        return 0
    try:
        from adjustText import adjust_text  # type: ignore

        arrowprops = dict(arrowstyle="-", color="0.5", lw=0.5) if show_arrows else None
        kw = {}
        if repel is not None:
            try:
                kw["force_text"] = (float(repel), float(repel))
            except (TypeError, ValueError):
                pass
        adjust_text(texts, ax=ax, arrowprops=arrowprops, **kw)
        return len(texts)
    except Exception:
        for t in texts:
            t.remove()
        arrowprops = dict(arrowstyle="-", color="0.5", lw=0.5) if show_arrows else None
        for lx, ly, txt in points:
            ax.annotate(txt, (lx, ly), fontsize=fs, color=color, xytext=(4, 4),
                        textcoords="offset points", zorder=5, bbox=bbox,
                        arrowprops=arrowprops)
        return len(points)


def _label_text(row, label_col, id_col, label_by):
    sym = str(row[label_col]).strip() if label_col and label_col in row else ""
    gid = str(row[id_col]).strip() if id_col and id_col in row else ""
    if label_by == "id" and gid:
        return gid
    if label_by == "both" and sym and gid:
        return f"{sym} ({gid})"
    return sym or gid


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    x = get_mapping(spec, "x", "log2_fold_change")
    p_col = get_mapping(spec, "p", None) or get_mapping(spec, "p_value", "p_value")
    label_col = get_mapping(spec, "label", None)
    id_col = get_mapping(spec, "id_col", None)
    class_col = get_mapping(spec, "class_col", None)
    # fc_cutoff (EnhancedVolcano name) aliases lfc_cutoff; default log2(1.5).
    lfc_cutoff = float(get_mapping(spec, "fc_cutoff", get_mapping(spec, "lfc_cutoff", 1.0)))
    p_cutoff = float(get_mapping(spec, "p_cutoff", 0.05))
    label_sig_only = bool(get_mapping(spec, "label_significant_only", True))
    selected_labels = get_mapping(spec, "selected_labels", None) or []
    # highlight_genes (EnhancedVolcano name) aliases label_list.
    label_list = (get_mapping(spec, "highlight_genes", None)
                  or get_mapping(spec, "label_list", None) or [])
    # use_fdr controls the y-axis label / wording; None => infer from the p column name.
    use_fdr = get_mapping(spec, "use_fdr", None)
    condition = get_mapping(spec, "condition", None) or get_mapping(spec, "conditionType", None)

    # v0.5 annotation controls.
    annotate = bool(get_mapping(spec, "annotate", True))
    label_mode = str(get_mapping(spec, "label_mode", "top_fdr")).lower()
    if label_mode not in _LABEL_MODES:
        label_mode = "top_fdr"
    # If the user supplied an explicit highlight_genes list and left the default
    # mode, label exactly those genes (EnhancedVolcano's selectLab behaviour).
    if label_list and label_mode == "top_fdr":
        label_mode = "pasted"
    # top_n falls back to the legacy max_labels so old specs keep their count.
    top_n = int(get_mapping(spec, "top_n", get_mapping(spec, "max_labels", 10)))
    top_n_up = int(get_mapping(spec, "top_n_up", 8))
    top_n_down = int(get_mapping(spec, "top_n_down", 8))
    label_by = str(get_mapping(spec, "label_by", "symbol")).lower()
    show_arrows = bool(get_mapping(spec, "show_arrows", True))
    label_box = bool(get_mapping(spec, "label_box", False))
    label_color = get_mapping(spec, "label_color", None)
    label_font_size = get_mapping(spec, "label_font_size", None)
    repel_strength = get_mapping(spec, "repel_strength", None)
    max_labels_warn = int(get_mapping(spec, "max_labels_warn", 40))
    auto_subtitle = bool(get_mapping(spec, "auto_subtitle", True))

    # Duplicate-label handling (rows/features sharing a gene symbol).
    from make_my_figure_core.plots import label_policy as lp
    dup_policy = lp.normalize_policy(get_mapping(spec, "duplicate_label_policy", "all"))
    dup_rule = lp.normalize_rule(get_mapping(spec, "duplicate_label_representative_rule", "pvalue"))
    dup_show_count = bool(get_mapping(spec, "duplicate_label_show_count", False))
    # Point-identity selection/offsets (new); legacy text keys still honored below.
    selected_points = [str(s) for s in (get_mapping(spec, "selected_points", None) or [])]
    adj_col = get_mapping(spec, "adj_p", None) or get_mapping(spec, "padj", None)
    stat_col = get_mapping(spec, "statistic", None) or get_mapping(spec, "stat", None)

    require_columns(df, [x, p_col], context=PLOT_TYPE)
    work = df.copy()
    work[x] = coerce_numeric(work, x, context=PLOT_TYPE)
    work[p_col] = coerce_numeric(work, p_col, context=PLOT_TYPE)

    warnings: List[str] = []
    positive = work[p_col][work[p_col] > 0]
    floor = float(positive.min()) if not positive.empty else 1e-300
    pvals = work[p_col].clip(lower=floor)
    if (work[p_col] <= 0).any():
        warnings.append("Non-positive p-values clamped to the smallest positive value before -log10.")
    work = work.assign(_neglog10p=-np.log10(pvals))

    if class_col and class_col in work.columns:
        cls = work[class_col].astype(str)
        up = cls.eq("Up")
        down = cls.eq("Down")
    else:
        up = (work[x] >= lfc_cutoff) & (work[p_col] <= p_cutoff)
        down = (work[x] <= -lfc_cutoff) & (work[p_col] <= p_cutoff)
    ns = ~(up | down)

    n_up, n_down, n_ns = int(up.sum()), int(down.sum()), int(ns.sum())
    selected_set = {str(s).strip().lower() for s in selected_labels}
    pasted_set = {str(s).strip().lower() for s in label_list}

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.85))
        sig_size = max(22.0, style.marker_size * 0.6)
        ns_size = max(12.0, style.marker_size * 0.32)
        ax.scatter(work.loc[ns, x], work.loc[ns, "_neglog10p"], color=_NS_COLOR,
                   label="n.s.", s=ns_size, edgecolors="none", alpha=0.55, zorder=1)
        ax.scatter(work.loc[down, x], work.loc[down, "_neglog10p"], color=_DOWN_COLOR,
                   label=f"Down (n={n_down})", s=sig_size, edgecolors="white",
                   linewidths=0.4, alpha=0.95, zorder=3)
        ax.scatter(work.loc[up, x], work.loc[up, "_neglog10p"], color=_UP_COLOR,
                   label=f"Up (n={n_up})", s=sig_size, edgecolors="white",
                   linewidths=0.4, alpha=0.95, zorder=3)

        thr_lw = max(0.8, style.spine_width_pt * 0.8)
        ax.axvline(lfc_cutoff, ls="--", lw=thr_lw, color="0.5", zorder=0)
        ax.axvline(-lfc_cutoff, ls="--", lw=thr_lw, color="0.5", zorder=0)
        ax.axhline(-np.log10(p_cutoff), ls="--", lw=thr_lw, color="0.5", zorder=0)

        ymax = float(work["_neglog10p"].max()) if len(work) else 1.0

        # --- Label selection (point-identity aware) ----------------------
        n_labeled = 0
        if annotate and label_col and label_col in work.columns:
            sig_mask = (up | down)
            label_series = work[label_col].astype(str).str.strip()
            has_text = (label_series.ne("") & label_series.str.lower().ne("nan")
                        & work[label_col].notna())

            def _text_fn(i):
                return _label_text(work.loc[i], label_col, id_col, label_by)

            rep_columns = {"pvalue": p_col, "padj": adj_col, "effect": x, "statistic": stat_col}
            total_counts = lp.total_label_counts(work.loc[has_text, label_col])

            def _pts(ranked, *, policy, limit=None):
                return lp.build_label_points(
                    work, ranked, label_series=label_series, text_fn=_text_fn,
                    x_col=x, y_col="_neglog10p", id_col=id_col, policy=policy,
                    representative_rule=dup_rule, show_count=dup_show_count,
                    rep_columns=rep_columns, limit=limit, total_counts=total_counts)

            # 1) Explicit point selections (clicks) — always individual points.
            explicit_pts: List = []
            if selected_points:
                sel_idx = [work.index[k] for k in range(len(work))
                           if lp.point_id_for(work, work.index[k], id_col) in set(selected_points)]
                explicit_pts = _pts(sel_idx, policy="all")

            # 2) Legacy text selections (older specs / clicked-by-name) — under policy.
            text_pts: List = []
            if selected_set:
                sel = work[label_series.str.lower().isin(selected_set) & has_text]
                ranked = list(sel.sort_values("_neglog10p", ascending=False).index)
                text_pts = _pts(ranked, policy=dup_policy)

            # 3) Mode-driven candidates — ranked, then policy applied.
            pool = work[sig_mask & has_text] if label_sig_only else work[has_text]
            mode_pts: List = []
            if label_mode == "pasted":
                m = work[label_series.str.lower().isin(pasted_set) & has_text]
                ranked = list(m.sort_values("_neglog10p", ascending=False).index)
                mode_pts = _pts(ranked, policy=dup_policy)
            elif label_mode == "selected":
                mode_pts = []  # only explicit / text selections above
            elif label_mode == "top_lfc":
                ranked = list(pool.reindex(pool[x].abs().sort_values(ascending=False).index).index)
                mode_pts = _pts(ranked, policy=dup_policy, limit=top_n)
            elif label_mode == "top_up_down":
                up_ranked = list(work[up & has_text].sort_values("_neglog10p", ascending=False).index)
                dn_ranked = list(work[down & has_text].sort_values("_neglog10p", ascending=False).index)
                mode_pts = _pts(up_ranked, policy=dup_policy, limit=top_n_up) + \
                    _pts(dn_ranked, policy=dup_policy, limit=top_n_down)
            elif label_mode == "significant_all":
                sig_frame = work[sig_mask & has_text].sort_values("_neglog10p", ascending=False)
                ranked = list(sig_frame.index)
                mode_pts = _pts(ranked, policy=dup_policy)
                if len(mode_pts) > max_labels_warn:
                    warnings.append(
                        f"{len(mode_pts)} significant labels exceed the {max_labels_warn}-label cap; "
                        f"labeled the top {top_n}. Reduce the count or enlarge the figure.")
                    mode_pts = _pts(ranked, policy=dup_policy, limit=top_n)
            else:  # top_fdr (default)
                ranked = list(pool.sort_values("_neglog10p", ascending=False).index)
                mode_pts = _pts(ranked, policy=dup_policy, limit=top_n)

            # Merge, keeping point identity (never collapse duplicates by text).
            label_points: List = []
            seen_pid: set = set()
            for pt in (explicit_pts + text_pts + mode_pts):
                if pt.point_id in seen_pid:
                    continue
                seen_pid.add(pt.point_id)
                label_points.append(pt)

            if len(label_points) > max_labels_warn:
                warnings.append(
                    f"{len(label_points)} labels requested exceed the {max_labels_warn}-label cap; "
                    f"showing the first {max_labels_warn}. Reduce top N or enlarge the figure.")
                label_points = label_points[:max_labels_warn]

            # Extra top headroom so repelled labels are not clipped.
            ax.set_ylim(0, ymax * (1.30 if label_points else 1.18))

            # Manual offsets keyed by POINT identity (new) with a text-key fallback
            # for legacy specs. Moving one duplicate never disturbs the others; each
            # moved label keeps a leader line to its own point.
            point_offsets = lp.parse_offsets(get_mapping(spec, "point_offsets", None))
            legacy_offsets = lp.parse_offsets(get_mapping(spec, "label_offsets", None))
            fs_lab = label_font_size or style.annotation_pt
            manual: List = []
            auto: List = []
            for pt in label_points:
                off = point_offsets.get(pt.point_id)
                if off is None:
                    off = (legacy_offsets.get(pt.label_text)
                           or legacy_offsets.get(str(pt.label_text).lower()))
                if off is not None:
                    manual.append((pt, off))
                else:
                    auto.append(pt)
            for pt, off in manual:
                dx, dy = float(off[0]), float(off[1])
                ax.annotate(pt.label_text, (pt.anchor_x, pt.anchor_y), fontsize=fs_lab,
                            color=label_color or style.text_color,
                            xytext=(dx, dy), textcoords="offset points", zorder=6,
                            arrowprops=dict(arrowstyle="-", color="0.5", lw=0.5))
            auto_tuples = [(pt.anchor_x, pt.anchor_y, pt.label_text) for pt in auto]
            n_labeled = len(manual) + _repel_labels(
                ax, auto_tuples, style, show_arrows=show_arrows, box=label_box,
                color=label_color, font_size=label_font_size, repel=repel_strength)

            # Warn if identical labels land on the same anchor (stacked, unresolved).
            _anchors: Dict[Any, int] = {}
            for pt in label_points:
                key = (round(pt.anchor_x, 6), round(pt.anchor_y, 6), pt.label_text)
                _anchors[key] = _anchors.get(key, 0) + 1
            if any(c > 1 for c in _anchors.values()):
                warnings.append(
                    "Some duplicate labels share the same position; move them "
                    "individually or use a unique-label policy.")
        else:
            ax.set_ylim(0, ymax * 1.18)

        # FDR vs raw-P wording for the y-axis + subtitle; infer from column if unset.
        _use_fdr = use_fdr
        if _use_fdr is None:
            _use_fdr = any(k in str(p_col).lower() for k in
                           ("adj", "fdr", "padj", "q.val", "qval", "q_value", "q-value"))
        p_kind = "FDR" if _use_fdr else "P"
        ax.set_xlabel(spec.get("layout", {}).get("x_label", "log$_2$ fold change"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", f"-log$_{{10}}$ {p_kind}"))
        title = spec.get("layout", {}).get("title") or get_mapping(spec, "title", None)
        subtitle = spec.get("layout", {}).get("subtitle")
        if auto_subtitle and not subtitle:
            cond = f"{condition}  —  " if condition else ""
            subtitle = (f"{cond}Up {n_up} · Down {n_down} · NS {n_ns}   "
                        f"({p_kind} < {p_cutoff:g}, |log$_2$FC| ≥ {lfc_cutoff:g})")
        # Bold title with a smaller, grey subtitle beneath it (EnhancedVolcano style).
        if title:
            ax.set_title(str(title), fontsize=style.title_font_pt, fontweight="bold",
                         pad=(20 if subtitle else 8))
            if subtitle:
                ax.text(0.5, 1.015, subtitle, transform=ax.transAxes, ha="center",
                        va="bottom", fontsize=max(8.5, style.annotation_pt), color="0.4")
        elif subtitle:
            ax.set_title(subtitle, fontsize=max(9.0, style.annotation_pt), color="0.4")
        style_axes(ax, style)
        place_legend(ax, style, force_outside=True)
        leg = ax.get_legend()
        if leg is not None:
            for h in leg.legend_handles:
                try:
                    h.set_sizes([40])
                except Exception:
                    pass

    meta = base_metadata(spec, style, work, used_columns=[x, p_col, label_col, id_col])
    # Click-identify table: map a click on the live canvas back to a gene.
    # Guarded — it is an optional GUI convenience and must never break the
    # render or export if it hits an unexpected data/dtype edge.
    try:
        from make_my_figure_core.plots.base import (
            build_pickable_points, choose_label_column, resolve_point_labels)

        pick_col = choose_label_column(
            work, [label_col, "gene", "gene_symbol", "symbol", id_col, "gene_id"])
        point_ids = [lp.point_id_for(work, idx, id_col) for idx in work.index]
        meta["pickable_points"] = build_pickable_points(
            work[x].to_numpy(float), work["_neglog10p"].to_numpy(float),
            resolve_point_labels(work, pick_col), point_ids=point_ids)
        # Clicks store POINT identity (so duplicate-symbol points stay independent).
        meta["pick_label_key"] = "selected_points"
        meta["pick_offset_key"] = "point_offsets"
        meta["pick_label_column"] = pick_col         # mapping['label'] set to this when labeling
    except Exception as exc:  # noqa: BLE001
        meta["pickable_points"] = []
        warnings.append(f"Click-identify data unavailable: {exc}")
    meta["lfc_cutoff"] = lfc_cutoff
    meta["p_cutoff"] = p_cutoff
    meta["n_up"] = n_up
    meta["n_down"] = n_down
    meta["n_ns"] = n_ns
    meta["n_labeled"] = n_labeled
    meta["annotate"] = annotate
    meta["duplicate_label_policy"] = dup_policy
    meta["duplicate_label_representative_rule"] = dup_rule
    meta["duplicate_label_show_count"] = dup_show_count
    meta["label_mode"] = label_mode
    meta["show_arrows"] = show_arrows
    meta["classified_from"] = "class_col" if (class_col and class_col in work.columns) else "cutoffs"
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
