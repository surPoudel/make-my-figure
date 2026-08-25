"""Header-row selection and merged / stacked spreadsheet headers.

Regression cover for collaborator concern C2. Three worksheets could not be brought into a
plottable shape at all. Two defects were behind it:

1. ``load_table`` accepted a ``header=`` argument, documented it, and never forwarded it to the
   readers, so choosing a header row - or "no header" - changed nothing. The loader's own warning
   tells the user to "confirm the header row", which was impossible to act on.
2. A group label merged across a block of replicate columns survived only on the first column of
   the block, because Excel stores a merged value once and pandas reports the rest as
   ``Unnamed: n``.

Every fixture here is written in-test with openpyxl. Nothing is copied from the collaborator's
workbook.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import pytest

from make_my_figure_core.io.loaders import LoaderError, load_table

openpyxl = pytest.importorskip("openpyxl")


# --------------------------------------------------------------------------------------
# fixtures: small workbooks that reproduce the awkward shapes
# --------------------------------------------------------------------------------------

def _merged_group_header(path, *, merge: bool = True):
    """One header row with a group label spanning three replicate columns per group.

    This is the shape of a fatigue-protocol or force-frequency sheet: an index column, then a
    block of replicates per condition with the condition name written once over the block.
    ``merge=False`` writes the same thing visually but without a merged range, which is the case
    the loader must *not* silently treat as a span.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws["A1"] = "x"
    ws["B1"] = "WT"
    ws["E1"] = "MUT"
    if merge:
        ws.merge_cells("B1:D1")
        ws.merge_cells("E1:G1")
    for row in range(2, 6):
        ws.cell(row=row, column=1, value=row - 1)
        for col in range(2, 8):
            ws.cell(row=row, column=col, value=float(row * 10 + col))
    wb.save(path)
    return path


def _two_level_header(path):
    """Fibre type on row 1, genotype on row 3, a blank row between, and a spacer column."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws["A1"] = "type 2a"
    ws["D1"] = "type 2b"
    ws["A3"] = "WT"
    ws["B3"] = "MUT"
    ws["D3"] = "WT"
    ws["E3"] = "MUT"
    for row in range(4, 8):
        for col in (1, 2, 4, 5):
            ws.cell(row=row, column=col, value=float(row + col))
    wb.save(path)
    return path


def _title_row_then_header(path):
    """A report title on row 1 and the real header on row 2."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws["A1"] = "Exported 2026-01-01"
    ws["A2"] = "gene"
    ws["B2"] = "value"
    for i, (g, v) in enumerate([("AAA", 1.5), ("BBB", 2.5), ("CCC", 3.5)], start=3):
        ws.cell(row=i, column=1, value=g)
        ws.cell(row=i, column=2, value=v)
    wb.save(path)
    return path


# --------------------------------------------------------------------------------------
# the header argument must actually do something
# --------------------------------------------------------------------------------------

CSV = "Exported 2026-01-01,,\ngene,value,note\nAAA,1.5,ok\nBBB,2.5,ok\n"


def test_delimited_header_row_is_honoured():
    """Before the fix every header value returned the same frame."""
    zero = load_table(CSV.encode(), source_name="s.csv", file_type="csv", header=0)
    one = load_table(CSV.encode(), source_name="s.csv", file_type="csv", header=1)
    assert list(zero.dataframe.columns)[0] == "Exported 2026-01-01"
    assert list(one.dataframe.columns) == ["gene", "value", "note"]
    assert one.dataframe.shape == (2, 3)


def test_delimited_no_header_gives_positional_names():
    """'No header' must be selectable; positional names keep column mapping usable."""
    info = load_table(CSV.encode(), source_name="s.csv", file_type="csv", header=None)
    assert list(info.dataframe.columns) == ["column_1", "column_2", "column_3"]
    assert info.dataframe.shape == (4, 3)


