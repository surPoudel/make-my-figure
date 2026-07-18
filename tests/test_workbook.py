"""Tests for the shared multi-sheet Excel workbook layer (io/workbook.py).

Covers sheet listing/order, universal selectability (documentation/empty/hidden),
Unicode + odd headers, advisory classification, full load + provenance, output-name
sanitization/uniqueness, and cache-key behavior. GUI wiring is tested separately
(test_ui_consistency / controller tests) because Qt/Streamlit can't run headless.
"""

from __future__ import annotations

import io
import os

import pandas as pd
import pytest

from make_my_figure_core.io import workbook as wb
from make_my_figure_core.io.loaders import LoaderError

FIXTURE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "examples", "multi_sheet_workbook", "synthetic_multisheet.xlsx",
)

EXPECTED_ORDER = [
    "README", "DE_sheet_legend", "Comparison_A", "Comparison_B",
    "Matrix", "Metadata", "EmptySheet", "OddHeaders", "Résumé_βγ",
]


@pytest.fixture(scope="module")
def workbook_info():
    assert os.path.exists(FIXTURE), (
        "run scripts/generate_multi_sheet_fixture.py to build the test workbook"
    )
    return wb.inspect_excel_workbook(FIXTURE)


@pytest.fixture(scope="module")
def workbook_bytes():
    with open(FIXTURE, "rb") as fh:
        return fh.read()


# --- listing / order -------------------------------------------------------- #
def test_sheet_names_listed_in_workbook_order(workbook_info):
    assert workbook_info.sheet_names == EXPECTED_ORDER
    # list_excel_sheets is the same order.
    assert wb.list_excel_sheets(FIXTURE) == EXPECTED_ORDER


def test_every_worksheet_is_selectable(workbook_info):
    for name in workbook_info.sheet_names:
        prev = wb.preview_excel_sheet(workbook_info, name)
        assert prev.selectable is True


def test_documentation_sheet_selectable_and_classified(workbook_info):
    prev = wb.preview_excel_sheet(workbook_info, "README")
    assert prev.selectable is True
    assert prev.inferred_type == wb.SHEET_TYPE_DOCUMENTATION
    assert "documentation" in prev.type_message.lower()


def test_empty_sheet_selectable_but_marked_empty(workbook_info):
    prev = wb.preview_excel_sheet(workbook_info, "EmptySheet")
    assert prev.selectable is True
    assert prev.is_empty is True
    assert prev.inferred_type == wb.SHEET_TYPE_EMPTY
    assert any("empty" in w.lower() for w in prev.warnings)


def test_hidden_sheet_detected_but_not_omitted(workbook_info):
    # DE_sheet_legend was marked hidden in the fixture.
    assert "DE_sheet_legend" in workbook_info.hidden_sheets
    assert "DE_sheet_legend" in workbook_info.sheet_names  # still listed
    prev = wb.preview_excel_sheet(workbook_info, "DE_sheet_legend")
    assert prev.is_hidden is True
    assert prev.selectable is True


def test_unicode_sheet_name(workbook_info):
    assert "Résumé_βγ" in workbook_info.sheet_names
    prev = wb.preview_excel_sheet(workbook_info, "Résumé_βγ")
    assert prev.column_count == 5


# --- classification is advisory -------------------------------------------- #
def test_differential_sheet_detected(workbook_info):
    for name in ("Comparison_A", "Comparison_B"):
        prev = wb.preview_excel_sheet(workbook_info, name)
        assert prev.inferred_type == wb.SHEET_TYPE_DIFFERENTIAL


def test_matrix_sheet_detected(workbook_info):
    prev = wb.preview_excel_sheet(workbook_info, "Matrix")
    assert prev.inferred_type == wb.SHEET_TYPE_MATRIX


def test_metadata_sheet_detected(workbook_info):
    prev = wb.preview_excel_sheet(workbook_info, "Metadata")
    assert prev.inferred_type == wb.SHEET_TYPE_METADATA


def test_documentation_sheet_gets_no_de_recommendation(workbook_info):
    # A notes sheet must not be misread as differential results.
    prev = wb.preview_excel_sheet(workbook_info, "README")
    assert prev.inferred_type != wb.SHEET_TYPE_DIFFERENTIAL
    assert prev.inferred_type != wb.SHEET_TYPE_MATRIX


def test_classification_never_blocks_selection(workbook_info):
    # Even an unknown/odd sheet stays selectable.
    prev = wb.preview_excel_sheet(workbook_info, "OddHeaders")
    assert prev.selectable is True


# --- header handling -------------------------------------------------------- #
def test_odd_headers_with_explicit_header_row(workbook_info):
    prev = wb.preview_excel_sheet(workbook_info, "OddHeaders", header=2)
    assert prev.headers == ["sample", "value", "group"]


def test_no_header_read_gives_positional_columns(workbook_info):
    prev = wb.preview_excel_sheet(workbook_info, "OddHeaders", header=None)
    assert list(prev.preview.columns) == ["column_1", "column_2", "column_3"]


