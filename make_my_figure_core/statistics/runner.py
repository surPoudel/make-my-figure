"""High-level statistics orchestration used by both apps.

:func:`run_statistics` takes a DataFrame, a StatsSpec dict, and (optionally) the
plot type + plot mapping, resolves which comparisons to run, dispatches to the
test modules, applies multiple-testing correction across the family, and returns
a :class:`StatsReport` with per-comparison method sentences and an overall
methods paragraph.

The contract: nothing is fabricated. If a design is invalid the runner records a
warning (or raises :class:`StatsError` for a hard configuration error) rather
than emitting a questionable p-value.
"""

from __future__ import annotations

import itertools
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from make_my_figure_core.statistics import anova, categorical, nonparametric, pairwise, survival
from make_my_figure_core.statistics import method_reporting as report
from make_my_figure_core.statistics import validators as val
from make_my_figure_core.statistics._versions import software_versions
from make_my_figure_core.statistics.models import StatResult, StatsError, StatsReport
from make_my_figure_core.statistics.multiple_testing import apply_correction, canonical_method
from make_my_figure_core.statistics.test_registry import TESTS, recommend_tests

TWO_GROUP = {"students_t", "welch_t", "mann_whitney", "paired_t", "wilcoxon"}
PARAMETRIC_PAIR = {"students_t", "welch_t", "paired_t"}


# --- column resolution ------------------------------------------------------

def resolve_columns(plot_type: Optional[str], mapping: Dict[str, Any],
                    spec: Dict[str, Any]) -> Dict[str, Any]:
    """Merge explicit StatsSpec columns with sensible plot-mapping defaults."""
    mapping = mapping or {}
    out = {
        "value_column": spec.get("value_column") or mapping.get("y"),
        "group_column": spec.get("group_column") or mapping.get("x") or mapping.get("group"),
        "subgroup_column": spec.get("subgroup_column"),
        "subject_column": spec.get("subject_column") or spec.get("paired_id_column"),
        "time_column": spec.get("time_column") or mapping.get("time"),
        "event_column": spec.get("event_column") or mapping.get("event"),
        "x_column": spec.get("x_column") or mapping.get("x"),
        "y_column": spec.get("y_column") or mapping.get("y"),
        "row_column": spec.get("row_column"),
        "col_column": spec.get("col_column"),
    }
    if plot_type == "grouped_barplot_with_error_bar":
        out["group_column"] = spec.get("group_column") or mapping.get("x")
        out["subgroup_column"] = spec.get("subgroup_column") or mapping.get("group")
    if plot_type == "kaplan_meier_survival_curve":
        out["group_column"] = spec.get("group_column") or mapping.get("group")
    if plot_type == "scatterplot_with_regression":
        out["subgroup_column"] = spec.get("subgroup_column") or mapping.get("color")
    if plot_type in ("stacked_bar_composition", "oncoprint_mutation_heatmap"):
        out["row_column"] = spec.get("row_column") or mapping.get("x") or mapping.get("sample")
        out["col_column"] = spec.get("col_column") or mapping.get("stack") or mapping.get("row")
    return out


def _levels(df: pd.DataFrame, col: str) -> List[Any]:
    return val.group_levels(df, col)


def _pairs(levels: List[Any], mode: str, reference: Any,
           selected: Optional[List[List[Any]]]) -> List[Tuple[Any, Any]]:
    if mode == "vs_control" and reference is not None:
        return [(reference, lv) for lv in levels if lv != reference]
    if mode == "selected_pairs" and selected:
        out = []
        lvset = set(levels)
        for pair in selected:
            if len(pair) == 2 and pair[0] in lvset and pair[1] in lvset:
                out.append((pair[0], pair[1]))
        return out
    return list(itertools.combinations(levels, 2))


# --- pairwise dispatch ------------------------------------------------------

