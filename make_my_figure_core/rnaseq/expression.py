"""Normalized / raw expression matrices (Mode B): transforms, gene selection,
and heatmap PlotSpec construction.

An :class:`ExpressionMatrix` separates gene metadata (id/symbol/biotype/...) from
the numeric sample block. Transforms are explicit and labelled so the figure and
the RnaSeqSpec always record what was applied. Raw-count DE analysis is NOT done
here (that needs the R pipeline); this module only prepares matrices for
heatmaps / PCA / correlation / gene-level plots.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from make_my_figure_core.rnaseq.detect import split_expression_matrix

TRANSFORMS = {
    "none": "values used as supplied",
    "log2p1": "log2(x + 1)",
    "cpm": "counts per million",
    "log2cpm": "log2(CPM + 1)",
    "zscore": "per-gene z-score (row standardization)",
}


@dataclass
class ExpressionMatrix:
    """A gene x sample matrix plus its metadata columns."""

    frame: pd.DataFrame
    metadata_columns: List[str]
    sample_columns: List[str]
    gene_id_col: Optional[str] = None
    gene_symbol_col: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    @property
    def values(self) -> pd.DataFrame:
        return self.frame[self.sample_columns].apply(pd.to_numeric, errors="coerce")

    def labels(self, prefer_symbol: bool = True) -> pd.Series:
        col = self.gene_symbol_col if (prefer_symbol and self.gene_symbol_col) else self.gene_id_col
        if col and col in self.frame.columns:
            s = self.frame[col].astype(str)
            # fall back to id where symbol is blank
            if self.gene_id_col and self.gene_id_col in self.frame.columns:
                gid = self.frame[self.gene_id_col].astype(str)
                s = s.where(s.str.strip().ne("") & s.str.lower().ne("nan"), gid)
            return s
        return pd.Series(self.frame.index.astype(str), index=self.frame.index)


def build_expression_matrix(df: pd.DataFrame, *, metadata_columns: Optional[List[str]] = None,
                            sample_columns: Optional[List[str]] = None) -> ExpressionMatrix:
    if metadata_columns is None or sample_columns is None:
        metadata_columns, sample_columns = split_expression_matrix(df)
    lc = {c.lower(): c for c in metadata_columns}
    gid = next((lc[k] for k in ("gene_id", "row_id", "gene", "ensembl") if k in lc), None)
    gsym = next((lc[k] for k in ("genesymbol", "gene_symbol", "symbol", "gene_name")
                 if k in lc), None)
    warnings: List[str] = []
    if len(sample_columns) < 2:
        warnings.append("Fewer than 2 sample columns detected; check the metadata/sample split.")
    return ExpressionMatrix(frame=df, metadata_columns=list(metadata_columns),
                            sample_columns=list(sample_columns), gene_id_col=gid,
                            gene_symbol_col=gsym, warnings=warnings)


def transform_matrix(values: pd.DataFrame, method: str = "none") -> pd.DataFrame:
    """Apply an expression transform to a gene x sample numeric frame."""
    method = (method or "none").lower()
    v = values.astype(float)
    if method == "none":
        return v
    if method == "log2p1":
        return np.log2(v.clip(lower=0) + 1.0)
    if method in ("cpm", "log2cpm"):
        libsize = v.sum(axis=0).replace(0, np.nan)
        cpm = v.divide(libsize, axis=1) * 1e6
        return np.log2(cpm + 1.0) if method == "log2cpm" else cpm
    if method == "zscore":
        mu = v.mean(axis=1)
        sd = v.std(axis=1, ddof=1).replace(0, np.nan)
        z = v.sub(mu, axis=0).div(sd, axis=0)
        return z.fillna(0.0)
    raise ValueError(f"Unknown transform '{method}'. Options: {sorted(TRANSFORMS)}")


def select_genes(em: ExpressionMatrix, *, method: str = "top_variable", n: int = 50,
                 genes: Optional[List[str]] = None,
                 de_significant: Optional[List[str]] = None) -> pd.Index:
    """Return the row index of selected genes.

    Methods: ``all``, ``top_variable`` (highest across-sample variance),
    ``selected`` (by id or symbol in ``genes``), ``de_significant`` (rows whose
    id/symbol is in the provided significant list).
    """
    values = em.values
    if method == "all":
        return em.frame.index
    if method == "top_variable":
        var = values.var(axis=1, ddof=1)
        return var.sort_values(ascending=False).head(int(n)).index
    if method == "selected" and genes:
        return _match_gene_rows(em, genes)
    if method == "de_significant" and de_significant:
        return _match_gene_rows(em, de_significant).intersection(em.frame.index)
    # default fallback
    var = values.var(axis=1, ddof=1)
    return var.sort_values(ascending=False).head(int(n)).index


def _match_gene_rows(em: ExpressionMatrix, names: List[str]) -> pd.Index:
    wanted = {str(x).strip().lower() for x in names}
    mask = pd.Series(False, index=em.frame.index)
    for col in (em.gene_symbol_col, em.gene_id_col):
        if col and col in em.frame.columns:
            mask = mask | em.frame[col].astype(str).str.strip().str.lower().isin(wanted)
    # also match against the index itself
    mask = mask | em.frame.index.astype(str).str.strip().str.lower().isin(wanted)
    return em.frame.index[mask]


def heatmap_spec_from_expression(em: ExpressionMatrix, *, transform: str = "zscore",
                                 selection: str = "top_variable", n_genes: int = 50,
                                 genes: Optional[List[str]] = None,
                                 de_significant: Optional[List[str]] = None,
                                 cluster_rows: bool = True, cluster_columns: bool = True,
                                 prefer_symbol: bool = True, title: Optional[str] = None,
                                 journal_style: str = "publication",
                                 input_table: str = "expression_matrix",
                                 metadata: Optional[pd.DataFrame] = None,
                                 sample_id_col: Optional[str] = None,
                                 annotation_columns: Optional[List[str]] = None,
                                 ) -> Dict[str, Any]:
    """Build a (spec, dataframe) pair for the clustered-heatmap renderer.

    Returns ``{"spec": PlotSpec, "dataframe": <row_id + samples>, "genes": [...],
    "transform": ..., "selection": ...}``. The dataframe is what the heatmap
    renderer consumes (row-id column + sample columns).
    """
    rows = select_genes(em, method=selection, n=n_genes, genes=genes,
                        de_significant=de_significant)
    values = transform_matrix(em.values.loc[rows], "none" if transform == "zscore" else transform)
    if transform == "zscore":
        values = transform_matrix(em.values.loc[rows], "zscore")
    labels = em.labels(prefer_symbol=prefer_symbol).loc[rows]
    # de-duplicate row labels so the heatmap axis is unambiguous
    labels = _dedupe_labels(labels)
    plot_df = values.copy()
    plot_df.insert(0, "gene", labels.values)
    color_scale = "diverging" if transform in ("zscore",) else "sequential"
    colorbar = {"zscore": "row z-score", "log2cpm": "log2 CPM", "cpm": "CPM",
                "log2p1": "log2(x+1)", "none": "expression"}.get(transform, "expression")
    n_rows = int(plot_df.shape[0])
    spec: Dict[str, Any] = {
        "plot_type": "heatmap_clustered_matrix",
        "input_table": input_table,
        "journal_style": journal_style,
        "mapping": {"row_id": "gene", "cluster_rows": bool(cluster_rows),
                    "cluster_columns": bool(cluster_columns), "color_scale": color_scale},
        "layout": {"colorbar_label": colorbar, "y_label": "Gene",
                   "title": title or "Expression heatmap"},
        "output": {"formats": ["svg", "png", "pdf"], "width_mm": 150.0, "dpi": 300},
    }
    # Optional sample-annotation strips from metadata (condition/batch/...).
    if metadata is not None and sample_id_col and annotation_columns:
        meta_idx = metadata.set_index(metadata[sample_id_col].astype(str))
        tracks = []
        for col in annotation_columns:
            if col in metadata.columns:
                values = {s: str(meta_idx[col].get(s, "")) for s in em.sample_columns}
                tracks.append({"label": col, "values": values})
        if tracks:
            spec["column_annotations"] = tracks
    return {"spec": spec, "dataframe": plot_df,
            "genes": list(labels.values), "transform": transform, "selection": selection,
            "n_genes": n_rows}


def _dedupe_labels(labels: pd.Series) -> pd.Series:
    seen: Dict[str, int] = {}
    out = []
    for v in labels.astype(str):
        if v in seen:
            seen[v] += 1
            out.append(f"{v}.{seen[v]}")
        else:
            seen[v] = 0
            out.append(v)
    return pd.Series(out, index=labels.index)
