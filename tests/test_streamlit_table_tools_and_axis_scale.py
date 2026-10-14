"""Browser app: recorded transformations, the design check and axis scale controls.

Runs the real Streamlit script with AppTest on the bundled box/violin sample.
"""
import os

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from make_my_figure_core.plots.registry import display_name  # noqa: E402

_APP = os.path.join(os.path.dirname(__file__), "..", "apps", "streamlit_app", "streamlit_app.py")


def _by_label(widgets, label):
    for w in widgets:
        if w.label == label:
            return w
    raise AssertionError(f"no widget {label!r}; have {[w.label for w in widgets]}")


def _app(plot_type="boxplot_or_violin_with_points"):
    at = AppTest.from_file(_APP, default_timeout=300).run()
    assert not at.exception
    _by_label(at.selectbox, "Example dataset (by plot type)").set_value(display_name(plot_type))
    at.run()
    assert not at.exception
    return at


def test_transform_adds_a_derived_column_and_keeps_the_original():
    at = _app()
    num_col = _by_label(at.selectbox, "Column").options[0]
    _by_label(at.selectbox, "Column").set_value(num_col)
    _by_label(at.selectbox, "Transformation").set_value("log10")
    at.run()
    _by_label(at.button, "Add this transformation").click()
    at.run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert f"log10({num_col})" in text
    downloads = [b.label for b in at.get("download_button")]
    assert "Download derived table (CSV)" in downloads and "Download transformation record (JSON)" in downloads
    assert "Figure Package" in downloads
    # the derived column is offered for mapping, and the original still is
    y = _by_label(at.sidebar.selectbox, "y")
    assert f"log10({num_col})" in y.options and num_col in y.options
    y.set_value(f"log10({num_col})")
    at.run()
    assert not at.exception and not any("Could not render" in e.value for e in at.error)


def test_log_axis_control_is_offered_and_applies_without_error():
    at = _app()
    labels = [w.label for w in at.sidebar.selectbox]
    assert "Y axis scale (display only)" in labels
    assert "X axis scale (display only)" not in labels        # categories on x
    _by_label(at.sidebar.selectbox, "Y axis scale (display only)").set_value("log10")
    _by_label(at.sidebar.selectbox, "Y tick labels").set_value("plain")
    at.run()
    assert not at.exception
    assert not any("Could not render" in e.value for e in at.error)


def test_axis_scale_control_is_absent_where_it_cannot_act():
    at = _app("volcano_plot")
    assert not any("axis scale" in w.label for w in at.sidebar.selectbox)


def test_design_check_explains_a_non_estimable_design():
    at = _app()
    factors = _by_label(at.multiselect, "Factors (up to 3)")
    first = factors.options[0]
    factors.set_value([first])
    at.run()
    _by_label(at.button, "Check design and run").click()
    at.run()
    assert not at.exception
    assert any("estimable" in t.value or "cannot be estimated" in t.value for t in at.text)
