"""Parse the RNA-seq analysis config (the JSON used by the reference R pipeline).

The config lists comparisons, covariates, and file paths. We parse it into a
normalized dict the runner + GUI can use, and validate comparisons against the
metadata's group column when available.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import pandas as pd


def parse_rnaseq_config(source: Any) -> Dict[str, Any]:
    """Parse a config JSON (path, bytes, str, or dict) into a normalized dict.

    Output keys: ``comparisons`` (list of {group1, group2}), ``covariates``
    (list), ``meta_file``, ``count_file``, ``output_folder``, ``batch``,
    ``reference_group`` (from the first comparison's group1 if present).
    """
    if isinstance(source, dict):
        raw = source
    else:
        if hasattr(source, "read"):
            text = source.read()
            text = text.decode("utf-8") if isinstance(text, bytes) else text
        elif isinstance(source, bytes):
            text = source.decode("utf-8")
        elif isinstance(source, str) and source.strip().startswith("{"):
            text = source
        else:  # treat as path
            with open(source, "r", encoding="utf-8") as fh:
                text = fh.read()
        raw = json.loads(text)

    comps = raw.get("comparisons") or []
    if isinstance(comps, dict):
        comps = [comps]
    norm_comps: List[Dict[str, str]] = []
    for c in comps:
        if isinstance(c, dict) and c.get("group1") is not None and c.get("group2") is not None:
            norm_comps.append({"group1": str(c["group1"]), "group2": str(c["group2"])})

    covariates = raw.get("covariates") or []
    if isinstance(covariates, str):
        covariates = [covariates]

    return {
        "comparisons": norm_comps,
        "covariates": [str(c) for c in covariates],
        "batch": raw.get("batch"),
        "meta_file": raw.get("meta_file"),
        "count_file": raw.get("count_file"),
        "output_folder": raw.get("output_folder"),
        "reference_group": norm_comps[0]["group1"] if norm_comps else raw.get("reference_group"),
    }


def validate_config_against_metadata(cfg: Dict[str, Any], meta: pd.DataFrame,
                                     group_col: str = "Group") -> List[str]:
    """Return a list of human-readable problems (empty if OK)."""
    problems: List[str] = []
    if group_col not in meta.columns:
        problems.append(f"Metadata has no '{group_col}' column; set the condition column.")
        return problems
    levels = set(meta[group_col].astype(str).str.replace(" ", "_"))
    for c in cfg.get("comparisons", []):
        for side in ("group1", "group2"):
            g = str(c[side]).replace(" ", "_")
            if g not in levels:
                problems.append(f"Comparison group '{c[side]}' not found in metadata "
                                f"'{group_col}' levels {sorted(levels)}.")
    for cov in cfg.get("covariates", []):
        if cov not in meta.columns:
            problems.append(f"Covariate '{cov}' not found in metadata columns.")
    return problems
