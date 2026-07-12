"""Define sample/observation groups in-app, without a separate metadata file.

Two common needs:

* **Wide matrix** (features x samples, e.g. an expression matrix): assign each
  sample column to a group, then reshape selected features to long format so the
  standard bar/box/violin/stats plots can compare groups.
* **Long table** (one row per observation): derive a grouping column by mapping
  the values of an existing column to group labels.

Everything here is pure pandas and returns new frames (never mutates the input),
so both GUIs share the same logic.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


def metadata_from_assignment(sample_to_group: Dict[str, str], *,
                             sample_col: str = "SampleID",
                             group_col: str = "Group") -> pd.DataFrame:
    """Build a tidy metadata frame from an in-app sample->group assignment."""
    rows = [{sample_col: s, group_col: g} for s, g in sample_to_group.items()
            if str(g).strip() != ""]
    return pd.DataFrame(rows, columns=[sample_col, group_col])


def melt_matrix_to_long(df: pd.DataFrame, *, sample_columns: List[str],
                        sample_to_group: Dict[str, str],
                        feature_col: Optional[str] = None,
                        features: Optional[List[str]] = None,
                        value_name: str = "value", group_col: str = "group",
                        sample_col: str = "sample",
                        feature_name: str = "feature") -> pd.DataFrame:
    """Reshape a wide features x samples matrix to long, tagged with groups.

    Returns a long frame with columns ``[feature_name, sample_col, group_col,
    value_name]`` containing only the assigned samples and (optionally) the
    selected features. Suitable for bar/box/violin/stats grouped by ``group_col``.
    """
    assigned = [s for s in sample_columns if str(sample_to_group.get(s, "")).strip() != ""]
    if not assigned:
        raise ValueError("No samples were assigned to a group.")
    work = df.copy()
    if feature_col and feature_col in work.columns:
        work = work.set_index(feature_col)
    if features:
        wanted = [f for f in features if f in work.index]
        if not wanted:
            raise ValueError("None of the selected features were found in the matrix.")
        work = work.loc[wanted]
    long = (work[assigned]
            .apply(pd.to_numeric, errors="coerce")
            .reset_index()
            .melt(id_vars=work.index.name or "index",
                  var_name=sample_col, value_name=value_name))
    long = long.rename(columns={work.index.name or "index": feature_name})
    long[group_col] = long[sample_col].map(sample_to_group)
    long = long.dropna(subset=[value_name, group_col])
    return long[[feature_name, sample_col, group_col, value_name]]


def numeric_sample_columns(df: pd.DataFrame, feature_col: Optional[str] = None) -> List[str]:
    """Candidate *sample* columns of a wide matrix: numeric, excluding the label.

    Drops non-numeric annotation columns (e.g. geneSymbol / bioType) so only
    plausible sample columns are offered for group assignment. Numeric annotation
    columns (e.g. annotationLevel) can't be told apart by dtype — leave those
    unassigned in the UI (unassigned columns are excluded from the output).
    """
    out = []
    for c in df.columns:
        if feature_col and c == feature_col:
            continue
        if pd.to_numeric(df[c], errors="coerce").notna().any():
            out.append(c)
    return out


def wide_grouped_matrix(df: pd.DataFrame, *, feature_col: str, sample_columns: List[str],
                        sample_to_group: Dict[str, str], features: Optional[List[str]] = None,
                        group_col: str = "group"):
    """Wide features x samples matrix restricted to the *assigned* samples.

    Returns ``(wide_df, column_annotations)`` for a **heatmap** (or PCA): the wide
    frame keeps the feature-id column plus only the samples that were assigned a
    group (ordered by group), and ``column_annotations`` is a group color-strip
    spec (``[{"label", "values": {sample: group}}]``) the heatmap can draw. Unlike
    :func:`melt_matrix_to_long` (which is for bar/box/violin), this preserves the
    matrix shape so a heatmap actually renders.
    """
    assigned = [s for s in sample_columns if str(sample_to_group.get(s, "")).strip() != ""]
    if not assigned:
        raise ValueError("No samples were assigned to a group.")
    ordered = sorted(assigned, key=lambda s: (str(sample_to_group[s]), str(s)))
    work = df.copy()
    keep = ([feature_col] if feature_col in work.columns else []) + ordered
    wide = work[keep]
    if features and feature_col in work.columns:
        wanted = {str(f) for f in features}
        wide = wide[wide[feature_col].astype(str).isin(wanted)]
    ann = [{"label": group_col, "values": {s: str(sample_to_group[s]) for s in ordered}}]
    return wide.reset_index(drop=True), ann


def add_group_column(df: pd.DataFrame, *, source_col: str,
                     value_to_group: Dict[Any, str], new_col: str = "group",
                     default: Optional[str] = None) -> pd.DataFrame:
    """Return a copy of ``df`` with a new grouping column mapped from ``source_col``.

    Values not present in ``value_to_group`` become ``default`` (or are left as
    the original value's string when ``default`` is None).
    """
    if source_col not in df.columns:
        raise ValueError(f"Column '{source_col}' not found.")
    out = df.copy()
    mapped = out[source_col].map(lambda v: value_to_group.get(v, value_to_group.get(str(v))))
    if default is not None:
        mapped = mapped.fillna(default)
    else:
        mapped = mapped.fillna(out[source_col].astype(str))
    out[new_col] = mapped
    return out


def guess_groups_from_names(sample_columns: List[str]) -> Dict[str, str]:
    """Heuristic initial grouping from sample names (a starting point to edit).

    Groups by a trailing/leading token split on common separators; if that yields
    a single group, everything defaults to 'Group1'. This is only a suggestion —
    the user edits it in the UI.
    """
    import re

    def token(name: str) -> str:
        parts = re.split(r"[ _\-.]+", str(name))
        # prefer an alphabetic token (e.g. Ctrl/Treated) over pure-digit ids
        for p in parts:
            if p and not p.isdigit():
                return re.sub(r"\d+$", "", p) or p
        return parts[0] if parts else "Group1"

    guess = {s: token(s) for s in sample_columns}
    if len(set(guess.values())) <= 1:
        return {s: "Group1" for s in sample_columns}
    return guess
