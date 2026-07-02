"""Registry of statistical tests and an advisory recommendation system.

The registry records, for each test, a human label, its family, and design
requirements (min groups, whether pairing/subjects are needed). The
:func:`recommend_tests` helper is *advisory only*: given a plot type and column
mapping it suggests plausible tests, but never auto-runs them or claims one is
correct for the user's design.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass(frozen=True)
class TestInfo:
    test_id: str
    label: str
    family: str            # two_group | omnibus | correlation | regression | survival | categorical | posthoc
    parametric: Optional[bool] = None
    requires_pairing: bool = False
    requires_subject: bool = False
    min_groups: int = 2
    max_groups: Optional[int] = None
    notes: str = ""


TESTS: Dict[str, TestInfo] = {
    "students_t": TestInfo("students_t", "Student's t-test", "two_group", True, min_groups=2, max_groups=2),
    "welch_t": TestInfo("welch_t", "Welch's t-test", "two_group", True, min_groups=2, max_groups=2),
    "mann_whitney": TestInfo("mann_whitney", "Mann-Whitney U test", "two_group", False, min_groups=2, max_groups=2),
    "paired_t": TestInfo("paired_t", "Paired t-test", "two_group", True, requires_pairing=True, requires_subject=True, min_groups=2, max_groups=2),
    "wilcoxon": TestInfo("wilcoxon", "Wilcoxon signed-rank test", "two_group", False, requires_pairing=True, requires_subject=True, min_groups=2, max_groups=2),
    "one_way_anova": TestInfo("one_way_anova", "One-way ANOVA", "omnibus", True, min_groups=3),
    "two_way_anova": TestInfo("two_way_anova", "Two-way ANOVA", "omnibus", True, min_groups=2),
    "rm_anova": TestInfo("rm_anova", "Repeated-measures ANOVA", "omnibus", True, requires_subject=True, min_groups=2),
    "kruskal_wallis": TestInfo("kruskal_wallis", "Kruskal-Wallis test", "omnibus", False, min_groups=3),
    "dunn": TestInfo("dunn", "Dunn's test (post-hoc)", "posthoc", False, min_groups=3),
    "chi_square": TestInfo("chi_square", "Chi-square test", "categorical", None, min_groups=2),
    "fishers_exact": TestInfo("fishers_exact", "Fisher's exact test", "categorical", None, min_groups=2),
    "logrank": TestInfo("logrank", "Log-rank test", "survival", None, min_groups=2),
    "cox_ph": TestInfo("cox_ph", "Cox proportional-hazards (HR)", "survival", None, min_groups=2),
    "pearson": TestInfo("pearson", "Pearson correlation", "correlation", True),
    "spearman": TestInfo("spearman", "Spearman correlation", "correlation", False),
    "linear_regression": TestInfo("linear_regression", "Linear regression", "regression", True),
}


# Plot type constants (import lazily to avoid a hard dependency cycle).
def _n_levels(df: Optional[pd.DataFrame], col: Optional[str]) -> int:
    if df is None or not col or col not in df.columns:
        return 0
    return int(df[col].dropna().nunique())


def recommend_tests(plot_type: str, mapping: Dict[str, Any], *,
                    df: Optional[pd.DataFrame] = None,
                    stats_mapping: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return advisory test suggestions for a plot type + mapping.

    Output: ``{"suggested": [test_id, ...], "primary": test_id or None,
    "notes": [str, ...]}``. Uses the number of group levels when a DataFrame is
    provided to prefer two-group vs multi-group tests.
    """
    sm = stats_mapping or {}
    group_col = sm.get("group_column") or mapping.get("x") or mapping.get("group")
    subgroup = sm.get("subgroup_column") or mapping.get("group")
    has_subject = bool(sm.get("subject_column"))
    n_groups = _n_levels(df, group_col)
    suggested: List[str] = []
    notes: List[str] = []

    box_bar = {"barplot_with_error_bar", "boxplot_or_violin_with_points",
               "grouped_barplot_with_error_bar"}

    if plot_type in box_bar:
        two_factor = bool(subgroup and subgroup != group_col and plot_type == "grouped_barplot_with_error_bar")
        if two_factor:
            suggested += ["two_way_anova", "welch_t", "mann_whitney"]
            notes.append("Two grouping variables detected: two-way ANOVA, or pairwise tests "
                         "within each x category.")
        if n_groups == 2 or n_groups == 0:
            suggested += ["welch_t", "students_t", "mann_whitney"]
            if has_subject:
                suggested += ["paired_t", "wilcoxon"]
                notes.append("A subject/pair ID is set: paired t-test or Wilcoxon are available.")
        if n_groups >= 3:
            suggested += ["one_way_anova", "kruskal_wallis"]
            notes.append("Three or more groups: one-way ANOVA or Kruskal-Wallis, optionally "
                         "with post-hoc pairwise tests and correction.")
    elif plot_type == "scatterplot_with_regression":
        suggested += ["pearson", "spearman", "linear_regression"]
        notes.append("Correlation/regression statistics; per-group if a color/group column is set.")
    elif plot_type == "kaplan_meier_survival_curve":
        suggested += ["logrank", "cox_ph"]
        notes.append("Log-rank compares survival across groups; Cox reports hazard ratios "
                     "(proportional-hazards assumption is not auto-checked).")
    elif plot_type in ("stacked_bar_composition", "oncoprint_mutation_heatmap"):
        suggested += ["chi_square", "fishers_exact"]
        notes.append("Categorical association: chi-square for larger tables, Fisher's exact "
                     "for 2x2 or small expected counts.")
    elif plot_type == "volcano_plot":
        notes.append("Volcano p-values are supplied in the input; the app does not recompute "
                     "differential statistics. Only threshold annotation is applied.")
    elif plot_type == "lollipop_mutation_plot":
        notes.append("Lollipop plots are descriptive; categorical tests need a phenotype/condition "
                     "table and are not run automatically.")
    else:
        notes.append("No automatic statistical test is offered for this plot type.")

    # De-duplicate preserving order.
    seen = set()
    ordered = [t for t in suggested if not (t in seen or seen.add(t))]
    return {"suggested": ordered, "primary": ordered[0] if ordered else None, "notes": notes}
