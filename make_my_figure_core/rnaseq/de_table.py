"""Precomputed differential-expression (DE) result tables (Mode A).

Parse a DE result into a standard schema, classify genes as Up / Down / n.s.
given thresholds, and build a PlotSpec for the volcano renderer. P-values are
taken verbatim from the uploaded table - never recomputed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from make_my_figure_core.rnaseq.detect import detect_de_columns


@dataclass
class DEResult:
    """A normalized DE result with an explicit column mapping."""

    frame: pd.DataFrame                       # standardized columns (see below)
    mapping: Dict[str, Optional[str]]         # role -> original column name
    n_up: int = 0
    n_down: int = 0
    n_ns: int = 0
    thresholds: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    @property
    def n_significant(self) -> int:
        return self.n_up + self.n_down


def parse_de_table(df: pd.DataFrame, mapping: Optional[Dict[str, Optional[str]]] = None,
                   ) -> DEResult:
    """Normalize a DE table into standard columns using an (auto/edited) mapping.

    Output frame columns (when available): ``gene_id``, ``gene_symbol``,
    ``logFC``, ``p_value``, ``adj_p``, ``ave_expr``, ``statistic``. The original
    frame is not mutated.
    """
    mp = dict(detect_de_columns(df))
    if mapping:
        mp.update({k: v for k, v in mapping.items() if v})
    warnings: List[str] = []
    out = pd.DataFrame(index=df.index)

    def _col(role: str, numeric: bool) -> None:
        src = mp.get(role)
        if src and src in df.columns:
            out[role] = pd.to_numeric(df[src], errors="coerce") if numeric else df[src].astype(str)

    _col("gene_id", numeric=False)
    _col("gene_symbol", numeric=False)
    _col("logFC", numeric=True)
    _col("p_value", numeric=True)
    _col("adj_p", numeric=True)
    _col("ave_expr", numeric=True)
    _col("statistic", numeric=True)

    # Gene id fallback: use the frame index if no explicit id column mapped.
    if "gene_id" not in out.columns:
        out["gene_id"] = df.index.astype(str)
    if "gene_symbol" not in out.columns:
        out["gene_symbol"] = out["gene_id"]

    if "logFC" not in out.columns or "p_value" not in out.columns:
        raise ValueError("DE table must have a log fold-change column and a p-value column. "
                         "Map them explicitly if auto-detection missed them.")
    if "adj_p" not in out.columns:
        warnings.append("No adjusted p-value column detected; thresholding on the raw p-value.")
    return DEResult(frame=out, mapping=mp, warnings=warnings)


def classify_de(de: DEResult, *, lfc_cutoff: float = 1.0, alpha: float = 0.05,
                use_adjusted: bool = True) -> DEResult:
    """Add an ``_class`` column (Up/Down/Not significant) and count each group."""
    f = de.frame
    p_field = "adj_p" if (use_adjusted and "adj_p" in f.columns) else "p_value"
    sig = f[p_field] <= alpha
    up = sig & (f["logFC"] >= lfc_cutoff)
    down = sig & (f["logFC"] <= -lfc_cutoff)
    cls = np.where(up, "Up", np.where(down, "Down", "Not significant"))
    de.frame = f.assign(_class=cls)
    de.n_up = int(up.sum())
    de.n_down = int(down.sum())
    de.n_ns = int((~(up | down)).sum())
    de.thresholds = {"lfc_cutoff": float(lfc_cutoff), "alpha": float(alpha),
                     "p_field": p_field, "use_adjusted": bool(use_adjusted)}
    return de


def significant_table(de: DEResult) -> pd.DataFrame:
    """Return only the significant (Up/Down) rows, sorted by significance."""
    f = de.frame
    if "_class" not in f.columns:
        return f.iloc[0:0]
    sig = f[f["_class"].isin(["Up", "Down"])].copy()
    p_field = de.thresholds.get("p_field", "p_value")
    return sig.sort_values(p_field)


def volcano_spec_from_de(de: DEResult, *, label_by: str = "gene_symbol",
                         top_n_labels: int = 15, selected_genes: Optional[List[str]] = None,
                         label_significant_only: bool = True,
                         title: Optional[str] = None, journal_style: str = "publication",
                         input_table: str = "de_table") -> Dict[str, Any]:
    """Build a volcano PlotSpec from a classified DE result.

    The volcano renderer receives a ready-to-plot frame via ``_rnaseq_volcano``
    mapping fields; thresholds/subtitle/labels are all recorded in the spec so
    the figure is reproducible.
    """
    thr = de.thresholds or {}
    p_field = thr.get("p_field", "adj_p" if "adj_p" in de.frame.columns else "p_value")
    subtitle = (f"Up: {de.n_up} | Down: {de.n_down} | "
                f"{'FDR' if p_field == 'adj_p' else 'p'} < {thr.get('alpha', 0.05):g}, "
                f"|log2FC| >= {thr.get('lfc_cutoff', 1.0):g}")
    y_label = ("-log$_{10}$ adjusted p-value" if p_field == "adj_p"
               else "-log$_{10}$ p-value")
    spec: Dict[str, Any] = {
        "plot_type": "volcano_plot",
        "input_table": input_table,
        "journal_style": journal_style,
        "mapping": {
            "x": "logFC",
            "p": p_field,
            "label": label_by if label_by in de.frame.columns else "gene_symbol",
            "class_col": "_class",
            "lfc_cutoff": thr.get("lfc_cutoff", 1.0),
            "p_cutoff": thr.get("alpha", 0.05),
            "max_labels": int(top_n_labels),
            "label_significant_only": bool(label_significant_only),
        },
        "layout": {"y_label": y_label, "subtitle": subtitle,
                   "title": title or "Differential expression"},
        "output": {"formats": ["svg", "png", "pdf"], "width_mm": 130.0, "dpi": 300},
    }
    if selected_genes:
        spec["mapping"]["selected_labels"] = list(selected_genes)
    return spec
