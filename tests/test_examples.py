"""Tests for the per-plot example/template data system (examples/)."""

import json
import os
import sys

import matplotlib
import matplotlib.pyplot as plt
import pytest

matplotlib.use("Agg")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from make_my_figure_core import examples
from make_my_figure_core.io.loaders import load_table
from make_my_figure_core.plots.registry import (
    available_plot_types,
    render,
    render_to_files,
)
from make_my_figure_core.spec.validate import validate_plot_spec
from make_my_figure_core.styles.engine import list_profiles

REQUIRED_MANIFEST_KEYS = {
    "plot_type", "name", "description", "use_case", "required_columns",
    "optional_columns", "files", "recommended_style_profiles",
    "compatible_renderers", "expected_export_formats", "data_type", "source",
    "license", "user_replacement_note",
}

EXPECTED_SHEETS = {  # combined workbook sheet names
    "Bar_error", "Grouped_bar", "Box_violin", "Scatter", "Line_timecourse",
    "Heatmap", "Volcano", "Enrichment_dot", "Kaplan_Meier", "Stacked_composition",
    "Waterfall", "PCA", "Oncoprint", "Lollipop", "ROC", "Forest", "Ridgeline",
}

_ENTRIES = examples.load_manifest()["plot_types"] if examples.has_manifest() else []
_IDS = [e["plot_type"] for e in _ENTRIES]


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


def test_manifest_present():
    assert examples.has_manifest(), "run scripts/generate_example_data.py"


def test_every_supported_plot_type_has_example():
    covered = set(examples.plot_types_with_examples())
    missing = set(available_plot_types()) - covered
    assert not missing, f"plot types without example data: {missing}"


def test_manifest_is_all_synthetic_cc0():
    man = examples.load_manifest()
    assert man["data_type"] == "synthetic"
    for e in man["plot_types"]:
        assert e["data_type"] == "synthetic"
        assert e["license"].startswith("CC0")


@pytest.mark.parametrize("entry", _ENTRIES, ids=_IDS)
def test_manifest_entry_complete(entry):
    assert REQUIRED_MANIFEST_KEYS <= set(entry), \
        f"missing keys: {REQUIRED_MANIFEST_KEYS - set(entry)}"


@pytest.mark.parametrize("entry", _ENTRIES, ids=_IDS)
def test_all_formats_exist_and_load(entry):
    for ext in ("csv", "tsv", "xlsx"):
        path = os.path.join(_ROOT, entry["files"][ext])
        assert os.path.exists(path), f"missing {path}"
        info = load_table(path)
        assert info.n_rows > 0 and len(info.columns) > 0


@pytest.mark.parametrize("entry", _ENTRIES, ids=_IDS)
def test_required_columns_present(entry):
    info = load_table(os.path.join(_ROOT, entry["files"]["csv"]))
    for col in entry["required_columns"]:
        if "<" in col:   # placeholder like "<sample columns>"
            continue
        assert col in info.columns, f"{entry['plot_type']} missing column {col}"


@pytest.mark.parametrize("entry", _ENTRIES, ids=_IDS)
def test_plotspec_validates(entry):
    with open(os.path.join(_ROOT, entry["files"]["plotspec"])) as fh:
        spec = json.load(fh)
    validate_plot_spec(spec, known_plot_types=available_plot_types(),
                       known_styles=list_profiles())


@pytest.mark.parametrize("entry", _ENTRIES, ids=_IDS)
def test_example_renders(entry):
    info, aux, spec = examples.load_example(entry["plot_type"])
    aux_dfs = {k: v.dataframe for k, v in aux.items()} or None
    result = render(spec, info.dataframe, aux=aux_dfs)
    assert result.figure is not None
    plt.close(result.figure)


@pytest.mark.parametrize("entry", _ENTRIES, ids=_IDS)
def test_example_exports_all_formats(entry, tmp_path):
    info, aux, spec = examples.load_example(entry["plot_type"])
    aux_dfs = {k: v.dataframe for k, v in aux.items()} or None
    base = str(tmp_path / entry["slug"])
    out = render_to_files(spec, info.dataframe, base, formats=["svg", "png", "pdf"], aux=aux_dfs)
    assert len(out["files"]) == 3
    for f in out["files"]:
        assert os.path.getsize(f) > 200
    assert os.path.exists(out["sidecar"])  # PlotSpec JSON sidecar


def test_combined_workbook_has_all_sheets():
    import openpyxl

    path = os.path.join(_ROOT, "examples", "Make_My_Figure_All_Example_Data.xlsx")
    assert os.path.exists(path)
    wb = openpyxl.load_workbook(path, read_only=True)
    sheets = set(wb.sheetnames)
    wb.close()
    assert EXPECTED_SHEETS <= sheets, f"missing sheets: {EXPECTED_SHEETS - sheets}"
    for s in sheets:
        assert len(s) <= 31, f"sheet name too long for Excel: {s}"


def test_readme_per_plot_exists():
    for e in _ENTRIES:
        assert os.path.exists(os.path.join(_ROOT, e["files"]["readme"]))
