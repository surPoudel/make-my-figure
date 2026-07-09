"""Streamlit RNA-seq workflow view.

Shares the same :mod:`make_my_figure_core.rnaseq` engine as the desktop app:
upload a table, detect the mode, map columns, and generate a volcano (from a
precomputed DE table) or a heatmap (from a normalized matrix). Raw-count DE runs
through R and degrades gracefully with install instructions when R is missing.
"""

from __future__ import annotations

import io
import json

import pandas as pd

from make_my_figure_core.plots.registry import figure_to_bytes, render
from make_my_figure_core.rnaseq import (
    build_expression_matrix, check_r_environment, classify_de, detect_input_mode,
    heatmap_spec_from_expression, load_rnaseq_table, parse_de_table,
    volcano_spec_from_de,
)
from make_my_figure_core.rnaseq.detect import split_expression_matrix
from make_my_figure_core.rnaseq.spec import RnaSeqSpec, method_report_markdown


def _fig_downloads(st, fig, basename):
    c1, c2, c3 = st.columns(3)
    c1.download_button("SVG", figure_to_bytes(fig, "svg"), file_name=f"{basename}.svg",
                       mime="image/svg+xml")
    c2.download_button("PNG", figure_to_bytes(fig, "png"), file_name=f"{basename}.png",
                       mime="image/png")
    c3.download_button("PDF", figure_to_bytes(fig, "pdf"), file_name=f"{basename}.pdf",
                       mime="application/pdf")


def render_rnaseq_workflow(st) -> None:
    st.header("RNA-seq workflow")
    st.caption("Upload a precomputed DE table, a normalized expression matrix, or raw counts. "
               "Statistics are never fabricated — DE p-values come from your table or the R pipeline.")

    up = st.file_uploader("Upload RNA-seq table (DE result / matrix / counts)",
                          type=["txt", "tsv", "csv", "xlsx"])
    if up is None:
        st.info("Example files live in `test_matrix/` — e.g. `Ctrl_vs_Treatment_DE.txt` "
                "(volcano) or `voom_norm_annot.txt` (heatmap).")
        return

    info = load_rnaseq_table(io.BytesIO(up.getvalue()), source_name=up.name)
    det = detect_input_mode(info)
    modes = ["de_result", "expression_matrix", "raw_counts", "sample_metadata", "unknown"]
    mode = st.selectbox("Detected mode (override if needed)", modes,
                        index=modes.index(det["mode"]) if det["mode"] in modes else 0)
    st.caption("Detection: " + "; ".join(det.get("reasons", [])))
    st.dataframe(info.dataframe.head(10), use_container_width=True)

    if mode == "de_result":
        _de_volcano(st, info, up.name)
    elif mode == "expression_matrix":
        _matrix_heatmap(st, info, up.name)
    elif mode == "raw_counts":
        _raw_counts(st, info)
    else:
        st.warning("This table was not recognized as a DE result, matrix, or counts. "
                   "Override the mode above if you know its type.")


def _de_volcano(st, info, name):
    st.subheader("Volcano from precomputed DE result")
    det = detect_input_mode(info)["de_columns"]
    cols = list(info.dataframe.columns)
    c1, c2, c3 = st.columns(3)
    lfc = c1.number_input("|log2FC| >=", value=1.0, step=0.5)
    alpha = c2.number_input("p / FDR <", value=0.05, step=0.01, format="%.4f")
    use_adj = c3.checkbox("Use adjusted p (FDR)", value=True)
    topn = st.slider("Top N labels", 0, 60, 15)
    selected = st.text_input("Also label these genes (comma-separated)", "")
    de = classify_de(parse_de_table(info.dataframe), lfc_cutoff=lfc, alpha=alpha, use_adjusted=use_adj)
    m1, m2, m3 = st.columns(3)
    m1.metric("Up", de.n_up); m2.metric("Down", de.n_down); m3.metric("n.s.", de.n_ns)
    spec = volcano_spec_from_de(de, top_n_labels=topn,
                                selected_genes=[s.strip() for s in selected.split(",") if s.strip()] or None,
                                input_table=name)
    res = render(spec, de.frame)
    st.pyplot(res.figure, use_container_width=False)
    _fig_downloads(st, res.figure, name.rsplit(".", 1)[0] + "_volcano")

    spec_obj = RnaSeqSpec(input_mode="de_result", volcano_thresholds=de.thresholds,
                          de_columns_used=de.mapping)
    st.download_button("RnaSeqSpec JSON", json.dumps(spec_obj.to_dict(), indent=2).encode(),
                       file_name="analysis.rnaseq_spec.json", mime="application/json")
    st.download_button("Significant gene table (CSV)",
                       de.frame[de.frame["_class"].isin(["Up", "Down"])].to_csv().encode(),
                       file_name="significant_genes.csv", mime="text/csv")
    with st.expander("Method report"):
        st.markdown(method_report_markdown(spec_obj))


