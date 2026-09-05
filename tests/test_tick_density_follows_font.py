"""Automatic tick density must follow the style's tick font even when the figure is drawn
outside the style context (as the Figure Builder does when it rasterises a panel)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from make_my_figure_core.plots.registry import make_spec, render
from make_my_figure_core.styles.engine import load_profile


def _survival_table():
    rng = np.random.default_rng(0)
    return pd.DataFrame({"time": rng.integers(10, 3000, 60), "event": rng.integers(0, 2, 60),
                         "group": ["a", "b"] * 30})


def test_axis_tick_label_size_matches_style_token():
    spec = make_spec("kaplan_meier_survival_curve", "s.csv", "publication",
                     mapping={"time": "time", "event": "event", "group": "group"})
    spec["style"] = {"tick_label_pt": 20.0}
    result = render(spec, _survival_table())
    ax = result.figure.axes[0]
    # The size matplotlib's locator will use at draw time (outside any rc context).
    assert ax.xaxis._get_tick_label_size("x") == 20.0
    plt.close(result.figure)


def test_large_tick_font_yields_fewer_ticks_when_drawn_outside_style_context():
    def n_xticks(pt):
        spec = make_spec("kaplan_meier_survival_curve", "s.csv", "publication",
                         mapping={"time": "time", "event": "event", "group": "group"})
        spec["style"] = {"tick_label_pt": pt}
        fig = render(spec, _survival_table()).figure
        fig.canvas.draw()                      # plain draw: rcParams are the defaults here
        n = len([t for t in fig.axes[0].get_xticks() if fig.axes[0].get_xlim()[0] <= t <= fig.axes[0].get_xlim()[1]])
        plt.close(fig)
        return n
    assert n_xticks(24.0) < n_xticks(8.0)


def test_rotated_multiline_tick_labels_are_joined_on_one_line():
    """Two-line category labels rotated by autorotate_xticklabels must become single-line
    (rotated line breaks draw as parallel strips that collide with neighbouring labels)."""
    from make_my_figure_core.plots.base import autorotate_xticklabels

    fig, ax = plt.subplots()
    ax.set_xticks(range(3))
    ax.set_xticklabels(["WT\nU", "pum1\u0394\nB", "plain"])
    autorotate_xticklabels(ax, None, rotation=65)
    assert [t.get_text() for t in ax.get_xticklabels()] == ["WT U", "pum1\u0394 B", "plain"]
    # horizontal labels keep their line breaks
    ax.set_xticklabels(["WT\nU", "a", "b"])
    autorotate_xticklabels(ax, None, rotation="horizontal")
    assert ax.get_xticklabels()[0].get_text() == "WT\nU"
    plt.close(fig)
