"""A style Figure Preset must transfer its palette (in order) and marker/line/typography settings to a
compatible plot on a different table with different category names (manuscript Figure 4, panel C audit)."""
import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd
from matplotlib.colors import to_rgb

from make_my_figure_core.plots.registry import make_spec, render
from make_my_figure_core.presets import apply_preset, extract_preset, preset_contains_data

PALETTE = ["#005A9C", "#B84A00", "#007A5C", "#8E3B7A", "#9C6F00"]


def _scatter_spec(table, x, y, color):
    return make_spec("scatterplot_with_regression", table, "publication",
                     mapping={"x": x, "y": y, "color": color, "fit_line": True, "show_fit_stats": False},
                     layout={"title": table, "legend_location": "lower right"})


def _observe(spec, df):
    r = render(spec, df); ax = r.figure.axes[0]; r.figure.canvas.draw()
    colls = [c for c in ax.collections if len(c.get_offsets())]
    out = {"colours": [tuple(np.round(c.get_facecolor()[0][:3], 4)) for c in colls],
           "size": float(colls[0].get_sizes()[0]), "edge": float(colls[0].get_linewidths()[0]),
           "lw": float(ax.lines[0].get_linewidth()), "tick_pt": float(ax.get_xticklabels()[0].get_fontsize()),
           "legend": [t.get_text() for t in ax.get_legend().get_texts()], "title": ax.get_title()}
    matplotlib.pyplot.close(r.figure); return out


def test_style_preset_transfers_palette_order_to_new_categories():
    rng = np.random.default_rng(0)
    a = pd.DataFrame({"x": rng.normal(size=60), "y": rng.normal(size=60), "g": np.repeat(["A", "B", "C"], 20)})
    b = pd.DataFrame({"u": rng.normal(size=100), "v": rng.normal(size=100), "k": np.repeat(["X", "Y", "Z", "W", "V"], 20)})
    spec_a = _scatter_spec("a.csv", "x", "y", "g")
    spec_a["style"] = {"palette": PALETTE, "marker_size": 40.0, "marker_edge_width": 0.4, "line_width_pt": 1.8, "tick_label_pt": 12.0}
    preset = extract_preset(spec_a, mode="style", name="t")
    assert preset_contains_data(preset) == []
    res = apply_preset(preset, _scatter_spec("b.csv", "u", "v", "k"), columns=b.columns)
    oa, ob = _observe(spec_a, a), _observe(res.spec, b)
    # palette order is transferred: the k-th category of the receiving table takes the k-th palette colour
    assert ob["colours"] == [tuple(np.round(to_rgb(c), 4)) for c in PALETTE[:5]]
    assert oa["colours"] == ob["colours"][:3]
    assert (ob["size"], ob["edge"], ob["lw"], ob["tick_pt"]) == (40.0, 0.4, 1.8, 12.0)
    # the receiving plot keeps its own categories and title
    assert ob["legend"] == ["X", "Y", "Z", "W", "V"] and ob["title"] == "b.csv"
    assert "mapping_roles" not in preset and "input_table" not in preset
