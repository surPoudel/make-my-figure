"""Source-level guardrails for the multi-sheet workbook browser in both frontends.

Qt and Streamlit cannot run in the headless sandbox, so these assert that the
worksheet-browser contract stays wired in both apps: a shared workbook loader, a
persistent sheet dropdown listing every sheet, stale-state clearing on switch,
empty-sheet handling, and sheet-aware export names.
"""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
_MAIN = (ROOT / "apps" / "desktop_app" / "main.py").read_text(encoding="utf-8")
_STREAM = (ROOT / "apps" / "streamlit_app" / "streamlit_app.py").read_text(encoding="utf-8")
_CTRL = (ROOT / "apps" / "desktop_app" / "controller.py").read_text(encoding="utf-8")


def test_both_frontends_import_shared_workbook_loader():
    for src in (_MAIN, _STREAM, _CTRL):
        assert "from make_my_figure_core.io import workbook as workbook_io" in src


def test_streamlit_lists_all_sheets_in_a_persistent_dropdown():
    # selectbox over wbk.sheet_names with a stable session key.
    assert "options=wbk.sheet_names" in _STREAM
    assert 'key="_wb_sheet"' in _STREAM


def test_streamlit_inspects_workbook_and_previews():
    assert "inspect_excel_workbook" in _STREAM
    assert "preview_excel_sheet" in _STREAM
    assert "load_excel_sheet" in _STREAM


def test_streamlit_clears_stale_state_on_switch():
    assert "_clear_sheet_dependent_state" in _STREAM
    assert '_wb_active_sheet' in _STREAM


def test_streamlit_empty_sheet_disables_plotting():
    assert "prev.is_empty" in _STREAM
    # An empty sheet stops before rendering.
    assert "Plotting is disabled" in _STREAM


def test_streamlit_export_names_are_sheet_aware():
    assert "workbook_io.output_basename" in _STREAM


def test_streamlit_passes_source_provenance_to_make_spec():
    assert "source=_source_prov" in _STREAM


def test_desktop_has_worksheet_dropdown_over_all_sheets():
    assert "self.sheet_combo" in _MAIN
    assert "for name in wbk.sheet_names:" in _MAIN
    assert "self.sheet_combo.addItem(label, name)" in _MAIN


def test_desktop_switch_handler_reloads_and_clears():
    assert "_on_sheet_changed" in _MAIN
    assert "load_workbook_sheet" in _MAIN
    # Resets the plot type to placeholder on switch (clears stale plot/mapping).
    assert "self.plot_combo.setCurrentIndex(0)" in _MAIN


def test_desktop_empty_sheet_stays_selectable_without_crash():
    # LoaderError from an empty sheet is caught; plotting disabled, not a crash.
    assert "Plotting disabled" in _MAIN


def test_desktop_export_names_are_sheet_aware():
    assert "_export_basename" in _MAIN
    assert "workbook_io.output_basename" in _MAIN


def test_desktop_build_spec_includes_source_provenance():
    # Worksheet provenance still flows into the spec source (now merged with any
    # Matrix-Workflow handoff provenance).
    assert "self.data.source_provenance()" in _MAIN
    assert "source=source or None" in _MAIN


def test_desktop_status_bar_shows_workbook_and_worksheet():
    assert "_source_status" in _MAIN
    assert "Worksheet:" in _MAIN


def test_controller_exposes_workbook_api():
    for name in ("inspect_workbook", "load_workbook_sheet", "preview_sheet",
                 "is_excel_path", "metadata_file_sheets"):
        assert f"def {name}" in _CTRL


def test_no_journal_style_leaks_in_workbook_ui():
    for src in (_MAIN, _STREAM):
        for bad in ("nature_like", "science_like", "cell_like"):
            assert bad not in src
