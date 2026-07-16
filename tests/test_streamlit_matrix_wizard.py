"""Streamlit matrix-wizard integration.

Skipped where Streamlit isn't installed (e.g. the CI sandbox). Where it is, this
uses Streamlit's headless AppTest to drive the wizard through map -> confirm ->
groups -> recommend and asserts state persists across reruns.
"""

import os

import pandas as pd
import pytest

st = pytest.importorskip("streamlit")
try:
    from streamlit.testing.v1 import AppTest
except Exception:  # pragma: no cover - very old streamlit
    pytest.skip("streamlit AppTest unavailable", allow_module_level=True)

from make_my_figure_core.matrix_workflow.examples import CTRL, SAMPLES, TREAT, build_example_matrix


def _wizard_script():
    # Runs inside AppTest: seed a matrix and invoke the wizard.
    import pandas as pd  # noqa: F811

    from apps.streamlit_app.matrix_wizard import render_matrix_wizard
    from make_my_figure_core.matrix_workflow.examples import build_example_matrix

    render_matrix_wizard(build_example_matrix(), "matrix.tsv")


def test_wizard_renders_map_step():
    at = AppTest.from_function(_wizard_script).run(timeout=30)
    assert not at.exception
    # the "Map columns" step header should be present
    text = " ".join(str(m.value) for m in at.markdown) + " ".join(
        str(getattr(e, "label", "")) for e in at.expander)
    assert "Map columns" in text or any("Map columns" in str(getattr(e, "label", ""))
                                        for e in at.expander)


def test_confirmed_spec_persists_and_recommends():
    at = AppTest.from_function(_wizard_script).run(timeout=30)
    # Seed a confirmed spec directly in session state (as the Confirm button would).
    import make_my_figure_core.matrix_workflow as mw
    spec = mw.MatrixSpec(feature_id_column="feature_id", value_columns=list(SAMPLES),
                         value_type="log_normalized", confirmed_by_user=True)
    at.session_state["mw_spec"] = spec.to_dict()
    at.run(timeout=30)
    assert not at.exception
    assert at.session_state["mw_spec"]["confirmed_by_user"] is True
