"""Auto-detect differential-expression (DE) result columns for confirmation.

A DE result table (e.g. from edgeR/limma or DESeq2) uses different headers per
tool — ``logFC``/``P.Value``/``adj.P.Val`` vs ``log2FoldChange``/``pvalue``/
``padj``. This module makes a *best guess* at which column plays each role so the
GUI can pre-fill the volcano-plot mapping; the user always confirms or overrides
the guess. Detection is deterministic, never mutates data, and never fabricates a
column — an unresolved role simply comes back as ``None``.

This is pure pandas with no R / RNA-seq-pipeline dependency.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

import pandas as pd

# Case-insensitive alias lists for DE-result columns (first match wins).
DE_COLUMN_ALIASES: Dict[str, List[str]] = {
    "gene_id": ["gene", "gene_id", "geneid", "feature_id", "ensembl", "ensembl_id",
                "gene_stable_id", "id"],
    "gene_symbol": ["genesymbol", "symbol", "gene_name", "gene_symbol",
                    "external_gene_name", "hgnc_symbol", "mgi_symbol"],
    "logFC": ["logfc", "log2foldchange", "log2fc", "lfc", "log2_fold_change",
              "log2foldchange_shrunk"],
    "p_value": ["p.value", "pvalue", "p_value", "pval", "p"],
    "adj_p": ["adj.p.val", "fdr", "padj", "qvalue", "q_value", "adj_p_value",
              "adjpval", "adjusted_p_value", "bh"],
    "ave_expr": ["aveexpr", "logcpm", "basemean", "mean_expression", "avgexpr",
                 "average_expression"],
    "statistic": ["t", "f", "lr", "stat", "waldstatistic", "z", "b"],
}


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9.]", "", str(name).strip().lower())


def _find_alias(columns: List[str], aliases: List[str]) -> Optional[str]:
    normed = {_norm(c): c for c in columns}
    for a in aliases:
        if _norm(a) in normed:
            return normed[_norm(a)]
    return None


def detect_de_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Best-guess mapping of DE-result roles to actual column names.

    Returns a dict keyed by role (``gene_id``, ``gene_symbol``, ``logFC``,
    ``p_value``, ``adj_p``, ``ave_expr``, ``statistic``); a value is the matched
    column name or ``None`` when no alias matched.
    """
    columns = list(df.columns)
    mapping: Dict[str, Optional[str]] = {}
    for role, aliases in DE_COLUMN_ALIASES.items():
        mapping[role] = _find_alias(columns, aliases)
    # Prefer a dedicated statistic column that is not the adjusted p or logFC.
    if mapping["statistic"] in (mapping.get("adj_p"), mapping.get("logFC"), mapping.get("p_value")):
        mapping["statistic"] = None
    return mapping
