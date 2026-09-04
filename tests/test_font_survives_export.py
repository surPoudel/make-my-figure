"""The profile's font stack must be applied at export time, not only while rendering."""
import io

import matplotlib
matplotlib.use("Agg")
import pandas as pd
import pytest

from make_my_figure_core.plots.registry import figure_to_bytes, make_spec, render

fitz = pytest.importorskip("fitz")


def test_requested_font_is_embedded_in_pdf_saved_outside_style_context():
    df = pd.DataFrame({"g": ["a", "b", "a", "b"], "v": [1.0, 2.0, 3.0, 4.0]})
    spec = make_spec("dot_strip_plot", "t.csv", "publication", mapping={"x": "g", "y": "v", "summary": "none"})
    spec["style"] = {"font_family": "DejaVu Sans Mono"}   # ships with matplotlib on every platform
    res = render(spec, df)
    pdf = figure_to_bytes(res.figure, "pdf")               # saved outside style.apply()
    fonts = {f[3] for f in fitz.open(stream=pdf, filetype="pdf")[0].get_fonts()}
    assert any("DejaVuSansMono" in f for f in fonts), fonts
