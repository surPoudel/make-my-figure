"""Re-placing a legend via layout['legend_location'] must keep the profile's legend font sizes."""
import matplotlib
matplotlib.use("Agg")
import pandas as pd
import pytest

from make_my_figure_core.plots.registry import make_spec, render


@pytest.mark.parametrize("location", ["upper left", "outside right", "outside bottom"])
def test_legend_font_sizes_follow_profile_tokens(location):
    df = pd.DataFrame({"g": ["a", "b"] * 4, "v": range(8), "c": ["x", "x", "y", "y"] * 2})
    spec = make_spec("dot_strip_plot", "t.csv", "publication", mapping={"x": "g", "y": "v", "color": "c", "summary": "none"})
    spec["style"] = {"legend_pt": 5.5, "legend_title_pt": 6.5}
    spec["layout"] = {"legend_location": location}
    leg = render(spec, df).figure.axes[0].get_legend()
    assert leg is not None
    assert leg.get_texts()[0].get_fontsize() == pytest.approx(5.5)
    assert leg.get_title().get_fontsize() == pytest.approx(6.5)
