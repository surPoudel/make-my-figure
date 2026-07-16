"""Validate a confirmed MatrixSpec (+ optional SampleMetadataSpec) before any
plot recommendation, transformation, or statistic. Returns a structured report;
never raises for ordinary data problems (they become errors/warnings the UI shows).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from make_my_figure_core.matrix_workflow.matrix_spec import MatrixSpec
from make_my_figure_core.matrix_workflow.metadata_spec import (
    SampleMetadataSpec,
    metadata_sample_match,
)


@dataclass
class ValidationReport:
    ok: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.ok = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def to_dict(self) -> Dict[str, Any]:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings,
                "summary": self.summary}


def validate_matrix(df: pd.DataFrame, spec: MatrixSpec,
                    metadata: Optional[SampleMetadataSpec] = None) -> ValidationReport:
    r = ValidationReport()
    if not spec.confirmed_by_user:
        r.add_error("Column mapping is not confirmed yet — confirm the MatrixSpec first.")

    if not spec.feature_id_column or spec.feature_id_column not in df.columns:
        r.add_error(f"Feature id column '{spec.feature_id_column}' not found.")
    value_cols = [c for c in spec.value_columns if c in df.columns]
    missing_val = [c for c in spec.value_columns if c not in df.columns]
    if missing_val:
        r.add_error(f"Value column(s) not found: {missing_val}.")
    if not value_cols:
        r.add_error("No value/sample columns selected.")

    # annotation columns must not overlap value columns
    overlap = set(spec.annotation_columns) & set(spec.value_columns)
    if overlap:
        r.add_error(f"Column(s) marked as both annotation and value: {sorted(overlap)}.")

    # numeric convertibility of value columns
    non_numeric = []
    n_missing = 0
    if value_cols:
        num = df[value_cols].apply(lambda s: pd.to_numeric(s, errors="coerce"))
        for c in value_cols:
            if not num[c].notna().any():
                non_numeric.append(c)
        n_missing = int(num.isna().sum().sum())
        if non_numeric:
            r.add_error(f"Value column(s) not numeric/convertible: {non_numeric}.")

    # duplicate feature ids
    n_dup = 0
    if spec.feature_id_column in df.columns:
        dup = df[spec.feature_id_column].astype(str)
        n_dup = int(dup.duplicated().sum())
        if n_dup:
            r.add_warning(f"{n_dup} duplicate feature id(s); "
                          f"resolve with duplicate_feature_policy (currently "
                          f"'{spec.duplicate_feature_policy}').")

    n_features = int(len(df))
    n_samples = len(value_cols)
    if n_missing:
        r.add_warning(f"{n_missing} missing/non-numeric value cell(s) "
                      f"(policy '{spec.missing_value_policy}').")
    if n_samples and n_samples < 2:
        r.add_warning("Only one sample/value column — most comparisons need >= 2.")

    groups: Dict[str, int] = {}
    if metadata is not None:
        match = metadata_sample_match(metadata, value_cols)
        r.summary["sample_match"] = match
        if metadata.sample_to_group and not match["matched"]:
            r.add_error("No metadata sample ids match the selected value columns.")
        elif match["in_matrix_not_metadata"]:
            r.add_warning(f"{len(match['in_matrix_not_metadata'])} value column(s) have no "
                          "group assignment.")
        groups = metadata.group_sizes()
        for g, n in groups.items():
            if n < 2:
                r.add_warning(f"Group '{g}' has only {n} sample(s).")

    r.summary.update({
        "n_features": n_features, "n_samples": n_samples,
        "n_annotation_columns": len([c for c in spec.annotation_columns if c in df.columns]),
        "n_groups": len(groups), "group_sizes": groups,
        "n_missing_values": n_missing, "n_duplicate_features": n_dup,
        "non_numeric_value_columns": non_numeric,
        "value_type": spec.value_type,
    })
    return r


def require_for_statistics(spec: MatrixSpec, metadata: Optional[SampleMetadataSpec]
                           ) -> ValidationReport:
    """Extra gate before a differential summary / group statistics run."""
    r = ValidationReport()
    if metadata is None or not metadata.confirmed_by_user:
        r.add_error("Confirm sample groups before running statistics.")
        return r
    if len([g for g, n in metadata.group_sizes().items() if n >= 1]) < 2:
        r.add_error("At least two groups are required for a differential summary.")
    if spec.value_type == "unknown_user_confirmed":
        r.add_warning("Value scale unconfirmed — fold change will report mean difference only.")
    return r
