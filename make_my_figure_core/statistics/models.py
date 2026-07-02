"""Core data models for the statistics engine.

A :class:`StatResult` is the single, serializable record produced by every
statistical test. It carries everything needed for transparent reporting: the
exact test, the groups compared, sample sizes, the statistic, p-value, adjusted
p-value, effect size, confidence interval, assumptions, warnings, and a
human-readable method sentence. Figures may only display a p-value that comes
from a stored :class:`StatResult` (never a decorative label).

Design note: plain dataclasses (not pydantic) to match the rest of the core,
which has no pydantic dependency. ``to_dict``/``from_dict`` give a stable JSON
shape for the StatsSpec sidecar.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


def _clean(value: Any) -> Any:
    """Make a value JSON-safe (NaN/inf -> None, numpy scalars -> python)."""
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    # numpy scalar?
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            return _clean(value.item())
        except Exception:
            return value
    return value


@dataclass
class StatResult:
    """One statistical comparison, fully described for reproducible reporting."""

    test_id: str
    test_name: str
    plot_type: Optional[str] = None
    comparison_type: str = "two_group"  # two_group | multi_group | omnibus | correlation | survival | categorical | regression
    grouping_columns: List[str] = field(default_factory=list)
    value_column: Optional[str] = None
    group_a: Optional[str] = None
    group_b: Optional[str] = None
    paired_id_column: Optional[str] = None
    block_column: Optional[str] = None  # blocking / repeated-measures factor
    n_total: Optional[int] = None
    n_by_group: Dict[str, int] = field(default_factory=dict)
    statistic: Optional[float] = None
    statistic_name: Optional[str] = None
    df: Optional[float] = None            # degrees of freedom (or "df1, df2" via df2)
    df2: Optional[float] = None
    p_value: Optional[float] = None
    adjusted_p_value: Optional[float] = None
    correction_method: Optional[str] = None
    reject_null: Optional[bool] = None    # decision at alpha, using adjusted p when present
    alpha: float = 0.05
    effect_size_name: Optional[str] = None
    effect_size: Optional[float] = None
    effect_ci_low: Optional[float] = None
    effect_ci_high: Optional[float] = None
    confidence_interval_low: Optional[float] = None   # CI on the estimate (e.g. mean diff, HR)
    confidence_interval_high: Optional[float] = None
    ci_level: float = 0.95
    estimate: Optional[float] = None      # the point estimate the CI refers to
    estimate_name: Optional[str] = None
    alternative: str = "two-sided"
    paired: bool = False
    assumptions_checked: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    missing_data_policy: str = "listwise deletion (drop non-finite values)"
    method_sentence: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)
    reproducibility: Dict[str, Any] = field(default_factory=dict)
    software_versions: Dict[str, str] = field(default_factory=dict)

    # --- convenience --------------------------------------------------------
    @property
    def display_p(self) -> Optional[float]:
        """The p-value that decisions/labels should use (adjusted if present)."""
        return self.adjusted_p_value if self.adjusted_p_value is not None else self.p_value

    @property
    def comparison_label(self) -> str:
        if self.group_a is not None and self.group_b is not None:
            return f"{self.group_a} vs {self.group_b}"
        if self.grouping_columns:
            return " x ".join(self.grouping_columns)
        return self.value_column or self.test_name

    def to_dict(self) -> Dict[str, Any]:
        return _clean(asdict(self))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StatResult":
        known = {f: data[f] for f in cls.__dataclass_fields__ if f in data}
        return cls(**known)


@dataclass
class StatsReport:
    """A collection of :class:`StatResult` plus overall method reporting."""

    results: List[StatResult] = field(default_factory=list)
    correction_method: Optional[str] = None
    method_paragraph: str = ""
    legend_sentence: str = ""
    warnings: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    software_versions: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "results": [r.to_dict() for r in self.results],
            "correction_method": self.correction_method,
            "method_paragraph": self.method_paragraph,
            "legend_sentence": self.legend_sentence,
            "warnings": list(self.warnings),
            "config": _clean(self.config),
            "software_versions": dict(self.software_versions),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StatsReport":
        return cls(
            results=[StatResult.from_dict(r) for r in data.get("results", [])],
            correction_method=data.get("correction_method"),
            method_paragraph=data.get("method_paragraph", ""),
            legend_sentence=data.get("legend_sentence", ""),
            warnings=list(data.get("warnings", [])),
            config=data.get("config", {}) or {},
            software_versions=data.get("software_versions", {}) or {},
        )


class StatsError(Exception):
    """Raised when a statistical design is invalid or a test cannot be run.

    Carries user-facing messages so the GUI can show a friendly validation
    error instead of returning a questionable p-value.
    """

    def __init__(self, messages):
        if isinstance(messages, str):
            messages = [messages]
        self.messages = list(messages)
        super().__init__("; ".join(self.messages))
