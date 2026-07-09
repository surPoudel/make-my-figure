"""Validation for raw-count matrices and sample metadata (Mode C).

Validators return a structured report (errors + warnings + summary) so the GUI
can show clear, actionable messages before any DE analysis is attempted. They
never silently coerce or drop data without saying so.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class ValidationReport:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"ok": self.ok, "errors": list(self.errors),
                "warnings": list(self.warnings), "summary": dict(self.summary)}


def validate_counts(counts: pd.DataFrame, sample_columns: List[str], *,
                    min_count: int = 1, min_samples: int = 2) -> ValidationReport:
    """Validate a gene x sample raw-count matrix.

    Checks: numeric nonnegative (near-)integers, no all-NA rows, flags missing
    values, duplicated gene ids, and estimates how many low-count genes would be
    filtered (CPM-style). Genes are rows; ``sample_columns`` are the count cols.
    """
    errors: List[str] = []
    warnings: List[str] = []
    values = counts[sample_columns].apply(pd.to_numeric, errors="coerce")
    arr = values.to_numpy(dtype="float64")

    if values.shape[1] < min_samples:
        errors.append(f"Need at least {min_samples} sample columns; found {values.shape[1]}.")

    n_missing = int(np.isnan(arr).sum())
    if n_missing:
        warnings.append(f"{n_missing} missing/non-numeric count value(s) detected; "
                        "these must be resolved before DE (counts cannot be NA).")

    finite = arr[~np.isnan(arr)]
    if finite.size:
        if float((finite < 0).mean()) > 0:
            errors.append("Negative values found; raw counts must be nonnegative.")
        non_integer = float((finite != finite.round()).mean())
        if non_integer > 0.02:
            warnings.append(f"{non_integer:.0%} of values are non-integer; RSEM/expected counts "
                            "are rounded by edgeR. Confirm these are counts, not normalized values.")

    # Duplicate gene ids (row index).
    dup = int(pd.Index(counts.index).duplicated().sum())
    if dup:
        warnings.append(f"{dup} duplicated gene id(s); they will be made unique before analysis.")

    # Low-count gene estimate (informational; the R pipeline does the real filter).
    low = 0
    if finite.size and values.shape[1] >= 1:
        libsize = np.nansum(arr, axis=0)
        libsize[libsize == 0] = np.nan
        cpm = np.divide(arr, libsize) * 1e6
        expressed = np.nansum(cpm > 1, axis=1)
        low = int((expressed < max(1, min_samples)).sum())

    report = ValidationReport(
        ok=len(errors) == 0,
        errors=errors, warnings=warnings,
        summary={"n_genes": int(counts.shape[0]), "n_samples": int(values.shape[1]),
                 "n_missing": n_missing, "n_low_count_genes_est": low,
                 "sample_columns": list(sample_columns)},
    )
    return report


def validate_metadata(meta: pd.DataFrame, *, sample_id_col: Optional[str] = None,
                      group_col: Optional[str] = None,
                      count_samples: Optional[List[str]] = None) -> ValidationReport:
    """Validate sample metadata and (optionally) that sample IDs match counts."""
    errors: List[str] = []
    warnings: List[str] = []
    cols_lc = {c.lower(): c for c in meta.columns}

    sid = sample_id_col or next((cols_lc[k] for k in ("sampleid", "sample_id", "sample", "id")
                                 if k in cols_lc), None)
    grp = group_col or next((cols_lc[k] for k in ("group", "condition", "treatment", "genotype")
                             if k in cols_lc), None)
    if sid is None:
        errors.append("No sample-ID column found (expected e.g. 'SampleID').")
    if grp is None:
        errors.append("No condition/group column found (expected e.g. 'Group' or 'condition').")

    n_groups = 0
    if grp is not None:
        levels = meta[grp].astype(str).str.replace(" ", "_")
        n_groups = int(levels.nunique())
        counts_per = levels.value_counts()
        if n_groups < 2:
            errors.append(f"Group column '{grp}' has < 2 levels; DE needs >= 2 groups.")
        if (counts_per < 2).any():
            warnings.append("Some groups have < 2 replicates; DE power/estimates will be weak.")

    matched = None
    if sid is not None and count_samples is not None:
        meta_ids = set(meta[sid].astype(str))
        cnt_ids = set(map(str, count_samples))
        common = meta_ids & cnt_ids
        matched = len(common)
        if not common:
            errors.append("No sample IDs in the metadata match the count-matrix columns.")
        else:
            missing_in_counts = meta_ids - cnt_ids
            missing_in_meta = cnt_ids - meta_ids
            if missing_in_counts:
                warnings.append(f"{len(missing_in_counts)} metadata sample(s) not in counts "
                                "(will be dropped).")
            if missing_in_meta:
                warnings.append(f"{len(missing_in_meta)} count sample(s) not in metadata "
                                "(will be dropped).")

    return ValidationReport(
        ok=len(errors) == 0, errors=errors, warnings=warnings,
        summary={"sample_id_col": sid, "group_col": grp, "n_samples": int(meta.shape[0]),
                 "n_groups": n_groups, "matched_samples": matched},
    )
