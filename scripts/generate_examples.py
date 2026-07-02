"""Render example figures for all 5 Milestone-1 plot types from mock data.

Usage:
    python scripts/generate_examples.py [--style nature_like] [--out reports/example_figures]
"""

from __future__ import annotations

import argparse
import os
import sys

import matplotlib

matplotlib.use("Agg")

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from make_my_figure_core.io.loaders import load_table
from make_my_figure_core.plots.registry import make_spec, render_to_files

CASES = [
    ("barplot_with_error_bar", "mock_data/barplot_error_raw.csv"),
    ("grouped_barplot_with_error_bar", "mock_data/grouped_barplot_error.csv"),
    ("heatmap_clustered_matrix", "mock_data/heatmap_expression_matrix.tsv"),
    ("volcano_plot", "mock_data/volcano_plot.csv"),
    ("scatterplot_with_regression", "mock_data/scatter_regression.csv"),
    ("boxplot_or_violin_with_points", "mock_data/box_violin_points.csv"),
    ("lineplot_timecourse_with_error_band", "mock_data/line_timecourse.tsv"),
    ("ridge_or_density_plot", "mock_data/ridge_density.csv"),
    ("enrichment_dotplot", "mock_data/enrichment_dotplot.csv"),
    ("kaplan_meier_survival_curve", "mock_data/survival_km.csv"),
    ("stacked_bar_composition", "mock_data/stacked_composition.csv"),
    ("waterfall_plot", "mock_data/waterfall_response.csv"),
    ("pca_scatter_from_matrix", "mock_data/pca_expression_matrix.tsv"),
    ("oncoprint_mutation_heatmap", "mock_data/oncoprint_long.csv"),
    ("lollipop_mutation_plot", "mock_data/lollipop_mutations.csv"),
    ("roc_curve", "mock_data/roc_curve_scores.csv"),
    ("forest_plot", "mock_data/forest_plot.csv"),
]

# Plot types needing an auxiliary table (matrix sample -> metadata mapping).
AUX = {"pca_scatter_from_matrix": ("metadata", "mock_data/pca_sample_metadata.csv")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", default="nature_like")
    parser.add_argument("--out", default="reports/example_figures")
    parser.add_argument("--formats", default="png,svg")
    args = parser.parse_args()

    os.makedirs(os.path.join(_REPO_ROOT, args.out), exist_ok=True)
    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    for plot_type, rel in CASES:
        info = load_table(os.path.join(_REPO_ROOT, rel))
        spec = make_spec(plot_type, os.path.basename(rel), args.style)
        base = os.path.join(_REPO_ROOT, args.out, plot_type)
        aux = None
        if plot_type in AUX:
            key, aux_rel = AUX[plot_type]
            aux = {key: load_table(os.path.join(_REPO_ROOT, aux_rel)).dataframe}
        out = render_to_files(spec, info.dataframe, base, formats=formats, aux=aux)
        print(f"{plot_type}: {[os.path.basename(f) for f in out['files']]}"
              f"{' WARN: ' + '; '.join(out['warnings']) if out['warnings'] else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
