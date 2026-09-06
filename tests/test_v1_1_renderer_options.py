"""Renderer options and export fixes added for v1.1.0.

* tight-bbox exports include axis labels and titles (long axis labels were clipped);
* box/violin ``point_size``; volcano ``show_legend``; MA plot ``lfc_cutoff``;
* heatmap honours an explicit ``layout['aspect']``;
* title weight follows the ``title_font_weight`` style token in every renderer that sets it;
* forest plots on a log axis label ratio ticks as plain numbers;
* PCA legends go through ``place_legend`` (style tokens, legend controls);
* survival statistics annotation placement is configurable (``location``).
"""
import io
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.plots.registry import export_figure, figure_to_bytes, make_spec, render

rng = np.random.default_rng(11)


def _groups(n=30):
    return pd.DataFrame({"g": ["a", "b", "c"] * (n // 3), "y": rng.normal(size=n)})


def test_export_tight_bbox_keeps_long_axis_label(tmp_path):
    df = _groups()
    spec = make_spec("boxplot_or_violin_with_points", "t.csv", "publication", mapping={"x": "g", "y": "y"})
    spec["layout"] = {"x_label": "an extremely long x-axis label that runs well past the axes on both sides " * 2}
    fig = render(spec, df).figure
    fig.canvas.draw()
    label_w = fig.axes[0].xaxis.label.get_window_extent().width
    axes_w = fig.axes[0].get_window_extent().width
    assert label_w > axes_w  # the premise: the label is wider than the axes
    export_figure(fig, str(tmp_path / "long"), ["png"], dpi=100)
    from PIL import Image
    w_px = Image.open(tmp_path / "long.png").width
    # The exported width must cover the label (in pixels at 100 dpi) rather than only the axes.
    assert w_px >= label_w * (100 / fig.dpi) * 0.98
    plt.close(fig)


def test_figure_to_bytes_uses_the_same_tight_bbox():
    df = _groups()
    spec = make_spec("boxplot_or_violin_with_points", "t.csv", "publication", mapping={"x": "g", "y": "y"})
    spec["layout"] = {"x_label": "very long label " * 12}
    fig = render(spec, df).figure
    from PIL import Image
    w_long = Image.open(io.BytesIO(figure_to_bytes(fig, "png", dpi=72))).width
    plt.close(fig)
    spec["layout"] = {"x_label": "short"}
    fig2 = render(spec, df).figure
    w_short = Image.open(io.BytesIO(figure_to_bytes(fig2, "png", dpi=72))).width
    plt.close(fig2)
    assert w_long > w_short


def test_box_violin_point_size_option():
    df = _groups()
    sizes = {}
    for ps in (4.0, 40.0):
        spec = make_spec("boxplot_or_violin_with_points", "t.csv", "publication",
                         mapping={"x": "g", "y": "y", "points": True, "point_size": ps})
        ax = render(spec, df).figure.axes[0]
        coll = [c for c in ax.collections if len(c.get_offsets())]
        sizes[ps] = float(np.mean(coll[0].get_sizes()))
        plt.close(ax.figure)
    assert sizes[4.0] == 4.0 and sizes[40.0] == 40.0


def _de_table(n=200):
    return pd.DataFrame({"gene": [f"g{i}" for i in range(n)], "lfc": rng.normal(scale=1.5, size=n),
                         "p": rng.uniform(1e-6, 1, size=n), "mean": rng.uniform(1, 1e4, size=n)})


def test_volcano_show_legend_option():
    df = _de_table()
    spec = make_spec("volcano_plot", "t.csv", "publication", mapping={"x": "lfc", "p": "p", "label": "gene", "show_legend": False})
    ax = render(spec, df).figure.axes[0]
    assert ax.get_legend() is None
    spec["mapping"]["show_legend"] = True
    ax2 = render(spec, df).figure.axes[0]
    assert ax2.get_legend() is not None
    plt.close("all")


def test_ma_plot_lfc_cutoff_restricts_significance():
    df = _de_table()
    base = make_spec("ma_plot", "t.csv", "publication", mapping={"x": "mean", "y": "lfc", "p": "p", "label": "gene", "p_cutoff": 0.2})
    m0 = render(base, df).metadata
    base["mapping"]["lfc_cutoff"] = 1.0
    m1 = render(base, df).metadata
    expected = int(((df.p <= 0.2) & (df.lfc.abs() >= 1.0)).sum())
    assert m1["lfc_cutoff"] == 1.0
    assert m1["n_up"] + m1["n_down"] == expected
    assert m1["n_up"] + m1["n_down"] <= m0["n_up"] + m0["n_down"]
    plt.close("all")


def test_heatmap_explicit_aspect_sets_figure_shape():
    genes = [f"g{i}" for i in range(20)]
    df = pd.DataFrame(rng.normal(size=(20, 16)), columns=[f"s{i}" for i in range(16)])
    df.insert(0, "gene", genes)
    spec = make_spec("heatmap_clustered_matrix", "t.csv", "publication", mapping={"row_id": "gene"})
    spec["layout"] = {"column_width": "single", "aspect": 1.6}
    w, h = render(spec, df).figure.get_size_inches()
    assert abs(h / w - 1.6) < 0.01
    plt.close("all")


@pytest.mark.parametrize("plot_type,mapping,frame", [
    ("volcano_plot", {"x": "lfc", "p": "p", "label": "gene"}, "de"),
    ("heatmap_clustered_matrix", {"row_id": "gene"}, "matrix"),
])
def test_title_weight_follows_style_token(plot_type, mapping, frame):
    if frame == "de":
        df = _de_table()
    else:
        df = pd.DataFrame(rng.normal(size=(12, 8)), columns=[f"s{i}" for i in range(8)]); df.insert(0, "gene", [f"g{i}" for i in range(12)])
    spec = make_spec(plot_type, "t.csv", "publication", mapping=mapping)
    spec["layout"] = {"title": "Weighted"}
    spec["style"] = {"title_font_weight": "normal"}
    fig = render(spec, df).figure
    titles = [t for t in fig.findobj(matplotlib.text.Text) if t.get_text() == "Weighted"]
    assert titles and all(str(t.get_fontweight()) in ("normal", "400") for t in titles)
    plt.close(fig)


def test_forest_log_axis_ticks_are_plain_numbers():
    df = pd.DataFrame({"label": list("abcdef"), "est": [0.7, 0.9, 1.2, 1.5, 2.0, 2.6],
                       "lo": [0.5, 0.7, 0.9, 1.1, 1.5, 1.9], "hi": [1.0, 1.2, 1.6, 2.1, 2.7, 3.5]})
    spec = make_spec("forest_plot", "t.csv", "publication",
                     mapping={"label": "label", "estimate": "est", "lower": "lo", "upper": "hi", "log_scale": True})
    fig = render(spec, df).figure; fig.canvas.draw()
    ax = fig.axes[0]
    assert ax.get_xscale() == "log"
    labels = [t.get_text() for t in ax.get_xticklabels() if t.get_text()]
    assert labels and all("10^" not in s and "$" not in s for s in labels)
    plt.close(fig)


def test_pca_legend_uses_style_legend_size():
    df = pd.DataFrame(rng.normal(size=(30, 6)), columns=[f"s{i}" for i in range(6)]); df.insert(0, "gene", [f"g{i}" for i in range(30)])
    meta = pd.DataFrame({"sample_id": [f"s{i}" for i in range(6)], "group": ["x", "x", "x", "y", "y", "y"]})
    spec = make_spec("pca_scatter_from_matrix", "t.csv", "publication", mapping={"row_id": "gene", "color": "group"})
    spec["style"] = {"legend_pt": 5.0}
    res = render(spec, df, aux={"metadata": meta})
    leg = res.figure.axes[0].get_legend()
    assert leg is not None and all(abs(t.get_fontsize() - 5.0) < 1e-6 for t in leg.get_texts())
    plt.close("all")


def test_survival_annotation_location_is_configurable():
    df = pd.DataFrame({"t": rng.integers(1, 40, 40), "e": rng.integers(0, 2, 40), "g": ["a", "b"] * 20})
    spec = make_spec("kaplan_meier_survival_curve", "t.csv", "publication", mapping={"time": "t", "event": "e", "group": "g"})
    spec["statistics"] = {"enabled": True, "test": "logrank", "annotation": {"location": "center right"}}
    fig = render(spec, df).figure
    texts = [t for t in fig.axes[0].texts if "Log-rank" in t.get_text() or "log-rank" in t.get_text().lower()]
    assert texts and texts[0].get_position()[0] > 0.9 and abs(texts[0].get_position()[1] - 0.5) < 1e-6
    plt.close(fig)
