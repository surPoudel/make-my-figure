"""Contact sheets for visual review of the legend and colour work.

Four sheets, written to visual_qc/ beside this file. They exist to be LOOKED at:
the audit proves a control changed the right artist, which is not the same as the
figure being right - clipping, overlap, contrast and legibility are judged by eye.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent / "visual_qc"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))

from make_my_figure_core import examples                     # noqa: E402
from make_my_figure_core.plots import registry               # noqa: E402


def render(plot_type, *, style=None, layout=None, mapping=None, df=None):
    table, aux, spec = examples.load_example(plot_type)
    spec = json.loads(json.dumps(spec))
    if style:
        spec["style"] = {**(spec.get("style") or {}), **style}
    if layout:
        spec["layout"] = {**(spec.get("layout") or {}), **layout}
    if mapping:
        spec["mapping"] = {**spec["mapping"], **mapping}
    frame = table.dataframe if df is None else df
    return registry.render(spec, frame,
                           aux={k: v.dataframe for k, v in (aux or {}).items()})


def sheet(name, panels, cols=2, size=(5.2, 3.6)):
    """One PNG of rendered figures, each captioned with what it shows."""
    import matplotlib.image as mpimg
    import io

    rows = (len(panels) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(size[0] * cols, size[1] * rows))
    axes = np.atleast_1d(axes).ravel()
    for ax, (caption, result) in zip(axes, panels):
        buf = io.BytesIO()
        result.figure.savefig(buf, format="png", dpi=110, bbox_inches="tight",
                              facecolor="white")
        buf.seek(0)
        ax.imshow(mpimg.imread(buf))
        ax.set_title(caption, fontsize=9)
        plt.close(result.figure)
    for ax in axes:
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
    fig.tight_layout()
    path = OUT / f"{name}.png"
    fig.savefig(path, dpi=110, facecolor="white")
    plt.close(fig)
    print(f"  wrote {path.relative_to(ROOT)}")


def main():
    warnings.filterwarnings("ignore")

    # 1. legend geometry, on plots that place their legend differently
    sheet("01_legend_geometry", [
        ("scatter: default", render("scatterplot_with_regression")),
        ("scatter: offset +24,-18 pt",
         render("scatterplot_with_regression",
                layout={"legend_offset_x": 24.0, "legend_offset_y": -18.0})),
        ("volcano: default (outside by design)", render("volcano_plot")),
        ("volcano: nudged +18 pt, still outside",
         render("volcano_plot", layout={"legend_offset_x": 18.0})),
        ("survival: outside right + 24 pt gap",
         render("kaplan_meier_survival_curve",
                layout={"legend_location": "outside right", "legend_gap": 24.0})),
        ("survival: roomy legend",
         render("kaplan_meier_survival_curve",
                layout={"legend_borderpad": 1.4, "legend_labelspacing": 1.2})),
    ])

    # 2. the three plots whose class colours were exposed
    sheet("02_class_colours", [
        ("MA: default", render("ma_plot")),
        ("MA: up/down/ns recoloured",
         render("ma_plot", mapping={"color_up": "#D81B60", "color_down": "#1E88E5",
                                    "color_ns": "#DDDDDD"})),
        ("Bland-Altman: default", render("bland_altman_plot")),
        ("Bland-Altman: limits apart + agreement categories",
         render("bland_altman_plot",
                mapping={"loa_upper_color": "#D81B60", "loa_lower_color": "#1E88E5",
                         "color_points_by_agreement": True,
                         "point_color_above": "#D81B60", "point_color_within": "#9E9E9E",
                         "point_color_below": "#1E88E5"})),
        ("UpSet: default", render("upset_plot")),
        ("UpSet: bars told apart",
         render("upset_plot", mapping={"intersection_bar_color": "#6A1B9A",
                                       "set_bar_color": "#00897B"})),
    ])

    # 3. how many categories a palette can carry
    rng = np.random.default_rng(7)
    panels = []
    for n in (2, 3, 5, 10):
        df = pd.DataFrame({"c": [f"G{i:02d}" for i in range(n) for _ in range(5)],
                           "m": rng.normal(1.0, 0.2, n * 5)})
        spec = registry.make_spec("barplot_with_error_bar", "t.csv", "publication")
        spec["mapping"] = {"x": "c", "y": "m", "color": "c", "error": "sem"}
        result = registry.render(spec, df)
        warned = any("categories were drawn" in w for w in result.warnings)
        panels.append((f"{n} groups, publication"
                       f"{' - WARNS: colours repeat' if warned else ''}", result))
    df10 = pd.DataFrame({"c": [f"G{i:02d}" for i in range(10) for _ in range(5)],
                         "m": rng.normal(1.0, 0.2, 50)})
    for palette in ("tab20", "Paired"):
        spec = registry.make_spec("barplot_with_error_bar", "t.csv", "publication")
        spec["mapping"] = {"x": "c", "y": "m", "color": "c", "error": "sem"}
        spec["style"] = {"palette_name": palette}
        panels.append((f"10 groups, {palette} (the suggested fix)",
                       registry.render(spec, df10)))
    sheet("03_category_capacity", panels, cols=3, size=(4.4, 3.2))

    # 4. per-category overrides and the continuous maps
    sheet("04_colour_kinds", [
        ("categorical: palette", render("boxplot_or_violin_with_points")),
        ("categorical: one group overridden by name",
         render("scatterplot_with_regression",
                style={"color_overrides": {"Responder": "#D81B60"}})),
        ("continuous: default sequential", render("spatial_feature_map")),
        ("continuous: Greys", render("spatial_feature_map",
                                     style={"sequential_cmap": "Greys"})),
        ("continuous: diverging default", render("heatmap_clustered_matrix")),
        ("continuous: PuOr", render("heatmap_clustered_matrix",
                                    style={"diverging_cmap": "PuOr"})),
    ])
    print(f"\n  {len(list(OUT.glob('*.png')))} sheets in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