def _run_two_group(test_id: str, df: pd.DataFrame, value_col: str, group_col: str,
                   ga: Any, gb: Any, subject_col: Optional[str], alternative: str,
                   alpha: float) -> StatResult:
    ctx = TESTS[test_id].label
    info = TESTS[test_id]
    if info.requires_pairing:
        if not subject_col:
            raise StatsError(f"{ctx} requires a subject/pair ID column.")
        a, b, ids = val.paired_arrays(df, value_col, group_col, ga, gb, subject_col, context=ctx)
        if test_id == "paired_t":
            return pairwise.paired_t(a, b, value_col=value_col, group_col=group_col,
                                     group_a=ga, group_b=gb, id_col=subject_col,
                                     alternative=alternative, alpha=alpha)
        return pairwise.wilcoxon_signed_rank(a, b, value_col=value_col, group_col=group_col,
                                             group_a=ga, group_b=gb, id_col=subject_col,
                                             alternative=alternative, alpha=alpha)
    a, b = val.two_group_arrays(df, value_col, group_col, ga, gb, context=ctx)
    if test_id == "students_t":
        return pairwise.students_t(a, b, value_col=value_col, group_col=group_col,
                                   group_a=ga, group_b=gb, alternative=alternative, alpha=alpha)
    if test_id == "welch_t":
        return pairwise.welch_t(a, b, value_col=value_col, group_col=group_col,
                                group_a=ga, group_b=gb, alternative=alternative, alpha=alpha)
    return pairwise.mann_whitney(a, b, value_col=value_col, group_col=group_col,
                                 group_a=ga, group_b=gb, alternative=alternative, alpha=alpha)


# --- main entry -------------------------------------------------------------

def run_statistics(df: pd.DataFrame, stats_spec: Dict[str, Any], *,
                   plot_type: Optional[str] = None,
                   mapping: Optional[Dict[str, Any]] = None) -> StatsReport:
    """Run the configured statistics and return a :class:`StatsReport`."""
    stats_spec = dict(stats_spec or {})
    if not stats_spec.get("enabled", False):
        return StatsReport(config=stats_spec, software_versions=software_versions())

    mapping = mapping or {}
    cols = resolve_columns(plot_type, mapping, stats_spec)
    alpha = float(stats_spec.get("alpha", 0.05))
    alternative = stats_spec.get("alternative", "two-sided")
    correction = canonical_method(stats_spec.get("correction", "benjamini_hochberg"))
    mode = stats_spec.get("comparison_mode", "auto")
    reference = stats_spec.get("reference_group")
    selected = stats_spec.get("selected_pairs")
    test = stats_spec.get("test", "auto")
    posthoc = bool(stats_spec.get("posthoc", False))

    results: List[StatResult] = []
    warnings: List[str] = []

    if test == "auto":
        rec = recommend_tests(plot_type or "", mapping, df=df, stats_mapping=stats_spec)
        test = rec.get("primary")
        if test is None:
            return StatsReport(config=stats_spec, warnings=["No applicable test for this plot type."],
                               software_versions=software_versions())

    try:
        results = _dispatch(test, df, cols, plot_type, mode, reference, selected,
                            alternative, alpha, posthoc, stats_spec)
    except StatsError as exc:
        warnings.extend(exc.messages)

    # Family-wide correction across pairwise/posthoc p-values only (omnibus F/H
    # tests are single tests and are not folded into the pairwise family).
    corr_family = [r for r in results if r.comparison_type in ("two_group",)]
    if corr_family:
        apply_correction(corr_family, method=correction, alpha=alpha)
    for r in results:
        if r.comparison_type not in ("two_group",):
            r.alpha = alpha
            r.correction_method = "none"
            r.reject_null = bool(r.p_value is not None and r.p_value == r.p_value and r.p_value < alpha)

    for r in results:
        r.plot_type = plot_type
        r.method_sentence = report.method_sentence(r)
        warnings.extend([w for w in r.warnings if w not in warnings])

    used_correction = correction if corr_family else "none"
    rep = StatsReport(
        results=results, correction_method=used_correction,
        method_paragraph=report.methods_paragraph(results, used_correction),
        legend_sentence=report.legend_sentence(results, used_correction),
        warnings=warnings, config=stats_spec, software_versions=software_versions(),
    )
    return rep


