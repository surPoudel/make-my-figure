"""Streamlit app smoke tests using AppTest.

These run the dashboard script in-process (no browser/server) and assert it
executes without raising for each plot type's bundled sample.
"""

import os

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_APP = os.path.join(_REPO_ROOT, "apps", "streamlit_app", "streamlit_app.py")


def test_app_runs_default_sample():
    at = AppTest.from_file(_APP, default_timeout=60).run()
    assert not at.exception
    # default flow uses a bundled sample, so a figure should render
    assert len(at.title) >= 1


def test_app_runs_each_sample_plot_type():
    from make_my_figure_core.plots.registry import available_plot_types

    at = AppTest.from_file(_APP, default_timeout=180).run()
    assert not at.exception
    # The first selectbox is the bundled-sample picker (keyed by plot type).
    sample_picker = at.selectbox[0]
    for pt in available_plot_types():
        sample_picker.set_value(pt)
        at.run()
        assert not at.exception, f"app raised for sample {pt}"
