"""Cross-platform UI consistency + responsive-layout guardrails.

Qt and Streamlit can't run in the headless test sandbox, so these verify the shared
UI contract and assert that the specific anti-patterns fixed in the cross-platform
audit stay fixed (deterministic placeholder default, no fixed-width clipping cap,
recommendation-card min height, resizable/capped preview columns). Source-level
checks — they prevent regression without needing a live GUI.
"""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
_MAIN = (ROOT / "apps" / "desktop_app" / "main.py").read_text(encoding="utf-8")
_RECS = (ROOT / "apps" / "desktop_app" / "recommendations_panel.py").read_text(encoding="utf-8")
_STREAM = (ROOT / "apps" / "streamlit_app" / "streamlit_app.py").read_text(encoding="utf-8")


# --- shared UI strings ------------------------------------------------------
def test_shared_ui_strings():
    from make_my_figure_core import ui_strings as s
    assert s.PLOT_TYPE_PLACEHOLDER.strip()
    assert s.STYLE_DISPLAY_NAME == "Publication"
    for name in ("PLOT_TYPE_PLACEHOLDER", "STYLE_DISPLAY_NAME", "ACTION_MATRIX_WORKFLOW",
                 "ACTION_DEFINE_GROUPS", "ACTION_HOME", "EMPTY_STATE_MESSAGE"):
        val = getattr(s, name).lower()
        assert not any(t in val for t in ("nature", "science", "cell-like", "journal"))
    assert s.ACTION_MATRIX_WORKFLOW == "Matrix workflow…"      # full label, not clipped


def test_both_frontends_use_shared_placeholder():
    assert "PLOT_TYPE_PLACEHOLDER" in _MAIN
    assert "PLOT_TYPE_PLACEHOLDER" in _STREAM


# --- deterministic default (no silent Bar) ----------------------------------
def test_streamlit_does_not_default_to_first_plot_on_upload():
    # The old anti-pattern: default_plot_type = available_plot_types()[0] on upload.
    assert "available_plot_types()[0]" not in _STREAM
    # Placeholder is prepended to the selectbox options and is the default.
    assert "[PLOT_TYPE_PLACEHOLDER] + list(available_plot_types())" in _STREAM


def test_streamlit_gates_render_on_placeholder():
    assert "if plot_type == PLOT_TYPE_PLACEHOLDER" in _STREAM
    assert "st.stop()" in _STREAM


def test_desktop_resets_to_placeholder_on_upload():
    # load path sets the combo to index 0 (the placeholder) on every upload.
    assert "self.plot_combo.setCurrentIndex(0)" in _MAIN


# --- responsive layout anti-patterns fixed ----------------------------------
def test_desktop_controls_pane_has_no_fixed_max_width_cap():
    # The 480px cap clipped wide controls / the "Matrix workflow…" button.
    assert "setMaximumWidth(480)" not in _MAIN


def test_desktop_nav_is_stacked_not_clipping_row():
    # Nav buttons stacked vertically so full labels show at any width/DPI.
    assert "nav_row = QVBoxLayout()" in _MAIN
    assert 'QPushButton("\\U0001F9EE  Matrix workflow…")' in _MAIN  # full label present


def test_recommendation_scroll_has_min_height():
    assert "setMinimumHeight(240)" in _RECS


def test_preview_columns_capped_and_have_tooltips():
    assert "QHeaderView" in _MAIN
    assert "setColumnWidth" in _MAIN
    assert ".setToolTip(str(colname))" in _MAIN


def test_splitter_state_is_validated():
    # Stale/degenerate persisted splitter sizes fall back to a proportional default.
    assert "left < 300" in _MAIN and "setSizes([400, 820])" in _MAIN


# --- no journal styles leaked into UI ---------------------------------------
def test_no_journal_style_labels_in_apps():
    import re
    for src in (_MAIN, _STREAM):
        for line in src.splitlines():
            low = line.strip().lower()
            if low.startswith("#") or low.startswith('"'):
                continue
            if re.search(r"(selectbox|addItem|combo)", line, re.I):
                assert not any(t in low for t in ("nature_like", "science_like", "cell_like"))
