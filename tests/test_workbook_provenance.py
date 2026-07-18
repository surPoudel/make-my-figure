"""Worksheet-provenance persistence across PlotSpec, MatrixSpec, StatsSpec, Panel.

Verifies that a worksheet source travels from the workbook loader into every spec
and its exported sidecar, that it round-trips, and that legacy specs without any
provenance still load (backward compatibility).
"""

from __future__ import annotations

import pandas as pd
import pytest

from make_my_figure_core.plots.registry import make_spec, render
from make_my_figure_core.plots.base import base_metadata
from make_my_figure_core.spec.validate import validate_plot_spec, SpecValidationError
from make_my_figure_core.styles.engine import load_profile
from make_my_figure_core.matrix_workflow.matrix_spec import MatrixSpec
from make_my_figure_core.panels.models import Panel
from make_my_figure_core.panels.builder import panel_from_dict

SOURCE = {
    "source_workbook_name": "Aging_DE.xlsx",
    "source_workbook_hash": "abc123",
    "source_sheet_name": "Sol_24M_vs_6M",
    "source_sheet_index": 2,
    "source_sheet_type": "differential_results",
    "source_header_row": 0,
}


def test_make_spec_records_source():
    spec = make_spec("scatter", "Aging_DE.xlsx [Sol_24M_vs_6M]", "publication",
                     mapping={"x": "a", "y": "b"}, source=SOURCE)
    assert spec["source"]["source_sheet_name"] == "Sol_24M_vs_6M"
    assert spec["source"]["source_sheet_index"] == 2


def test_make_spec_mirrors_source_into_statistics():
    spec = make_spec("barplot", "wb [s]", "publication",
                     statistics={"enabled": True, "test": "welch"}, source=SOURCE)
    assert spec["statistics"]["source"]["source_sheet_name"] == "Sol_24M_vs_6M"


def test_spec_without_source_has_no_source_key():
    spec = make_spec("scatter", "data.csv", "publication", mapping={"x": "a", "y": "b"})
    assert "source" not in spec


def test_validate_accepts_source_block():
    spec = make_spec("scatter", "wb [s]", "publication",
                     mapping={"x": "a", "y": "b"}, source=SOURCE)
    validate_plot_spec(spec, known_plot_types=["scatter"], known_styles=["publication"])


def test_legacy_spec_without_source_still_validates():
    spec = {
        "plot_type": "scatter", "input_table": "old.csv",
        "mapping": {"x": "a", "y": "b"}, "journal_style": "publication",
        "output": {"formats": ["png"], "dpi": 300},
    }
    validate_plot_spec(spec, known_plot_types=["scatter"], known_styles=["publication"])


def test_render_metadata_carries_source():
    df = pd.DataFrame({"a": [1.0, 2, 3, 4], "b": [4.0, 5, 6, 7]})
    spec = make_spec("scatterplot_with_regression", "wb [s]", "publication",
                     mapping={"x": "a", "y": "b"}, source=SOURCE)
    result = render(spec, df)
    # base_metadata echoes source; registry stamps the full spec too.
    assert result.metadata["source"]["source_sheet_name"] == "Sol_24M_vs_6M"
    assert result.metadata["spec"]["source"]["source_sheet_name"] == "Sol_24M_vs_6M"


def test_base_metadata_without_source():
    df = pd.DataFrame({"a": [1, 2]})
    spec = {"plot_type": "scatter", "output": {}}
    meta = base_metadata(spec, load_profile("publication"), df, used_columns=["a"])
    assert "source" not in meta


def test_matrix_spec_round_trips_worksheet_provenance():
    ms = MatrixSpec(source_file="Aging_DE.xlsx [Matrix]",
                    source_workbook="Aging_DE.xlsx", source_sheet="Matrix",
                    source_sheet_index=4, value_columns=["s1", "s2"])
    d = ms.to_dict()
    assert d["source_sheet"] == "Matrix" and d["source_sheet_index"] == 4
    back = MatrixSpec.from_dict(d)
    assert back.source_sheet == "Matrix"
    assert back.source_workbook == "Aging_DE.xlsx"


def test_legacy_matrix_spec_without_source_fields_loads():
    back = MatrixSpec.from_dict({"source_file": "x.csv", "value_columns": ["a"]})
    assert back.source_sheet is None


def test_panel_records_and_round_trips_worksheet():
    p = Panel(label="A", source_name="Aging_DE.xlsx [Sol_24M_vs_6M]",
              source_workbook="Aging_DE.xlsx", source_sheet="Sol_24M_vs_6M",
              plot_spec=make_spec("scatter", "t", "publication",
                                  mapping={"x": "a", "y": "b"}, source=SOURCE))
    d = p.to_dict()
    assert d["source_sheet"] == "Sol_24M_vs_6M"
    back = panel_from_dict(d)
    assert back.source_sheet == "Sol_24M_vs_6M"
    assert back.source_workbook == "Aging_DE.xlsx"


def test_two_panels_same_workbook_different_sheets_distinguishable():
    p1 = Panel(source_workbook="wb.xlsx", source_sheet="A")
    p2 = Panel(source_workbook="wb.xlsx", source_sheet="B")
    assert p1.to_dict()["source_sheet"] != p2.to_dict()["source_sheet"]


def test_panel_derives_source_from_plot_spec_when_fields_blank():
    p = Panel(plot_spec=make_spec("scatter", "t", "publication",
                                  mapping={"x": "a", "y": "b"}, source=SOURCE))
    d = p.to_dict()
    assert d["source_sheet"] == "Sol_24M_vs_6M"