def test_excel_header_row_is_honoured(tmp_path):
    path = _title_row_then_header(tmp_path / "titled.xlsx")
    zero = load_table(str(path), header=0)
    one = load_table(str(path), header=1)
    assert list(zero.dataframe.columns)[0] == "Exported 2026-01-01"
    assert list(one.dataframe.columns) == ["gene", "value"]
    assert one.dataframe.shape == (3, 2)
    assert one.dataframe["value"].tolist() == [1.5, 2.5, 3.5]


def test_excel_no_header_gives_positional_names(tmp_path):
    path = _title_row_then_header(tmp_path / "titled.xlsx")
    info = load_table(str(path), header=None)
    assert list(info.dataframe.columns) == ["column_1", "column_2"]


def test_empty_header_sequence_is_rejected(tmp_path):
    path = _title_row_then_header(tmp_path / "titled.xlsx")
    with pytest.raises(LoaderError, match="empty sequence"):
        load_table(str(path), header=[])


def test_negative_header_row_is_rejected(tmp_path):
    path = _title_row_then_header(tmp_path / "titled.xlsx")
    with pytest.raises(LoaderError, match=">= 0"):
        load_table(str(path), header=[-1, 0])


# --------------------------------------------------------------------------------------
# merged group labels
# --------------------------------------------------------------------------------------

def test_merged_group_label_spans_its_block(tmp_path):
    """A label merged over three columns must name all three, not just the first."""
    path = _merged_group_header(tmp_path / "merged.xlsx", merge=True)
    df = load_table(str(path), header=0).dataframe
    columns = list(df.columns)
    assert df.shape == (4, 7)
    assert columns[0] == "x"
    # every replicate carries its group, disambiguated rather than deduplicated
    assert [c.split(".")[0] for c in columns[1:4]] == ["WT", "WT", "WT"]
    assert [c.split(".")[0] for c in columns[4:7]] == ["MUT", "MUT", "MUT"]
    assert len(set(columns)) == 7, "columns must stay distinct"
    assert not any(str(c).startswith("Unnamed") for c in columns)


def test_unmerged_blank_header_is_not_given_an_invented_span(tmp_path):
    """A blank header outside a merge means 'no name'; the default must not guess otherwise."""
    path = _merged_group_header(tmp_path / "unmerged.xlsx", merge=False)
    df = load_table(str(path), header=0).dataframe
    groups = [str(c).split(".")[0] for c in df.columns]
    # only the columns that actually held a label are named for their group
    assert groups.count("WT") == 1
    assert groups.count("MUT") == 1


def test_forward_fill_is_opt_in_for_unmerged_blanks(tmp_path):
    """The visual reading is available, but only when explicitly requested."""
    path = _two_level_header(tmp_path / "twolevel.xlsx")
    default = load_table(str(path), header=[0, 2]).dataframe
    forward = load_table(str(path), header=[0, 2], header_fill="forward").dataframe

    assert "type 2a | WT" in list(default.columns)
    # under the default the second column of each block loses the outer label...
    assert "type 2a | MUT" not in list(default.columns)
    # ...and gains it when forward fill is asked for
    assert "type 2a | MUT" in list(forward.columns)
    assert "type 2b | MUT" in list(forward.columns)
    assert len(set(forward.columns)) == forward.shape[1]


def test_two_level_header_composes_both_levels(tmp_path):
    path = _two_level_header(tmp_path / "twolevel.xlsx")
    df = load_table(str(path), header=[0, 2], header_fill="forward").dataframe
    assert df.shape[0] == 4
    for name in ("type 2a | WT", "type 2a | MUT", "type 2b | WT", "type 2b | MUT"):
        assert name in list(df.columns)
    assert pd.api.types.is_numeric_dtype(df["type 2a | WT"])


def test_unknown_header_fill_mode_is_rejected(tmp_path):
    path = _two_level_header(tmp_path / "twolevel.xlsx")
    with pytest.raises(LoaderError, match="header_fill"):
        load_table(str(path), header=[0, 2], header_fill="sideways")


