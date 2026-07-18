"""Canonical plot-editor handoff (frontend-agnostic).

The Matrix Workflow prepares and validates data, then hands a **plot-ready** dataset
to the *same* plot editor the normal (quick-plot) workflow uses — so there is one
source of truth for plot controls, PlotSpec generation, rendering, annotations,
export, and Figure Builder. There is no second, reduced Matrix-only plot UI.

A :class:`PlotEditorHandoff` carries everything the editor needs to open a
recommendation with full controls:

* ``plot_type`` — the canonical registry plot type,
* ``data`` — the plot-ready derived dataset,
* ``mappings`` — suggested column mappings (the user can still change them),
* ``aux`` — auxiliary tables (e.g. PCA sample metadata),
* ``spec_extra`` — extra top-level PlotSpec keys (e.g. ``column_annotations``),
* ``defaults`` — suggested option defaults (e.g. a suggested significance field),
* ``provenance`` — matrix/metadata/preprocessing/stats/workbook source, stored on the
  PlotSpec ``source`` block so exports and Figure Builder panels stay traceable.

Both Desktop and Streamlit build the same object; only the "open" step differs
(loading a Qt workbench vs. Streamlit session state).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class PlotEditorHandoff:
    """A self-contained request to open one recommendation in the full plot editor."""

    plot_type: str
    data: pd.DataFrame
    mappings: Dict[str, Any] = field(default_factory=dict)
    aux: Dict[str, pd.DataFrame] = field(default_factory=dict)
    spec_extra: Dict[str, Any] = field(default_factory=dict)
    defaults: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)
    table_name: str = "matrix_derived"
    source_workflow: str = "matrix"
    return_target: str = "matrix_workflow"
    warnings: List[str] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        """Small dict for a UI provenance banner (no DataFrames)."""
        return {
            "plot_type": self.plot_type,
            "table_name": self.table_name,
            "source_workflow": self.source_workflow,
            "n_rows": int(len(self.data)) if self.data is not None else 0,
            "provenance": dict(self.provenance),
        }


def matrix_source_id(matrix_spec) -> str:
    """Stable short id for a confirmed matrix mapping (for provenance/caching)."""
    parts = [
        str(getattr(matrix_spec, "source_file", "") or ""),
        str(getattr(matrix_spec, "source_sheet", "") or ""),
        str(getattr(matrix_spec, "feature_id_column", "") or ""),
        ",".join(map(str, getattr(matrix_spec, "value_columns", []) or [])),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]


def build_matrix_provenance(
    matrix_spec,
    *,
    metadata=None,
    preprocessing: Optional[List[str]] = None,
    statistics: Optional[Dict[str, Any]] = None,
    workbook_name: Optional[str] = None,
    sheet_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble the PlotSpec ``source`` block for a Matrix-Workflow handoff.

    Only includes fields that are available; safe to call with just ``matrix_spec``.
    The worksheet fields (``source_workbook_name`` / ``source_sheet_name``) are kept
    at the top level so the existing multi-sheet provenance consumers keep working.
    """
    ms = matrix_spec
    prov: Dict[str, Any] = {
        "source_workflow": "matrix",
        "source_matrix_id": matrix_source_id(ms),
        "source_matrix": {
            "feature_id": getattr(ms, "feature_id_column", None),
            "n_value_columns": len(getattr(ms, "value_columns", []) or []),
            "value_type": getattr(ms, "value_type", None),
        },
    }
    wb = workbook_name or getattr(ms, "source_workbook", None)
    sh = sheet_name or getattr(ms, "source_sheet", None)
    if wb:
        prov["source_workbook_name"] = wb
    if sh:
        prov["source_sheet_name"] = sh
    if getattr(ms, "source_sheet_index", None) is not None:
        prov["source_sheet_index"] = ms.source_sheet_index
    if metadata is not None and getattr(metadata, "confirmed_by_user", False):
        groups = sorted({str(g) for g in (getattr(metadata, "sample_to_group", {}) or {}).values()})
        prov["source_metadata"] = {
            "group_column": getattr(metadata, "group_column", None),
            "groups": groups,
            "source_metadata_id": hashlib.sha256(
                ("meta|" + ",".join(groups)).encode("utf-8")).hexdigest()[:12],
        }
    if preprocessing:
        prov["source_preprocessing"] = list(preprocessing)
        prov["source_preprocessing_id"] = hashlib.sha256(
            ("prep|" + ",".join(map(str, preprocessing))).encode("utf-8")).hexdigest()[:12]
    if statistics:
        prov["source_statistics"] = dict(statistics)
        sid_seed = str(statistics.get("method") or statistics.get("test") or statistics)
        prov["source_stats_id"] = hashlib.sha256(
            ("stats|" + sid_seed).encode("utf-8")).hexdigest()[:12]
    return prov