# --- full load + provenance ------------------------------------------------- #
def test_selected_sheet_loads_correct_data(workbook_info):
    a = wb.load_excel_sheet(workbook_info, "Comparison_A")
    b = wb.load_excel_sheet(workbook_info, "Comparison_B")
    assert list(a.columns) == ["feature_id", "log2FoldChange", "pvalue", "padj", "baseMean"]
    assert list(b.columns) == ["gene", "logFC", "P.Value", "adj.P.Val", "AveExpr"]
    assert a.n_rows == 40 and b.n_rows == 35


def test_load_records_worksheet_provenance(workbook_info):
    t = wb.load_excel_sheet(workbook_info, "Comparison_A")
    prov = t.provenance()
    assert prov["source_workbook_name"] == "synthetic_multisheet.xlsx"
    assert prov["source_sheet_name"] == "Comparison_A"
    assert prov["source_sheet_index"] == 2
    assert prov["source_sheet_type"] == wb.SHEET_TYPE_DIFFERENTIAL
    assert prov["source_workbook_hash"]


def test_empty_sheet_full_load_raises(workbook_info):
    with pytest.raises(LoaderError):
        wb.load_excel_sheet(workbook_info, "EmptySheet")


def test_switching_sheets_without_source_uses_cache(workbook_bytes):
    # Inspect from bytes, then load different sheets without re-passing source.
    info = wb.inspect_excel_workbook(workbook_bytes, source_name="wb.xlsx")
    t1 = wb.load_excel_sheet(info, "Comparison_A")
    t2 = wb.load_excel_sheet(info, "Matrix")
    assert t1.source_sheet_name == "Comparison_A"
    assert t2.source_sheet_name == "Matrix"


# --- caching keys ----------------------------------------------------------- #
def test_cache_key_differs_by_sheet(workbook_info):
    a = wb.preview_excel_sheet(workbook_info, "Comparison_A")
    b = wb.preview_excel_sheet(workbook_info, "Comparison_B")
    assert a.sheet_name != b.sheet_name
    assert a.inferred_type == b.inferred_type  # both DE, but distinct entries
    key_a = (workbook_info.file_hash, "Comparison_A", 0, 50)
    key_b = (workbook_info.file_hash, "Comparison_B", 0, 50)
    assert key_a in wb._PREVIEW_CACHE and key_b in wb._PREVIEW_CACHE


def test_file_hash_stable_and_content_based(workbook_bytes):
    h1 = wb.compute_file_hash(workbook_bytes)
    h2 = wb.compute_file_hash(workbook_bytes)
    h3 = wb.compute_file_hash(workbook_bytes + b"x")
    assert h1 == h2 and h1 != h3


# --- output naming ---------------------------------------------------------- #
def test_sanitize_removes_invalid_path_chars():
    assert wb.sanitize_sheet_name_for_path('Sol 24M/vs:6M*') == "Sol_24M_vs_6M"
    assert "/" not in wb.sanitize_sheet_name_for_path("a/b\\c")
    assert wb.sanitize_sheet_name_for_path("   ...  ") == "sheet"


def test_sanitize_avoids_windows_reserved_names():
    assert wb.sanitize_sheet_name_for_path("CON").lower().startswith("con_")
    assert wb.sanitize_sheet_name_for_path("lpt1") != "lpt1"


def test_sanitize_preserves_unicode_readability():
    out = wb.sanitize_sheet_name_for_path("Résumé βγ")
    assert out.startswith("Résumé")
    assert " " not in out


def test_output_slug_uniqueness_prevents_overwrite():
    used = set()
    s1 = wb.make_sheet_output_slug("wb.xlsx", "A/B", existing=used)
    s2 = wb.make_sheet_output_slug("wb.xlsx", "A:B", existing=used)  # sanitizes same
    assert s1 != s2  # different sheets never collide
    assert s1 == "A_B" and s2 == "A_B_2"


def test_output_basename_includes_sheet_and_plot():
    assert wb.output_basename("Aging.xlsx", "Sol_24M_vs_6M", "volcano") == \
        "Sol_24M_vs_6M_volcano"
    # Falls back to workbook stem when no sheet (CSV/single-table).
    assert wb.output_basename("data.csv", None, "bar") == "data_bar"


def test_sheet_output_dir_two_levels():
    d = wb.sheet_output_dir("Aging.xlsx", "Sol 24M")
    assert d == os.path.join("Aging", "Sol_24M")


# --- error handling --------------------------------------------------------- #
def test_corrupt_workbook_raises_clear_error():
    with pytest.raises(LoaderError):
        wb.inspect_excel_workbook(b"not a real xlsx", source_name="bad.xlsx")


def test_missing_sheet_raises(workbook_info):
    with pytest.raises(LoaderError):
        wb.load_excel_sheet(workbook_info, "NoSuchSheet")


def test_classify_handles_empty_frame():
    kind, _ = wb.classify_worksheet(pd.DataFrame())
    assert kind == wb.SHEET_TYPE_EMPTY
