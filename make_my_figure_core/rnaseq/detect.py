"""Input-mode detection and column auto-detection for RNA-seq tables.

The detectors are deterministic and conservative: they report a best-guess mode
plus the evidence, and every guess is overridable in the GUI. Detection never
mutates data and never fabricates columns.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from make_my_figure_core.io.loaders import TableInfo, load_table

# Case-insensitive alias lists for DE-result columns (first match wins).
RNASEQ_COLUMN_ALIASES: Dict[str, List[str]] = {
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

# Ensembl / RefSeq-ish gene id patterns (used to recognise a gene-id index).
_GENE_ID_RE = re.compile(r"^(ENS[A-Z]*G\d|ENSMUSG|ENSG|NM_|NR_|XM_|XR_|LOC\d)", re.I)


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9.]", "", str(name).strip().lower())


def _find_alias(columns: List[str], aliases: List[str]) -> Optional[str]:
    normed = {_norm(c): c for c in columns}
    for a in aliases:
        if _norm(a) in normed:
            return normed[_norm(a)]
    return None


def load_rnaseq_table(source: Any, *, source_name: Optional[str] = None) -> TableInfo:
    """Load an RNA-seq table, promoting an R-style row-name index to a column.

    R's ``write.table`` writes row names (gene IDs) as an unnamed first column,
    which pandas reads as the index. We reset it into a real ``gene_id`` column
    so downstream detection/mapping can see it.
    """
    info = load_table(source, source_name=source_name)
    df = info.dataframe
    if not isinstance(df.index, pd.RangeIndex) and df.index.name is None:
        vals = df.index.astype(str)
        looks_like_gene_id = bool(vals.str.match(_GENE_ID_RE).mean() > 0.5)
        col_name = "gene_id" if looks_like_gene_id else "row_id"
        if col_name not in df.columns:
            df = df.reset_index().rename(columns={"index": col_name})
            info.dataframe = df
            info.categorical_columns = [col_name] + [c for c in info.categorical_columns
                                                     if c != col_name]
    return info


def detect_de_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Best-guess mapping of DE-result roles to actual column names."""
    columns = list(df.columns)
    mapping: Dict[str, Optional[str]] = {}
    for role, aliases in RNASEQ_COLUMN_ALIASES.items():
        mapping[role] = _find_alias(columns, aliases)
    # Prefer a dedicated statistic column that is not the adjusted p or logFC.
    if mapping["statistic"] in (mapping.get("adj_p"), mapping.get("logFC"), mapping.get("p_value")):
        mapping["statistic"] = None
    return mapping


def _looks_like_de(df: pd.DataFrame, det: Dict[str, Optional[str]]) -> bool:
    # A DE table has a fold change AND a p-value column.
    return bool(det.get("logFC") and det.get("p_value"))


def _numeric_fraction(series: pd.Series) -> float:
    return float(pd.to_numeric(series, errors="coerce").notna().mean())


def _looks_like_counts(values: pd.DataFrame) -> bool:
    """True if the numeric block looks like raw integer counts (nonneg integers)."""
    if values.empty:
        return False
    arr = values.to_numpy(dtype="float64", copy=False)
    finite = arr[~pd.isna(arr)]
    if finite.size == 0:
        return False
    nonneg = float((finite >= 0).mean())
    integral = float((finite == finite.round()).mean())
    big = float(finite.max()) if finite.size else 0.0
    # Raw counts: (near) all nonnegative integers, with a wide dynamic range.
    return nonneg > 0.98 and integral > 0.98 and big > 30


def split_expression_matrix(df: pd.DataFrame) -> Tuple[List[str], List[str]]:
    """Split a wide expression table into (metadata_columns, sample_columns).

    Leading non-numeric / annotation columns are metadata; the trailing block of
    numeric columns are samples. Recognised annotation names
    (gene_id/geneSymbol/bioType/annotationLevel) are always metadata.
    """
    columns = list(df.columns)
    known_meta = {"gene_id", "row_id", "genesymbol", "gene_symbol", "symbol", "biotype",
                  "annotationlevel", "gene", "gene_name", "chromosome", "chr",
                  "annotation_level"}
    meta: List[str] = []
    samples: List[str] = []
    # Walk columns; leading annotation/low-numeric columns are metadata, then the
    # numeric sample block begins and everything after is a sample.
    in_samples = False
    for c in columns:
        numfrac = _numeric_fraction(df[c])
        is_known_meta = _norm(c) in known_meta
        if not in_samples:
            if is_known_meta or numfrac < 0.9:
                meta.append(c)
                continue
            in_samples = True
        samples.append(c)
    return meta, samples


def detect_input_mode(info: TableInfo) -> Dict[str, Any]:
    """Classify a loaded table into an RNA-seq input mode.

    Returns ``{"mode", "confidence", "de_columns", "metadata_columns",
    "sample_columns", "reasons"}``. Modes: ``de_result``, ``expression_matrix``,
    ``raw_counts``, ``sample_metadata``, ``unknown``.
    """
    df = info.dataframe
    reasons: List[str] = []
    det = detect_de_columns(df)

    # Metadata table: narrow, has a sample-id-like col + a group-like col, no big
    # numeric matrix.
    lc = {_norm(c): c for c in df.columns}
    has_sample_id = any(k in lc for k in ("sampleid", "sample", "sample_id", "id"))
    has_group = any(k in lc for k in ("group", "condition", "treatment", "genotype", "arm"))
    meta_cols, sample_cols = split_expression_matrix(df)

    if _looks_like_de(df, det):
        reasons.append(f"found logFC='{det['logFC']}' and p-value='{det['p_value']}'")
        return {"mode": "de_result", "confidence": "high", "de_columns": det,
                "metadata_columns": meta_cols, "sample_columns": sample_cols, "reasons": reasons}

    # Sample metadata: samples-as-rows with a sample-ID + group column and only a
    # few stray numeric columns (real expression matrices have no 'group' column
    # and many sample columns). Checked before the matrix rule to avoid treating
    # metadata's numeric columns (age, well) as a sample block.
    if has_sample_id and has_group and len(sample_cols) < 4:
        reasons.append("has a sample-ID column and a group/condition column; samples as rows")
        return {"mode": "sample_metadata", "confidence": "high", "de_columns": det,
                "metadata_columns": list(df.columns), "sample_columns": [], "reasons": reasons}

    # Wide numeric matrix -> expression or raw counts.
    if len(sample_cols) >= 2:
        values = df[sample_cols].apply(pd.to_numeric, errors="coerce")
        if _looks_like_counts(values):
            reasons.append(f"{len(sample_cols)} sample columns of nonnegative integers")
            return {"mode": "raw_counts", "confidence": "medium", "de_columns": det,
                    "metadata_columns": meta_cols, "sample_columns": sample_cols, "reasons": reasons}
        reasons.append(f"{len(sample_cols)} numeric sample columns; values look normalized/continuous")
        return {"mode": "expression_matrix", "confidence": "high", "de_columns": det,
                "metadata_columns": meta_cols, "sample_columns": sample_cols, "reasons": reasons}

    reasons.append("no fold-change/p-value pair and no wide numeric matrix detected")
    return {"mode": "unknown", "confidence": "low", "de_columns": det,
            "metadata_columns": meta_cols, "sample_columns": sample_cols, "reasons": reasons}
