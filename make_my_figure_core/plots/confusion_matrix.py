"""Confusion matrix as an annotated heatmap (binary or multiclass).

Two input modes: (a) true + predicted label columns (the KxK count matrix is
built here over the sorted union of classes), or (b) a precomputed matrix table
(first column = true-class label, remaining columns = predicted classes).
Counts can be shown raw or normalized by row / column / total.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots._v04_shared import numeric_matrix, ordered_unique
from make_my_figure_core.plots.base import (
    RenderResult,
    base_metadata,
    figure_size,
    get_mapping,
    require_columns,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "confusion_matrix"

_NORMALIZE = ("none", "row", "column", "total")


def _normalize(counts: np.ndarray, mode: str) -> np.ndarray:
    mode = (mode or "none").lower()
    c = counts.astype(float)
    if mode == "row":
        denom = c.sum(axis=1, keepdims=True)
    elif mode == "column":
        denom = c.sum(axis=0, keepdims=True)
    elif mode == "total":
        denom = np.array([[c.sum()]])
    else:
        return c
    denom = np.where(denom == 0, np.nan, denom)
    return c / denom


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    true_col = get_mapping(spec, "true", None)
    pred_col = get_mapping(spec, "predicted", None)
    normalize = str(get_mapping(spec, "normalize", "none")).lower()
    if normalize not in _NORMALIZE:
        normalize = "none"

    warnings: List[str] = []
    from_labels = bool(true_col and pred_col and true_col in df.columns and pred_col in df.columns)
    work = df.copy()
    accuracy = None

    if from_labels:
        require_columns(work, [true_col, pred_col], context=PLOT_TYPE)
        true_vals = work[true_col].astype(str)
        pred_vals = work[pred_col].astype(str)
        classes = ordered_unique(sorted(set(true_vals) | set(pred_vals)))
        idx = {c: i for i, c in enumerate(classes)}
        counts = np.zeros((len(classes), len(classes)), dtype=float)
        for t, p in zip(true_vals, pred_vals):
            counts[idx[t], idx[p]] += 1
        row_labels = classes
        col_labels = classes
        total = counts.sum()
        accuracy = float(np.trace(counts) / total) if total else None
        used = [true_col, pred_col]
    else:
        # Precomputed matrix table: first column = true label, rest = predicted.
        row_labels, col_labels, counts, w = numeric_matrix(work, context=PLOT_TYPE)
        warnings.extend(w)
        counts = np.nan_to_num(counts, nan=0.0)
        used = list(work.columns)

    display = _normalize(counts, normalize)
    finite = display[np.isfinite(display)]
    vmax = float(np.nanmax(finite)) if finite.size else 1.0
    vmin = 0.0
    n_r, n_c = display.shape

    # Cell annotation font shrinks a little for large matrices but stays legible.
    ann_fs = style.tick_label_pt if max(n_r, n_c) <= 8 else max(7.0, style.tick_label_pt - 2)

    with style.apply():
        w_in, _ = style.figure_size_inches(
            str(spec.get("layout", {}).get("column_width", "default")).lower(), aspect=1.0)
        side = max(w_in, 0.5 * n_c + 1.6)
        fig, ax = plt.subplots(figsize=(min(side, 12.0), min(side, 12.0)))
        im = ax.imshow(display, cmap=style.sequential_cmap, vmin=vmin, vmax=vmax,
                       interpolation="nearest", aspect="auto")
        for i in range(n_r):
            for j in range(n_c):
                v = display[i, j]
                if not np.isfinite(v):
                    continue
                if normalize == "none":
                    txt = f"{int(round(counts[i, j]))}"
                else:
                    txt = f"{v * 100:.0f}%"
                # Auto-contrast: light text on dark cells, dark on light.
                frac = (v - vmin) / (vmax - vmin) if vmax > vmin else 0.0
                color = "white" if frac > 0.55 else style.text_color
                ax.text(j, i, txt, ha="center", va="center", fontsize=ann_fs, color=color)

        ax.set_xticks(range(n_c))
        ax.set_yticks(range(n_r))
        longest = max((len(str(c)) for c in col_labels), default=0)
        rot = 45 if (n_c > 6 or longest > 6) else 0
        ax.set_xticklabels([str(c) for c in col_labels], rotation=rot,
                           ha="right" if rot else "center")
        ax.set_yticklabels([str(r) for r in row_labels])
        ax.set_xlabel(spec.get("layout", {}).get("x_label", "Predicted"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", "True"))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        for spine in ax.spines.values():
            spine.set_visible(False)
        _cb_loc = str(get_mapping(spec, "colorbar_location", "right")).lower()
        if _cb_loc not in ("right", "left", "top", "bottom"):
            _cb_loc = "right"
        cbar = fig.colorbar(im, ax=ax, location=_cb_loc,
                            fraction=float(get_mapping(spec, "colorbar_fraction", 0.046) or 0.046),
                            pad=float(get_mapping(spec, "colorbar_pad", 0.03) or 0.03),
                            shrink=float(get_mapping(spec, "colorbar_shrink", 1.0) or 1.0))
        cbar.ax.tick_params(labelsize=style.tick_label_pt, width=style.tick_width,
                            length=style.tick_length)
        cbar.set_label("count" if normalize == "none" else "fraction",
                       fontsize=style.axis_font_pt)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=used)
    meta["n_classes"] = int(max(n_r, n_c))
    meta["normalize"] = normalize
    if accuracy is not None:
        meta["accuracy"] = round(accuracy, 4)
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
