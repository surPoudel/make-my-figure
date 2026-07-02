"""Reusable statistics engine for Make My Figure.

Frontend-agnostic: statistical tests, effect sizes, multiple-testing correction,
survival statistics, categorical tests, transparent method reporting, and the
StatsSpec config/result sidecar. Both the Streamlit and desktop apps call
:func:`run_statistics`.

Guiding principle: never fabricate a p-value. Tests are advisory to select but
fully transparent to report - exact test, groups, sample size, pairing,
p-value, adjusted p-value, correction method, effect size, and confidence
interval are all recorded on each :class:`StatResult`.
"""

from make_my_figure_core.statistics.models import (
    StatResult,
    StatsReport,
    StatsError,
)
from make_my_figure_core.statistics.runner import run_statistics
from make_my_figure_core.statistics.test_registry import TESTS, TestInfo, recommend_tests
from make_my_figure_core.statistics.multiple_testing import (
    adjust_pvalues,
    apply_correction,
    canonical_method,
)
from make_my_figure_core.statistics.schemas import (
    default_stats_spec,
    normalize_stats_spec,
    validate_stats_spec,
    stats_sidecar_payload,
)
from make_my_figure_core.statistics.annotations import (
    AnnotationItem,
    build_pairwise_annotations,
    stat_text_panel,
)
from make_my_figure_core.statistics import method_reporting

__all__ = [
    "StatResult",
    "StatsReport",
    "StatsError",
    "run_statistics",
    "TESTS",
    "TestInfo",
    "recommend_tests",
    "adjust_pvalues",
    "apply_correction",
    "canonical_method",
    "default_stats_spec",
    "normalize_stats_spec",
    "validate_stats_spec",
    "stats_sidecar_payload",
    "AnnotationItem",
    "build_pairwise_annotations",
    "stat_text_panel",
    "method_reporting",
]
