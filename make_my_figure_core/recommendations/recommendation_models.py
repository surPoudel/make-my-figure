"""Data models for the figure recommendation engine.

These are frontend-agnostic dataclasses describing (a) a profiled table
(:class:`DataProfile`), and (b) a set of figure recommendations
(:class:`RecommendationSpec` of :class:`Recommendation`). Everything is
JSON-serialisable via ``to_dict()`` so a recommendation set can ride along with
a session/report.

Scope note: recommendations never include RNA-seq differential-expression
analysis. The engine plots *provided* data — generic numeric / expression-like
matrices and **precomputed** differential/feature-level results tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ColumnRole:
    """A detected semantic role for one column (best-guess, overridable)."""

    role: str                       # e.g. "group", "p_value", "logFC", "time"
    column: str
    confidence: float = 0.5
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"role": self.role, "column": self.column,
                "confidence": round(self.confidence, 3), "reason": self.reason}


@dataclass
class DataProfile:
    """A lightweight, cheap-to-compute profile of an uploaded table."""

    table_name: str
    n_rows: int
    n_cols: int
    column_kinds: Dict[str, str] = field(default_factory=dict)      # col -> kind
    numeric_columns: List[str] = field(default_factory=list)
    categorical_columns: List[str] = field(default_factory=list)
    datetime_columns: List[str] = field(default_factory=list)
    id_columns: List[str] = field(default_factory=list)
    binary_columns: List[str] = field(default_factory=list)
    missingness: Dict[str, float] = field(default_factory=dict)     # col -> fraction
    duplicate_id_columns: List[str] = field(default_factory=list)
    roles: List[ColumnRole] = field(default_factory=list)
    # matrix characterisation
    is_matrix: bool = False
    matrix_kind: Optional[str] = None       # "count_like" | "expression_like" | None
    matrix_feature_col: Optional[str] = None
    matrix_sample_columns: List[str] = field(default_factory=list)
    is_correlation_matrix: bool = False
    is_adjacency_matrix: bool = False
    notes: List[str] = field(default_factory=list)

    def role_column(self, role: str) -> Optional[str]:
        for r in self.roles:
            if r.role == role:
                return r.column
        return None

    def has_role(self, role: str) -> bool:
        return self.role_column(role) is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "column_kinds": self.column_kinds,
            "numeric_columns": self.numeric_columns,
            "categorical_columns": self.categorical_columns,
            "datetime_columns": self.datetime_columns,
            "id_columns": self.id_columns,
            "binary_columns": self.binary_columns,
            "missingness": {k: round(v, 4) for k, v in self.missingness.items()},
            "duplicate_id_columns": self.duplicate_id_columns,
            "roles": [r.to_dict() for r in self.roles],
            "is_matrix": self.is_matrix,
            "matrix_kind": self.matrix_kind,
            "matrix_feature_col": self.matrix_feature_col,
            "matrix_sample_columns": self.matrix_sample_columns,
            "is_correlation_matrix": self.is_correlation_matrix,
            "is_adjacency_matrix": self.is_adjacency_matrix,
            "notes": self.notes,
        }


@dataclass
class Recommendation:
    """A single recommended figure, with a one-click PlotSpec draft."""

    id: str
    plot_type: str
    display_name: str
    confidence: float
    why: str
    required_mappings: Dict[str, Any] = field(default_factory=dict)
    missing_mappings: List[str] = field(default_factory=list)
    suggested_statistics: Optional[Dict[str, Any]] = None
    suggested_style: str = "publication"
    suggested_thresholds: Dict[str, Any] = field(default_factory=dict)
    estimated_cost: str = "low"             # "low" | "medium" | "high"
    requires_confirmation: bool = False
    warnings: List[str] = field(default_factory=list)
    plot_spec_draft: Optional[Dict[str, Any]] = None
    # kind: "direct" (map existing columns), "transform" (reshape the data first,
    # then plot — carries a `transform` spec), or "guidance" (informational only:
    # explains what data/analysis is needed, e.g. run stats to get p/FDR/logFC).
    kind: str = "direct"
    transform: Optional[Dict[str, Any]] = None   # {name, params, result_columns, output_filename}
    instructions: Optional[str] = None           # how-to text for guidance recs

    @property
    def is_renderable(self) -> bool:
        """True when the rec can render the CURRENT data directly (kind='direct').

        Transform recs must reshape the data first; guidance recs are
        informational — neither renders the uploaded table as-is.
        """
        from make_my_figure_core.plots.registry import available_plot_types

        return (self.kind == "direct" and self.plot_spec_draft is not None
                and self.plot_type in available_plot_types())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "plot_type": self.plot_type,
            "display_name": self.display_name,
            "confidence": round(self.confidence, 3),
            "why": self.why,
            "required_mappings": self.required_mappings,
            "missing_mappings": self.missing_mappings,
            "suggested_statistics": self.suggested_statistics,
            "suggested_style": self.suggested_style,
            "suggested_thresholds": self.suggested_thresholds,
            "estimated_cost": self.estimated_cost,
            "requires_confirmation": self.requires_confirmation,
            "warnings": self.warnings,
            "plot_spec_draft": self.plot_spec_draft,
            "kind": self.kind,
            "transform": self.transform,
            "instructions": self.instructions,
        }


@dataclass
class RecommendationSpec:
    """The full set of recommendations produced from a table or an analysis."""

    table_name: str
    schema: str
    profile_summary: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[Recommendation] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def top(self) -> Optional[Recommendation]:
        return self.recommendations[0] if self.recommendations else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "schema": self.schema,
            "profile_summary": self.profile_summary,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "notes": self.notes,
        }
