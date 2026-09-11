"""Guided matrix workflow for the Streamlit app.

Upload -> confirm column roles -> build/confirm metadata -> validate -> recommend
-> (optional) differential summary -> generate a publication plot -> download / add
to the Figure Builder. All state is kept in ``st.session_state`` under the ``mw_``
prefix so it survives reruns and plot-type changes. No silent guessing: suggestions
are shown, the user confirms. This is a generic feature matrix (no raw-count
pipeline, no R).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

import make_my_figure_core.matrix_workflow as mw
from make_my_figure_core.matrix_workflow.differential_summary import (
    CORRECTIONS,
    MULTI_GROUP_TESTS,
    TWO_GROUP_TESTS,
)
from make_my_figure_core.matrix_workflow.matrix_spec import VALUE_TYPES
from make_my_figure_core.plots.registry import figure_to_bytes, make_spec, render


def _get(key: str, default: Any = None) -> Any:
    return st.session_state.get(f"mw_{key}", default)


def _set(key: str, value: Any) -> None:
    st.session_state[f"mw_{key}"] = value


def _spec() -> Optional[mw.MatrixSpec]:
    d = _get("spec")
    return mw.MatrixSpec.from_dict(d) if d else None


def _meta() -> Optional[mw.SampleMetadataSpec]:
    d = _get("meta")
    return mw.SampleMetadataSpec.from_dict(d) if d else None


def render_matrix_wizard(df: pd.DataFrame, source_name: str) -> None:
    st.header("Matrix workflow (guided)")
    st.caption("Map a feature-by-sample matrix, define groups, then get plot "
               "recommendations. Nothing is plotted until you confirm the mapping — "
               "annotation columns are never treated as measurements. Generic feature "
               "matrix; no raw-count pipeline, no R.")
    if st.button("↺ Restart matrix workflow"):
        for k in [k for k in st.session_state if k.startswith("mw_")]:
            del st.session_state[k]
        st.rerun()

    _step_map_columns(df, source_name)
    spec = _spec()
    if spec and spec.confirmed_by_user:
        _step_metadata(df, spec)
    meta = _meta()
    if spec and spec.confirmed_by_user:
        _step_preprocess(df, spec, meta)
        # Downstream steps use the processed matrix if the user applied one,
        # otherwise the raw uploaded matrix. The original is never mutated.
        active_df, active_spec = _active_matrix(df, spec)
        _step_validate(active_df, active_spec, meta)
        _step_recommend_and_generate(active_df, active_spec, meta)
    _step_figure_builder()


def _active_matrix(df: pd.DataFrame, spec: mw.MatrixSpec):
    """The matrix downstream steps operate on: processed if the user applied a
    confirmed preprocessing chain, else the raw uploaded matrix."""
    proc = _get("processed_df")
    proc_spec = _get("processed_spec")
    if proc is not None and proc_spec:
        return proc, mw.MatrixSpec.from_dict(proc_spec)
    return df, spec


# --- Step 1: map columns -------------------------------------------------
def _step_map_columns(df: pd.DataFrame, source_name: str) -> None:
    confirmed = bool(_get("spec"))
    header = "① Map columns" + (" ✅" if confirmed else "")
    with st.expander(header, expanded=not confirmed):
        sug = mw.suggest_matrix_spec(df, source_file=source_name)
        cols = list(df.columns)
        c1, c2 = st.columns(2)
        feature_id = c1.selectbox("Feature ID column", cols,
                                  index=cols.index(sug.feature_id_column)
                                  if sug.feature_id_column in cols else 0, key="mw_ui_fid")
        disp_opts = ["(none)"] + [c for c in cols if c != feature_id]
        disp_default = sug.feature_display_column if sug.feature_display_column in disp_opts else "(none)"
        display = c2.selectbox("Feature display column (optional)", disp_opts,
                               index=disp_opts.index(disp_default), key="mw_ui_disp")
        others = [c for c in cols if c != feature_id and c != (None if display == "(none)" else display)]
        value_default = [c for c in sug.value_columns if c in others]
        value_cols = st.multiselect("Value (sample/measurement) columns", others,
                                    default=value_default, key="mw_ui_vals",
                                    help="Numeric per-sample measurements only. Numeric "
                                         "annotation columns (e.g. a 1/2/3 level code) are "
                                         "left out by default — add them only if they are "
                                         "real measurements.")
        annot_default = [c for c in others if c not in value_cols]
        annotation_cols = st.multiselect("Annotation columns", others,
                                         default=annot_default, key="mw_ui_annot")
        value_type = st.selectbox(
            "Value scale (you confirm — never inferred)", list(VALUE_TYPES),
            index=list(VALUE_TYPES).index("unknown_user_confirmed"), key="mw_ui_vtype",
            help="Drives fold-change: log_normalized -> mean difference; normalized/"
                 "raw_numeric -> log2 ratio; unknown -> mean difference only.")
        if value_cols and mw.looks_log_scale(df, value_cols) and value_type == "unknown_user_confirmed":
            st.caption("Hint: these values look log-scaled (modest range / negatives). "
                       "If so, choose **log_normalized**.")
        if not value_cols:
            st.warning("Select at least one value column.")
        if st.button("Confirm mapping", type="primary", disabled=not value_cols):
            spec = mw.MatrixSpec(
                source_file=source_name, feature_id_column=feature_id,
                feature_display_column=None if display == "(none)" else display,
                annotation_columns=annotation_cols, value_columns=value_cols,
                value_type=value_type, confirmed_by_user=True)
            _set("spec", spec.to_dict())
            # a mapping change invalidates any downstream differential table
            _set("diff", None)
            st.rerun()
        if confirmed:
            s = _spec()
            st.success(f"Confirmed: {len(s.value_columns)} value columns, "
                       f"feature id '{s.feature_id_column}', scale '{s.value_type}'.")


# --- Step 2: metadata / groups ------------------------------------------
def _step_metadata(df: pd.DataFrame, spec: mw.MatrixSpec) -> None:
    confirmed = bool(_get("meta"))
    with st.expander("② Define groups" + (" ✅" if confirmed else ""), expanded=not confirmed):
        mode = st.radio("How do you want to define groups?",
                        ["Build in-app", "Upload metadata table"], key="mw_ui_metamode",
                        horizontal=True)
        if mode == "Build in-app":
            existing = (_meta().sample_to_group if _meta() else {})
            assign = pd.DataFrame({"sample": spec.value_columns,
                                   "group": [existing.get(s, "") for s in spec.value_columns]})
            edited = st.data_editor(assign, hide_index=True, use_container_width=True,
                                    key="mw_ui_assign")
            if st.button("Confirm groups", type="primary"):
                s2g = {str(r["sample"]): str(r["group"]) for _, r in edited.iterrows()
                       if str(r["group"]).strip()}
                _set("meta", mw.metadata_from_assignment(s2g).to_dict())
                _set("diff", None)
                st.rerun()
        else:
            up = st.file_uploader("Metadata table (CSV/TSV/XLSX)",
                                  type=["csv", "tsv", "txt", "xlsx", "xls"], key="mw_ui_metafile")
            if up is not None:
                meta_df = _read_table(up)
                sug = mw.suggest_metadata_from_table(meta_df, spec.value_columns)
                mcols = list(meta_df.columns)
                sid = st.selectbox("Sample ID column", mcols,
                                   index=mcols.index(sug.sample_id_column)
                                   if sug.sample_id_column in mcols else 0, key="mw_ui_sid")
                gcol = st.selectbox("Group column", mcols,
                                    index=mcols.index(sug.group_column)
                                    if sug.group_column in mcols else 0, key="mw_ui_gcol")
                match = mw.metadata_sample_match(
                    mw.SampleMetadataSpec(sample_to_group={
                        str(r[sid]): str(r[gcol]) for _, r in meta_df.iterrows()}),
                    spec.value_columns)
                st.caption(f"{len(match['matched'])} of {len(spec.value_columns)} value "
                           f"columns matched by sample id.")
                if st.button("Confirm groups", type="primary", disabled=not match["matched"]):
                    s2g = {str(r[sid]): str(r[gcol]) for _, r in meta_df.iterrows()
                           if str(r[sid]) in set(spec.value_columns)}
                    _set("meta", mw.metadata_from_assignment(s2g).to_dict())
                    _set("diff", None)
                    st.rerun()
        if confirmed:
            st.success("Groups: " + ", ".join(f"{g} (n={n})"
                       for g, n in _meta().group_sizes().items()))


# --- Optional step: preprocess a raw-like matrix -------------------------
def _step_preprocess(df: pd.DataFrame, spec: mw.MatrixSpec, meta) -> None:
    applied = _get("processed_df") is not None
    header = "🧪 Preprocess (raw-like, optional)" + (" ✅" if applied else "")
    with st.expander(header, expanded=False):
        st.caption("For raw, unnormalized, skewed, count-like or intensity-like matrices. "
                   "The app diagnoses and recommends — nothing is applied until you confirm. "
                   "The original matrix is never changed; every step is recorded in a "
                   "reproducible preprocessing spec. Python-only, no R.")

        if st.button("Run diagnostics", key="mw_prep_diag_btn"):
            try:
                _set("qc", mw.diagnose_matrix(df, spec))
            except Exception as exc:  # noqa: BLE001
                st.error(f"Diagnostics failed: {exc}")

        qc = _get("qc")
        if qc is None:
            st.info("Run diagnostics to see the data profile and recommended preprocessing.")
        else:
            _render_qc_summary(qc)
            recs = mw.recommend_preprocessing(qc)
            if not recs:
                st.success("No preprocessing looks necessary for this matrix.")
            else:
                labels = {f"{r.name} — {r.reason}": r for r in recs}
                choice = st.selectbox("Recommended preprocessing", list(labels), key="mw_ui_prep")
                rec = labels[choice]
                st.markdown("**Steps:** " + " → ".join(f"`{s['method']}`" for s in rec.steps))
                for a in rec.assumptions:
                    st.caption(f"• assumes: {a}")
                for w in rec.warnings:
                    st.warning(w)
                confirm = st.checkbox(
                    "I confirm applying this preprocessing chain to a derived copy",
                    key="mw_ui_prep_confirm")
                if st.button("Apply preprocessing", disabled=not confirm, key="mw_prep_apply_btn"):
                    try:
                        final_df, dspec, ps = mw.run_preprocessing(
                            df, spec, rec.steps, metadata=meta, output_matrix_id="processed")
                        _set("processed_df", final_df)
                        _set("processed_spec", dspec.to_dict())
                        _set("processed_id", ps.output_matrix_id)
                        _set("prep_note", ps.method_sentence())
                        # Full records for the reproducible figure package (raw matrix + specs).
                        _set("prep_spec", ps.to_dict())
                        _set("raw_matrix_df", df)
                        _set("raw_matrix_spec", spec.to_dict())
                        _set("raw_matrix_name", source_name)
                        _set("meta_spec", meta.to_dict() if meta is not None else None)
                        # A derived matrix invalidates any differential summary on the raw one.
                        for k in ("diff", "diff_sentence"):
                            st.session_state.pop(f"mw_{k}", None)
                        st.success("Applied. " + ps.method_sentence())
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Preprocessing failed: {exc}")

        if _get("processed_df") is not None:
            st.divider()
            st.markdown("✅ **Downstream steps now use the processed matrix.** "
                        + (_get("prep_note") or ""))
            proc_spec = mw.MatrixSpec.from_dict(_get("processed_spec"))
            _before_after_qc(df, spec, _get("processed_df"), proc_spec, meta)
            if st.button("↺ Revert to raw matrix", key="mw_prep_revert_btn"):
                for k in ("processed_df", "processed_spec", "processed_id", "prep_note",
                          "diff", "diff_sentence"):
                    st.session_state.pop(f"mw_{k}", None)
                st.rerun()


def _render_qc_summary(qc) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Features", qc.n_features)
    c2.metric("Samples", qc.n_samples)
    c3.metric("Zero fraction", f"{qc.zero_fraction:.0%}")
    skew = qc.skewness_summary.get("overall")
    c4.metric("Skew (overall)", f"{skew:.2f}" if skew is not None else "n/a")
    st.caption(f"Suspected data type: **{qc.suspected_data_type}** · "
               f"negative fraction {qc.negative_value_fraction:.0%} · "
               f"integer-like: {qc.integer_like}")
    for w in qc.warnings:
        st.warning(w)


def _before_after_qc(raw_df, raw_spec, proc_df, proc_spec, meta) -> None:
    kinds = {c["label"]: c["key"] for c in mw.qc_plot_catalog()}
    kind_label = st.selectbox("Before/after QC plot", list(kinds), key="mw_ui_prep_qc")
    kind = kinds[kind_label]
    b1, b2 = st.columns(2)
    with b1:
        st.caption("Before (raw)")
        _render_qc_plot(kind, raw_df, raw_spec, meta)
    with b2:
        st.caption("After (processed)")
        _render_qc_plot(kind, proc_df, proc_spec, meta)


def _render_qc_plot(kind: str, df: pd.DataFrame, spec: mw.MatrixSpec, meta) -> None:
    try:
        pi = mw.qc_plot_inputs(kind, df, spec, metadata=meta)
        ps = make_spec(pi.plot_type, spec.source_file or "matrix", "publication",
                       mapping=pi.mapping,
                       source=st.session_state.get("_mw_source_prov"))
        for k, v in (pi.spec_extra or {}).items():
            ps[k] = v
        result = render(ps, pi.dataframe, aux=pi.aux or None)
        st.pyplot(result.figure)
    except Exception as exc:  # noqa: BLE001
        st.caption(f"⚠ {exc}")


# --- Step 3: validate ----------------------------------------------------
def _step_validate(df: pd.DataFrame, spec: mw.MatrixSpec, meta) -> None:
    with st.expander("③ Validation", expanded=False):
        rep = mw.validate_matrix(df, spec, meta)
        s = rep.summary
        c = st.columns(4)
        c[0].metric("Features", s.get("n_features", 0))
        c[1].metric("Samples", s.get("n_samples", 0))
        c[2].metric("Groups", s.get("n_groups", 0))
        c[3].metric("Missing values", s.get("n_missing_values", 0))
        if s.get("group_sizes"):
            st.caption("Group sizes: " + ", ".join(f"{g}={n}" for g, n in s["group_sizes"].items()))
        for e in rep.errors:
            st.error(e)
        for w in rep.warnings:
            st.warning(w)
        if rep.ok:
            st.success("Validation passed.")


# --- Step 4: recommend + generate ---------------------------------------
def _step_recommend_and_generate(df: pd.DataFrame, spec: mw.MatrixSpec, meta) -> None:
    with st.expander("④ Recommended plots & generate", expanded=True):
        has_diff = _get("diff") is not None
        _differential_summary_section(df, spec, meta)
        recs = mw.recommend_plots(spec, meta, has_differential_summary=has_diff,
                                  n_features=len(df))
        ready = [r for r in recs if r.readiness_status == "ready"]
        not_ready = [r for r in recs if r.readiness_status != "ready"]
        if not ready:
            st.info("No plots are ready yet — confirm groups and/or compute a "
                    "differential summary above.")
        labels = {f"{r.label}  —  {r.reason}": r for r in ready}
        if labels:
            choice = st.selectbox("Choose a recommended plot", list(labels), key="mw_ui_rec")
            rec = labels[choice]
            _generate_section(df, spec, meta, rec)
        if not_ready:
            st.caption("Not yet available: " + "; ".join(
                f"{r.label} ({r.readiness_status.replace('_', ' ')})" for r in not_ready))


def _differential_summary_section(df: pd.DataFrame, spec: mw.MatrixSpec, meta) -> None:
    gate = mw.require_for_statistics(spec, meta)
    with st.container():
        st.markdown("**Feature-level differential summary** (optional — enables volcano / "
                    "MA / ranked-effect). Generic per-feature test on normalized values; "
                    "not a raw-count model.")
        if not gate.ok:
            for e in gate.errors:
                st.caption(f"• {e}")
            return
        groups = meta.groups()
        c1, c2, c3 = st.columns(3)
        test = c1.selectbox("Test", list(TWO_GROUP_TESTS) + list(MULTI_GROUP_TESTS), key="mw_ui_test")
        correction = c2.selectbox("Correction", list(CORRECTIONS), key="mw_ui_corr")
        multi = test in MULTI_GROUP_TESTS
        ga = c3.selectbox("Group A", groups, key="mw_ui_ga")
        gb = None
        if not multi:
            gb_opts = [g for g in groups if g != ga]
            gb = st.selectbox("Group B", gb_opts, key="mw_ui_gb") if gb_opts else None
        if st.button("Compute differential summary"):
            try:
                res = mw.feature_differential_summary(
                    df, spec, meta, group_a=ga, group_b=gb, test=test, correction=correction,
                    preprocessing_note=_get("prep_note", ""),
                    source_matrix_id=_get("processed_id") or None,
                    preprocessing_spec_id=_get("processed_id") or None)
                _set("diff", res.table)
                _set("diff_sentence", res.method_sentence())
                st.success(res.method_sentence())
                for w in res.warnings:
                    st.warning(w)
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
        if _get("diff") is not None:
            st.caption("✅ Differential summary ready. " + (_get("diff_sentence") or ""))
            st.download_button("Download differential summary CSV",
                               _get("diff").to_csv(index=False),
                               file_name="differential_summary.csv", mime="text/csv")


def _generate_section(df: pd.DataFrame, spec: mw.MatrixSpec, meta, rec) -> None:
    """Prepare mappings + hand the recommendation to the full plot editor.

    This tab only prepares data + mappings and shows *why* a plot is recommended.
    Thresholds, labels, colors, annotations, layout, and export all live in the one
    canonical plot editor — there is no second reduced plot UI here."""
    from make_my_figure_core.matrix_workflow.plot_builder import build_plot_inputs
    from make_my_figure_core.plots.handoff import build_matrix_provenance

    # Data-prep choices only (which features / how many / which significance column).
    params: Dict[str, Any] = {}
    selected: Optional[List[str]] = None
    if rec.key in ("box_by_group", "dot_by_group", "raincloud_by_group", "bar_by_group"):
        fid = spec.feature_id_column
        feats = df[fid].astype(str).tolist()
        selected = st.multiselect("Feature(s) to show (blank = most variable)", feats,
                                  key="mw_ui_feats", max_selections=12)
    if rec.key in ("top_variable_heatmap", "ranked_effect"):
        params["top_n"] = st.slider("Top N", 5, 100, 30, key=f"mw_ui_topn_{rec.key}")
    if rec.key in ("volcano", "ma"):
        # Suggested y-axis significance field (editable later in the plot editor).
        sig = st.radio("Suggested y-axis significance", ["adjusted p-value (FDR)", "raw p-value"],
                       horizontal=True, key=f"mw_ui_sig_{rec.key}")
        params["significance"] = "fdr" if sig.startswith("adjusted") else "pvalue"

    st.caption("Open this recommendation in the full plot editor to adjust thresholds, "
               "labels, colors, annotations, layout, and export settings.")
    c1, c2 = st.columns(2)
    open_clicked = c1.button("Open in plot editor", key=f"mw_open_{rec.key}", type="primary")
    preview_clicked = c2.button("Quick preview", key=f"mw_prev_{rec.key}")
    if not (open_clicked or preview_clicked):
        return

    try:
        pi = build_plot_inputs(rec, df, spec, metadata=meta, differential_table=_get("diff"),
                               selected_features=selected, params=params)
    except Exception as exc:  # noqa: BLE001
        st.error(str(exc))
        return
    for w in pi.warnings:
        st.caption(f"• {w}")

    if open_clicked:
        prep = [_get("prep_note")] if _get("prep_note") else None
        stats = ({"method": _get("diff_sentence")}
                 if _get("diff_sentence") and rec.key in ("volcano", "ma", "ranked_effect")
                 else None)
        prov = build_matrix_provenance(spec, metadata=meta, preprocessing=prep,
                                       statistics=stats)
        base_prov = st.session_state.get("_mw_source_prov") or {}
        prov = {**base_prov, **prov}
        # Clear any prior plot's mapping widgets, then seed the handoff state the
        # Quick-plot editor consumes (one source of truth for all plot controls).
        for k in [k for k in list(st.session_state)
                  if str(k).startswith(("map_", "valcols_", "annot_"))]:
            del st.session_state[k]
        st.session_state["_grouped_df"] = pi.dataframe
        st.session_state["_grouped_name"] = f"{spec.source_file or 'matrix'} · {rec.key}"
        st.session_state["rec_plot_type"] = pi.plot_type
        st.session_state["_handoff_mappings"] = dict(pi.mapping)
        st.session_state["_handoff_defaults"] = {
            k: v for k, v in (pi.mapping or {}).items()
            if k in ("use_fdr", "significance", "scale", "color_scale", "cluster_rows",
                     "cluster_columns", "points", "kind", "error", "sort", "metadata_key",
                     "group_separators")}
        st.session_state["_handoff_spec_extra"] = dict(pi.spec_extra or {})
        st.session_state["_handoff_aux"] = pi.aux or None
        st.session_state["_handoff_source"] = prov
        st.session_state["workflow_mode"] = "Quick plot"
        st.rerun()
        return

    # Quick preview only (default Publication style; full control is in the editor).
    ps = make_spec(pi.plot_type, spec.source_file or "matrix", "publication",
                   mapping=pi.mapping, source=st.session_state.get("_mw_source_prov"))
    for _k, _v in (pi.spec_extra or {}).items():
        ps[_k] = _v
    try:
        result = render(ps, pi.dataframe, aux=pi.aux or None)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Render failed: {exc}")
        return
    st.pyplot(result.figure)
    st.caption("Quick preview (default style). Use **Open in plot editor** for full control.")
    for w in (result.warnings or []):
        st.caption(f"⚠ {w}")


# --- Figure Builder ------------------------------------------------------
def _step_figure_builder() -> None:
    panels = _get("panels", [])
    if not panels:
        return
    with st.expander(f"⑤ Figure Builder ({len(panels)} panel(s))", expanded=False):
        st.write(", ".join(p["name"] for p in panels))
        cols = st.number_input("Columns", 1, 4, min(2, len(panels)), key="mw_ui_cols")
        if st.button("Compose multi-panel figure"):
            try:
                from make_my_figure_core.panels import build_figure
                from make_my_figure_core.panels.models import (
                    FigureLayout,
                    MultiPanelFigure,
                    Panel,
                )
                mpf = MultiPanelFigure(name="Figure 1",
                                       layout=FigureLayout(ncols=int(cols)))
                for p in panels:
                    mpf.add_panel(Panel(plot_spec=p["plot_spec"], table=p["table"],
                                        aux=p.get("aux") or {}, source_name=p["name"]))
                fig = build_figure(mpf)
                st.pyplot(fig)
                fc1, fc2, fc3 = st.columns(3)
                fc1.download_button("PNG", figure_to_bytes(fig, "png"),
                                    file_name="figure.png", mime="image/png")
                fc2.download_button("SVG", figure_to_bytes(fig, "svg"),
                                    file_name="figure.svg", mime="image/svg+xml")
                fc3.download_button("PDF", figure_to_bytes(fig, "pdf"),
                                    file_name="figure.pdf", mime="application/pdf")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Compose failed: {exc}")
        if st.button("Clear Figure Builder"):
            _set("panels", [])
            st.rerun()


def _read_table(uploaded) -> pd.DataFrame:
    name = uploaded.name.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded)
    sep = "\t" if name.endswith((".tsv", ".txt")) else ","
    return pd.read_csv(uploaded, sep=sep)
