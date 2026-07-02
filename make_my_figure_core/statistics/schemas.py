"""StatsSpec: the serializable statistics configuration + results sidecar.

A StatsSpec is a plain dict embedded inside a PlotSpec under the ``statistics``
key (config only) and, after running, exported alongside the figure as a
``*.stats_spec.json`` sidecar that also carries the computed results and method
report. This module provides light validation + normalization and the default
config, so the config shape is stable across the desktop app, Streamlit, and the
CLI.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from make_my_figure_core.statistics.models import StatsReport
from make_my_figure_core.statistics.multiple_testing import canonical_method

VALID_TESTS = {
    "auto", "students_t", "welch_t", "mann_whitney", "paired_t", "wilcoxon",
    "one_way_anova", "two_way_anova", "rm_anova", "kruskal_wallis",
    "chi_square", "fishers_exact", "logrank", "cox_ph",
    "pearson", "spearman", "linear_regression",
}
VALID_MODES = {"auto", "all_pairs", "vs_control", "selected_pairs", "within_x", "omnibus"}
VALID_ANNOTATION_MODES = {"stars", "p", "both"}


def default_annotation() -> Dict[str, Any]:
    return {
        "mode": "stars",              # stars | p | both
        "digits": 3,
        "sci_threshold": 1e-3,
        "show_effect": False,
        "show_nonsignificant": True,  # draw a bracket even when ns
        "font_size": None,            # None -> style.annotation_pt
        "line_width": None,           # None -> style-derived
        "bracket_height_frac": 0.03,  # bracket tick height, fraction of y-range
        "gap_frac": 0.06,             # vertical gap between stacked brackets
        "top_margin_frac": 0.12,      # extra headroom added above the data
    }


def default_stats_spec() -> Dict[str, Any]:
    return {
        "enabled": False,
        "test": "auto",
        "comparison_mode": "auto",
        "correction": "benjamini_hochberg",
        "alpha": 0.05,
        "alternative": "two-sided",
        "posthoc": False,
        "posthoc_test": "welch_t",
        "value_column": None,
        "group_column": None,
        "subgroup_column": None,
        "subject_column": None,
        "time_column": None,
        "event_column": None,
        "x_column": None,
        "y_column": None,
        "row_column": None,
        "col_column": None,
        "reference_group": None,
        "selected_pairs": None,
        "annotate": True,
        "annotation": default_annotation(),
    }


def normalize_stats_spec(spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Fill defaults and normalize enum-ish fields. Never raises for unknown
    keys (they are preserved) so forward-compatible specs still load."""
    out = default_stats_spec()
    if not spec:
        return out
    out.update({k: v for k, v in spec.items() if k != "annotation"})
    ann = default_annotation()
    ann.update(spec.get("annotation", {}) or {})
    out["annotation"] = ann
    # normalize
    if out.get("test") not in VALID_TESTS:
        out["test"] = "auto"
    if out.get("comparison_mode") not in VALID_MODES:
        out["comparison_mode"] = "auto"
    out["correction"] = canonical_method(out.get("correction"))
    if ann.get("mode") not in VALID_ANNOTATION_MODES:
        ann["mode"] = "stars"
    try:
        alpha = float(out.get("alpha", 0.05))
        out["alpha"] = alpha if 0 < alpha < 1 else 0.05
    except (TypeError, ValueError):
        out["alpha"] = 0.05
    return out


def validate_stats_spec(spec: Dict[str, Any]) -> List[str]:
    """Return a list of human-readable problems (empty if OK)."""
    errors: List[str] = []
    if not isinstance(spec, dict):
        return ["StatsSpec must be an object."]
    if spec.get("test") not in VALID_TESTS:
        errors.append(f"test '{spec.get('test')}' is not recognized.")
    if spec.get("comparison_mode") not in VALID_MODES:
        errors.append(f"comparison_mode '{spec.get('comparison_mode')}' is not recognized.")
    a = spec.get("alpha", 0.05)
    try:
        if not (0 < float(a) < 1):
            errors.append("alpha must be between 0 and 1.")
    except (TypeError, ValueError):
        errors.append("alpha must be numeric.")
    return errors


def stats_sidecar_payload(stats_spec: Dict[str, Any], report: StatsReport) -> Dict[str, Any]:
    """Build the ``*.stats_spec.json`` payload (config + results + methods)."""
    return {
        "stats_spec": normalize_stats_spec(stats_spec),
        "results": [r.to_dict() for r in report.results],
        "method_paragraph": report.method_paragraph,
        "legend_sentence": report.legend_sentence,
        "correction_method": report.correction_method,
        "warnings": list(report.warnings),
        "software_versions": dict(report.software_versions),
        "disclaimer": (
            "Statistical results were computed by Make My Figure. Users are responsible "
            "for choosing tests appropriate to their experimental design; these results "
            "do not replace statistical review."
        ),
    }
