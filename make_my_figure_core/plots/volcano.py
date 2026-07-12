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
    lfc_cutoff = float(get_mapping(spec, "lfc_cutoff", 1.0))
    p_cutoff = float(get_mapping(spec, "p_cutoff", 0.05))
    label_sig_only = bool(get_mapping(spec, "label_significant_only", True))
    selected_labels = get_mapping(spec, "selected_labels", None) or []
    label_list = get_mapping(spec, "label_list", None) or []

    # v0.5 annotation controls.
    annotate = bool(get_mapping(spec, "annotate", True))
    label_mode = str(get_mapping(spec, "label_mode", "top_fdr")).lower()
    if label_mode not in _LABEL_MODES:
        label_mode = "top_fdr"
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

        # --- Label selection ---------------------------------------------
        n_labeled = 0
        if annotate and label_col and label_col in work.columns:
            xr = (work[x].max() - work[x].min()) or 1.0
            sig_mask = (up | down)
            has_text = work[label_col].astype(str).str.strip().ne("") & work[label_col].notna()

            def _rows_to_pts(frame):
                return [(float(r[x]), float(r["_neglog10p"]), _label_text(r, label_col, id_col, label_by))
                        for _, r in frame.iterrows()]

            # Explicit selections are always labeled, regardless of mode.
            pts: List = []
            if selected_set:
                sel = work[work[label_col].astype(str).str.strip().str.lower().isin(selected_set)]
                pts += _rows_to_pts(sel)

            pool = work[sig_mask & has_text] if label_sig_only else work[has_text]
            mode_pts: List = []
            if label_mode == "pasted":
                m = work[work[label_col].astype(str).str.strip().str.lower().isin(pasted_set) & has_text]
                mode_pts = _rows_to_pts(m)
            elif label_mode == "selected":
                mode_pts = []  # only the explicit selections above
            elif label_mode == "top_lfc":
                mode_pts = _rows_to_pts(pool.reindex(pool[x].abs().sort_values(ascending=False).index).head(top_n))
            elif label_mode == "top_up_down":
                up_pool = work[up & has_text].sort_values("_neglog10p", ascending=False).head(top_n_up)
                dn_pool = work[down & has_text].sort_values("_neglog10p", ascending=False).head(top_n_down)
                mode_pts = _rows_to_pts(up_pool) + _rows_to_pts(dn_pool)
            elif label_mode == "significant_all":
                sig_frame = work[sig_mask & has_text]
                if len(sig_frame) <= max_labels_warn:
                    mode_pts = _rows_to_pts(sig_frame)
                else:
                    warnings.append(
                        f"{len(sig_frame)} significant features exceed the {max_labels_warn}-label cap; "
                        f"labeled the top {top_n} by significance instead. Reduce the count or enlarge the figure.")
                    mode_pts = _rows_to_pts(sig_frame.sort_values("_neglog10p", ascending=False).head(top_n))
            else:  # top_fdr (default)
                mode_pts = _rows_to_pts(pool.sort_values("_neglog10p", ascending=False).head(top_n))

            seen = {t for _, _, t in pts}
            for p in mode_pts:
                if p[2] and p[2] not in seen:
                    seen.add(p[2])
                    pts.append(p)

            if len(pts) > max_labels_warn:
                warnings.append(
                    f"{len(pts)} labels requested exceed the {max_labels_warn}-label cap; "
                    f"showing the first {max_labels_warn}. Reduce top N or enlarge the figure.")
                pts = pts[:max_labels_warn]

            kept = dedupe_labels_by_distance(pts, min_dx=xr * 0.045, min_dy=ymax * 0.035)
            # Extra top headroom so repelled labels are not clipped.
            ax.set_ylim(0, ymax * (1.30 if kept else 1.18))
            n_labeled = _repel_labels(ax, kept, style, show_arrows=show_arrows, box=label_box,
                                      color=label_color, font_size=label_font_size,
                                      repel=repel_strength)
        else:
            ax.set_ylim(0, ymax * 1.18)

        ax.set_xlabel(spec.get("layout", {}).get("x_label", "log$_2$ fold change"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", "-log$_{10}$(p)"))
        title = spec.get("layout", {}).get("title")
        subtitle = spec.get("layout", {}).get("subtitle")
        if auto_subtitle and not subtitle:
            subtitle = f"Up: {n_up} | Down: {n_down} | FDR < {p_cutoff:g}, |log2FC| >= {lfc_cutoff:g}"
        if title and subtitle:
            ax.set_title(title + "\n" + subtitle, fontsize=style.title_font_pt)
        elif title:
            ax.set_title(title)
        elif subtitle:
            ax.set_title(subtitle, fontsize=max(9.0, style.annotation_pt))
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
    from make_my_figure_core.plots.base import (
        build_pickable_points, choose_label_column, resolve_point_labels)

    pick_col = choose_label_column(
        work, [label_col, "gene", "gene_symbol", "symbol", id_col, "gene_id"])
    meta["pickable_points"] = build_pickable_points(
        work[x].to_numpy(float), work["_neglog10p"].to_numpy(float),
        resolve_point_labels(work, pick_col))
    meta["pick_label_key"] = "selected_labels"   # GUI appends clicked genes here
    meta["pick_label_column"] = pick_col         # set mapping['label'] to this when labeling
    meta["lfc_cutoff"] = lfc_cutoff
    meta["p_cutoff"] = p_cutoff
    meta["n_up"] = n_up
    meta["n_down"] = n_down
    meta["n_ns"] = n_ns
    meta["n_labeled"] = n_labeled
    meta["annotate"] = annotate
    meta["label_mode"] = label_mode
    meta["show_arrows"] = show_arrows
    meta["classified_from"] = "class_col" if (class_col and class_col in work.columns) else "cutoffs"
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
