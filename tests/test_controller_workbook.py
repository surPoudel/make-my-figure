"""GUI-free tests for the desktop controller's multi-sheet workbook flow.

These run without Qt (the controller holds no Qt state) and confirm the desktop
and Streamlit apps share the same workbook loader and that sheet selection drives
data, provenance, and spec building.
"""

from __future__ import annotations

import os

import pytest

from apps.desktop_app.controller import DesktopController

FIXTURE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "examples", "multi_sheet_workbook", "synthetic_multisheet.xlsx",
)


@pytest.fixture()
def controller():
    return DesktopController()


def test_is_excel_path(controller):
    assert controller.is_excel_path(FIXTURE)
    assert not controller.is_excel_path("data.csv")


def test_load_file_lists_all_sheets(controller):
    data = controller.load_file(FIXTURE)
    assert data.is_workbook
    assert data.workbook.n_sheets == 9
    # first sheet loaded for preview
    assert data.sheet_name == "README"


def test_switch_sheet_changes_data_and_provenance(controller):
    a = controller.load_file(FIXTURE, sheet_name="Comparison_A")
    b = controller.load_file(FIXTURE, sheet_name="Comparison_B")
    assert list(a.info.columns) != list(b.info.columns)
    assert a.source_provenance()["source_sheet_name"] == "Comparison_A"
    assert b.source_provenance()["source_sheet_name"] == "Comparison_B"


def test_build_spec_embeds_selected_sheet_provenance(controller):
    b = controller.load_file(FIXTURE, sheet_name="Comparison_B")
    spec = controller.build_spec(
        "volcano_plot", "publication", b.table_name,
        {"logfc": "logFC", "pvalue": "P.Value"},
        source=b.source_provenance(),
    )
    assert spec["source"]["source_sheet_name"] == "Comparison_B"
    assert spec["source"]["source_sheet_type"] == "differential_results"


def test_preview_sheet_via_controller_is_advisory(controller):
    data = controller.load_file(FIXTURE)
    prev = controller.preview_sheet(data.workbook, "README")
    assert prev.selectable  # documentation stays selectable
    prev_empty = controller.preview_sheet(data.workbook, "EmptySheet")
    assert prev_empty.is_empty and prev_empty.selectable


def test_metadata_file_sheets_lists_workbook(controller):
    sheets = controller.metadata_file_sheets(FIXTURE)
    assert "Metadata" in sheets
    assert controller.metadata_file_sheets("meta.csv") == []


def test_metadata_suggest_from_workbook_sheet(controller):
    spec, summary = controller.matrix_metadata_suggest_from_file(
        FIXTURE, ["ctrl_1", "ctrl_2", "treat_5", "treat_6"], sheet_name="Metadata")
    assert summary["n_matched"] >= 1
    assert summary["sample_column"] == "sample_id"
