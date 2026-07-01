"""Make My Figure — Streamlit dashboard (Milestone 1).

Flow:
1. Upload a CSV/TSV/XLSX file (or load a bundled sample table).
2. Preview and validate the table.
3. Choose a plot type and map columns.
4. Choose a journal-like style profile (Nature-like / Science-like / Cell-like).
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

matplotlib.use("Agg")  # headless backend for server-side rendering

# Make the package importable when run via
# `streamlit run apps/streamlit_app/streamlit_app.py`.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import streamlit as st

from make_my_figure_core.io.loaders import LoaderError, load_table
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
COLUMN_FIELDS = {
    "barplot_with_error_bar": ["x", "y", "color"],
    "grouped_barplot_with_error_bar": ["x", "group", "y"],
    "heatmap_clustered_matrix": ["row_id"],
    "volcano_plot": ["x", "p", "label"],
    "scatterplot_with_regression": ["x", "y", "color", "label"],
    "boxplot_or_violin_with_points": ["x", "y"],
    "lineplot_timecourse_with_error_band": ["x", "y", "color"],
    "ridge_or_density_plot": ["x", "group"],
    "enrichment_dotplot": ["y", "x", "size", "color"],
    "kaplan_meier_survival_curve": ["time", "event", "group"],
    "stacked_bar_composition": ["x", "stack", "y", "facet_or_sort_by"],
    "waterfall_plot": ["x", "y", "color"],
    "pca_scatter_from_matrix": ["matrix_row_id", "color", "shape"],
    "oncoprint_mutation_heatmap": ["sample", "row", "fill"],
    "lollipop_mutation_plot": ["x", "y", "color", "label"],
    "roc_curve": ["label", "score", "score2"],
    "forest_plot": ["label", "estimate", "lower", "upper"],
}


st.set_page_config(page_title="Make My Figure", layout="wide")
st.title("Make My Figure")
st.caption(
    "Manuscript-style figures with Nature-like / Science-like / Cell-like aesthetics. "
    "These are *-like style profiles only — not official journal templates, and not a "
    "guarantee of submission compliance."
)


# --- 1. Data source ---------------------------------------------------------
st.sidebar.header("1. Data")
source_mode = st.sidebar.radio("Data source", ["Bundled sample", "Upload file"])

table_info = None
table_name = None
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
    default_plot_type = available_plot_types()[0]
    if uploaded is not None:
        try:
            data = uploaded.getvalue()
            table_info = load_table(data, source_name=uploaded.name)
            table_name = uploaded.name
        except LoaderError as exc:
            st.sidebar.error(f"Could not load file: {exc}")

if table_info is None:
    st.info("Choose a bundled sample or upload a data file to begin.")
    st.stop()

# --- Table preview + validation messages ------------------------------------
st.subheader(f"Table preview — {table_name}")
st.dataframe(table_info.dataframe.head(20), use_container_width=True)
cols = st.columns(3)
cols[0].metric("Rows", table_info.n_rows)
cols[1].metric("Columns", len(table_info.columns))
cols[2].metric("Numeric columns", len(table_info.numeric_columns))
if table_info.warnings:
    for w in table_info.warnings:
        st.warning(w)


# --- 2. Plot type + 3. style ------------------------------------------------
st.sidebar.header("2. Plot type")
plot_type = st.sidebar.selectbox(
    "Plot type",
    options=available_plot_types(),
    index=available_plot_types().index(default_plot_type) if default_plot_type in available_plot_types() else 0,
    format_func=display_name,
)

st.sidebar.header("3. Style profile")
profiles = list_profiles()
journal_style = st.sidebar.selectbox("Journal-like style", options=profiles)

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


for field in COLUMN_FIELDS.get(plot_type, []):
    mapping[field] = _column_select(field, field, mapping.get(field))

# Plot-type-specific options.
if plot_type in ("barplot_with_error_bar", "grouped_barplot_with_error_bar"):
    mapping["error"] = st.sidebar.selectbox("Error bar", ["sem", "sd", "ci95", "none"], index=0)
if plot_type == "heatmap_clustered_matrix":
    mapping["cluster_rows"] = st.sidebar.checkbox("Cluster rows", value=True)
    mapping["cluster_columns"] = st.sidebar.checkbox("Cluster columns", value=True)
    mapping["color_scale"] = st.sidebar.selectbox("Color scale", ["diverging", "sequential"], index=0)
if plot_type == "volcano_plot":
    mapping["lfc_cutoff"] = st.sidebar.number_input("log2FC cutoff", value=1.0, step=0.5)
    mapping["p_cutoff"] = st.sidebar.number_input("p-value cutoff", value=0.05, step=0.01, format="%.3f")
if plot_type == "scatterplot_with_regression":
    mapping["fit_line"] = st.sidebar.checkbox("Fit regression line", value=True)
if plot_type == "boxplot_or_violin_with_points":
    mapping["kind"] = st.sidebar.selectbox("Kind", ["box", "violin"], index=0)
    mapping["points"] = st.sidebar.checkbox("Overlay points", value=True)
if plot_type == "lineplot_timecourse_with_error_band":
    mapping["error"] = st.sidebar.selectbox("Error band", ["sem", "sd", "ci95", "none"], index=0)
if plot_type == "ridge_or_density_plot":
    mapping["overlap"] = st.sidebar.slider("Ridge overlap", 0.0, 0.95, 0.7, step=0.05)
if plot_type == "enrichment_dotplot":
    mapping["top_n"] = st.sidebar.slider("Top N terms", 5, 40, 20, step=1)
if plot_type == "stacked_bar_composition":
    mapping["facet_or_sort_by"] = _column_select("sort by", "sortby", mapping.get("facet_or_sort_by"))
if plot_type == "waterfall_plot":
    mapping["sort"] = st.sidebar.selectbox("Sort", ["ascending", "descending"], index=0)
if plot_type == "forest_plot":
    mapping["reference"] = st.sidebar.number_input("Reference line", value=1.0, step=0.5)
    mapping["log_scale"] = st.sidebar.checkbox("Log x-axis", value=True)

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
st.sidebar.header("5. Labels & size")
title = st.sidebar.text_input("Title", value="")
x_label = st.sidebar.text_input("X label (blank = auto)", value="")
y_label = st.sidebar.text_input("Y label (blank = auto)", value="")
column_width = st.sidebar.selectbox("Figure width", ["single", "double"], index=0)
dpi = st.sidebar.slider("Raster DPI (PNG/TIFF)", 150, 600, 300, step=50)

layout = {}
if title:
    layout["title"] = title
if x_label:
    layout["x_label"] = x_label
if y_label:
    layout["y_label"] = y_label

style = load_profile(journal_style)
width = "double" if column_width == "double" else "single"
w_mm = style.double_column_width_mm if width == "double" else style.single_column_width_mm

spec = make_spec(
    plot_type,
    table_name,
    journal_style,
    mapping=mapping,
    layout=layout or None,
    output=default_output_block(["svg", "png", "pdf"], width_mm=w_mm, dpi=dpi),
)
# Pass the requested column width through to renderers via statistics-free hook.
spec["layout"] = {**spec.get("layout", {}), "column_width": width}


# --- Render + preview -------------------------------------------------------
st.subheader("Figure preview")
try:
    result = render(spec, table_info.dataframe, style=style, aux=pca_aux)
    fig = result.figure
    st.pyplot(fig, use_container_width=False)
    for w in result.warnings:
        st.warning(w)

    with st.expander("Render metadata"):
        st.json(result.metadata)

    # --- 6. Exports ---------------------------------------------------------
    st.subheader("Export")

    def _fig_bytes(fmt: str) -> bytes:
        buf = io.BytesIO()
        save_kwargs = {"format": fmt, "bbox_inches": "tight"}
        if fmt in ("png", "tiff"):
            save_kwargs["dpi"] = dpi
        fig.savefig(buf, **save_kwargs)
        return buf.getvalue()

    base = os.path.splitext(table_name)[0] + f"_{plot_type}"
    c1, c2, c3, c4 = st.columns(4)
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
    )

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