def _dispatch(test: str, df: pd.DataFrame, cols: Dict[str, Any], plot_type: Optional[str],
              mode: str, reference: Any, selected, alternative: str, alpha: float,
              posthoc: bool, stats_spec: Dict[str, Any]) -> List[StatResult]:
    value_col = cols["value_column"]
    group_col = cols["group_column"]
    subgroup_col = cols["subgroup_column"]
    subject_col = cols["subject_column"]

    info = TESTS.get(test)
    if info is None:
        raise StatsError(f"Unknown test '{test}'.")

    # --- correlation / regression (scatter) --------------------------------
    if info.family in ("correlation", "regression"):
        return _run_correlation(test, df, cols, alternative, alpha)

    # --- survival ----------------------------------------------------------
    if info.family == "survival":
        if not (cols["time_column"] and cols["event_column"] and group_col):
            raise StatsError("Survival statistics need time, event, and group columns.")
        if test == "logrank":
            return [survival.logrank_test(df, cols["time_column"], cols["event_column"],
                                          group_col, alpha=alpha)]
        return survival.cox_hazard_ratio(df, cols["time_column"], cols["event_column"],
                                         group_col, reference=reference, alpha=alpha)

    # --- categorical -------------------------------------------------------
    if info.family == "categorical":
        row_c = cols["row_column"] or group_col
        col_c = cols["col_column"] or subgroup_col
        if not (row_c and col_c):
            raise StatsError("Categorical tests need two categorical columns (row and column).")
        table = categorical.contingency_from_columns(df, row_c, col_c)
        if test == "chi_square":
            return [categorical.chi_square(table, row_col=row_c, col_col=col_c, alpha=alpha)]
        return [categorical.fishers_exact(table, row_col=row_c, col_col=col_c,
                                          alternative=alternative, alpha=alpha)]

    # --- two-way ANOVA -----------------------------------------------------
    if test == "two_way_anova":
        if not (value_col and group_col and subgroup_col):
            raise StatsError("Two-way ANOVA needs a value column and two factors.")
        return anova.two_way_anova(df, value_col, group_col, subgroup_col, alpha=alpha)

    # --- repeated-measures ANOVA ------------------------------------------
    if test == "rm_anova":
        if not (value_col and group_col and subject_col):
            raise StatsError("Repeated-measures ANOVA needs value, within-factor, and subject columns.")
        return [anova.repeated_measures_anova(df, value_col, subject_col, group_col, alpha=alpha)]

    # --- one-way omnibus (+ optional post-hoc) ----------------------------
    if test in ("one_way_anova", "kruskal_wallis"):
        if not (value_col and group_col):
            raise StatsError(f"{info.label} needs a value column and a grouping column.")
        levels, arrays = val.multi_group_arrays(df, value_col, group_col, context=info.label)
        if test == "one_way_anova":
            omni = anova.one_way_anova(levels, arrays, value_col=value_col, group_col=group_col, alpha=alpha)
            out = [omni]
            if posthoc:
                pair_test = stats_spec.get("posthoc_test", "welch_t")
                out += _run_pairwise_family(pair_test, df, value_col, group_col, levels,
                                            subject_col, mode, reference, selected, alternative, alpha)
            return out
        omni = nonparametric.kruskal_wallis(levels, arrays, value_col=value_col, group_col=group_col, alpha=alpha)
        out = [omni]
        if posthoc:
            out += nonparametric.dunn_posthoc(levels, arrays, value_col=value_col, group_col=group_col)
        return out

    # --- two-group tests (single pair, all pairs, within-x, vs control) ----
    if info.family == "two_group":
        if not (value_col and group_col):
            raise StatsError(f"{info.label} needs a value column and a grouping column.")
        # Grouped plot: compare subgroups within each x category.
        if mode == "within_x" and subgroup_col:
            return _run_within_x(test, df, value_col, group_col, subgroup_col,
                                 subject_col, reference, selected, alternative, alpha)
        levels = _levels(df, group_col)
        return _run_pairwise_family(test, df, value_col, group_col, levels, subject_col,
                                    mode, reference, selected, alternative, alpha)

    raise StatsError(f"Test '{test}' is not supported in this context.")