def _matrix_heatmap(st, info, name):
    st.subheader("Heatmap from normalized expression matrix")
    mc, sc = split_expression_matrix(info.dataframe)
    em = build_expression_matrix(info.dataframe, metadata_columns=mc, sample_columns=sc)
    st.caption(f"{len(sc)} samples, gene id='{em.gene_id_col}', symbol='{em.gene_symbol_col}'")
    c1, c2, c3 = st.columns(3)
    transform = c1.selectbox("Transform", ["zscore", "log2cpm", "cpm", "log2p1", "none"])
    selection = c2.selectbox("Genes", ["top_variable", "selected", "all"])
    n_genes = c3.slider("N genes", 2, 200, 50)
    genes = st.text_input("Genes (for 'selected', comma-separated)", "")
    meta_up = st.file_uploader("Optional sample metadata for annotation strips",
                               type=["csv", "tsv", "txt", "xlsx"], key="hm_meta")
    metadata = sid = None
    annot_cols = []
    if meta_up is not None:
        from make_my_figure_core.io.loaders import load_table
        metadata = load_table(io.BytesIO(meta_up.getvalue()), source_name=meta_up.name).dataframe
        sid = next((c for c in metadata.columns
                    if c.lower() in ("sampleid", "sample_id", "sample", "id")), None)
        annot_cols = st.multiselect("Annotation tracks", list(metadata.columns))
    hm = heatmap_spec_from_expression(
        em, transform=transform, selection=selection, n_genes=n_genes,
        genes=[g.strip() for g in genes.split(",") if g.strip()] or None,
        metadata=metadata, sample_id_col=sid, annotation_columns=annot_cols or None)
    res = render(hm["spec"], hm["dataframe"])
    st.pyplot(res.figure, use_container_width=False)
    _fig_downloads(st, res.figure, name.rsplit(".", 1)[0] + "_heatmap")
    spec_obj = RnaSeqSpec(input_mode="expression_matrix", heatmap_transform=hm["transform"],
                          gene_selection_method=hm["selection"])
    st.download_button("RnaSeqSpec JSON", json.dumps(spec_obj.to_dict(), indent=2).encode(),
                       file_name="analysis.rnaseq_spec.json", mime="application/json")


def _raw_counts(st, info):
    st.subheader("Differential expression from raw counts")
    env = check_r_environment()
    if env.ready:
        st.success("R environment ready: " + (env.r_version or ""))
    else:
        st.error(env.message)
        st.info("You can still generate volcano plots from a precomputed DE table without R.")
    st.write("Upload sample metadata and choose the design, then run the edgeR + limma-voom "
             "pipeline. (Running DE requires R with edgeR/limma.)")
    meta_up = st.file_uploader("Sample metadata", type=["csv", "tsv", "txt", "xlsx"], key="rc_meta")
    if meta_up is None:
        return
    from make_my_figure_core.io.loaders import load_table
    from make_my_figure_core.rnaseq.validate import validate_counts, validate_metadata
    metadata = load_table(io.BytesIO(meta_up.getvalue()), source_name=meta_up.name).dataframe
    _, sample_cols = split_expression_matrix(info.dataframe)
    group = st.selectbox("Condition column", list(metadata.columns))
    crep = validate_counts(info.dataframe, sample_cols)
    mrep = validate_metadata(metadata, group_col=group, count_samples=sample_cols)
    with st.expander("Validation", expanded=True):
        st.write("Counts:", "OK" if crep.ok else "errors", crep.errors + crep.warnings)
        st.write("Metadata:", "OK" if mrep.ok else "errors", mrep.errors + mrep.warnings)
    levels = [str(x) for x in metadata[group].dropna().unique()]
    ref = st.selectbox("Reference group", levels)
    comp = st.selectbox("Comparison group", [l for l in levels if l != ref] or levels)
    covs = st.text_input("Covariates (comma-separated)", "")
    if st.button("Run RNA-seq DE", disabled=not env.ready):
        from make_my_figure_core.rnaseq import run_de_pipeline
        from make_my_figure_core.rnaseq.runner import RDependencyError
        base = info.dataframe
        counts = base.set_index(base.columns[0])[sample_cols]
        sid = next((c for c in metadata.columns
                    if c.lower() in ("sampleid", "sample_id", "sample", "id")), None)
        try:
            res = run_de_pipeline(counts, metadata, sample_id_col=sid, group_col=group,
                                  reference_group=ref,
                                  comparisons=[{"group1": comp, "group2": ref}],
                                  covariates=[c.strip() for c in covs.split(",") if c.strip()])
        except RDependencyError as exc:
            st.error(str(exc)); return
        except Exception as exc:
            st.error(f"DE failed: {exc}"); return
        st.success("DE complete: " + res["method"].get("de_method", ""))
        st.code(res["log"])
