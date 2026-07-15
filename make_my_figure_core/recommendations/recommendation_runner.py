"""Single entrypoints for the figure recommendation engine.

``recommend_for_table`` profiles a freshly-uploaded table and returns a
:class:`RecommendationSpec`. ``recommend_after_analysis`` suggests follow-up
figures once the user has run statistics or has a precomputed differential
results table.

No RNA-seq differential-expression analysis is ever recommended or triggered;
profiling is cheap and anything potentially expensive is flagged
``requires_confirmation``.
"""

from __future__ import annotations

from typing import Any, List, Optional

import pandas as pd

from make_my_figure_core.recommendations.data_profiler import profile_table
from make_my_figure_core.recommendations.plot_recommender import recommend_plots
from make_my_figure_core.recommendations.recommendation_models import (
    Recommendation,
    RecommendationSpec,
)
from make_my_figure_core.recommendations.schema_detector import detect_schema
from make_my_figure_core.recommendations.stat_recommender import suggest_stats

_DE_NOTE = ("Make My Figure does not run differential-expression analysis. Upload a "
            "precomputed differential results table (fold-change + p-value/FDR) for volcano "
            "or MA-style plots.")


def recommend_for_table(df: pd.DataFrame, table_name: str = "data") -> RecommendationSpec:
    """Profile ``df`` and recommend appropriate figures (cheap; no heavy analysis)."""
    profile = profile_table(df, table_name)
    schema = detect_schema(profile, df)
    recs = recommend_plots(profile, schema, df, table_name)

    notes: List[str] = []
    if schema in ("numeric_matrix", "expression_like_matrix", "matrix_plus_metadata"):
        notes.append("For group comparison plots, use 'Define groups' to tag samples, then "
                     "box/violin/bar plots become available.")
        notes.append(_DE_NOTE)
    if schema == "unknown":
        notes.append("Could not confidently detect a schema — pick a plot type manually or "
                     "check column headers.")

    return RecommendationSpec(
        table_name=table_name, schema=schema,
        profile_summary=profile.to_dict(), recommendations=recs, notes=notes)


def recommend_after_analysis(df: pd.DataFrame, *, stats_report: Any = None,
                             differential: bool = False, has_matrix: bool = False,
                             table_name: str = "data") -> RecommendationSpec:
    """Suggest follow-up figures after statistics were run or a differential table exists."""
    profile = profile_table(df, table_name)
    recs: List[Recommendation] = []
    notes: List[str] = []

    if stats_report is not None:
        # After group statistics: annotated distribution + effect-size views.
        grp = profile.role_column("group")
        vals = [c for c in profile.numeric_columns]
        cm = {"x": grp, "y": vals[0] if vals else None}
        base = recommend_plots(profile, "generic_long", df, table_name)
        for r in base:
            if r.plot_type == "boxplot_or_violin_with_points":
                r.why = ("Statistics were computed — an annotated box/violin plot displays the "
                         "groups with significance brackets.")
                r.confidence = 0.85
                recs.append(r)
        notes.append("Add significance annotations from the computed statistics before export.")

    if differential:
        diff = recommend_plots(profile, "precomputed_differential", df, table_name)
        recs.extend(diff)
        if has_matrix:
            notes.append("A compatible matrix is available — a top-feature heatmap of the most "
                         "significant features is also recommended (select features, then heatmap).")

    if not recs:
        # Fall back to the standard table recommendations.
        return recommend_for_table(df, table_name)

    recs.sort(key=lambda r: r.confidence, reverse=True)
    schema = "post_analysis"
    return RecommendationSpec(table_name=table_name, schema=schema,
                              profile_summary=profile.to_dict(),
                              recommendations=recs, notes=notes)
