"""QC: categorical x-axis labels must not overlap, even with many long labels
(e.g. ~20 sample names). Auto-rotation in the renderers should keep the DEFAULT
plot readable without the user changing any option.
"""

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")

from make_my_figure_core.plots.registry import make_spec, render

# long, sample-name-like categories (like 3345023_..._DHP001) — the case that broke
_COLS = [f"3345{i:03d}_STRANDED_DHP{i + 1:03d}" for i in range(20)]


def _long_frame(n_per=10, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for c in _COLS:
        for _ in range(n_per):
            rows.append({"column": c, "value": float(rng.normal(5.0, 1.0))})
    return pd.DataFrame(rows)


def _xlabels_overlap(fig, ax, tol=1.0) -> bool:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = [t.get_window_extent(renderer) for t in ax.get_xticklabels() if t.get_text()]
    boxes.sort(key=lambda b: b.x0)
    for a, b in zip(boxes, boxes[1:]):
        if a.x1 > b.x0 + tol:      # right edge of one past the left edge of the next
            return True
    return False


@pytest.mark.parametrize("plot_type, extra", [
    ("boxplot_or_violin_with_points", {"kind": "box", "points": False}),
    ("boxplot_or_violin_with_points", {"kind": "violin", "points": False}),
    ("barplot_with_error_bar", {"error": "sd"}),
    ("dot_strip_plot", {}),
    ("beeswarm_plot", {}),
    ("raincloud_plot", {}),
])
def test_no_xlabel_overlap_with_20_long_labels(plot_type, extra):
    df = _long_frame()
    spec = make_spec(plot_type, "m.csv", "publication",
                     mapping={"x": "column", "y": "value", **extra})
    result = render(spec, df)
    ax = result.figure.axes[0]
    assert not _xlabels_overlap(result.figure, ax), (
        f"{plot_type}: x-axis labels overlap with 20 long labels")
    import matplotlib.pyplot as plt
    plt.close(result.figure)


def test_rotation_option_is_respected():
    df = _long_frame()
    spec = make_spec("boxplot_or_violin_with_points", "m.csv", "publication",
                     mapping={"x": "column", "y": "value", "kind": "box",
                              "points": False, "x_tick_rotation": "vertical"})
    result = render(spec, df)
    ax = result.figure.axes[0]
    angles = {round(t.get_rotation()) for t in ax.get_xticklabels() if t.get_text()}
    assert angles == {90}
    import matplotlib.pyplot as plt
    plt.close(result.figure)
