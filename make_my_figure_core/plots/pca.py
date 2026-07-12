"""PCA scatter from an expression matrix plus sample metadata.

The primary table is a feature-by-sample matrix (first column = feature id,
remaining columns = samples). Sample metadata is supplied as an auxiliary
table whose ``metadata_key`` column matches the matrix sample (column) names.
PCA is computed with a plain NumPy SVD (no scikit-learn dependency).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from make_my_figure_core.plots.base import (
    RenderError,
    RenderResult,
    base_metadata,
    figure_size,
    get_mapping,
    require_columns,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "pca_scatter_from_matrix"

_MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]


def render(spec: Dict[str, Any], df, style: StyleProfile,
           aux: Optional[Dict[str, pd.DataFrame]] = None) -> RenderResult:
    aux = aux or {}
    row_id = get_mapping(spec, "matrix_row_id", None) or df.columns[0]
    require_columns(df, [row_id], context=PLOT_TYPE)
    meta_key = get_mapping(spec, "metadata_key", "sample_id")
    color_by = get_mapping(spec, "color", None)
    shape_by = get_mapping(spec, "shape", None)

    warnings: List[str] = []
    exclude = {str(c) for c in (get_mapping(spec, "exclude_columns", None) or [])}
    sample_cols = [c for c in df.columns if c != row_id and str(c) not in exclude]
    # Restrict to actual samples (present in the metadata's sample-id column)
    # when metadata is supplied. This drops RNA-seq annotation columns
    # (geneSymbol/bioType/annotationLevel) that sit before the sample columns.
    meta_df = aux.get("metadata")
    if meta_df is not None and meta_key in meta_df.columns:
        ids = set(meta_df[meta_key].astype(str))
        matched = [c for c in sample_cols if str(c) in ids]
        if matched:
            dropped_meta = [c for c in sample_cols if c not in matched]
            if dropped_meta:
                warnings.append(f"Ignored column(s) not present in metadata '{meta_key}': "
                                f"{dropped_meta}.")
            sample_cols = matched
    numeric_all = df[sample_cols].apply(lambda s: pd.to_numeric(s, errors="coerce"))
    numeric_cols = [c for c in sample_cols if numeric_all[c].notna().any()]
    dropped_nonnum = [c for c in sample_cols if c not in numeric_cols]
    if dropped_nonnum:
        warnings.append(f"Ignored non-numeric column(s): {dropped_nonnum}.")
    sample_cols = numeric_cols
    if len(sample_cols) < 3:
        raise RenderError(f"{PLOT_TYPE}: need >= 3 numeric sample columns for a PCA "
                          f"(found {len(sample_cols)}). Check the metadata sample IDs match "
                          "the matrix column headers, or set 'exclude_columns'.")

    numeric = numeric_all[sample_cols]
    X = numeric.to_numpy(dtype=float).T  # samples x features
    if np.isnan(X).any():
        warnings.append("Non-numeric/missing matrix entries replaced with feature means.")
        col_means = np.nanmean(X, axis=0)
        idx = np.where(np.isnan(X))
        X[idx] = np.take(col_means, idx[1])

    # Center features, SVD.
    Xc = X - X.mean(axis=0, keepdims=True)
    U, S, _ = np.linalg.svd(Xc, full_matrices=False)
    scores = U * S
    explained = (S ** 2) / np.sum(S ** 2) if np.sum(S ** 2) > 0 else np.zeros_like(S)
    pc1, pc2 = scores[:, 0], scores[:, 1]

    # Attach metadata aligned to sample column order.
    meta_df = aux.get("metadata")
    meta_lookup = {}
    if meta_df is not None and meta_key in meta_df.columns:
        meta_lookup = meta_df.set_index(meta_df[meta_key].astype(str)).to_dict("index")
    elif color_by or shape_by:
        warnings.append("No matching sample metadata supplied; points drawn uncolored.")
        color_by = shape_by = None

    def _attr(sample: str, col):
        rec = meta_lookup.get(str(sample))
        return rec.get(col) if rec and col in rec else None

    color_vals = [_attr(s, color_by) for s in sample_cols] if color_by else [None] * len(sample_cols)
    shape_vals = [_attr(s, shape_by) for s in sample_cols] if shape_by else [None] * len(sample_cols)
    color_levels = list(dict.fromkeys([c for c in color_vals if c is not None]))
    shape_levels = list(dict.fromkeys([s for s in shape_vals if s is not None]))
    color_map = {lvl: style.color_for(i) for i, lvl in enumerate(color_levels)}
    shape_map = {lvl: _MARKERS[i % len(_MARKERS)] for i, lvl in enumerate(shape_levels)}

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.85))
        for i, s in enumerate(sample_cols):
            col = color_map.get(color_vals[i], style.color_for(0))
            mk = shape_map.get(shape_vals[i], "o")
            ax.scatter(pc1[i], pc2[i], color=col, marker=mk, s=30,
                       edgecolors="black", linewidths=style.spine_width_pt, zorder=3)

        ax.set_xlabel(spec.get("layout", {}).get("x_label", f"PC1 ({explained[0]*100:.1f}%)"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", f"PC2 ({explained[1]*100:.1f}%)"))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        ax.axhline(0, color="0.8", lw=style.spine_width_pt, zorder=0)
        ax.axvline(0, color="0.8", lw=style.spine_width_pt, zorder=0)

        # Build legends.
        handles = []
        if color_levels:
            for lvl in color_levels:
                handles.append(plt.Line2D([], [], marker="o", linestyle="",
                                          markerfacecolor=color_map[lvl],
                                          markeredgecolor="black", label=str(lvl)))
        if shape_levels:
            for lvl in shape_levels:
                handles.append(plt.Line2D([], [], marker=shape_map[lvl], linestyle="",
                                          markerfacecolor="grey", markeredgecolor="black",
                                          label=str(lvl)))
        if handles:
            ax.legend(handles=handles, frameon=False, loc="best", fontsize=style.axis_font_pt - 1)
        style_axes(ax, style)
        fig.tight_layout()

    meta = base_metadata(spec, style, df, used_columns=[row_id] + sample_cols)
    meta["n_samples"] = len(sample_cols)
    meta["n_features"] = int(numeric.shape[0])
    meta["explained_variance_ratio"] = [round(float(e), 4) for e in explained[:5]]
    meta["color_by"] = color_by
    meta["shape_by"] = shape_by
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
