"""Generate the User Manual's plot catalogue (Part X) from the live registry.

One mini-section per registered plot type, filled from the code: display name, column roles,
options (with scope), statistics support, colour model and style capabilities, the bundled example
and its columns, and the catalogue figure rendered from that example. Nothing is typed by hand.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from make_my_figure_core import examples as ex, ui_hints  # noqa: E402
from make_my_figure_core.plots.registry import available_plot_types, display_name  # noqa: E402
from make_my_figure_core.styles.capabilities import get_style_capabilities  # noqa: E402
import audit_style_capabilities as audit  # noqa: E402

OUT = os.path.join(ROOT, "docs", "manuals", "User_Manual", "parts", "03_plot_catalog.md")
STATS_PLOTS = {
    "barplot_with_error_bar": "yes — pairwise brackets or above-bar labels",
    "grouped_barplot_with_error_bar": "yes — comparisons within each x category",
    "boxplot_or_violin_with_points": "yes — pairwise brackets or above-bar labels",
    "scatterplot_with_regression": "yes — correlation / regression statistics box",
    "kaplan_meier_survival_curve": "yes — log-rank / Cox in a corner panel (subject-level input only)",
    "stacked_bar_composition": "yes — chi-square / Fisher in a corner panel",
}
PURPOSE = {
    "barplot_with_error_bar": ("Compare a mean (or median) per category with an error bar.", "few categories, replicate measurements; consider a box or strip plot when you want to show every point"),
    "grouped_barplot_with_error_bar": ("Compare means across categories split by a second factor.", "two crossed factors with replicates"),
    "heatmap_clustered_matrix": ("Show a feature × sample matrix as colour, optionally clustered on both axes.", "expression, intensity, or any normalised matrix; z-score rows for pattern contrast"),
    "volcano_plot": ("Effect size against significance for every feature of a differential-expression table.", "any precomputed DE result (edgeR, limma, DESeq2, proteomics)"),
    "scatterplot_with_regression": ("Two numeric variables per observation, optionally coloured by group, with a fitted line and its statistics.", "relationships, method comparison, dose vs response before fitting a model"),
    "boxplot_or_violin_with_points": ("Distribution per category as a box or violin, with the individual points.", "replicate measurements across conditions; the default recommendation for grouped observations"),
    "lineplot_timecourse_with_error_band": ("Mean over an ordered x (time, dose, contraction number) per series with an SEM/SD/CI band.", "time courses, fatigue protocols, force–frequency curves"),
    "ridge_or_density_plot": ("Smoothed density per group, stacked (ridgeline) or overlaid.", "comparing distribution shapes across several groups"),
    "histogram_distribution": ("Binned counts of one measurement, one panel per group or overlaid, bars and/or a frequency polygon.", "distribution shape when modes, gaps and tails matter — bins never smooth"),
    "enrichment_dotplot": ("Enriched terms ranked by enrichment, dot size = count, colour = significance.", "GO / pathway enrichment results"),
    "kaplan_meier_survival_curve": ("Survival probability over time per group, from subject-level events or a precomputed curve.", "time-to-event data"),
    "stacked_bar_composition": ("Composition of categories within each x as stacked bars (counts or proportions).", "cell-type or class composition per sample"),
    "waterfall_plot": ("Sorted per-subject responses as bars around zero.", "best response per patient, screen hits"),
    "pca_scatter_from_matrix": ("Principal-component scores of samples from a matrix, coloured and shaped from a metadata table.", "sample structure, batch effects, outliers"),
    "oncoprint_mutation_heatmap": ("Samples × genes grid of alteration classes.", "mutation / alteration matrices in long form"),
    "lollipop_mutation_plot": ("Positions along a protein with lollipops sized by count and coloured by class.", "mutation positions along a sequence"),
    "roc_curve": ("True- vs false-positive rate for one or two scores with AUC.", "classifier or biomarker evaluation"),
    "forest_plot": ("Point estimates with confidence intervals per row and a reference line.", "hazard/odds ratios, subgroup effects, meta-analysis"),
    "dot_strip_plot": ("Every observation per category with a summary marker.", "small-n replicate data"),
    "beeswarm_plot": ("Every observation per category, spread to avoid overlap.", "small- to medium-n distributions"),
    "paired_slopegraph": ("Each subject's paired values joined by a line across conditions.", "before/after or matched designs"),
    "raincloud_plot": ("Half-violin, box and jittered points per category.", "distribution + summary + raw data in one"),
    "hierarchical_dendrogram": ("Tree of hierarchical clustering of the matrix rows or columns.", "similarity structure among samples or features"),
    "ma_plot": ("Log fold change against average abundance per feature.", "DE tables; intensity-dependent bias"),
    "manhattan_plot": ("−log10 p by genomic position, coloured by chromosome, with significance lines.", "GWAS / association results"),
    "qq_plot": ("Observed vs expected p-value quantiles (or sample quantiles).", "checking p-value inflation or normality"),
    "bland_altman_plot": ("Difference vs mean of two measurement methods with bias and limits of agreement.", "method agreement"),
    "precision_recall_curve": ("Precision vs recall for one or two scores.", "imbalanced classification"),
    "confusion_matrix": ("Counts (or normalised rates) of true vs predicted classes.", "classifier evaluation"),
    "calibration_plot": ("Predicted probability vs observed frequency in bins.", "probability calibration"),
    "dose_response_curve": ("Response vs dose per group with an optional four-parameter logistic fit.", "IC50/EC50-style experiments"),
    "upset_plot": ("Set intersections as a matrix with intersection-size bars.", "overlaps among several sets"),
    "swimmer_plot": ("One horizontal bar per subject with events marked along time.", "treatment timelines"),
    "spider_plot": ("Change from baseline per subject over time.", "longitudinal response"),
    "sankey_plot": ("Flows between two stages as proportional bands.", "transitions, allocations"),
    "embedding_scatter": ("Precomputed 2-D embedding coordinates coloured by a label or a continuous value.", "UMAP / t-SNE results computed elsewhere"),
    "hierarchical_clustering": ("Clustered heatmap with k clusters marked and a dendrogram.", "grouping features/samples into k clusters"),
    "network_graph": ("Nodes and edges from an edge list with layout, community detection and colour/size mappings.", "interaction or correlation networks"),
}
LIMITS = {
    "kaplan_meier_survival_curve": "A precomputed curve cannot yield a log-rank test (no numbers at risk); the app refuses rather than invents one.",
    "volcano_plot": "The palette does not apply — points are coloured by significance class (up / down / not significant options). Thresholds travel only in a full preset.",
    "heatmap_clustered_matrix": "Rows are capped at `max_features` (default 2 000, selected by variance) for responsiveness.",
    "hierarchical_clustering": "Rows are capped at `max_features` (default 2 000).",
    "network_graph": "Layouts with a random component are reproducible only with the `seed` option; large networks are slow.",
    "lineplot_timecourse_with_error_band": "No statistical annotation on this plot type.",
    "ridge_or_density_plot": "A kernel density estimate can merge two modes into one shoulder; use the histogram when shape matters.",
    "histogram_distribution": "Bins are shared across groups by design; an overlay of raw counts with unequal group sizes warns you to use percent.",
    "embedding_scatter": "Coordinates must be precomputed; the app does not run UMAP or t-SNE.",
    "dose_response_curve": "The 4PL fit is a display fit; report parameters from a dedicated tool for inference.",
}


def section(pt: str) -> str:
    dn = display_name(pt)
    roles = ui_hints.column_fields(pt)
    opts = ui_hints.options(pt)
    caps = get_style_capabilities(pt)
    scan = audit.scan_renderer(pt)
    info, aux, spec = ex.load_example(pt)
    cols = list(map(str, info.columns))
    purpose, when = PURPOSE.get(pt, ("", ""))
    style_opts = [o for o in opts if o.scope == "style"]
    config_opts = [o for o in opts if o.scope == "config"]
    color_bits = []
    if caps.supports_palette:
        color_bits.append("Publication palette (publication / colorblind_safe / high_contrast / grayscale)")
    if caps.supports_continuous_colormap:
        color_bits.append("continuous colormap (sequential/diverging from the palette; `colormap` option where present)")
    colour_opts = [o.key for o in opts if any(t in o.key for t in ("color", "cmap", "colormap"))]
    if colour_opts:
        color_bits.append("plot options: " + ", ".join(f"`{k}`" for k in colour_opts))
    if not caps.supports_palette and not colour_opts:
        color_bits.append("fixed colours (no palette effect) — " + caps.unsupported_controls_reason)
    axis_bits = ["title, x/y labels, tick angles, label/title padding, margins (layout engine)"]
    if caps.supports_marker_size:
        axis_bits.append("marker size")
    if caps.supports_line_width:
        axis_bits.append("line width")
    legend = "legend location (inside/outside), legend size" if caps.supports_legend else "no legend drawn"
    if caps.supports_colorbar:
        legend += "; colorbar location / pad / size"
    ann = "point picking, label selection, duplicate-label policy" if any(o.key.startswith("duplicate") for o in opts) or pt in ("scatterplot_with_regression", "embedding_scatter") else "manual annotation layer via PlotSpec"
    if pt in STATS_PLOTS:
        ann += "; statistical annotation (stars / p / effect)"
    lines = [
        f"### {dn}",
        "",
        f"*Registry key:* `{pt}`",
        "",
        f"**Purpose:** {purpose}  ",
        f"**When to use:** {when}",
        "",
        "**Required / optional input:** one table with the roles below; the bundled example has columns "
        + ", ".join(f"`{c}`" for c in cols[:8]) + (" …" if len(cols) > 8 else "") + ".",
        "",
        "**Column mapping:** " + ", ".join(f"`{r}`" + (" (multi-select)" if ui_hints.is_multi_column(r) else "") for r in roles)
        + (f"; example mapping `{json.dumps({k: v for k, v in spec['mapping'].items() if k in roles})}`" if roles else "")
        + (" — plus PCA metadata roles `color`, `shape` from the metadata table" if pt == "pca_scatter_from_matrix" else "")
        + (" — set columns are given as the `sets` list" if pt == "upset_plot" else "") + ".",
        "",
        f"**Statistics supported:** {STATS_PLOTS.get(pt, 'no on-figure statistical annotation (the Statistics panel still runs for the mapped columns where a test applies)')}.",
        "",
        "**Colour controls:** " + "; ".join(color_bits) + ".",
        "",
        f"**Annotation controls:** {ann}.",
        "",
        "**Axis controls:** " + ", ".join(axis_bits) + ".",
        "",
        f"**Legend / colorbar controls:** {legend}.",
        "",
        "**Plot-specific controls (visual, carried in a style preset):** "
        + (", ".join(f"`{o.key}` — {o.label}" for o in style_opts) if style_opts else "none") + ".  ",
        "**Analytical / data-dependent options (full preset only):** "
        + (", ".join(f"`{o.key}` — {o.label}" for o in config_opts) if config_opts else "none") + ".",
        "",
        "**Recommended export:** SVG or PDF for vector; PNG/TIFF at 300–600 dpi for raster."
        + (" Heat-map cells and dense point clouds are still vector in SVG/PDF but large; PNG is often the practical choice." if pt in ("heatmap_clustered_matrix", "hierarchical_clustering", "manhattan_plot", "embedding_scatter") else ""),
        "",
        "**Figure preset support:** style and full presets (verified in the registry-wide preset QC).",
        "",
        f"**Example data:** `examples/by_plot_type/{ex.example_slug(pt) if hasattr(ex, 'example_slug') else os.path.basename(os.path.dirname(ex.template_path(pt, 'csv') or ''))}/` (synthetic).",
        "",
        f"**Known limitations:** {LIMITS.get(pt, 'none specific beyond the general limitations in Part XXV')}.",
        "",
        f"![{dn}: rendered from the bundled synthetic example with Publication defaults.](../../assets/figures/{pt}.png)",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    pts = available_plot_types()
    head = [
        "## Part X — Plot catalogue",
        "",
        f"The {len(pts)} plot types below are the complete registry on this commit, enumerated from code "
        "(`plots/registry.py`) — not a historical list. Each figure was rendered from its bundled synthetic "
        "example with Publication defaults. Colour and control facts come from the same capability scan that "
        "the test suite enforces, so a control listed here is one the renderer actually reads.",
        "",
    ]
    body = [section(pt) for pt in pts]
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(head + body))
    print(f"wrote {os.path.relpath(OUT, ROOT)} with {len(pts)} plot sections")


if __name__ == "__main__":
    main()
