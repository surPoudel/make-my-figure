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
_SAMPLE_PICKER_LABEL = "Example dataset (by plot type)"


def test_app_runs_default_sample():
    at = AppTest.from_file(_APP, default_timeout=60).run()
    assert not at.exception
    # default flow uses a bundled sample, so a figure should render
    assert len(at.title) >= 1


def _sample_picker(at):
    """The bundled-sample selectbox, found by label rather than position.

    Indexing into ``at.selectbox`` broke silently: the matrix wizard added selectboxes
    ahead of this one, so ``[0]`` became "Feature id column" and every plot type was
    "selected" into the wrong widget. Matching the label keeps the test pinned to the
    widget it means to drive.
    """
    for box in at.selectbox:
        if box.label == _SAMPLE_PICKER_LABEL:
            return box
    raise AssertionError(
        f"no selectbox labelled {_SAMPLE_PICKER_LABEL!r}; found "
        f"{[b.label for b in at.selectbox]}")


def test_app_runs_each_sample_plot_type():
    from make_my_figure_core.plots.registry import available_plot_types, display_name

    at = AppTest.from_file(_APP, default_timeout=300).run()
    assert not at.exception
    picker = _sample_picker(at)
    # The widget offers display names, not plot-type keys, so select through display_name.
    offered = set(picker.options)
    for pt in available_plot_types():
        label = display_name(pt)
        assert label in offered, f"{pt} has no entry in the example picker"
        _sample_picker(at).set_value(label)
        at.run()
        assert not at.exception, f"app raised for sample {pt} ({label})"
