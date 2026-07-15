"""Thin wrapper over the statistics test recommender.

Keeps the recommendation engine's dependency on the statistics package in one
place and shields it from import errors (returns an empty suggestion instead of
raising, so figure recommendations still work if stats are unavailable).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd


def suggest_stats(plot_type: str, mapping: Dict[str, Any],
                  df: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
    """Return ``{"suggested", "primary", "notes"}`` or ``None``.

    Delegates to :func:`make_my_figure_core.statistics.recommend_tests`. Never
    raises — a failure yields ``None`` so the caller simply omits a stats hint.
    """
    try:
        from make_my_figure_core.statistics import recommend_tests

        rec = recommend_tests(plot_type, mapping, df=df)
    except Exception:
        return None
    if not rec or not (rec.get("suggested") or rec.get("primary")):
        return None
    return rec
