"""Column roles for an ordinary experimental table.

A feature matrix has one shape (features x samples). An experimental table has
whatever columns the experimenter recorded, under whatever names they chose:
``sample id``, ``treatment``, ``colony id``, ``bee body size_mm``, ``total
quantity``. Which column is the measured response, which are factors, which is a
covariate and which identifies the independent experimental unit is a scientific
decision the software cannot make from the numbers. A numeric column may be a
response, a covariate, or a factor coded as numbers (``time`` = 2, 4).

So roles are *assigned by the user*. :func:`suggest_roles` offers an advisory
guess with its reason; :class:`ColumnRoles` holds the user's decision, and a
manual assignment always replaces the suggestion.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, List, Optional

import pandas as pd

ROLES = ("identifier", "response", "factor", "time", "covariate", "subject", "label", "metadata", "ignore")
ROLE_LABELS = {
    "identifier": "Identifier (one per row)",
    "response": "Response (measured value)",
    "factor": "Factor / group",
    "time": "Time",
    "covariate": "Covariate (continuous)",
    "subject": "Subject / colony (experimental unit)",
    "label": "Label",
    "metadata": "Other metadata",
    "ignore": "Ignore",
}
_ID_WORDS = ("id", "identifier", "sample", "name", "barcode", "code")
_SUBJECT_WORDS = ("colony", "subject", "patient", "animal", "individual", "plot", "block",
                  "hive", "mouse", "donor", "replicate", "site")
_TIME_WORDS = ("time", "day", "hour", "week", "month", "year", "visit", "timepoint", "date")


@dataclass
class RoleSuggestion:
    column: str
    role: str
    reason: str


@dataclass
class ColumnRoles:
    """The user's role assignment. Columns not listed are 'metadata'."""

    roles: Dict[str, str] = field(default_factory=dict)
    factor_order: List[str] = field(default_factory=list)   # first = primary group

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ColumnRoles":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (d or {}).items() if k in known})

    def set(self, column: str, role: str) -> None:
        if role not in ROLES:
            raise ValueError(f"Unknown role {role!r}; choose one of {', '.join(ROLES)}.")
        self.roles[column] = role
        if role == "factor" and column not in self.factor_order:
            self.factor_order.append(column)
        if role != "factor" and column in self.factor_order:
            self.factor_order.remove(column)

    def columns(self, role: str) -> List[str]:
        if role == "factor":
            listed = [c for c in self.factor_order if self.roles.get(c) == "factor"]
            return listed + [c for c, r in self.roles.items() if r == "factor" and c not in listed]
        return [c for c, r in self.roles.items() if r == role]

    def role_of(self, column: str) -> str:
        return self.roles.get(column, "metadata")


def _words(name: str) -> List[str]:
    import re

    return [w for w in re.split(r"[^a-z0-9]+", str(name).lower()) if w]


def suggest_roles(df: pd.DataFrame) -> List[RoleSuggestion]:
    """Advisory role per column, with the reason. Never applied without the user."""
    out: List[RoleSuggestion] = []
    n = len(df)
    for col in df.columns:
        s = df[col]
        words = _words(col)
        nunique = int(s.dropna().nunique())
        numeric = pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)
        if any(w in _SUBJECT_WORDS for w in words):
            reason = "name suggests the experimental unit (repeated rows from one unit are not independent)"
            out.append(RoleSuggestion(col, "subject", reason))
        elif any(w in _ID_WORDS for w in words) and nunique == n and n > 0:
            out.append(RoleSuggestion(col, "identifier", "one distinct value per row"))
        elif any(w in _TIME_WORDS for w in words):
            out.append(RoleSuggestion(col, "time", "name suggests time; use it as a factor if only a few "
                                                    "time points were sampled"))
        elif not numeric:
            if nunique == n and n > 20:
                out.append(RoleSuggestion(col, "label", "text with one distinct value per row"))
            elif nunique == n:
                out.append(RoleSuggestion(col, "factor", f"text with {nunique} level(s) — each level "
                                                         "occurs once, so it has no replication"))
            else:
                out.append(RoleSuggestion(col, "factor", f"text with {nunique} level(s)"))
        elif nunique <= 1:
            out.append(RoleSuggestion(col, "metadata", "constant — every row has the same value"))
        else:
            out.append(RoleSuggestion(col, "response", "numeric measurement (could also be a covariate)"))
    return out


def roles_from_suggestions(suggestions: List[RoleSuggestion]) -> ColumnRoles:
    roles = ColumnRoles()
    for s in suggestions:
        roles.set(s.column, s.role)
    return roles


def validate_roles(df: pd.DataFrame, roles: ColumnRoles) -> List[str]:
    """Problems with an assignment (empty when usable)."""
    problems: List[str] = []
    for col, role in roles.roles.items():
        if col not in df.columns:
            problems.append(f"{col!r} has a role but is not in the table.")
            continue
        if role in ("response", "covariate"):
            coerced = pd.to_numeric(df[col], errors="coerce")
            bad = int((coerced.isna() & df[col].notna()).sum())
            if bad:
                problems.append(f"{col!r} is a {role} but {bad} value(s) are not numbers.")
    return problems
