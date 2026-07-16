"""Turn a RecommendedPlot into render-ready inputs (plot type + dataframe + mapping
+ aux), applying the transformations that recommendation requires.

Pure/frontend-agnostic so both GUIs and tests share it. The result is fed straight
to ``registry.render``. Every statistic on a differential plot comes from the
supplied differential table (never recomputed here).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from make_my_figure_core.matrix_workflow import transformations as T
from make_my_figure_core.matrix_workflow.matrix_spec import MatrixSpec
from make_my_figure_core.matrix_workflow.metadata_spec import SampleMetadataSpec
from make_my_figure_core.matrix_workflow.recommendations import RecommendedPlot


@dataclass
class PlotInputs:
    plot_type: str
    dataframe: pd.DataFrame
    mapping: Dict[str, Any]
    aux: Dict[str, pd.DataFrame] = field(default_factory=dict)
    spec_extra: Dict[str, Any] = field(default_factory=dict)   # top-level spec keys (e.g. column_annotations)
    transformation_specs: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _group_strip(metadata, value_columns) -> Dict[str, Any]:
    """A heatmap column-annotation (group color strip) from confirmed groups, or {}."""
    if not (metadata and metadata.confirmed_by_user and metadata.sample_to_group):
        return {}
    vals = {s: metadata.sample_to_group[s] for s in value_columns
            if metadata.sample_to_group.get(s)}
    if not vals:
        return {}
    return {"column_annotations": [{"label": "group", "values": vals}]}


def build_plot_inputs(rec: RecommendedPlot, df: pd.DataFrame, matrix_spec: MatrixSpec, *,
                      metadata: Optional[SampleMetadataSpec] = None,
                      differential_table: Optional[pd.DataFrame] = None,
                      selected_features: Optional[List[str]] = None,
                      params: Optional[Dict[str, Any]] = None) -> PlotInputs:
    """Build render-ready inputs for ``rec``. Raises ValueError if prerequisites
    (confirmed matrix, groups, or a differential table) are missing."""
    params = dict(params or {})
    key = rec.key or rec.plot_type
    fid = matrix_spec.feature_id_column
    vcols = list(matrix_spec.value_columns)
    if not matrix_spec.confirmed_by_user or not vcols:
        raise ValueError("Confirm the matrix mapping (feature id + value columns) first.")

    # --- matrix heatmaps / clustering / pca ---
    strip = _group_strip(metadata, vcols)
    if key == "heatmap":
        m = {"row_id": fid, "value_columns": vcols}
        if strip:
            m["group_separators"] = True
        return PlotInputs("heatmap_clustered_matrix", df, m, spec_extra=strip)
    if key == "heatmap_zscore":
        m = {"row_id": fid, "value_columns": vcols, "scale": "row_zscore"}
        if strip:
            m["group_separators"] = True
        return PlotInputs("heatmap_clustered_matrix", df, m, spec_extra=strip)
    if key == "clustering":
        return PlotInputs("hierarchical_clustering", df,
                          {"row_id": fid, "value_columns": vcols, "scale": "row_zscore"})
    if key == "dendrogram":
        return PlotInputs("hierarchical_dendrogram", df,
                          {"row_id": fid, "value_columns": vcols, "cluster": "columns"})
    if key == "sample_correlation_heatmap":
        corr, ts = T.sample_correlation(df, matrix_spec, method=params.get("method", "pearson"))
        return PlotInputs("heatmap_clustered_matrix", corr,
                          {"row_id": "sample_id", "color_scale": "diverging",
                           "cluster_rows": True, "cluster_columns": True},
                          transformation_specs=[ts.to_dict()])
    if key == "feature_correlation_heatmap":
        corr, ts = T.feature_correlation(df, matrix_spec, method=params.get("method", "pearson"),
                                         max_features=int(params.get("max_features", 200)))
        return PlotInputs("heatmap_clustered_matrix", corr,
                          {"row_id": "feature_id", "color_scale": "diverging"},
                          transformation_specs=[ts.to_dict()], warnings=list(ts.warnings))
    if key == "top_variable_heatmap":
        sub, ts = T.top_variable_features(df, matrix_spec, top_n=int(params.get("top_n", 50)))
        m = {"row_id": fid, "value_columns": vcols, "scale": "row_zscore"}
        if strip:
            m["group_separators"] = True
        return PlotInputs("heatmap_clustered_matrix", sub, m, spec_extra=strip,
                          transformation_specs=[ts.to_dict()], warnings=list(ts.warnings))
    if key in ("pca", "pca_by_group"):
        mapping: Dict[str, Any] = {"matrix_row_id": fid, "value_columns": vcols}
        aux: Dict[str, pd.DataFrame] = {}
        if key == "pca_by_group":
            if not (metadata and metadata.confirmed_by_user):
                raise ValueError("Confirm sample groups to color the PCA by group.")
            meta_df = metadata.metadata_frame(sample_col="sample_id", group_col="group")
            aux = {"metadata": meta_df}
            mapping.update({"metadata_key": "sample_id", "color": "group"})
        return PlotInputs("pca_scatter_from_matrix", df, mapping, aux=aux)

    # --- selected-feature group comparisons (need groups) ---
    if key in ("box_by_group", "dot_by_group", "raincloud_by_group", "bar_by_group"):
        if not (metadata and metadata.confirmed_by_user):
            raise ValueError("Confirm sample groups first.")
        long, ts = T.wide_to_long(df, matrix_spec, metadata)
        warns = list(ts.warnings)
        feats = selected_features
        if not feats:
            sub_df, _ = T.top_variable_features(df, matrix_spec, top_n=1)
            feats = sub_df[fid].astype(str).tolist()
            warns.append(f"No feature selected — showing the most variable: {feats}.")
        long = long[long["feature_id"].astype(str).isin([str(f) for f in feats])]
        long = long.dropna(subset=["value", "group"])
        mapping = {"x": "group", "y": "value"}
        if key == "box_by_group":
            mapping.update({"kind": params.get("kind", "violin"), "points": True})
        elif key == "bar_by_group":
            mapping.update({"error": params.get("error", "sem")})
        return PlotInputs(rec.plot_type, long, mapping,
                          transformation_specs=[ts.to_dict()], warnings=warns)

    # --- differential-summary plots (values come from the supplied table) ---
    if key in ("volcano", "ma", "ranked_effect", "top_feature_heatmap"):
        if key == "top_feature_heatmap":
            if differential_table is None:
                raise ValueError("A differential table is required.")
            n = int(params.get("top_n", 40))
            eff = _effect_col(differential_table)
            top = (differential_table.reindex(differential_table[eff].abs()
                   .sort_values(ascending=False).index).head(n))
            ids = top[_id_col(differential_table)].astype(str).tolist()
            sub = df[df[fid].astype(str).isin(ids)]
            return PlotInputs("heatmap_clustered_matrix", sub,
                              {"row_id": fid, "value_columns": vcols, "scale": "row_zscore"})
        if differential_table is None:
            raise ValueError("Run a feature-level differential summary first.")
        tbl = differential_table
        eff = _effect_col(tbl)
        p_adj = "adjusted_p_value" if "adjusted_p_value" in tbl.columns else _p_col(tbl)
        label = "feature_label" if "feature_label" in tbl.columns else _id_col(tbl)
        if key == "volcano":
            return PlotInputs("volcano_plot", tbl,
                              {"x": eff, "p": p_adj, "label": label, "use_fdr": True})
        if key == "ma":
            tbl = tbl.copy()
            abund = _abundance_col(tbl)
            if abund is None:
                tbl["average_abundance"] = tbl[["mean_a", "mean_b"]].mean(axis=1)
                abund = "average_abundance"
            return PlotInputs("ma_plot", tbl,
                              {"x": abund, "y": eff, "p": p_adj, "label": label})
        if key == "ranked_effect":
            tbl = tbl.copy()
            n = int(params.get("top_n", 20))
            tbl = tbl.reindex(tbl[eff].abs().sort_values(ascending=False).index).head(n)
            return PlotInputs("waterfall_plot", tbl,
                              {"x": label, "y": eff, "sort": "descending"})

    raise ValueError(f"No builder for recommendation key '{key}'.")


def _id_col(tbl: pd.DataFrame) -> str:
    for c in ("feature_id", "feature", "id"):
        if c in tbl.columns:
            return c
    return tbl.columns[0]


def _effect_col(tbl: pd.DataFrame) -> str:
    for c in ("log2_fold_change", "logFC", "log2FoldChange", "effect", "estimate", "mean_difference"):
        if c in tbl.columns:
            return c
    raise ValueError("No effect/log-fold-change column found in the differential table.")


def _p_col(tbl: pd.DataFrame) -> str:
    for c in ("adjusted_p_value", "adj.P.Val", "padj", "FDR", "p_value", "P.Value", "pvalue"):
        if c in tbl.columns:
            return c
    raise ValueError("No p-value column found in the differential table.")


def _abundance_col(tbl: pd.DataFrame) -> Optional[str]:
    for c in ("average_abundance", "AveExpr", "baseMean", "base_mean", "aveexpr"):
        if c in tbl.columns:
            return c
    return None
