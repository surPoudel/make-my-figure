"""Transform-aware and guidance recommendations.

Two extra families beyond the direct (map-existing-columns) recommendations:

* **transform** — plots reachable by reshaping the data (wide→long for ridge/box,
  a correlation matrix for a heatmap, category counts for a bar). Each carries a
  ``transform`` spec; the app applies it (saving the reshaped CSV) before plotting.
* **guidance** — informational only: plots that need columns the table doesn't
  have yet (e.g. volcano/MA need precomputed fold-change + p-value/FDR). Make My
  Figure never computes those; it tells the user what analysis to run.
"""

from __future__ import annotations

from typing import List

import pandas as pd

from make_my_figure_core.plots.registry import available_plot_types, make_spec
from make_my_figure_core.recommendations.recommendation_models import (
    DataProfile,
    Recommendation,
)


def _base_name(table_name: str) -> str:
    return table_name.rsplit(".", 1)[0] if "." in table_name else table_name


def _draft(plot_type: str, table_name: str, mapping: dict) -> dict:
    spec = make_spec(plot_type, table_name, "publication")
    spec["mapping"] = mapping
    return spec


def recommend_transforms(profile: DataProfile, schema: str, df: pd.DataFrame,
                         table_name: str = "data") -> List[Recommendation]:
    """Recommendations that first reshape the data, then plot (one-click)."""
    recs: List[Recommendation] = []
    numerics = list(profile.numeric_columns)
    base = _base_name(table_name)
    matrix_samples = list(profile.matrix_sample_columns or [])

    # A) wide numeric block -> melt to long -> ridge / box across columns.
    melt_cols = matrix_samples if (profile.is_matrix and len(matrix_samples) >= 3) else numerics
    if len(melt_cols) >= 3:
        out = f"{base}__long.csv"
        tf = {"name": "wide_to_long", "params": {"value_cols": melt_cols},
              "result_columns": ["column", "value"], "output_filename": out}
        recs.append(Recommendation(
            id="tf_ridge_columns", plot_type="ridge_or_density_plot",
            display_name="Ridge of per-column distributions (reshape → long)",
            confidence=0.5, kind="transform", transform=tf,
            why="Reshape the wide numeric columns to long form and compare each column's "
                "distribution as a ridge/density plot.",
            warnings=[f"Reshapes the data (wide → long) and saves {out}."],
            plot_spec_draft=_draft("ridge_or_density_plot", out,
                                   {"x": "value", "group": "column", "overlap": 0.6})))
        recs.append(Recommendation(
            id="tf_box_columns", plot_type="boxplot_or_violin_with_points",
            display_name="Box/violin of per-column distributions (reshape → long)",
            confidence=0.48, kind="transform", transform=tf,
            why="Reshape wide → long and compare each column's distribution with box/violin.",
            warnings=[f"Reshapes the data (wide → long) and saves {out}."],
            plot_spec_draft=_draft("boxplot_or_violin_with_points", out,
                                   {"x": "column", "y": "value"})))

    # B) >=3 numeric columns -> correlation matrix -> clustered heatmap.
    if len(numerics) >= 3:
        cols = matrix_samples if (profile.is_matrix and len(matrix_samples) >= 3) else numerics
        out = f"{base}__corr.csv"
        tf = {"name": "correlation_matrix", "params": {"columns": cols},
              "result_columns": ["feature", *cols], "output_filename": out}
        recs.append(Recommendation(
            id="tf_corr_heatmap", plot_type="heatmap_clustered_matrix",
            display_name="Correlation heatmap (compute correlation matrix)",
            confidence=0.55, kind="transform", transform=tf,
            why="Compute the pairwise correlation of the numeric columns and show a clustered "
                "heatmap — reveals which columns/samples move together.",
            warnings=[f"Computes a correlation matrix and saves {out}."],
            plot_spec_draft=_draft("heatmap_clustered_matrix", out,
                                   {"row_id": "feature", "scale": "none",
                                    "color_scale": "diverging"})))

    # C) a categorical column -> frequency (value_counts) bar.
    cats = [c for c in profile.categorical_columns if c not in profile.id_columns]
    cat = profile.role_column("group") or (cats[0] if cats else None)
    if cat:
        out = f"{base}__counts.csv"
        tf = {"name": "value_counts", "params": {"column": cat, "category_name": cat},
              "result_columns": [cat, "count"], "output_filename": out}
        recs.append(Recommendation(
            id="tf_count_bar", plot_type="barplot_with_error_bar",
            display_name=f"Frequency bar of '{cat}' (count categories)",
            confidence=0.45, kind="transform", transform=tf,
            why=f"Count how many rows fall in each '{cat}' category and show a frequency bar.",
            warnings=[f"Aggregates counts per category and saves {out}."],
            plot_spec_draft=_draft("barplot_with_error_bar", out, {"x": cat, "y": "count"})))

    return [r for r in recs if r.plot_type in available_plot_types()]


def recommend_guidance(profile: DataProfile, schema: str,
                       df: pd.DataFrame) -> List[Recommendation]:
    """Informational recommendations for plots needing not-yet-available columns."""
    recs: List[Recommendation] = []
    if schema in ("numeric_matrix", "expression_like_matrix") or profile.is_matrix:
        instr = (
            "Volcano and MA plots need a PRECOMPUTED differential results table: one row per "
            "feature with a log2 fold-change column and a p-value/FDR column. Make My Figure "
            "does not compute differential expression or fabricate statistics. To get there: "
            "define your groups, run a differential/statistical analysis (in your analysis tool "
            "of choice) to produce per-feature log2FC + p-value/FDR (and an average-abundance / "
            "baseMean column for MA), then load that results table here — it will be recommended "
            "as a volcano (and MA).")
        if "volcano_plot" in available_plot_types():
            recs.append(Recommendation(
                id="guide_volcano", plot_type="volcano_plot",
                display_name="Volcano plot — needs a differential results table",
                confidence=0.4, kind="guidance", plot_spec_draft=None, instructions=instr,
                why="This is a matrix of measurements, not a differential results table; a "
                    "volcano needs per-feature fold-change + p-value/FDR.",
                warnings=["Define groups and run stats to get logFC + p/FDR first."]))
        if "ma_plot" in available_plot_types():
            recs.append(Recommendation(
                id="guide_ma", plot_type="ma_plot",
                display_name="MA plot — needs a differential results table",
                confidence=0.38, kind="guidance", plot_spec_draft=None, instructions=instr,
                why="An MA plot needs per-feature average abundance + log fold-change from a "
                    "differential analysis.",
                warnings=["Define groups and run stats to get logFC + mean abundance first."]))
    return recs
