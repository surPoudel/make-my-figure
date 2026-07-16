"""Publication-style QC plots for a (mapped) feature matrix.

Each builder returns render-ready :class:`PlotInputs` (plot_type + dataframe +
mapping) that go straight to ``registry.render`` — reusing the existing publication
renderers, so QC plots match the rest of the app and export to PNG/SVG/PDF. Used for
before/after preprocessing QC. Pure pandas/numpy.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from make_my_figure_core.matrix_workflow.matrix_spec import MatrixSpec
from make_my_figure_core.matrix_workflow.plot_builder import PlotInputs

# Distribution QC plots can subsample features for speed on huge matrices (QC only).
_QC_MAX_FEATURES = 4000


def qc_plot_catalog() -> List[Dict[str, str]]:
    return [
        {"key": "library_size", "label": "Per-sample total signal (library size)"},
        {"key": "sample_median", "label": "Per-sample median value"},
        {"key": "sample_boxplot", "label": "Per-sample value distribution (box)"},
        {"key": "value_density", "label": "Per-sample value density"},
        {"key": "zero_fraction", "label": "Zero fraction per sample"},
        {"key": "missing_fraction", "label": "Missing-value fraction per sample"},
        {"key": "sample_correlation", "label": "Sample correlation heatmap"},
        {"key": "pca", "label": "PCA (samples)"},
        {"key": "mean_variance", "label": "Mean–variance trend (features)"},
    ]


def _frame(df: pd.DataFrame, spec: MatrixSpec) -> pd.DataFrame:
    return spec.feature_frame(df)                       # features x samples (numeric)


def _long(df: pd.DataFrame, spec: MatrixSpec, seed: int = 0) -> pd.DataFrame:
    frame = _frame(df, spec)
    if len(frame) > _QC_MAX_FEATURES:
        rng = np.random.default_rng(seed)
        frame = frame.iloc[np.sort(rng.choice(len(frame), _QC_MAX_FEATURES, replace=False))]
    long = frame.reset_index().melt(id_vars=frame.index.name or "index",
                                    var_name="sample", value_name="value")
    return long.dropna(subset=["value"])


def _per_sample(df: pd.DataFrame, spec: MatrixSpec, stat: str) -> pd.DataFrame:
    frame = _frame(df, spec)
    if stat == "total":
        vals = np.nansum(frame.to_numpy(dtype=float), axis=0)
    elif stat == "median":
        vals = np.nanmedian(np.where(np.isfinite(frame.to_numpy(dtype=float)),
                                     frame.to_numpy(dtype=float), np.nan), axis=0)
    elif stat == "zero_fraction":
        m = frame.to_numpy(dtype=float)
        vals = (np.nan_to_num(m) == 0).mean(axis=0)
    elif stat == "missing_fraction":
        vals = np.isnan(frame.to_numpy(dtype=float)).mean(axis=0)
    else:
        vals = np.nanmean(frame.to_numpy(dtype=float), axis=0)
    return pd.DataFrame({"sample": list(frame.columns), "value": vals})


def qc_plot_inputs(kind: str, df: pd.DataFrame, matrix_spec: MatrixSpec, *,
                   metadata=None, title: Optional[str] = None) -> PlotInputs:
    """Build render-ready inputs for QC plot ``kind`` (see qc_plot_catalog)."""
    spec = matrix_spec
    ttl = {"title": title} if title else {}

    if kind in ("library_size", "sample_median", "zero_fraction", "missing_fraction"):
        stat = {"library_size": "total", "sample_median": "median",
                "zero_fraction": "zero_fraction", "missing_fraction": "missing_fraction"}[kind]
        d = _per_sample(df, spec, stat)
        ylab = {"total": "Total signal", "median": "Median value",
                "zero_fraction": "Zero fraction", "missing_fraction": "Missing fraction"}[stat]
        return PlotInputs("barplot_with_error_bar", d,
                          {"x": "sample", "y": "value", "error": "none"},
                          spec_extra={"layout": {**ttl, "y_label": ylab, "x_label": "Sample"}})

    if kind == "sample_boxplot":
        long = _long(df, spec)
        return PlotInputs("boxplot_or_violin_with_points", long,
                          {"x": "sample", "y": "value", "kind": "box", "points": False},
                          spec_extra={"layout": {**ttl, "y_label": "Value", "x_label": "Sample"}})

    if kind == "value_density":
        long = _long(df, spec)
        return PlotInputs("ridge_or_density_plot", long,
                          {"x": "value", "group": "sample"},
                          spec_extra={"layout": {**ttl}})

    if kind == "sample_correlation":
        from make_my_figure_core.matrix_workflow import transformations as T
        corr, _ts = T.sample_correlation(df, spec)
        return PlotInputs("heatmap_clustered_matrix", corr,
                          {"row_id": "sample_id", "color_scale": "sequential",
                           "cluster_rows": True, "cluster_columns": True},
                          spec_extra={"layout": {**ttl, "colorbar_label": "correlation"}})

    if kind == "pca":
        mapping: Dict[str, Any] = {"matrix_row_id": spec.feature_id_column,
                                   "value_columns": list(spec.value_columns)}
        aux = {}
        if metadata is not None and getattr(metadata, "confirmed_by_user", False) \
                and metadata.sample_to_group:
            aux = {"metadata": metadata.metadata_frame(sample_col="sample_id", group_col="group")}
            mapping.update({"metadata_key": "sample_id", "color": "group"})
        return PlotInputs("pca_scatter_from_matrix", df, mapping, aux=aux,
                          spec_extra={"layout": {**ttl}})

    if kind == "mean_variance":
        frame = _frame(df, spec)
        m = frame.to_numpy(dtype=float)
        d = pd.DataFrame({"mean": np.nanmean(m, axis=1), "variance": np.nanvar(m, axis=1)})
        d = d.replace([np.inf, -np.inf], np.nan).dropna()
        return PlotInputs("scatterplot_with_regression", d,
                          {"x": "mean", "y": "variance", "fit_line": False},
                          spec_extra={"layout": {**ttl, "x_label": "Feature mean",
                                                 "y_label": "Feature variance"}})

    raise ValueError(f"Unknown QC plot kind: {kind}")
