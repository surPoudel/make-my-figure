"""ROC curve(s) with AUC, computed without scikit-learn.

Supports one or two score columns (e.g. two models). The positive class is
``true_label == 1``.
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

PLOT_TYPE = "roc_curve"


def _roc(labels: np.ndarray, scores: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
    """Return (fpr, tpr, auc). Labels are 0/1; scores are continuous."""
    order = np.argsort(-scores)
    labels = labels[order]
    P = float(np.sum(labels == 1))
    N = float(np.sum(labels == 0))
    if P == 0 or N == 0:
        raise RenderError("ROC needs both positive and negative labels.")
    tps = np.cumsum(labels == 1)
    fps = np.cumsum(labels == 0)
    tpr = np.concatenate([[0.0], tps / P])
    fpr = np.concatenate([[0.0], fps / N])
    # np.trapz was renamed to np.trapezoid in NumPy 2.0.
    trapezoid = getattr(np, "trapezoid", None) or getattr(np, "trapz", None)
    auc = float(trapezoid(tpr, fpr))
    return fpr, tpr, auc


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    label_col = get_mapping(spec, "label", "true_label")
    score_col = get_mapping(spec, "score", "score_model_a")
    score2_col = get_mapping(spec, "score2", None)

    require_columns(df, [label_col, score_col], context=PLOT_TYPE)
    work = df.copy()
    work[label_col] = coerce_numeric(work, label_col, context=PLOT_TYPE)

    models = [score_col]
    if score2_col and score2_col in work.columns:
        models.append(score2_col)

    aucs: Dict[str, float] = {}
    warnings: List[str] = []

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=1.0))
        for mi, m in enumerate(models):
            sub = work[[label_col, m]].copy()
            sub[m] = coerce_numeric(sub, m, context=PLOT_TYPE)
            sub = sub.dropna()
            labels = (sub[label_col].to_numpy() == 1).astype(int)
            scores = sub[m].to_numpy(dtype=float)
            fpr, tpr, auc = _roc(labels, scores)
            aucs[str(m)] = round(auc, 4)
            ax.step(fpr, tpr, where="post", color=style.color_for(mi),
                    lw=style.line_width_pt, label=f"{m} (AUC={auc:.3f})")

        ax.plot([0, 1], [0, 1], ls="--", color="0.6", lw=style.spine_width_pt)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1.02)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel(spec.get("layout", {}).get("x_label", "False positive rate"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", "True positive rate"))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        ax.legend(frameon=False, loc="lower right")
        style_axes(ax)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[label_col] + models)
    meta["auc"] = aucs
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
