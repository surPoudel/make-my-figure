"""Reproducible, named transformations over a confirmed feature matrix.

Every transformation preserves the uploaded data, returns a NEW derived frame
plus a :class:`TransformationSpec` describing exactly what was done, and never
mutates its input. Frontend-agnostic (pandas/numpy/scipy only).

These are generic matrix operations (reshape, scaling, top-variable selection,
group summaries, correlation / distance / PCA / hierarchical clustering) — not an
RNA-seq pipeline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from make_my_figure_core.matrix_workflow.matrix_spec import MatrixSpec
from make_my_figure_core.matrix_workflow.metadata_spec import SampleMetadataSpec


@dataclass
class TransformationSpec:
    transformation_type: str
    input_dataset: Optional[str] = None
    output_dataset: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    reversible: bool = False
    user_confirmed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TransformationSpec":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (d or {}).items() if k in known})


def _matrix(df: pd.DataFrame, spec: MatrixSpec) -> Tuple[pd.Index, List[str], np.ndarray]:
    frame = spec.feature_frame(df)
    return frame.index, list(frame.columns), frame.to_numpy(dtype=float)


# --- 1. wide -> long ----------------------------------------------------
def wide_to_long(df: pd.DataFrame, spec: MatrixSpec,
                 metadata: Optional[SampleMetadataSpec] = None) -> Tuple[pd.DataFrame, TransformationSpec]:
    """Reshape features x samples -> long (one row per feature x sample)."""
    fid = spec.feature_id_column or (df.columns[0] if len(df.columns) else "feature")
    value_cols = [c for c in spec.value_columns if c in df.columns]
    keep_ann = [c for c in ([spec.feature_display_column] + list(spec.annotation_columns))
                if c and c in df.columns]
    id_vars = [fid] + keep_ann
    work = df[id_vars + value_cols].copy()
    long = work.melt(id_vars=id_vars, var_name="sample_id", value_name="value")
    long = long.rename(columns={fid: "feature_id"})
    if spec.feature_display_column and spec.feature_display_column in long.columns:
        long = long.rename(columns={spec.feature_display_column: "feature_label"})
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    warnings: List[str] = []
    if metadata and metadata.sample_to_group:
        long["group"] = long["sample_id"].map(metadata.sample_to_group)
        if metadata.batch_column and metadata.batch_column in df.columns:
            pass  # batch lives in metadata table, not the matrix; left to caller
        unmapped = int(long["group"].isna().sum())
        if unmapped:
            warnings.append(f"{unmapped} sample rows have no group assignment.")
    ts = TransformationSpec("wide_to_long", parameters={"value_columns": value_cols,
                            "feature_id_column": fid}, warnings=warnings, reversible=True,
                            user_confirmed=True)
    return long, ts


# --- 2 & 3. z-score -----------------------------------------------------
def row_zscore(df: pd.DataFrame, spec: MatrixSpec, *, ddof: int = 0
               ) -> Tuple[pd.DataFrame, TransformationSpec]:
    idx, cols, m = _matrix(df, spec)
    warnings: List[str] = []
    mean = np.nanmean(m, axis=1, keepdims=True)
    sd = np.nanstd(m, axis=1, ddof=ddof, keepdims=True)
    zero = (sd.ravel() == 0) | ~np.isfinite(sd.ravel())
    sd_safe = np.where((sd == 0) | ~np.isfinite(sd), 1.0, sd)
    z = (m - mean) / sd_safe
    z[np.broadcast_to(zero.reshape(-1, 1), z.shape)] = 0.0
    if zero.any():
        warnings.append(f"{int(zero.sum())} zero-variance feature(s) set to 0 after z-scoring.")
    out = pd.DataFrame(z, columns=cols)
    out.insert(0, spec.feature_id_column or "feature_id", list(idx))
    return out, TransformationSpec("row_zscore", parameters={"ddof": ddof},
                                   warnings=warnings, reversible=False, user_confirmed=True)


def column_zscore(df: pd.DataFrame, spec: MatrixSpec, *, ddof: int = 0
                  ) -> Tuple[pd.DataFrame, TransformationSpec]:
    idx, cols, m = _matrix(df, spec)
    mean = np.nanmean(m, axis=0, keepdims=True)
    sd = np.nanstd(m, axis=0, ddof=ddof, keepdims=True)
    sd_safe = np.where((sd == 0) | ~np.isfinite(sd), 1.0, sd)
    z = (m - mean) / sd_safe
    out = pd.DataFrame(z, columns=cols)
    out.insert(0, spec.feature_id_column or "feature_id", list(idx))
    return out, TransformationSpec("column_zscore", parameters={"ddof": ddof},
                                   reversible=False, user_confirmed=True)


# --- 4. top variable features ------------------------------------------
def top_variable_features(df: pd.DataFrame, spec: MatrixSpec, *, top_n: int = 50,
                          method: str = "variance") -> Tuple[pd.DataFrame, TransformationSpec]:
    idx, cols, m = _matrix(df, spec)
    if method == "iqr":
        score = np.nanpercentile(m, 75, axis=1) - np.nanpercentile(m, 25, axis=1)
    elif method == "mad":
        med = np.nanmedian(m, axis=1, keepdims=True)
        score = np.nanmedian(np.abs(m - med), axis=1)
    else:
        method = "variance"
        score = np.nanvar(m, axis=1)
    order = np.argsort(np.nan_to_num(score, nan=-np.inf))[::-1][:max(1, int(top_n))]
    keep = sorted(order.tolist())
    sub = df.iloc[keep].reset_index(drop=True)
    warnings = [] if len(keep) <= len(idx) else []
    return sub, TransformationSpec("top_variable_features",
                                   parameters={"top_n": int(top_n), "method": method,
                                               "n_features_in": int(len(idx))},
                                   warnings=warnings, reversible=False, user_confirmed=True)


# --- 5. group means -----------------------------------------------------
def group_means(df: pd.DataFrame, spec: MatrixSpec, metadata: SampleMetadataSpec, *,
                stat: str = "mean", error: str = "sd") -> Tuple[pd.DataFrame, TransformationSpec]:
    frame = spec.feature_frame(df)
    fid = spec.feature_id_column or "feature_id"
    rows = []
    warnings: List[str] = []
    for group in metadata.groups():
        samples = [s for s in metadata.samples_in_group(group) if s in frame.columns]
        if not samples:
            warnings.append(f"Group '{group}' has no matching value columns.")
            continue
        sub = frame[samples]
        center = sub.median(axis=1) if stat == "median" else sub.mean(axis=1)
        n = sub.notna().sum(axis=1).replace(0, np.nan)
        sd = sub.std(axis=1, ddof=1)
        if error == "sem":
            err = sd / np.sqrt(n)
        elif error == "ci95":
            err = 1.96 * sd / np.sqrt(n)
        else:
            err = sd
        for feat, c, e in zip(frame.index, center, err):
            rows.append({fid: feat, "group": group, "value": c, "error": e})
    out = pd.DataFrame(rows, columns=[fid, "group", "value", "error"])
    return out, TransformationSpec("group_means", parameters={"stat": stat, "error": error},
                                   warnings=warnings, reversible=False, user_confirmed=True)


# --- 6 & 7. correlation matrices ---------------------------------------
def sample_correlation(df: pd.DataFrame, spec: MatrixSpec, *, method: str = "pearson"
                       ) -> Tuple[pd.DataFrame, TransformationSpec]:
    frame = spec.feature_frame(df)
    corr = frame.corr(method=method)  # sample x sample
    out = corr.reset_index().rename(columns={"index": "sample_id"})
    if out.columns[0] != "sample_id":
        out = out.rename(columns={out.columns[0]: "sample_id"})
    return out, TransformationSpec("sample_correlation", parameters={"method": method},
                                   reversible=False, user_confirmed=True)


def feature_correlation(df: pd.DataFrame, spec: MatrixSpec, *, method: str = "pearson",
                        max_features: int = 200) -> Tuple[pd.DataFrame, TransformationSpec]:
    sub_df, _ = top_variable_features(df, spec, top_n=max_features, method="variance")
    frame = spec.feature_frame(sub_df)
    labels = sub_df[spec.feature_id_column].astype(str).tolist() if spec.feature_id_column in sub_df else list(frame.index)
    corr = pd.DataFrame(np.corrcoef(frame.to_numpy(dtype=float)) if method == "pearson"
                        else frame.T.corr(method=method).to_numpy(),
                        index=labels, columns=labels)
    warnings = []
    n_in = spec.feature_frame(df).shape[0]
    if n_in > max_features:
        warnings.append(f"Capped to top {max_features} variable features of {n_in} "
                        "for the feature-correlation matrix.")
    out = corr.reset_index().rename(columns={"index": "feature_id"})
    return out, TransformationSpec("feature_correlation",
                                   parameters={"method": method, "max_features": int(max_features)},
                                   warnings=warnings, reversible=False, user_confirmed=True)


# --- 8. distance matrix -------------------------------------------------
def distance_matrix(df: pd.DataFrame, spec: MatrixSpec, *, metric: str = "euclidean"
                    ) -> Tuple[pd.DataFrame, TransformationSpec]:
    from scipy.spatial.distance import pdist, squareform

    frame = spec.feature_frame(df)
    X = frame.to_numpy(dtype=float).T  # samples x features
    X = np.nan_to_num(X, nan=np.nanmean(X) if np.isfinite(X).any() else 0.0)
    m = "cityblock" if metric == "manhattan" else metric
    if metric == "correlation":
        m = "correlation"
    D = squareform(pdist(X, metric=m))
    out = pd.DataFrame(D, index=list(frame.columns), columns=list(frame.columns))
    out = out.reset_index().rename(columns={"index": "sample_id"})
    return out, TransformationSpec("distance_matrix", parameters={"metric": metric},
                                   reversible=False, user_confirmed=True)


# --- 9. PCA -------------------------------------------------------------
def compute_pca(df: pd.DataFrame, spec: MatrixSpec, *, n_components: int = 2,
                scale: bool = True) -> Tuple[pd.DataFrame, TransformationSpec]:
    """PCA of samples (columns). Returns a scores frame (sample_id + PC1..PCk).

    Variance-explained and loadings ride out in the TransformationSpec parameters.
    """
    frame = spec.feature_frame(df)
    X = frame.to_numpy(dtype=float).T  # samples x features
    warnings: List[str] = []
    if np.isnan(X).any():
        col_means = np.nanmean(X, axis=0)
        idx = np.where(np.isnan(X))
        X[idx] = np.take(np.nan_to_num(col_means), idx[1])
        warnings.append("Missing values replaced with feature means for PCA.")
    Xc = X - X.mean(axis=0, keepdims=True)
    if scale:
        sd = Xc.std(axis=0, ddof=0, keepdims=True)
        Xc = Xc / np.where(sd == 0, 1.0, sd)
    n_comp = int(min(n_components, min(Xc.shape) if min(Xc.shape) > 0 else 1))
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    scores = U[:, :n_comp] * S[:n_comp]
    var = (S ** 2) / max(1, (Xc.shape[0] - 1))
    total = var.sum() if var.sum() > 0 else 1.0
    var_ratio = (var[:n_comp] / total).tolist()
    out = pd.DataFrame(scores, columns=[f"PC{i+1}" for i in range(n_comp)])
    out.insert(0, "sample_id", list(frame.columns))
    ts = TransformationSpec("pca", parameters={
        "n_components": n_comp, "scale": scale,
        "variance_explained": var_ratio,
        "loadings": Vt[:n_comp].tolist()}, warnings=warnings,
        reversible=False, user_confirmed=True)
    return out, ts


# --- 10. hierarchical clustering ---------------------------------------
def hierarchical_clustering(df: pd.DataFrame, spec: MatrixSpec, *, cluster_rows: bool = True,
                            cluster_columns: bool = True, metric: str = "euclidean",
                            method: str = "average", k: int = 0
                            ) -> Tuple[pd.DataFrame, TransformationSpec]:
    """Cluster the matrix; return the input frame with an optional cluster column.

    The returned TransformationSpec parameters carry the row order, column order,
    and (when ``k>0``) the per-feature cluster assignment so callers can export it.
    """
    from make_my_figure_core import clustering as _clust

    frame = spec.feature_frame(df)
    M = np.nan_to_num(frame.to_numpy(dtype=float), nan=0.0)
    params: Dict[str, Any] = {"metric": metric, "method": method,
                              "cluster_rows": cluster_rows, "cluster_columns": cluster_columns,
                              "k": int(k)}
    warnings: List[str] = []
    row_order = list(range(M.shape[0]))
    col_order = list(range(M.shape[1]))
    out = df.copy()
    if cluster_rows and M.shape[0] > 2:
        try:
            zr = _clust.compute_linkage(M, method=method, metric=metric, axis="rows")
            row_order = _clust.leaf_order(zr)
            if k and k >= 2:
                assign = _clust.cut_k(zr, int(k), M.shape[0])
                col_name = "cluster"
                out[col_name] = [f"Cluster {int(c)}" for c in assign]
                params["cluster_assignment_column"] = col_name
                params["row_cluster_ids"] = [int(c) for c in assign]
        except Exception as exc:  # pragma: no cover - defensive
            warnings.append(f"Row clustering skipped: {exc}")
    if cluster_columns and M.shape[1] > 2:
        try:
            zc = _clust.compute_linkage(M, method=method, metric=metric, axis="columns")
            col_order = _clust.leaf_order(zc)
        except Exception as exc:  # pragma: no cover - defensive
            warnings.append(f"Column clustering skipped: {exc}")
    params["row_order"] = [int(i) for i in row_order]
    params["column_order"] = [int(i) for i in col_order]
    return out, TransformationSpec("hierarchical_clustering", parameters=params,
                                   warnings=warnings, reversible=False, user_confirmed=True)