def _run_pairwise_family(test: str, df, value_col, group_col, levels, subject_col,
                         mode, reference, selected, alternative, alpha) -> List[StatResult]:
    if len(levels) < 2:
        raise StatsError(f"'{group_col}' needs >= 2 groups (found {len(levels)}).")
    effective_mode = mode
    if mode in ("auto", "omnibus"):
        effective_mode = "vs_control" if reference is not None else "all_pairs"
    pairs = _pairs(levels, effective_mode, reference, selected)
    if not pairs:
        pairs = list(itertools.combinations(levels, 2))
    out: List[StatResult] = []
    for ga, gb in pairs:
        try:
            out.append(_run_two_group(test, df, value_col, group_col, ga, gb,
                                      subject_col, alternative, alpha))
        except StatsError as exc:
            # Skip an invalid single pair but keep the rest; record the reason.
            r = StatResult(test_id=test, test_name=TESTS[test].label,
                           comparison_type="two_group", value_column=value_col,
                           grouping_columns=[group_col], group_a=str(ga), group_b=str(gb),
                           software_versions=software_versions())
            r.warnings.append(exc.messages[0])
            out.append(r)
    return out


def _run_within_x(test, df, value_col, x_col, subgroup_col, subject_col,
                  reference, selected, alternative, alpha) -> List[StatResult]:
    out: List[StatResult] = []
    for xl in _levels(df, x_col):
        sub = df[df[x_col] == xl]
        sub_levels = _levels(sub, subgroup_col)
        if len(sub_levels) < 2:
            continue
        pairs = _pairs(sub_levels, "vs_control" if reference is not None else "all_pairs",
                       reference, selected)
        for ga, gb in pairs:
            try:
                r = _run_two_group(test, sub, value_col, subgroup_col, ga, gb,
                                   subject_col, alternative, alpha)
            except StatsError as exc:
                r = StatResult(test_id=test, test_name=TESTS[test].label,
                               comparison_type="two_group", value_column=value_col,
                               grouping_columns=[x_col, subgroup_col], group_a=str(ga),
                               group_b=str(gb), software_versions=software_versions())
                r.warnings.append(exc.messages[0])
            r.block_column = x_col
            r.extra = dict(r.extra or {})
            r.extra.update({"x_level": str(xl), "within_x": True})
            out.append(r)
    return out


def _run_correlation(test, df, cols, alternative, alpha) -> List[StatResult]:
    x_col, y_col = cols["x_column"], cols["y_column"]
    subgroup = cols["subgroup_column"]
    if not (x_col and y_col):
        raise StatsError("Correlation/regression needs x and y columns.")
    val.require_columns(df, [x_col, y_col], context=TESTS[test].label)
    fn = {"pearson": pairwise.pearson, "spearman": pairwise.spearman,
          "linear_regression": pairwise.linear_regression}[test]

    def _call(sub, label):
        x = pd.to_numeric(sub[x_col], errors="coerce").to_numpy(float)
        y = pd.to_numeric(sub[y_col], errors="coerce").to_numpy(float)
        mask = np.isfinite(x) & np.isfinite(y)
        if mask.sum() < 3:
            raise StatsError(f"{TESTS[test].label}: need >= 3 finite (x, y) pairs.")
        if test == "linear_regression":
            return fn(x[mask], y[mask], x_col=x_col, y_col=y_col, group_label=label, alpha=alpha)
        return fn(x[mask], y[mask], x_col=x_col, y_col=y_col, group_label=label,
                  alternative=alternative, alpha=alpha)

    out: List[StatResult] = []
    if subgroup and subgroup in df.columns:
        for g in _levels(df, subgroup):
            try:
                out.append(_call(df[df[subgroup] == g], str(g)))
            except StatsError as exc:
                r = StatResult(test_id=test, test_name=TESTS[test].label,
                               comparison_type=TESTS[test].family, value_column=y_col,
                               grouping_columns=[x_col], group_a=str(g),
                               software_versions=software_versions())
                r.warnings.append(exc.messages[0])
                out.append(r)
    else:
        out.append(_call(df, None))
    return out
