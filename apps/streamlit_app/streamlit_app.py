"""Make My Figure — Streamlit dashboard (Milestone 1).

Flow:
1. Upload a CSV/TSV/XLSX file (or load a bundled sample table).
2. Preview and validate the table.
3. Choose a plot type and map columns.
4. Fine-tune the Publication style (fonts, palette, sizes) if desired.
5. Preview the figure.
6. Export SVG / PNG / PDF and the reproducible PlotSpec JSON.

Run with:  streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import io
import json
import os
import sys

import matplotlib
import pandas as pd

matplotlib.use("Agg")  # headless backend for server-side rendering

# Make the package importable when run via
# `streamlit run apps/streamlit_app/streamlit_app.py`.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import streamlit as st

from make_my_figure_core import ui_hints
from make_my_figure_core.io.loaders import LoaderError, load_table
from make_my_figure_core.io import workbook as workbook_io
from make_my_figure_core.plots.base import RenderError
from make_my_figure_core.plots.registry import (
    available_plot_types,
    default_mapping,
    display_name,
    make_spec,
    render,
)
from make_my_figure_core.spec.validate import SpecValidationError, default_output_block
from make_my_figure_core.styles.engine import list_profiles, load_profile
from make_my_figure_core import examples

MOCK_DIR = os.path.join(_REPO_ROOT, "mock_data")

# Plot type -> bundled sample file used by the sample picker.
SAMPLE_FILES = {
    "barplot_with_error_bar": "barplot_error_raw.csv",
    "grouped_barplot_with_error_bar": "grouped_barplot_error.csv",
    "heatmap_clustered_matrix": "heatmap_expression_matrix.tsv",
    "volcano_plot": "volcano_plot.csv",
    "scatterplot_with_regression": "scatter_regression.csv",
    "boxplot_or_violin_with_points": "box_violin_points.csv",
    "lineplot_timecourse_with_error_band": "line_timecourse.tsv",
    "ridge_or_density_plot": "ridge_density.csv",
    "enrichment_dotplot": "enrichment_dotplot.csv",
    "kaplan_meier_survival_curve": "survival_km.csv",
    "stacked_bar_composition": "stacked_composition.csv",
    "waterfall_plot": "waterfall_response.csv",
    "pca_scatter_from_matrix": "pca_expression_matrix.tsv",
    "oncoprint_mutation_heatmap": "oncoprint_long.csv",
    "lollipop_mutation_plot": "lollipop_mutations.csv",
    "roc_curve": "roc_curve_scores.csv",
    "forest_plot": "forest_plot.csv",
}

# PCA needs a second (metadata) table; this maps the matrix sample -> metadata file.
PCA_METADATA_SAMPLE = "pca_sample_metadata.csv"

# Which mapping keys are exposed as column selectors per plot type.
# Column roles come from the shared ui_hints registry, which is also what the desktop app reads,
# so a role added for a plot type appears in both frontends instead of only one. This module used to
# keep its own copy of the table; it had drifted to 18 of the 37 plot types, which left the other 19
# with no column-mapping controls at all, and it lacked roles that had since been added elsewhere.
#
# EXTRA_COLUMN_FIELDS holds the few roles this app offers that ui_hints deliberately does not.
# PCA colour/shape are read from the separate sample-metadata table, so ui_hints exposes them via
# PCA_METADATA_FIELDS rather than as columns of the matrix; this app asks for them here instead.
# Entries are appended, never substituted, so switching to ui_hints cannot remove a control.
EXTRA_COLUMN_FIELDS = {
    "pca_scatter_from_matrix": ["color", "shape"],
}


def column_fields_for(plot_type: str) -> list:
    fields = list(ui_hints.column_fields(plot_type))
    for extra in EXTRA_COLUMN_FIELDS.get(plot_type, []):
        if extra not in fields:
            fields.append(extra)
    return fields



st.set_page_config(page_title="Make My Figure", layout="wide")
st.title("Make My Figure")
st.caption(
    "Manuscript-ready scientific figures in a single, polished Publication style. "
    "This is a general publication-ready visual style — not an official journal "
    "template, and not a guarantee of submission compliance."
)


# --- 1. Data source ---------------------------------------------------------
# --- App navigation: reset / upload new data --------------------------------
# Streamlit reruns top-to-bottom, so "return to upload" clears session state
# (dataset, mappings, stats, preprocessing) and reruns to a clean upload state.
if st.sidebar.button("🏠 Reset / Upload new data", use_container_width=True,
                     help="Clear the current dataset, plot, statistics, and "
                          "preprocessing results and return to a clean upload state "
                          "(no restart)."):
    for _k in list(st.session_state.keys()):
        del st.session_state[_k]
    st.rerun()

def _clear_sheet_dependent_state():
    """Drop state tied to a previously selected worksheet/workbook.

    Switching worksheets (or uploading a different workbook) must not silently
    reuse another sheet's column mappings, value-column picks, annotation offsets,
    matrix-workflow state, grouped/derived tables, or a stale plot-type choice.
    The Streamlit plot is recomputed every rerun, so clearing this state is what
    makes the switch clean.
    """
    prefixes = ("map_", "valcols_", "annot_", "mw_", "grp_")
    drop = [k for k in st.session_state if str(k).startswith(prefixes)]
    for k in ("_grouped_df", "_grouped_name", "rec_plot_type", "data_editor"):
        if k in st.session_state:
            drop.append(k)
    for k in drop:
        st.session_state.pop(k, None)


st.sidebar.divider()
# Build/version indicator: lets a user confirm they run the freshly-pulled code
# (not a stale installed package) — key for diagnosing platform-specific reports.
try:
    from make_my_figure_core.version import build_banner as _bb  # noqa: E402
    from make_my_figure_core.version import build_info as _binfo  # noqa: E402
    st.sidebar.caption("🔖 " + _bb())
    with st.sidebar.expander("🔧 Diagnostics", expanded=False):
        _bi = _binfo()
        st.write({"frontend": "streamlit", "version": _bi["version"],
                  "commit": _bi["commit"], "platform": _bi["platform"],
                  "python": _bi["python"], "python_executable": _bi["python_executable"],
                  "make_my_figure_core path": _bi["module_path"],
                  "matplotlib_backend": _bi["backend"]})
        st.caption("If `commit` doesn't match your pulled HEAD, a stale installed "
                   "package is shadowing the repo — run `python -m pip install -e .`.")
except Exception:  # noqa: BLE001
    pass
# Figure-preset values staged by the previous run are written into widget state here, before any
# widget exists. Streamlit refuses to change a widget's key once that widget has been created in the
# current run, and the column/option widgets are created long before the preset controls - so a
# preset is applied by staging its values and rerunning, never by writing into live widgets.
_pending = st.session_state.pop("_preset_pending", None)
if _pending:
    for _k, _v in _pending.items():
        st.session_state[_k] = _v

st.sidebar.header("1. Data")
source_mode = st.sidebar.radio("Data source",
                               ["Bundled sample", "Upload file", "Open PlotSpec", "Open Figure Package"],
                               help=("Open PlotSpec = specification only (needs the data table). "
                                     "Open Figure Package = .mmfpackage with the frozen data inside."))

# --- Open a figure package: specification + frozen data + records, verified by checksum ---
if source_mode == "Open Figure Package":
    from make_my_figure_core.package import (
        PACKAGE_EXTENSION,
        PackageError,
        open_figure_package,
        rebuild_composite,
        single_plot_inputs,
        verify_preprocessing,
        verify_statistics,
    )

    st.subheader("Open a reproducible figure package")
    st.caption(f"Upload a `*{PACKAGE_EXTENSION}` saved by Make My Figure. It carries the plot specification, "
               "a frozen copy of the data, statistics/preprocessing records and previews; every file is "
               "checked against the SHA-256 recorded in its manifest before anything is drawn.")
    pkg_file = st.file_uploader("Figure package", type=[PACKAGE_EXTENSION.lstrip(".")], key="pkg_upload")
    if pkg_file is None:
        st.info("Upload a figure package to reproduce the figure.")
        st.stop()
    try:
        _pkg = open_figure_package(pkg_file.getvalue())
    except PackageError as _exc:
        st.error(f"Could not open figure package: {_exc}")
        st.stop()
    except Exception as _exc:  # noqa: BLE001
        st.error(f"Could not open figure package (unexpected error): {_exc}")
        st.stop()
    st.success("Package integrity verified — " + "; ".join(_pkg.summary_lines()))
    try:
        if _pkg.kind == "composite":
            from make_my_figure_core.panels import build_figure as _build_figure

            _mpf = rebuild_composite(_pkg)
            _fig = _build_figure(_mpf)
            st.pyplot(_fig, use_container_width=False)
            st.caption(f"{len(_mpf.panels)} panel(s) rebuilt from the frozen panel data.")
            _stem = _mpf.name.replace(" ", "_")
        else:
            _spec, _df, _aux = single_plot_inputs(_pkg)
            _res = render(_spec, _df, aux=_aux or None)
            _fig = _res.figure
            st.pyplot(_fig, use_container_width=False)
            for _w in (_res.warnings or []):
                st.warning(_w)
            _probs = verify_statistics(_pkg.stats_payload, getattr(_res, "stats_report", None))
            if _probs:
                st.warning("Statistics recomputed from the frozen data differ from the stored StatsSpec: "
                           + "; ".join(_probs[:5]))
            elif _pkg.stats_payload:
                st.caption("Statistics recomputed from the frozen data match the stored StatsSpec.")
            if _pkg.preprocessing_spec:
                _chk = verify_preprocessing(_pkg)
                (st.warning if _chk["status"] in ("differs", "error") else st.caption)(
                    f"Preprocessing record check: {_chk['status']} — {_chk['detail']}")
            with st.expander("Frozen data table"):
                st.dataframe(_df, use_container_width=True)
            with st.expander("Plot specification (from the package)"):
                st.json(_spec)
            _stem = _pkg.name.replace(" ", "_")
        from make_my_figure_core.plots.registry import figure_to_bytes as _f2b

        _c1, _c2, _c3 = st.columns(3)
        _c1.download_button("PNG", _f2b(_fig, "png", dpi=300), file_name=f"{_stem}.png", mime="image/png")
        _c2.download_button("SVG", _f2b(_fig, "svg"), file_name=f"{_stem}.svg", mime="image/svg+xml")
        _c3.download_button("PDF", _f2b(_fig, "pdf"), file_name=f"{_stem}.pdf", mime="application/pdf")
    except Exception as _exc:  # noqa: BLE001
        st.error(f"Opened the package but could not reproduce the figure: {_exc}")
    st.stop()

# --- Open a saved PlotSpec: reproduce an exported figure from its JSON + data ---
if source_mode == "Open PlotSpec":
    st.subheader("Open a saved PlotSpec")
    st.caption("Upload a `*.plot_spec.json` you exported earlier (or a benchmark "
               "panel's plotspec.json) plus its data table to reproduce the exact "
               "figure — no need to re-map columns.")
    ps_file = st.file_uploader("PlotSpec JSON", type=["json"], key="ps_json")
    data_file = st.file_uploader("Data table (CSV / TSV / XLSX)",
                                 type=["csv", "tsv", "txt", "xlsx", "xls"], key="ps_data")
    if ps_file is None or data_file is None:
        st.info("Upload both the PlotSpec JSON and its data table to render.")
        st.stop()
    try:
        spec = json.load(io.BytesIO(ps_file.getvalue()))
        if not isinstance(spec, dict) or "plot_type" not in spec:
            raise ValueError("This file is not a PlotSpec (no 'plot_type').")
        from make_my_figure_core.styles.engine import normalize_style_name
        if spec.get("journal_style"):
            spec["journal_style"] = normalize_style_name(spec["journal_style"])
        _ti = load_table(data_file.getvalue(), source_name=data_file.name)
        result = render(spec, _ti.dataframe)
        st.pyplot(result.figure, use_container_width=False)
        for w in (result.warnings or []):
            st.warning(w)
        png = io.BytesIO(); result.figure.savefig(png, format="png", dpi=(spec.get("output") or {}).get("dpi", 300), bbox_inches="tight")
        st.download_button("Download PNG", png.getvalue(), file_name="reproduced.png", mime="image/png")
        st.download_button("Download PlotSpec JSON", json.dumps(spec, indent=2),
                           file_name="reproduced.plot_spec.json", mime="application/json")
    except Exception as exc:
        st.error(f"Could not reproduce this PlotSpec: {exc}")
    st.stop()

table_info = None
table_name = None
_upload_raw, _upload_name = None, None
bundled_aux = None

_use_examples = examples.has_manifest()

if source_mode == "Bundled sample":
    sample_keys = examples.plot_types_with_examples() if _use_examples else list(SAMPLE_FILES.keys())
    plot_for_sample = st.sidebar.selectbox(
        "Example dataset (by plot type)",
        options=sample_keys,
        format_func=display_name,
    )
    try:
        if _use_examples:
            info, aux_tables, _spec = examples.load_example(plot_for_sample)
            table_info = info
            table_name = f"{plot_for_sample} (example)"
            bundled_aux = {k: v.dataframe for k, v in aux_tables.items()}
            entry = examples.entry(plot_for_sample) or {}
            if entry.get("use_case"):
                st.sidebar.caption(f"Synthetic example — {entry['use_case']}")
        else:
            table_info = load_table(os.path.join(MOCK_DIR, SAMPLE_FILES[plot_for_sample]))
            table_name = SAMPLE_FILES[plot_for_sample]
    except (LoaderError, KeyError) as exc:
        st.sidebar.error(f"Could not load example: {exc}")
    default_plot_type = plot_for_sample
else:
    uploaded = st.sidebar.file_uploader("Upload CSV / TSV / XLSX", type=["csv", "tsv", "txt", "xlsx", "xls"])
    # No auto-selected plot on upload — start on the placeholder (parity with desktop;
    # do not silently default to the first/bar plot).
    default_plot_type = None
    _empty_sheet_selected = False
    if uploaded is not None:
        raw = uploaded.getvalue()
        _upload_raw, _upload_name = raw, uploaded.name
        if workbook_io.is_excel_source(uploaded.name):
            # --- Multi-sheet workbook browser -------------------------------
            try:
                wbk = workbook_io.inspect_excel_workbook(raw, source_name=uploaded.name)
            except LoaderError as exc:
                st.sidebar.error(f"Could not open workbook: {exc}")
                st.stop()
            # A different workbook clears everything sheet-dependent.
            if st.session_state.get("_wb_hash") != wbk.file_hash:
                _clear_sheet_dependent_state()
                st.session_state["_wb_hash"] = wbk.file_hash
                st.session_state.pop("_wb_sheet", None)
                st.session_state.pop("_wb_active_sheet", None)
            for _w in wbk.warnings:
                st.sidebar.caption("⚠ " + _w)
            st.sidebar.subheader("📑 Worksheet")
            st.sidebar.caption(f"{wbk.n_sheets} worksheet(s) — every sheet is "
                               "selectable, including notes/empty sheets.")

            def _sheet_label(name):
                return f"{name} (hidden)" if wbk.is_hidden(name) else name

            # Dropdown keeps workbook order, full names, Unicode; persists in session.
            sheet = st.sidebar.selectbox(
                "Worksheet", options=wbk.sheet_names, key="_wb_sheet",
                format_func=_sheet_label,
                help="Choose any worksheet. Documentation/empty sheets stay "
                     "selectable; classification is advisory only.")
            # Switching worksheets clears stale mappings/stats/derived tables.
            if st.session_state.get("_wb_active_sheet") != sheet:
                _clear_sheet_dependent_state()
                st.session_state["_wb_active_sheet"] = sheet
            prev = workbook_io.preview_excel_sheet(wbk, sheet, source=raw)
            st.sidebar.caption(prev.type_message)
            for _w in prev.warnings:
                st.sidebar.caption("• " + _w)
            if prev.is_empty:
                # Empty sheet: selectable + previewable, but plotting disabled.
                _empty_sheet_selected = True
                st.subheader("Workbook browser")
                st.info(f"**Workbook:** {uploaded.name}  \n**Worksheet:** {sheet}")
                st.warning("This worksheet is empty. Plotting is disabled — pick "
                           "another worksheet from the dropdown.")
                st.stop()
            # Header row. A sheet written for people often carries a title row above the real
            # header, or a group label on one row and the sub-label on the next. Without this
            # control the loader's own "confirm the header row" advice cannot be acted on.
            _hdr_choice = st.sidebar.selectbox(
                "Header row", options=["First row", "Choose row…", "Two rows (stacked)",
                                       "No header"],
                key="_wb_header_mode",
                help="Where the column names are. Use 'Two rows' when a group label sits above "
                     "a sub-label, and 'No header' when the sheet starts straight into data.")
            if _hdr_choice == "First row":
                _header: object = 0
            elif _hdr_choice == "No header":
                _header = None
            elif _hdr_choice == "Choose row…":
                _header = int(st.sidebar.number_input(
                    "Header is spreadsheet row", min_value=1,
                    max_value=max(1, int(prev.row_count) + 1), value=1, step=1,
                    key="_wb_header_row",
                    help="Counting the way the spreadsheet does, so row 1 is the top row.")) - 1
            else:
                _top = int(st.sidebar.number_input(
                    "Outer label on spreadsheet row", min_value=1,
                    max_value=max(1, int(prev.row_count) + 1), value=1, step=1,
                    key="_wb_header_top")) - 1
                _sub = int(st.sidebar.number_input(
                    "Sub-label on spreadsheet row", min_value=1,
                    max_value=max(1, int(prev.row_count) + 1), value=2, step=1,
                    key="_wb_header_sub")) - 1
                _header = sorted({_top, _sub})
            _fill = "merged"
            if _hdr_choice == "Two rows (stacked)":
                _fill = "forward" if st.sidebar.checkbox(
                    "Carry a group label across blank cells", value=False,
                    key="_wb_header_fill",
                    help="On by default only when the label was written once without merging the "
                         "cells. Off means a blank header cell stays unnamed, which is what the "
                         "file actually records.") else "merged"
            # Changing how the header is read changes every column name, so drop stale mappings.
            if st.session_state.get("_wb_header_applied") != (sheet, str(_header), _fill):
                _clear_sheet_dependent_state()
                st.session_state["_wb_header_applied"] = (sheet, str(_header), _fill)
            try:
                table_info = workbook_io.load_excel_sheet(
                    wbk, sheet, source=raw, header=_header, header_fill=_fill)
                table_name = f"{uploaded.name} [{sheet}]"
            except LoaderError as exc:
                st.sidebar.error(f"Could not load worksheet '{sheet}': {exc}")
                st.stop()
        else:
            # Delimited text: clear stale workbook state if the file changed.
            _h = workbook_io.compute_file_hash(raw)
            if st.session_state.get("_wb_hash") != _h:
                _clear_sheet_dependent_state()
                st.session_state["_wb_hash"] = _h
                st.session_state.pop("_wb_active_sheet", None)
            try:
                table_info = load_table(raw, source_name=uploaded.name)
                table_name = uploaded.name
            except LoaderError as exc:
                st.sidebar.error(f"Could not load file: {exc}")

if table_info is None:
    st.info("Choose a bundled sample or upload a data file to begin.")
    st.stop()

# --- Active-source summary (worksheet-aware) --------------------------------
_prov = table_info.provenance() if table_info is not None else {}
if _prov.get("source_sheet_name"):
    _stype = _prov.get("source_sheet_type", "unknown")
    st.caption(
        f"**Workbook:** {_prov.get('source_workbook_name')}  ·  "
        f"**Worksheet:** {_prov.get('source_sheet_name')}  ·  "
        f"**Detected type:** {_stype}  ·  "
        f"**Rows × columns:** {table_info.n_rows} × {len(table_info.columns)}")

# --- Workflow mode ----------------------------------------------------------
# "Quick plot" is the classic single-plot flow below. "Matrix workflow (guided)"
# runs the map -> groups -> validate -> recommend -> generate wizard for a
# feature-by-sample matrix (no silent guessing; annotation columns are not values).
st.sidebar.divider()
workflow_mode = st.sidebar.radio(
    "Workflow", ["Quick plot", "Matrix workflow (guided)"], key="workflow_mode",
    help="Guided matrix workflow: map a feature matrix, define groups, get plot "
         "recommendations, and generate publication plots.")
if workflow_mode.startswith("Matrix"):
    from apps.streamlit_app.matrix_wizard import render_matrix_wizard
    # Stash worksheet provenance so matrix-workflow exports stay sheet-aware.
    st.session_state["_mw_source_prov"] = _prov or None
    render_matrix_wizard(table_info.dataframe, table_name)
    st.stop()

# --- Matrix-Workflow handoff banner (this plot came from the Matrix Workflow) ----
_ho_src = st.session_state.get("_handoff_source")
if _ho_src:
    _bits = [f"**Matrix Workflow → full plot editor.**"]
    if _ho_src.get("source_sheet_name"):
        _bits.append(f"Source: {_ho_src.get('source_workbook_name','')} · "
                     f"{_ho_src['source_sheet_name']}")
    if _ho_src.get("source_preprocessing"):
        _bits.append(f"Preprocessing: {', '.join(map(str, _ho_src['source_preprocessing']))}")
    if _ho_src.get("source_statistics"):
        _bits.append(f"Stats: {_ho_src['source_statistics'].get('method', '')}")
    st.info("  ·  ".join(_bits) + "  —  full thresholds, labels, colors, annotations, "
            "layout, and export are available below.")
    if st.button("↩ Return to Matrix Workflow", key="_handoff_return_btn"):
        # Keep matrix state (mw_*); drop this plot's derived table + handoff context.
        for _k in ("_grouped_df", "_grouped_name", "_handoff_source",
                   "_handoff_defaults", "_handoff_spec_extra", "_handoff_aux"):
            st.session_state.pop(_k, None)
        st.session_state["workflow_mode"] = "Matrix workflow (guided)"
        st.rerun()

# --- Table preview + validation messages ------------------------------------
# Editable table: edits made here feed straight into the figure below.
st.subheader(f"Table — {table_name}")
st.caption("Edit cells directly to update the figure. Add/remove rows with the "
           "controls at the bottom of the table.")
_edited = st.data_editor(table_info.dataframe, use_container_width=True,
                         num_rows="dynamic", key="data_editor")
if _edited is not None and len(_edited.columns) == len(table_info.dataframe.columns):
    # Re-classify numeric columns after edits so downstream mapping stays correct.
    table_info.dataframe = _edited
cols = st.columns(3)
cols[0].metric("Rows", table_info.n_rows)
cols[1].metric("Columns", len(table_info.columns))
cols[2].metric("Numeric columns", len(table_info.numeric_columns))
if table_info.warnings:
    for w in table_info.warnings:
        st.warning(w)

# --- Define groups in-app (no metadata file) --------------------------------
from make_my_figure_core.grouping import (
    add_group_column as _add_group_column,
    guess_groups_from_names as _guess_groups,
    melt_matrix_to_long as _melt_matrix,
)
from make_my_figure_core.io.loaders import table_info_from_dataframe as _info_from_df

with st.expander("🗂 Define groups (no metadata file needed)"):
    st.caption("Assign sample columns to groups for a wide matrix, or label rows "
               "by an existing column's values. The grouped table replaces the one above.")
    gmode = st.radio("Grouping mode",
                     ["Assign sample groups (wide matrix)", "Group by column values"],
                     key="grouping_mode")
    if gmode.startswith("Assign"):
        all_cols = list(table_info.columns)
        num = set(table_info.numeric_columns)
        feat_default = next((c for c in all_cols if c not in num), all_cols[0])
        feature_col = st.selectbox("Feature id column", all_cols,
                                   index=all_cols.index(feat_default), key="grp_feat")
        sample_cols = [c for c in all_cols if c != feature_col]
        # Separate per-sample VALUE columns from numeric annotation columns (e.g.
        # annotationLevel coded 1/2/3): only value columns are pre-assigned a group;
        # annotation columns start blank so they are not treated as measurements.
        from make_my_figure_core.grouping import value_matrix_columns as _value_cols
        value_cols, annot_cols = _value_cols(table_info.dataframe, feature_col)
        value_set = {str(c) for c in value_cols}
        guess = _guess_groups([c for c in sample_cols if str(c) in value_set])
        assign_df = pd.DataFrame({"sample": sample_cols,
                                  "group": [guess.get(s, "") for s in sample_cols]})
        if annot_cols:
            st.caption("Numeric column(s) detected as annotations (left blank — assign a "
                       f"group only if they really are samples): {', '.join(map(str, annot_cols))}")
        edited_assign = st.data_editor(assign_df, key="grp_assign", use_container_width=True,
                                       hide_index=True)
        feat_values = table_info.dataframe[feature_col].astype(str).tolist()
        chosen = st.multiselect("Features to include (empty = all)", feat_values, key="grp_feats")
        if st.button("Create grouped table", key="grp_make_matrix"):
            s2g = dict(zip(edited_assign["sample"].astype(str), edited_assign["group"].astype(str)))
            try:
                long = _melt_matrix(table_info.dataframe, sample_columns=sample_cols,
                                    sample_to_group=s2g, feature_col=feature_col,
                                    features=chosen or None)
                st.session_state["_grouped_df"] = long
                st.session_state["_grouped_name"] = f"{table_name} (grouped)"
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        # Differential screen (2 groups -> results table with log2FC/p/FDR).
        st.markdown("**Differential screen (2 groups)** — normalized matrix only; a basic "
                    "per-feature test + BH FDR, *not* a count-based model (DESeq2/edgeR/voom).")
        from make_my_figure_core.differential import TESTS as _DIFF_TESTS, _TEST_LABELS as _DIFF_LBL
        _de_test = st.selectbox("DE test", list(_DIFF_TESTS),
                                format_func=lambda t: _DIFF_LBL.get(t, t), key="grp_detest")
        if st.button("Run differential screen", key="grp_run_de"):
            s2g = dict(zip(edited_assign["sample"].astype(str), edited_assign["group"].astype(str)))
            try:
                from make_my_figure_core.differential import differential_screen
                dres = differential_screen(table_info.dataframe, feature_col=feature_col,
                                           group_labels=s2g, test=_de_test)
                st.session_state["_grouped_df"] = dres.table
                st.session_state["_grouped_name"] = f"{table_name.rsplit('.',1)[0]}__diff.csv"
                st.success(dres.method_sentence())
                for _w in dres.warnings:
                    st.warning(_w)
                st.download_button("Download differential results CSV",
                                   dres.table.to_csv(index=False),
                                   file_name="differential_results.csv", mime="text/csv")
                st.info("Now pick Volcano plot / MA plot below (or see Recommended figures).")
            except Exception as exc:
                st.error(str(exc))
    else:
        source_col = st.selectbox("Source column", list(table_info.columns), key="grp_src")
        new_col = st.text_input("New group column name", value="group", key="grp_newcol")
        uniq = list(dict.fromkeys(table_info.dataframe[source_col].astype(str).tolist()))
        map_df = pd.DataFrame({"value": uniq, "group": uniq})
        edited_map = st.data_editor(map_df, key="grp_valmap", use_container_width=True,
                                    hide_index=True)
        if st.button("Add group column", key="grp_make_col"):
            mapping = {r["value"]: r["group"] for _, r in edited_map.iterrows()
                       if str(r["group"]).strip()}
            try:
                out = _add_group_column(table_info.dataframe, source_col=source_col,
                                        value_to_group=mapping, new_col=(new_col or "group"))
                st.session_state["_grouped_df"] = out
                st.session_state["_grouped_name"] = table_name
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

# Adopt a grouped table produced above (persists across reruns until reset).
if "_grouped_df" in st.session_state:
    table_info = _info_from_df(st.session_state["_grouped_df"], st.session_state["_grouped_name"])
    table_name = st.session_state["_grouped_name"]
    st.success(f"Using grouped table: {table_name} "
               f"({table_info.n_rows} rows × {len(table_info.columns)} columns). "
               "Map its columns below; use Reset to return to the original.")


# --- Recommended figures (intelligent suggestions) --------------------------
from make_my_figure_core.recommendations import recommend_for_table as _recommend_for_table

with st.expander("🔮 Recommended figures", expanded=False):
    st.caption("Make My Figure profiled your table and suggests figures — all use the "
               "Publication style. Click a suggestion to load its plot type, then map "
               "columns below. (Make My Figure does not run differential-expression "
               "analysis; upload a precomputed results table for volcano/MA plots.)")
    try:
        _rec_spec = _recommend_for_table(table_info.dataframe, table_name=table_name)
        st.markdown(f"**Detected data type:** `{_rec_spec.schema}`")
        for _r in _rec_spec.recommendations:
            _conf = int(round(float(_r.confidence) * 100))
            st.markdown(f"**{_r.display_name}** · {_conf}% match  \n{_r.why}")
            if getattr(_r, "instructions", None):
                st.caption("ℹ " + _r.instructions)   # guidance rec (e.g. run stats first)
            for _w in (_r.warnings or []):
                st.caption(f"⚠ {_w}")
            _tf = getattr(_r, "transform", None)
            if _tf and st.button(f"Use ▸ {_r.display_name}", key=f"rec_{_r.id}"):
                # reshape the data, adopt it as the working table, then load the plot type
                from make_my_figure_core.transforms import apply_transform as _apply_tf
                st.session_state["_grouped_df"] = _apply_tf(
                    table_info.dataframe, _tf["name"], _tf.get("params"))
                st.session_state["_grouped_name"] = _tf.get("output_filename") or "reshaped.csv"
                st.session_state["rec_plot_type"] = _r.plot_type
                st.rerun()
            elif _r.plot_spec_draft and not _tf and st.button(
                    f"Use ▸ {_r.display_name}", key=f"rec_{_r.id}"):
                st.session_state["rec_plot_type"] = _r.plot_type
                st.rerun()
            st.divider()
    except Exception as _exc:
        st.caption(f"Recommendations unavailable: {_exc}")

# A recommendation click sets the plot type once (manual choice wins after).
default_plot_type = st.session_state.pop("rec_plot_type", default_plot_type)

# --- 2. Plot type + 3. style ------------------------------------------------
from make_my_figure_core.ui_strings import PLOT_TYPE_PLACEHOLDER  # noqa: E402

st.sidebar.header("2. Plot type")
_plot_options = [PLOT_TYPE_PLACEHOLDER] + list(available_plot_types())
_default_idx = (_plot_options.index(default_plot_type)
                if default_plot_type in _plot_options else 0)   # 0 = placeholder
plot_type = st.sidebar.selectbox(
    "Plot type", options=_plot_options, index=_default_idx,
    format_func=lambda p: p if p == PLOT_TYPE_PLACEHOLDER else display_name(p),
)

st.sidebar.header("3. Style")
profiles = list_profiles()
journal_style = st.sidebar.selectbox(
    "Style", options=profiles, format_func=lambda s: "Publication" if s == "publication" else s,
    help="Make My Figure uses a single Publication style. Adjust palette/fonts/sizes below.")

st.sidebar.header("4. Column mapping")
mapping = default_mapping(plot_type)
columns = ["(none)"] + table_info.columns


def _column_select(label: str, key: str, default):
    options = columns
    if default in table_info.columns:
        idx = options.index(default)
    else:
        idx = 0
    choice = st.sidebar.selectbox(label, options=options, index=idx, key=f"map_{key}")
    return None if choice == "(none)" else choice


# A Matrix-Workflow handoff supplies suggested mappings for the recommended plot;
# they seed the selectbox defaults once (the map_* keys were cleared on handoff).
_MATRIX_PLOT_TYPES_EARLY = {"heatmap_clustered_matrix", "pca_scatter_from_matrix",
                            "hierarchical_clustering", "hierarchical_dendrogram"}
_handoff_mappings = st.session_state.get("_handoff_mappings") or {}
for field in column_fields_for(plot_type):
    _default = _handoff_mappings.get(field, mapping.get(field))
    if ui_hints.is_multi_column(field) and not (field == "value_columns"
                                                  and plot_type in _MATRIX_PLOT_TYPES_EARLY):
        # Several columns, one per series. A single-value picker here would quietly plot only the
        # first of them. For matrix plots "value_columns" keeps its own richer widget further
        # down; for anything else (a wide-form histogram) it is an ordinary multi-select.
        _opts = [c for c in table_info.columns]
        _pre = [c for c in (_default or []) if c in _opts] if isinstance(_default, (list, tuple)) \
            else ([_default] if _default in _opts else [])
        _picked = st.sidebar.multiselect(
            field, _opts, default=_pre, key=f"map_{field}",
            help="Pick one column per series. Repeated spreadsheet headers arrive "
                 "disambiguated (e.g. event, event.1, event.2) — select them all.")
        if _picked:
            mapping[field] = list(_picked)
    else:
        mapping[field] = _column_select(field, field, _default)

# Matrix plots: let the user pick the VALUE (measurement) columns explicitly.
# Populate every non-id column and default the selection to the auto-detected
# value columns, so numeric annotation columns (e.g. annotationLevel) are left out
# unless the user opts them in. Nothing is silently assumed — the selection here
# is what gets plotted.
_MATRIX_PLOT_TYPES = {"heatmap_clustered_matrix", "pca_scatter_from_matrix",
                      "hierarchical_clustering", "hierarchical_dendrogram"}
if plot_type in _MATRIX_PLOT_TYPES:
    _id_field = "matrix_row_id" if plot_type == "pca_scatter_from_matrix" else "row_id"
    _id_col = mapping.get(_id_field)
    _all = [c for c in table_info.columns if c != _id_col]
    try:
        from make_my_figure_core.grouping import value_matrix_columns as _vmc
        _val, _ann = _vmc(table_info.dataframe, _id_col)
    except Exception:
        _val, _ann = _all, []
    _ho_vals = _handoff_mappings.get("value_columns")
    _vc_default = ([c for c in _all if c in set(map(str, _ho_vals))] if _ho_vals
                   else [c for c in _all if c in set(map(str, _val)) or c in _val])
    _sel = st.sidebar.multiselect(
        "Value columns (measurements)", _all,
        default=_vc_default,
        key=f"valcols_{plot_type}",
        help="Numeric sample columns to plot. Annotation columns (e.g. annotationLevel) "
             "are left out by default; add them only if they are real measurements.")
    if _sel:
        mapping["value_columns"] = _sel

# The handoff mappings are one-shot — consumed now that the mapping widgets exist.
st.session_state.pop("_handoff_mappings", None)

# Plot-type-specific options. (Bar plots: ``summary`` / ``error`` and the observation, fill,
# n-label and orientation controls all come from the registry via the generic block below, under
# the same ``opt_{plot_type}_{key}`` session keys.)
if plot_type == "heatmap_clustered_matrix":
    mapping["cluster_rows"] = st.sidebar.checkbox("Cluster rows", value=True, key=f"opt_{plot_type}_cluster_rows")
    mapping["cluster_columns"] = st.sidebar.checkbox("Cluster columns", value=True, key=f"opt_{plot_type}_cluster_columns")
    mapping["color_scale"] = st.sidebar.selectbox("Color scale", ["diverging", "sequential"], index=0, key=f"opt_{plot_type}_color_scale")
if plot_type == "volcano_plot":
    mapping["lfc_cutoff"] = st.sidebar.number_input("log2FC cutoff", value=1.0, step=0.5, key=f"opt_{plot_type}_lfc_cutoff")
    mapping["p_cutoff"] = st.sidebar.number_input("p-value cutoff", value=0.05, step=0.01, format="%.3f", key=f"opt_{plot_type}_p_cutoff")
# Interactive labelling (volcano / MA) — Streamlit's canvas is static, so this is the
# click-to-label FALLBACK: choose points to label, then move a selected label with
# offset controls. Backed by the shared AnnotationState so it round-trips into the
# PlotSpec exactly like the desktop click-to-label path.
if plot_type in ("volcano_plot", "ma_plot"):
    from make_my_figure_core.plots.annotation_state import AnnotationState  # noqa: E402
    _lab_col = mapping.get("label")
    if _lab_col and _lab_col in table_info.dataframe.columns:
        with st.sidebar.expander("Label points (annotate)", expanded=False):
            from make_my_figure_core.plots import label_policy as _lp  # noqa: E402
            _key = f"annot_{plot_type}"
            # Duplicate-label handling: several rows/peptides may share a gene symbol.
            st.caption("Multiple rows may share the same gene symbol. Choose whether "
                       "to label every plotted row or only one representative point "
                       "per gene.")
            _pol = st.selectbox(
                "Duplicate label handling", list(_lp.DUPLICATE_POLICIES),
                format_func=lambda p: _lp.POLICY_LABELS[p], key=f"{_key}_pol",
                help="'Label every selected point' keeps every peptide row (default).")
            mapping["duplicate_label_policy"] = _pol
            if _pol in ("unique", "count"):
                _rep_cols = {"pvalue": mapping.get("p"),
                             "padj": mapping.get("adj_p") or mapping.get("padj"),
                             "effect": mapping.get("x") or mapping.get("y"),
                             "statistic": mapping.get("statistic")}
                _avail = _lp.available_rules(_rep_cols, table_info.dataframe.columns)
                _rule = st.selectbox(
                    "Representative point", _avail,
                    format_func=lambda r: _lp.RULE_LABELS[r], key=f"{_key}_rule",
                    help="Which row represents each gene when collapsing duplicates.")
                mapping["duplicate_label_representative_rule"] = _rule
                mapping["duplicate_label_show_count"] = (_pol == "count")
            _choices = [str(v) for v in table_info.dataframe[_lab_col].dropna().unique()][:2000]
            _state = AnnotationState.from_mapping(st.session_state.get(_key, {}))
            _picked = st.multiselect("Points to label", _choices,
                                     default=[l for l in _state.labels() if l in _choices],
                                     key=f"{_key}_pick")
            # rebuild state: keep offsets for still-picked labels
            _new = AnnotationState.from_mapping({"selected_labels": _picked,
                                                 "label_offsets": {
                                                     k: v for k, v in
                                                     ({a.label_text: [a.offset_x_points, a.offset_y_points]
                                                       for a in _state.annotations.values() if a.moved}).items()
                                                     if k in _picked}})
            if _picked:
                _sel = st.selectbox("Move which label", _picked, key=f"{_key}_sel")
                _dx = st.number_input("x offset (pt)", value=float(
                    (_new.annotations.get(_sel).offset()[0]) if _new.annotations.get(_sel) else 8.0),
                    step=4.0, key=f"{_key}_dx")
                _dy = st.number_input("y offset (pt)", value=float(
                    (_new.annotations.get(_sel).offset()[1]) if _new.annotations.get(_sel) else 8.0),
                    step=4.0, key=f"{_key}_dy")
                if st.button("Reset this label position", key=f"{_key}_reset"):
                    _new.reset(_sel)
                else:
                    _new.set_offset(_sel, _dx, _dy)
            st.session_state[_key] = _new.to_mapping()
            mapping.update(_new.to_mapping())
            mapping.setdefault("annotate", True)
            if _picked:
                mapping["label_mode"] = "pasted"
                mapping["label_list"] = _picked

if plot_type == "scatterplot_with_regression":
    mapping["fit_line"] = st.sidebar.checkbox("Fit regression line", value=True, key=f"opt_{plot_type}_fit_line")
if plot_type == "boxplot_or_violin_with_points":
    mapping["kind"] = st.sidebar.selectbox("Kind", ["box", "violin"], index=0, key=f"opt_{plot_type}_kind")
    mapping["points"] = st.sidebar.checkbox("Overlay points", value=True, key=f"opt_{plot_type}_points")
if plot_type == "lineplot_timecourse_with_error_band":
    mapping["error"] = st.sidebar.selectbox("Error band", ["sem", "sd", "ci95", "none"], index=0, key=f"opt_{plot_type}_error")
if plot_type == "ridge_or_density_plot":
    mapping["overlap"] = st.sidebar.slider("Ridge overlap", 0.0, 0.95, 0.7, step=0.05, key=f"opt_{plot_type}_overlap")
if plot_type == "enrichment_dotplot":
    mapping["top_n"] = st.sidebar.slider("Top N terms", 5, 40, 20, step=1, key=f"opt_{plot_type}_top_n")
if plot_type == "stacked_bar_composition":
    mapping["facet_or_sort_by"] = _column_select("sort by", "sortby", mapping.get("facet_or_sort_by"))
if plot_type == "waterfall_plot":
    mapping["sort"] = st.sidebar.selectbox("Sort", ["ascending", "descending"], index=0, key=f"opt_{plot_type}_sort")
if plot_type == "forest_plot":
    mapping["reference"] = st.sidebar.number_input("Reference line", value=1.0, step=0.5, key=f"opt_{plot_type}_reference")
    mapping["log_scale"] = st.sidebar.checkbox("Log x-axis", value=True, key=f"opt_{plot_type}_log_scale")
if plot_type == "network_graph":
    # --- Edge color: by a categorical edge column (e.g. interaction_type),
    # single fixed color, or by sign (correlation). We auto-detect a categorical
    # edge column and map it so edges actually get colored (parity with desktop).
    _cat_edge_cols = [c for c in table_info.columns
                      if c not in ("source", "target", "weight")
                      and str(table_info.dataframe[c].dtype) == "object"]
    _default_ec = next((c for c in table_info.columns
                        if c.lower() in ("interaction_type", "edge_type", "type",
                                         "pathway", "category", "sign")), None)
    _edge_mode = st.sidebar.selectbox(
        "Edge color mode", ["By category column", "Single color", "By sign (correlation)"],
        index=0 if _default_ec else 1)
    if _edge_mode == "By category column":
        _opts = _cat_edge_cols or table_info.columns[:]
        _idx = _opts.index(_default_ec) if _default_ec in _opts else 0
        _ec_col = st.sidebar.selectbox("Edge color column", _opts, index=_idx,
                                       help="Categorical edge attribute to color edges by.")
        # The renderer reads the edge category via mapping['interaction_type'];
        # setting it here is what makes Streamlit match desktop.
        mapping["interaction_type"] = _ec_col
        mapping["edge_color_by"] = _ec_col
        st.sidebar.caption(f"Edge colors: **{_ec_col}** (categorical)")
    elif _edge_mode == "Single color":
        mapping["edge_color_by"] = "none"
        mapping["edge_color"] = st.sidebar.selectbox(
            "Edge color", ["#888888", "#BBBBBB", "#333333", "black"], index=0)
    else:
        mapping["edge_color_by"] = "none"  # renderer uses +/- correlation colors
    # --- Node color: group (needs node table), numeric value, or a fixed color.
    mapping["color_by"] = st.sidebar.selectbox(
        "Color nodes by", ["group", "value", "none"], index=0,
        help="'group'/'value' need a node-attributes table; 'none' uses a single color.")
    mapping["node_color"] = st.sidebar.selectbox(
        "Node color (when 'none')",
        ["(palette)", "#2166AC", "#B2182B", "#1B7837", "#762A83", "#E08214", "#333333", "black"],
        index=0)
    mapping["layout"] = st.sidebar.selectbox(
        "Layout", ["spring", "kamada_kawai", "circular", "shell", "spectral",
                   "multipartite", "fixed", "random"], index=0)
    _ncm = st.sidebar.text_input('Custom node colors (JSON, e.g. {"g1":"#B2182B"})', value="")
    if _ncm.strip():
        mapping["node_color_map"] = _ncm.strip()
    mapping["node_labels"] = st.sidebar.checkbox("Show node labels", value=True, key=f"opt_{plot_type}_node_labels")
    mapping["show_legend"] = st.sidebar.checkbox("Show legend", value=True, key=f"opt_{plot_type}_show_legend")
# PCA needs a second metadata table mapping sample columns to attributes.
pca_aux = None
if plot_type == "pca_scatter_from_matrix":
    if source_mode == "Bundled sample":
        if bundled_aux and "metadata" in bundled_aux:
            pca_aux = bundled_aux
            st.sidebar.caption("Using the bundled example sample metadata.")
        else:
            try:
                meta_info = load_table(os.path.join(MOCK_DIR, PCA_METADATA_SAMPLE))
                pca_aux = {"metadata": meta_info.dataframe}
                st.sidebar.caption(f"Using bundled metadata: {PCA_METADATA_SAMPLE}")
            except LoaderError as exc:
                st.sidebar.error(f"Could not load PCA metadata: {exc}")
    else:
        meta_upload = st.sidebar.file_uploader(
            "PCA sample metadata (CSV/TSV)", type=["csv", "tsv", "txt"], key="pca_meta"
        )
        if meta_upload is not None:
            try:
                meta_info = load_table(meta_upload.getvalue(), source_name=meta_upload.name)
                pca_aux = {"metadata": meta_info.dataframe}
            except LoaderError as exc:
                st.sidebar.error(f"Could not load metadata: {exc}")
        else:
            st.sidebar.info("Upload a sample-metadata table to color the PCA.")

# --- 5. Layout + output -----------------------------------------------------
# --- 5. Publication style (grouped; shares the core engine with the desktop app) ---
from make_my_figure_core.styles.engine import USER_PALETTES  # noqa: E402

_STYLE_DEFAULTS = {
    "lay_width": "default", "lay_dpi": 300, "lay_ml": 0.0, "lay_mr": 0.0, "lay_mt": 0.0,
    "lay_mb": 0.0, "lay_autofix": False,
    "sty_palette": "(profile default)", "sty_title_pt": 14, "sty_axis_pt": 12, "sty_tick_pt": 10,
    "sty_annot_pt": 10, "sty_marker": 45, "sty_linew": 1.8, "sty_spine": 1.1, "sty_grid": False,
    "lab_title": "", "lab_x": "", "lab_y": "", "lay_xrot": "auto", "lay_yrot": "auto",
    "lay_xpad": 0.0, "lay_ypad": 0.0, "lay_tpad": 0.0,
    "lay_legloc": "auto", "sty_legend_pt": 10, "sty_legend_out": False,
    "lay_cbloc": "default", "lay_cbpad": 0.0, "lay_cbshrink": 1.0,
}
for _k, _v in _STYLE_DEFAULTS.items():
    st.session_state.setdefault(_k, _v)

# --- Figure preset: save this figure's configuration, apply it to new data later --------------
# A thin layer over make_my_figure_core.presets (shared with the desktop app). Applying a preset
# writes its values into the session-state keys of the controls below and reruns, so the widgets
# show what is in effect and the user can keep editing from there.
from make_my_figure_core import presets as _presets  # noqa: E402


def _preset_to_session(preset: dict, columns) -> "_presets.PresetApplyResult":
    """Stage a preset's values for the widget state keys (applied on the next run); returns the
    apply report. Values are staged rather than written because most target widgets already exist
    in this run - see the ``_preset_pending`` block at the top of the script."""
    skeleton = make_spec(plot_type, table_name, journal_style, mapping=dict(mapping))
    res = _presets.apply_preset(preset, skeleton, columns=list(columns))
    spec_ = res.spec
    staged: dict = {}
    sty = spec_.get("style") or {}
    _sty_keys = {"title_font_pt": "sty_title_pt", "axis_font_pt": "sty_axis_pt",
                 "tick_label_pt": "sty_tick_pt", "annotation_pt": "sty_annot_pt",
                 "marker_size": "sty_marker", "line_width_pt": "sty_linew",
                 "spine_width_pt": "sty_spine", "grid": "sty_grid", "legend_pt": "sty_legend_pt",
                 "legend_outside": "sty_legend_out"}
    for tok, key in _sty_keys.items():
        if tok in sty:
            staged[key] = sty[tok]
    if sty.get("palette_name"):
        staged["sty_palette"] = sty["palette_name"]
    lay = spec_.get("layout") or {}
    if lay.get("column_width"):
        staged["lay_width"] = lay["column_width"]
    for lk, key in (("x_tick_rotation", "lay_xrot"), ("y_tick_rotation", "lay_yrot")):
        if lk in lay:
            staged[key] = str(lay[lk])
    if "legend_location" in lay:
        staged["lay_legloc"] = lay["legend_location"]
    for lk, key in (("x_label_pad", "lay_xpad"), ("y_label_pad", "lay_ypad"),
                    ("title_pad", "lay_tpad"), ("margin_left", "lay_ml"),
                    ("margin_right", "lay_mr"), ("margin_top", "lay_mt"),
                    ("margin_bottom", "lay_mb")):
        if lk in lay:
            staged[key] = float(lay[lk])
    staged["lay_autofix"] = bool(lay.get("auto_fix_layout", False))
    for lk, key in (("title", "lab_title"), ("x_label", "lab_x"), ("y_label", "lab_y")):
        if lk in lay:
            staged[key] = str(lay[lk])
    out = spec_.get("output") or {}
    if out.get("dpi"):
        staged["lay_dpi"] = int(out["dpi"])
    mp = spec_.get("mapping") or {}
    for mk, key in (("colorbar_location", "lay_cbloc"), ("colorbar_pad", "lay_cbpad"),
                    ("colorbar_shrink", "lay_cbshrink")):
        if mk in mp:
            staged[key] = mp[mk]
    roles = set(_presets.role_keys(plot_type))
    for k, v in mp.items():
        if k in roles:
            if v is not None:
                staged[f"map_{k}"] = list(v) if isinstance(v, (list, tuple)) else v
        elif k in ("colorbar_location", "colorbar_pad", "colorbar_shrink"):
            continue
        else:
            staged[f"opt_{plot_type}_{k}"] = v
    st.session_state["_preset_pending"] = staged
    st.session_state["_preset_report"] = {
        "name": preset.get("name", ""), "applied": len(res.applied), "skipped": res.skipped,
        "unresolved": res.unresolved_roles, "warnings": res.warnings}
    return res


with st.sidebar.expander("Figure preset", expanded=False):
    st.caption("Save this figure's configuration and apply it to new data later. "
               "Presets never contain your data.")
    _store = _presets.PresetStore()
    try:
        _entries = _store.list(plot_type)
    except Exception as _exc:  # noqa: BLE001
        _entries, _store_err = [], str(_exc)
    else:
        _store_err = ""
    if _store_err:
        st.warning(f"Preset library unavailable: {_store_err}")
    from make_my_figure_core import experimental_presets as _xp  # noqa: E402
    from make_my_figure_core import preset_preview as _pv  # noqa: E402
    _show_exp = st.checkbox(
        "Show experimental presets", value=False, key="preset_show_experimental",
        help="Evidence-derived style presets bundled with the app (read-only). They describe visual "
             "conventions measured in published open-access figures and publishers' stated artwork "
             "requirements. Not journal templates, no endorsement; they never change data, statistics "
             "or thresholds, and always open the preview first.")
    _exp_entries = _xp.list_experimental_presets(plot_type=plot_type) if _show_exp else []
    _labels = ["(choose a preset)"] + [e.label for e in _entries] + [e.label for e in _exp_entries]
    _chosen = st.selectbox("Figure preset", _labels, key=f"preset_pick_{plot_type}")
    _entry = next((e for e in _entries if e.label == _chosen), None)
    _exp_entry = next((e for e in _exp_entries if e.label == _chosen), None)
    _any = _entry or _exp_entry
    _c0, _c1, _c2, _c3 = st.columns(4)
    if _c0.button("Preview", key="preset_preview", disabled=_any is None,
                  help="Before/after on synthetic example data and the list of changes; nothing is applied."):
        st.session_state["_preset_preview_path"] = _any.path
    if _c1.button("Apply", key="preset_apply", disabled=_entry is None,
                  help="Applies a preset from your library immediately. Experimental presets are applied "
                       "from the preview."):
        try:
            _p = _presets.load_preset(_entry.path)
            _pv.apply_with_guard(_p, make_spec(plot_type, table_name, journal_style, mapping=dict(mapping)),
                                 columns=list(table_info.columns))
            _preset_to_session(_p, table_info.columns)
            st.rerun()
        except _presets.PresetError as _exc:
            st.error(str(_exc))
    if _c2.button("Delete", key="preset_delete", disabled=_entry is None):
        _store.delete(_entry.path)
        st.rerun()
    if _entry is not None:
        try:
            _c3.download_button("Export", _presets.preset_to_json(_presets.load_preset(_entry.path)),
                                file_name=_presets.safe_filename(_entry.name) + _presets.PRESET_EXTENSION,
                                mime="application/json", key="preset_export")
        except _presets.PresetError as _exc:
            st.error(str(_exc))
    _pp = st.session_state.get("_preset_preview_path")
    if _pp:
        try:
            _pre = _presets.load_preset(_pp)
            _base = make_spec(plot_type, table_name, journal_style, mapping=dict(mapping))
            _prev = None
            try:
                # the user's own data (their groups and replicate counts), in memory only
                _prev = _pv.preview_pair(_pre, plot_type, base_spec=_base,
                                         data=(table_info.dataframe, None))
            except Exception:  # noqa: BLE001 - unmapped or aux-dependent figure: fall back
                _prev = None
            if _prev is None:
                _prev = _pv.preview_pair(_pre, plot_type, base_spec={"style": _base.get("style"),
                                                                     "layout": _base.get("layout"),
                                                                     "output": _base.get("output")})
        except (_presets.PresetError, KeyError, ValueError) as _exc:
            st.error(f"Cannot preview: {_exc}")
            _prev = None
        if _prev is not None:
            st.markdown(f"**Preview: {_pre.get('name', '')}**")
            _pc1, _pc2 = st.columns(2)
            _pc1.image(_prev.before_png, caption="Current settings", use_container_width=True)
            _pc2.image(_prev.after_png, caption="With this preset", use_container_width=True)
            st.caption(_prev.synthetic_data_notice)
            if _prev.changes:
                st.table([{"setting": c.label, "now": repr(c.old), "preset": repr(c.new)} for c in _prev.changes])
            else:
                st.caption("No setting would change.")
            if _prev.apply_result.skipped:
                st.caption(f"{len(_prev.apply_result.skipped)} setting(s) do not apply to this plot type.")
            if _xp.is_experimental(_pre):
                st.info(_xp.provenance_text(_pre))
            if _prev.safe_to_apply:
                st.success("Checked: no data, column role, statistical test, threshold or transformation changes.")
            else:
                st.error("Refused: this preset would change analytical settings ("
                         + ", ".join(_prev.protected_violations) + "). It cannot be applied.")
            _a1, _a2 = st.columns(2)
            if _a1.button("Apply this preset", key="preset_preview_apply", disabled=not _prev.safe_to_apply):
                try:
                    _pv.apply_with_guard(_pre, _base, columns=list(table_info.columns))
                    _preset_to_session(_pre, table_info.columns)
                    st.session_state.pop("_preset_preview_path", None)
                    st.rerun()
                except _presets.PresetError as _exc:
                    st.error(str(_exc))
            if _a2.button("Cancel", key="preset_preview_cancel"):
                st.session_state.pop("_preset_preview_path", None)
                st.rerun()
            if _xp.is_experimental(_pre):
                _lab_name = st.text_input("Save as my preset (name)", value=f"{_pre.get('name', 'preset')} (lab copy)",
                                          key="preset_lab_copy_name")
                if st.button("Save as my preset", key="preset_lab_copy_save"):
                    try:
                        _store.save(_xp.clone_for_lab(_pre, name=_lab_name))
                        st.success(f"Saved “{_lab_name}” to your preset library.")
                    except _presets.PresetError as _exc:
                        st.error(str(_exc))
    _rep = st.session_state.pop("_preset_report", None)
    if _rep:
        st.success(f"Applied “{_rep['name']}”: {_rep['applied']} setting(s).")
        if _rep["unresolved"]:
            st.warning("The preset named columns this table does not have - nothing was "
                       "substituted. Choose a column for: "
                       + ", ".join(f"{r} (wanted {w!r})" for r, w in _rep["unresolved"].items()))
        for _w in _rep["warnings"]:
            if "universal settings" in _w:
                st.info(_w)
        if _rep["skipped"]:
            st.caption(f"{len(_rep['skipped'])} setting(s) do not apply to this plot type.")
    with st.form("preset_save_form", clear_on_submit=False):
        st.markdown("**Save preset**")
        _pname = st.text_input("Preset name", value=f"{display_name(plot_type)} preset")
        _pmode = st.radio("Save", ["Figure style only", "Full figure configuration"],
                          help="Style: fonts, colours, layout, legend, export - portable to any data "
                               "of this plot type. Full: also column roles, thresholds, labels and "
                               "statistics; asks for remapping on new data.")
        if st.form_submit_button("Save"):
            st.session_state["_preset_save_request"] = {
                "name": _pname.strip() or f"{display_name(plot_type)} preset",
                "mode": "style" if _pmode.startswith("Figure style") else "full"}
    _imp = st.file_uploader("Import preset", type=["json"], key="preset_import")
    if _imp is not None and st.session_state.get("_preset_imported") != _imp.name:
        try:
            _store.save(_presets.load_preset_bytes(_imp.getvalue(), name=_imp.name.split(".")[0]))
            st.session_state["_preset_imported"] = _imp.name
            st.rerun()
        except _presets.PresetError as _exc:
            st.error(str(_exc))
    if st.button("Reset to Publication defaults", key="preset_reset"):
        st.session_state["_preset_pending"] = dict(_STYLE_DEFAULTS)
        st.rerun()

# Every control below carries a session-state key so a Figure preset can set it (see the
# "Figure preset" expander above). Defaults are seeded once, and the widgets are created without
# an explicit value, which is the pattern Streamlit expects when state is written programmatically.

st.sidebar.header("5. Publication style")
style_overrides = {}
_layout_controls = {}

# ① Figure — dimensions, DPI, margins, auto layout.
with st.sidebar.expander("① Figure", expanded=False):
    column_width = st.selectbox("Figure width preset",
                                ["default", "single", "onehalf", "double"], key="lay_width")
    dpi = st.slider("Raster DPI (PNG/TIFF)", 150, 600, step=50, key="lay_dpi")
    _ml = st.slider("Left margin (0 = auto)", 0.0, 0.5, step=0.02, key="lay_ml")
    _mr = st.slider("Right margin (0 = auto)", 0.0, 0.5, step=0.02, key="lay_mr")
    _mt = st.slider("Top margin (0 = auto)", 0.0, 0.5, step=0.02, key="lay_mt")
    _mb = st.slider("Bottom margin (0 = auto)", 0.0, 0.5, step=0.02, key="lay_mb")
    _autofix = st.checkbox("Auto-fix layout (prevent clipping)", key="lay_autofix")

# ② Typography — palette, fonts/sizes, marks.
with st.sidebar.expander("② Typography", expanded=False):
    # Only the curated, user-facing palettes — never the internal journal-named
    # entries kept in NAMED_PALETTES for backward compatibility.
    pal = st.selectbox("Palette", ["(profile default)"] + list(USER_PALETTES), key="sty_palette")
    if pal != "(profile default)":
        style_overrides["palette_name"] = pal
    style_overrides["title_font_pt"] = st.slider("Title pt", 8, 28, key="sty_title_pt")
    style_overrides["axis_font_pt"] = st.slider("Axis label pt", 8, 24, key="sty_axis_pt")
    style_overrides["tick_label_pt"] = st.slider("Tick label pt", 6, 20, key="sty_tick_pt")
    style_overrides["annotation_pt"] = st.slider("Annotation pt", 6, 20, key="sty_annot_pt")
    style_overrides["marker_size"] = st.slider("Marker size", 6, 200, key="sty_marker")
    style_overrides["line_width_pt"] = st.slider("Line width", 0.5, 6.0, step=0.1, key="sty_linew")
    style_overrides["regression_line_width"] = style_overrides["line_width_pt"]
    style_overrides["spine_width_pt"] = st.slider("Axis/spine width", 0.4, 4.0, step=0.1,
                                                  key="sty_spine")
    style_overrides["grid"] = st.checkbox("Grid", key="sty_grid")

# ③ Axes & labels — titles, tick rotation, padding.
with st.sidebar.expander("③ Axes & labels", expanded=False):
    title = st.text_input("Title", key="lab_title")
    x_label = st.text_input("X label (blank = auto)", key="lab_x")
    y_label = st.text_input("Y label (blank = auto)", key="lab_y")
    _xr = st.selectbox("X tick angle", ["auto", "0", "45", "90"], key="lay_xrot")
    _yr = st.selectbox("Y tick angle", ["auto", "0", "45", "90"], key="lay_yrot")
    _xpad = st.slider("X label padding", 0.0, 30.0, step=1.0, key="lay_xpad")
    _ypad = st.slider("Y label padding", 0.0, 30.0, step=1.0, key="lay_ypad")
    _tpad = st.slider("Title padding", 0.0, 30.0, step=1.0, key="lay_tpad")

# ④ Legend — location, size, inside/outside.
with st.sidebar.expander("④ Legend", expanded=False):
    _legloc = st.selectbox("Location",
                           ["auto", "inside upper right", "inside upper left",
                            "inside lower right", "inside lower left", "outside right",
                            "outside left", "outside top", "outside bottom"], key="lay_legloc")
    style_overrides["legend_pt"] = st.slider("Legend pt", 6, 20, key="sty_legend_pt")
    style_overrides["legend_outside"] = st.checkbox("Legend outside plot", key="sty_legend_out")

# ⑤ Colorbar — heatmap / clustering / confusion / enrichment only.
with st.sidebar.expander("⑤ Colorbar", expanded=False):
    _cbloc = st.selectbox("Location", ["default", "right", "left", "top", "bottom"], key="lay_cbloc")
    _cbpad = st.slider("Padding (0 = default)", 0.0, 0.4, step=0.02, key="lay_cbpad")
    _cbshrink = st.slider("Size", 0.3, 1.0, step=0.1, key="lay_cbshrink")
    st.caption("Applies to heatmap, clustered heatmap, confusion matrix, enrichment dot.")

# Assemble the shared layout controls (applied to every plot by the layout engine).
if _xr != "auto":
    _layout_controls["x_tick_rotation"] = int(_xr)
if _yr != "auto":
    _layout_controls["y_tick_rotation"] = int(_yr)
if _legloc != "auto":
    _layout_controls["legend_location"] = _legloc
for _k, _v in (("margin_left", _ml), ("margin_right", _mr), ("margin_top", _mt),
               ("margin_bottom", _mb)):
    if _v > 0:
        _layout_controls[_k] = _v
if _xpad > 0:
    _layout_controls["x_label_pad"] = _xpad
if _ypad > 0:
    _layout_controls["y_label_pad"] = _ypad
if _tpad > 0:
    _layout_controls["title_pad"] = _tpad
if _autofix:
    _layout_controls["auto_fix_layout"] = True
# Colorbar controls are read from the mapping by colorbar-capable renderers.
if _cbloc != "default":
    mapping["colorbar_location"] = _cbloc
if _cbpad > 0:
    mapping["colorbar_pad"] = _cbpad
if _cbshrink < 1.0:
    mapping["colorbar_shrink"] = _cbshrink

# Any remaining registered option for this plot type, rendered from ui_hints.
#
# The hand-written widgets elsewhere cover the options this app has always offered. This fills in
# the rest, so an option added to the shared registry reaches the browser app as well as the
# desktop one instead of being reachable only by hand-editing a PlotSpec.
#
# It deliberately runs after EVERY other section that writes into `mapping` - the per-plot
# options, the publication-style controls and the colorbar controls all do - and skips any key
# already set. Placing it earlier rendered a second widget for keys a later section then
# overwrote, and an exclusion list would drift out of date, which is the duplication this change
# is removing in the first place.
# Keys that already have a dedicated widget in another section. Most per-plot options are
# detected by simply being present in `mapping`, but these are set into `_layout_controls`
# instead, or written only when moved off their default, so they would otherwise be offered a
# second time under the registry's own label - "X-axis label angle" beside the existing
# "X tick angle", or "Colorbar location" beside the ⑤ Colorbar expander's "Location".
_OPTIONS_OWNED_ELSEWHERE = {
    "x_tick_rotation", "y_tick_rotation", "y_label_rotation",   # ⑤ Axis labels
    "legend_location",                                          # ⑤ Legend
    "colorbar_location", "colorbar_pad", "colorbar_shrink",      # ⑤ Colorbar
}
_generic_opts = [o for o in ui_hints.options(plot_type)
                 if o.key not in mapping and o.key not in _OPTIONS_OWNED_ELSEWHERE]
if _generic_opts:
    for _o in _generic_opts:
        _label = _o.label or _o.key
        if _o.kind == "choice" and _o.choices:
            _default = _o.default if _o.default in _o.choices else _o.choices[0]
            mapping[_o.key] = st.sidebar.selectbox(
                _label, list(_o.choices), index=list(_o.choices).index(_default),
                key=f"opt_{plot_type}_{_o.key}")
        elif _o.kind == "bool":
            mapping[_o.key] = st.sidebar.checkbox(
                _label, value=bool(_o.default), key=f"opt_{plot_type}_{_o.key}")
        elif _o.kind == "number":
            # A number option with no default is optional: an empty box must stay unset rather
            # than silently becoming a value the user never chose.
            if _o.default is None:
                _raw = st.sidebar.text_input(_label, value="",
                                             key=f"opt_{plot_type}_{_o.key}")
                if str(_raw).strip():
                    try:
                        mapping[_o.key] = float(_raw)
                    except ValueError:
                        st.sidebar.warning(f"{_label}: '{_raw}' is not a number — ignored.")
            else:
                _kw = {}
                if _o.minimum is not None:
                    _kw["min_value"] = float(_o.minimum)
                if _o.maximum is not None:
                    _kw["max_value"] = float(_o.maximum)
                if _o.step is not None:
                    _kw["step"] = float(_o.step)
                mapping[_o.key] = st.sidebar.number_input(
                    _label, value=float(_o.default), key=f"opt_{plot_type}_{_o.key}", **_kw)

# Honest, plot-aware note: flag controls that don't apply to the active plot instead
# of silently ignoring them (plot-specific colors live in the per-plot options above).
from make_my_figure_core.styles.capabilities import (  # noqa: E402
    warn_ignored_style_controls)
_ignored = warn_ignored_style_controls(plot_type, style_overrides)
if _ignored:
    st.sidebar.caption("ⓘ Not applicable to **" + plot_type.replace("_", " ") + "**: "
                       + " ".join(_ignored))

# --- 6. Statistics (shares the core statistics engine with the desktop app) --
from make_my_figure_core.statistics import TESTS as _STAT_TESTS  # noqa: E402
from make_my_figure_core.statistics import recommend_tests as _recommend  # noqa: E402

st.sidebar.header("6. Statistics")
stats_spec = {"enabled": False}
with st.sidebar.expander("Statistical tests & annotations", expanded=False):
    stats_enabled = st.checkbox("Enable statistics", value=False)
    _cols = list(table_info.dataframe.columns)
    _test_ids = ["auto"] + list(_STAT_TESTS.keys())
    _test_labels = {"auto": "Auto-suggest", **{t: i.label for t, i in _STAT_TESTS.items()}}
    try:
        _rec = _recommend(plot_type, mapping, df=table_info.dataframe)
        if _rec.get("notes"):
            st.caption("Advisory: " + " ".join(_rec["notes"]))
    except Exception:
        pass
    test = st.selectbox("Test", _test_ids, format_func=lambda t: _test_labels.get(t, t))
    comparison_mode = st.selectbox(
        "Comparison", ["auto", "all_pairs", "vs_control", "within_x", "omnibus"])
    correction = st.selectbox(
        "Correction", ["benjamini_hochberg", "bonferroni", "holm", "none"])
    ann_mode = st.selectbox("Annotation", ["stars", "p", "both"])
    ann_placement = st.selectbox(
        "Annotation placement", ["bracket", "above_bar"],
        help="'bracket' spans the two compared categories. 'above_bar' puts one label over each "
             "compared bar and leaves the control bar unmarked — the usual convention when every "
             "condition is tested against one control, where brackets would stack up and squeeze "
             "the bars. Needs a control group; anything it cannot place falls back to a bracket.")
    show_effect = st.checkbox("Show effect size on figure", value=False)
    posthoc = st.checkbox("Post-hoc pairwise after omnibus", value=False)
    _none = "(none)"
    group_column = st.selectbox("Group column", [_none] + _cols)
    subgroup_column = st.selectbox("Subgroup column", [_none] + _cols)
    subject_column = st.selectbox("Subject/pair ID", [_none] + _cols)
    reference_group = st.text_input("Control group (for vs-control)", value="")
    if stats_enabled:
        stats_spec = {
            "enabled": True, "test": test, "comparison_mode": comparison_mode,
            "correction": correction, "posthoc": posthoc,
            "group_column": None if group_column == _none else group_column,
            "subgroup_column": None if subgroup_column == _none else subgroup_column,
            "subject_column": None if subject_column == _none else subject_column,
            "reference_group": reference_group or None,
            "annotate": True,
            "annotation": {"mode": ann_mode, "show_effect": show_effect,
                           "placement": ann_placement},
        }

# No plot chosen yet: show the empty-state and stop before building a spec (parity
# with the desktop placeholder — nothing is rendered until a real plot is picked).
if plot_type == PLOT_TYPE_PLACEHOLDER:
    from make_my_figure_core.ui_strings import EMPTY_STATE_MESSAGE  # noqa: E402
    st.subheader("Figure preview")
    st.info(EMPTY_STATE_MESSAGE)
    st.stop()

layout = dict(_layout_controls)   # shared tick/legend/margin controls
if title:
    layout["title"] = title
if x_label:
    layout["x_label"] = x_label
if y_label:
    layout["y_label"] = y_label

style = load_profile(journal_style)
w_mm = style.figure_size_inches(column_width)[0] * 25.4

# Matrix-Workflow handoff: apply suggested option defaults for options that have no
# dedicated widget (e.g. heatmap z-score scale), and use the handoff's provenance/aux.
_handoff_defaults = st.session_state.get("_handoff_defaults") or {}
for _k, _v in _handoff_defaults.items():
    mapping.setdefault(_k, _v)
_handoff_source = st.session_state.get("_handoff_source")
_handoff_extra = st.session_state.get("_handoff_spec_extra") or {}
_source_prov = _handoff_source or (table_info.provenance() or None)
spec = make_spec(
    plot_type,
    table_name,
    journal_style,
    mapping=mapping,
    layout=layout or None,
    output=default_output_block(["svg", "png", "pdf"], width_mm=w_mm, dpi=dpi),
    source=_source_prov,
)
for _k, _v in _handoff_extra.items():   # e.g. column_annotations (group strip)
    spec[_k] = _v
spec["layout"] = {**spec.get("layout", {}), "column_width": column_width}
spec["style"] = style_overrides
if stats_spec.get("enabled"):
    spec["statistics"] = stats_spec
    if _source_prov:
        spec["statistics"].setdefault("source", dict(_source_prov))

# A "Save preset" submitted in the sidebar is fulfilled here, from the fully assembled spec.
_save_req = st.session_state.pop("_preset_save_request", None)
if _save_req:
    try:
        _saved = _presets.extract_preset(spec, mode=_save_req["mode"], name=_save_req["name"])
        _presets.PresetStore().save(_saved)
        st.sidebar.success(f"Saved preset “{_save_req['name']}”.")
        st.sidebar.download_button(
            "Download the saved preset", _presets.preset_to_json(_saved),
            file_name=_presets.safe_filename(_save_req["name"]) + _presets.PRESET_EXTENSION,
            mime="application/json", key="preset_download_saved")
    except _presets.PresetError as _exc:
        st.sidebar.error(f"Could not save preset: {_exc}")


# --- Render + preview -------------------------------------------------------
st.subheader("Figure preview")
try:
    # Aux tables (node attributes for networks, sample metadata for PCA). Networks
    # previously got no aux in Streamlit, so `color_by=group` had no node groups and
    # collapsed to one color — desktop passed it, hence the discrepancy.
    render_aux = pca_aux
    if plot_type == "network_graph" and bundled_aux:
        render_aux = bundled_aux
    _handoff_aux = st.session_state.get("_handoff_aux")
    if _handoff_aux:   # e.g. PCA sample metadata prepared by the Matrix Workflow
        render_aux = _handoff_aux
    result = render(spec, table_info.dataframe, style=style, aux=render_aux)
    fig = result.figure
    st.pyplot(fig, use_container_width=False)
    check = result.metadata.get("publication_check", {})
    if check.get("passed", True):
        st.success(check.get("summary", "Publication check: passed"))
    else:
        st.warning(check.get("summary", "Publication check found issues"))
    for w in result.warnings:
        st.warning(w)

    # --- Publication QC (scored readiness) ---------------------------------
    with st.expander("✅ Publication QC — ready-to-export checks", expanded=False):
        from make_my_figure_core.qc import score_publication as _score_pub

        _score = _score_pub(result=result, spec=spec,
                            stats_report=getattr(result, "stats_report", None))
        _emoji = {"pass": "🟢", "warn": "🟡", "fail": "🔴"}.get(_score.level, "⚪")
        st.markdown(f"{_emoji} **{_score.level.upper()}** — score {_score.score}/100. {_score.summary}")
        _issues = _score.issues() if hasattr(_score, "issues") else _score.checks
        for _c in _issues:
            _ic = {"fail": "✗", "warn": "⚠", "pass": "✓"}.get(getattr(_c, "level", "warn"), "•")
            st.markdown(f"{_ic} **{getattr(_c, 'message', '')}**  \n"
                        f"<span style='color:#666'>{getattr(_c, 'suggestion', '')}</span>",
                        unsafe_allow_html=True)
        if not _issues:
            st.caption("No publication-readiness issues detected.")

    # --- Statistics results -------------------------------------------------
    stats_report = getattr(result, "stats_report", None)
    if stats_report is not None and stats_report.results:
        st.subheader("Statistics")
        import pandas as _pd

        from apps.desktop_app.controller import DesktopController as _DC

        _rows = _DC().stats_table_rows(stats_report)
        st.dataframe(_pd.DataFrame(_rows), use_container_width=True)
        st.caption("Method: " + stats_report.method_paragraph)
        if stats_report.warnings:
            for _w in stats_report.warnings:
                st.warning(_w)
        from make_my_figure_core.statistics.schemas import stats_sidecar_payload as _ssp

        st.download_button(
            "StatsSpec JSON",
            json.dumps(_ssp(spec.get("statistics", {}), stats_report), indent=2).encode("utf-8"),
            file_name=f"{workbook_io.output_basename(_prov.get('source_workbook_name') or table_name, _prov.get('source_sheet_name'), plot_type)}.stats_spec.json",
            mime="application/json",
        )
    elif stats_spec.get("enabled"):
        st.info("Statistics enabled but no results were produced. Check the group/column "
                "selection and the advisory notes above.")

    with st.expander("Render metadata"):
        st.json(result.metadata)

    # --- 6. Exports ---------------------------------------------------------
    st.subheader("Export")

    def _fig_bytes(fmt: str) -> bytes:
        # Route through the registry so vector exports keep text as editable text
        # (svg.fonttype none / Type 42 fonts), exactly like the desktop export path.
        from make_my_figure_core.plots.registry import figure_to_bytes as _to_bytes

        return _to_bytes(fig, fmt, dpi=dpi)

    # Sheet-aware base name so exports from different worksheets never collide
    # (e.g. Sol_24M_vs_6M_volcano vs Gas_24M_vs_6M_volcano).
    base = workbook_io.output_basename(
        _prov.get("source_workbook_name") or table_name,
        _prov.get("source_sheet_name"), plot_type)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.download_button("SVG", _fig_bytes("svg"), file_name=f"{base}.svg", mime="image/svg+xml")
    c2.download_button("PNG", _fig_bytes("png"), file_name=f"{base}.png", mime="image/png")
    c3.download_button("PDF", _fig_bytes("pdf"), file_name=f"{base}.pdf", mime="application/pdf")
    sidecar = {
        "plot_spec": spec,
        "render_metadata": {k: v for k, v in result.metadata.items() if k != "spec"},
    }
    c4.download_button(
        "PlotSpec JSON",
        json.dumps(sidecar, indent=2).encode("utf-8"),
        file_name=f"{base}.plot_spec.json",
        mime="application/json",
        help="Specification only — the source data are required to reopen it.",
    )
    # --- reproducible figure package: specification + frozen data + records in ONE file ---
    from make_my_figure_core.package import (
        ARTIFACT_DESCRIPTIONS as _ART,
        PACKAGE_EXTENSION as _PKG_EXT,
        PRIVACY_NOTICE as _PKG_PRIVACY,
        MatrixContext as _MatrixContext,
        build_package_bytes as _build_pkg,
        content_for_single_plot as _content_single,
        table_digest as _table_digest,
    )

    _mc = None
    if (_source_prov or {}).get("source_workflow") == "matrix" and st.session_state.get("mw_raw_matrix_df") is not None:
        _mc = _MatrixContext(
            source_dataframe=st.session_state.get("mw_raw_matrix_df"),
            source_name=st.session_state.get("mw_raw_matrix_name"),
            source_provenance=st.session_state.get("_mw_source_prov") or None,
            matrix_spec=st.session_state.get("mw_processed_spec") or st.session_state.get("mw_raw_matrix_spec"),
            sample_metadata_spec=st.session_state.get("mw_meta_spec"),
            preprocessing_spec=st.session_state.get("mw_prep_spec"))
    _pkg_spec = json.loads(json.dumps(spec))
    _pkg_spec["source"] = {**(_pkg_spec.get("source") or {}),
                           "source_table_sha256": _table_digest(table_info.dataframe),
                           "source_table_shape": [int(table_info.dataframe.shape[0]), int(table_info.dataframe.shape[1])]}
    try:
        _content = _content_single(_pkg_spec, table_info.dataframe, result, table_name=table_name,
                                   aux=render_aux, provenance=_prov or None, matrix=_mc, name=base, preview_dpi=dpi)
        if _upload_raw is not None and _content.tables and _content.tables[0].role == "source_table" and _mc is None:
            _content.tables[0].original_bytes = _upload_raw
            _content.tables[0].original_filename = _upload_name
            _content.tables[0].sheet_name = (_prov or {}).get("source_sheet_name")
        _pkg_bytes, _pkg_manifest, _pkg_warn = _build_pkg(_content)
        c5.download_button(
            "Figure Package", _pkg_bytes, file_name=f"{base}{_PKG_EXT}", mime="application/zip",
            help=_ART["figure_package"] + "\n\n" + _PKG_PRIVACY,
        )
        st.caption(f"**Figure package** ({len(_pkg_bytes) / 1024 ** 2:.2f} MB): {_ART['figure_package']} "
                   "Figure packages include the data required to reproduce the figure.")
        for _w in _pkg_warn:
            st.caption("Package note: " + _w)
    except Exception as _exc:  # noqa: BLE001
        c5.caption(f"Figure package unavailable: {_exc}")

except (RenderError, SpecValidationError) as exc:
    st.error(f"Could not render figure: {exc}")
except Exception as exc:  # surface unexpected errors instead of failing silently
    st.error(f"Unexpected error: {exc}")

st.divider()
st.caption(
    "Replace mock data with your own: keep the required column names from "
    "`mock_data/plot_schema_manifest.json`, or remap columns in the sidebar. "
    "Validate by column name and type — column order does not matter."
)
