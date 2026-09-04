"""Precision-recall curve(s) with average precision (AUPRC), no scikit-learn.

Complements the ROC curve. The positive class is ``label == 1``. Two input
modes: (a) true labels + one/two score columns (the curve and AUPRC are
computed here), or (b) a precomputed ``recall``/``precision`` curve (AUPRC is
integrated by the trapezoid rule when recall is monotonic).
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots.base import (
    RenderError,
    RenderResult,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    require_columns,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "precision_recall_curve"


def _pr_from_scores(labels: np.ndarray, scores: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float, float, float]:
    """Return (recall_plot, precision_plot, average_precision, n_pos, n_neg)."""
    order = np.argsort(-scores, kind="stable")
    labels = labels[order]
    scores = scores[order]
    P = float(np.sum(labels == 1))
    N = float(np.sum(labels == 0))
    if P == 0 or N == 0:
        raise RenderError("Precision-recall needs both positive (label==1) and negative labels.")
    # One operating point per distinct score (tied scores are one threshold), so the
    # curve and the average precision do not depend on the input row order.
    last = np.r_[np.where(np.diff(scores) != 0)[0], scores.size - 1]
    tp = np.cumsum(labels == 1).astype(float)[last]
    fp = np.cumsum(labels == 0).astype(float)[last]
    precision = tp / np.maximum(tp + fp, 1e-12)
    recall = tp / P
    # Average precision: sum (R_n - R_{n-1}) * P_n, with R_{-1} = 0 (the
    # standard AP estimator; does not interpolate).
    r_prev = np.concatenate([[0.0], recall[:-1]])
    ap = float(np.sum((recall - r_prev) * precision))
    recall_plot = np.concatenate([[0.0], recall])
    precision_plot = np.concatenate([[precision[0]], precision])
    return recall_plot, precision_plot, ap, P, N


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    label_col = get_mapping(spec, "label", None)
    score_col = get_mapping(spec, "score", None)
    score2_col = get_mapping(spec, "score2", None)
    recall_col = get_mapping(spec, "recall", None)
    precision_col = get_mapping(spec, "precision", None)

    warnings: List[str] = []
    auprc: Dict[str, float] = {}
    meta_extra: Dict[str, Any] = {}
    used: List[str] = []

    from_scores = bool(label_col and score_col and label_col in df.columns and score_col in df.columns)
    precomputed = bool(recall_col and precision_col and recall_col in df.columns
                       and precision_col in df.columns)

    if not from_scores and not precomputed:
        # Give the most helpful error: default is the label+score workflow.
        require_columns(df, [label_col or "label", score_col or "score"], context=PLOT_TYPE)

    work = df.copy()

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=1.0))
        if from_scores:
            work[label_col] = coerce_numeric(work, label_col, context=PLOT_TYPE)
            models = [score_col] + ([score2_col] if (score2_col and score2_col in work.columns) else [])
            baseline = None
            for mi, m in enumerate(models):
                sub = work[[label_col, m]].copy()
                sub[m] = coerce_numeric(sub, m, context=PLOT_TYPE)
                sub = sub.dropna()
                labels = (sub[label_col].to_numpy() == 1).astype(int)
                scores = sub[m].to_numpy(dtype=float)
                rec, prec, ap, P, N = _pr_from_scores(labels, scores)
                auprc[str(m)] = round(ap, 4)
                baseline = P / (P + N)
                ax.step(rec, prec, where="post", color=style.color_for(mi),
                        lw=style.line_width_pt, label=f"{m} (AP={ap:.3f})")
            meta_extra["n_pos"] = int(P)
            meta_extra["n_neg"] = int(N)
            used = [label_col] + models
            if baseline is not None:
                ax.axhline(baseline, ls=":", color="0.6", lw=style.spine_width_pt,
                           label=f"baseline={baseline:.2f}")
        else:
            work[recall_col] = coerce_numeric(work, recall_col, context=PLOT_TYPE)
            work[precision_col] = coerce_numeric(work, precision_col, context=PLOT_TYPE)
            sub = work[[recall_col, precision_col]].dropna().sort_values(recall_col)
            rec = sub[recall_col].to_numpy(float)
            prec = sub[precision_col].to_numpy(float)
            ax.step(rec, prec, where="post", color=style.color_for(0), lw=style.line_width_pt,
                    label="precision-recall")
            trapezoid = getattr(np, "trapezoid", None) or getattr(np, "trapz", None)
            if rec.size >= 2 and np.all(np.diff(rec) >= 0):
                auprc["curve"] = round(float(trapezoid(prec, rec)), 4)
            else:
                warnings.append("Recall is not monotonic; AUPRC not integrated from precomputed curve.")
            used = [recall_col, precision_col]

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1.02)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel(spec.get("layout", {}).get("x_label", "Recall"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", "Precision"))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        ax.legend(frameon=False, loc="lower left", fontsize=max(7.0, style.legend_pt - 1))
        style_axes(ax, style)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=used)
    meta["auprc"] = auprc
    meta.update(meta_extra)
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
