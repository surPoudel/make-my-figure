"""The Publication style's font stack must survive export (found while composing manuscript Figure 4).

Text created inside ``style.apply()`` used the generic family "sans-serif", which matplotlib resolves
through the global rcParams at draw/save time - after the rc_context has closed - so exported figures
came out in DejaVu Sans even when the first font of the stack was installed."""
import matplotlib
matplotlib.use("Agg")
import pandas as pd

from make_my_figure_core.plots.registry import make_spec, render
from make_my_figure_core.styles.engine import load_profile


def test_font_stack_is_kept_outside_the_style_context():
    # DejaVu Serif ships with matplotlib, so it is installed everywhere the tests run.
    style = load_profile("publication").with_overrides({"font_family": "DejaVu Serif"})
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [1.0, 2.5, 2.0, 4.0]})
    spec = make_spec("scatterplot_with_regression", "t.csv", "publication", mapping={"x": "x", "y": "y"},
                     layout={"title": "t"})
    res = render(spec, df, style=style)
    ax = res.figure.axes[0]
    res.figure.canvas.draw()                      # resolution happens here, outside style.apply()
    assert ax.title.get_fontname() == "DejaVu Serif"
    assert ax.get_xticklabels()[0].get_fontname() == "DejaVu Serif"


def test_composite_letters_use_the_publication_font_stack():
    """Figure Builder letters/titles are drawn on the composite figure and used matplotlib's default
    family (DejaVu Sans) instead of the Publication stack."""
    from make_my_figure_core.panels import FigureLayout, MultiPanelFigure, Panel, build_figure
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [1.0, 2.5, 2.0, 4.0]})
    spec = make_spec("scatterplot_with_regression", "t.csv", "publication", mapping={"x": "x", "y": "y"})
    mpf = MultiPanelFigure(name="t", panels=[Panel(plot_spec=spec, table=df, source_name="t.csv"),
                                             Panel(plot_spec=spec, table=df, source_name="t.csv")],
                           layout=FigureLayout(ncols=2))
    comp = build_figure(mpf)
    letters = [t for ax in comp.axes for t in ax.texts if t.get_text() in ("A", "B")]
    assert letters and all(list(t.get_fontfamily()) == list(load_profile("publication").font_family) for t in letters)