def test_single_header_row_behaviour_is_unchanged_for_ordinary_sheets(tmp_path):
    """The common case must not shift: a plain header row still reads as before."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["gene", "logFC", "padj"])
    ws.append(["AAA", 1.2, 0.01])
    ws.append(["BBB", -0.5, 0.20])
    path = tmp_path / "plain.xlsx"
    wb.save(path)
    df = load_table(str(path)).dataframe
    assert list(df.columns) == ["gene", "logFC", "padj"]
    assert df.shape == (2, 3)


# --------------------------------------------------------------------------------------
# worksheet provenance survives header selection
# --------------------------------------------------------------------------------------

def test_worksheet_provenance_records_the_chosen_header_row(tmp_path):
    from make_my_figure_core.io.workbook import inspect_excel_workbook, load_excel_sheet

    path = _title_row_then_header(tmp_path / "titled.xlsx")
    wb = inspect_excel_workbook(str(path))
    info = load_excel_sheet(wb, "Sheet1", source=str(path), header=1)
    assert list(info.dataframe.columns) == ["gene", "value"]
    assert info.source_sheet_name == "Sheet1"
    assert info.source_header_row == 1
    assert info.source_workbook_name.endswith("titled.xlsx")


# --------------------------------------------------------------------------------------
# the reshape-and-plot path the concern needed
# --------------------------------------------------------------------------------------

def test_merged_replicate_block_reshapes_to_a_grouped_line_plot(tmp_path):
    """End to end: merged header -> long frame -> mean +/- SEM line plot per group."""
    from scipy import stats as sps

    from make_my_figure_core.grouping import melt_matrix_to_long
    from make_my_figure_core.plots.registry import make_spec, render

    path = _merged_group_header(tmp_path / "merged.xlsx", merge=True)
    df = load_table(str(path), header=0).dataframe
    x_col = df.columns[0]
    replicates = [c for c in df.columns[1:]]
    assignment = {c: str(c).split(".")[0] for c in replicates}

    long = melt_matrix_to_long(df, sample_columns=replicates, sample_to_group=assignment,
                               feature_col=x_col, value_name="force", group_col="genotype",
                               feature_name="step")
    long["step"] = pd.to_numeric(long["step"], errors="coerce")
    assert set(long["genotype"]) == {"WT", "MUT"}
    assert len(long) == 4 * 6

    spec = make_spec("lineplot_timecourse_with_error_band", "synthetic", "publication",
                     mapping={"x": "step", "y": "force", "color": "genotype", "error": "sem"})
    res = render(spec, long)
    try:
        ax = res.figure.axes[0]
        drawn = {str(line.get_label()): line for line in ax.lines
                 if not str(line.get_label()).startswith("_")}
        assert set(drawn) == {"WT", "MUT"}
        # every drawn point is the group mean at that x, checked against pandas
        for label, line in drawn.items():
            sub = long[long["genotype"] == label]
            for x, y in zip(line.get_xdata(), line.get_ydata()):
                expected = sub[sub["step"] == x]["force"].mean()
                assert y == pytest.approx(expected, abs=1e-9)
                # and the group really has 3 replicates, so SEM is defined
                assert len(sub[sub["step"] == x]) == 3
                assert sps.sem(sub[sub["step"] == x]["force"], ddof=1) > 0
    finally:
        plt.close(res.figure)


def test_density_overlay_mode_shows_every_group_on_a_shared_axis():
    """Two-group distribution comparison: the ridgeline hid one curve under the other."""
    import numpy as np

    from make_my_figure_core.plots.registry import make_spec, render

    rng = np.random.default_rng(3)
    long = pd.concat([
        pd.DataFrame({"d": rng.normal(30, 6, 400), "genotype": "WT"}),
        pd.DataFrame({"d": rng.normal(31, 6, 400), "genotype": "MUT"}),
    ], ignore_index=True)

    spec = make_spec("ridge_or_density_plot", "synthetic", "publication",
                     mapping={"x": "d", "group": "genotype", "density_mode": "overlay"})
    res = render(spec, long)
    try:
        ax = res.figure.axes[0]
        assert res.metadata["density_mode"] == "overlay"
        assert ax.get_ylabel() == "Density"
        assert ax.get_ylim()[0] == pytest.approx(0.0)
        labels = {str(t.get_text()) for t in ax.get_legend().get_texts()}
        assert labels == {"WT", "MUT"}
        # both curves start from the common baseline, so neither is offset out of view
        curves = [line for line in ax.lines if not str(line.get_label()).startswith("_")]
        assert len(curves) == 2
        for line in curves:
            ys = line.get_ydata()
            assert min(ys) >= 0.0
            assert max(ys) > 0.0
    finally:
        plt.close(res.figure)


def test_ridge_mode_remains_the_default():
    import numpy as np

    from make_my_figure_core.plots.registry import make_spec, render

    rng = np.random.default_rng(5)
    long = pd.concat([
        pd.DataFrame({"d": rng.normal(10, 2, 200), "g": "a"}),
        pd.DataFrame({"d": rng.normal(14, 2, 200), "g": "b"}),
    ], ignore_index=True)
    spec = make_spec("ridge_or_density_plot", "synthetic", "publication",
                     mapping={"x": "d", "group": "g"})
    res = render(spec, long)
    try:
        assert res.metadata["density_mode"] == "ridge"
        assert [t.get_text() for t in res.figure.axes[0].get_yticklabels()] == ["a", "b"]
    finally:
        plt.close(res.figure)


def test_unknown_density_mode_is_rejected():
    from make_my_figure_core.plots.base import RenderError
    from make_my_figure_core.plots.registry import make_spec, render

    long = pd.DataFrame({"d": [1.0, 2.0, 3.0, 4.0], "g": ["a", "a", "b", "b"]})
    spec = make_spec("ridge_or_density_plot", "synthetic", "publication",
                     mapping={"x": "d", "group": "g", "density_mode": "sideways"})
    with pytest.raises(RenderError, match="density_mode"):
        render(spec, long)


# --------------------------------------------------------------------------------------
# frontend propagation: the header choice must reach the loader from both frontends
# --------------------------------------------------------------------------------------

def test_desktop_controller_forwards_header_and_fill(tmp_path):
    from apps.desktop_app.controller import DesktopController
    from make_my_figure_core.io.workbook import inspect_excel_workbook

    path = _two_level_header(tmp_path / "twolevel.xlsx")
    wb = inspect_excel_workbook(str(path))
    controller = DesktopController()

    default = controller.load_workbook_sheet(wb, "Sheet1", source=str(path), header=[0, 2])
    forward = controller.load_workbook_sheet(wb, "Sheet1", source=str(path), header=[0, 2],
                                             header_fill="forward")
    assert "type 2a | MUT" not in list(default.info.dataframe.columns)
    assert "type 2a | MUT" in list(forward.info.dataframe.columns)
    assert forward.info.source_header_row == [0, 2]


def test_streamlit_app_passes_the_header_choice_to_the_loader():
    """Static check: Streamlit is not installed here, so the call site is inspected instead.

    The Streamlit app previously called ``load_excel_sheet(wbk, sheet, source=raw)`` with no header
    argument, so the header control could not have worked even once the loader honoured it. Guarding
    the call site keeps that from silently regressing in an environment where the app cannot run.
    """
    import ast
    import pathlib

    source = pathlib.Path("apps/streamlit_app/streamlit_app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "load_excel_sheet"
    ]
    assert calls, "the Streamlit app no longer loads a worksheet"
    for call in calls:
        keywords = {kw.arg for kw in call.keywords}
        assert "header" in keywords, "worksheet loaded without forwarding the header choice"
        assert "header_fill" in keywords, "worksheet loaded without forwarding header_fill"
