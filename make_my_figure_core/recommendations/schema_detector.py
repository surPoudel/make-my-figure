"""Classify a profiled table into a coarse *schema* used to pick figures.

``detect_schema(profile, df)`` returns one of a fixed vocabulary of schema
strings. Detection is priority-ordered (most specific first) and relies only on
the roles/flags already found by :func:`data_profiler.profile_table`.
"""

from __future__ import annotations

import pandas as pd

from make_my_figure_core.recommendations.recommendation_models import DataProfile

SCHEMAS = (
    # spatial (v2) - listed first because they are the most specific: they all
    # require corroborated tissue coordinates, which no other schema uses.
    "spatial_roi_polygons",
    "spatial_transcripts",
    "spatial_composition",
    "spatial_long_expression",
    "spatial_cells",
    "neighborhood_enrichment",
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

    # --- spatial (v2) --------------------------------------------------------
    # Checked first: every one of these needs corroborated tissue coordinates
    # (see data_profiler._spatial_coordinate_columns), so an ordinary x/y
    # scatter table never reaches them.
    if r("spatial_x") and r("spatial_y"):
        # ROI geometry: many rows per region, ordered vertices.
        if r("roi_id") and r("vertex_order"):
            return "spatial_roi_polygons"
        # Transcript detections: one row per molecule, not per cell.
        if r("transcript_gene") and (r("transcript_id") or r("quality_score")):
            return "spatial_transcripts"
        # Composition: one row per (spot, category) with a count or fraction.
        if (r("spot_id") or r("roi_id")) and r("cell_type") and \
                (r("fraction") or profile.numeric_columns):
            if _looks_like_composition(profile, df):
                return "spatial_composition"
        # Long expression: id + coordinates + feature + value.
        if r("transcript_gene") and _has_value_column(profile):
            return "spatial_long_expression"
        # Otherwise a cell/spot table.
        return "spatial_cells"

    # Enrichment matrix produced by the spatial workflow (no coordinates).
    if r("neighborhood") and r("cell_type"):
        lowered = {str(c).lower() for c in (df.columns if df is not None else [])}
        if any("enrich" in c for c in lowered):
            return "neighborhood_enrichment"

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

def _has_value_column(profile: DataProfile) -> bool:
    """A numeric column that is not one of the coordinates."""
    coords = {profile.role_column("spatial_x"), profile.role_column("spatial_y")}
    return any(c not in coords for c in profile.numeric_columns)


def _looks_like_composition(profile: DataProfile, df) -> bool:
    """Long composition: the same spot repeated once per category.

    Checked on the data rather than the header, because "spot_id + cell_type"
    also describes a per-cell table where each row is one cell.
    """
    if df is None:
        return False
    spot = profile.role_column("spot_id") or profile.role_column("roi_id")
    ct = profile.role_column("cell_type")
    if not spot or not ct or spot not in df.columns or ct not in df.columns:
        return False
    try:
        per_spot = df.groupby(spot)[ct].nunique()
        # several distinct categories per spot, and no category repeated within one
        return bool(per_spot.median() > 1 and not df.duplicated([spot, ct]).any())
    except Exception:  # noqa: BLE001 - detection must never raise
        return False
