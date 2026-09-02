"""Both frontends expose Figure presets through the one shared core - source-level guards.

Qt and Streamlit cannot run in the headless sandbox, so these checks read the frontend sources and
assert the contract: every preset action the spec asks for exists in both apps, both apps use
``make_my_figure_core.presets`` rather than a private re-implementation, the user-facing wording
is "Figure preset" (never "PlotSpec template"), and the desktop restores a spec into its controls
through a single path so "Open PlotSpec" and "Apply preset" cannot drift apart.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
_MAIN = (ROOT / "apps" / "desktop_app" / "main.py").read_text(encoding="utf-8")
_STATS = (ROOT / "apps" / "desktop_app" / "stats_panel.py").read_text(encoding="utf-8")
_STREAM = (ROOT / "apps" / "streamlit_app" / "streamlit_app.py").read_text(encoding="utf-8")


# --- one core, two frontends ----------------------------------------------------------------

def test_both_frontends_import_the_shared_preset_core():
    assert "make_my_figure_core.presets" in _MAIN
    assert "make_my_figure_core.presets" in _STREAM
    assert "make_my_figure_core.presets" in _STATS


def test_no_frontend_reimplements_preset_extraction():
    """Scope classification lives in the core only."""
    for src, name in ((_MAIN, "desktop"), (_STREAM, "streamlit")):
        assert "LAYOUT_STYLE_KEYS" not in src, f"{name} duplicates the core's scope tables"
        assert "def extract_preset" not in src, f"{name} re-implements extract_preset"
        assert "def apply_preset" not in src, f"{name} re-implements apply_preset"


# --- the controls the spec asks for --------------------------------------------------------------

def test_desktop_has_every_preset_action():
    for name in ("_build_preset_panel", "action_apply_preset", "action_save_preset",
                 "action_import_preset", "action_export_preset", "action_delete_preset",
                 "action_reset_style", "_refresh_preset_list"):
        assert f"def {name}(" in _MAIN, name
    # the panel is placed in the controls column and mirrored in the File menu
    assert "cv.addWidget(self._build_preset_panel())" in _MAIN
    assert 'filem.addMenu("Figure preset")' in _MAIN


def test_desktop_save_dialog_offers_both_modes():
    assert "Figure style only" in _MAIN
    assert "Full figure configuration" in _MAIN
    assert 'mode="style" if style_rb.isChecked() else "full"' in _MAIN


def test_desktop_restores_specs_through_one_path():
    """Open PlotSpec and Apply preset must share the widget-restore code."""
    assert "def _apply_spec_to_controls(" in _MAIN
    body = _MAIN[_MAIN.index("def _apply_plotspec_to_ui("):]
    body = body[:body.index("\n    def ", 10)]
    assert "self._apply_spec_to_controls(spec)" in body
    assert "self._apply_spec_to_controls(result.spec, keep_plot_type=True)" in _MAIN


def test_desktop_restore_covers_layout_colorbar_and_multi_column_roles():
    body = _MAIN[_MAIN.index("def _apply_spec_to_controls("):]
    body = body[:body.index("\n    def _build_style_panel(")]
    for token in ("cmb_xrot", "cmb_legloc", "sp_ml", "cmb_cbloc", "sp_cbshrink",
                  "_multi_col_widgets", "_value_cols_widget", "mmf_optional", "stats_panel.load_spec"):
        assert token in body, f"restore path does not cover {token}"


def test_desktop_reports_unresolved_roles_instead_of_guessing():
    assert "Nothing was substituted" in _MAIN
    assert "result.unresolved_roles" in _MAIN


def test_streamlit_has_every_preset_action():
    assert 'st.sidebar.expander("Figure preset"' in _STREAM
    for key in ("preset_apply", "preset_delete", "preset_export", "preset_import", "preset_reset",
                "preset_save_form"):
        assert key in _STREAM, key
    assert "Figure style only" in _STREAM and "Full figure configuration" in _STREAM


def test_streamlit_controls_are_keyed_so_a_preset_can_set_them():
    for key in ("sty_title_pt", "sty_palette", "sty_marker", "lay_xrot", "lay_legloc",
                "lay_width", "lay_dpi", "lab_title", "lay_cbloc"):
        assert f'key="{key}"' in _STREAM, key
    # hand-written per-plot option widgets carry the same key pattern as the generic renderer
    assert 'key=f"opt_{plot_type}_error"' in _STREAM
    assert 'key=f"opt_{plot_type}_kind"' in _STREAM


def test_streamlit_reports_unresolved_roles_instead_of_guessing():
    assert "nothing was" in _STREAM and "substituted" in _STREAM


# --- terminology -------------------------------------------------------------------------------

def test_user_facing_terminology_is_figure_preset():
    for src in (_MAIN, _STREAM):
        # widget labels / titles must say "Figure preset"; the phrase "PlotSpec template" never
        assert "PlotSpec template" not in src
    assert re.search(r'QGroupBox\("Figure preset"\)', _MAIN)
    assert 'expander("Figure preset"' in _STREAM


# --- Figure Builder ------------------------------------------------------------------------------

def test_figure_builder_has_flexible_sizing_controls():
    for name in ("rows_combo", "width_mm_spin", "wspace_spin", "hspace_spin", "label_style_combo",
                 "pw_spin", "ph_spin"):
        assert f"self.{name} = " in _STATS, name
    # and they feed the layout that is built
    body = _STATS[_STATS.index("def _make_layout("):]
    body = body[:body.index("\n    # --- layout presets")]
    for key in ("nrows=", "fig_width_mm=", "wspace=", "hspace=", "label_style="):
        assert key in body, key


def test_figure_builder_has_layout_preset_actions():
    for name in ("_apply_layout_preset", "_save_layout_preset", "_import_layout_preset",
                 "_export_layout_preset", "_delete_layout_preset", "_refresh_layout_presets"):
        assert f"def {name}(" in _STATS, name
    assert 'QGroupBox("Layout preset")' in _STATS
    # the user is told the difference between a layout preset and a saved figure
    assert "never contains the panels" in _STATS
