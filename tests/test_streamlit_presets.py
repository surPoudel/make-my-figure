"""Figure presets through the browser app: save from one figure, apply to another, in-process.

Drives the real Streamlit script with AppTest (no browser, no server). The sequence is the one the
spec describes: configure a figure, save a style preset, move to a *different* dataset of the same
plot type, apply the preset, and see the same settings come back - while the new data stays the new
data. The preset library is pointed at a temporary folder so the test never touches a user's.
"""

from __future__ import annotations

import json
import os

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from make_my_figure_core import presets as P  # noqa: E402

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_APP = os.path.join(_ROOT, "apps", "streamlit_app", "streamlit_app.py")
_PICKER = "Example dataset (by plot type)"


def _run(timeout=240):
    at = AppTest.from_file(_APP, default_timeout=timeout).run()
    assert not at.exception
    return at


def _pick_sample(at, label):
    box = next(b for b in at.selectbox if b.label == _PICKER)
    box.set_value(label)
    at.run()
    assert not at.exception, at.exception
    return at


def test_save_then_apply_style_preset_on_new_data(tmp_path, monkeypatch):
    monkeypatch.setenv("MAKE_MY_FIGURE_PRESETS", str(tmp_path / "lib"))
    at = _run()
    _pick_sample(at, "Bar plot with error bars")

    # configure: fonts, palette, tick angle, legend, a visual plot option (bar fill) and an
    # analytical one (the error bar definition) - only the visual one belongs in a style preset
    at.session_state["sty_title_pt"] = 19
    at.session_state["sty_palette"] = "grayscale"
    at.session_state["lay_xrot"] = "45"
    at.session_state["lay_legloc"] = "outside right"
    at.session_state["opt_barplot_with_error_bar_bar_fill"] = "outline"
    at.session_state["opt_barplot_with_error_bar_error"] = "sd"
    at.run()
    assert not at.exception

    # save as a style preset (the form submit sets the request; the next run fulfils it)
    at.session_state["_preset_save_request"] = {"name": "Lab bars", "mode": "style"}
    at.run()
    assert not at.exception
    saved = P.PresetStore().list("barplot_with_error_bar")
    assert [e.name for e in saved] == ["Lab bars"]
    preset = P.load_preset(saved[0].path)
    assert preset["style"]["title_font_pt"] == 19
    assert preset["style"]["palette_name"] == "grayscale"
    assert preset["layout"]["x_tick_rotation"] == 45
    assert preset["layout"]["legend_location"] == "outside right"
    assert preset["options"]["bar_fill"] == "outline"
    assert "error" not in preset["options"]          # what the whisker means is config, not style
    assert P.preset_contains_data(preset) == []
    text = json.dumps(preset)
    assert "condition" not in text and "measurement" not in text     # no column names in style

    # a fresh session on a DIFFERENT bar-plot dataset with defaults everywhere
    at2 = _run()
    _pick_sample(at2, "Bar plot with error bars")
    assert at2.session_state["sty_title_pt"] == 14
    assert at2.session_state["lay_xrot"] == "auto"

    # apply through the sidebar control
    picker = next(b for b in at2.selectbox if b.label == "Figure preset")
    picker.set_value("Lab bars  [style]")
    at2.run()
    at2.button(key="preset_apply").click()
    at2.run()
    assert not at2.exception, at2.exception
    assert at2.session_state["sty_title_pt"] == 19
    assert at2.session_state["sty_palette"] == "grayscale"
    assert at2.session_state["lay_xrot"] == "45"
    assert at2.session_state["lay_legloc"] == "outside right"
    assert at2.session_state["opt_barplot_with_error_bar_bar_fill"] == "outline"
    assert at2.session_state["opt_barplot_with_error_bar_error"] == "sem"   # untouched default


def test_reset_returns_the_controls_to_publication_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("MAKE_MY_FIGURE_PRESETS", str(tmp_path / "lib"))
    at = _run()
    _pick_sample(at, "Bar plot with error bars")
    at.session_state["sty_title_pt"] = 22
    at.session_state["lay_xrot"] = "90"
    at.run()
    at.button(key="preset_reset").click()
    at.run()
    assert not at.exception
    assert at.session_state["sty_title_pt"] == 14
    assert at.session_state["lay_xrot"] == "auto"


def test_full_preset_reports_columns_the_new_table_lacks(tmp_path, monkeypatch):
    """Applying a full preset onto data without the saved columns must warn, never substitute."""
    monkeypatch.setenv("MAKE_MY_FIGURE_PRESETS", str(tmp_path / "lib"))
    # a full preset for the scatter plot with roles the mock-free bundled sample does not have
    from make_my_figure_core.plots.registry import make_spec
    spec = make_spec("scatterplot_with_regression", "elsewhere.csv", "publication",
                     mapping={"x": "dose_uM", "y": "viability", "color": "cell_line"})
    P.PresetStore().save(P.extract_preset(spec, mode="full", name="Other lab scatter"))

    at = _run()
    _pick_sample(at, "Scatter plot")
    picker = next(b for b in at.selectbox if b.label == "Figure preset")
    picker.set_value("Other lab scatter  [full]")
    at.run()
    at.button(key="preset_apply").click()
    at.run()
    assert not at.exception, at.exception
    warnings = " ".join(w.value for w in at.warning)
    assert "nothing was substituted" in warnings.lower()
    assert "dose_uM" in warnings
    # the sample's own columns were not overwritten by the foreign names
    for k in ("map_x", "map_y"):
        # AppTest exposes a SafeSessionState proxy without .get(); index it instead
        if k in at.session_state:
            assert at.session_state[k] not in ("dose_uM", "viability")


def test_imported_preset_appears_in_the_library(tmp_path, monkeypatch):
    monkeypatch.setenv("MAKE_MY_FIGURE_PRESETS", str(tmp_path / "lib"))
    from make_my_figure_core.plots.registry import make_spec
    spec = make_spec("volcano_plot", "x.csv", "publication")
    spec["style"] = {"marker_size": 30}
    path = P.save_preset(P.extract_preset(spec, mode="style", name="Shared volcano"),
                         str(tmp_path / "shared"))
    at = _run()
    _pick_sample(at, "Volcano plot")
    # AppTest cannot upload files; import through the store exactly as the uploader does
    P.PresetStore().save(P.load_preset_bytes(open(path, "rb").read(), name="Shared volcano"))
    at.run()
    picker = next(b for b in at.selectbox if b.label == "Figure preset")
    assert "Shared volcano  [style]" in picker.options
