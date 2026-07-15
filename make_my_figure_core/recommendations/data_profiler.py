"""Cheap, deterministic profiling of an uploaded table.

``profile_table(df)`` classifies each column, detects candidate semantic roles
(group, subject, survival time/event, p-value, FDR, log-fold-change, GWAS
chromosome/position/p, dose/response, network source/target, mutation columns,
enrichment columns, classification label/score) and characterises wide numeric
matrices (count-like vs expression-like) and correlation/adjacency matrices.

Pure pandas + numpy, no plotting, no heavy statistics — safe to run on upload.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from make_my_figure_core.de_detect import _norm  # normalise header names
from make_my_figure_core.recommendations.recommendation_models import (
    ColumnRole,
    DataProfile,
)

# --- alias lists for role detection (matched against normalised names) -------
_ALIASES: Dict[str, List[str]] = {
    "group": ["group", "condition", "treatment", "genotype", "arm", "cohort", "class",
              "category", "cluster", "celltype", "cell_type", "status", "response_category"],
    "subject": ["subject", "subjectid", "patient", "patientid", "sampleid", "sample",
                "donor", "replicate", "id", "participant"],
    "survival_time": ["time", "survival", "survivaltime", "os", "ostime", "time_months",
                      "time_days", "followup", "duration", "tte"],
    "survival_event": ["event", "status", "death", "censor", "vital", "dead", "recurrence"],
    "p_value": ["p.value", "pvalue", "pval", "p", "p_value"],
    "adj_p": ["adj.p.val", "fdr", "padj", "qvalue", "q_value", "adj_p_value", "adjpval",
              "adjusted_p_value", "bh"],
    "logfc": ["logfc", "log2foldchange", "log2fc", "lfc", "log2_fold_change",
              "log2foldchange_shrunk", "effect", "estimate", "beta"],
    "ave_expr": ["aveexpr", "logcpm", "basemean", "mean_expression", "avgexpr",
                 "average_expression", "abundance", "expression"],
    "chromosome": ["chr", "chrom", "chromosome"],
    "position": ["pos", "position", "bp", "start", "location"],
    "dose": ["dose", "concentration", "conc", "log_dose", "logdose"],
    "response": ["response", "viability", "inhibition", "effect_pct", "percent_response",
                 "signal", "readout"],
    "source": ["source", "from", "node1", "regulator", "tf", "gene1"],
    "target": ["target", "to", "node2", "gene2"],
    "mutation_gene": ["gene", "gene_symbol", "genesymbol", "hugo", "symbol"],
    "mutation_type": ["mutation", "alteration", "variant", "consequence", "effect_type",
                      "mutation_type", "alteration_type", "variant_classification"],
    "enrichment_term": ["term", "pathway", "geneset", "go", "description", "name"],
    "enrichment_count": ["count", "gene_count", "genecount", "overlap", "size"],
    "enrichment_ratio": ["generatio", "gene_ratio", "ratio", "enrichment", "oddsratio"],
    "estimate_lower": ["ci_low", "cilow", "lower", "conf_low", "lcl", "l95"],
    "estimate_upper": ["ci_high", "cihigh", "upper", "conf_high", "ucl", "u95"],
    "label": ["label", "gene", "gene_symbol", "symbol", "name", "feature", "id"],
    "score": ["score", "prob", "probability", "prediction", "pred_score", "risk"],
}

_ID_HINTS = ("id", "sample", "patient", "barcode", "accession", "replicate", "subject",
             "gene", "feature", "name", "symbol", "term", "pathway")


def _find(columns: List[str], aliases: List[str]) -> Optional[str]:
    normed = {_norm(c): c for c in columns}
    for a in aliases:
        if _norm(a) in normed:
            return normed[_norm(a)]
    # substring fallback for compound headers
    for a in aliases:
        na = _norm(a)
        for nc, orig in normed.items():
            if na and (nc == na or nc.startswith(na) or nc.endswith(na)):
                return orig
    return None


def _looks_like_id(name: str) -> bool:
    lowered = _norm(name)
    return any(h in lowered for h in _ID_HINTS)


def _column_kind(s: pd.Series, name: str) -> str:
    if pd.api.types.is_datetime64_any_dtype(s):
        return "datetime"
    nonnull = s.dropna()
    if nonnull.empty:
        return "categorical"
    uniques = nonnull.unique()
    if pd.api.types.is_numeric_dtype(s):
        if _looks_like_id(name) and float(pd.Series(uniques).is_monotonic_increasing or 0):
            pass
        if set(pd.unique(nonnull)) <= {0, 1}:
            return "binary"
        return "numeric"
    # try datetime parse for object columns
    if s.dtype == object:
        try:
            parsed = pd.to_datetime(nonnull, errors="coerce", format="mixed")
            if parsed.notna().mean() > 0.9:
                return "datetime"
        except (ValueError, TypeError):
            pass
    if len(uniques) == 2:
        return "binary"
    if _looks_like_id(name) and len(uniques) == len(nonnull):
        return "id"
    return "categorical"


def _is_binary_event(s: pd.Series) -> bool:
    vals = set(pd.unique(s.dropna()))
    return vals <= {0, 1} and len(vals) >= 1 or vals <= {True, False}


def _numeric_block(df: pd.DataFrame, numeric_cols: List[str]):
    return df[numeric_cols].apply(pd.to_numeric, errors="coerce")


def _classify_matrix(block: pd.DataFrame) -> Optional[str]:
    arr = block.to_numpy(dtype="float64", copy=False)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return None
    nonneg = float((finite >= 0).mean())
    integral = float((finite == np.round(finite)).mean())
    big = float(finite.max())
    if nonneg > 0.98 and integral > 0.95 and big > 30:
        return "count_like"
    return "expression_like"


def profile_table(df: pd.DataFrame, table_name: str = "data") -> DataProfile:
    """Profile ``df`` into a :class:`DataProfile` (cheap, no rendering)."""
    columns = [str(c) for c in df.columns]
    n_rows, n_cols = int(len(df)), int(len(columns))

    kinds: Dict[str, str] = {}
    numeric, categorical, datetimes, ids, binaries = [], [], [], [], []
    for col in columns:
        kind = _column_kind(df[col], col)
        kinds[col] = kind
        if kind == "numeric":
            numeric.append(col)
        elif kind == "datetime":
            datetimes.append(col)
        elif kind == "binary":
            binaries.append(col)
            categorical.append(col)
        elif kind == "id":
            ids.append(col)
        else:
            categorical.append(col)

    missing = {c: float(df[c].isna().mean()) for c in columns if df[c].isna().any()}

    dup_ids = []
    for c in ids + [c for c in categorical if _looks_like_id(c)]:
        if c in df.columns and df[c].duplicated().any():
            dup_ids.append(c)

    prof = DataProfile(
        table_name=table_name, n_rows=n_rows, n_cols=n_cols, column_kinds=kinds,
        numeric_columns=numeric, categorical_columns=categorical,
        datetime_columns=datetimes, id_columns=ids, binary_columns=binaries,
        missingness=missing, duplicate_id_columns=dup_ids,
    )

    # --- role detection ------------------------------------------------------
    roles: List[ColumnRole] = []

    def add(role: str, col: Optional[str], conf: float, reason: str):
        if col is not None and col in columns:
            roles.append(ColumnRole(role, col, conf, reason))

    def has(role: str) -> bool:
        return any(r.role == role for r in roles)

    add("p_value", _find(columns, _ALIASES["p_value"]), 0.8, "p-value-like header")
    add("adj_p", _find(columns, _ALIASES["adj_p"]), 0.8, "adjusted-p/FDR-like header")
    add("logFC", _find(columns, _ALIASES["logfc"]), 0.8, "fold-change/effect header")
    add("ave_expr", _find(columns, _ALIASES["ave_expr"]), 0.6, "average-abundance header")
    add("estimate_lower", _find(columns, _ALIASES["estimate_lower"]), 0.6, "CI lower header")
    add("estimate_upper", _find(columns, _ALIASES["estimate_upper"]), 0.6, "CI upper header")

    # group / subject
    grp = _find([c for c in categorical], _ALIASES["group"])
    if not grp and numeric:
        # Fallback: any low-cardinality, non-id categorical column is a plausible
        # grouping variable (e.g. 'species', 'tissue', 'treatment_arm') even if its
        # name isn't in the alias list — as long as there's a numeric value column
        # to compare across it. Prefer the fewest-level column (most group-like).
        cands = []
        for c in categorical:
            if c in ids or _looks_like_id(c):
                continue
            n = int(df[c].dropna().nunique())
            if 2 <= n <= 20 and n < len(df):
                cands.append((n, c))
        if cands:
            grp = sorted(cands)[0][1]
    add("group", grp, 0.6, "group/condition-like categorical")
    subj = _find(columns, _ALIASES["subject"])
    if subj and subj != grp:
        add("subject", subj, 0.55, "subject/id-like header")

    # survival: a numeric time + a binary event
    st = _find(numeric, _ALIASES["survival_time"])
    ev = None
    for cand in [_find(columns, _ALIASES["survival_event"])] + binaries:
        if cand and cand in df.columns and _is_binary_event(df[cand]):
            ev = cand
            break
    if st is not None and ev is not None and st != ev:
        add("survival_time", st, 0.75, "numeric time-to-event header")
        add("survival_event", ev, 0.75, "binary event/censor column")

    # GWAS
    chrom = _find(columns, _ALIASES["chromosome"])
    posn = _find(numeric, _ALIASES["position"])
    if chrom and posn:
        add("chromosome", chrom, 0.7, "chromosome header")
        add("position", posn, 0.7, "genomic position header")

    # dose-response
    dose = _find(numeric, _ALIASES["dose"])
    resp = _find(numeric, _ALIASES["response"])
    if dose and resp and dose != resp:
        add("dose", dose, 0.65, "dose/concentration header")
        add("response", resp, 0.65, "response/readout header")

    # network edge list
    src = _find(columns, _ALIASES["source"])
    tgt = _find(columns, _ALIASES["target"])
    if src and tgt and src != tgt:
        add("source", src, 0.7, "edge source header")
        add("target", tgt, 0.7, "edge target header")

    # mutation long table
    mgene = _find(columns, _ALIASES["mutation_gene"])
    mtype = _find(columns, _ALIASES["mutation_type"])
    if mgene and mtype:
        add("mutation_gene", mgene, 0.6, "gene header")
        add("mutation_type", mtype, 0.7, "mutation/alteration header")
        msample = _find(columns, _ALIASES["subject"])
        add("mutation_sample", msample, 0.6, "sample/patient header")

    # enrichment
    eterm = _find(categorical + ids, _ALIASES["enrichment_term"])
    ecount = _find(numeric, _ALIASES["enrichment_count"])
    eratio = _find(numeric, _ALIASES["enrichment_ratio"])
    if eterm and (ecount or eratio) and (has("p_value") or has("adj_p")):
        add("enrichment_term", eterm, 0.7, "pathway/term header")
        add("enrichment_count", ecount, 0.6, "gene-count header")
        add("enrichment_ratio", eratio, 0.6, "gene-ratio header")

    # classification: a binary/2-level label + a numeric score in [0,1]-ish
    label_col = None
    for c in binaries + categorical:
        if c in df.columns and df[c].dropna().nunique() == 2:
            label_col = c
            break
    score_col = _find(numeric, _ALIASES["score"])
    if label_col and score_col and label_col != score_col:
        add("class_label", label_col, 0.65, "binary label column")
        add("class_score", score_col, 0.65, "numeric prediction/score header")

    prof.roles = roles

    # --- matrix characterisation --------------------------------------------
    feature_col = None
    non_numeric = [c for c in columns if kinds[c] in ("categorical", "id")]
    if non_numeric:
        # prefer an id/feature-like leading column
        feature_col = next((c for c in non_numeric if _looks_like_id(c)), non_numeric[0])
    if len(numeric) >= 3 and len(numeric) >= 0.5 * n_cols and feature_col is not None:
        block = _numeric_block(df, numeric)
        prof.is_matrix = True
        prof.matrix_feature_col = feature_col
        prof.matrix_sample_columns = numeric
        prof.matrix_kind = _classify_matrix(block)

    # correlation matrix: square numeric block, symmetric, unit diagonal
    if len(numeric) >= 3 and n_rows == len(numeric):
        block = _numeric_block(df, numeric).to_numpy(dtype="float64")
        if block.shape[0] == block.shape[1]:
            with np.errstate(invalid="ignore"):
                sym = np.allclose(block, block.T, atol=1e-6, equal_nan=True)
                diag_unit = np.allclose(np.diag(block), 1.0, atol=1e-6)
                in_range = np.nanmax(np.abs(block)) <= 1.0 + 1e-6
            if sym and diag_unit and in_range:
                prof.is_correlation_matrix = True
            elif sym and set(np.unique(block[np.isfinite(block)])) <= {0.0, 1.0}:
                prof.is_adjacency_matrix = True

    return prof
