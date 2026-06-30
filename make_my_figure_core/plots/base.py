"""Shared helpers and result type for plot renderers.

Every renderer receives a validated ``spec`` (PlotSpec dict), a loaded
``pandas.DataFrame``, and a resolved :class:`StyleProfile`, and returns a
:class:`RenderResult` carrying the figure plus a metadata record. Renderers
never mutate their input DataFrame in place (acceptance criterion: "no
renderer mutates input data silently").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from make_my_figure_core.styles.engine import StyleProfile


class RenderError(Exception):
    """Raised when a spec/data combination cannot be rendered."""


@dataclass
class RenderResult:
    """A rendered figure plus a reproducibility/metadata record."""

    figure: Figure
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


# --- small validation helpers ------------------------------------------------

def require_columns(df: pd.DataFrame, columns: List[str], *, context: str) -> None:
    missing = [c for c in columns if c and c not in df.columns]
    if missing:
        raise RenderError(
            f"{context}: missing required column(s) {missing}. "
            f"Available columns: {list(df.columns)}"
        )


def get_mapping(spec: Dict[str, Any], key: str, default: Any = None,
                *, required: bool = False, context: str = "mapping") -> Any:
    mapping = spec.get("mapping", {}) or {}
    value = mapping.get(key, default)
    if required and (value is None or value == ""):
        raise RenderError(f"{context}: mapping '{key}' is required.")
    return value


def coerce_numeric(df: pd.DataFrame, column: str, *, context: str) -> pd.Series:
    """Return a numeric copy of a column, raising if nothing is numeric."""
    series = pd.to_numeric(df[column], errors="coerce")
    if series.notna().sum() == 0:
        raise RenderError(f"{context}: column '{column}' has no numeric values.")
    return series


# --- statistics helpers ------------------------------------------------------

def summarize_error(values: np.ndarray, method: str) -> tuple[float, float]:
    """Return ``(center, error)`` for an array given an error method.

    ``method`` is one of ``sem``, ``sd``/``std``, ``ci95``, or ``none``.
    Center is always the mean. NaNs are dropped.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        return (np.nan, 0.0)
    mean = float(np.mean(arr))
    method = (method or "sem").lower()
    if arr.size < 2 or method == "none":
        return (mean, 0.0)
    sd = float(np.std(arr, ddof=1))
    if method in ("sd", "std"):
        return (mean, sd)
    sem = sd / np.sqrt(arr.size)
    if method == "sem":
        return (mean, sem)
    if method in ("ci", "ci95", "ci_95"):
        # Normal approximation 95% CI half-width.
        return (mean, 1.96 * sem)
    # Unknown -> default to SEM.
    return (mean, sem)


def figure_size(spec: Dict[str, Any], style: StyleProfile, *, aspect: float) -> tuple[float, float]:
    """Resolve figure size, honoring an optional layout['column_width'] hint."""
    width = (spec.get("layout", {}) or {}).get("column_width", "single")
    width = "double" if str(width).lower() == "double" else "single"
    return style.figure_size_inches(width, aspect=aspect)


def style_axes(ax) -> None:
    """Apply lightweight common axis cosmetics (ticks outward, no top/right)."""
    ax.tick_params(direction="out", length=2.5)
    for spine in ("top", "right"):
        if spine in ax.spines:
            ax.spines[spine].set_visible(False)


def base_metadata(spec: Dict[str, Any], style: StyleProfile, df: pd.DataFrame,
                  *, used_columns: List[str]) -> Dict[str, Any]:
    """Construct the common metadata block recorded for every figure."""
    output = spec.get("output", {}) or {}
    return {
        "plot_type": spec.get("plot_type"),
        "style_profile": style.name,
        "data_columns_used": [c for c in used_columns if c],
        "n_rows": int(len(df)),
        "statistics": dict(spec.get("statistics", {}) or {}),
        "export_dimensions": {
            "width_mm": output.get("width_mm"),
            "height_mm": output.get("height_mm"),
            "dpi": output.get("dpi"),
        },
        "disclaimer": (
            f"Formatted with '{style.name}' submission-like aesthetics. "
            "Not an official journal template; verify against author guidelines."
        ),
    }
