"""MatrixSpec: a *confirmed* column-role mapping for a feature-by-sample matrix.

The user explicitly confirms which column is the feature id, which are display /
annotation columns, and which are the numeric value (sample) columns. Nothing is
plotted or analysed from a matrix until a MatrixSpec is ``confirmed_by_user``.
This module also produces *suggestions* (never auto-applied) to prefill a mapping
wizard — the user always confirms.

Frontend-agnostic, pure pandas/numpy. This is a generic *feature matrix* layer
(expression / protein / metabolite / any feature-by-sample numeric matrix); it is
not an RNA-seq pipeline and does no raw-count differential expression.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from make_my_figure_core.version import __version__

# Confirmed nature of the numeric values (drives fold-change rules downstream).
VALUE_TYPES = ("normalized", "log_normalized", "raw_numeric", "unknown_user_confirmed")
MISSING_VALUE_POLICIES = ("keep", "drop_features", "zero", "mean_impute")
DUPLICATE_FEATURE_POLICIES = ("keep", "first", "mean", "max_variance")


@dataclass
class MatrixSpec:
    """A user-confirmed role mapping over the columns of a feature matrix."""

    source_file: Optional[str] = None
    feature_id_column: Optional[str] = None
    feature_display_column: Optional[str] = None
    annotation_columns: List[str] = field(default_factory=list)
    value_columns: List[str] = field(default_factory=list)
    excluded_columns: List[str] = field(default_factory=list)
    value_type: str = "unknown_user_confirmed"
    missing_value_policy: str = "keep"
    duplicate_feature_policy: str = "keep"
    confirmed_by_user: bool = False
    created_at: Optional[str] = None
    app_version: str = __version__

    # --- serialization ---------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MatrixSpec":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (d or {}).items() if k in known})

    # --- convenience -----------------------------------------------------
    def feature_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return the value matrix indexed by feature id (never mutates ``df``)."""
        if self.feature_id_column and self.feature_id_column in df.columns:
            work = df.set_index(self.feature_id_column)
        else:
            work = df.copy()
        cols = [c for c in self.value_columns if c in work.columns]
        return work[cols].apply(lambda s: pd.to_numeric(s, errors="coerce"))

    def display_labels(self, df: pd.DataFrame) -> Optional[pd.Series]:
        col = self.feature_display_column
        if col and col in df.columns:
            return df[col].astype(str)
        return None


def suggest_matrix_spec(df: pd.DataFrame, *, source_file: Optional[str] = None,
                        max_annotation_levels: int = 24) -> MatrixSpec:
    """Suggest (do NOT confirm) a column-role mapping for ``df``.

    - feature id: first non-numeric column (else the first column);
    - feature display: a second, higher-cardinality text column if present;
    - value columns: numeric columns that look like per-sample measurements;
    - annotation columns: everything else (text + integer-coded low-cardinality
      numeric columns like ``annotationLevel``).

    Returns a MatrixSpec with ``confirmed_by_user=False``. The value_type is left
    ``unknown_user_confirmed`` — scale is never inferred silently.
    """
    from make_my_figure_core.plots._v04_shared import classify_matrix_columns

    cols = list(df.columns)
    if not cols:
        return MatrixSpec(source_file=source_file)
    numeric_flags = {c: pd.to_numeric(df[c], errors="coerce").notna().any() for c in cols}
    text_cols = [c for c in cols if not numeric_flags[c]]

    feature_id = text_cols[0] if text_cols else cols[0]
    # display: a different text column, prefer the one with the most distinct values
    display = None
    other_text = [c for c in text_cols if c != feature_id]
    if other_text:
        display = max(other_text, key=lambda c: df[c].astype(str).nunique())

    candidates = [c for c in cols if c != feature_id and numeric_flags[c]]
    value_cols, annot_numeric = classify_matrix_columns(df, candidates,
                                                        max_levels=max_annotation_levels)
    annotation_cols = [c for c in cols
                       if c not in (feature_id, display) and c not in value_cols]
    return MatrixSpec(
        source_file=source_file,
        feature_id_column=feature_id,
        feature_display_column=display,
        annotation_columns=annotation_cols,
        value_columns=value_cols,
        excluded_columns=[],
        value_type="unknown_user_confirmed",
        confirmed_by_user=False,
    )


def looks_log_scale(df: pd.DataFrame, value_columns: List[str]) -> bool:
    """Heuristic ONLY (to prompt the user): values look log-scaled when they are
    modest-magnitude and can be negative (e.g. log-transformed abundance). Never used to
    decide fold-change without explicit user confirmation of ``value_type``.
    """
    cols = [c for c in value_columns if c in df.columns]
    if not cols:
        return False
    vals = df[cols].apply(lambda s: pd.to_numeric(s, errors="coerce")).to_numpy(dtype=float)
    finite = vals[np.isfinite(vals)]
    if finite.size == 0:
        return False
    return bool(finite.min() < 0 or finite.max() < 40)
