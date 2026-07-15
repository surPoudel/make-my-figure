"""Classify a profiled table into a coarse *schema* used to pick figures.

``detect_schema(profile, df)`` returns one of a fixed vocabulary of schema
strings. Detection is priority-ordered (most specific first) and relies only on
the roles/flags already found by :func:`data_profiler.profile_table`.
"""

from __future__ import annotations

import pandas as pd

from make_my_figure_core.recommendations.recommendation_models import DataProfile

SCHEMAS = (
    "precomputed_differential",
    "survival",
    "gwas",
    "classification",
    "dose_response",
    "network_edge_list",
    "mutation_matrix",
    "enrichment",
    "correlation_matrix",
    "expression_like_matrix",
    "numeric_matrix",
    "matrix_plus_metadata",
    "paired",
    "generic_long",
    "unknown",
)


def detect_schema(profile: DataProfile, df: pd.DataFrame | None = None) -> str:
    r = profile.has_role

    # Precomputed differential/feature-level results: fold-change + a p or FDR.
    if r("logFC") and (r("p_value") or r("adj_p")):
        # An enrichment table also has p-values but is caught below by term+count.
        if not (r("enrichment_term") and (r("enrichment_count") or r("enrichment_ratio"))):
            return "precomputed_differential"

    if r("survival_time") and r("survival_event"):
        return "survival"

    if r("chromosome") and r("position") and (r("p_value") or r("adj_p")):
        return "gwas"

    if r("class_label") and r("class_score"):
        return "classification"

    if r("dose") and r("response"):
        return "dose_response"

    if r("source") and r("target"):
        return "network_edge_list"

    if r("enrichment_term") and (r("enrichment_count") or r("enrichment_ratio")) \
            and (r("p_value") or r("adj_p")):
        return "enrichment"

    if r("mutation_gene") and r("mutation_type"):
        return "mutation_matrix"

    if profile.is_correlation_matrix:
        return "correlation_matrix"

    if profile.is_matrix:
        return "expression_like_matrix" if profile.matrix_kind == "expression_like" \
            else "numeric_matrix"

    # Paired: a subject id + a 2-level condition + a numeric value (long form).
    if r("subject") and r("group") and profile.numeric_columns and df is not None:
        grp = profile.role_column("group")
        subj = profile.role_column("subject")
        if grp in df.columns and subj in df.columns:
            n_levels = df[grp].dropna().nunique()
            reps_per_subject = df.groupby(subj)[grp].nunique()
            if n_levels == 2 and (reps_per_subject >= 2).mean() > 0.5:
                return "paired"

    # Generic long: a group/category column + at least one numeric value column.
    if r("group") and profile.numeric_columns:
        return "generic_long"

    return "unknown"
