"""Map a profiled table + schema to recommended figures (existing renderers only).

Every recommendation carries a one-click ``plot_spec_draft`` built from
``registry.make_spec`` with the detected column mapping, plus a confidence,
rationale, suggested statistics, thresholds and cost estimate. Recommendations
are sorted most-confident first.

Scope: no RNA-seq differential-expression analysis is ever recommended. For a
count-like / numeric / expression-like matrix we recommend exploratory plots
(heatmap, PCA, clustering-style heatmap); for a **precomputed** differential
results table we recommend volcano and related summaries. Plot types that are
not implemented in this version (MA, Manhattan/Q-Q, network graph, dose-response
curve fitting) are either omitted or substituted with the closest existing type
plus an explicit warning — never fabricated.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from make_my_figure_core.de_detect import detect_de_columns
from make_my_figure_core.plots.registry import (
    default_mapping,
    display_name,
    make_spec,
)
from make_my_figure_core.recommendations.recommendation_models import (
    DataProfile,
    Recommendation,
)
from make_my_figure_core.recommendations.stat_recommender import suggest_stats
from make_my_figure_core.ui_hints import COLUMN_FIELDS

_LARGE_CELLS = 40_000     # matrix cell count above which clustering/PCA is "expensive"


def _mapping(plot_type: str, col_overrides: Dict[str, Optional[str]]) -> Dict[str, Any]:
    """Start from the default mapping (keeps option keys) and set column keys."""
    m = dict(default_mapping(plot_type))
    for key in COLUMN_FIELDS.get(plot_type, []):
        val = col_overrides.get(key)
        if val:
            m[key] = val
        else:
            m.pop(key, None)
    return m


def _draft(plot_type: str, table_name: str, mapping: Dict[str, Any],
           statistics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return make_spec(plot_type, table_name, "publication", mapping=mapping,
                     statistics=statistics)


def _numeric_values(profile: DataProfile) -> List[str]:
    """Numeric columns that are plain measurements (not detected special roles)."""
    special = {profile.role_column(r) for r in
               ("p_value", "adj_p", "logFC", "position", "ave_expr",
                "survival_time", "class_score", "estimate_lower", "estimate_upper")}
    return [c for c in profile.numeric_columns if c not in special]


def _measurement_columns(profile, df, exclude) -> List[str]:
    """Numeric columns that plausibly carry a measurement, not an identifier.

    A patient number and a cell index are numeric, but colouring tissue by
    "patient" is meaningless. Identifier-like columns are dropped, and so are
    near-constant ones, so the suggestion lands on something worth mapping.
    """
    skip = set(exclude) | set(profile.id_columns)
    for role in ("subject", "image_id", "spot_id", "transcript_id", "roi_id",
                 "vertex_order", "neighborhood", "cell_type"):
        col = profile.role_column(role)
        if col:
            skip.add(col)
    out = []
    for c in profile.numeric_columns:
        if c in skip or _looks_like_identifier(c):
            continue
        if df is not None and c in df.columns:
            try:
                if df[c].nunique(dropna=True) < 5:      # near-constant or a coded label
                    continue
            except Exception:  # noqa: BLE001
                pass
        out.append(c)
    return out


def _looks_like_identifier(name: str) -> bool:
    n = str(name).strip().lower().replace(" ", "_")
    return (n.endswith(("_id", "_idx", "_index", "_no", "_number"))
            or n in {"id", "index", "patient", "donor", "subject", "sample",
                     "replicate", "batch", "slide", "well", "tile", "fov"})


def recommend_plots(profile: DataProfile, schema: str, df: pd.DataFrame,
                    table_name: str = "data") -> List[Recommendation]:
    recs: List[Recommendation] = []

    def add(plot_type, conf, why, col_map=None, *, stats=None, thresholds=None,
            missing=None, warnings=None, cost="low", confirm=False, renderable=True):
        mapping = _mapping(plot_type, col_map or {}) if renderable else {}
        draft = _draft(plot_type, table_name, mapping, statistics=stats) if renderable else None
        recs.append(Recommendation(
            id=f"{plot_type}_{len(recs)}",
            plot_type=plot_type,
            display_name=display_name(plot_type) if renderable else plot_type.replace("_", " "),
            confidence=conf, why=why,
            required_mappings=mapping if renderable else (col_map or {}),
            missing_mappings=missing or [],
            suggested_statistics=stats, suggested_thresholds=thresholds or {},
            estimated_cost=cost, requires_confirmation=confirm,
            warnings=warnings or [], plot_spec_draft=draft))

    # ---- spatial (v2) -------------------------------------------------------
    # Advisory only, and deliberately shallow. A recommendation may suggest which
    # column looks like a coordinate or a label; it never proposes k, a radius, a
    # number of neighbourhoods, a transform or a normalisation, because those are
    # scientific choices the data cannot make on the user's behalf.
    if schema.startswith("spatial") or schema == "neighborhood_enrichment":
        sx = profile.role_column("spatial_x")
        sy = profile.role_column("spatial_y")
        cell_type = profile.role_column("cell_type")
        neighborhood = profile.role_column("neighborhood")
        image = profile.role_column("image_id")
        gene = profile.role_column("transcript_gene")
        roi = profile.role_column("roi_id")
        spot = profile.role_column("spot_id")
        units_note = ("Declare the coordinate units before export: units are never inferred, "
                      "and a scale bar is only drawn when they are physical.")

    if schema == "spatial_cells":
        if cell_type:
            add("spatial_categorical_map", 0.88,
                f"Tissue coordinates plus a {cell_type!r} label — a spatial map shows where "
                "each population sits in the section.",
                {"x": sx, "y": sy, "category": cell_type, "facet": image},
                warnings=[units_note])
        if neighborhood:
            add("spatial_categorical_map", 0.72,
                f"A {neighborhood!r} column is present — the same map colours cells by "
                "neighbourhood instead of by type.",
                {"x": sx, "y": sy, "category": neighborhood, "facet": image})
        values = _measurement_columns(profile, df, {sx, sy})
        if values:
            add("spatial_feature_map", 0.80,
                f"Numeric column(s) such as {values[0]!r} can be drawn as a continuous "
                "spatial map. No transform is applied unless you ask for one.",
                {"x": sx, "y": sy, "value": values[0], "facet": image},
                warnings=[units_note,
                          "Choose the transform yourself; the colourbar label follows it."])
        if cell_type:
            add("cellular_neighborhood_analysis", 0.55,
                f"With coordinates and {cell_type!r}, cellular-neighbourhood analysis is "
                "available. You choose the graph (k or radius) and the number of "
                "neighbourhoods — these are scientific decisions and are not suggested here."
                + ("" if image else " No image/sample column was found: set one, or every "
                   "cell in the table is treated as a single tissue."),
                {"x": sx, "y": sy, "cell_type": cell_type, "sample": image},
                cost="medium", confirm=True, renderable=False)

    elif schema == "spatial_transcripts":
        add("spatial_transcript_map", 0.9,
            f"One row per detection with a {gene!r} column — a transcript map shows where "
            "each gene was detected. Nothing is subsampled unless you ask.",
            {"x": sx, "y": sy, "gene": gene,
             "quality": profile.role_column("quality_score")},
            warnings=[units_note])

    elif schema == "spatial_roi_polygons":
        add("spatial_roi_map", 0.9,
            f"Ordered vertices grouped by {roi!r} — these are region outlines.",
            {"roi": roi, "x": sx, "y": sy,
             "vertex_order": profile.role_column("vertex_order")},
            warnings=[units_note])

    elif schema == "spatial_composition":
        add("spatial_composition_map", 0.85,
            f"One row per ({spot or roi!r}, {cell_type!r}) with a value — composition "
            "glyphs show the mixture at each position.",
            {"spot": spot or roi, "x": sx, "y": sy, "category": cell_type,
             "value": profile.role_column("fraction")
                      or next(iter(_measurement_columns(profile, df, {sx, sy})), None)},
            warnings=[units_note,
                      "Set normalize explicitly: counts and fractions are not guessed apart."])

    elif schema == "spatial_long_expression":
        add("spatial_feature_map", 0.85,
            f"Long form with a {gene!r} column — one panel per feature, on shared coordinates.",
            {"x": sx, "y": sy,
             "value": next(iter(_measurement_columns(profile, df, {sx, sy})), None),
             "feature": gene},
            warnings=[units_note])

    elif schema == "neighborhood_enrichment":
        enr = next((c for c in df.columns if "enrich" in str(c).lower()), None)
        freq = next((c for c in df.columns if "freq" in str(c).lower()), None)
        add("neighborhood_enrichment_matrix", 0.9,
            "Enrichment values per (neighbourhood, cell type) — the dot matrix shows "
            "enrichment as colour and frequency as point area.",
            {"neighborhood": neighborhood, "cell_type": cell_type,
             "enrichment": enr, "frequency": freq})

    # ---- precomputed differential results ----------------------------------
    if schema == "precomputed_differential":
        det = detect_de_columns(df)
        p_col = det.get("p_value") or det.get("adj_p")
        label = det.get("gene_symbol") or det.get("gene_id")
        add("volcano_plot", 0.92,
            "Table has a fold-change column and a p-value/FDR column — a volcano plot "
            "summarises effect size vs significance. p-values are read verbatim; the app "
            "does not run differential-expression analysis.",
            {"x": det.get("logFC"), "p": p_col, "label": label},
            thresholds={"lfc_cutoff": 1.0, "p_cutoff": 0.05})
        if profile.has_role("estimate_lower") and profile.has_role("estimate_upper"):
            add("forest_plot", 0.6,
                "Effect sizes with confidence intervals are present — a forest plot compares "
                "them across features.",
                {"label": det.get("gene_symbol") or det.get("gene_id"),
                 "estimate": det.get("logFC"),
                 "lower": profile.role_column("estimate_lower"),
                 "upper": profile.role_column("estimate_upper")})
        if profile.has_role("ave_expr"):
            add("ma_plot", 0.7,
                "Average-abundance and fold-change columns are present — an MA plot shows "
                "log-fold-change against mean abundance, highlighting significant features.",
                {"x": profile.role_column("ave_expr"), "y": det.get("logFC"), "p": p_col,
                 "label": label},
                thresholds={"p_cutoff": 0.05})

    # ---- survival -----------------------------------------------------------
    elif schema == "survival":
        cm = {"time": profile.role_column("survival_time"),
              "event": profile.role_column("survival_event"),
              "group": profile.role_column("group")}
        add("kaplan_meier_survival_curve", 0.88,
            "Time-to-event and event-status columns are present — a Kaplan–Meier curve with a "
            "log-rank test compares survival between groups.",
            cm, stats=suggest_stats("kaplan_meier_survival_curve", cm, df),
            missing=[] if cm["group"] else ["group (no grouping column detected)"])

    # ---- classification -----------------------------------------------------
    elif schema == "classification":
        lbl = profile.role_column("class_label")
        scr = profile.role_column("class_score")
        add("roc_curve", 0.85,
            "A binary label and a numeric prediction score are present — an ROC curve shows "
            "classifier discrimination (AUC).",
            {"label": lbl, "score": scr})
        add("precision_recall_curve", 0.72,
            "Precision-recall curve (AUPRC) — preferred when classes are imbalanced.",
            {"label": lbl, "score": scr})
        add("calibration_plot", 0.6,
            "A calibration plot checks whether predicted probabilities match observed rates "
            "(Brier score).",
            {"label": lbl, "score": scr})
        if profile.role_column("class_predicted"):
            add("confusion_matrix", 0.6,
                "A predicted-label column is present — a confusion matrix summarises errors.",
                {"true": lbl, "predicted": profile.role_column("class_predicted")})

    # ---- enrichment ---------------------------------------------------------
    elif schema == "enrichment":
        color = profile.role_column("adj_p") or profile.role_column("p_value")
        add("enrichment_dotplot", 0.8,
            "Pathway/term rows with counts/ratios and significance are present — an enrichment "
            "dot plot ranks terms by significance and size.",
            {"y": profile.role_column("enrichment_term"),
             "x": profile.role_column("enrichment_ratio") or profile.role_column("enrichment_count"),
             "size": profile.role_column("enrichment_count"),
             "color": color})

    # ---- mutation -----------------------------------------------------------
    elif schema == "mutation_matrix":
        add("oncoprint_mutation_heatmap", 0.78,
            "Sample / gene / alteration columns are present — an oncoprint summarises the "
            "mutation landscape across samples.",
            {"sample": profile.role_column("mutation_sample"),
             "row": profile.role_column("mutation_gene"),
             "fill": profile.role_column("mutation_type")})
        if profile.has_role("position"):
            add("lollipop_mutation_plot", 0.55,
                "Protein positions are present — a lollipop plot shows mutation hotspots along "
                "the protein.",
                {"x": profile.role_column("position"),
                 "color": profile.role_column("mutation_type")})

    # ---- correlation matrix -------------------------------------------------
    elif schema == "correlation_matrix":
        add("heatmap_clustered_matrix", 0.82,
            "A square, symmetric correlation matrix — a clustered heatmap reveals structure "
            "among features.",
            {"row_id": profile.matrix_feature_col},
            cost="medium")

    # ---- numeric / expression-like matrix -----------------------------------
    elif schema in ("numeric_matrix", "expression_like_matrix", "matrix_plus_metadata"):
        cells = profile.n_rows * max(1, len(profile.matrix_sample_columns))
        big = cells > _LARGE_CELLS
        add("heatmap_clustered_matrix", 0.85,
            "A wide numeric matrix (features × samples) — a clustered heatmap with row/column "
            "clustering shows structure. Use 'Define groups' to tag samples for group plots.",
            {"row_id": profile.matrix_feature_col},
            cost="high" if big else "medium", confirm=big)
        add("pca_scatter_from_matrix", 0.7,
            "A numeric matrix is ideal for PCA to summarise sample structure. Provide a sample "
            "metadata table to colour points by group.",
            {"matrix_row_id": profile.matrix_feature_col},
            missing=["color / shape (needs a sample metadata table)"],
            cost="high" if big else "medium", confirm=big)
        recs[-1].plot_spec_draft = None  # PCA needs an aux metadata table to render

    # ---- paired -------------------------------------------------------------
    elif schema == "paired":
        y = _numeric_values(profile)
        cm = {"x": profile.role_column("group"), "y": y[0] if y else None}
        add("paired_slopegraph", 0.75,
            "Repeated measures per subject across conditions — a paired slopegraph connects each "
            "subject's values across conditions.",
            {"subject": profile.role_column("subject"),
             "condition": profile.role_column("condition"),
             "value": y[0] if y else None})
        add("boxplot_or_violin_with_points", 0.7,
            "The same paired data as distributions — a box/violin with points; choose a paired "
            "test (paired t / Wilcoxon).",
            cm, stats=suggest_stats("boxplot_or_violin_with_points", cm, df))

    # ---- generic long (group + numeric value) -------------------------------
    elif schema == "generic_long":
        y = _numeric_values(profile)
        yy = y[0] if y else None
        cm = {"x": profile.role_column("group"), "y": yy}
        add("boxplot_or_violin_with_points", 0.72,
            "A grouping column and a numeric value — a box/violin plot with points compares the "
            "distribution across groups, with an appropriate statistical test.",
            cm, stats=suggest_stats("boxplot_or_violin_with_points", cm, df))
        if yy:
            add("ridge_or_density_plot", 0.62,
                "A grouping column and a numeric value — a ridge / density plot shows and "
                "compares each group's full distribution.",
                {"x": yy, "group": profile.role_column("group"), "overlap": 0.6})
        add("barplot_with_error_bar", 0.6,
            "Compare group means with error bars.",
            {"x": profile.role_column("group"), "y": yy, "color": profile.role_column("group")},
            stats=suggest_stats("barplot_with_error_bar", cm, df))
        # two categoricals + a value -> grouped bar
        cats = [c for c in profile.categorical_columns if c != profile.role_column("group")]
        if cats and yy:
            add("grouped_barplot_with_error_bar", 0.55,
                "Two categorical factors and a value — a grouped bar plot shows the interaction.",
                {"x": profile.role_column("group"), "group": cats[0], "y": yy})
        if len(y) >= 2:
            add("scatterplot_with_regression", 0.5,
                "Two numeric columns — a scatter with regression shows their relationship.",
                {"x": y[0], "y": y[1]}, stats=suggest_stats(
                    "scatterplot_with_regression", {"x": y[0], "y": y[1]}, df))

    # ---- GWAS (Manhattan + Q-Q) ---------------------------------------------
    elif schema == "gwas":
        add("manhattan_plot", 0.82,
            "Chromosome / position / p-value columns are GWAS summary statistics — a Manhattan "
            "plot shows −log10(p) across the genome with genome-wide/suggestive lines.",
            {"chrom": profile.role_column("chromosome"),
             "pos": profile.role_column("position"),
             "p": profile.role_column("p_value")})
        add("qq_plot", 0.7,
            "A Q-Q plot of the p-values checks for genomic inflation (λ).",
            {"mode": "pvalue", "p": profile.role_column("p_value")})

    # ---- dose-response (4PL curve) ------------------------------------------
    elif schema == "dose_response":
        add("dose_response_curve", 0.82,
            "Dose and response columns are present — a dose-response curve fits a 4-parameter "
            "logistic and reports EC50/IC50.",
            {"dose": profile.role_column("dose"), "response": profile.role_column("response"),
             "group": profile.role_column("group")})

    # ---- network edge list --------------------------------------------------
    elif schema == "network_edge_list":
        add("network_graph", 0.8,
            "Source / target columns are a network edge list — a network graph lays out nodes and "
            "edges (spring layout; filter by weight/degree).",
            {"source": profile.role_column("source"),
             "target": profile.role_column("target"),
             "weight": profile.role_column("weight") if profile.has_role("weight") else None},
            cost="medium")
        # Secondary, low-confidence suggestion for the same edge-list shape: a chord diagram
        # shows the flow between categories on one ring (best for <= ~20 categories).
        add("chord_diagram", 0.55,
            "The same source / target edge list can be drawn as a Circos-style chord diagram: one "
            "ring of categories with ribbons proportional to the link value (no statistics).",
            {"source": profile.role_column("source"),
             "target": profile.role_column("target"),
             "value": profile.role_column("weight") if profile.has_role("weight") else None,
             "group": None})

    # Nothing matched or unknown → offer a scatter if there are 2+ numerics.
    if not recs:
        y = _numeric_values(profile)
        if len(y) >= 2:
            add("scatterplot_with_regression", 0.4,
                "Two or more numeric columns — a scatter with regression is a safe starting point.",
                {"x": y[0], "y": y[1]})

    recs.sort(key=lambda r: r.confidence, reverse=True)
    return recs
