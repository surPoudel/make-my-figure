"""Intelligent figure recommendation engine.

Profiles an uploaded table, detects its schema, and recommends appropriate
figures (existing renderers only) with one-click PlotSpec drafts. Never
recommends or runs RNA-seq differential-expression analysis — it plots the data
you provide (generic/expression-like matrices → heatmap/PCA/clustering;
precomputed differential results tables → volcano and related summaries).
"""

from make_my_figure_core.recommendations.data_profiler import profile_table
from make_my_figure_core.recommendations.plot_recommender import recommend_plots
from make_my_figure_core.recommendations.recommendation_models import (
    ColumnRole,
    DataProfile,
    Recommendation,
    RecommendationSpec,
)
from make_my_figure_core.recommendations.recommendation_runner import (
    recommend_after_analysis,
    recommend_for_table,
)
from make_my_figure_core.recommendations.schema_detector import SCHEMAS, detect_schema
from make_my_figure_core.recommendations.stat_recommender import suggest_stats

__all__ = [
    "profile_table",
    "detect_schema",
    "SCHEMAS",
    "recommend_plots",
    "recommend_for_table",
    "recommend_after_analysis",
    "suggest_stats",
    "ColumnRole",
    "DataProfile",
    "Recommendation",
    "RecommendationSpec",
]
