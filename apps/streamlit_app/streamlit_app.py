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
    "Manuscript-ready scientific figures in a single, polished Publication style. "
    "This is a general publication-ready visual style — not an official journal "
    "template, and not a guarantee of submission compliance."
)


# --- 1. Data source ---------------------------------------------------------
# --- App navigation: reset / upload new data --------------------------------
# Streamlit reruns top-to-bottom, so "return to upload" clears session state
# (dataset, mappings, stats, RNA-seq) and reruns to a clean upload state.
if st.sidebar.button("🏠 Reset / Upload new data", use_container_width=True,
                     help="Clear the current dataset, plot, statistics, and RNA-seq "
                          "results and return to a clean upload state (no restart)."):
    for _k in list(st.session_state.keys()):
        del st.session_state[_k]
    st.rerun()

st.sidebar.divider()
st.sidebar.header("1. Data")
source_mode = st.sidebar.radio("Data source",
                               ["Bundled sample", "Upload file", "Open PlotSpec"])

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
        guess = _guess_groups(sample_cols)
        assign_df = pd.DataFrame({"sample": sample_cols,
                                  "group": [guess.get(s, "Group1") for s in sample_cols]})
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
st.sidebar.header("2. Plot type")
plot_type = st.sidebar.selectbox(
    "Plot type",
    options=available_plot_types(),
    index=available_plot_types().index(default_plot_type) if default_plot_type in available_plot_types() else 0,
    format_func=display_name,
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
column_width = st.sidebar.selectbox("Figure width", ["default", "single", "onehalf", "double"], index=0)
dpi = st.sidebar.slider("Raster DPI (PNG/TIFF)", 150, 600, 300, step=50)

# --- 6. Formatting (shares the core style engine with the desktop app) -------
from make_my_figure_core.styles.engine import NAMED_PALETTES  # noqa: E402

st.sidebar.header("6. Formatting")
style_overrides = {}
with st.sidebar.expander("Publication style controls", expanded=False):
    pal = st.selectbox("Palette", ["(profile default)"] + list(NAMED_PALETTES))
    if pal != "(profile default)":
        style_overrides["palette_name"] = pal
    style_overrides["axis_font_pt"] = st.slider("Axis label pt", 8, 24, 12)
    style_overrides["tick_label_pt"] = st.slider("Tick label pt", 6, 20, 10)
    style_overrides["legend_pt"] = st.slider("Legend pt", 6, 20, 10)
    style_overrides["annotation_pt"] = st.slider("Annotation pt", 6, 20, 10)
    style_overrides["marker_size"] = st.slider("Marker size", 6, 200, 45)
    style_overrides["line_width_pt"] = st.slider("Line width", 0.5, 6.0, 1.8, 0.1)
    style_overrides["regression_line_width"] = style_overrides["line_width_pt"]
    style_overrides["spine_width_pt"] = st.slider("Axis/spine width", 0.4, 4.0, 1.1, 0.1)
    style_overrides["legend_outside"] = st.checkbox("Legend outside plot", value=False)
    style_overrides["grid"] = st.checkbox("Grid", value=False)

# --- 7. Statistics (shares the core statistics engine with the desktop app) --
from make_my_figure_core.statistics import TESTS as _STAT_TESTS  # noqa: E402
from make_my_figure_core.statistics import recommend_tests as _recommend  # noqa: E402

st.sidebar.header("7. Statistics")
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
            "annotation": {"mode": ann_mode, "show_effect": show_effect},
        }

layout = {}
if title:
    layout["title"] = title
if x_label:
    layout["x_label"] = x_label
if y_label:
    layout["y_label"] = y_label

style = load_profile(journal_style)
w_mm = style.figure_size_inches(column_width)[0] * 25.4

spec = make_spec(
    plot_type,
    table_name,
    journal_style,
    mapping=mapping,
    layout=layout or None,
    output=default_output_block(["svg", "png", "pdf"], width_mm=w_mm, dpi=dpi),
)
spec["layout"] = {**spec.get("layout", {}), "column_width": column_width}
spec["style"] = style_overrides
if stats_spec.get("enabled"):
    spec["statistics"] = stats_spec


# --- Render + preview -------------------------------------------------------
st.subheader("Figure preview")
try:
    result = render(spec, table_info.dataframe, style=style, aux=pca_aux)
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
            file_name=f"{os.path.splitext(table_name)[0]}_{plot_type}.stats_spec.json",
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
