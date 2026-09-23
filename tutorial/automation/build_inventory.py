"""Build tutorial/audit/plot_tutorial_inventory.csv from the LIVE plot registry.

Nothing is hard-coded: plot ids, display names, column roles, options, statistics suggestions,
example datasets and preset capabilities are read from the code that the desktop application
itself imports. Tutorial and video status come from what exists under tutorial/.

    python tutorial/automation/build_inventory.py
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
TUT = os.path.join(ROOT, "tutorial")

import matplotlib  # noqa: E402
matplotlib.use("Agg")

from make_my_figure_core import examples, ui_hints, version  # noqa: E402
from make_my_figure_core.plots import registry  # noqa: E402
from make_my_figure_core.statistics import recommend_tests  # noqa: E402
from make_my_figure_core.statistics.test_registry import TESTS  # noqa: E402
from make_my_figure_core.styles.capabilities import get_style_capabilities  # noqa: E402

# Families are a tutorial grouping (folder), not an application concept.
FAMILY = {
    "barplot_with_error_bar": "03_Group_Comparisons", "grouped_barplot_with_error_bar": "03_Group_Comparisons",
    "boxplot_or_violin_with_points": "03_Group_Comparisons", "dot_strip_plot": "03_Group_Comparisons",
    "beeswarm_plot": "03_Group_Comparisons", "raincloud_plot": "03_Group_Comparisons",
    "paired_slopegraph": "03_Group_Comparisons", "ridge_or_density_plot": "02_Basic_Plots",
    "histogram_distribution": "02_Basic_Plots", "lineplot_timecourse_with_error_band": "02_Basic_Plots",
    "stacked_bar_composition": "02_Basic_Plots", "waterfall_plot": "02_Basic_Plots",
    "scatterplot_with_regression": "04_Relationships_and_Regression",
    "bland_altman_plot": "04_Relationships_and_Regression", "calibration_plot": "04_Relationships_and_Regression",
    "roc_curve": "04_Relationships_and_Regression", "precision_recall_curve": "04_Relationships_and_Regression",
    "confusion_matrix": "04_Relationships_and_Regression", "dose_response_curve": "04_Relationships_and_Regression",
    "heatmap_clustered_matrix": "05_Matrix_and_Omics", "hierarchical_clustering": "05_Matrix_and_Omics",
    "hierarchical_dendrogram": "05_Matrix_and_Omics", "pca_scatter_from_matrix": "05_Matrix_and_Omics",
    "embedding_scatter": "05_Matrix_and_Omics", "volcano_plot": "05_Matrix_and_Omics", "ma_plot": "05_Matrix_and_Omics",
    "enrichment_dotplot": "05_Matrix_and_Omics", "manhattan_plot": "05_Matrix_and_Omics", "qq_plot": "05_Matrix_and_Omics",
    "kaplan_meier_survival_curve": "07_Survival_and_Effect_Plots", "forest_plot": "07_Survival_and_Effect_Plots",
    "swimmer_plot": "07_Survival_and_Effect_Plots", "spider_plot": "07_Survival_and_Effect_Plots",
    "oncoprint_mutation_heatmap": "08_Advanced_Plots", "lollipop_mutation_plot": "08_Advanced_Plots",
    "network_graph": "08_Advanced_Plots", "chord_diagram": "08_Advanced_Plots", "sankey_plot": "08_Advanced_Plots",
    "upset_plot": "08_Advanced_Plots",
}

# Pilot tutorials are named by topic; map plot ids to their action script / video script ids.
PLOT_TO_TUTORIAL = {
    "scatterplot_with_regression": "scatter_regression",
    "boxplot_or_violin_with_points": "group_comparison_box",
    "volcano_plot": "volcano_manual_mapping",
    "heatmap_clustered_matrix": "heatmap_clustered",
    "kaplan_meier_survival_curve": "kaplan_meier",
}

COLUMNS = ["plot_id", "display_name", "plot_family", "required_columns", "optional_columns",
           "recommended_input_shape", "compatible_statistics", "transformations", "annotations",
           "preset_support", "Figure_Package_support", "example_dataset", "existing_manual_section",
           "tutorial_status", "video_status"]

INPUT_SHAPE = {
    "long": "long table: one row per observation",
    "matrix": "feature x sample matrix (one id column + numeric value columns)",
    "edges": "edge list: one row per link",
    "de": "one row per feature with effect size and p-value",
    "survival": "one row per subject: time, event (0/1), group",
    "sets": "one column per set (membership 0/1) or long membership table",
}
SHAPE = {"heatmap_clustered_matrix": "matrix", "hierarchical_clustering": "matrix", "hierarchical_dendrogram": "matrix",
         "pca_scatter_from_matrix": "matrix", "network_graph": "edges", "chord_diagram": "edges", "sankey_plot": "edges",
         "volcano_plot": "de", "ma_plot": "de", "kaplan_meier_survival_curve": "survival", "upset_plot": "sets"}


def manual_section(pt: str, display: str) -> str:
    path = os.path.join(ROOT, "docs", "manuals", "User_Manual", "MakeMyFigure_User_Manual.md")
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.startswith("#") and (pt in line or display.lower() in line.lower()):
                return line.strip("# \n")[:80]
    return ""


def tutorial_status(pt: str) -> str:
    plots_dir = os.path.join(TUT, "plots")
    if os.path.exists(os.path.join(plots_dir, f"{pt}.md")):
        return "WRITTEN"
    return "MISSING"


def video_status(pt: str) -> str:
    ids = [pt, PLOT_TO_TUTORIAL.get(pt, pt)]
    mapping = os.path.join(TUT, "videos", "video_links.json")
    if os.path.exists(mapping):
        with open(mapping, encoding="utf-8") as fh:
            links = json.load(fh).get("videos", {})
        for i in ids:
            if links.get(i) and not str(links[i]).startswith("VIDEO_URL_"):
                return "PUBLISHED"
    return "SCRIPT" if any(os.path.exists(os.path.join(TUT, "video_scripts", f"{i}.md")) for i in ids) else "MISSING"


def compatible_statistics(pt: str) -> str:
    try:
        rec = recommend_tests(pt, registry.default_mapping(pt))
    except Exception:  # noqa: BLE001
        return ""
    ids = rec.get("suggested") or []
    return "; ".join(TESTS[i].label for i in ids if i in TESTS)


def main() -> int:
    pts = registry.available_plot_types()
    manifest = examples.load_manifest()
    by_pt = {e["plot_type"]: e for e in manifest.get("plot_types", [])}
    rows = []
    for pt in pts:
        display = registry.display_name(pt)
        fields = ui_hints.column_fields(pt)
        defaults = registry.default_mapping(pt)
        req = [f for f in fields if defaults.get(f) not in (None, "") and f in defaults]
        opt = [f for f in fields if f not in req]
        ex = by_pt.get(pt, {})
        opts = ui_hints.options(pt)
        caps = get_style_capabilities(pt)
        cap_keys = [k for k in ("legend", "colorbar", "markers", "line_width", "error_bars", "palette")
                    if getattr(caps, k, None) not in (None, False)]
        rows.append({
            "plot_id": pt, "display_name": display, "plot_family": FAMILY.get(pt, "08_Advanced_Plots"),
            "required_columns": "; ".join(req) if req else "(chosen in Map columns)",
            "optional_columns": "; ".join(opt),
            "recommended_input_shape": INPUT_SHAPE[SHAPE.get(pt, "long")],
            "compatible_statistics": compatible_statistics(pt),
            "transformations": "wide_to_long; correlation_matrix; value_counts (Define groups / Matrix workflow where applicable)"
            if SHAPE.get(pt, "long") in ("long", "matrix") else "",
            "annotations": "; ".join(o.key for o in opts)[:200],
            "preset_support": "yes (style presets: " + ", ".join(cap_keys) + ")" if cap_keys else "yes",
            "Figure_Package_support": "yes",
            "example_dataset": (ex.get("files") or {}).get("csv", ""),
            "existing_manual_section": manual_section(pt, display),
            "tutorial_status": tutorial_status(pt),
            "video_status": video_status(pt),
        })
    out = os.path.join(TUT, "audit", "plot_tutorial_inventory.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    summary = {"version": version.__version__, "registered_plot_types": len(pts),
               "tutorials_written": sum(r["tutorial_status"] == "WRITTEN" for r in rows),
               "video_scripts": sum(r["video_status"] in ("SCRIPT", "PUBLISHED") for r in rows)}
    print(json.dumps(summary))
    with open(os.path.join(TUT, "audit", "inventory_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
